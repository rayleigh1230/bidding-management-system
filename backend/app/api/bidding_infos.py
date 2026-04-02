import json
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..core.security import get_current_user
from ..models.project import ProjectInfo, ProjectStatus
from ..models.bidding_info import BiddingInfo
from ..models.bid_info import BidInfo
from ..models.organization import Organization
from ..models.platform import Platform
from ..models.user import User
from ..schemas.bidding import BiddingInfoCreate, BiddingInfoUpdate, BiddingInfoResponse
from ..services.logger import log_operation

router = APIRouter(prefix="/api/biddings", tags=["招标信息管理"])


def enrich_bidding_info(bidding: BiddingInfo, db: Session) -> dict:
    """Enrich a BiddingInfo with related names."""
    data = BiddingInfoResponse.model_validate(bidding).model_dump()

    # Enrich project_name
    project = db.query(ProjectInfo).filter(ProjectInfo.id == bidding.project_id).first()
    data["project_name"] = project.project_name if project else None

    # Enrich agency_name
    if bidding.agency_id:
        org = db.query(Organization).filter(Organization.id == bidding.agency_id).first()
        data["agency_name"] = org.name if org else None
    else:
        data["agency_name"] = None

    # Enrich platform_name
    if bidding.publish_platform_id:
        platform = db.query(Platform).filter(Platform.id == bidding.publish_platform_id).first()
        data["platform_name"] = platform.name if platform else None
    else:
        data["platform_name"] = None

    # Enrich specialist_name
    if bidding.bid_specialist_id:
        user = db.query(User).filter(User.id == bidding.bid_specialist_id).first()
        data["specialist_name"] = user.display_name if user else None
    else:
        data["specialist_name"] = None

    return data


@router.get("", response_model=dict)
def list_bidding_infos(
    keyword: str = Query("", description="搜索关键词"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = db.query(BiddingInfo)

    if keyword:
        # Search by project name through join
        project_subquery = (
            db.query(ProjectInfo.id)
            .filter(ProjectInfo.project_name.contains(keyword))
            .subquery()
        )
        query = query.filter(BiddingInfo.project_id.in_(project_subquery))

    total = query.count()
    items = (
        query.order_by(BiddingInfo.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    enriched = [enrich_bidding_info(item, db) for item in items]
    return {
        "items": enriched,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("", response_model=dict)
def create_bidding_info(
    data: BiddingInfoCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    # Verify project exists
    project = db.query(ProjectInfo).filter(ProjectInfo.id == data.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="关联项目不存在")

    # Check if BiddingInfo already exists for this project
    existing = db.query(BiddingInfo).filter(BiddingInfo.project_id == data.project_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="该项目已存在招标信息")

    bidding = BiddingInfo(
        project_id=data.project_id,
        agency_id=data.agency_id,
        publish_platform_id=data.publish_platform_id,
        tags=json.dumps(data.tags, ensure_ascii=False) if data.tags else [],
        registration_deadline=data.registration_deadline,
        bid_deadline=data.bid_deadline,
        budget_type=data.budget_type,
        budget_amount=data.budget_amount,
        is_prequalification=data.is_prequalification,
        bid_specialist_id=data.bid_specialist_id,
        bid_documents=json.dumps(data.bid_documents, ensure_ascii=False) if data.bid_documents else [],
        notes=data.notes,
    )
    db.add(bidding)
    db.flush()
    log_operation(db, current_user.id, "create", "bidding_info", bidding.id, f"创建招标信息, 项目: {project.project_name}")
    db.commit()
    db.refresh(bidding)
    return enrich_bidding_info(bidding, db)


@router.get("/{bidding_id}", response_model=dict)
def get_bidding_info(
    bidding_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    bidding = db.query(BiddingInfo).filter(BiddingInfo.id == bidding_id).first()
    if not bidding:
        raise HTTPException(status_code=404, detail="招标信息不存在")
    return enrich_bidding_info(bidding, db)


@router.put("/{bidding_id}", response_model=dict)
def update_bidding_info(
    bidding_id: int,
    data: BiddingInfoUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    bidding = db.query(BiddingInfo).filter(BiddingInfo.id == bidding_id).first()
    if not bidding:
        raise HTTPException(status_code=404, detail="招标信息不存在")

    update_data = data.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="没有需要更新的字段")

    for field, value in update_data.items():
        if field in ("tags", "bid_documents") and isinstance(value, list):
            value = json.dumps(value, ensure_ascii=False)
        setattr(bidding, field, value)

    log_operation(db, current_user.id, "update", "bidding_info", bidding.id, "更新招标信息")
    db.commit()
    db.refresh(bidding)
    return enrich_bidding_info(bidding, db)


@router.post("/{bidding_id}/prepare", response_model=dict)
def prepare_bid(
    bidding_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    bidding = db.query(BiddingInfo).filter(BiddingInfo.id == bidding_id).first()
    if not bidding:
        raise HTTPException(status_code=404, detail="招标信息不存在")

    # Check if BidInfo already exists for this BiddingInfo
    existing = db.query(BidInfo).filter(BidInfo.bidding_info_id == bidding_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="该招标信息已准备投标")

    # Create empty BidInfo
    bid_info = BidInfo(
        bidding_info_id=bidding_id,
        created_by=current_user.id,
    )
    db.add(bid_info)

    # Update project status to "准备投标"
    project = db.query(ProjectInfo).filter(ProjectInfo.id == bidding.project_id).first()
    if project:
        project.status = ProjectStatus.preparing

    log_operation(db, current_user.id, "advance", "bidding_info", bidding.id, f"准备投标, 项目: {project.project_name if project else ''}")
    db.commit()
    db.refresh(bid_info)

    return {
        "message": "准备投标成功",
        "bid_info_id": bid_info.id,
    }


@router.post("/{bidding_id}/abandon", response_model=dict)
def abandon_bidding(
    bidding_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    bidding = db.query(BiddingInfo).filter(BiddingInfo.id == bidding_id).first()
    if not bidding:
        raise HTTPException(status_code=404, detail="招标信息不存在")

    # Update project status to "已放弃"
    project = db.query(ProjectInfo).filter(ProjectInfo.id == bidding.project_id).first()
    if project:
        project.status = ProjectStatus.abandoned

    log_operation(db, current_user.id, "abandon", "bidding_info", bidding.id, f"放弃招标, 项目: {project.project_name if project else ''}")
    db.commit()
    return {"message": "已放弃该招标"}
