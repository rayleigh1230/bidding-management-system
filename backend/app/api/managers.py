from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_

from ..core.database import get_db
from ..models.manager import Manager
from ..schemas.dict import ManagerCreate, ManagerUpdate, ManagerResponse
from ..core.security import get_current_user
from ..services.logger import log_operation

router = APIRouter(prefix="/api/managers", tags=["经办人管理"])


@router.get("", response_model=dict)
def list_managers(
    keyword: str = Query("", description="搜索关键词"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = db.query(Manager)
    if keyword:
        query = query.filter(
            or_(
                Manager.name.contains(keyword),
                Manager.phone.contains(keyword),
                Manager.company.contains(keyword),
            )
        )
    total = query.count()
    items = (
        query.order_by(Manager.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {
        "items": [ManagerResponse.model_validate(item) for item in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("", response_model=ManagerResponse)
def create_manager(
    data: ManagerCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    existing = db.query(Manager).filter(Manager.name == data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="经办人名称已存在")
    manager = Manager(**data.model_dump())
    db.add(manager)
    db.flush()
    log_operation(db, current_user.id, "create", "manager", manager.id, f"创建经办人: {manager.name}")
    db.commit()
    db.refresh(manager)
    return manager


@router.put("/{manager_id}", response_model=ManagerResponse)
def update_manager(
    manager_id: int,
    data: ManagerUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    manager = db.query(Manager).filter(Manager.id == manager_id).first()
    if not manager:
        raise HTTPException(status_code=404, detail="经办人不存在")
    update_data = data.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="没有需要更新的字段")
    if "name" in update_data and update_data["name"] != manager.name:
        existing = (
            db.query(Manager).filter(Manager.name == update_data["name"]).first()
        )
        if existing:
            raise HTTPException(status_code=400, detail="经办人名称已存在")
    for field, value in update_data.items():
        setattr(manager, field, value)
    log_operation(db, current_user.id, "update", "manager", manager.id, f"更新经办人: {manager.name}")
    db.commit()
    db.refresh(manager)
    return manager


@router.delete("/{manager_id}")
def delete_manager(
    manager_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    manager = db.query(Manager).filter(Manager.id == manager_id).first()
    if not manager:
        raise HTTPException(status_code=404, detail="经办人不存在")
    log_operation(db, current_user.id, "delete", "manager", manager.id, f"删除经办人: {manager.name}")
    db.delete(manager)
    db.commit()
    return {"message": "删除成功"}
