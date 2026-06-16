"""金华中介超市 — Playwright + 系统 Chrome（API 响应拦截）。
站点 URL: https://jhzjcs.ggzyjy.jinhua.gov.cn
SPA 站点，需真实浏览器渲染。从 XHR 响应中拦截 getComparePublicList 数据。
"""
import logging
import os
from datetime import date
from typing import Optional

from .base import (
    BaseScraper, ScrapeItem, match_keywords, parse_date_safe,
)

logger = logging.getLogger(__name__)

PAGE_URL = "https://jhzjcs.ggzyjy.jinhua.gov.cn/jhzjcs/jhzjcs/website/pages/default/index"
CHROME_PATH = "C:/Program Files/Google/Chrome/Application/chrome.exe"
TARGET_API_KEYWORD = "getComparePublicList"


class JhzjcsScraper(BaseScraper):
    name = "jhzjcs"
    requires_playwright = True

    def fetch(self, day: date) -> list[dict]:
        """启动 Chrome 访问页面，拦截 API 响应获取数据。"""
        from playwright.sync_api import sync_playwright

        results = []
        captured_responses = []

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
                page.wait_for_timeout(5000)
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

        return results

    def _extract_records(self, body) -> list[dict]:
        """从 API 响应 JSON 中提取记录列表（容错多种结构）。"""
        if isinstance(body, dict):
            for key in ("data", "result", "body"):
                if key in body:
                    inner = body[key]
                    if isinstance(inner, dict):
                        for sub_key in ("list", "records", "rows", "items"):
                            if sub_key in inner and isinstance(inner[sub_key], list):
                                return inner[sub_key]
            for key in ("list", "records", "rows", "items"):
                if key in body and isinstance(body[key], list):
                    return body[key]
        elif isinstance(body, list):
            return body
        return []

    def normalize(self, raw: dict) -> Optional[ScrapeItem]:
        title = (raw.get("projectName") or raw.get("title") or "").strip()
        if not title:
            return None
        if not match_keywords(title):
            return None

        dept_name = raw.get("deptName") or None
        serve_title = raw.get("serveTitle") or None
        publish_time = raw.get("publishTime") or None
        publish_date = parse_date_safe(publish_time)

        return ScrapeItem(
            project_name=title,
            bidding_type="中介超市",
            bidding_unit_name=dept_name,
            publish_platform_name="金华中介超市",
            region='["浙江省","金华市"]',
            publish_date=publish_date,
            description=(
                f"来源: jhzjcs.ggzyjy.jinhua.gov.cn\n"
                f"服务类型: {serve_title or ''}\n"
                f"业主: {dept_name or ''}"
            ),
        )
