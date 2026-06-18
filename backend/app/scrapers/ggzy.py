"""浙江省公共资源交易平台 — requests POST JSON API（带 WAF 绕过）。
站点 URL: https://ggzy.zj.gov.cn
覆盖 4 交易领域下各领域实际存在的业务相关公告类型，共 9 个数据源：
  工程建设: 招标公告(002001001) / 资格预审公告(002001002) / 招标文件公示(002001011)
  政府采购: 采购公告(002002001) / 竞争性磋商公告(002002005) / 竞争性谈判公告(002002006) / 询价公告(002002008)
  国企采购: 交易公告(002011001)  —— 该领域侧栏仅「交易公告/交易结果」2 类
  小额工程: 交易公告(002012001)  —— 该领域侧栏仅「交易公告/交易结果」2 类
注：各领域的公告类型体系不同，不能统一套同一组类型代码。
地区 infoc=33 = 浙江全省（前缀匹配 33 开头的 6 位地区代码）。
不传服务端 titlenew 关键词过滤（站点分词会漏抓），改为 1 次按日期拿全部，
本地 normalize 用 is_result_announcement 过滤（关键词过滤上移到 scrape_runner）。
"""
import logging
from datetime import date
from typing import Optional

import requests

from .base import (
    BaseScraper, ScrapeItem, is_result_announcement, parse_date_safe,
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

# 9 个数据源（categorynum, "领域-类型"）
# 各领域类型体系不同：工程建设 13 类细分、政府采购 8 类细分、国企采购/小额工程 仅 2 类
CATEGORIES = [
    # 工程建设
    ("002001001", "工程建设-招标公告"),
    ("002001002", "工程建设-资格预审公告"),
    ("002001011", "工程建设-招标文件公示"),
    # 政府采购
    ("002002001", "政府采购-采购公告"),
    ("002002005", "政府采购-竞争性磋商公告"),
    ("002002006", "政府采购-竞争性谈判公告"),
    ("002002008", "政府采购-询价公告"),
    # 国企采购（侧栏仅「交易公告」1 类业务相关）
    ("002011001", "国企采购-交易公告"),
    # 小额工程（侧栏仅「交易公告」1 类业务相关）
    ("002012001", "小额工程-交易公告"),
]

PAGE_SIZE = 100
MAX_PAGES = 10  # 单数据源最多翻 10 页 = 1000 条兜底


class GgzyScraper(BaseScraper):
    name = "ggzy"
    requires_playwright = False

    def fetch(self, day: date) -> list[dict]:
        """遍历 9 个数据源，每个按当天日期翻页拿全部，合并去重。"""
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
        seen_ids = set()

        for cat_num, cat_name in CATEGORIES:
            for page_idx in range(MAX_PAGES):
                pn = page_idx * PAGE_SIZE
                payload = {
                    "token": "", "pn": pn, "rn": PAGE_SIZE, "wd": "",
                    "fields": "title", "cnum": "001",
                    "sort": '{"webdate":"0"}', "cl": 200,
                    "condition": [
                        {"fieldName": "categorynum", "isLike": True, "likeType": 2, "equal": cat_num},
                        {"fieldName": "infoc", "isLike": True, "likeType": 2, "equal": "33"},
                    ],
                    "time": [{"fieldName": "webdate", "startTime": date_start, "endTime": date_end}],
                    "isBusiness": "1", "noParticiple": "0", "accuracy": "",
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
                    if not records:
                        break
                    for rec in records:
                        rid = rec.get("id") or rec.get("infoid") or rec.get("linkurl") or ""
                        if rid and rid not in seen_ids:
                            seen_ids.add(rid)
                            rec["_category"] = cat_name
                            results.append(rec)
                    # 不足一页说明已到末尾
                    if len(records) < PAGE_SIZE:
                        break
                except Exception as e:
                    logger.warning(f"ggzy {cat_name} 第 {page_idx+1} 页抓取失败: {e}")
                    break
            logger.info(f"ggzy {cat_name}: 累计 {len(results)} 条")

        return results

    def normalize(self, raw: dict) -> Optional[ScrapeItem]:
        title = (raw.get("title") or "").strip()
        if not title:
            return None
        if is_result_announcement(title):
            return None

        region_text = raw.get("infod") or ""
        region = f'["浙江省","{region_text}"]' if region_text else '["浙江省"]'

        webdate = raw.get("webdate") or ""
        publish_date = parse_date_safe(webdate)

        source_url = raw.get("url") or raw.get("linkurl") or None
        # ggzy API 返回相对路径，需拼接域名
        if source_url and source_url.startswith("/"):
            source_url = "https://ggzy.zj.gov.cn" + source_url

        category = raw.get("_category", "")

        return ScrapeItem(
            project_name=title,
            bidding_type="公开招标",
            publish_platform_name="浙江省公共资源交易平台",
            region=region,
            source_url=source_url,
            publish_date=publish_date,
            description=f"来源: ggzy.zj.gov.cn\n类别: {category}\n地区: {region_text}\n原始链接: {source_url or ''}",
        )
