from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_

from ..core.database import get_db
from ..models.organization import Organization
from ..schemas.dict import OrganizationCreate, OrganizationUpdate, OrganizationResponse
from ..core.security import get_current_user
from ..services.logger import log_operation

router = APIRouter(prefix="/api/organizations", tags=["机构管理"])


@router.get("", response_model=dict)
def list_organizations(
    keyword: str = Query("", description="搜索关键词"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = db.query(Organization)
    if keyword:
        query = query.filter(
            or_(
                Organization.name.contains(keyword),
                Organization.short_name.contains(keyword),
            )
        )
    total = query.count()
    items = (
        query.order_by(Organization.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {
        "items": [OrganizationResponse.model_validate(item) for item in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("", response_model=OrganizationResponse)
def create_organization(
    data: OrganizationCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    existing = db.query(Organization).filter(Organization.name == data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="机构名称已存在")
    org = Organization(**data.model_dump())
    db.add(org)
    db.flush()
    log_operation(db, current_user.id, "create", "organization", org.id, f"创建机构: {org.name}")
    db.commit()
    db.refresh(org)
    return org


@router.put("/{org_id}", response_model=OrganizationResponse)
def update_organization(
    org_id: int,
    data: OrganizationUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="机构不存在")
    update_data = data.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="没有需要更新的字段")
    if "name" in update_data and update_data["name"] != org.name:
        existing = (
            db.query(Organization).filter(Organization.name == update_data["name"]).first()
        )
        if existing:
            raise HTTPException(status_code=400, detail="机构名称已存在")
    for field, value in update_data.items():
        setattr(org, field, value)
    log_operation(db, current_user.id, "update", "organization", org.id, f"更新机构: {org.name}")
    db.commit()
    db.refresh(org)
    return org


@router.delete("/{org_id}")
def delete_organization(
    org_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="机构不存在")
    log_operation(db, current_user.id, "delete", "organization", org.id, f"删除机构: {org.name}")
    db.delete(org)
    db.commit()
    return {"message": "删除成功"}
