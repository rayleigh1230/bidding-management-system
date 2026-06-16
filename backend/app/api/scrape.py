"""招标信息抓取 API。

POST   /api/scrape/run              触发抓取（管理员）
GET    /api/scrape/status/{run_id}  查询状态（轮询）
GET    /api/scrape/runs             历史列表
GET    /api/scrape/runs/{run_id}    单次详情（含 item_logs）
"""
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..core.security import get_current_user
from ..models.scrape import ScrapeRun, ScrapeItemLog
from ..models.user import User, UserRole
from ..schemas.scrape import (
    ScrapeRunResponse, ScrapeRunDetailResponse, ScrapeItemLogResponse,
)
from ..services.scrape_runner import run_scraper

router = APIRouter(prefix="/api/scrape", tags=["招标抓取"])


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """要求当前用户是管理员。"""
    role_val = current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role)
    if role_val != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可执行此操作")
    return current_user


@router.post("/run")
def trigger_scrape(
    bg: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """触发一次抓取。立即返回 run_id，后台异步执行。"""
    existing = (
        db.query(ScrapeRun)
        .filter(ScrapeRun.status == "running")
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"已有抓取任务进行中 (run_id={existing.id})，请等待完成",
        )

    run = ScrapeRun(
        started_at=datetime.now(),
        triggered_by=current_user.id,
        status="running",
        total_count=0,
        created_count=0,
        skipped_count=0,
        failed_count=0,
        sites_summary={},
        error_summary={},
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    bg.add_task(run_scraper, run.id, current_user.id)
    return {"run_id": run.id, "status": "running"}


@router.get("/status/{run_id}")
def get_status(
    run_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    run = db.query(ScrapeRun).filter(ScrapeRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="抓取记录不存在")
    return _enrich_run_dict(run, db)


@router.get("/runs")
def list_runs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(ScrapeRun).order_by(ScrapeRun.started_at.desc())
    total = query.count()
    runs = query.offset((page - 1) * page_size).limit(page_size).all()
    return {
        "items": [_enrich_run_dict(r, db) for r in runs],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/runs/{run_id}")
def get_run_detail(
    run_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    run = db.query(ScrapeRun).filter(ScrapeRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="抓取记录不存在")

    logs = (
        db.query(ScrapeItemLog)
        .filter(ScrapeItemLog.run_id == run_id)
        .order_by(ScrapeItemLog.id.asc())
        .all()
    )

    resp = _enrich_run_dict(run, db)
    resp["item_logs"] = [ScrapeItemLogResponse.model_validate(log) for log in logs]
    return resp


def _enrich_run_dict(run: ScrapeRun, db: Session) -> dict:
    triggered_by_name = None
    if run.triggered_by:
        user = db.query(User).filter(User.id == run.triggered_by).first()
        if user:
            triggered_by_name = user.display_name or user.username

    return {
        "id": run.id,
        "started_at": run.started_at,
        "finished_at": run.finished_at,
        "triggered_by": run.triggered_by,
        "triggered_by_name": triggered_by_name,
        "status": run.status,
        "total_count": run.total_count,
        "created_count": run.created_count,
        "skipped_count": run.skipped_count,
        "failed_count": run.failed_count,
        "sites_summary": run.sites_summary or {},
        "error_summary": run.error_summary or {},
    }
