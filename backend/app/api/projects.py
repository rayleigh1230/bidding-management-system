import json
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_

from ..core.database import get_db
from ..core.security import get_current_user
from ..models.project import ProjectInfo, ProjectStatus
from ..models.bidding_info import BiddingInfo
from ..models.organization import Organization
from ..models.manager import Manager
from ..schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse
from ..services.logger import log_operation

router = APIRouter(prefix="/api/projects", tags=["项目管理"])


def enrich_project(project: ProjectInfo, db: Session) -> dict:
    """Enrich a project with bidding_unit_name and manager_names."""
    data = ProjectResponse.model_validate(project).model_dump()

    # Enrich bidding_unit_name
    if project.bidding_unit_id:
        org = db.query(Organization).filter(Organization.id == project.bidding_unit_id).first()
        data["bidding_unit_name"] = org.name if org else None
    else:
        data["bidding_unit_name"] = None

    # Enrich manager_names
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

    return data


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
        query = query.filter(ProjectInfo.status == status)
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
        if field == "manager_ids" and isinstance(value, list):
            value = json.dumps(value, ensure_ascii=False)
        setattr(project, field, value)

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

    # Check for linked BiddingInfo
    linked_bidding = db.query(BiddingInfo).filter(BiddingInfo.project_id == project_id).first()
    if linked_bidding:
        raise HTTPException(status_code=400, detail="该项目已关联招标信息，无法删除")

    log_operation(db, current_user.id, "delete", "project", project.id, f"删除项目: {project.project_name}")
    db.delete(project)
    db.commit()
    return {"message": "删除成功"}


@router.post("/{project_id}/publish", response_model=dict)
def publish_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    project = db.query(ProjectInfo).filter(ProjectInfo.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    # Check if BiddingInfo already exists for this project
    existing = db.query(BiddingInfo).filter(BiddingInfo.project_id == project_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="该项目已发布招标公告")

    # Create empty BiddingInfo
    bidding_info = BiddingInfo(project_id=project_id)
    db.add(bidding_info)

    # Update project status
    project.status = ProjectStatus.published

    log_operation(db, current_user.id, "advance", "project", project.id, f"发布招标公告，项目: {project.project_name}")
    db.commit()
    db.refresh(bidding_info)

    return {
        "message": "发布成功",
        "bidding_info_id": bidding_info.id,
    }


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

    project.status = ProjectStatus.abandoned
    if body and "reason" in body:
        project.abandon_reason = body["reason"]

    reason = body.get("reason", "") if body else ""
    log_operation(db, current_user.id, "abandon", "project", project.id, f"放弃项目: {project.project_name}, 原因: {reason}")
    db.commit()
    db.refresh(project)
    return {"message": "已放弃该项目"}
