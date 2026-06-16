"""浙江省公共资源交易平台 — requests POST JSON API（带 WAF 绕过）。
站点 URL: https://ggzy.zj.gov.cn
分类号 002001001 = 招标公告；地区 infoc=330 = 浙江全省。
"""
import logging
from datetime import date
from typing import Optional

import requests

from .base import (
    BaseScraper, ScrapeItem, match_keywords, is_result_announcement, parse_date_safe,
)

logger = logging.getLogger(__name__)

API_URL = "https://ggzy.zj.gov.cn/inteligentsearch/rest/esinteligentsearch/getFullTextDataNew"
PAGE_URL = "https://ggzy.zj.gov.cn/"

HEADERS = {
    "Content-Type": "application/json;charset=utf-8",
    "X-Requested-With": "XMLHttpRequest",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://ggzy.zj.gov.cn/",
    "Origin": "https://ggzy.zj.gov.cn",
}

SEARCH_KEYWORDS = ["检测", "人防", "防雷", "消防", "勘察", "测绘", "监测", "鉴定", "评估", "试验"]


class GgzyScraper(BaseScraper):
    name = "ggzy"
    requires_playwright = False

    def fetch(self, day: date) -> list[dict]:
        """逐关键词搜索招标公告，合并去重。"""
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        session = requests.Session()
        session.headers.update(HEADERS)
        try:
            session.get(PAGE_URL, timeout=self.REQUEST_TIMEOUT, verify=False)
        except Exception as e:
            logger.warning(f"ggzy 获取 cookie 失败（继续尝试）: {e}")

        date_start = f"{day.strftime('%Y-%m-%d')} 00:00:00"
        date_end = f"{day.strftime('%Y-%m-%d')} 23:59:59"

        results = []
        seen_urls = set()

        for kw in SEARCH_KEYWORDS:
            payload = {
                "token": "", "pn": 0, "rn": 20, "wd": "",
                "fields": "title", "cnum": "001",
                "sort": '{"webdate":"0"}', "cl": 200,
                "condition": [
                    {"fieldName": "categorynum", "isLike": True, "likeType": 2, "equal": "002001001"},
                    {"fieldName": "infoc", "isLike": True, "likeType": 2, "equal": "330"},
                    {"fieldName": "titlenew", "isLike": True, "likeType": 0, "equal": kw},
                ],
                "time": [{"fieldName": "webdate", "startTime": date_start, "endTime": date_end}],
                "isBusiness": "1", "noParticiple": "1", "accuracy": "",
                "highlights": "", "statistics": None, "unionCondition": None,
                "inc_wd": "", "exc_wd": "", "ssort": "title", "terminal": "",
                "searchRange": None,
            }
            try:
                resp = session.post(
                    API_URL, json=payload,
                    timeout=self.REQUEST_TIMEOUT, verify=False,
                )
                resp.raise_for_status()
                data = resp.json()
                records = data.get("result", {}).get("records", []) or []
                for rec in records:
                    url = rec.get("url") or rec.get("linkurl") or ""
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        rec["_keyword"] = kw
                        results.append(rec)
            except Exception as e:
                logger.warning(f"ggzy 关键词 '{kw}' 搜索失败: {e}")
                continue

        return results

    def normalize(self, raw: dict) -> Optional[ScrapeItem]:
        title = (raw.get("title") or "").strip()
        if not title:
            return None
        if not match_keywords(title):
            return None
        if is_result_announcement(title):
            return None

        region_text = raw.get("infod") or ""
        region = f'["浙江省","{region_text}"]' if region_text else '["浙江省"]'

        webdate = raw.get("webdate") or ""
        publish_date = parse_date_safe(webdate)

        source_url = raw.get("url") or raw.get("linkurl") or None

        return ScrapeItem(
            project_name=title,
            bidding_type="公开招标",
            publish_platform_name="浙江省公共资源交易平台",
            region=region,
            source_url=source_url,
            publish_date=publish_date,
            description=f"来源: ggzy.zj.gov.cn\n地区: {region_text}\n关键词: {raw.get('_keyword','')}\n原始链接: {source_url or ''}",
        )
