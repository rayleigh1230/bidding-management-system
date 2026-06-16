"""金华中介超市 — Playwright + 系统 Chrome（API 响应拦截）。
站点 URL: https://jhzjcs.ggzyjy.jinhua.gov.cn
SPA 站点，需真实浏览器渲染。从 XHR 响应中拦截 getComparePublicList 数据。
"""
import logging
import os
from datetime import date
from typing import Optional

from .base import (
    BaseScraper, ScrapeItem, match_keywords, is_result_announcement, parse_date_safe,
)

logger = logging.getLogger(__name__)

PAGE_URL = "https://jhzjcs.ggzyjy.jinhua.gov.cn/jhzjcs/jhzjcs/website/pages/comparison_public/comparison_public.html"
CHROME_PATH = "C:/Program Files/Google/Chrome/Application/chrome.exe"
TARGET_API_KEYWORD = "getComparePublicList"


class JhzjcsScraper(BaseScraper):
    name = "jhzjcs"
    requires_playwright = True

    def fetch(self, day: date) -> list[dict]:
        """启动 Chrome 访问页面，拦截 API 响应获取数据。"""
        import sys
        import asyncio
        from playwright.sync_api import sync_playwright

        results = []
        captured_responses = []

        # Windows 上 uvicorn 使用 SelectorEventLoop，不支持子进程，
        # Playwright 需要启动浏览器子进程，因此临时切换为 ProactorEventLoop
        old_policy = None
        if sys.platform == "win32":
            old_policy = asyncio.get_event_loop_policy()
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

        try:
            with sync_playwright() as p:
                launch_kwargs = {"headless": True, "timeout": self.REQUEST_TIMEOUT * 1000}
                if os.path.exists(CHROME_PATH):
                    launch_kwargs["executable_path"] = CHROME_PATH
                browser = p.chromium.launch(**launch_kwargs)
                page = browser.new_page()

                def on_response(resp):
                    if TARGET_API_KEYWORD in resp.url:
                        captured_responses.append(resp)

                page.on("response", on_response)

                try:
                    page.goto(PAGE_URL, timeout=self.REQUEST_TIMEOUT * 1000)
                    page.wait_for_timeout(8000)
                except Exception as e:
                    logger.warning(f"jhzjcs 页面加载超时（可能仍有数据）: {e}")

                for resp in captured_responses:
                    try:
                        body = resp.json()
                        records = self._extract_records(body)
                        results.extend(records)
                    except Exception as e:
                        logger.warning(f"jhzjcs 响应解析失败: {e}")

                browser.close()
        except Exception as e:
            logger.error(f"jhzjcs Playwright 失败: {type(e).__name__}: {e}", exc_info=True)
            raise
        finally:
            if old_policy is not None:
                asyncio.set_event_loop_policy(old_policy)

        return results

    def _extract_records(self, body) -> list[dict]:
        """从 API 响应 JSON 中提取记录列表。
        实际结构: body['custom']['dataList']
        """
        if isinstance(body, dict):
            # 主要路径: custom.dataList
            custom = body.get("custom")
            if isinstance(custom, dict):
                for sub_key in ("dataList", "list", "records", "rows", "items"):
                    if sub_key in custom and isinstance(custom[sub_key], list):
                        return custom[sub_key]
            # 容错: 其他常见嵌套结构
            for key in ("data", "result", "body"):
                if key in body:
                    inner = body[key]
                    if isinstance(inner, dict):
                        for sub_key in ("dataList", "list", "records", "rows", "items"):
                            if sub_key in inner and isinstance(inner[sub_key], list):
                                return inner[sub_key]
            for key in ("dataList", "list", "records", "rows", "items"):
                if key in body and isinstance(body[key], list):
                    return body[key]
        elif isinstance(body, list):
            return body
        return []

    def normalize(self, raw: dict) -> Optional[ScrapeItem]:
        title = (raw.get("projectName") or raw.get("title") or "").strip()
        if not title:
            return None
        # 中介超市的项目名是工程名，服务类型在 serveTitle，两者都检查关键词
        serve_title = (raw.get("serveTitle") or "").strip()
        combined_text = f"{title} {serve_title}"
        if not match_keywords(combined_text):
            return None
        if is_result_announcement(title):
            return None

        dept_name = raw.get("deptName") or None
        serve_title = raw.get("serveTitle") or None
        publish_time = raw.get("publishTime") or None
        publish_date = parse_date_safe(publish_time)

        # 中介超市是 SPA，用 guid 构造详情页链接
        guid = raw.get("guid") or raw.get("projectguid") or ""
        source_url = f"{PAGE_URL}?id={guid}" if guid else PAGE_URL

        return ScrapeItem(
            project_name=title,
            bidding_type="中介超市",
            bidding_unit_name=dept_name,
            publish_platform_name="金华中介超市",
            region='["浙江省","金华市"]',
            external_no=guid or None,
            source_url=source_url,
            publish_date=publish_date,
            description=(
                f"来源: jhzjcs.ggzyjy.jinhua.gov.cn\n"
                f"服务类型: {serve_title or ''}\n"
                f"业主: {dept_name or ''}"
            ),
        )
