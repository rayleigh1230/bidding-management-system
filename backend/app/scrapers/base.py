"""Scraper 抽象基类 + 共享数据结构 + 过滤 helper。"""
import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional


# 关键词：标题/描述含任一即保留（OR 逻辑）
KEYWORDS = [
    "检测", "人防", "防雷", "勘察", "测绘",
    "监测", "鉴定", "试验", "定检", "年检",
]

# 浙江省下属市县关键词（用于地区判断）
ZHEJIANG_PLACES = [
    "浙江", "杭州", "宁波", "温州", "绍兴", "嘉兴", "湖州",
    "金华", "衢州", "台州", "丽水", "舟山", "义乌",
]


def match_keywords(text: str) -> bool:
    """标题/描述中包含任一关键词即匹配。"""
    if not text:
        return False
    return any(kw in text for kw in KEYWORDS)


# 中标/结果类公告排除关键词：标题含这些词组说明是结果公示，不是招标公告
RESULT_KEYWORDS = [
    "中标公告", "中标结果", "中标候选人", "中标公示",
    "成交公告", "成交结果", "成交候选人", "成交公示",
    "开标记录", "开标结果",
    "结果公示", "结果公告", "结果记录",
    "废标公告", "流标公告", "终止公告",
    "合同公告", "合同公示",
]


def is_result_announcement(text: str) -> bool:
    """判断标题是否为中标/成交/结果类公告（应排除）。"""
    if not text:
        return False
    return any(kw in text for kw in RESULT_KEYWORDS)


def match_region_zhejiang(region_text: str = None, extra: dict = None) -> bool:
    """浙江地区判断。
    region_text: 标题/地区文本
    extra: 额外信号，如 {'zone_id': '330000', 'infoc': '330'}
    """
    # 金华阳光采购站点本身就是金华市，不需要额外判断
    if extra and extra.get("is_jinhua"):
        return True
    combined = (region_text or "")
    if extra:
        for v in extra.values():
            if isinstance(v, str):
                combined += " " + v
    if any(place in combined for place in ZHEJIANG_PLACES):
        return True
    # CCGP zoneId / GGZY infoc 以 330 开头
    if extra:
        zone = str(extra.get("zone_id", "") or "")
        infoc = str(extra.get("infoc", "") or "")
        if zone.startswith("330") or infoc.startswith("330"):
            return True
    return False


@dataclass
class ScrapeItem:
    """归一化后的单条招标公告。"""
    project_name: str
    bidding_type: str = "公开招标"
    bidding_unit_name: Optional[str] = None
    agency_name: Optional[str] = None
    publish_platform_name: Optional[str] = None
    region: Optional[str] = None  # JSON 字符串，如 '["浙江省","杭州市"]'
    external_no: Optional[str] = None
    source_url: Optional[str] = None
    budget_amount: Optional[float] = None
    registration_deadline: Optional[date] = None
    bid_deadline: Optional[date] = None
    publish_date: Optional[date] = None
    description: Optional[str] = None


class SiteFetchError(Exception):
    """站点级抓取失败异常。"""


class BaseScraper(ABC):
    """所有站点 Scraper 的抽象基类。"""
    name: str = ""
    requires_playwright: bool = False

    MAX_RETRIES = 3
    RETRY_DELAY = 2  # 秒
    REQUEST_TIMEOUT = 30  # 秒

    @abstractmethod
    def fetch(self, day: date) -> list[dict]:
        """抓取指定日期的原始公告列表（未归一化）。"""

    @abstractmethod
    def normalize(self, raw: dict) -> Optional[ScrapeItem]:
        """原始数据 → ScrapeItem。返回 None 表示过滤掉。"""

    def fetch_with_retry(self, day: date) -> list[dict]:
        """带重试的 fetch。3 次失败抛 SiteFetchError。"""
        last_err = None
        for attempt in range(self.MAX_RETRIES):
            try:
                return self.fetch(day)
            except Exception as e:
                last_err = e
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(self.RETRY_DELAY * (attempt + 1))
        raise SiteFetchError(
            f"{self.name} 连续 {self.MAX_RETRIES} 次失败: "
            f"{type(last_err).__name__}: {last_err}"
        )


def parse_date_safe(s: str, formats: list[str] = None) -> Optional[date]:
    """安全解析日期字符串，失败返回 None。"""
    if not s or not isinstance(s, str):
        return None
    s = s.strip()
    if not s:
        return None
    default_formats = [
        "%Y-%m-%d", "%Y/%m/%d", "%Y年%m月%d日",
        "%Y-%m-%dT%H:%M:%S", "%Y/%m/%d %H:%M:%S",
    ]
    for fmt in (formats or default_formats):
        try:
            return datetime.strptime(s[:len(s)], fmt).date()
        except (ValueError, IndexError):
            continue
    try:
        return datetime.strptime(s[:10], "%Y-%m-%d").date()
    except (ValueError, IndexError):
        return None
