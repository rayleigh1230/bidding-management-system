import json
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..core.security import get_current_user
from ..models.project import ProjectInfo, ProjectStatus
from ..models.bidding_info import BiddingInfo
from ..models.bid_info import BidInfo, DepositStatus
from ..models.bid_result import BidResult
from ..models.organization import Organization
from ..schemas.bid import BidInfoUpdate, BidInfoResponse
from ..services.logger import log_operation

router = APIRouter(prefix="/api/bids", tags=["投标信息管理"])


def _get_project_from_bid_info(bid_info: BidInfo, db: Session) -> ProjectInfo:
    """Traverse BidInfo -> BiddingInfo -> ProjectInfo."""
    bidding = db.query(BiddingInfo).filter(BiddingInfo.id == bid_info.bidding_info_id).first()
    if not bidding:
        return None
    return db.query(ProjectInfo).filter(ProjectInfo.id == bidding.project_id).first()


def enrich_bid_info(bid: BidInfo, db: Session) -> dict:
    """Enrich a BidInfo with project_name and partner_names."""
    data = BidInfoResponse.model_validate(bid).model_dump()

    # Enrich project_name through bidding_info -> project
    bidding = db.query(BiddingInfo).filter(BiddingInfo.id == bid.bidding_info_id).first()
    if bidding:
        project = db.query(ProjectInfo).filter(ProjectInfo.id == bidding.project_id).first()
        data["project_name"] = project.project_name if project else None
    else:
        data["project_name"] = None

    # Enrich partner_names
    partner_ids = bid.partner_ids if bid.partner_ids else []
    if isinstance(partner_ids, str):
        try:
            partner_ids = json.loads(partner_ids)
        except (json.JSONDecodeError, TypeError):
            partner_ids = []
    if partner_ids:
        orgs = db.query(Organization).filter(Organization.id.in_(partner_ids)).all()
        org_map = {o.id: o.name for o in orgs}
        data["partner_names"] = [org_map.get(pid) for pid in partner_ids if pid in org_map]
    else:
        data["partner_names"] = []

    return data


@router.get("", response_model=dict)
def list_bid_infos(
    keyword: str = Query("", description="搜索关键词"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = db.query(BidInfo)

    if keyword:
        # Search by project name through the chain: BidInfo -> BiddingInfo -> ProjectInfo
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
        query = query.filter(BidInfo.bidding_info_id.in_(bidding_subquery))

    total = query.count()
    items = (
        query.order_by(BidInfo.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    enriched = [enrich_bid_info(item, db) for item in items]
    return {
        "items": enriched,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/{bid_id}", response_model=dict)
def get_bid_info(
    bid_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    bid = db.query(BidInfo).filter(BidInfo.id == bid_id).first()
    if not bid:
        raise HTTPException(status_code=404, detail="投标信息不存在")
    return enrich_bid_info(bid, db)


@router.put("/{bid_id}", response_model=dict)
def update_bid_info(
    bid_id: int,
    data: BidInfoUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    bid = db.query(BidInfo).filter(BidInfo.id == bid_id).first()
    if not bid:
        raise HTTPException(status_code=404, detail="投标信息不存在")

    update_data = data.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="没有需要更新的字段")

    for field, value in update_data.items():
        if field == "partner_ids" and isinstance(value, list):
            value = json.dumps(value, ensure_ascii=False)
        elif field == "bid_files" and isinstance(value, list):
            value = json.dumps(value, ensure_ascii=False)
        setattr(bid, field, value)

    log_operation(db, current_user.id, "update", "bid_info", bid.id, "更新投标信息")
    db.commit()
    db.refresh(bid)
    return enrich_bid_info(bid, db)


@router.post("/{bid_id}/submit", response_model=dict)
def submit_bid(
    bid_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    bid = db.query(BidInfo).filter(BidInfo.id == bid_id).first()
    if not bid:
        raise HTTPException(status_code=404, detail="投标信息不存在")

    # Set bid_status to "已投标"
    bid.bid_status = "已投标"

    # If has_deposit and deposit_status is "已缴纳", set deposit_status to "未收回"
    if bid.has_deposit and bid.deposit_status == "已缴纳":
        bid.deposit_status = "未收回"

    # Check if BidResult already exists for this BidInfo
    existing = db.query(BidResult).filter(BidResult.bid_info_id == bid_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="该投标已存在投标结果")

    # Create empty BidResult
    bid_result = BidResult(bid_info_id=bid_id)
    db.add(bid_result)

    # Update project status to "已投标"
    project = _get_project_from_bid_info(bid, db)
    if project:
        project.status = ProjectStatus.submitted

    log_operation(db, current_user.id, "advance", "bid_info", bid.id, f"提交投标, 项目: {project.project_name if project else ''}")
    db.commit()
    db.refresh(bid_result)

    return {
        "message": "提交投标成功",
        "bid_result_id": bid_result.id,
    }


@router.post("/{bid_id}/abandon", response_model=dict)
def abandon_bid(
    bid_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    bid = db.query(BidInfo).filter(BidInfo.id == bid_id).first()
    if not bid:
        raise HTTPException(status_code=404, detail="投标信息不存在")

    # Update project status to "已放弃"
    project = _get_project_from_bid_info(bid, db)
    if project:
        project.status = ProjectStatus.abandoned

    log_operation(db, current_user.id, "abandon", "bid_info", bid.id, f"放弃投标, 项目: {project.project_name if project else ''}")
    db.commit()
    return {"message": "已放弃该投标"}
