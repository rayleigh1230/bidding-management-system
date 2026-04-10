import json
from fastapi import APIRouter, Depends, HTTPException, Query
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

def enrich_project(project: ProjectInfo, db: Session) -> dict:
    """填充所有 enrich 字段：关联名称 + 价格计算显示"""
    data = ProjectResponse.model_validate(project).model_dump()

    # bidding_unit_name
    if project.bidding_unit_id:
        org = db.query(Organization).filter(Organization.id == project.bidding_unit_id).first()
        data["bidding_unit_name"] = org.name if org else None
    else:
        data["bidding_unit_name"] = None

    # manager_names
    manager_ids = project.manager_ids if project.manager_ids else []
    if isinstance(manager_ids, str):
        try:
            manager_ids = json.loads(manager_ids)
        except (json.JSONDecodeError, TypeError):
            manager_ids = []
    if manager_ids:
        managers = db.query(Manager).filter(Manager.id.in_(manager_ids)).all()
        manager_map = {m.id: m.name for m in managers}
        data["manager_names"] = [manager_map.get(mid) for mid in manager_ids if mid in manager_map]
    else:
        data["manager_names"] = []

    # agency_name
    if project.agency_id:
        org = db.query(Organization).filter(Organization.id == project.agency_id).first()
        data["agency_name"] = org.name if org else None
    else:
        data["agency_name"] = None

    # platform_name
    if project.publish_platform_id:
        platform = db.query(Platform).filter(Platform.id == project.publish_platform_id).first()
        data["platform_name"] = platform.name if platform else None
    else:
        data["platform_name"] = None

    # specialist_name
    if project.bid_specialist_id:
        specialist = db.query(User).filter(User.id == project.bid_specialist_id).first()
        data["specialist_name"] = specialist.display_name if specialist else None
    else:
        data["specialist_name"] = None

    # partner_names
    partner_ids = project.partner_ids if project.partner_ids else []
    if isinstance(partner_ids, str):
        try:
            partner_ids = json.loads(partner_ids)
        except (json.JSONDecodeError, TypeError):
            partner_ids = []
    if partner_ids:
        partners = db.query(Organization).filter(Organization.id.in_(partner_ids)).all()
        partner_map = {p.id: p.name for p in partners}
        data["partner_names"] = [partner_map.get(pid) for pid in partner_ids if pid in partner_map]
    else:
        data["partner_names"] = []

    # winning_org_name (backward compat)
    if project.winning_org_id:
        winning_org = db.query(Organization).filter(Organization.id == project.winning_org_id).first()
        data["winning_org_name"] = winning_org.name if winning_org else None
    else:
        data["winning_org_name"] = None

    # winning_org_names (multi)
    winning_ids = project.winning_org_ids or []
    if isinstance(winning_ids, str):
        try:
            winning_ids = json.loads(winning_ids)
        except (json.JSONDecodeError, TypeError):
            winning_ids = []
    if winning_ids:
        win_orgs = db.query(Organization).filter(Organization.id.in_(winning_ids)).all()
        win_map = {o.id: o.name for o in win_orgs}
        data["winning_org_names"] = [win_map.get(oid) for oid in winning_ids if oid in win_map]
        # backward compat: set winning_org_name from first entry
        if not data["winning_org_name"] and winning_ids:
            first = db.query(Organization).filter(Organization.id == winning_ids[0]).first()
            data["winning_org_name"] = first.name if first else None
    else:
        data["winning_org_names"] = []

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

    # deposit_status_display: 根据状态显示不同阶段的保证金状态
    if not project.has_deposit:
        data["deposit_status_display"] = "无"
    elif project.status in (ProjectStatus.submitted, ProjectStatus.won, ProjectStatus.lost):
        # 已投标及之后：显示收回状态
        if project.result_deposit_status:
            data["deposit_status_display"] = project.result_deposit_status.value
        else:
            data["deposit_status_display"] = "无"
    else:
        # 准备投标及之前：显示缴纳状态
        data["deposit_status_display"] = project.deposit_status.value if project.deposit_status else "无"

    return data


# ---- JSON list fields that need serialization ----

_JSON_LIST_FIELDS = {"manager_ids", "tags", "bid_documents", "partner_ids", "bid_files", "competitors", "scoring_details", "winning_org_ids"}


# ---- Endpoints ----

@router.get("", response_model=dict)
def list_projects(
    keyword: str = Query("", description="搜索关键词"),
    status: str = Query("", description="项目状态"),
    bidding_type: str = Query("", description="招标类型"),
    region: str = Query("", description="地区"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = db.query(ProjectInfo)

    if keyword:
        query = query.filter(ProjectInfo.project_name.contains(keyword))
    if status:
        try:
            status_enum = ProjectStatus(status)
        except ValueError:
            status_enum = None
        if status_enum:
            query = query.filter(ProjectInfo.status == status_enum)
    if bidding_type:
        query = query.filter(ProjectInfo.bidding_type == bidding_type)
    if region:
        query = query.filter(ProjectInfo.region.contains(region))

    total = query.count()
    items = (
        query.order_by(ProjectInfo.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    enriched = [enrich_project(item, db) for item in items]
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
    project = ProjectInfo(
        bidding_type=data.bidding_type,
        project_name=data.project_name,
        bidding_unit_id=data.bidding_unit_id,
        region=data.region,
        manager_ids=json.dumps(data.manager_ids, ensure_ascii=False) if data.manager_ids else [],
        status=ProjectStatus.following,
        description=data.description,
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

    for field, value in update_data.items():
        if field in _JSON_LIST_FIELDS and isinstance(value, list):
            value = json.dumps(value, ensure_ascii=False)
        setattr(project, field, value)

    # Auto-calculate winning_price / winning_amount when is_won changes
    # Only when project is in "已投标" status
    if "is_won" in update_data and project.status == ProjectStatus.submitted:
        control_type = _control_type_str(project.control_price_type)
        our_price = float(project.our_price) if project.our_price else 0
        is_shortlisting = project.is_prequalification  # 入围标

        if project.is_won:
            if is_shortlisting:
                # 入围标：不自动计算，保持前端传入的手动值
                project.status = ProjectStatus.won
            else:
                # 非入围标：自动计算 winning_price / winning_amount
                if control_type == "金额":
                    project.winning_price = None
                    project.winning_amount = our_price if our_price else None
                elif control_type in ("折扣率", "下浮率"):
                    project.winning_price = our_price if our_price else None
                    project.winning_amount = _calc_winning_amount(
                        our_price, control_type, project.control_price_upper, project.budget_amount
                    )
                project.status = ProjectStatus.won
        else:
            if is_shortlisting:
                # 入围标未中标：不自动计算
                project.status = ProjectStatus.lost
            else:
                # 非入围标：自动计算 winning_amount
                if control_type == "金额":
                    project.winning_price = None
                elif control_type in ("折扣率", "下浮率"):
                    project.winning_amount = _calc_winning_amount(
                        project.winning_price, control_type, project.control_price_upper, project.budget_amount
                    )
                project.status = ProjectStatus.lost

    log_operation(db, current_user.id, "update", "project", project.id, f"更新项目: {project.project_name}")
    db.commit()
    db.refresh(project)
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

    log_operation(db, current_user.id, "delete", "project", project.id, f"删除项目: {project.project_name}")
    db.delete(project)
    db.commit()
    return {"message": "删除成功"}


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
    if project.status != ProjectStatus.following:
        raise HTTPException(status_code=400, detail="只有跟进中的项目才能发布公告")

    project.status = ProjectStatus.published
    log_operation(db, current_user.id, "advance", "project", project.id, f"发布招标公告: {project.project_name}")
    db.commit()
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
    if project.status != ProjectStatus.published:
        raise HTTPException(status_code=400, detail="只有已发公告的项目才能准备投标")

    project.status = ProjectStatus.preparing
    log_operation(db, current_user.id, "advance", "project", project.id, f"准备投标: {project.project_name}")
    db.commit()
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
    if project.status != ProjectStatus.preparing:
        raise HTTPException(status_code=400, detail="只有准备投标的项目才能提交投标")

    project.status = ProjectStatus.submitted

    # Deposit status transition: set result_deposit_status to 未收回
    if project.has_deposit and project.deposit_status == DepositStatus.paid:
        project.result_deposit_status = ResultDepositStatus.not_returned

    log_operation(db, current_user.id, "advance", "project", project.id, f"提交投标: {project.project_name}")
    db.commit()
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
    if project.status == ProjectStatus.abandoned:
        raise HTTPException(status_code=400, detail="项目已放弃")

    project.status = ProjectStatus.abandoned
    if body and "reason" in body:
        project.abandon_reason = body["reason"]

    reason = body.get("reason", "") if body else ""
    log_operation(db, current_user.id, "abandon", "project", project.id, f"放弃项目: {project.project_name}, 原因: {reason}")
    db.commit()
    return {"message": "已放弃该项目"}
