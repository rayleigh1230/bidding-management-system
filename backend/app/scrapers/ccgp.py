"""中国政府采购网 — scrapling Fetcher（curl_cffi 浏览器指纹）。
站点 URL: http://search.ccgp.gov.cn/bxsearch
"""
import re
import logging
from datetime import date
from typing import Optional

from .base import (
    BaseScraper, ScrapeItem, is_result_announcement, match_region_zhejiang,
    extract_region_from_text,
)

logger = logging.getLogger(__name__)

SEARCH_URL = "http://search.ccgp.gov.cn/bxsearch"
SEARCH_KEYWORDS = ["检测", "人防", "防雷", "勘察", "测绘", "监测", "鉴定", "试验", "定检", "年检"]

LIST_RE = re.compile(
    r'<a[^>]*href="(http://www\.ccgp\.gov\.cn/[^"]+)"[^>]*>\s*([^<]{6,}?)\s*</a>'
)


class CcgpScraper(BaseScraper):
    name = "ccgp"
    requires_playwright = False

    def fetch(self, day: date) -> list[dict]:
        """逐关键词搜索当日公开招标公告。"""
        from scrapling.fetchers import Fetcher

        date_str = day.strftime("%Y:%m:%d")
        results = []
        seen_urls = set()

        for kw in SEARCH_KEYWORDS:
            params = (
                f"?searchtype=1&page_index=1&bidSort=0&pinMu=0"
                f"&bidType=1&dbSelect=bidx"
                f"&kw={kw}&start_time={date_str}&end_time={date_str}"
                f"&timeType=6&displayZone=&zoneId=&pppStatus=0&agentName="
            )
            url = SEARCH_URL + params
            try:
                page = Fetcher.get(url, impersonate="chrome", verify=False, timeout=15)
                html = page.html_content or ""
                for match in LIST_RE.finditer(html):
                    link, title = match.group(1), match.group(2).strip()
                    if link in seen_urls:
                        continue
                    seen_urls.add(link)
                    results.append({"url": link, "title": title, "_keyword": kw})
            except Exception as e:
                logger.warning(f"ccgp 关键词 '{kw}' 搜索失败: {e}")
                continue

        return results

    def normalize(self, raw: dict) -> Optional[ScrapeItem]:
        title = (raw.get("title") or "").strip()
        if not title:
            return None
        if is_result_announcement(title):
            return None

        source_url = raw.get("url")

        if not match_region_zhejiang(title):
            return None

        # 从标题提取市/县区，提取不到就留空（不再硬编码 浙江省）
        region = extract_region_from_text(title)

        return ScrapeItem(
            project_name=title,
            bidding_type="公开招标",
            publish_platform_name="中国政府采购网",
            region=region,
            source_url=source_url,
            publish_date=None,
            description=f"来源: ccgp.gov.cn\n关键词: {raw.get('_keyword','')}\n原始链接: {source_url or ''}",
        )
