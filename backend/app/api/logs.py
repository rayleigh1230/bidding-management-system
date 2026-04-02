from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_

from ..core.database import get_db
from ..core.security import get_current_user
from ..models.user import User
from ..models.operation_log import OperationLog

router = APIRouter(prefix="/api/logs", tags=["操作日志"])


@router.get("")
def get_logs(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
    entity_type: Optional[str] = Query(None, description="实体类型筛选"),
    action: Optional[str] = Query(None, description="操作类型筛选"),
    start_date: Optional[str] = Query(None, description="开始日期 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="结束日期 (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Paginated operation logs with optional filters, enriched with username."""
    query = db.query(OperationLog)

    # Apply filters
    if entity_type:
        query = query.filter(OperationLog.entity_type == entity_type)
    if action:
        query = query.filter(OperationLog.action == action)
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            query = query.filter(OperationLog.created_at >= start_dt)
        except ValueError:
            pass
    if end_date:
        try:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            # Include the entire end day
            end_dt = end_dt.replace(hour=23, minute=59, second=59)
            query = query.filter(OperationLog.created_at <= end_dt)
        except ValueError:
            pass

    total = query.count()

    items = (
        query.order_by(OperationLog.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    # Batch fetch usernames for the logs on this page
    user_ids = {log.user_id for log in items if log.user_id is not None}
    user_map = {}
    if user_ids:
        users = db.query(User).filter(User.id.in_(user_ids)).all()
        for u in users:
            user_map[u.id] = u.display_name or u.username

    # Build enriched items
    enriched_items = []
    for log in items:
        enriched_items.append({
            "id": log.id,
            "user_id": log.user_id,
            "username": user_map.get(log.user_id, "未知用户"),
            "action": log.action,
            "entity_type": log.entity_type,
            "entity_id": log.entity_id,
            "detail": log.detail,
            "created_at": str(log.created_at) if log.created_at else None,
        })

    return {
        "items": enriched_items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }
