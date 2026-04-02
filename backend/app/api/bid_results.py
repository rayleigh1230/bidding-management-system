import json
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..core.security import get_current_user
from ..models.project import ProjectInfo, ProjectStatus
from ..models.bidding_info import BiddingInfo
from ..models.bid_info import BidInfo
from ..models.bid_result import BidResult
from ..schemas.result import BidResultUpdate, BidResultResponse
from ..services.logger import log_operation

router = APIRouter(prefix="/api/results", tags=["投标结果管理"])


def _get_project_from_bid_result(result: BidResult, db: Session) -> ProjectInfo:
    """Traverse BidResult -> BidInfo -> BiddingInfo -> ProjectInfo."""
    bid_info = db.query(BidInfo).filter(BidInfo.id == result.bid_info_id).first()
    if not bid_info:
        return None
    bidding = db.query(BiddingInfo).filter(BiddingInfo.id == bid_info.bidding_info_id).first()
    if not bidding:
        return None
    return db.query(ProjectInfo).filter(ProjectInfo.id == bidding.project_id).first()


def enrich_bid_result(result: BidResult, db: Session) -> dict:
    """Enrich a BidResult with project_name."""
    data = BidResultResponse.model_validate(result).model_dump()

    # Enrich project_name through bid_info -> bidding_info -> project
    project = _get_project_from_bid_result(result, db)
    data["project_name"] = project.project_name if project else None

    return data


@router.get("", response_model=dict)
def list_bid_results(
    keyword: str = Query("", description="搜索关键词"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = db.query(BidResult)

    if keyword:
        # Search by project name through the full chain
        project_subquery = (
            db.query(ProjectInfo.id)
            .filter(ProjectInfo.project_name.contains(keyword))
            .subquery()
        )
        bidding_subquery = (
            db.query(BiddingInfo.id)
            .filter(BiddingInfo.project_id.in_(project_subquery))
            .subquery()
        )
        bid_info_subquery = (
            db.query(BidInfo.id)
            .filter(BidInfo.bidding_info_id.in_(bidding_subquery))
            .subquery()
        )
        query = query.filter(BidResult.bid_info_id.in_(bid_info_subquery))

    total = query.count()
    items = (
        query.order_by(BidResult.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    enriched = [enrich_bid_result(item, db) for item in items]
    return {
        "items": enriched,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/{result_id}", response_model=dict)
def get_bid_result(
    result_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = db.query(BidResult).filter(BidResult.id == result_id).first()
    if not result:
        raise HTTPException(status_code=404, detail="投标结果不存在")
    return enrich_bid_result(result, db)


@router.put("/{result_id}", response_model=dict)
def update_bid_result(
    result_id: int,
    data: BidResultUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = db.query(BidResult).filter(BidResult.id == result_id).first()
    if not result:
        raise HTTPException(status_code=404, detail="投标结果不存在")

    update_data = data.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="没有需要更新的字段")

    for field, value in update_data.items():
        if field in ("competitors", "scoring_details") and isinstance(value, list):
            value = json.dumps(value, ensure_ascii=False)
        setattr(result, field, value)

    db.commit()
    db.refresh(result)

    # After update, check is_won and update project status accordingly
    project = _get_project_from_bid_result(result, db)
    status_desc = "中标" if result.is_won else "未中标"
    if project:
        if result.is_won:
            project.status = ProjectStatus.won
        else:
            project.status = ProjectStatus.lost

    log_operation(db, current_user.id, "update", "bid_result", result.id, f"更新投标结果({status_desc}), 项目: {project.project_name if project else ''}")
    db.commit()

    return enrich_bid_result(result, db)
