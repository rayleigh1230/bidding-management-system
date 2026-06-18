"""金华中介超市 — requests POST JSON API。
站点 URL: https://jhzjcs.ggzyjy.jinhua.gov.cn
直接调用 getComparePublicList API，按工程检验检测分类获取全部项目。
"""
import logging
from datetime import date
from typing import Optional

import requests

from .base import (
    BaseScraper, ScrapeItem, is_result_announcement, parse_date_safe,
    extract_region_from_text,
)

logger = logging.getLogger(__name__)

API_URL = "https://jhzjcs.ggzyjy.jinhua.gov.cn/jhzjcs/rest/jhzjcsprojectnotice/getComparePublicList"
PAGE_URL = "https://jhzjcs.ggzyjy.jinhua.gov.cn/jhzjcs/jhzjcs/website/pages/comparison_public/comparison_public.html"
HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": PAGE_URL,
}

# 工程检验检测（房建、市政、交通、水利）分类 ID
CATEGORY_ID = "6bbd9b33-ad3b-4c7a-a689-4365326f2626"


class JhzjcsScraper(BaseScraper):
    name = "jhzjcs"
    requires_playwright = False

    def fetch(self, day: date) -> list[dict]:
        """调用 API 获取工程检验检测分类下的全部比选项目。"""
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        payload = {
            "token": "Epoint_WebSerivce_**##0601",
            "params": {
                "selectedOptionId": CATEGORY_ID,
                "projectState": "1",
                "keywords": "",
                "pageIndex": 0,
                "pageSize": 200,
                "orderField": "single",
                "orderSort": "desc",
                "searchType": "",
                "searchText": "",
                "timeRange": {},
                "choicedTags": [],
                "viewWay": "timeshaft",
                "agencytype": "10",
            },
        }

        try:
            resp = requests.post(
                API_URL, json=payload, headers=HEADERS,
                timeout=self.REQUEST_TIMEOUT, verify=False,
            )
            resp.raise_for_status()
            data = resp.json()
            records = data.get("custom", {}).get("dataList", []) or []
            return records
        except Exception as e:
            logger.warning(f"jhzjcs API 请求失败: {e}")
            raise

    def normalize(self, raw: dict) -> Optional[ScrapeItem]:
        title = (raw.get("projectName") or raw.get("title") or "").strip()
        if not title:
            return None
        # 工程检验检测分类下的项目全部保留，不做关键词过滤
        if is_result_announcement(title):
            return None

        dept_name = raw.get("deptName") or None
        serve_title = raw.get("serveTitle") or None
        publish_time = raw.get("publishTime") or None
        publish_date = parse_date_safe(publish_time)

        guid = raw.get("guid") or raw.get("projectguid") or ""
        source_url = f"{PAGE_URL}?id={guid}" if guid else PAGE_URL
        # 站点本身是金华市，优先从标题提取县区颗粒度，否则回退金华市
        region = extract_region_from_text(title) or '["浙江省","金华市"]'

        return ScrapeItem(
            project_name=title,
            bidding_type="中介超市",
            bidding_unit_name=dept_name,
            publish_platform_name="金华中介超市",
            region=region,
            external_no=guid or None,
            source_url=source_url,
            publish_date=publish_date,
            description=(
                f"来源: jhzjcs.ggzyjy.jinhua.gov.cn\n"
                f"服务类型: {serve_title or ''}\n"
                f"业主: {dept_name or ''}"
            ),
        )
