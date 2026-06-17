"""金华市阳光采购服务平台 — requests POST JSON API。
站点 URL: https://www.jhygcg.com
所有数据均在金华市内，无需额外地域过滤。
"""
import logging
from datetime import date
from typing import Optional

import requests

from .base import (
    BaseScraper, ScrapeItem, match_keywords, is_result_announcement, parse_date_safe,
)

logger = logging.getLogger(__name__)

SEARCH_URL = "https://www.jhygcg.com/siteapi/api/Portal/GetSearchInfo"
HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.jhygcg.com/home",
}

SEARCH_KEYWORDS = ["检测", "人防", "防雷", "勘察", "测绘", "监测", "鉴定", "试验", "定检", "年检"]


class JhygcgScraper(BaseScraper):
    name = "jhygcg"
    requires_playwright = False

    def fetch(self, day: date) -> list[dict]:
        """按关键词搜索当日采购公告，合并去重。"""
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        results = []
        seen_ids = set()
        date_str = day.strftime("%Y-%m-%d")

        for kw in SEARCH_KEYWORDS:
            try:
                payload = {
                    "keyword": kw,
                    "pageIndex": 1,
                    "pageSize": 50,
                    "classID": "21",
                }
                resp = requests.post(
                    SEARCH_URL, json=payload, headers=HEADERS,
                    timeout=self.REQUEST_TIMEOUT, verify=False,
                )
                resp.raise_for_status()
                data = resp.json()
                items = (
                    data.get("body", {}).get("data", {}).get("searchList", [])
                    or []
                )
                for item in items:
                    article_id = item.get("articleId", "")
                    pub_date_raw = item.get("publishDate", "")
                    pub_date = parse_date_safe(pub_date_raw)
                    if pub_date and pub_date.strftime("%Y-%m-%d") != date_str:
                        continue
                    if article_id and article_id not in seen_ids:
                        seen_ids.add(article_id)
                        item["_keyword"] = kw
                        results.append(item)
            except Exception as e:
                logger.warning(f"jhygcg 关键词 '{kw}' 搜索失败: {e}")
                continue

        return results

    def normalize(self, raw: dict) -> Optional[ScrapeItem]:
        title = (raw.get("title") or raw.get("bulletinTitle") or "").strip()
        if not title:
            return None
        # API 混有采购结果(classId=24)和成交候选人(classId=22)，只保留采购公告(classId=21)
        class_id = str(raw.get("classId", ""))
        if class_id and class_id != "21":
            return None
        if not match_keywords(title):
            return None
        if is_result_announcement(title):
            return None

        publish_date = parse_date_safe(raw.get("publishDate"))
        article_id = raw.get("articleId", "")
        external_no = raw.get("prjNo") or article_id or None
        region = '["浙江省","金华市"]'
        source_url = f"https://www.jhygcg.com/detail?bulletinId={article_id}" if article_id else None

        return ScrapeItem(
            project_name=title,
            bidding_type="公开招标",
            publish_platform_name="金华市阳光采购服务平台",
            region=region,
            external_no=external_no,
            source_url=source_url,
            publish_date=publish_date,
            description=f"来源: jhygcg.com\n关键词: {raw.get('_keyword','')}\n原始链接: {source_url or ''}",
        )
