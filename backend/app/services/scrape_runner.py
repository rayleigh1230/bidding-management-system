"""抓取主流程：遍历所有 scraper → 去重 → 创建项目 → 记日志。"""
import logging
from datetime import datetime, date

from sqlalchemy.orm import Session

from ..core.database import SessionLocal
from ..models.project import ProjectInfo, ProjectStatus
from ..models.scrape import ScrapeRun, ScrapeItemLog
from ..models.user import User
from ..scrapers import ScraperRegistry
from ..scrapers.base import ScrapeItem, SiteFetchError
from .org_matcher import match_or_create_org, match_or_create_platform

logger = logging.getLogger(__name__)


def run_scraper(run_id: int, user_id: int):
    """主入口：由 BackgroundTasks 调用。串行跑所有站点。"""
    db = SessionLocal()
    run = db.get(ScrapeRun, run_id)
    if not run:
        logger.error(f"ScrapeRun {run_id} 不存在")
        db.close()
        return

    current_user = db.query(User).filter(User.id == user_id).first()

    try:
        scrapers = ScraperRegistry.all()
        day = date.today()
        logger.info(f"开始抓取 run_id={run_id}，共 {len(scrapers)} 个站点")

        for scraper in scrapers:
            site_stat = {"fetched": 0, "created": 0, "skipped": 0, "failed": 0}
            try:
                raw_list = scraper.fetch_with_retry(day)
                site_stat["fetched"] = len(raw_list)
                logger.info(f"[{scraper.name}] 抓取到 {len(raw_list)} 条")

                for raw in raw_list:
                    _try_process_one(db, run, scraper, raw, site_stat, current_user)

                run.sites_summary = {**(run.sites_summary or {}), scraper.name: site_stat}
                db.commit()
            except SiteFetchError as e:
                run.error_summary = {**(run.error_summary or {}), scraper.name: str(e)}
                logger.warning(f"[{scraper.name}] 站点级失败: {e}")
                db.commit()

        run.status = _derive_run_status(run)
        run.finished_at = datetime.now()
        db.commit()
        logger.info(
            f"抓取完成 run_id={run_id} status={run.status} "
            f"created={run.created_count} skipped={run.skipped_count} failed={run.failed_count}"
        )
    except Exception as e:
        logger.exception(f"run_scraper 崩溃 run_id={run_id}")
        run.status = "failed"
        run.error_summary = {**(run.error_summary or {}), "system": f"run_scraper crashed: {e}"}
        run.finished_at = datetime.now()
        db.commit()
    finally:
        db.close()


def _try_process_one(db, run, scraper, raw, site_stat, current_user):
    """处理单条 raw 公告。"""
    try:
        item = scraper.normalize(raw)
    except Exception as e:
        _record_failure(db, run, scraper.name, raw, f"normalize 失败: {e}")
        site_stat["failed"] += 1
        logger.exception(f"[{scraper.name}] normalize 失败")
        return

    if item is None:
        return  # 被关键词/地区过滤

    try:
        created = _process_item(db, run, item, scraper.name, current_user)
        if created:
            site_stat["created"] += 1
        else:
            site_stat["skipped"] += 1
    except Exception as e:
        db.rollback()
        _record_failure(db, run, scraper.name, item, str(e))
        site_stat["failed"] += 1
        logger.exception(f"[{scraper.name}] process_item 失败")


def _process_item(db, run, item: ScrapeItem, source: str, current_user) -> bool:
    """返回 True=created, False=skipped。"""
    dup = _find_duplicate(db, item)
    if dup:
        skip_reason = (
            f"external_no 重复 (project_id={dup.id})"
            if item.external_no and dup.external_no == item.external_no
            else f"项目名称重复 (project_id={dup.id})"
        )
        _log_item(db, run, item, source, "skipped", skip_reason=skip_reason)
        run.skipped_count += 1
        run.total_count += 1
        return False

    bidding_unit_id, _ = match_or_create_org(item.bidding_unit_name, db, current_user)
    agency_id, _ = match_or_create_org(item.agency_name, db, current_user)
    platform_id, _ = match_or_create_platform(item.publish_platform_name, db, current_user)

    desc = item.description or ""
    if item.external_no:
        desc = f"项目编号: {item.external_no}\n" + desc

    project = ProjectInfo(
        bidding_type=item.bidding_type,
        project_name=item.project_name,
        bidding_unit_id=bidding_unit_id,
        agency_id=agency_id,
        publish_platform_id=platform_id,
        region=item.region or "",
        external_no=item.external_no,
        source=source,
        source_url=item.source_url or "",
        budget_amount=item.budget_amount or 0,
        registration_deadline=item.registration_deadline,
        bid_deadline=item.bid_deadline,
        description=desc,
        status=ProjectStatus.following,
    )
    db.add(project)
    db.flush()

    _log_item(db, run, item, source, "created", project_id=project.id)
    run.created_count += 1
    run.total_count += 1
    return True


def _find_duplicate(db, item: ScrapeItem) -> ProjectInfo | None:
    """项目编号优先，名称兜底。"""
    if item.external_no:
        dup = (
            db.query(ProjectInfo)
            .filter(ProjectInfo.external_no == item.external_no)
            .first()
        )
        if dup:
            return dup
    if item.project_name:
        dup = (
            db.query(ProjectInfo)
            .filter(ProjectInfo.project_name == item.project_name)
            .first()
        )
        if dup:
            return dup
    return None


def _log_item(
    db, run, item: ScrapeItem, source: str, result: str,
    project_id: int = None, skip_reason: str = None, error_message: str = None,
):
    """写 scrape_item_logs 一行。"""
    log = ScrapeItemLog(
        run_id=run.id,
        source=source,
        external_no=item.external_no if isinstance(item, ScrapeItem) else None,
        project_name=item.project_name if isinstance(item, ScrapeItem) else str(item),
        source_url=item.source_url if isinstance(item, ScrapeItem) else None,
        result=result,
        project_id=project_id,
        skip_reason=skip_reason,
        error_message=error_message,
    )
    db.add(log)
    db.commit()


def _record_failure(db, run, source: str, item_or_raw, error_message: str):
    """记录失败项。"""
    if isinstance(item_or_raw, ScrapeItem):
        project_name = item_or_raw.project_name
        source_url = item_or_raw.source_url
        external_no = item_or_raw.external_no
    else:
        project_name = (
            item_or_raw.get("title") or item_or_raw.get("projectName")
            or item_or_raw.get("bulletinTitle") or ""
        )
        source_url = item_or_raw.get("url") or item_or_raw.get("source_url")
        external_no = item_or_raw.get("prjNo") or item_or_raw.get("articleId")

    log = ScrapeItemLog(
        run_id=run.id,
        source=source,
        external_no=external_no,
        project_name=project_name,
        source_url=source_url,
        result="failed",
        error_message=error_message,
    )
    db.add(log)
    run.failed_count += 1
    run.total_count += 1
    db.commit()


def _derive_run_status(run: ScrapeRun) -> str:
    """根据 error_summary 推导最终状态。"""
    site_failures = {k: v for k, v in (run.error_summary or {}).items() if k != "system"}
    total_sites = 4
    if len(site_failures) >= total_sites:
        return "failed"
    if len(site_failures) > 0:
        return "partial"
    return "success"
