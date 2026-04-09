from datetime import date, timedelta
from collections import defaultdict
import json

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..core.database import get_db
from ..core.security import get_current_user
from ..models.user import User
from ..models.project import ProjectInfo, ProjectStatus
from ..models.organization import Organization

router = APIRouter(prefix="/api/stats", tags=["统计分析"])


@router.get("/overview")
def get_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Dashboard overview: status counts, monthly summary, upcoming deadlines, unreturned deposits."""

    # --- status_counts ---
    status_rows = (
        db.query(ProjectInfo.status, func.count(ProjectInfo.id))
        .group_by(ProjectInfo.status)
        .all()
    )
    status_counts = {}
    for status_val, count in status_rows:
        status_key = status_val.value if hasattr(status_val, "value") else str(status_val)
        status_counts[status_key] = count

    # --- monthly_summary: projects submitted/won/lost this month ---
    today = date.today()
    month_start = today.replace(day=1)
    result_statuses = [ProjectStatus.submitted, ProjectStatus.won, ProjectStatus.lost]

    month_projects = (
        db.query(ProjectInfo)
        .filter(
            ProjectInfo.status.in_(result_statuses),
            ProjectInfo.updated_at >= month_start,
        )
        .all()
    )
    month_bids = len(month_projects)
    month_wins = sum(1 for p in month_projects if p.status == ProjectStatus.won)
    month_win_rate = round(month_wins / month_bids, 4) if month_bids > 0 else 0.0

    # --- upcoming_deadlines ---
    deadline_end = today + timedelta(days=7)
    active_statuses = [ProjectStatus.published, ProjectStatus.preparing]

    upcoming = (
        db.query(ProjectInfo)
        .filter(
            ProjectInfo.bid_deadline >= today,
            ProjectInfo.bid_deadline <= deadline_end,
            ProjectInfo.status.in_(active_statuses),
        )
        .all()
    )
    upcoming_deadlines = [
        {
            "project_id": p.id,
            "project_name": p.project_name,
            "bid_deadline": str(p.bid_deadline) if p.bid_deadline else None,
            "budget_amount": float(p.budget_amount) if p.budget_amount else 0,
        }
        for p in upcoming
    ]

    # --- deposit_not_returned ---
    deposit_not_returned_list = (
        db.query(ProjectInfo)
        .filter(ProjectInfo.deposit_status == "未收回")
        .all()
    )
    deposit_not_returned = [
        {
            "project_id": p.id,
            "project_name": p.project_name,
            "deposit_amount": float(p.deposit_amount) if p.deposit_amount else 0,
            "deposit_date": str(p.deposit_date) if p.deposit_date else None,
        }
        for p in deposit_not_returned_list
    ]

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
    year: int = Query(None, description="年份"),
    bidding_type: str = Query(None, description="招标类型筛选"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Win rate statistics grouped by time period."""
    query = db.query(ProjectInfo).filter(
        ProjectInfo.status.in_([ProjectStatus.won, ProjectStatus.lost])
    )

    if year is not None:
        query = query.filter(
            ProjectInfo.updated_at >= date(year, 1, 1),
            ProjectInfo.updated_at < date(year + 1, 1, 1),
        )

    if bidding_type:
        query = query.filter(ProjectInfo.bidding_type == bidding_type)

    projects = query.all()

    groups = defaultdict(lambda: {"total": 0, "wins": 0})
    for p in projects:
        updated = p.updated_at
        if updated is None:
            continue
        if period == "month":
            label = updated.strftime("%Y-%m")
        elif period == "quarter":
            q = (updated.month - 1) // 3 + 1
            label = f"{updated.year}-Q{q}"
        elif period == "year":
            label = str(updated.year)
        else:
            label = updated.strftime("%Y-%m")
        groups[label]["total"] += 1
        if p.status == ProjectStatus.won:
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
    """Competitor analysis from competitors JSON field."""
    projects = db.query(ProjectInfo).filter(ProjectInfo.competitors.isnot(None)).all()

    org_ids = set()
    competitor_records = []

    for p in projects:
        competitors = p.competitors
        if not competitors:
            continue
        if isinstance(competitors, str):
            try:
                competitors = json.loads(competitors)
            except (json.JSONDecodeError, TypeError):
                continue
        if not isinstance(competitors, list):
            continue
        competitor_records.append((p, competitors))
        for comp in competitors:
            if isinstance(comp, dict) and "org_id" in comp:
                org_ids.add(comp["org_id"])

    org_map = {}
    if org_ids:
        orgs = db.query(Organization).filter(Organization.id.in_(org_ids)).all()
        for org in orgs:
            org_map[org.id] = org.name

    stats = defaultdict(lambda: {"encounter_count": 0, "win_count": 0})
    for p, competitors in competitor_records:
        for comp in competitors:
            if not isinstance(comp, dict) or "org_id" not in comp:
                continue
            org_id = comp["org_id"]
            stats[org_id]["encounter_count"] += 1
            if not p.is_won:
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
    response.sort(key=lambda x: x["encounter_count"], reverse=True)
    return response


@router.get("/deposits")
def get_deposits(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Deposit tracking: all projects with has_deposit=True."""
    projects = (
        db.query(ProjectInfo)
        .filter(ProjectInfo.has_deposit == True)  # noqa: E712
        .all()
    )

    today = date.today()
    response = []
    for p in projects:
        deposit_status_value = (
            p.result_deposit_status.value
            if p.result_deposit_status and hasattr(p.result_deposit_status, "value")
            else (p.deposit_status.value if p.deposit_status and hasattr(p.deposit_status, "value") else "")
        )

        days_overdue = 0
        if deposit_status_value == "未收回" and p.deposit_date:
            days_since_deposit = (today - p.deposit_date).days
            if days_since_deposit > 30:
                days_overdue = days_since_deposit - 30

        response.append({
            "project_id": p.id,
            "project_name": p.project_name,
            "deposit_amount": float(p.deposit_amount) if p.deposit_amount else 0,
            "deposit_status": deposit_status_value,
            "deposit_date": str(p.deposit_date) if p.deposit_date else None,
            "deposit_return_date": str(p.deposit_return_date) if p.deposit_return_date else None,
            "days_overdue": days_overdue,
        })

    response.sort(key=lambda x: (0 if x["deposit_status"] == "未收回" else 1, -x["days_overdue"]))
    return response
