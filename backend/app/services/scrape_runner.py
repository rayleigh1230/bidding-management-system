"""抓取主流程：遍历所有 scraper → 关键词分类 → LLM 灰度精筛 → 去重 → 创建项目。

三阶段流水线（站点级批量并发）：
  阶段 1：normalize + is_result_announcement 过滤 + 关键词三态分类（串行）
            white → 入 white_items
            grey  → 入 grey_items（等阶段 2 LLM 精筛）
            reject → 直接 skipped 记日志
  阶段 2：grey_items 批量并发调 LLM（ThreadPoolExecutor）
            ENABLE_LLM_FILTER=false → grey 全部 reject
            LLM 单条异常 → fallback 为 white（保留）
  阶段 3：white_items + grey 通过项 → 去重 + 入库（串行）
"""
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, date, timedelta

from ..core.config import settings
from ..core.database import SessionLocal
from ..models.project import ProjectInfo, ProjectStatus
from ..models.scrape import ScrapeRun, ScrapeItemLog
from ..models.user import User
from ..scrapers import ScraperRegistry
from ..scrapers.base import (
    ScrapeItem, SiteFetchError, classify_by_keyword,
    is_correction_announcement, strip_correction_keyword, derive_correction_notice,
)
from .org_matcher import match_or_create_org, match_or_create_platform

logger = logging.getLogger(__name__)

# 这类 scraper 整分类抓取、不经关键词/LLM 筛选（中介超市等）
SKIP_CLASSIFY_SCRAPERS = {"jhzjcs"}

# 每次抓取回溯的天数（含今天）。跨日重复由 _create_one 的 external_no 去重兜底。
LOOKBACK_DAYS = 3


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
        # 抓取最近 LOOKBACK_DAYS 天（含今天）— 每个站点逐日 fetch 后合并，
        # 跨日重复由 _create_one 的 external_no 去重兜底。
        today = date.today()
        days = [today - timedelta(days=i) for i in range(LOOKBACK_DAYS)]
        logger.info(f"开始抓取 run_id={run_id}，共 {len(scrapers)} 个站点，回溯 {LOOKBACK_DAYS} 天 {days}")

        for scraper in scrapers:
            site_stat = {"fetched": 0, "created": 0, "skipped": 0, "failed": 0}
            try:
                raw_list = []
                day_errors = []
                # SKIP_CLASSIFY_SCRAPERS（如 jhzjcs）整分类抓全量、不按日过滤，
                # 只需调一次即可覆盖回溯窗口内的全部新公告。
                fetch_days = [today] if scraper.name in SKIP_CLASSIFY_SCRAPERS else days
                for d in fetch_days:
                    try:
                        raw_list.extend(scraper.fetch_with_retry(d))
                    except SiteFetchError as e:
                        day_errors.append(f"{d}: {e}")
                # 全部天数都失败才记站点级错误；部分成功则继续处理拿到的数据
                if len(day_errors) == len(fetch_days):
                    raise SiteFetchError(f"{scraper.name} 连续 {len(fetch_days)} 次抓取全部失败: " + " | ".join(day_errors))
                elif day_errors:
                    logger.warning(f"[{scraper.name}] 部分天数失败: {day_errors}")

                site_stat["fetched"] = len(raw_list)
                logger.info(f"[{scraper.name}] 抓取到 {len(raw_list)} 条（{LOOKBACK_DAYS} 天合计）")

                skip_classify = scraper.name in SKIP_CLASSIFY_SCRAPERS

                # 阶段 1：normalize + 关键词分类
                white_items: list[ScrapeItem] = []
                grey_items: list[ScrapeItem] = []
                for raw in raw_list:
                    _classify_one(
                        db, run, scraper, raw, site_stat,
                        skip_classify, white_items, grey_items,
                    )

                # 阶段 2：grey 批量 LLM 精筛
                _process_grey_batch(db, run, scraper, site_stat, grey_items)

                # 阶段 3：入库（white + LLM 通过的 grey）
                for item in white_items + grey_items:
                    _create_one(db, run, scraper, site_stat, current_user, item)

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


# === 阶段 1：normalize + 关键词分类 ===

def _classify_one(
    db, run, scraper, raw, site_stat,
    skip_classify: bool,
    white_items: list, grey_items: list,
):
    """单条 raw：normalize → 关键词分类。
    skip_classify=True 时（如中介超市）直接走 white_items，不经关键词/LLM。"""
    try:
        item = scraper.normalize(raw)
    except Exception as e:
        _record_failure(db, run, scraper.name, raw, f"normalize 失败: {e}")
        site_stat["failed"] += 1
        logger.exception(f"[{scraper.name}] normalize 失败")
        return

    if item is None:
        return  # normalize 内部过滤（is_result_announcement / region 等）

    # 更正/变更/补遗/澄清/延期类后续公告：尝试关联到原项目（更新 correction_url/notice）
    # 找不到原项目才 skip。这类公告 external_no 与原公告不同，单纯去重拦不住。
    if is_correction_announcement(item.project_name):
        attached = _attach_correction_to_original(db, run, item, scraper.name)
        if attached:
            site_stat["created"] += 1  # 视作一次成功处理（更新到原项目）
        else:
            _log_item(
                db, run, item, scraper.name, "skipped",
                skip_reason="更正公告未匹配到原项目",
            )
            site_stat["skipped"] += 1
            run.skipped_count += 1
            run.total_count += 1
        return

    if skip_classify:
        white_items.append(item)
        return

    decision = classify_by_keyword(item.project_name)
    if decision == "white":
        white_items.append(item)
    elif decision == "grey":
        grey_items.append(item)
    else:  # reject
        _log_item(
            db, run, item, scraper.name, "skipped",
            skip_reason="关键词拒绝（黑名单/不命中业务词）",
        )
        site_stat["skipped"] += 1
        run.skipped_count += 1
        run.total_count += 1


# === 更正公告关联原项目 ===

def _attach_correction_to_original(db, run, item: ScrapeItem, source: str) -> bool:
    """更正公告关联到原项目：更新 correction_url + correction_notice。

    匹配策略：剥离更正关键词后得到核心名，与现有项目名双向 LIKE 模糊匹配。
    命中多个时取 created_at 最新。找不到返回 False。
    """
    core = strip_correction_keyword(item.project_name)
    if len(core) < 6:
        # 太短的核心名容易误匹配，放弃
        logger.info(f"[更正关联] 核心名过短跳过: {item.project_name}")
        return False

    notice = derive_correction_notice(item.project_name)
    url = item.source_url or ""

    # 双向匹配：原项目名包含核心名 OR 核心名包含原项目名
    # SQL 层先用核心名做正向 LIKE 粗查（拿候选），Python 层做双向精筛
    candidates = (
        db.query(ProjectInfo)
        .filter(ProjectInfo.project_name.like(f"%{core}%"))
        .order_by(ProjectInfo.created_at.desc())
        .limit(20)
        .all()
    )
    matched = [p for p in candidates if core in p.project_name or p.project_name in core]
    if not matched:
        logger.info(f"[更正关联] 未匹配到原项目: {item.project_name} (核心={core})")
        return False

    target = matched[0]
    # 同一公告可能多次更正，覆盖为最新
    target.correction_url = url
    target.correction_notice = notice
    db.commit()
    logger.info(
        f"[更正关联] 关联到 project_id={target.id} "
        f"notice={notice} url={url[:60]}"
    )
    _log_item(
        db, run, item, source, "created",
        project_id=target.id,
        skip_reason=f"更正公告已关联到原项目 #{target.id}",
    )
    run.created_count += 1
    run.total_count += 1
    return True

def _process_grey_batch(db, run, scraper, site_stat, grey_items: list):
    """grey_items 批量并发 LLM 分类。
    ENABLE_LLM_FILTER=false → 全部 reject；LLM 异常单条 fallback 为 white。"""
    if not grey_items:
        return

    if not settings.ENABLE_LLM_FILTER:
        for item in grey_items:
            _log_item(
                db, run, item, scraper.name, "skipped",
                skip_reason="灰度拒绝（LLM 筛选已关闭）",
            )
            site_stat["skipped"] += 1
            run.skipped_count += 1
            run.total_count += 1
        grey_items.clear()
        return

    try:
        classifier = get_classifier()
    except Exception as e:
        # 分类器初始化失败（如未配 API key）：全部按 white fallback（宁多抓不漏抓）
        logger.warning(f"[{scraper.name}] LLM 分类器初始化失败，grey 全部 fallback=white: {e}")
        return

    def _one(item: ScrapeItem):
        try:
            decision, reason = classifier.classify(
                title=item.project_name,
                context=item.description or "",
                external_no=item.external_no,
            )
            return item, (decision, reason)
        except Exception as e:
            # 单条异常 fallback 为 white（保留）
            logger.warning(f"LLM 单条异常 fallback=white: {e}")
            return item, ("white", f"LLM 异常 fallback: {type(e).__name__}")

    concurrency = max(1, settings.LLM_CONCURRENCY)
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        results = list(pool.map(_one, grey_items))

    passed: list[ScrapeItem] = []
    for item, (decision, reason) in results:
        if decision == "white":
            passed.append(item)
        else:
            _log_item(
                db, run, item, scraper.name, "skipped",
                skip_reason=f"LLM 拒绝: {reason}",
            )
            site_stat["skipped"] += 1
            run.skipped_count += 1
            run.total_count += 1

    grey_items.clear()
    grey_items.extend(passed)


# === 阶段 3：去重 + 入库 ===

def _create_one(db, run, scraper, site_stat, current_user, item: ScrapeItem):
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
    total_sites = 6  # ccgp / ggzy / jhygcg / jhzjcs / jhggzy / zcy
    if len(site_failures) >= total_sites:
        return "failed"
    if len(site_failures) > 0:
        return "partial"
    return "success"


# 延迟导入避免循环依赖（classifier 依赖 settings，本模块也依赖 settings）
def get_classifier():
    from .classifier import get_classifier as _get
    return _get()
