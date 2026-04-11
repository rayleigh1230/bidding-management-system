from datetime import date, timedelta
from collections import defaultdict
import json

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, case, text, literal

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

    # --- status_counts (已经是 SQL GROUP BY，无需改动) ---
    status_rows = (
        db.query(ProjectInfo.status, func.count(ProjectInfo.id))
        .group_by(ProjectInfo.status)
        .all()
    )
    status_counts = {}
    for status_val, count in status_rows:
        status_key = status_val.value if hasattr(status_val, "value") else str(status_val)
        status_counts[status_key] = count

    # --- monthly_summary: 使用 SQL 聚合替代 Python 遍历 ---
    today = date.today()
    month_start = today.replace(day=1)
    result_statuses = [ProjectStatus.submitted, ProjectStatus.won, ProjectStatus.lost]

    month_row = (
        db.query(
            func.count(ProjectInfo.id).label("total"),
            func.sum(case((ProjectInfo.status == ProjectStatus.won, 1), else_=0)).label("wins"),
        )
        .filter(
            ProjectInfo.status.in_(result_statuses),
            ProjectInfo.updated_at >= month_start,
        )
        .first()
    )
    month_bids = month_row.total or 0
    month_wins = month_row.wins or 0
    month_win_rate = round(month_wins / month_bids, 4) if month_bids > 0 else 0.0

    # --- upcoming_deadlines (结果集小，保持不变) ---
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

    # --- deposit_not_returned (结果集小，保持不变) ---
    deposit_not_returned_list = (
        db.query(ProjectInfo)
        .filter(
            ProjectInfo.has_deposit == True,  # noqa: E712
            ProjectInfo.result_deposit_status == "未收回",
        )
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
    """Win rate statistics — SQL 按月聚合，Python 合并为季度/年."""
    # 统一按月 SQL 聚合（最多产生几十行，极快）
    month_expr = func.strftime("%Y-%m", ProjectInfo.updated_at)

    query = db.query(
        month_expr.label("ym"),
        func.count(ProjectInfo.id).label("total_bids"),
        func.sum(case((ProjectInfo.status == ProjectStatus.won, 1), else_=0)).label("wins"),
    ).filter(
        ProjectInfo.status.in_([ProjectStatus.won, ProjectStatus.lost])
    )

    if year is not None:
        query = query.filter(
            ProjectInfo.updated_at >= date(year, 1, 1),
            ProjectInfo.updated_at < date(year + 1, 1, 1),
        )

    if bidding_type:
        query = query.filter(ProjectInfo.bidding_type == bidding_type)

    month_rows = query.group_by(month_expr).order_by(month_expr).all()

    # 按周期合并（月度数据行很少，Python 处理微不足道）
    groups = defaultdict(lambda: {"total_bids": 0, "wins": 0})
    for row in month_rows:
        ym = row.ym
        if period == "month":
            label = ym
        elif period == "quarter":
            y, m = ym.split("-")
            q = (int(m) - 1) // 3 + 1
            label = f"{y}-Q{q}"
        elif period == "year":
            label = ym[:4]
        else:
            label = ym
        groups[label]["total_bids"] += row.total_bids
        groups[label]["wins"] += row.wins or 0

    return [
        {
            "period_label": label,
            "total_bids": data["total_bids"],
            "wins": data["wins"],
            "win_rate": round(data["wins"] / data["total_bids"], 4) if data["total_bids"] > 0 else 0.0,
        }
        for label, data in sorted(groups.items())
    ]


@router.get("/competitors")
def get_competitors(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Competitor analysis — 使用 SQLite json_each() 替代 Python 全表遍历."""
    # 使用原生 SQL 的 json_each() 展开 competitors JSON 数组
    # 同时兼容旧格式 org_id 和新格式 org_ids
    raw_sql = text("""
        SELECT
            COALESCE(
                json_extract(je.value, '$.org_ids[0]'),
                json_extract(je.value, '$.org_id')
            ) AS org_id,
            COUNT(*) AS encounter_count,
            SUM(CASE WHEN pi.is_won = 0 AND pi.is_bid_failed = 0 THEN 1 ELSE 0 END) AS win_count
        FROM project_infos pi, json_each(pi.competitors) je
        WHERE pi.competitors IS NOT NULL
            AND pi.competitors != '[]'
            AND pi.competitors != ''
            AND COALESCE(
                json_extract(je.value, '$.org_ids[0]'),
                json_extract(je.value, '$.org_id')
            ) IS NOT NULL
        GROUP BY org_id
        ORDER BY encounter_count DESC
    """)

    rows = db.execute(raw_sql).fetchall()

    org_ids = [row[0] for row in rows if row[0] is not None]
    org_map = {}
    if org_ids:
        orgs = db.query(Organization).filter(Organization.id.in_(org_ids)).all()
        org_map = {o.id: o.name for o in orgs}

    response = []
    for row in rows:
        oid = row[0]
        if oid is None:
            continue
        encounter_count = row[1]
        win_count = row[2] or 0
        response.append({
            "org_id": oid,
            "org_name": org_map.get(oid, f"未知机构({oid})"),
            "encounter_count": encounter_count,
            "win_count": win_count,
            "win_rate": round(win_count / encounter_count, 4) if encounter_count > 0 else 0.0,
        })

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
        deposit_status_value = ""
        if p.status in (ProjectStatus.submitted, ProjectStatus.won, ProjectStatus.lost):
            # 已投标及之后：显示收回状态
            if p.result_deposit_status and hasattr(p.result_deposit_status, "value"):
                deposit_status_value = p.result_deposit_status.value
        else:
            # 已投标前：显示缴纳状态
            if p.deposit_status and hasattr(p.deposit_status, "value"):
                deposit_status_value = p.deposit_status.value

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
