"""金华市公共资源交易网 — requests GET AJAX API。
站点 URL: http://ggzyjy.jinhua.gov.cn
覆盖 11 县区分站 ×（预公告 + 招标公告 + 采购公告）= 33 个数据源。
站点仅 HTTP（HTTPS 返回 410 Gone），需 verify=False。
"""
import json
import logging
import re
from datetime import date
from typing import Optional

import requests
import urllib3

from .base import (
    BaseScraper, ScrapeItem,
    match_keywords, is_result_announcement, parse_date_safe,
)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
logger = logging.getLogger(__name__)

API_URL = "http://ggzyjy.jinhua.gov.cn/api-gateway/jpaas-publish-server/front/page/build/unit"
BASE_URL = "http://ggzyjy.jinhua.gov.cn"
WEB_ID = "3818"
TPL_SET_ID = "LpcyxkYSwRoJNKPT7EX2v"
TAG_ID = "概览信息列表"
PAGE_SIZE = 10
MAX_PAGES_PER_SOURCE = 30

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": BASE_URL,
    "X-Requested-With": "XMLHttpRequest",
    "Accept": "application/json",
}

# 33 个数据源（county, type, page_url）
SOURCES = [
    # 预公告（11）— 顶级栏目，URL 形如 /col/col<colId>/index.html
    ("市本级", "预公告", "/col/col1229840390/index.html"),
    ("婺城区", "预公告", "/col/col1229847283/index.html"),
    ("金东区", "预公告", "/col/col1229847286/index.html"),
    ("兰溪市", "预公告", "/col/col1229847305/index.html"),
    ("义乌市", "预公告", "/col/col1229847289/index.html"),
    ("东阳市", "预公告", "/col/col1229847292/index.html"),
    ("永康市", "预公告", "/col/col1229847296/index.html"),
    ("浦江县", "预公告", "/col/col1229847308/index.html"),
    ("武义县", "预公告", "/col/col1229847320/index.html"),
    ("磐安县", "预公告", "/col/col1229847312/index.html"),
    ("开发区", "预公告", "/col/col1229847325/index.html"),
    # 招标公告（11）— 子路径栏目，URL 形如 /col/col<parentColId>/<subCode>/index.html
    ("市本级", "招标公告", "/col/col1229633710/zbggbzlm20/index.html"),
    ("婺城区", "招标公告", "/col/col1229633750/zbggbzlm518/index.html"),
    ("金东区", "招标公告", "/col/col1229641886/zbggbzlm521/index.html"),
    ("兰溪市", "招标公告", "/col/col1229641981/zbggbzlm261/index.html"),
    ("义乌市", "招标公告", "/col/col1229641912/zbggbzlm525/index.html"),
    ("东阳市", "招标公告", "/col/col1229641936/zbggbzlm267/index.html"),
    ("永康市", "招标公告", "/col/col1229641958/zbggbzlm603/index.html"),
    ("浦江县", "招标公告", "/col/col1229642012/zbggbzlm844/index.html"),
    ("武义县", "招标公告", "/col/col1229642061/zbggbzlm137/index.html"),
    ("磐安县", "招标公告", "/col/col1229642033/zbggbzlm536/index.html"),
    ("开发区", "招标公告", "/col/col1229642081/zbggbzlm77/index.html"),
    # 采购公告（11）— 顶级栏目，URL 形如 /col/col<colId>/index.html
    ("市本级", "采购公告", "/col/col1229641558/index.html"),
    ("婺城区", "采购公告", "/col/col1229641872/index.html"),
    ("金东区", "采购公告", "/col/col1229641890/index.html"),
    ("兰溪市", "采购公告", "/col/col1229641985/index.html"),
    ("义乌市", "采购公告", "/col/col1229641916/index.html"),
    ("东阳市", "采购公告", "/col/col1229641940/index.html"),
    ("永康市", "采购公告", "/col/col1229641962/index.html"),
    ("浦江县", "采购公告", "/col/col1229642016/index.html"),
    ("武义县", "采购公告", "/col/col1229642065/index.html"),
    ("磐安县", "采购公告", "/col/col1229642037/index.html"),
    ("开发区", "采购公告", "/col/col1229642085/index.html"),
]


class JhggzyScraper(BaseScraper):
    name = "jhggzy"
    requires_playwright = False

    def __init__(self):
        self._page_id_cache = {}  # url -> pageId

    def _resolve_page_id(self, page_url: str) -> Optional[str]:
        """从栏目 URL 解析 AJAX API 所需的 pageId。
        - 顶级栏目 (/col/col<colId>/index.html): pageId = colId
        - 子路径栏目 (/col/col<parent>/<sub>/index.html): fetch 静态页解析 querydata
        """
        if page_url in self._page_id_cache:
            return self._page_id_cache[page_url]

        # 顶级栏目：URL 形如 /col/col<colId>/index.html，pageId 直接 = colId
        m = re.match(r"^/col/col(\d+)/index\.html$", page_url)
        if m:
            page_id = m.group(1)
            self._page_id_cache[page_url] = page_id
            return page_id

        # 子路径栏目：fetch 静态页，从 querydata 里解析哈希 pageId
        try:
            resp = requests.get(
                BASE_URL + page_url, headers=HEADERS,
                timeout=self.REQUEST_TIMEOUT, verify=False,
            )
            resp.raise_for_status()
            html = resp.text
            qd_match = re.search(r"querydata=\"([^\"]+)\"", html)
            if not qd_match:
                logger.warning(f"jhggzy 未在 {page_url} 找到 querydata")
                return None
            qd_str = qd_match.group(1).replace("'", '"')
            qd = json.loads(qd_str)
            page_id = qd.get("pageId")
            if page_id:
                self._page_id_cache[page_url] = str(page_id)
            return str(page_id) if page_id else None
        except Exception as e:
            logger.warning(f"jhggzy 解析 pageId 失败 {page_url}: {e}")
            return None

    @staticmethod
    def _parse_html_items(html_frag: str) -> list:
        """解析 AJAX API 返回的 HTML 片段为 [{title, url, publish_date}, ...]。"""
        raise NotImplementedError("Task 3 实现")

    def _fetch_source(self, page_id: str, date_str: str) -> list:
        """翻页调用 AJAX API，返回 publish_date == date_str 的原始记录。"""
        raise NotImplementedError("Task 4 实现")

    def fetch(self, day: date) -> list:
        """遍历 33 个数据源，返回原始记录（含 _county / _type 元字段）。"""
        raise NotImplementedError("Task 5 实现")

    def normalize(self, raw: dict) -> Optional[ScrapeItem]:
        """原始记录 → ScrapeItem。返回 None 表示过滤掉。"""
        raise NotImplementedError("Task 5 实现")
