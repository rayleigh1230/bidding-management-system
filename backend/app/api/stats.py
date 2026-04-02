from datetime import date, datetime, timedelta
from collections import defaultdict

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..core.database import get_db
from ..core.security import get_current_user
from ..models.user import User
from ..models.project import ProjectInfo, ProjectStatus
from ..models.bidding_info import BiddingInfo
from ..models.bid_info import BidInfo, DepositStatus
from ..models.bid_result import BidResult
from ..models.organization import Organization

router = APIRouter(prefix="/api/stats", tags=["统计分析"])


@router.get("/overview")
def get_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Dashboard overview: status counts, monthly summary, upcoming deadlines, unreturned deposits."""

    # --- status_counts: count projects grouped by status ---
    status_rows = (
        db.query(ProjectInfo.status, func.count(ProjectInfo.id))
        .group_by(ProjectInfo.status)
        .all()
    )
    status_counts = {}
    for status_val, count in status_rows:
        # Enum values come back as their string value
        status_key = status_val.value if hasattr(status_val, "value") else str(status_val)
        status_counts[status_key] = count

    # --- monthly_summary: bids and wins in current month ---
    today = date.today()
    month_start = today.replace(day=1)

    # Month bids: count BidResults created this month
    month_bid_results = (
        db.query(BidResult)
        .filter(BidResult.created_at >= month_start)
        .all()
    )
    month_bids = len(month_bid_results)
    month_wins = sum(1 for r in month_bid_results if r.is_won)
    month_win_rate = round(month_wins / month_bids, 4) if month_bids > 0 else 0.0

    # --- upcoming_deadlines: BiddingInfo where bid_deadline within 7 days and project is active ---
    deadline_end = today + timedelta(days=7)
    active_statuses = [ProjectStatus.published, ProjectStatus.preparing]

    upcoming_bidding_infos = (
        db.query(BiddingInfo)
        .join(ProjectInfo, BiddingInfo.project_id == ProjectInfo.id)
        .filter(
            BiddingInfo.bid_deadline >= today,
            BiddingInfo.bid_deadline <= deadline_end,
            ProjectInfo.status.in_(active_statuses),
        )
        .all()
    )
    upcoming_deadlines = []
    for bi in upcoming_bidding_infos:
        project = db.query(ProjectInfo).filter(ProjectInfo.id == bi.project_id).first()
        upcoming_deadlines.append({
            "bidding_info_id": bi.id,
            "project_id": bi.project_id,
            "project_name": project.project_name if project else "",
            "bid_deadline": str(bi.bid_deadline) if bi.bid_deadline else None,
            "budget_amount": float(bi.budget_amount) if bi.budget_amount else 0,
        })

    # --- deposit_not_returned: BidInfo where deposit_status is "未收回" ---
    deposit_not_returned_list = (
        db.query(BidInfo)
        .filter(BidInfo.deposit_status == DepositStatus.not_returned)
        .all()
    )
    deposit_not_returned = []
    for bid in deposit_not_returned:
        bidding_info = db.query(BiddingInfo).filter(BiddingInfo.id == bid.bidding_info_id).first()
        project = (
            db.query(ProjectInfo).filter(ProjectInfo.id == bidding_info.project_id).first()
            if bidding_info else None
        )
        deposit_not_returned.append({
            "bid_info_id": bid.id,
            "project_name": project.project_name if project else "",
            "deposit_amount": float(bid.deposit_amount) if bid.deposit_amount else 0,
            "deposit_date": str(bid.deposit_date) if bid.deposit_date else None,
        })

    return {
        "status_counts": status_counts,
        "monthly_summary": {
            "month_bids": month_bids,
            "month_wins": month_wins,
            "month_win_rate": month_win_rate,
        },
        "upcoming_deadlines": upcoming_deadlines,
        "deposit_not_returned": deposit_not_returned,
    }


@router.get("/win-rate")
def get_win_rate(
    period: str = Query("month", description="统计周期: month/quarter/year"),
    year: int = Query(None, description="年份, 不传则取全部"),
    bidding_type: str = Query(None, description="招标类型筛选"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Win rate statistics grouped by time period."""
    query = db.query(BidResult)

    if year is not None:
        query = query.filter(
            BidResult.created_at >= date(year, 1, 1),
            BidResult.created_at < date(year + 1, 1, 1),
        )

    # If bidding_type filter is needed, join through BidInfo -> BiddingInfo -> ProjectInfo
    if bidding_type:
        query = (
            query
            .join(BidInfo, BidResult.bid_info_id == BidInfo.id)
            .join(BiddingInfo, BidInfo.bidding_info_id == BiddingInfo.id)
            .join(ProjectInfo, BiddingInfo.project_id == ProjectInfo.id)
            .filter(ProjectInfo.bidding_type == bidding_type)
        )

    results = query.all()

    # Group results by period
    groups = defaultdict(lambda: {"total": 0, "wins": 0})

    for r in results:
        created = r.created_at
        if created is None:
            continue

        if period == "month":
            label = created.strftime("%Y-%m")
        elif period == "quarter":
            q = (created.month - 1) // 3 + 1
            label = f"{created.year}-Q{q}"
        elif period == "year":
            label = str(created.year)
        else:
            label = created.strftime("%Y-%m")

        groups[label]["total"] += 1
        if r.is_won:
            groups[label]["wins"] += 1

    response = []
    for label in sorted(groups.keys()):
        total = groups[label]["total"]
        wins = groups[label]["wins"]
        response.append({
            "period_label": label,
            "total_bids": total,
            "wins": wins,
            "win_rate": round(wins / total, 4) if total > 0 else 0.0,
        })

    return response


@router.get("/competitors")
def get_competitors(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Competitor analysis: encounter count and win rate per competitor organization."""
    # Fetch all BidResults that have competitors data
    results = db.query(BidResult).all()

    # Collect all unique org_ids from competitors JSON
    org_ids = set()
    competitor_records = []  # list of (result, competitor_list)

    for r in results:
        competitors = r.competitors
        if not competitors or not isinstance(competitors, list):
            continue
        competitor_records.append((r, competitors))
        for comp in competitors:
            if isinstance(comp, dict) and "org_id" in comp:
                org_ids.add(comp["org_id"])

    # Batch fetch organization names
    org_map = {}
    if org_ids:
        orgs = db.query(Organization).filter(Organization.id.in_(org_ids)).all()
        for org in orgs:
            org_map[org.id] = org.name

    # Build stats per competitor
    stats = defaultdict(lambda: {"encounter_count": 0, "win_count": 0})

    for r, competitors in competitor_records:
        for comp in competitors:
            if not isinstance(comp, dict) or "org_id" not in comp:
                continue
            org_id = comp["org_id"]
            stats[org_id]["encounter_count"] += 1
            # If we lost (is_won=False), the competitor might have won
            # We count competitor "win" when our result is_won=False
            if not r.is_won:
                stats[org_id]["win_count"] += 1

    response = []
    for org_id, data in stats.items():
        encounter_count = data["encounter_count"]
        win_count = data["win_count"]
        response.append({
            "org_id": org_id,
            "org_name": org_map.get(org_id, f"未知机构({org_id})"),
            "encounter_count": encounter_count,
            "win_count": win_count,
            "win_rate": round(win_count / encounter_count, 4) if encounter_count > 0 else 0.0,
        })

    # Sort by encounter_count descending
    response.sort(key=lambda x: x["encounter_count"], reverse=True)
    return response


@router.get("/deposits")
def get_deposits(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Deposit tracking: all BidInfo with deposit info, enriched with project name and overdue calculation."""
    # Query all BidInfo that have deposits
    bid_infos = (
        db.query(BidInfo)
        .filter(BidInfo.has_deposit == True)  # noqa: E712
        .all()
    )

    today = date.today()
    response = []

    for bid in bid_infos:
        # Walk up the chain: BidInfo -> BiddingInfo -> ProjectInfo
        bidding_info = (
            db.query(BiddingInfo).filter(BiddingInfo.id == bid.bidding_info_id).first()
        )
        project = (
            db.query(ProjectInfo).filter(ProjectInfo.id == bidding_info.project_id).first()
            if bidding_info else None
        )

        # Also check BidResult for deposit_status
        bid_result = (
            db.query(BidResult).filter(BidResult.bid_info_id == bid.id).first()
        )

        deposit_status_value = (
            bid_result.deposit_status.value
            if bid_result and bid_result.deposit_status
            else (bid.deposit_status.value if bid.deposit_status else "")
        )

        # Calculate days overdue: if deposit_status is "未收回" and >30 days since bid_deadline
        days_overdue = 0
        if deposit_status_value == "未收回" and bid.deposit_date:
            days_since_deposit = (today - bid.deposit_date).days
            if days_since_deposit > 30:
                days_overdue = days_since_deposit - 30

        response.append({
            "bid_info_id": bid.id,
            "project_name": project.project_name if project else "",
            "deposit_amount": float(bid.deposit_amount) if bid.deposit_amount else 0,
            "deposit_status": deposit_status_value,
            "deposit_date": str(bid.deposit_date) if bid.deposit_date else None,
            "deposit_return_date": str(bid.deposit_return_date) if bid.deposit_return_date else None,
            "days_overdue": days_overdue,
        })

    # Sort: unreturned deposits first, then by days_overdue descending
    response.sort(key=lambda x: (0 if x["deposit_status"] == "未收回" else 1, -x["days_overdue"]))
    return response
