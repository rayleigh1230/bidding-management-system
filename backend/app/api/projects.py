import json
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..core.security import get_current_user
from ..models.project import (
    ProjectInfo, ProjectStatus, BudgetType,
    BidStatus, DepositStatus, ContractStatus, ResultDepositStatus,
)
from ..models.organization import Organization
from ..models.manager import Manager
from ..models.platform import Platform
from ..models.user import User
from ..schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse
from ..services.logger import log_operation

# ---- 多标段父项目状态推导 ----

_STATUS_PRIORITY = {
    ProjectStatus.following: 0,
    ProjectStatus.published: 1,
    ProjectStatus.not_registered: 2,
    ProjectStatus.registered: 3,
    ProjectStatus.preparing: 4,
    ProjectStatus.submitted: 5,
}


def recalc_multi_lot_parent_status(parent_id: int, db: Session):
    """当子标段状态变更时，重新计算多标段父项目的状态。
    状态跟随截止到"已投标"，已中标/未中标/已流标不再同步；
    如果所有子标段都已放弃，父项目也变为已放弃。"""
    parent = db.query(ProjectInfo).filter(ProjectInfo.id == parent_id).first()
    if not parent or not parent.is_multi_lot:
        return

    children = db.query(ProjectInfo).filter(
        ProjectInfo.parent_project_id == parent_id
    ).all()

    if not children:
        return

    if all(c.status == ProjectStatus.abandoned for c in children):
        parent.status = ProjectStatus.abandoned
    else:
        active = [c for c in children if c.status != ProjectStatus.abandoned]
        if not active:
            return
        max_priority = max(_STATUS_PRIORITY.get(c.status, 0) for c in active)
        for s, p in _STATUS_PRIORITY.items():
            if p == max_priority:
                parent.status = s
                break

    db.commit()


router = APIRouter(prefix="/api/projects", tags=["项目管理"])


# ---- Price calculation helpers (moved from bid_results.py) ----

def _control_type_str(raw) -> str:
    """将数据库中的 control_price_type（枚举名或值）统一转为中文值。"""
    if isinstance(raw, BudgetType):
        return raw.value
    s = str(raw)
    for bt in BudgetType:
        if s == bt.name or s == bt.value:
            return bt.value
    return "金额"


def _format_price(value, control_type: str) -> str:
    if value is None or float(value) == 0:
        return "-"
    v = float(value)
    if control_type == "金额":
        return f"¥{v:,.2f}"
    elif control_type in ("折扣率", "下浮率"):
        return f"{v}%"
    return f"{v}"


def _calc_winning_amount(price_value, control_type: str, control_upper, budget) -> float | None:
    v = float(price_value) if price_value else 0
    if v == 0:
        return None
    if control_type == "金额":
        return round(v, 2)
    upper = float(control_upper) if control_upper else 0
    budget_f = float(budget) if budget else 0
    if upper == 0 or budget_f == 0:
        return None
    if control_type == "折扣率":
        return round(v / upper * budget_f, 2)
    if control_type == "下浮率":
        return round((1 - v / 100) / (1 - upper / 100) * budget_f, 2)
    return None


def _format_amount(value) -> str:
    if value is None or float(value) == 0:
        return "-"
    return f"¥{float(value):,.2f}"


def _enrich_winning_display(is_won, control_type, our_price, winning_price, winning_amount, control_upper, budget) -> dict:
    def _has_value(v):
        return v is not None and float(v) != 0

    result = {}
    if is_won:
        if control_type == "金额":
            result["winning_price_display"] = "-"
            amount = winning_amount if _has_value(winning_amount) else our_price
            result["winning_amount_display"] = _format_amount(amount)
        else:
            price = winning_price if _has_value(winning_price) else our_price
            result["winning_price_display"] = _format_price(price, control_type)
            if _has_value(winning_amount):
                result["winning_amount_display"] = _format_amount(winning_amount)
            else:
                result["winning_amount_display"] = _format_amount(
                    _calc_winning_amount(price, control_type, control_upper, budget)
                )
    else:
        if control_type == "金额":
            result["winning_price_display"] = "-"
            result["winning_amount_display"] = _format_amount(winning_amount)
        else:
            result["winning_price_display"] = _format_price(winning_price, control_type)
            if _has_value(winning_amount):
                result["winning_amount_display"] = _format_amount(winning_amount)
            else:
                result["winning_amount_display"] = _format_amount(
                    _calc_winning_amount(winning_price, control_type, control_upper, budget)
                )
    return result


# ---- Enrich function ----

def _parse_json_list(raw):
    """将 JSON 字段统一解析为 list"""
    if not raw:
        return []
    if isinstance(raw, list):
        return raw
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return []
    return []


def _enrich_project_with_maps(project: ProjectInfo, org_map: dict, manager_map: dict, platform_map: dict, user_map: dict, parent_map: dict, parent_map_meta: dict = None) -> dict:
    """使用预加载的映射表填充 enrich 字段（无数据库查询）"""
    data = ProjectResponse.model_validate(project).model_dump()

    # bidding_unit_name
    data["bidding_unit_name"] = org_map.get(project.bidding_unit_id, {}).get("name") if project.bidding_unit_id else None

    # manager_names
    mids = _parse_json_list(project.manager_ids)
    data["manager_names"] = [manager_map.get(mid) for mid in mids if mid in manager_map]

    # agency_name
    data["agency_name"] = org_map.get(project.agency_id, {}).get("name") if project.agency_id else None

    # platform_name
    data["platform_name"] = platform_map.get(project.publish_platform_id) if project.publish_platform_id else None

    # specialist_name
    data["specialist_name"] = user_map.get(project.bid_specialist_id) if project.bid_specialist_id else None

    # partner_names
    pids = _parse_json_list(project.partner_ids)
    data["partner_names"] = [org_map.get(pid, {}).get("name") for pid in pids if pid in org_map]

    # winning_org_name (backward compat)
    data["winning_org_name"] = org_map.get(project.winning_org_id, {}).get("name") if project.winning_org_id else None

    # winning_org_names (multi)
    winning_ids = _parse_json_list(project.winning_org_ids)
    if winning_ids:
        data["winning_org_names"] = [org_map.get(oid, {}).get("name") for oid in winning_ids if oid in org_map]
        if not data["winning_org_name"] and winning_ids:
            data["winning_org_name"] = org_map.get(winning_ids[0], {}).get("name")
    else:
        data["winning_org_names"] = []

    # competitors: backward compat + enrich org_names
    raw_competitors = _parse_json_list(data.get("competitors", []))
    converted = []
    for c in raw_competitors:
        if not isinstance(c, dict):
            continue
        if "org_ids" not in c and "org_id" in c:
            c["org_ids"] = [c["org_id"]] if c["org_id"] else []
        if "org_ids" not in c:
            c["org_ids"] = []
        if "is_winning" not in c:
            c["is_winning"] = False
        c["org_names"] = [org_map.get(oid, {}).get("name", "未知单位") for oid in c["org_ids"]]
        converted.append(c)
    data["competitors"] = converted

    # Price displays
    control_type = _control_type_str(project.control_price_type)
    our_price = float(project.our_price) if project.our_price else 0
    data["our_price_display"] = _format_price(our_price, control_type)

    display = _enrich_winning_display(
        project.is_won, control_type, our_price,
        project.winning_price, project.winning_amount,
        project.control_price_upper, project.budget_amount,
    )
    data["winning_price_display"] = display["winning_price_display"]
    data["winning_amount_display"] = display["winning_amount_display"]

    # parent_project_name
    data["parent_project_name"] = parent_map.get(project.parent_project_id) if project.parent_project_id else None

    # parent_is_multi_lot
    if parent_map_meta and project.parent_project_id:
        data["parent_is_multi_lot"] = parent_map_meta.get(project.parent_project_id, False)
    else:
        data["parent_is_multi_lot"] = False

    # deposit_status_display
    if not project.has_deposit:
        data["deposit_status_display"] = "无"
    elif project.status in (ProjectStatus.submitted, ProjectStatus.won, ProjectStatus.lost, ProjectStatus.failed_bid):
        if project.result_deposit_status:
            data["deposit_status_display"] = project.result_deposit_status.value
        else:
            data["deposit_status_display"] = "无"
    else:
        data["deposit_status_display"] = project.deposit_status.value if project.deposit_status else "无"

    # is_registered: 虚拟字段，从 status 推导
    data["is_registered"] = (project.status == ProjectStatus.registered)

    return data


def enrich_project(project: ProjectInfo, db: Session) -> dict:
    """单项目富化（用于详情页等单条查询场景）"""
    data = ProjectResponse.model_validate(project).model_dump()

    # 收集此项目需要的所有 ID
    org_ids = set()
    manager_ids = set()
    platform_ids = set()
    user_ids = set()
    parent_ids = set()

    if project.bidding_unit_id:
        org_ids.add(project.bidding_unit_id)
    if project.agency_id:
        org_ids.add(project.agency_id)
    if project.publish_platform_id:
        platform_ids.add(project.publish_platform_id)
    if project.bid_specialist_id:
        user_ids.add(project.bid_specialist_id)
    if project.winning_org_id:
        org_ids.add(project.winning_org_id)
    if project.parent_project_id:
        parent_ids.add(project.parent_project_id)
    for mid in _parse_json_list(project.manager_ids):
        manager_ids.add(mid)
    for pid in _parse_json_list(project.partner_ids):
        org_ids.add(pid)
    for wid in _parse_json_list(project.winning_org_ids):
        org_ids.add(wid)
    for c in _parse_json_list(data.get("competitors", [])):
        if isinstance(c, dict):
            for oid in c.get("org_ids", []):
                org_ids.add(oid)
            if "org_id" in c and c["org_id"]:
                org_ids.add(c["org_id"])

    # 批量查询（最多 5 次查询）
    org_map = {}
    if org_ids:
        for o in db.query(Organization).filter(Organization.id.in_(org_ids)).all():
            org_map[o.id] = {"name": o.name}

    manager_map = {}
    if manager_ids:
        for m in db.query(Manager).filter(Manager.id.in_(manager_ids)).all():
            manager_map[m.id] = m.name

    platform_map = {}
    if platform_ids:
        for p in db.query(Platform).filter(Platform.id.in_(platform_ids)).all():
            platform_map[p.id] = p.name

    user_map = {}
    if user_ids:
        for u in db.query(User).filter(User.id.in_(user_ids)).all():
            user_map[u.id] = u.display_name

    parent_map = {}
    parent_map_meta = {}
    if parent_ids:
        for pp in db.query(ProjectInfo).filter(ProjectInfo.id.in_(parent_ids)).all():
            parent_map[pp.id] = pp.project_name
            parent_map_meta[pp.id] = pp.is_multi_lot

    return _enrich_project_with_maps(project, org_map, manager_map, platform_map, user_map, parent_map, parent_map_meta)


def enrich_project_list(projects: list, db: Session) -> list:
    """批量富化项目列表（用于列表页，5 次查询替代 N×9 次）"""
    # 第一轮：收集所有需要的 ID
    org_ids = set()
    manager_ids = set()
    platform_ids = set()
    user_ids = set()
    parent_ids = set()

    for p in projects:
        if p.bidding_unit_id:
            org_ids.add(p.bidding_unit_id)
        if p.agency_id:
            org_ids.add(p.agency_id)
        if p.publish_platform_id:
            platform_ids.add(p.publish_platform_id)
        if p.bid_specialist_id:
            user_ids.add(p.bid_specialist_id)
        if p.winning_org_id:
            org_ids.add(p.winning_org_id)
        if p.parent_project_id:
            parent_ids.add(p.parent_project_id)
        for mid in _parse_json_list(p.manager_ids):
            manager_ids.add(mid)
        for pid in _parse_json_list(p.partner_ids):
            org_ids.add(pid)
        for wid in _parse_json_list(p.winning_org_ids):
            org_ids.add(wid)
        for c in _parse_json_list(p.competitors):
            if isinstance(c, dict):
                for oid in c.get("org_ids", []):
                    org_ids.add(oid)
                if "org_id" in c and c["org_id"]:
                    org_ids.add(c["org_id"])

    # 第二轮：5 次批量查询
    org_map = {}
    if org_ids:
        for o in db.query(Organization).filter(Organization.id.in_(org_ids)).all():
            org_map[o.id] = {"name": o.name}

    manager_map = {}
    if manager_ids:
        for m in db.query(Manager).filter(Manager.id.in_(manager_ids)).all():
            manager_map[m.id] = m.name

    platform_map = {}
    if platform_ids:
        for p in db.query(Platform).filter(Platform.id.in_(platform_ids)).all():
            platform_map[p.id] = p.name

    user_map = {}
    if user_ids:
        for u in db.query(User).filter(User.id.in_(user_ids)).all():
            user_map[u.id] = u.display_name

    parent_map = {}
    parent_map_meta = {}
    if parent_ids:
        for pp in db.query(ProjectInfo).filter(ProjectInfo.id.in_(parent_ids)).all():
            parent_map[pp.id] = pp.project_name
            parent_map_meta[pp.id] = pp.is_multi_lot

    # 第三轮：组装结果
    return [_enrich_project_with_maps(p, org_map, manager_map, platform_map, user_map, parent_map, parent_map_meta) for p in projects]


# ---- JSON list fields that need serialization ----

_JSON_LIST_FIELDS = {"manager_ids", "tags", "bid_documents", "partner_ids", "bid_files", "competitors", "scoring_details", "winning_org_ids"}


# ---- Endpoints ----

@router.get("", response_model=dict)
def list_projects(
    keyword: str = Query("", description="搜索关键词"),
    keyword_match: str = Query("fuzzy", description="关键词匹配方式: fuzzy/exact"),
    status: str = Query("", description="项目状态"),
    bidding_type: str = Query("", description="招标类型"),
    region: str = Query("", description="地区"),
    is_prequalification: Optional[bool] = Query(None, description="是否入围标"),
    is_multi_lot: Optional[bool] = Query(None, description="是否多标段"),
    manager_id: Optional[int] = Query(None, description="负责人ID"),
    bidding_unit_id: Optional[int] = Query(None, description="招标单位ID"),
    agency_id: Optional[int] = Query(None, description="代理单位ID"),
    publish_platform_id: Optional[int] = Query(None, description="发布平台ID"),
    partner_id: Optional[int] = Query(None, description="合作单位ID"),
    bid_method: str = Query("", description="投标方式"),
    is_won: Optional[bool] = Query(None, description="是否中标"),
    created_after: str = Query("", description="创建时间起始"),
    created_before: str = Query("", description="创建时间结束"),
    bid_deadline_after: str = Query("", description="开标时间起始"),
    bid_deadline_before: str = Query("", description="开标时间结束"),
    budget_min: Optional[float] = Query(None, description="预算金额最小值"),
    budget_max: Optional[float] = Query(None, description="预算金额最大值"),
    winning_amount_min: Optional[float] = Query(None, description="中标金额最小值"),
    winning_amount_max: Optional[float] = Query(None, description="中标金额最大值"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = db.query(ProjectInfo)

    # 关键词匹配
    if keyword:
        if keyword_match == "exact":
            query = query.filter(ProjectInfo.project_name == keyword)
        else:
            query = query.filter(ProjectInfo.project_name.contains(keyword))
    # 状态
    if status:
        try:
            status_enum = ProjectStatus(status)
        except ValueError:
            status_enum = None
        if status_enum:
            query = query.filter(ProjectInfo.status == status_enum)
    # 招标类型
    if bidding_type:
        query = query.filter(ProjectInfo.bidding_type == bidding_type)
    # 地区
    if region:
        query = query.filter(ProjectInfo.region.contains(region))
    # 是否入围标
    if is_prequalification is not None:
        query = query.filter(ProjectInfo.is_prequalification == is_prequalification)
    # 是否多标段
    if is_multi_lot is not None:
        query = query.filter(ProjectInfo.is_multi_lot == is_multi_lot)
    # 负责人（JSON 数组包含）
    if manager_id:
        query = query.filter(text(
            "EXISTS (SELECT 1 FROM json_each(project_infos.manager_ids) WHERE json_each.value = :mid)"
        )).params(mid=manager_id)
    # 招标单位
    if bidding_unit_id:
        query = query.filter(ProjectInfo.bidding_unit_id == bidding_unit_id)
    # 代理单位
    if agency_id:
        query = query.filter(ProjectInfo.agency_id == agency_id)
    # 发布平台
    if publish_platform_id:
        query = query.filter(ProjectInfo.publish_platform_id == publish_platform_id)
    # 合作单位（JSON 数组包含）
    if partner_id:
        query = query.filter(text(
            "EXISTS (SELECT 1 FROM json_each(project_infos.partner_ids) WHERE json_each.value = :pid)"
        )).params(pid=partner_id)
    # 投标方式
    if bid_method:
        query = query.filter(ProjectInfo.bid_method == bid_method)
    # 中标结果
    if is_won is not None:
        query = query.filter(ProjectInfo.is_won == is_won)
    # 创建时间范围
    if created_after:
        query = query.filter(ProjectInfo.created_at >= created_after)
    if created_before:
        end = datetime.strptime(created_before, "%Y-%m-%d") + timedelta(days=1)
        query = query.filter(ProjectInfo.created_at < end)
    # 开标时间范围
    if bid_deadline_after:
        query = query.filter(ProjectInfo.bid_deadline >= bid_deadline_after)
    if bid_deadline_before:
        query = query.filter(ProjectInfo.bid_deadline <= bid_deadline_before)
    # 预算金额范围
    if budget_min is not None:
        query = query.filter(ProjectInfo.budget_amount >= budget_min)
    if budget_max is not None:
        query = query.filter(ProjectInfo.budget_amount <= budget_max)
    # 中标金额范围
    if winning_amount_min is not None:
        query = query.filter(ProjectInfo.winning_amount >= winning_amount_min)
    if winning_amount_max is not None:
        query = query.filter(ProjectInfo.winning_amount <= winning_amount_max)

    total = query.count()
    items = (
        query.order_by(ProjectInfo.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    enriched = enrich_project_list(items, db)
    return {
        "items": enriched,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("", response_model=dict)
def create_project(
    data: ProjectCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    # ---- 多标段校验 ----
    project_name = data.project_name
    if data.parent_project_id:
        parent = db.query(ProjectInfo).filter(ProjectInfo.id == data.parent_project_id).first()
        if not parent:
            raise HTTPException(status_code=404, detail="父项目不存在")
        # 子标段不能也是多标段
        if parent.is_multi_lot and data.is_multi_lot:
            raise HTTPException(status_code=400, detail="子标段不能也是多标段父项目")
        # 多标段子标段不能设为入围分项
        if parent.is_multi_lot and data.bidding_type == "入围分项":
            raise HTTPException(status_code=400, detail="多标段子标段不能设置为入围分项类型")
        # 子标段继承父项目名称（如果未指定）
        if parent.is_multi_lot and not project_name:
            project_name = parent.project_name

    # 互斥约束
    if data.is_multi_lot and data.bidding_type == "入围分项":
        raise HTTPException(status_code=400, detail="多标段项目不能设置为入围分项类型")

    project = ProjectInfo(
        bidding_type=data.bidding_type,
        project_name=project_name,
        bidding_unit_id=data.bidding_unit_id,
        region=data.region,
        manager_ids=json.dumps(data.manager_ids, ensure_ascii=False) if data.manager_ids else [],
        status=ProjectStatus.following,
        description=data.description,
        parent_project_id=data.parent_project_id,
        is_multi_lot=bool(data.is_multi_lot),
        created_by=current_user.id,
    )
    db.add(project)
    db.flush()
    log_operation(db, current_user.id, "create", "project", project.id, f"创建项目: {project.project_name}")
    db.commit()
    db.refresh(project)
    return enrich_project(project, db)


@router.get("/{project_id}", response_model=dict)
def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    project = db.query(ProjectInfo).filter(ProjectInfo.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    return enrich_project(project, db)


@router.put("/{project_id}", response_model=dict)
def update_project(
    project_id: int,
    data: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    project = db.query(ProjectInfo).filter(ProjectInfo.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    update_data = data.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="没有需要更新的字段")

    # 互斥约束
    new_is_multi_lot = update_data.get("is_multi_lot", project.is_multi_lot)
    new_is_prequal = update_data.get("is_prequalification", project.is_prequalification)
    if new_is_multi_lot and new_is_prequal:
        raise HTTPException(status_code=400, detail="多标段项目不能同时作为入围标")

    # 多标段父项目：禁止手动修改 status（由 auto-recalc 接管）
    orig_status = project.status
    if project.is_multi_lot and "status" in update_data:
        del update_data["status"]

    for field, value in update_data.items():
        if field == "is_registered":
            continue  # 虚拟字段，不写入 DB
        if field in _JSON_LIST_FIELDS and isinstance(value, list):
            value = json.dumps(value, ensure_ascii=False)
        setattr(project, field, value)

    # ---- 报名状态推导（已发公告/未报名/已报名之间） ----
    if project.status in (ProjectStatus.published, ProjectStatus.not_registered, ProjectStatus.registered):
        if "registration_deadline" in update_data or "is_registered" in update_data:
            is_registered = update_data.get("is_registered", project.status == ProjectStatus.registered)
            has_deadline = bool(project.registration_deadline) or bool(update_data.get("registration_deadline"))
            if has_deadline and is_registered:
                project.status = ProjectStatus.registered
            elif has_deadline:
                project.status = ProjectStatus.not_registered
            else:
                project.status = ProjectStatus.published

    # ---- 投标结果状态推导（is_won / is_bid_failed → 已中标/未中标/已流标） ----
    result_statuses = (ProjectStatus.submitted, ProjectStatus.won, ProjectStatus.lost, ProjectStatus.failed_bid)
    if project.status in result_statuses and ("is_won" in update_data or "is_bid_failed" in update_data):
        if project.is_bid_failed:
            # 流标：强制 is_won=false，状态→已流标
            project.is_won = False
            project.status = ProjectStatus.failed_bid
        elif project.is_won:
            # 已中标：推导 winning 信息
            control_type = _control_type_str(project.control_price_type)
            is_shortlisting = project.is_prequalification
            raw_comps = project.competitors
            if isinstance(raw_comps, str):
                try:
                    raw_comps = json.loads(raw_comps)
                except (json.JSONDecodeError, TypeError):
                    raw_comps = []

            winning_entries = [c for c in raw_comps if isinstance(c, dict) and c.get("is_winning")]

            if not winning_entries:
                # 无中标勾选 → 回退已投标
                project.status = ProjectStatus.submitted
                project.winning_org_ids = json.dumps([], ensure_ascii=False)
                project.winning_org_id = None
            else:
                derived_org_ids = []
                for entry in winning_entries:
                    org_ids = entry.get("org_ids", [])
                    if not org_ids and entry.get("org_id"):
                        org_ids = [entry["org_id"]]
                    derived_org_ids.extend(org_ids)

                if derived_org_ids:
                    seen = set()
                    unique_ids = [oid for oid in derived_org_ids if oid not in seen and not seen.add(oid)]
                    project.winning_org_ids = json.dumps(unique_ids, ensure_ascii=False)
                    project.winning_org_id = unique_ids[0] if unique_ids else None
                else:
                    project.winning_org_ids = json.dumps([], ensure_ascii=False)
                    project.winning_org_id = None

                if is_shortlisting:
                    project.status = ProjectStatus.won
                else:
                    wp = winning_entries[0].get("price", 0)
                    if wp:
                        if control_type == "金额":
                            project.winning_price = None
                            project.winning_amount = wp
                        else:
                            project.winning_price = wp
                            project.winning_amount = _calc_winning_amount(
                                wp, control_type, project.control_price_upper, project.budget_amount
                            )
                    project.status = ProjectStatus.won
        elif not project.is_won:
            # 未中标（is_won=False 且 is_bid_failed=False）
            control_type = _control_type_str(project.control_price_type)
            is_shortlisting = project.is_prequalification
            raw_comps = project.competitors
            if isinstance(raw_comps, str):
                try:
                    raw_comps = json.loads(raw_comps)
                except (json.JSONDecodeError, TypeError):
                    raw_comps = []

            winning_entries = [c for c in raw_comps if isinstance(c, dict) and c.get("is_winning")]

            if not winning_entries:
                # 没有任何参标单位勾选中标 → 回退到已投标
                project.status = ProjectStatus.submitted
                project.winning_org_ids = json.dumps([], ensure_ascii=False)
                project.winning_org_id = None
            else:
                derived_org_ids = []
                for entry in winning_entries:
                    org_ids = entry.get("org_ids", [])
                    if not org_ids and entry.get("org_id"):
                        org_ids = [entry["org_id"]]
                    derived_org_ids.extend(org_ids)

                if derived_org_ids:
                    seen = set()
                    unique_ids = [oid for oid in derived_org_ids if oid not in seen and not seen.add(oid)]
                    project.winning_org_ids = json.dumps(unique_ids, ensure_ascii=False)
                    project.winning_org_id = unique_ids[0] if unique_ids else None
                else:
                    project.winning_org_ids = json.dumps([], ensure_ascii=False)
                    project.winning_org_id = None

                if not is_shortlisting and winning_entries:
                    wp = winning_entries[0].get("price", 0)
                    if wp:
                        if control_type == "金额":
                            project.winning_price = None
                            project.winning_amount = wp
                        else:
                            project.winning_price = wp
                            project.winning_amount = _calc_winning_amount(
                                wp, control_type, project.control_price_upper, project.budget_amount
                            )
                project.status = ProjectStatus.lost

    log_operation(db, current_user.id, "update", "project", project.id, f"更新项目: {project.project_name}")
    db.commit()
    db.refresh(project)

    # 多标段子标段：状态变更后触发父项目重算
    if project.parent_project_id and project.status != orig_status:
        recalc_multi_lot_parent_status(project.parent_project_id, db)

    return enrich_project(project, db)


@router.delete("/{project_id}")
def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    project = db.query(ProjectInfo).filter(ProjectInfo.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    # 多标段父项目：级联删除所有子标段
    if project.is_multi_lot:
        children = db.query(ProjectInfo).filter(
            ProjectInfo.parent_project_id == project_id
        ).all()
        for child in children:
            log_operation(db, current_user.id, "delete", "project", child.id,
                          f"级联删除子标段: {child.project_name} (父项目ID={project_id})")
            db.delete(child)
        if children:
            db.flush()

    log_operation(db, current_user.id, "delete", "project", project.id, f"删除项目: {project.project_name}")
    db.delete(project)
    db.commit()
    return {"message": "删除成功"}


@router.post("/{project_id}/sync-competitors", response_model=dict)
def sync_competitors(
    project_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """从父入围标项目同步参标单位到当前入围分项项目"""
    project = db.query(ProjectInfo).filter(ProjectInfo.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    if not project.parent_project_id:
        raise HTTPException(status_code=400, detail="该项目未关联父入围标项目")

    parent = db.query(ProjectInfo).filter(ProjectInfo.id == project.parent_project_id).first()
    if not parent:
        raise HTTPException(status_code=404, detail="父入围标项目不存在")

    # 复制父项目的 competitors（清理 is_winning 标志，保留 org_ids/price/score 结构）
    raw_comps = parent.competitors
    if isinstance(raw_comps, str):
        try:
            raw_comps = json.loads(raw_comps)
        except (json.JSONDecodeError, TypeError):
            raw_comps = []

    synced = []
    for c in raw_comps:
        if not isinstance(c, dict):
            continue
        entry = {
            "org_ids": c.get("org_ids", []),
            "price": 0,  # 重置报价，入围分项的报价独立
            "score": 0,
            "is_shortlisted": False,
            "is_winning": False,
        }
        synced.append(entry)

    project.competitors = json.dumps(synced, ensure_ascii=False)
    log_operation(db, current_user.id, "update", "project", project.id,
                  f"从父项目(ID={parent.id})同步参标单位")
    db.commit()
    db.refresh(project)
    return enrich_project(project, db)


@router.get("/{project_id}/lots", response_model=dict)
def list_project_lots(
    project_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """获取多标段父项目的所有子标段"""
    parent = db.query(ProjectInfo).filter(ProjectInfo.id == project_id).first()
    if not parent:
        raise HTTPException(status_code=404, detail="项目不存在")
    if not parent.is_multi_lot:
        raise HTTPException(status_code=400, detail="该项目不是多标段父项目")

    lots = db.query(ProjectInfo).filter(
        ProjectInfo.parent_project_id == project_id
    ).order_by(ProjectInfo.id).all()

    return {"items": enrich_project_list(lots, db), "total": len(lots)}


# ---- Flow endpoints (status changes only, no record creation) ----

@router.post("/{project_id}/publish", response_model=dict)
def publish_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    project = db.query(ProjectInfo).filter(ProjectInfo.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    if project.is_multi_lot:
        raise HTTPException(status_code=400, detail="多标段父项目不参与投标流程，请在子标段中操作")
    if project.status != ProjectStatus.following:
        raise HTTPException(status_code=400, detail="只有跟进中的项目才能发布公告")

    project.status = ProjectStatus.published
    log_operation(db, current_user.id, "advance", "project", project.id, f"发布招标公告: {project.project_name}")
    db.commit()
    # 子标段状态变更后重算父项目
    if project.parent_project_id:
        recalc_multi_lot_parent_status(project.parent_project_id, db)
    return {"message": "发布成功"}


@router.post("/{project_id}/prepare", response_model=dict)
def prepare_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    project = db.query(ProjectInfo).filter(ProjectInfo.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    if project.is_multi_lot:
        raise HTTPException(status_code=400, detail="多标段父项目不参与投标流程，请在子标段中操作")
    if project.status not in (ProjectStatus.published, ProjectStatus.not_registered, ProjectStatus.registered):
        raise HTTPException(status_code=400, detail="只有已发公告/未报名/已报名的项目才能准备投标")

    project.status = ProjectStatus.preparing
    log_operation(db, current_user.id, "advance", "project", project.id, f"准备投标: {project.project_name}")
    db.commit()
    if project.parent_project_id:
        recalc_multi_lot_parent_status(project.parent_project_id, db)
    return {"message": "准备投标成功"}


@router.post("/{project_id}/submit", response_model=dict)
def submit_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    project = db.query(ProjectInfo).filter(ProjectInfo.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    if project.is_multi_lot:
        raise HTTPException(status_code=400, detail="多标段父项目不参与投标流程，请在子标段中操作")
    if project.status != ProjectStatus.preparing:
        raise HTTPException(status_code=400, detail="只有准备投标的项目才能提交投标")

    project.status = ProjectStatus.submitted

    # Deposit status transition: set result_deposit_status to 未收回
    if project.has_deposit and project.deposit_status == DepositStatus.paid:
        project.result_deposit_status = ResultDepositStatus.not_returned

    log_operation(db, current_user.id, "advance", "project", project.id, f"提交投标: {project.project_name}")
    db.commit()
    if project.parent_project_id:
        recalc_multi_lot_parent_status(project.parent_project_id, db)
    return {"message": "提交投标成功"}


@router.post("/{project_id}/abandon", response_model=dict)
def abandon_project(
    project_id: int,
    body: dict = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    project = db.query(ProjectInfo).filter(ProjectInfo.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    if project.is_multi_lot:
        raise HTTPException(status_code=400, detail="多标段父项目不参与投标流程，请在子标段中操作")
    if project.status == ProjectStatus.abandoned:
        raise HTTPException(status_code=400, detail="项目已放弃")

    project.status = ProjectStatus.abandoned
    if body and "reason" in body:
        project.abandon_reason = body["reason"]

    reason = body.get("reason", "") if body else ""
    log_operation(db, current_user.id, "abandon", "project", project.id, f"放弃项目: {project.project_name}, 原因: {reason}")
    db.commit()
    if project.parent_project_id:
        recalc_multi_lot_parent_status(project.parent_project_id, db)
    return {"message": "已放弃该项目"}
