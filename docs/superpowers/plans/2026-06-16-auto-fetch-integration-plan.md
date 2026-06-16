# 招标信息自动抓取集成系统 — 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 `/scrape` skill 集成到系统中，实现 UI 按钮触发 → 后台抓取 4 站点 → 自动入库 + 历史追溯。

**Architecture:** 每站点一个 Scraper 模块（继承 `BaseScraper`）+ FastAPI BackgroundTasks 异步执行 + `scrape_runs`/`scrape_item_logs` 两表记录。前端轮询状态 + 历史页。

**Tech Stack:** FastAPI + SQLAlchemy + Vue 3 + Element Plus + scrapling/requests/playwright

**Spec:** `docs/superpowers/specs/2026-06-16-auto-fetch-integration-design.md`

**重要约定（本项目特有）：**
- 本项目**无测试套件**（CLAUDE.md 明确记录 "No tests"），所有验证采用手动方式（启动后端 + Swagger + 临时脚本）
- 所有中文输出，代码/路径/变量名用英文
- 提交信息用中文，前缀 `feat：` / `fix：` / `docs：`（注意是中文冒号）
- 绝不提交 `backend/data/`（含 app.db）、`backend/migrate_db.py`、`.superpowers/`
- 提交时用显式文件名 `git add file1 file2`，不用 `git add -A`

---

## Task 1: 创建 ScrapeRun + ScrapeItemLog 数据模型

**Files:**
- Create: `backend/app/models/scrape.py`

- [ ] **Step 1: 创建模型文件**

创建 `backend/app/models/scrape.py`：

```python
from datetime import datetime
from sqlalchemy import String, Text, DateTime, Integer, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column

from ..core.database import Base


class ScrapeRun(Base):
    __tablename__ = "scrape_runs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    finished_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    triggered_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="running")
    total_count: Mapped[int] = mapped_column(Integer, default=0)
    created_count: Mapped[int] = mapped_column(Integer, default=0)
    skipped_count: Mapped[int] = mapped_column(Integer, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, default=0)
    sites_summary: Mapped[str] = mapped_column(JSON, default={})
    error_summary: Mapped[str] = mapped_column(JSON, default={})


class ScrapeItemLog(Base):
    __tablename__ = "scrape_item_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("scrape_runs.id", ondelete="CASCADE"), nullable=False
    )
    source: Mapped[str] = mapped_column(String(50), default="")
    external_no: Mapped[str] = mapped_column(String(100), nullable=True)
    project_name: Mapped[str] = mapped_column(String(300), default="")
    source_url: Mapped[str] = mapped_column(String(500), nullable=True)
    result: Mapped[str] = mapped_column(String(20), default="")
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("project_infos.id"), nullable=True
    )
    skip_reason: Mapped[str] = mapped_column(String(200), nullable=True)
    error_message: Mapped[str] = mapped_column(Text, nullable=True)
    processed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
```

- [ ] **Step 2: 验证文件无语法错误**

Run: `cd backend && python -c "from app.models.scrape import ScrapeRun, ScrapeItemLog; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/models/scrape.py
git commit -m "feat：新增 ScrapeRun/ScrapeItemLog 数据模型"
```

---

## Task 2: ProjectInfo 模型加 3 个字段

**Files:**
- Modify: `backend/app/models/project.py:68-142`

- [ ] **Step 1: 在 ProjectInfo 模型 Section 1 区域加 3 个字段**

在 `backend/app/models/project.py` 中，找到 `created_at` / `updated_at` 字段所在位置（约 line 84-85），在其后（Section 2 注释之前）插入：

```python
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)
    # ---- 抓取来源 ----
    external_no: Mapped[str] = mapped_column(String(100), nullable=True)
    source: Mapped[str] = mapped_column(String(50), default="manual")
    source_url: Mapped[str] = mapped_column(String(500), default="")
```

- [ ] **Step 2: 在 `__table_args__` 中加索引**

找到 `__table_args__` 元组（约 line 134-142），在最后一个 `Index(...)` 后加：

```python
    __table_args__ = (
        Index('ix_project_status', 'status'),
        Index('ix_project_bidding_type', 'bidding_type'),
        Index('ix_project_bid_deadline', 'bid_deadline'),
        Index('ix_project_updated_at', 'updated_at'),
        Index('ix_project_has_deposit', 'has_deposit'),
        Index('ix_project_parent_project_id', 'parent_project_id'),
        Index('ix_project_is_multi_lot', 'is_multi_lot'),
        Index('ix_project_external_no', 'external_no'),
    )
```

- [ ] **Step 3: 验证无语法错误**

Run: `cd backend && python -c "from app.models.project import ProjectInfo; print(ProjectInfo.external_no, ProjectInfo.source, ProjectInfo.source_url)"`
Expected: `ProjectInfo.external_no ProjectInfo.source ProjectInfo.source_url`

- [ ] **Step 4: Commit**

```bash
git add backend/app/models/project.py
git commit -m "feat：ProjectInfo 加 external_no/source/source_url 字段"
```

---

## Task 3: main.py — 模型注册 + 字段迁移 + 孤儿清理

**Files:**
- Modify: `backend/app/main.py`

- [ ] **Step 1: 在 on_startup 的模型 import 中加 scrape**

找到 `on_startup` 函数中的 import 块（约 line 21-24），加 `scrape`：

```python
    from .models import (  # noqa: F401
        user, organization, platform, manager,
        project, operation_log, scrape,
    )
```

- [ ] **Step 2: 在 result_documents 迁移块之后加 3 个字段的迁移**

找到 `result_documents` 迁移块（约 line 74-80），在其后（`# Create default admin user` 之前）插入：

```python
    # Auto-migrate: add external_no/source/source_url columns to project_infos
    proj_columns = [col['name'] for col in inspector.get_columns('project_infos')]
    if 'external_no' not in proj_columns:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE project_infos ADD COLUMN external_no VARCHAR(100)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_project_external_no ON project_infos(external_no)"))
            conn.commit()
        print("Migration: added external_no column to project_infos")
    if 'source' not in proj_columns:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE project_infos ADD COLUMN source VARCHAR(50) DEFAULT 'manual'"))
            conn.commit()
        print("Migration: added source column to project_infos")
    if 'source_url' not in proj_columns:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE project_infos ADD COLUMN source_url VARCHAR(500) DEFAULT ''"))
            conn.commit()
        print("Migration: added source_url column to project_infos")
```

- [ ] **Step 3: 在 `# Create default admin user` 之前加孤儿 run 清理**

在 admin user 创建之前（约 line 82），插入：

```python
    # Cleanup orphan scrape runs from previous unclean shutdown
    from sqlalchemy.orm import Session
    from .models.scrape import ScrapeRun
    cleanup_db = Session(bind=engine)
    try:
        orphans = cleanup_db.query(ScrapeRun).filter(
            ScrapeRun.status == "running",
            ScrapeRun.finished_at.is_(None),
        ).all()
        for orphan in orphans:
            orphan.status = "failed"
            orphan.error_summary = {"system": "服务重启中断"}
            orphan.finished_at = datetime.now()
        if orphans:
            cleanup_db.commit()
            print(f"Cleanup: marked {len(orphans)} orphan scrape run(s) as failed")
    finally:
        cleanup_db.close()
```

注意：`datetime` 需要从 `datetime` 模块导入。文件顶部已有 `from sqlalchemy import text, inspect as sa_inspect`，但没有 `datetime`。在 import 区域加：

```python
from datetime import datetime
```

放在 `from fastapi import FastAPI` 之后。

- [ ] **Step 4: 启动后端验证迁移**

Run: `cd backend && python -c "from app.main import app; print('startup OK')"`
Expected: 看到 `Migration: added ...` 打印 + `startup OK`（如果数据库已有字段则不打印迁移）

- [ ] **Step 5: Commit**

```bash
git add backend/app/main.py
git commit -m "feat：main.py 注册 scrape 模型 + 迁移新字段 + 孤儿 run 清理"
```

---

## Task 4: scrapers/base.py — 抽象基类 + 过滤 helper

**Files:**
- Create: `backend/app/scrapers/__init__.py`（空文件 + ScraperRegistry）
- Create: `backend/app/scrapers/base.py`

- [ ] **Step 1: 创建 `__init__.py`（仅占位）**

创建 `backend/app/scrapers/__init__.py`，内容：

```python
"""招标信息抓取模块。"""
```

- [ ] **Step 2: 创建 `base.py`**

创建 `backend/app/scrapers/base.py`：

```python
"""Scraper 抽象基类 + 共享数据结构 + 过滤 helper。"""
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

import time


# 关键词：标题/描述含任一即保留（OR 逻辑）
KEYWORDS = [
    "检测", "人防", "防雷", "消防", "勘察", "测绘",
    "监测", "鉴定", "评估", "试验",
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
        raise SiteFetchError(f"{self.name} 连续 {self.MAX_RETRIES} 次失败: {last_err}")


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
            return datetime.strptime(s[:len(s)], fmt).date() if fmt == "%Y-%m-%d" else datetime.strptime(s[:19], fmt).date()
        except (ValueError, IndexError):
            continue
    # 尝试截取前 10 位
    try:
        return datetime.strptime(s[:10], "%Y-%m-%d").date()
    except (ValueError, IndexError):
        return None


# 用于 parse_date_safe 内部的 datetime 引用
from datetime import datetime
```

- [ ] **Step 3: 修复 parse_date_safe 的 datetime 引用顺序**

`datetime` 在 `parse_date_safe` 内部使用，但在文件末尾才导入。把 `from datetime import datetime` 移到文件顶部 `import time` 之后。同时简化 `parse_date_safe`：

将文件末尾的 `from datetime import datetime` 删除，在顶部 `import time` 后加：

```python
import time
from datetime import datetime, date
```

然后简化 `parse_date_safe` 函数体：

```python
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
            return datetime.strptime(s[:len(s)] if fmt in ("%Y-%m-%d",) else s[:len(s)], fmt).date()
        except (ValueError, IndexError):
            continue
    try:
        return datetime.strptime(s[:10], "%Y-%m-%d").date()
    except (ValueError, IndexError):
        return None
```

- [ ] **Step 4: 验证导入**

Run: `cd backend && python -c "from app.scrapers.base import BaseScraper, ScrapeItem, SiteFetchError, match_keywords, match_region_zhejiang; print('OK')"`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add backend/app/scrapers/__init__.py backend/app/scrapers/base.py
git commit -m "feat：scrapers/base.py 抽象基类 + 关键词/地区过滤 helper"
```

---

## Task 5: ScraperRegistry 注册中心

**Files:**
- Modify: `backend/app/scrapers/__init__.py`

- [ ] **Step 1: 重写 `__init__.py` 加入 ScraperRegistry**

将 `backend/app/scrapers/__init__.py` 内容替换为：

```python
"""招标信息抓取模块 + ScraperRegistry。"""


class ScraperRegistry:
    """站点 Scraper 注册中心。懒加载，避免 import 时立即初始化所有 scraper。"""
    _scrapers = None

    @classmethod
    def all(cls) -> list:
        """返回所有已注册的 scraper 实例列表。"""
        if cls._scrapers is None:
            cls._scrapers = cls._load_all()
        return cls._scrapers

    @classmethod
    def _load_all(cls) -> list:
        """实例化所有站点 scraper。延迟 import 避免循环依赖。"""
        scrapers = []
        try:
            from .ccgp import CcgpScraper
            scrapers.append(CcgpScraper())
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"CcgpScraper 加载失败: {e}")
        try:
            from .ggzy import GgzyScraper
            scrapers.append(GgzyScraper())
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"GgzyScraper 加载失败: {e}")
        try:
            from .jhygcg import JhygcgScraper
            scrapers.append(JhygcgScraper())
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"JhygcgScraper 加载失败: {e}")
        try:
            from .jhzjcs import JhzjcsScraper
            scrapers.append(JhzjcsScraper())
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"JhzjcsScraper 加载失败: {e}")
        return scrapers

    @classmethod
    def reload(cls):
        """强制重新加载（测试用）。"""
        cls._scrapers = None
```

注意：此时 ccgp/ggzy/jhygcg/jhzjcs 模块还未创建，import 会抛异常但被 try/except 捕获，返回空列表。这是预期行为。

- [ ] **Step 2: 验证不会崩溃**

Run: `cd backend && python -c "from app.scrapers import ScraperRegistry; print(len(ScraperRegistry.all()))"`
Expected: `0`（因为 4 个 scraper 模块还不存在，都被 try/except 跳过）

- [ ] **Step 3: Commit**

```bash
git add backend/app/scrapers/__init__.py
git commit -m "feat：ScraperRegistry 注册中心（懒加载 + 容错）"
```

---

## Task 6: jhygcg.py — 金华阳光采购（requests）

**Files:**
- Create: `backend/app/scrapers/jhygcg.py`

- [ ] **Step 1: 创建 scraper 文件**

创建 `backend/app/scrapers/jhygcg.py`：

```python
"""金华市阳光采购服务平台 — requests POST JSON API。
站点 URL: https://www.jhygcg.com
所有数据均在金华市内，无需额外地域过滤。
"""
import re
import logging
from datetime import date, datetime
from typing import Optional

import requests

from .base import (
    BaseScraper, ScrapeItem, match_keywords, parse_date_safe,
)

logger = logging.getLogger(__name__)

SEARCH_URL = "https://www.jhygcg.com/siteapi/api/Portal/GetSearchInfo"
HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.jhygcg.com/home",
}

# 关键词搜索列表（与 KEYWORDS 一致，逐个搜索后合并去重）
SEARCH_KEYWORDS = ["检测", "人防", "防雷", "消防", "勘察", "测绘", "监测", "鉴定", "评估", "试验"]


class JhygcgScraper(BaseScraper):
    name = "jhygcg"
    requires_playwright = False

    def fetch(self, day: date) -> list[dict]:
        """按关键词搜索当日采购公告，合并去重。"""
        results = []
        seen_ids = set()
        date_str = day.strftime("%Y-%m-%d")

        for kw in SEARCH_KEYWORDS:
            try:
                payload = {
                    "keyword": kw,
                    "pageIndex": 1,
                    "pageSize": 50,
                    "classID": "21",  # 采购公告
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
                    # 只保留当天的
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
        # 关键词过滤
        if not match_keywords(title):
            return None

        publish_date = parse_date_safe(raw.get("publishDate"))

        # 从标题中提取项目编号（如有）
        external_no = raw.get("prjNo") or raw.get("articleId") or None

        # 地区：金华市
        region = '["浙江省","金华市"]'

        # 原始链接
        source_url = f"https://www.jhygcg.com/home/bulletin/{raw.get('articleId','')}" if raw.get("articleId") else None

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
```

- [ ] **Step 2: 验证导入**

Run: `cd backend && python -c "from app.scrapers.jhygcg import JhygcgScraper; s=JhygcgScraper(); print(s.name, s.requires_playwright)"`
Expected: `jhygcg False`

- [ ] **Step 3: 验证 Registry 能加载**

Run: `cd backend && python -c "from app.scrapers import ScraperRegistry; ScraperRegistry.reload(); print([s.name for s in ScraperRegistry.all()])"`
Expected: `['jhygcg']`（其余 3 个还不存在）

- [ ] **Step 4: Commit**

```bash
git add backend/app/scrapers/jhygcg.py
git commit -m "feat：jhygcg scraper — 金华阳光采购（requests）"
```

---

## Task 7: ggzy.py — 浙江公共资源交易网（requests + WAF）

**Files:**
- Create: `backend/app/scrapers/ggzy.py`

- [ ] **Step 1: 创建 scraper 文件**

创建 `backend/app/scrapers/ggzy.py`：

```python
"""浙江省公共资源交易平台 — requests POST JSON API（带 WAF 绕过）。
站点 URL: https://ggzy.zj.gov.cn
分类号 002001003 = 招标公告；地区 infoc=330 = 浙江全省。
"""
import logging
from datetime import date, datetime
from typing import Optional

import requests

from .base import (
    BaseScraper, ScrapeItem, match_keywords, match_region_zhejiang,
    parse_date_safe,
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
        # 先访问首页获取 cookie（绕 WAF）
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
                    {"fieldName": "categorynum", "isLike": True, "likeType": 2, "equal": "002001003"},
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

        # GGZY 已限定 infoc=330（浙江），地区无需再判断
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
```

- [ ] **Step 2: 验证导入 + Registry**

Run: `cd backend && python -c "from app.scrapers import ScraperRegistry; ScraperRegistry.reload(); print([s.name for s in ScraperRegistry.all()])"`
Expected: `['jhygcg', 'ggzy']`

- [ ] **Step 3: Commit**

```bash
git add backend/app/scrapers/ggzy.py
git commit -m "feat：ggzy scraper — 浙江公共资源交易网（requests + WAF）"
```

---

## Task 8: ccgp.py — 中国政府采购网（scrapling）

**Files:**
- Create: `backend/app/scrapers/ccgp.py`

- [ ] **Step 1: 创建 scraper 文件**

创建 `backend/app/scrapers/ccgp.py`：

```python
"""中国政府采购网 — scrapling Fetcher（curl_cffi 浏览器指纹）。
站点 URL: http://search.ccgp.gov.cn/bxsearch
搜索时限定浙江省（zoneId=plplplplplplplplplplplplplplplplplplplplplplplplplplplplplplplpl — 实际不传，用结果中的地区字段过滤）。
"""
import re
import logging
from datetime import date
from typing import Optional

from .base import (
    BaseScraper, ScrapeItem, match_keywords, match_region_zhejiang,
    parse_date_safe,
)

logger = logging.getLogger(__name__)

SEARCH_URL = "http://search.ccgp.gov.cn/bxsearch"
SEARCH_KEYWORDS = ["检测", "人防", "防雷", "消防", "勘察", "测绘", "监测", "鉴定", "评估", "试验"]

# 列表页标题+链接正则
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
        if not match_keywords(title):
            return None

        source_url = raw.get("url")

        # CCGP 列表页无地区字段，标题中含浙江地名才保留
        if not match_region_zhejiang(title):
            return None

        return ScrapeItem(
            project_name=title,
            bidding_type="公开招标",
            publish_platform_name="中国政府采购网",
            region='["浙江省"]',
            source_url=source_url,
            publish_date=None,  # 列表页无日期，详情页才有
            description=f"来源: ccgp.gov.cn\n关键词: {raw.get('_keyword','')}\n原始链接: {source_url or ''}",
        )
```

- [ ] **Step 2: 安装 scrapling 依赖**

Run: `cd backend && pip install scrapling 2>&1 | tail -5`

如果安装失败（Windows 编译问题），记录错误，后续在 requirements.txt 中标注。scraper 内的 `from scrapling.fetchers import Fetcher` 在 `fetch()` 方法内延迟导入，不影响后端启动。

- [ ] **Step 3: 验证导入 + Registry（不实际抓取）**

Run: `cd backend && python -c "from app.scrapers import ScraperRegistry; ScraperRegistry.reload(); print([s.name for s in ScraperRegistry.all()])"`
Expected: `['jhygcg', 'ggzy', 'ccgp']`（如果 scrapling 未装，ccgp 加载失败则只有 `['jhygcg', 'ggzy']`）

- [ ] **Step 4: Commit**

```bash
git add backend/app/scrapers/ccgp.py
git commit -m "feat：ccgp scraper — 中国政府采购网（scrapling）"
```

---

## Task 9: jhzjcs.py — 金华中介超市（Playwright）

**Files:**
- Create: `backend/app/scrapers/jhzjcs.py`

- [ ] **Step 1: 创建 scraper 文件（Playwright 延迟导入）**

创建 `backend/app/scrapers/jhzjcs.py`：

```python
"""金华中介超市 — Playwright + 系统 Chrome（API 响应拦截）。
站点 URL: https://jhzjcs.ggzyjy.jinhua.gov.cn
SPA 站点，需真实浏览器渲染。从 XHR 响应中拦截 getComparePublicList 数据。
"""
import json
import logging
import os
from datetime import date
from typing import Optional

from .base import (
    BaseScraper, ScrapeItem, match_keywords,
)

logger = logging.getLogger(__name__)

PAGE_URL = "https://jhzjcs.ggzyjy.jinhua.gov.cn/jhzjcs/jhzjcs/website/pages/default/index"
CHROME_PATH = "C:/Program Files/Google/Chrome/Application/chrome.exe"
TARGET_API_KEYWORD = "getComparePublicList"  # 比选公告


class JhzjcsScraper(BaseScraper):
    name = "jhzjcs"
    requires_playwright = True

    def fetch(self, day: date) -> list[dict]:
        """启动 Chrome 访问页面，拦截 API 响应获取数据。"""
        # Playwright 延迟导入：未安装时仅此站点失败，不影响后端启动
        from playwright.sync_api import sync_playwright

        results = []
        captured_responses = []

        with sync_playwright() as p:
            launch_kwargs = {"headless": True, "timeout": self.REQUEST_TIMEOUT * 1000}
            # 优先用系统 Chrome
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
                page.wait_for_timeout(5000)  # 等 SPA 渲染 + API 请求
            except Exception as e:
                logger.warning(f"jhzjcs 页面加载超时（可能仍有数据）: {e}")

            # 解析捕获的响应
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
            # 常见结构: {data: {list: [...]}} 或 {result: {list: [...]}} 或直接 {list: [...]}
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

        dept_name = raw.get("deptName") or None  # 业主/招标单位
        serve_title = raw.get("serveTitle") or None  # 服务类型
        publish_time = raw.get("publishTime") or None

        from .base import parse_date_safe
        publish_date = parse_date_safe(publish_time)

        # 金华市，无需额外地区判断
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
```

- [ ] **Step 2: 验证导入（不启动 Chrome）**

Run: `cd backend && python -c "from app.scrapers.jhzjcs import JhzjcsScraper; s=JhzjcsScraper(); print(s.name, s.requires_playwright)"`
Expected: `jhzjcs True`

- [ ] **Step 3: 验证 Registry 全量加载**

Run: `cd backend && python -c "from app.scrapers import ScraperRegistry; ScraperRegistry.reload(); print([s.name for s in ScraperRegistry.all()])"`
Expected: `['jhygcg', 'ggzy', 'ccgp', 'jhzjcs']`（如果 scrapling 未装则没有 ccgp，如果 playwright 未装则 jhzjcs 仍能 import 但 fetch 时才报错）

- [ ] **Step 4: Commit**

```bash
git add backend/app/scrapers/jhzjcs.py
git commit -m "feat：jhzjcs scraper — 金华中介超市（Playwright + 系统 Chrome）"
```

---

## Task 10: services/org_matcher.py — 提取组织匹配 helper

**Files:**
- Create: `backend/app/services/org_matcher.py`

- [ ] **Step 1: 创建 org_matcher.py**

创建 `backend/app/services/org_matcher.py`：

```python
"""组织/平台匹配创建 helper — 供 documents.py 和 scrape_runner.py 共用。"""
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..models.organization import Organization
from ..models.platform import Platform
from ..schemas.dict import OrganizationCreate, PlatformCreate
from ..api.organizations import create_organization as _create_org
from ..api.platforms import create_platform as _create_platform


def match_or_create_org(
    name: str, db: Session, current_user
) -> tuple[int | None, str | None]:
    """按名称匹配组织，无匹配则创建 external 类型。返回 (org_id, matched_name)。"""
    name = (name or "").strip()
    if not name:
        return None, None
    existing = (
        db.query(Organization)
        .filter(
            or_(
                Organization.name == name,
                Organization.name.contains(name),
                Organization.short_name.contains(name),
            )
        )
        .first()
    )
    if existing:
        return existing.id, existing.name
    dup = db.query(Organization).filter(Organization.name == name).first()
    if dup:
        return dup.id, dup.name
    new_org = _create_org(
        OrganizationCreate(name=name, org_type="external"),
        db=db,
        current_user=current_user,
    )
    return new_org.id, new_org.name


def match_or_create_platform(
    name: str, db: Session, current_user
) -> tuple[int | None, str | None]:
    """按名称匹配平台，无匹配则创建。"""
    name = (name or "").strip()
    if not name:
        return None, None
    existing = (
        db.query(Platform)
        .filter(or_(Platform.name == name, Platform.name.contains(name)))
        .first()
    )
    if existing:
        return existing.id, existing.name
    dup = db.query(Platform).filter(Platform.name == name).first()
    if dup:
        return dup.id, dup.name
    new_pf = _create_platform(PlatformCreate(name=name), db=db, current_user=current_user)
    return new_pf.id, new_pf.name
```

- [ ] **Step 2: 修改 documents.py 复用共享 helper**

在 `backend/app/api/documents.py` 中：
1. 删除文件内的 `_match_or_create_org` 和 `_match_or_create_platform` 函数定义（约 line 65-114）
2. 在 import 区加：

```python
from ..services.org_matcher import match_or_create_org as _match_or_create_org
from ..services.org_matcher import match_or_create_platform as _match_or_create_platform
```

注意：这两个函数被 `_build_bidding_response` 和 `_build_result_response` 调用，函数签名完全一致，import 后原调用代码不需改动。

- [ ] **Step 3: 验证 documents.py 导入正常**

Run: `cd backend && python -c "from app.api.documents import router; print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/org_matcher.py backend/app/api/documents.py
git commit -m "refactor：提取 org_matcher.py 共享组织匹配 helper"
```

---

## Task 11: services/scrape_runner.py — 抓取主流程

**Files:**
- Create: `backend/app/services/scrape_runner.py`

- [ ] **Step 1: 创建 scrape_runner.py**

创建 `backend/app/services/scrape_runner.py`：

```python
"""抓取主流程：遍历所有 scraper → 去重 → 创建项目 → 记日志。"""
import logging
from datetime import datetime, date

from sqlalchemy.orm import Session

from ..core.database import SessionLocal
from ..models.project import ProjectInfo, ProjectStatus
from ..models.scrape import ScrapeRun, ScrapeItemLog
from ..models.user import User
from ..scrapers import ScraperRegistry
from ..scrapers.base import ScrapeItem, SiteFetchError
from .org_matcher import match_or_create_org, match_or_create_platform

logger = logging.getLogger(__name__)


def run_scraper(run_id: int, user_id: int):
    """主入口：由 BackgroundTasks 调用。串行跑所有站点。"""
    db = SessionLocal()
    run = db.get(ScrapeRun, run_id)
    if not run:
        logger.error(f"ScrapeRun {run_id} 不存在")
        db.close()
        return

    # 获取触发用户（用于 _create_org 的 current_user 参数）
    current_user = db.query(User).filter(User.id == user_id).first()

    try:
        scrapers = ScraperRegistry.all()
        day = date.today()
        logger.info(f"开始抓取 run_id={run_id}，共 {len(scrapers)} 个站点")

        for scraper in scrapers:
            site_stat = {"fetched": 0, "created": 0, "skipped": 0, "failed": 0}
            try:
                raw_list = scraper.fetch_with_retry(day)
                site_stat["fetched"] = len(raw_list)
                logger.info(f"[{scraper.name}] 抓取到 {len(raw_list)} 条")

                for raw in raw_list:
                    _try_process_one(db, run, scraper, raw, site_stat, current_user)

                run.sites_summary = {**(run.sites_summary or {}), scraper.name: site_stat}
                db.commit()
            except SiteFetchError as e:
                run.error_summary = {**(run.error_summary or {}), scraper.name: str(e)}
                logger.warning(f"[{scraper.name}] 站点级失败: {e}")
                db.commit()

        run.status = _derive_run_status(run)
        run.finished_at = datetime.now()
        db.commit()
        logger.info(
            f"抓取完成 run_id={run_id} status={run.status} "
            f"created={run.created_count} skipped={run.skipped_count} failed={run.failed_count}"
        )
    except Exception as e:
        logger.exception(f"run_scraper 崩溃 run_id={run_id}")
        run.status = "failed"
        run.error_summary = {**(run.error_summary or {}), "system": f"run_scraper crashed: {e}"}
        run.finished_at = datetime.now()
        db.commit()
    finally:
        db.close()


def _try_process_one(db, run, scraper, raw, site_stat, current_user):
    """处理单条 raw 公告。"""
    try:
        item = scraper.normalize(raw)
    except Exception as e:
        _record_failure(db, run, scraper.name, raw, f"normalize 失败: {e}")
        site_stat["failed"] += 1
        logger.exception(f"[{scraper.name}] normalize 失败")
        return

    if item is None:
        return  # 被关键词/地区过滤，不计入统计

    try:
        created = _process_item(db, run, item, scraper.name, current_user)
        if created:
            site_stat["created"] += 1
        else:
            site_stat["skipped"] += 1
    except Exception as e:
        db.rollback()
        _record_failure(db, run, scraper.name, item, str(e))
        site_stat["failed"] += 1
        logger.exception(f"[{scraper.name}] process_item 失败")


def _process_item(db, run, item: ScrapeItem, source: str, current_user) -> bool:
    """返回 True=created, False=skipped。"""
    # 1) 去重
    dup = _find_duplicate(db, item)
    if dup:
        skip_reason = (
            f"external_no 重复 (project_id={dup.id})"
            if item.external_no and dup.external_no == item.external_no
            else f"项目名称重复 (project_id={dup.id})"
        )
        _log_item(db, run, item, source, "skipped", skip_reason=skip_reason)
        run.skipped_count += 1
        run.total_count += 1
        return False

    # 2) 匹配/创建组织
    bidding_unit_id, _ = match_or_create_org(item.bidding_unit_name, db, current_user)
    agency_id, _ = match_or_create_org(item.agency_name, db, current_user)
    platform_id, _ = match_or_create_platform(item.publish_platform_name, db, current_user)

    # 3) 构造 description
    desc = item.description or ""
    if item.external_no:
        desc = f"项目编号: {item.external_no}\n" + desc

    # 4) 创建项目（初始状态：跟进中）
    project = ProjectInfo(
        bidding_type=item.bidding_type,
        project_name=item.project_name,
        bidding_unit_id=bidding_unit_id,
        agency_id=agency_id,
        publish_platform_id=platform_id,
        region=item.region or "",
        external_no=item.external_no,
        source=source,
        source_url=item.source_url or "",
        budget_amount=item.budget_amount or 0,
        registration_deadline=item.registration_deadline,
        bid_deadline=item.bid_deadline,
        description=desc,
        status=ProjectStatus.following,
    )
    db.add(project)
    db.flush()

    _log_item(db, run, item, source, "created", project_id=project.id)
    run.created_count += 1
    run.total_count += 1
    return True


def _find_duplicate(db, item: ScrapeItem) -> ProjectInfo | None:
    """项目编号优先，名称兜底。"""
    if item.external_no:
        dup = (
            db.query(ProjectInfo)
            .filter(ProjectInfo.external_no == item.external_no)
            .first()
        )
        if dup:
            return dup
    if item.project_name:
        dup = (
            db.query(ProjectInfo)
            .filter(ProjectInfo.project_name == item.project_name)
            .first()
        )
        if dup:
            return dup
    return None


def _log_item(
    db, run, item: ScrapeItem, source: str, result: str,
    project_id: int = None, skip_reason: str = None, error_message: str = None,
):
    """写 scrape_item_logs 一行。"""
    log = ScrapeItemLog(
        run_id=run.id,
        source=source,
        external_no=item.external_no if isinstance(item, ScrapeItem) else None,
        project_name=item.project_name if isinstance(item, ScrapeItem) else str(item),
        source_url=item.source_url if isinstance(item, ScrapeItem) else None,
        result=result,
        project_id=project_id,
        skip_reason=skip_reason,
        error_message=error_message,
    )
    db.add(log)
    db.commit()


def _record_failure(db, run, source: str, item_or_raw, error_message: str):
    """记录失败项（normalize 阶段失败时 item 可能是 raw dict）。"""
    if isinstance(item_or_raw, ScrapeItem):
        project_name = item_or_raw.project_name
        source_url = item_or_raw.source_url
        external_no = item_or_raw.external_no
    else:
        project_name = (
            item_or_raw.get("title") or item_or_raw.get("projectName")
            or item_or_raw.get("bulletinTitle") or ""
        )
        source_url = item_or_raw.get("url") or item_or_raw.get("source_url")
        external_no = item_or_raw.get("prjNo") or item_or_raw.get("articleId")

    log = ScrapeItemLog(
        run_id=run.id,
        source=source,
        external_no=external_no,
        project_name=project_name,
        source_url=source_url,
        result="failed",
        error_message=error_message,
    )
    db.add(log)
    run.failed_count += 1
    run.total_count += 1
    db.commit()


def _derive_run_status(run: ScrapeRun) -> str:
    """根据 error_summary 推导最终状态。"""
    failed_sites = len(run.error_summary or {})
    # 排除 system 级错误（那是 run 级崩溃，在外层处理）
    site_failures = {k: v for k, v in (run.error_summary or {}).items() if k != "system"}
    total_sites = 4
    if len(site_failures) >= total_sites:
        return "failed"
    if len(site_failures) > 0:
        return "partial"
    return "success"
```

- [ ] **Step 2: 验证导入**

Run: `cd backend && python -c "from app.services.scrape_runner import run_scraper; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/scrape_runner.py
git commit -m "feat：scrape_runner.py 抓取主流程（去重 + 入库 + 日志）"
```

---

## Task 12: schemas/scrape.py — Pydantic 响应模型

**Files:**
- Create: `backend/app/schemas/scrape.py`

- [ ] **Step 1: 创建 schema 文件**

创建 `backend/app/schemas/scrape.py`：

```python
from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel


class ScrapeRunResponse(BaseModel):
    id: int
    started_at: datetime
    finished_at: Optional[datetime] = None
    triggered_by: Optional[int] = None
    triggered_by_name: Optional[str] = None
    status: str
    total_count: int = 0
    created_count: int = 0
    skipped_count: int = 0
    failed_count: int = 0
    sites_summary: Any = {}
    error_summary: Any = {}
    model_config = {"from_attributes": True}


class ScrapeItemLogResponse(BaseModel):
    id: int
    run_id: int
    source: str
    external_no: Optional[str] = None
    project_name: str
    source_url: Optional[str] = None
    result: str
    project_id: Optional[int] = None
    skip_reason: Optional[str] = None
    error_message: Optional[str] = None
    processed_at: datetime
    model_config = {"from_attributes": True}


class ScrapeRunDetailResponse(ScrapeRunResponse):
    item_logs: list[ScrapeItemLogResponse] = []
```

- [ ] **Step 2: 验证导入**

Run: `cd backend && python -c "from app.schemas.scrape import ScrapeRunResponse; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/schemas/scrape.py
git commit -m "feat：schemas/scrape.py 响应模型"
```

---

## Task 13: api/scrape.py — 4 个 API 端点

**Files:**
- Create: `backend/app/api/scrape.py`

- [ ] **Step 1: 创建 API 文件**

创建 `backend/app/api/scrape.py`：

```python
"""招标信息抓取 API。

POST   /api/scrape/run              触发抓取（管理员）
GET    /api/scrape/status/{run_id}  查询状态（轮询）
GET    /api/scrape/runs             历史列表
GET    /api/scrape/runs/{run_id}    单次详情（含 item_logs）
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..core.security import get_current_user
from ..models.scrape import ScrapeRun, ScrapeItemLog
from ..models.user import User, UserRole
from ..schemas.scrape import (
    ScrapeRunResponse, ScrapeRunDetailResponse, ScrapeItemLogResponse,
)
from ..services.scrape_runner import run_scraper

router = APIRouter(prefix="/api/scrape", tags=["招标抓取"])


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """要求当前用户是管理员。"""
    if current_user.role != UserRole.admin and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可执行此操作")
    return current_user


@router.post("/run")
def trigger_scrape(
    bg: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """触发一次抓取。立即返回 run_id，后台异步执行。"""
    # 防并发：已有 running 的 run 则拒绝
    existing = (
        db.query(ScrapeRun)
        .filter(ScrapeRun.status == "running")
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"已有抓取任务进行中 (run_id={existing.id})，请等待完成",
        )

    run = ScrapeRun(
        started_at=datetime.now(),
        triggered_by=current_user.id,
        status="running",
        total_count=0,
        created_count=0,
        skipped_count=0,
        failed_count=0,
        sites_summary={},
        error_summary={},
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    bg.add_task(run_scraper, run.id, current_user.id)
    return {"run_id": run.id, "status": "running"}


@router.get("/status/{run_id}", response_model=ScrapeRunResponse)
def get_status(
    run_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """查询某次 run 状态（前端轮询用）。"""
    run = db.query(ScrapeRun).filter(ScrapeRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="抓取记录不存在")
    return _enrich_run(run, db)


@router.get("/runs")
def list_runs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """抓取历史列表（分页）。"""
    query = db.query(ScrapeRun).order_by(ScrapeRun.started_at.desc())
    total = query.count()
    runs = query.offset((page - 1) * page_size).limit(page_size).all()
    return {
        "items": [_enrich_run_dict(r, db) for r in runs],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/runs/{run_id}", response_model=ScrapeRunDetailResponse)
def get_run_detail(
    run_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """单次 run 详情（含 item_logs）。"""
    run = db.query(ScrapeRun).filter(ScrapeRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="抓取记录不存在")

    logs = (
        db.query(ScrapeItemLog)
        .filter(ScrapeItemLog.run_id == run_id)
        .order_by(ScrapeItemLog.id.asc())
        .all()
    )

    resp = _enrich_run(run, db)
    resp["item_logs"] = [ScrapeItemLogResponse.model_validate(log) for log in logs]
    return resp


def _enrich_run(run: ScrapeRun, db: Session) -> dict:
    """转 dict 并补充 triggered_by_name。"""
    d = _enrich_run_dict(run, db)
    return d


def _enrich_run_dict(run: ScrapeRun, db: Session) -> dict:
    """ScrapeRun → dict，补充触发用户名。"""
    triggered_by_name = None
    if run.triggered_by:
        user = db.query(User).filter(User.id == run.triggered_by).first()
        if user:
            triggered_by_name = user.display_name or user.username

    return {
        "id": run.id,
        "started_at": run.started_at,
        "finished_at": run.finished_at,
        "triggered_by": run.triggered_by,
        "triggered_by_name": triggered_by_name,
        "status": run.status,
        "total_count": run.total_count,
        "created_count": run.created_count,
        "skipped_count": run.skipped_count,
        "failed_count": run.failed_count,
        "sites_summary": run.sites_summary or {},
        "error_summary": run.error_summary or {},
    }
```

- [ ] **Step 2: 在 main.py 注册 scrape_router**

在 `backend/app/main.py` 的路由注册区（约 line 139），加：

```python
from .api.scrape import router as scrape_router
```

在 `app.include_router(documents_router)` 之后加：

```python
app.include_router(scrape_router)
```

- [ ] **Step 3: 启动后端验证端点**

Run: `cd backend && python -m uvicorn app.main:app --port 8000 &` 然后 `sleep 3` 然后 `curl -s http://localhost:8000/openapi.json | python -c "import sys,json; d=json.load(sys.stdin); print([p for p in d['paths'] if 'scrape' in p])"`

Expected: `['/api/scrape/run', '/api/scrape/status/{run_id}', '/api/scrape/runs', '/api/scrape/runs/{run_id}']`

杀掉 uvicorn 进程。

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/scrape.py backend/app/main.py
git commit -m "feat：api/scrape.py 4 个抓取 API + require_admin 权限"
```

---

## Task 14: ProjectResponse 暴露新 3 字段

**Files:**
- Modify: `backend/app/schemas/project.py:76-152`

- [ ] **Step 1: 在 ProjectResponse 中加 3 字段**

在 `backend/app/schemas/project.py` 的 `ProjectResponse` 类中，找到 `parent_project_id: Optional[int] = None`（约 line 88），在其后加：

```python
    parent_project_id: Optional[int] = None
    external_no: Optional[str] = None
    source: Optional[str] = None
    source_url: Optional[str] = None
```

- [ ] **Step 2: 验证 schema**

Run: `cd backend && python -c "from app.schemas.project import ProjectResponse; print(ProjectResponse.model_fields.keys().__class__)" 2>&1 | head -3`
Expected: 无报错（如果有 enrich_project 函数也需检查，但 model_config=from_attributes 会自动读取新字段）

- [ ] **Step 3: Commit**

```bash
git add backend/app/schemas/project.py
git commit -m "feat：ProjectResponse 暴露 external_no/source/source_url"
```

---

## Task 15: requirements.txt 加抓取依赖

**Files:**
- Modify: `backend/requirements.txt`

- [ ] **Step 1: 追加依赖**

在 `backend/requirements.txt` 末尾追加：

```
# 抓取模块依赖
requests>=2.31.0
scrapling>=0.2.0
# playwright 是可选依赖（仅 jhzjcs 站点需要）：
#   pip install playwright && playwright install chromium
# 未安装时 jhzjcs 站点会失败，不影响后端启动和其他站点
# playwright>=1.40.0
```

- [ ] **Step 2: 安装新依赖**

Run: `cd backend && pip install requests scrapling -i https://pypi.tuna.tsinghua.edu.cn/simple 2>&1 | tail -5`

Playwright 单独装（体积大）：

Run: `cd backend && pip install playwright -i https://pypi.tuna.tsinghua.edu.cn/simple 2>&1 | tail -3`

注意：playwright pip 包安装后还需 `playwright install chromium` 下载浏览器内核（约 150MB），但本方案用系统 Chrome（`channel="chrome"`），所以可以跳过 chromium 下载。

- [ ] **Step 3: Commit**

```bash
git add backend/requirements.txt
git commit -m "feat：requirements.txt 加 requests/scrapling/playwright"
```

---

## Task 16: 前端 api/scrape.js

**Files:**
- Create: `frontend/src/api/scrape.js`

- [ ] **Step 1: 创建 API 模块**

创建 `frontend/src/api/scrape.js`：

```javascript
import request from './index'

export function triggerScrape() {
  return request.post('/scrape/run')
}

export function getScrapeStatus(runId) {
  return request.get(`/scrape/status/${runId}`)
}

export function getScrapeRuns(params) {
  return request.get('/scrape/runs', { params })
}

export function getScrapeRunDetail(runId) {
  return request.get(`/scrape/runs/${runId}`)
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/api/scrape.js
git commit -m "feat：前端 api/scrape.js"
```

---

## Task 17: ProjectList.vue 加抓取按钮 + 进度轮询

**Files:**
- Modify: `frontend/src/views/project/ProjectList.vue`

- [ ] **Step 1: 在工具栏加抓取按钮（仅管理员可见）**

找到 `<el-button type="primary" @click="$router.push('/projects/new')">` 那一行（约 line 56），在其前加抓取按钮：

```html
        <el-button type="primary" @click="$router.push('/projects/new')"><el-icon><Plus /></el-icon> 新增项目</el-button>
        <el-button
          v-if="userStore.user?.role === 'admin'"
          type="success"
          :loading="scrapeState.running"
          @click="handleScrape"
        >
          <el-icon><Download /></el-icon> 抓取招标信息
        </el-button>
```

注意：需在 `<script setup>` 中 `import { Download } from '@element-plus/icons-vue'`（检查现有图标导入，统一加）。

- [ ] **Step 2: 在模板底部加进度展示弹窗**

在 `<template>` 根元素内（表格之后、分页之前或之后均可），加进度对话框：

```html
    <!-- 抓取进度 -->
    <el-dialog v-model="scrapeState.showProgress" title="抓取进度" width="520px" :close-on-click-modal="false" :close-on-press-escape="false">
      <div v-if="scrapeState.running">
        <el-progress :percentage="scrapeState.percentage" :status="'warning'" />
        <p style="margin-top: 12px; color: #666">
          已入库: {{ scrapeState.created }} | 重复跳过: {{ scrapeState.skipped }} | 失败: {{ scrapeState.failed }}
        </p>
        <p style="color: #999; font-size: 13px">正在抓取，请勿关闭页面...</p>
      </div>
      <div v-else>
        <el-result
          :icon="scrapeResultIcon"
          :title="scrapeResultTitle"
          :sub-title="scrapeResultSub"
        >
          <template #extra>
            <el-button @click="scrapeState.showProgress = false">关闭</el-button>
            <el-button type="primary" @click="$router.push('/scrape/history')">查看抓取记录</el-button>
          </template>
        </el-result>
      </div>
    </el-dialog>
```

- [ ] **Step 3: 在 `<script setup>` 中加抓取逻辑**

在 `<script setup>` 区域，加入以下代码（import 区、响应式状态、方法）：

在现有 import 区加：

```javascript
import { triggerScrape, getScrapeStatus } from '../../api/scrape'
```

在 `useUserStore` 引用区（如果没有则加）：

```javascript
import { useUserStore } from '../../stores/user'
const userStore = useUserStore()
```

在响应式状态区加：

```javascript
const scrapeState = reactive({
  running: false,
  showProgress: false,
  runId: null,
  percentage: 0,
  created: 0,
  skipped: 0,
  failed: 0,
  status: '',  // running / success / partial / failed
  pollTimer: null,
})

const scrapeResultIcon = computed(() => {
  if (scrapeState.status === 'success') return 'success'
  if (scrapeState.status === 'partial') return 'warning'
  return 'error'
})

const scrapeResultTitle = computed(() => {
  const map = { success: '抓取完成', partial: '部分成功', failed: '抓取失败' }
  return map[scrapeState.status] || '完成'
})

const scrapeResultSub = computed(() => {
  const errs = scrapeState.errorSummary || {}
  const failedSites = Object.keys(errs).filter(k => k !== 'system')
  const parts = [
    `入库 ${scrapeState.created}，跳过 ${scrapeState.skipped}，失败 ${scrapeState.failed}`,
  ]
  if (failedSites.length) {
    parts.push(`失败站点: ${failedSites.join(', ')}`)
  }
  return parts.join('；')
})
```

在方法区加：

```javascript
async function handleScrape() {
  try {
    await ElMessageBox.confirm(
      '将抓取 4 个站点今日新增的招标公告，预计 1-2 分钟。\n\n抓取到的项目会自动入库（初始状态：跟进中），可在列表中查看。',
      '确认抓取',
      { confirmButtonText: '开始抓取', cancelButtonText: '取消', type: 'info' }
    )
  } catch {
    return  // 用户取消
  }

  try {
    const resp = await triggerScrape()
    scrapeState.running = true
    scrapeState.showProgress = true
    scrapeState.runId = resp.run_id
    scrapeState.percentage = 0
    scrapeState.created = 0
    scrapeState.skipped = 0
    scrapeState.failed = 0
    scrapeState.status = 'running'
    scrapeState.errorSummary = {}
    localStorage.setItem('lastScrapeRunId', resp.run_id)
    pollScrapeStatus()
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '触发抓取失败')
  }
}

function pollScrapeStatus() {
  if (scrapeState.pollTimer) clearInterval(scrapeState.pollTimer)
  scrapeState.pollTimer = setInterval(async () => {
    if (!scrapeState.runId) return
    try {
      const data = await getScrapeStatus(scrapeState.runId)
      scrapeState.created = data.created_count
      scrapeState.skipped = data.skipped_count
      scrapeState.failed = data.failed_count
      scrapeState.errorSummary = data.error_summary || {}
      // 进度估算：根据已完成站点数
      const sites = data.sites_summary || {}
      const errors = data.error_summary || {}
      const doneSites = Object.keys(sites).length + Object.keys(errors).length
      scrapeState.percentage = Math.min(95, Math.round((doneSites / 4) * 100))

      if (data.status !== 'running') {
        clearInterval(scrapeState.pollTimer)
        scrapeState.pollTimer = null
        scrapeState.running = false
        scrapeState.status = data.status
        scrapeState.percentage = 100
        localStorage.removeItem('lastScrapeRunId')
        ElMessage.success(`抓取完成：入库 ${data.created_count} 条`)
        loadData()  // 刷新项目列表
      }
    } catch (err) {
      console.error('轮询失败', err)
    }
  }, 2000)
}

// 页面加载时恢复轮询（如果上次离开时还在跑）
onMounted(() => {
  const lastRunId = localStorage.getItem('lastScrapeRunId')
  if (lastRunId) {
    scrapeState.runId = parseInt(lastRunId)
    scrapeState.showProgress = true
    scrapeState.running = true
    pollScrapeStatus()
  }
})

onUnmounted(() => {
  if (scrapeState.pollTimer) clearInterval(scrapeState.pollTimer)
})
```

注意：检查现有 `<script setup>` 是否已导入 `reactive, computed, onMounted, onUnmounted`，如果没有则在 `import { ref } from 'vue'` 处补充。同样检查 `ElMessageBox, ElMessage` 是否已导入。

- [ ] **Step 4: 验证前端编译**

Run: `cd frontend && npx vite build 2>&1 | tail -10`
Expected: 构建成功（或仅警告，无 error）

- [ ] **Step 5: Commit**

```bash
git add frontend/src/views/project/ProjectList.vue
git commit -m "feat：ProjectList 加抓取按钮 + 进度轮询"
```

---

## Task 18: ScrapeHistory.vue — 抓取历史页

**Files:**
- Create: `frontend/src/views/scrape/ScrapeHistory.vue`

- [ ] **Step 1: 创建历史页组件**

创建 `frontend/src/views/scrape/ScrapeHistory.vue`：

```vue
<template>
  <div>
    <el-card>
      <template #header>
        <span>抓取记录</span>
      </template>

      <el-table :data="runs" v-loading="loading" stripe>
        <el-table-column label="开始时间" width="160">
          <template #default="{ row }">
            {{ formatTime(row.started_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="triggered_by_name" label="触发用户" width="100" />
        <el-table-column prop="total_count" label="总数" width="70" align="center" />
        <el-table-column prop="created_count" label="入库" width="70" align="center">
          <template #default="{ row }">
            <span style="color: #67c23a">{{ row.created_count }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="skipped_count" label="跳过" width="70" align="center">
          <template #default="{ row }">
            <span style="color: #909399">{{ row.skipped_count }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="failed_count" label="失败" width="70" align="center">
          <template #default="{ row }">
            <span style="color: #f56c6c">{{ row.failed_count }}</span>
          </template>
        </el-table-column>
        <el-table-column label="耗时" width="80">
          <template #default="{ row }">
            {{ formatDuration(row.started_at, row.finished_at) }}
          </template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="statusTag(row.status)">{{ statusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="失败站点" min-width="200">
          <template #default="{ row }">
            <span v-if="row.error_summary && Object.keys(row.error_summary).length" style="font-size: 12px; color: #e6a23c">
              {{ formatErrors(row.error_summary) }}
            </span>
            <span v-else style="color: #c0c4cc">—</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="80" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="showDetail(row.id)">详情</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div style="margin-top: 16px; text-align: right">
        <el-pagination
          v-model:current-page="page"
          :page-size="20"
          :total="total"
          layout="total, prev, pager, next"
          @current-change="loadData"
        />
      </div>
    </el-card>

    <!-- 详情抽屉 -->
    <el-drawer v-model="detailVisible" title="抓取详情" size="70%">
      <div v-if="detail">
        <el-descriptions :column="4" border style="margin-bottom: 16px">
          <el-descriptions-item label="开始时间">{{ formatTime(detail.started_at) }}</el-descriptions-item>
          <el-descriptions-item label="结束时间">{{ formatTime(detail.finished_at) }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="statusTag(detail.status)">{{ statusText(detail.status) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="触发用户">{{ detail.triggered_by_name }}</el-descriptions-item>
          <el-descriptions-item label="入库">{{ detail.created_count }}</el-descriptions-item>
          <el-descriptions-item label="跳过">{{ detail.skipped_count }}</el-descriptions-item>
          <el-descriptions-item label="失败">{{ detail.failed_count }}</el-descriptions-item>
          <el-descriptions-item label="总数">{{ detail.total_count }}</el-descriptions-item>
        </el-descriptions>

        <el-table :data="detail.item_logs" stripe max-height="500">
          <el-table-column prop="source" label="来源" width="90" />
          <el-table-column prop="project_name" label="项目名称" min-width="250" show-overflow-tooltip />
          <el-table-column prop="external_no" label="编号" width="140" show-overflow-tooltip />
          <el-table-column label="结果" width="80">
            <template #default="{ row }">
              <el-tag :type="resultTag(row.result)" size="small">{{ resultText(row.result) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="skip_reason" label="跳过原因" width="200" show-overflow-tooltip />
          <el-table-column prop="error_message" label="错误信息" width="250" show-overflow-tooltip />
          <el-table-column label="链接" width="70">
            <template #default="{ row }">
              <el-link v-if="row.source_url" :href="row.source_url" target="_blank" type="primary">查看</el-link>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getScrapeRuns, getScrapeRunDetail } from '../../api/scrape'

const runs = ref([])
const loading = ref(false)
const page = ref(1)
const total = ref(0)

const detailVisible = ref(false)
const detail = ref(null)

async function loadData() {
  loading.value = true
  try {
    const data = await getScrapeRuns({ page: page.value, page_size: 20 })
    runs.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

async function showDetail(runId) {
  detail.value = await getScrapeRunDetail(runId)
  detailVisible.value = true
}

function formatTime(s) {
  if (!s) return '—'
  return new Date(s).toLocaleString('zh-CN', { hour12: false })
}

function formatDuration(start, end) {
  if (!start || !end) return '—'
  const sec = Math.round((new Date(end) - new Date(start)) / 1000)
  const m = Math.floor(sec / 60)
  const s = sec % 60
  return `${m}:${s.toString().padStart(2, '0')}`
}

function formatErrors(errs) {
  const entries = Object.entries(errs).filter(([k]) => k !== 'system')
  return entries.map(([k, v]) => `${k}: ${v}`).join('; ')
}

function statusText(s) {
  return { running: '进行中', success: '成功', partial: '部分成功', failed: '失败' }[s] || s
}

function statusTag(s) {
  return { running: 'warning', success: 'success', partial: 'warning', failed: 'danger' }[s] || ''
}

function resultText(r) {
  return { created: '入库', skipped: '跳过', failed: '失败' }[r] || r
}

function resultTag(r) {
  return { created: 'success', skipped: 'info', failed: 'danger' }[r] || ''
}

onMounted(loadData)
</script>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/views/scrape/ScrapeHistory.vue
git commit -m "feat：ScrapeHistory 抓取历史页 + 详情抽屉"
```

---

## Task 19: router + Layout 加路由和菜单

**Files:**
- Modify: `frontend/src/router/index.js`
- Modify: `frontend/src/components/Layout.vue`

- [ ] **Step 1: 在 router 加 `/scrape/history` 路由**

在 `frontend/src/router/index.js` 的 children 数组中，在 `logs` 路由之后加：

```javascript
      {
        path: 'scrape/history',
        name: 'ScrapeHistory',
        component: () => import('../views/scrape/ScrapeHistory.vue'),
        meta: { title: '抓取记录' },
      },
```

- [ ] **Step 2: 在 Layout 侧边栏加菜单项**

在 `frontend/src/components/Layout.vue` 的 `<el-menu>` 中，在「操作日志」菜单项之前加：

```html
          <el-menu-item index="/scrape/history">
            <el-icon><Download /></el-icon>
            <span>抓取记录</span>
          </el-menu-item>
```

在 `<script setup>` 的图标导入中加 `Download`（检查现有导入语句格式，通常是 `import { DataBoard, Document, ... } from '@element-plus/icons-vue'`）。

- [ ] **Step 3: 验证前端构建**

Run: `cd frontend && npx vite build 2>&1 | tail -10`
Expected: 构建成功

- [ ] **Step 4: Commit**

```bash
git add frontend/src/router/index.js frontend/src/components/Layout.vue
git commit -m "feat：router + Layout 加抓取记录路由和菜单"
```

---

## Task 20: 端到端联调测试

**Files:**
- 临时脚本（不提交）: `backend/test_scraper_manual.py`

- [ ] **Step 1: 启动后端**

Run: `cd backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`

确认看到：
- `Migration: added external_no/source/source_url` （首次）
- `Application startup complete`
- 无 import 错误

- [ ] **Step 2: 验证数据库表结构**

打开 `backend/data/app.db`（用 DB Browser for SQLite 或命令行）：

```bash
cd backend && python -c "
from app.core.database import engine
from sqlalchemy import inspect
insp = inspect(engine)
print('project_infos columns:', [c['name'] for c in insp.get_columns('project_infos') if c['name'] in ('external_no','source','source_url')])
print('scrape_runs exists:', insp.has_table('scrape_runs'))
print('scrape_item_logs exists:', insp.has_table('scrape_item_logs'))
"
```

Expected: 3 个字段都在；两个新表都存在。

- [ ] **Step 3: 验证 API 端点可访问**

打开浏览器访问 `http://localhost:8000/docs`，确认看到「招标抓取」分组下有 4 个端点。

- [ ] **Step 4: 用 Swagger 测试抓取（管理员 token）**

先登录拿 token：
```bash
curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'
```

触发抓取：
```bash
curl -s -X POST http://localhost:8000/api/scrape/run \
  -H "Authorization: Bearer <TOKEN>"
```

Expected: `{"run_id":1,"status":"running"}`

轮询状态：
```bash
curl -s http://localhost:8000/api/scrape/status/1 \
  -H "Authorization: Bearer <TOKEN>"
```

等待 status 变为 `success` / `partial` / `failed`。

- [ ] **Step 5: 检查入库结果**

```bash
curl -s "http://localhost:8000/api/projects?page=1&page_size=5" \
  -H "Authorization: Bearer <TOKEN>" | python -c "
import sys, json
data = json.load(sys.stdin)
for p in data['items'][:5]:
    print(f\"id={p['id']} source={p.get('source')} name={p['project_name'][:40]}\")
"
```

Expected: 能看到 `source=jhygcg` / `source=ggzy` / `source=ccgp` 的项目。

- [ ] **Step 6: 前端 UI 验证**

启动前端：`cd frontend && npm run dev`

打开浏览器，以 admin 登录：
- 项目列表页应看到绿色「抓取招标信息」按钮
- 点击 → 确认对话框 → 进度弹窗 → 完成提示
- 侧边栏「抓取记录」菜单 → 历史列表 → 详情抽屉

切换普通用户（001/002/003）登录：
- 项目列表页**不应**看到抓取按钮
- 侧边栏**应**看到「抓取记录」菜单

- [ ] **Step 7: 重复抓取验证**

再次点击抓取按钮，确认第二次大部分项目被 skipped（去重生效）。

- [ ] **Step 8: 清理临时脚本**

如有创建 `backend/test_scraper_manual.py`，删除它（不提交）。

- [ ] **Step 9: Commit（如有修复）**

如果联调中发现 bug 并修复，提交修复：

```bash
git add <修复的文件>
git commit -m "fix：联调修复 <具体问题>"
```

---

## Task 21: 更新 CLAUDE.md

**Files:**
- Modify: `E:\经营中心信息管理\CLAUDE.md`

- [ ] **Step 1: 在 Backend Structure 加 scrape 相关说明**

找到 `api/stats.py` 条目附近，在 `api/documents.py` 条目之后加：

```markdown
- **`api/scrape.py`** — Auto-scrape endpoints. `POST /api/scrape/run` triggers a scrape run (admin only, returns `{run_id}` immediately, runs `run_scraper` via BackgroundTasks). `GET /api/scrape/status/{run_id}` for polling. `GET /api/scrape/runs` lists history. `GET /api/scrape/runs/{run_id}` returns detail with item_logs. `require_admin` dependency checks `role == "admin"`. Prevents concurrent runs (409 if another run is `running`).
```

在 `services/document_parser.py` 条目之后加：

```markdown
- **`services/scrape_runner.py`** — Main scrape orchestration. `run_scraper(run_id, user_id)` iterates all scrapers, calls `fetch_with_retry` → `normalize` → `_process_item`. `_find_duplicate` checks `external_no` first, then `project_name`. `_process_item` creates ProjectInfo with `status=following`. `_record_failure` / `_log_item` write to `scrape_item_logs`. Counter invariant: `total_count = created_count + skipped_count + failed_count`.
- **`services/org_matcher.py`** — Shared `match_or_create_org` / `match_or_create_platform` helpers, reused by both `documents.py` and `scrape_runner.py`.
```

在 `main.py` 条目中追加：

```markdown
 Also registers `scrape_router`, imports `scrape` model, migrates `external_no`/`source`/`source_url` columns, and cleans up orphan scrape runs on startup.
```

- [ ] **Step 2: 在 Frontend Structure 加 scrape 说明**

在 `api/project.js` 条目之后加：

```markdown
- **`api/scrape.js`** — Scrape API: `triggerScrape` / `getScrapeStatus` / `getScrapeRuns` / `getScrapeRunDetail`.
```

在 `views/project/` 条目中加：

```markdown
 `ProjectList.vue` also has a "抓取招标信息" button (admin only) that triggers scrape + polls progress.
- **`views/scrape/ScrapeHistory.vue`** — Scrape run history list + detail drawer (all users can view).
```

- [ ] **Step 3: 在 Data Model 表格中更新**

在「项目基本信息」行的 Columns cover 中追加 `external_no, source, source_url`。

在表格下方加新表说明：

```markdown
**Scrape tables**: `scrape_runs` (run-level stats: status, counts, sites_summary, error_summary) and `scrape_item_logs` (per-item: result=created/skipped/failed, project_id, skip_reason, error_message). Both auto-created on startup.
```

- [ ] **Step 4: 在 Key Technical Notes 加 scrape 说明**

在 "No tests" 条目之前，加：

```markdown
- **Auto-scrape**: `POST /api/scrape/run` (admin only) triggers `run_scraper(run_id, user_id)` via FastAPI BackgroundTasks. Iterates all registered scrapers (ccgp/ggzy/jhygcg/jhzjcs), each via `ScraperRegistry.all()` (lazy-loaded, fault-tolerant — a broken scraper doesn't crash the run). Prevents concurrent runs (409). Orphan runs (status=running + finished_at=NULL) cleaned on startup.
- **Scraper architecture**: `scrapers/base.py` defines `BaseScraper` (abstract `fetch`/`normalize`, `fetch_with_retry` with 3 retries + exponential backoff), `ScrapeItem` dataclass, `SiteFetchError`. `scrapers/__init__.py:ScraperRegistry` lazily imports and instantiates all scrapers in try/except blocks. Each scraper module: `ccgp.py` (scrapling), `ggzy.py` (requests + WAF), `jhygcg.py` (requests), `jhzjcs.py` (Playwright, delayed import in `fetch()`).
- **Keyword + region filter**: `scrapers/base.py:KEYWORDS` = [检测/人防/防雷/消防/勘察/测绘/监测/鉴定/评估/试验]. `match_keywords(text)` = OR match. `match_region_zhejiang()` checks title for 浙江 city names, or CCGP zoneId / GGZY infoc starting with 330. jhygcg/jhzjcs are inherently 金华市, skip region check.
- **Dedup**: `_find_duplicate` checks `external_no` (indexed) first, then exact `project_name`. No fuzzy matching (avoid false positives). Does NOT update existing projects on duplicate (preserves user edits).
- **Playwright delayed import**: `jhzjcs.py` imports playwright inside `fetch()`, so backend starts fine even if playwright is not installed. The jhzjcs scraper just fails gracefully (recorded in `error_summary`). Uses system Chrome via `executable_path` when available.
- **Scrape project fields**: Created projects have `status=跟进中`, `source` set to scraper name (ccgp/ggzy/jhygcg/jhzjcs), `external_no` from announcement number, `source_url` from original link. Manual projects default `source=manual`.
- **org_matcher.py**: `match_or_create_org` / `match_or_create_platform` extracted from `api/documents.py` into `services/org_matcher.py` for reuse by both document parsing and scrape runner. Signatures unchanged.
```

- [ ] **Step 5: 在 Design Document 行追加 spec 引用**

在文件末尾 Design Document 区域加：

```markdown
Auto-fetch integration spec: `docs/superpowers/specs/2026-06-16-auto-fetch-integration-design.md`
Auto-fetch integration plan: `docs/superpowers/plans/2026-06-16-auto-fetch-integration-plan.md`
```

- [ ] **Step 6: Commit**

```bash
git add CLAUDE.md
git commit -m "docs：更新 CLAUDE.md — 抓取集成功能说明"
```

---

## Task 22: 最终验证 + 推送

- [ ] **Step 1: 确认无敏感文件未提交**

Run: `git status`
Expected: `backend/data/` / `.superpowers/` / `backend/migrate_db.py` 不在 untracked 列表中

- [ ] **Step 2: 确认提交历史**

Run: `git log --oneline -25`
Expected: 能看到约 18-20 个新提交，均为 `feat：` / `refactor：` / `docs：` 前缀

- [ ] **Step 3: 确认后端能正常启动**

Run: `cd backend && python -c "from app.main import app; print('OK')"`
Expected: `OK`（无 import 错误）

- [ ] **Step 4: 确认前端能构建**

Run: `cd frontend && npx vite build 2>&1 | tail -5`
Expected: 构建成功

- [ ] **Step 5: 推送（需用户确认）**

询问用户是否推送。确认后：

```bash
git push origin main
```

---

## 附录：关键风险与应对

| 风险 | 应对 |
|------|------|
| scrapling 在 Windows 安装失败 | scraper 内延迟导入，不影响后端启动；ccgp 站点会被 ScraperRegistry 跳过 |
| Playwright 未安装 | 同上，jhzjcs 站点失败，其余 3 个正常 |
| GGZY WAF 拦截 | 已设 session + UA headers；如仍被拦，error_summary 会记录，run 标记为 partial |
| SQLite database locked | database.py 已设 `busy_timeout=30000` + WAL 模式，抓取中操作前端应无锁冲突 |
| 抓取超时 | 每站点 3 次重试 + 30s 超时，最坏情况每站点约 2 分钟，4 站点约 8 分钟 |
