"""招标文件上传 + 解析 API。

POST   /api/documents/parse?project_id=N   上传并解析招标文件
GET    /api/documents/{project_id}/files    读取已保存的文件列表
DELETE /api/documents/{project_id}/files/{index}  删除一条文件记录（含本地文件）
"""
import json
import os
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..core.config import settings, BASE_DIR
from ..core.database import get_db
from ..core.security import get_current_user
from ..models.organization import Organization
from ..models.platform import Platform
from ..models.project import ProjectInfo
from ..schemas.dict import OrganizationCreate, PlatformCreate
from ..services.document_parser import DocumentParseError, get_parser
from ..services.logger import log_operation
from .organizations import create_organization as _create_org
from .platforms import create_platform as _create_platform

router = APIRouter(prefix="/api/documents", tags=["文档解析"])

# 不参与自动匹配创建的招标类型
ALLOWED_BIDDING_TYPES = {"公开招标", "邀请招标", "中介超市"}
ALLOWED_CONTROL_TYPES = {"金额", "折扣率", "下浮率"}


def _save_upload(file: UploadFile, project_id: int) -> dict:
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"不支持的文件格式: {ext or '(无后缀)'}。"
                "支持 PDF/DOCX/TXT/JPG/PNG；旧版 .doc 请另存为 PDF 后重试。"
            ),
        )
    contents = file.file.read()
    if len(contents) > settings.UPLOAD_MAX_SIZE:
        raise HTTPException(status_code=400, detail="文件超过 20MB 限制")

    subdir = os.path.join(settings.UPLOAD_DIR, str(project_id))
    os.makedirs(subdir, exist_ok=True)
    stored_name = f"{project_id}_{int(datetime.now().timestamp())}_{uuid.uuid4().hex[:8]}{ext}"
    abs_path = os.path.join(subdir, stored_name)
    with open(abs_path, "wb") as f:
        f.write(contents)

    rel_path = f"uploads/{project_id}/{stored_name}"
    return {
        "filename": file.filename or stored_name,
        "stored_path": rel_path,
        "size": len(contents),
        "uploaded_at": datetime.now().isoformat(timespec="seconds"),
    }


def _match_or_create_org(
    name: str, db: Session, current_user
) -> tuple[int | None, str | None]:
    """返回 (org_id, matched_name)。无输入返回 (None, None)。"""
    name = (name or "").strip()
    if not name:
        return None, None
    existing = (
        db.query(Organization)
        .filter(
            or_(
                Organization.name == name,
                Organization.name.contains(name),
                Organization.short_name.contains(name),
            )
        )
        .first()
    )
    if existing:
        return existing.id, existing.name
    # 先查重避免触发 create_organization 内置的 400
    dup = db.query(Organization).filter(Organization.name == name).first()
    if dup:
        return dup.id, dup.name
    new_org = _create_org(
        OrganizationCreate(name=name, org_type="external"),
        db=db,
        current_user=current_user,
    )
    return new_org.id, new_org.name


def _match_or_create_platform(
    name: str, db: Session, current_user
) -> tuple[int | None, str | None]:
    name = (name or "").strip()
    if not name:
        return None, None
    existing = (
        db.query(Platform)
        .filter(or_(Platform.name == name, Platform.name.contains(name)))
        .first()
    )
    if existing:
        return existing.id, existing.name
    dup = db.query(Platform).filter(Platform.name == name).first()
    if dup:
        return dup.id, dup.name
    new_pf = _create_platform(PlatformCreate(name=name), db=db, current_user=current_user)
    return new_pf.id, new_pf.name


def _to_float(value):
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_date(value):
    if not value or not isinstance(value, str):
        return None
    s = value.strip()
    # 兼容 "2026年7月1日" → "2026-07-01"
    if "年" in s:
        m = (
            s.replace("年", "-")
            .replace("月", "-")
            .replace("日", "")
            .strip()
        )
        s = m
    try:
        return datetime.strptime(s[:10], "%Y-%m-%d").strftime("%Y-%m-%d")
    except ValueError:
        return None


@router.post("/parse", response_model=dict)
async def parse_document(
    project_id: int = Query(..., description="目标项目 ID"),
    parse_type: str = Query("bidding", description="解析类型: bidding=招标信息, result=中标结果"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """上传文件 → 调用 Qwen-Long 解析 → 字段回传给前端表单。

    parse_type="bidding": 招标公告，回填招标信息字段
    parse_type="result": 中标公告/中标结果，回填候选人 + 合同字段 + 自动推导 is_won

    file 对象不入库；前端把 file 追加到本地列表（bid_documents / result_documents），
    用户点保存时随其他字段一起 PUT 进库。
    """
    project = db.query(ProjectInfo).filter(ProjectInfo.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    file_meta = _save_upload(file, project_id)
    abs_path = os.path.join(BASE_DIR, file_meta["stored_path"])

    try:
        parser = get_parser()
        file_id = parser.upload_file(abs_path)
        if parse_type == "result":
            parsed = parser.parse(file_id, parse_type="result", control_price_type=project.control_price_type)
        else:
            parsed = parser.parse(file_id)
    except DocumentParseError as e:
        raise HTTPException(
            status_code=502, detail=f"解析失败: {e} (code={e.code})"
        ) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"解析服务异常: {e}") from e

    if parse_type == "result":
        return _build_result_response(project_id, file_meta, parsed, db, current_user)

    return _build_bidding_response(project_id, file_meta, parsed, db, current_user)


def _build_bidding_response(
    project_id: int, file_meta: dict, parsed: dict, db: Session, current_user
) -> dict:
    bidding_unit_id, bidding_unit_name = _match_or_create_org(
        parsed.get("bidding_unit_name"), db, current_user
    )
    agency_id, agency_name = _match_or_create_org(
        parsed.get("agency_name"), db, current_user
    )
    platform_id, platform_name = _match_or_create_platform(
        parsed.get("publish_platform_name"), db, current_user
    )

    bidding_type_raw = parsed.get("bidding_type")
    bidding_type = bidding_type_raw if bidding_type_raw in ALLOWED_BIDDING_TYPES else None

    control_type_raw = parsed.get("control_price_type")
    control_type = control_type_raw if control_type_raw in ALLOWED_CONTROL_TYPES else None

    # 下浮率语义：上限=最小降价幅度（较小值），下限=最大降价幅度（较大值）
    # LLM 通常按 min/max 输出，这里做反转校正
    control_upper = _to_float(parsed.get("control_price_upper"))
    control_lower = _to_float(parsed.get("control_price_lower"))
    if control_type == "下浮率" and control_upper is not None and control_lower is not None and control_upper > control_lower:
        control_upper, control_lower = control_lower, control_upper

    is_prequal = parsed.get("is_prequalification")
    if isinstance(is_prequal, str):
        is_prequal = is_prequal.strip() in ("true", "True", "是", "1", "yes")
    elif not isinstance(is_prequal, bool):
        is_prequal = None

    fields = {
        "project_name": parsed.get("project_name"),
        "bidding_type": bidding_type,
        "region_text": parsed.get("region_text"),
        "bidding_unit_id": bidding_unit_id,
        "bidding_unit_name": bidding_unit_name or parsed.get("bidding_unit_name"),
        "agency_id": agency_id,
        "agency_name": agency_name or parsed.get("agency_name"),
        "publish_platform_id": platform_id,
        "publish_platform_name": platform_name or parsed.get("publish_platform_name"),
        "registration_deadline": _to_date(parsed.get("registration_deadline")),
        "bid_deadline": _to_date(parsed.get("bid_deadline")),
        "budget_amount": _to_float(parsed.get("budget_amount")),
        "control_price_type": control_type,
        "control_price_upper": control_upper,
        "control_price_lower": control_lower,
        "is_prequalification": is_prequal,
        "tags": parsed.get("tags") or [],
        "bidding_notes": parsed.get("bidding_notes"),
    }

    return {
        "project_id": project_id,
        "file": file_meta,
        "fields": fields,
        "_debug": {
            "raw_control_price_type": parsed.get("control_price_type"),
            "raw_control_price_upper": parsed.get("control_price_upper"),
            "raw_control_price_lower": parsed.get("control_price_lower"),
            "final_control_type": control_type,
            "final_control_upper": control_upper,
            "final_control_lower": control_lower,
        },
    }


def _get_our_org_ids(db: Session) -> list[int]:
    """查询所有 org_type=ours 的组织 id（通常只有 1 个）。"""
    rows = (
        db.query(Organization)
        .filter(Organization.org_type == "ours")
        .all()
    )
    return [r.id for r in rows]


def _build_result_response(
    project_id: int, file_meta: dict, parsed: dict, db: Session, current_user
) -> dict:
    """构造中标结果解析响应。"""
    our_org_ids = set(_get_our_org_ids(db))
    raw_candidates = parsed.get("candidates") or []

    competitors: list[dict] = []
    any_winning_ours = False
    winning_org_ids: list[int] = []

    for cand in raw_candidates:
        names = cand.get("org_names") or []
        if isinstance(names, str):
            names = [names]
        org_ids: list[int] = []
        org_names_out: list[str] = []
        for nm in names:
            org_id, matched_name = _match_or_create_org(nm, db, current_user)
            if org_id:
                org_ids.append(org_id)
                org_names_out.append(matched_name or nm)

        is_winning = bool(cand.get("is_winning"))
        if is_winning:
            winning_org_ids.extend(org_ids)
            if any(oid in our_org_ids for oid in org_ids):
                any_winning_ours = True

        competitors.append({
            "org_ids": org_ids,
            "org_names": org_names_out,
            "price": _to_float(cand.get("price")) or 0,
            "score": _to_float(cand.get("score")) or 0,
            "rank": cand.get("rank"),
            "is_shortlisted": False,
            "is_winning": is_winning,
        })

    fields: dict = {
        "competitors": competitors,
        "is_won": any_winning_ours if competitors else None,
        "winning_org_ids": winning_org_ids if winning_org_ids else None,
        "contract_number": parsed.get("contract_number"),
        "contract_amount": _to_float(parsed.get("contract_amount")),
        "result_notes": parsed.get("result_notes"),
    }

    return {
        "project_id": project_id,
        "file": file_meta,
        "fields": fields,
    }


@router.get("/{project_id}/files", response_model=dict)
def list_documents(
    project_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    project = db.query(ProjectInfo).filter(ProjectInfo.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    raw = project.bid_documents or []
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            raw = []
    if not isinstance(raw, list):
        raw = []
    return {"items": raw, "total": len(raw)}


@router.delete("/{project_id}/files/{index}", response_model=dict)
def delete_document(
    project_id: int,
    index: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    project = db.query(ProjectInfo).filter(ProjectInfo.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    raw = project.bid_documents or []
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            raw = []
    if not isinstance(raw, list):
        raw = []
    if index < 0 or index >= len(raw):
        raise HTTPException(status_code=400, detail="文件索引越界")

    removed = raw.pop(index)
    project.bid_documents = json.dumps(raw, ensure_ascii=False)

    stored_path = removed.get("stored_path") if isinstance(removed, dict) else None
    if stored_path:
        abs_path = os.path.join(BASE_DIR, stored_path)
        if os.path.exists(abs_path):
            try:
                os.remove(abs_path)
            except OSError:
                pass

    filename = removed.get("filename", "") if isinstance(removed, dict) else ""
    log_operation(
        db,
        current_user.id,
        "delete",
        "project",
        project.id,
        f"删除招标文件: {filename}",
    )
    db.commit()
    return {"message": "删除成功"}


@router.get("/{project_id}/result-files", response_model=dict)
def list_result_documents(
    project_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    project = db.query(ProjectInfo).filter(ProjectInfo.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    raw = project.result_documents or []
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            raw = []
    if not isinstance(raw, list):
        raw = []
    return {"items": raw, "total": len(raw)}


@router.delete("/{project_id}/result-files/{index}", response_model=dict)
def delete_result_document(
    project_id: int,
    index: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    project = db.query(ProjectInfo).filter(ProjectInfo.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    raw = project.result_documents or []
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            raw = []
    if not isinstance(raw, list):
        raw = []
    if index < 0 or index >= len(raw):
        raise HTTPException(status_code=400, detail="文件索引越界")

    removed = raw.pop(index)
    project.result_documents = json.dumps(raw, ensure_ascii=False)

    stored_path = removed.get("stored_path") if isinstance(removed, dict) else None
    if stored_path:
        abs_path = os.path.join(BASE_DIR, stored_path)
        if os.path.exists(abs_path):
            try:
                os.remove(abs_path)
            except OSError:
                pass

    filename = removed.get("filename", "") if isinstance(removed, dict) else ""
    log_operation(
        db,
        current_user.id,
        "delete",
        "project",
        project.id,
        f"删除中标结果文件: {filename}",
    )
    db.commit()
    return {"message": "删除成功"}
