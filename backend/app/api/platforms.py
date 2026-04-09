from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_

from ..core.database import get_db
from ..models.platform import Platform
from ..schemas.dict import PlatformCreate, PlatformUpdate, PlatformResponse
from ..core.security import get_current_user
from ..services.logger import log_operation

router = APIRouter(prefix="/api/platforms", tags=["平台管理"])


@router.get("", response_model=dict)
def list_platforms(
    keyword: str = Query("", description="搜索关键词"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = db.query(Platform)
    if keyword:
        query = query.filter(
            or_(
                Platform.name.contains(keyword),
                Platform.url.contains(keyword),
            )
        )
    total = query.count()
    items = (
        query.order_by(Platform.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {
        "items": [PlatformResponse.model_validate(item) for item in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("", response_model=PlatformResponse)
def create_platform(
    data: PlatformCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    existing = db.query(Platform).filter(Platform.name == data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="平台名称已存在")
    platform = Platform(**data.model_dump())
    db.add(platform)
    db.flush()
    log_operation(db, current_user.id, "create", "platform", platform.id, f"创建平台: {platform.name}")
    db.commit()
    db.refresh(platform)
    return platform


@router.put("/{platform_id}", response_model=PlatformResponse)
def update_platform(
    platform_id: int,
    data: PlatformUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    platform = db.query(Platform).filter(Platform.id == platform_id).first()
    if not platform:
        raise HTTPException(status_code=404, detail="平台不存在")
    update_data = data.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="没有需要更新的字段")
    if "name" in update_data and update_data["name"] != platform.name:
        existing = (
            db.query(Platform).filter(Platform.name == update_data["name"]).first()
        )
        if existing:
            raise HTTPException(status_code=400, detail="平台名称已存在")
    for field, value in update_data.items():
        setattr(platform, field, value)
    log_operation(db, current_user.id, "update", "platform", platform.id, f"更新平台: {platform.name}")
    db.commit()
    db.refresh(platform)
    return platform


@router.delete("/{platform_id}")
def delete_platform(
    platform_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    platform = db.query(Platform).filter(Platform.id == platform_id).first()
    if not platform:
        raise HTTPException(status_code=404, detail="平台不存在")
    log_operation(db, current_user.id, "delete", "platform", platform.id, f"删除平台: {platform.name}")
    db.delete(platform)
    db.commit()
    return {"message": "删除成功"}
