"""Scraper 抽象基类 + 共享数据结构 + 过滤 helper。"""
import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional


# 关键词：标题/描述含任一即保留（OR 逻辑）— 向后兼容，jhzjcs 等不用
KEYWORDS = [
    "检测", "人防", "防雷", "勘察", "测绘",
    "监测", "鉴定", "试验", "定检", "年检",
]

# === 三层关键词体系（用于 classify_by_keyword） ===
#
# 设计原则：我们是做建设工程的【检测/监测/勘察/测绘/鉴定】服务，
# 不是做工程本身。所以：
#   - 必须命中 CORE_SERVICE_KEYWORDS（业务动作词）才是潜在目标
#   - 纯「工程施工」「工程招标」类即使含「工程」「建筑」也要 reject
#   - 工程领域词（ENGINEERING_DOMAIN）只是加分项，决定 white 还是 grey

# 核心业务动作词 — 标题必须命中任一，否则直接 reject
# （这是我们实际在做的事：检测/监测/勘察/测绘/鉴定 等）
CORE_SERVICE_KEYWORDS = [
    "检测", "监测", "勘察", "测绘", "鉴定", "试验", "检验", "评估",
    "定检", "年检", "观测",
]

# 工程领域信号词 — 命中核心词 + 这些词 = 强工程业务，white
# （建筑/桥梁/道路 等工程实体 + 防雷/消防 等专项领域）
ENGINEERING_DOMAIN_KEYWORDS = [
    # 主体结构 / 土建
    "工程", "建筑", "桥梁", "隧道", "道路", "公路", "市政", "水利", "交通",
    "轨道", "地铁", "高铁", "机场", "码头", "港口", "管网", "管廊", "路基",
    "路面", "桥隧", "钢结构", "混凝土", "桩基", "地基", "基坑", "主体结构",
    "幕墙", "屋面", "楼板", "墙体", "边坡", "挡墙", "涵洞", "岩土",
    # 专项检测领域
    "防雷", "消防", "智能化", "弱电", "安防", "人防", "节能", "绿色建筑",
    "装配式", "保温", "防水", "防腐", "室内环境", "空气质量", "环境监测",
    "噪声", "振动", "变形", "沉降", "抗震", "可靠性",
    # 勘察测绘相关
    "地形", "地籍", "竣工", "验收",
]

# 黑名单 — 即使命中核心词也要 LLM 二次判断（grey）
BLACKLIST_KEYWORDS = [
    # 医学/医疗
    "医学", "医疗", "医院", "临床", "诊断", "核酸", "药品", "药材", "中药",
    "中医药", "血液", "细胞", "基因", "放射诊疗", "医疗器械", "病理",
    # 食品/农产品
    "食品", "农产品", "粮食", "蔬菜", "水果", "酒类", "饮料", "肉类", "水产",
    "茶叶", "饲料", "肥料", "农药残留", "保健品",
    # 商品/货物/办公
    "商品", "货物", "办公用品", "电脑", "打印机", "复印机", "家具", "家电",
    "电梯", "空调", "LED", "网络设备", "服务器", "信创", "软件采购",
    "车辆", "汽车", "新能源车", "报废",
    # 服务类
    "保洁", "保安", "物业", "绿化养护", "餐饮", "保险", "广告", "印刷",
    "法律服务", "劳务派遣", "审计", "财务",
    # 服装/轻工
    "服装", "校服", "纺织品",
]

# 浙江省下属市县关键词（用于地区判断）
ZHEJIANG_PLACES = [
    "浙江", "杭州", "宁波", "温州", "绍兴", "嘉兴", "湖州",
    "金华", "衢州", "台州", "丽水", "舟山", "义乌",
]

# 浙江省 11 市 → 下属县区全量映射（用于从标题/地区字段提取颗粒度到县区的 region）
ZHEJIANG_CITIES = {
    "杭州市": ["上城区", "拱墅区", "西湖区", "滨江区", "萧山区", "余杭区", "临平区",
              "钱塘区", "富阳区", "临安区", "桐庐县", "淳安县", "建德市"],
    "宁波市": ["海曙区", "江北区", "北仑区", "镇海区", "鄞州区", "奉化区",
              "余姚市", "慈溪市", "象山县", "宁海县"],
    "温州市": ["鹿城区", "龙湾区", "瓯海区", "洞头区", "乐清市", "瑞安市", "龙港市",
              "永嘉县", "平阳县", "苍南县", "文成县", "泰顺县"],
    "嘉兴市": ["南湖区", "秀洲区", "海宁市", "平湖市", "桐乡市", "嘉善县", "海盐县"],
    "湖州市": ["吴兴区", "南浔区", "德清县", "长兴县", "安吉县"],
    "绍兴市": ["越城区", "柯桥区", "上虞区", "诸暨市", "嵊州市", "新昌县"],
    "金华市": ["婺城区", "金东区", "兰溪市", "义乌市", "东阳市", "永康市",
              "浦江县", "武义县", "磐安县"],
    "衢州市": ["柯城区", "衢江区", "江山市", "龙游县", "常山县", "开化县"],
    "舟山市": ["定海区", "普陀区", "岱山县", "嵊泗县"],
    "台州市": ["椒江区", "黄岩区", "路桥区", "温岭市", "临海市", "玉环市",
              "三门县", "天台县", "仙居县"],
    "丽水市": ["莲都区", "龙泉市", "青田县", "缙云县", "遂昌县", "松阳县",
              "云和县", "庆元县", "景宁畲族自治县"],
}

# 县区 → 市反向映射
_COUNTY_TO_CITY = {
    county: city
    for city, counties in ZHEJIANG_CITIES.items()
    for county in counties
}


def extract_region_from_text(text: str) -> Optional[str]:
    """从文本中提取浙江省市县地区，返回 JSON 字符串如 '["浙江省","金华市","义乌市"]'。

    优先匹配县区级（精确），其次市级（含"市"字），最后市级简称（如"金华"）。
    未识别到任何地区信号时返回 None（调用方应将 region 留空）。
    """
    if not text:
        return None

    # 1. 县区级匹配（最精确，含所属市）
    for county, city in _COUNTY_TO_CITY.items():
        if county in text:
            return f'["浙江省","{city}","{county}"]'

    # 2. 市级全称匹配（"金华市"）
    for city in ZHEJIANG_CITIES:
        if city in text:
            return f'["浙江省","{city}"]'

    # 3. 市级简称匹配（"金华"），注意景宁县简称"景宁"
    for city in ZHEJIANG_CITIES:
        short = city[:-1]  # 去"市"
        if short in text:
            return f'["浙江省","{city}"]'

    return None


def match_keywords(text: str) -> bool:
    """标题/描述中包含任一关键词即匹配。"""
    if not text:
        return False
    return any(kw in text for kw in KEYWORDS)


def classify_by_keyword(text: str) -> str:
    """三态关键词分类。
    返回:
      "white"  — 命中核心业务词 + 工程领域词，且不在黑名单
      "grey"   — 命中核心业务词但无工程领域信号，或命中黑名单，需 LLM 二次判断
      "reject" — 未命中核心业务词（检测/监测/勘察/测绘/鉴定 等）

    核心原则：我们是做建设工程的【检测/监测/勘察/测绘/鉴定】服务，
    不是做工程本身。所以「XX 道路工程」「XX 建筑施工」这类纯工程施工类
    项目即使含「工程」「建筑」字样，没有核心业务动作词也要 reject。
    """
    if not text:
        return "reject"

    has_core = any(kw in text for kw in CORE_SERVICE_KEYWORDS)
    has_eng = any(kw in text for kw in ENGINEERING_DOMAIN_KEYWORDS)
    has_black = any(kw in text for kw in BLACKLIST_KEYWORDS)

    # 1. 未命中核心业务动作词 → 直接拒绝（纯工程施工/货物采购/服务等）
    if not has_core:
        return "reject"

    # 2. 命中黑名单 → grey，让 LLM 判断（如「医疗器械检测」）
    if has_black:
        return "grey"

    # 3. 核心 + 工程领域 = 强工程业务，white
    if has_eng:
        return "white"

    # 4. 只有核心词但无工程领域信号 → grey（如「质量检测」需 LLM 判断是否工程类）
    return "grey"


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
