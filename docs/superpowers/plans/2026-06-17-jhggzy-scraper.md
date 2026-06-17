# jhggzy 抓取模块实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增 `jhggzy` scraper，抓取金华市公共资源交易网 11 县区分站的「预公告 + 招标公告 + 采购公告」共 33 个数据源，纳入现有 `ScraperRegistry` 统一调度。

**Architecture:** 单个 `JhggzyScraper` 类（继承 `BaseScraper`），内部维护 33 行数据源配置表。通过 AJAX API（`/api-gateway/jpaas-publish-server/front/page/build/unit`）翻页拿 HTML 片段，正则解析标题/链接/日期，应用关键词+结果公告过滤后转为 `ScrapeItem`。复用现有 `run_scraper` 编排管线，仅注册一行即生效。

**Tech Stack:** Python 3.13 / requests / 正则 / FastAPI 既有抓取管线 / SQLAlchemy 既有模型。

**Spec:** `docs/superpowers/specs/2026-06-17-jhggzy-scraper-design.md`

---

## 项目约束（先读）

- **项目无测试套件**（CLAUDE.md 明确说明）。本计划用 Python REPL 手动验证替代 TDD，每个 Task 末尾给出验证命令。
- **所有输出中文**（CLAUDE.md 语言规则），含 commit message。
- **后端 .py 改动后必须手动重启 uvicorn**（不依赖 `--reload`）。每个改后端代码的 Task 末尾有重启步骤，参考本计划「附录 A：重启 uvicorn」。
- **commit message 风格**：`feat：`/`fix：`/`docs：`/`refactor：` + 中文描述（参考 `git log --oneline`）。

---

## 文件结构

| 文件 | 操作 | 职责 |
|---|---|---|
| `backend/app/scrapers/jhggzy.py` | 新建 | scraper 主体（常量 + SOURCES 表 + `JhggzyScraper` 类） |
| `backend/app/scrapers/__init__.py` | 改 1 行 | 在 `ScraperRegistry._load_all` 列表追加 `("jhggzy", "JhggzyScraper")` |
| `CLAUDE.md` | 改 scrapers 段落 | 在站点模块列表追加 `jhggzy.py` 条目 + 关键技术说明 |

不创建其它文件。不修改 `base.py` / `scrape_runner.py` / `api/scrape.py` / 数据库 schema。

---

## Task 1：创建 jhggzy.py 骨架（常量 + SOURCES 表 + 空类）

**Files:**
- Create: `backend/app/scrapers/jhggzy.py`

- [ ] **Step 1：写完整骨架文件**

创建 `backend/app/scrapers/jhggzy.py`，内容如下：

```python
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
        raise NotImplementedError("Task 2 实现")

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
```

- [ ] **Step 2：验证文件可被 Python import**

```bash
cd backend && python -c "from app.scrapers.jhggzy import JhggzyScraper, SOURCES; print('name=', JhggzyScraper.name); print('sources=', len(SOURCES))"
```

Expected:
```
name= jhggzy
sources= 33
```

- [ ] **Step 3：commit**

```bash
git add backend/app/scrapers/jhggzy.py
git commit -m "feat：jhggzy scraper 骨架 — 33 数据源表 + 常量 + 类占位"
```

---

## Task 2：实现 `_resolve_page_id`

**Files:**
- Modify: `backend/app/scrapers/jhggzy.py`（替换 `_resolve_page_id` 方法的 `raise NotImplementedError`）

- [ ] **Step 1：用以下实现替换 `_resolve_page_id` 方法体**

```python
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
```

- [ ] **Step 2：Python REPL 验证两种 URL 形态**

```bash
cd backend && python -c "
from app.scrapers.jhggzy import JhggzyScraper
s = JhggzyScraper()
# 顶级栏目（预公告）：直接返回 colId，不发请求
print('pre_announce=', s._resolve_page_id('/col/col1229847292/index.html'))
# 顶级栏目（采购公告）：直接返回 colId
print('purchase=', s._resolve_page_id('/col/col1229641940/index.html'))
# 子路径栏目（招标公告）：fetch 静态页解析哈希
print('tender=', s._resolve_page_id('/col/col1229641936/zbggbzlm267/index.html'))
# 缓存命中
print('cached=', s._page_id_cache.get('/col/col1229847292/index.html'))
"
```

Expected（哈希值每次站点重建会变，结构应该形如）：
```
pre_announce= 1229847292
purchase= 1229641940
tender= <32位或更短的哈希字符串，非纯数字>
cached= 1229847292
```

- [ ] **Step 3：commit**

```bash
git add backend/app/scrapers/jhggzy.py
git commit -m "feat：jhggzy 实现 _resolve_page_id — 顶级栏目直接用 colId，子路径栏目 fetch 解析"
```

---

## Task 3：实现 `_parse_html_items`

**Files:**
- Modify: `backend/app/scrapers/jhggzy.py`（替换 `_parse_html_items` 方法的 `raise NotImplementedError`，去掉 `@staticmethod` 装饰器行下方的占位）

- [ ] **Step 1：用以下实现替换 `_parse_html_items` 方法体**

```python
    @staticmethod
    def _parse_html_items(html_frag: str) -> list:
        """解析 AJAX API 返回的 HTML 片段为 [{title, url, publish_date}, ...]。
        片段示例（节选）：
          <a href="/col/col1229847292/art/2026/art_9f52b7fdcc874cc7bc3438f2c99d073b.html"
             title="...">东阳市巍山镇...招标文件预公示
             公告类型：招标文件预公示2026-06-17</a>
        """
        if not html_frag:
            return []
        items = []
        # 匹配 <a href="...art_<32hex>.html" ...>标题内容</a>
        pattern = re.compile(
            r'<a[^>]+href="([^"]*?art_[a-f0-9]+\.html)"[^>]*>(.*?)</a>',
            re.DOTALL,
        )
        for m in pattern.finditer(html_frag):
            url = m.group(1)
            title_html = m.group(2)
            # 剥 HTML 标签 + 规范化空白
            title = re.sub(r"<[^>]+>", "", title_html)
            title = re.sub(r"\s+", " ", title).strip()
            # 去掉混在标题里的「公告类型：xxx」前缀（保留纯标题）
            title = re.sub(r"^公告类型：\S+\s*", "", title)
            # 提取发布日期（标题尾部或紧随其后的文本含 YYYY-MM-DD）
            date_match = re.search(r"(20\d{2}-\d{2}-\d{2})", title)
            publish_date = date_match.group(1) if date_match else None
            # 把日期从标题末尾去掉，得到纯标题
            if date_match:
                title = title[:date_match.start()].strip()
            if title and url:
                items.append({
                    "title": title,
                    "url": url,
                    "publish_date": publish_date,
                })
        return items
```

- [ ] **Step 2：Python REPL 验证解析正确**

```bash
cd backend && python -c "
from app.scrapers.jhggzy import JhggzyScraper
sample = '''
<li><a href=\"/col/col1229847292/art/2026/art_9f52b7fdcc874cc7bc3438f2c99d073b.html\" title=\"x\">
东阳市巍山镇古渊头村村民活动中心改造项目招标文件预公示
        公告类型：招标文件预公示2026-06-17</a></li>
<li><a href=\"/col/col1229847292/art/2026/art_e1ac35ce170e47b28204c6a68d688fa3.html\">
东阳市湖溪镇白水口村文化礼堂装修项目招标文件预公示
        公告类型：招标文件预公示2026-06-16</a></li>
'''
items = JhggzyScraper._parse_html_items(sample)
for it in items:
    print(it['publish_date'], '|', it['title'][:40], '|', it['url'][-40:])
"
```

Expected:
```
2026-06-17 | 东阳市巍山镇古渊头村村民活动中心改造项目招标文件预公示 | ...art_9f52b7fdcc874cc7bc3438f2c99d073b.html
2026-06-16 | 东阳市湖溪镇白水口村文化礼堂装修项目招标文件预公示 | ...art_e1ac35ce170e47b28204c6a68d688fa3.html
```

确认点：
- 标题里「公告类型：xxx」被剥除
- 日期从标题里分离到 `publish_date` 字段
- URL 完整保留

- [ ] **Step 3：commit**

```bash
git add backend/app/scrapers/jhggzy.py
git commit -m "feat：jhggzy 实现 _parse_html_items — 正则解析 HTML 片段含标题清洗"
```

---

## Task 4：实现 `_fetch_source`（翻页 + 日期过滤）

**Files:**
- Modify: `backend/app/scrapers/jhggzy.py`

- [ ] **Step 1：用以下实现替换 `_fetch_source` 方法体**

```python
    def _fetch_source(self, page_id: str, date_str: str) -> list:
        """翻页调用 AJAX API，返回 publish_date == date_str 的原始记录。
        终止条件（满足任一）：
        1) 某条 publish_date < date_str（已翻到历史数据）
        2) API success=false 或 html 空 或 解析出 0 条
        3) 达到 MAX_PAGES_PER_SOURCE（兜底，防失控）
        """
        results = []
        for page_no in range(1, MAX_PAGES_PER_SOURCE + 1):
            try:
                params = {
                    "webId": WEB_ID,
                    "pageId": page_id,
                    "parseType": "bulidstatic",
                    "pageType": "column",
                    "tagId": TAG_ID,
                    "tplSetId": TPL_SET_ID,
                    "paramJson": json.dumps({
                        "pageNo": page_no,
                        "pageSize": PAGE_SIZE,
                    }),
                }
                resp = requests.get(
                    API_URL, params=params, headers=HEADERS,
                    timeout=self.REQUEST_TIMEOUT, verify=False,
                )
                resp.raise_for_status()
                data = resp.json()
                if not data.get("success"):
                    break
                html_frag = (data.get("data") or {}).get("html", "")
                if not html_frag:
                    break
                page_items = self._parse_html_items(html_frag)
                if not page_items:
                    break

                stop = False
                for item in page_items:
                    pd = item.get("publish_date")
                    if pd == date_str:
                        results.append(item)
                    elif pd and pd < date_str:
                        # 此条及之后都是历史数据，本页处理完即停
                        stop = True
                if stop:
                    break
            except Exception as e:
                logger.warning(
                    f"jhggzy 翻页失败 page_id={page_id} pageNo={page_no}: {e}"
                )
                break
        return results
```

- [ ] **Step 2：Python REPL 验证（用真实 pageId 抓 1 个数据源）**

```bash
cd backend && python -c "
from app.scrapers.jhggzy import JhggzyScraper
from datetime import date
s = JhggzyScraper()
# 用东阳预公告 col1229847292 当 pageId，抓最近一天的数据
# 先看第 1 页有哪些日期，挑最新的一天做 date_str 验证
import json, requests, urllib3
urllib3.disable_warnings()
params = {'webId':'3818','pageId':'1229847292','parseType':'bulidstatic','pageType':'column','tagId':'概览信息列表','tplSetId':'LpcyxkYSwRoJNKPT7EX2v','paramJson':json.dumps({'pageNo':1,'pageSize':10})}
r = requests.get('http://ggzyjy.jinhua.gov.cn/api-gateway/jpaas-publish-server/front/page/build/unit', params=params, verify=False, timeout=30)
items = s._parse_html_items(r.json()['data']['html'])
latest = items[0]['publish_date']
print('latest_date_on_site=', latest)
got = s._fetch_source('1229847292', latest)
print('fetched_count=', len(got))
print('all_match_date=', all(it['publish_date']==latest for it in got))
"
```

Expected：`fetched_count >= 1`，`all_match_date=True`。具体条数取决于该日发布量。

- [ ] **Step 3：commit**

```bash
git add backend/app/scrapers/jhggzy.py
git commit -m "feat：jhggzy 实现 _fetch_source — 翻页 + 当日日期过滤 + 三类终止条件"
```

---

## Task 5：实现 `fetch` + `normalize`

**Files:**
- Modify: `backend/app/scrapers/jhggzy.py`

- [ ] **Step 1：用以下实现替换 `fetch` 方法体**

```python
    def fetch(self, day: date) -> list:
        """遍历 33 个数据源，返回原始记录列表。
        每条记录除 title/url/publish_date 外，额外带 _county / _type 元字段，
        供 normalize 使用。单数据源失败不影响其它。
        """
        results = []
        date_str = day.strftime("%Y-%m-%d")
        for county, ann_type, page_url in SOURCES:
            try:
                page_id = self._resolve_page_id(page_url)
                if not page_id:
                    logger.warning(f"jhggzy 跳过（无 pageId）: {county}/{ann_type}")
                    continue
                items = self._fetch_source(page_id, date_str)
                for item in items:
                    item["_county"] = county
                    item["_type"] = ann_type
                    results.append(item)
                if items:
                    logger.info(f"jhggzy {county}/{ann_type}: 抓到 {len(items)} 条")
            except Exception as e:
                logger.warning(f"jhggzy {county}/{ann_type} 抓取失败: {e}")
                continue
        return results
```

- [ ] **Step 2：用以下实现替换 `normalize` 方法体**

```python
    def normalize(self, raw: dict) -> Optional[ScrapeItem]:
        title = (raw.get("title") or "").strip()
        if not title:
            return None
        if is_result_announcement(title):
            return None
        if not match_keywords(title):
            return None

        county = raw.get("_county", "")
        ann_type = raw.get("_type", "")
        url = raw.get("url", "")
        full_url = BASE_URL + url if url.startswith("/") else url
        publish_date = parse_date_safe(raw.get("publish_date"))

        # artId（URL 里 32 位 hex）作为 external_no，用于去重
        art_match = re.search(r"art_([a-f0-9]+)\.html", url)
        external_no = f"art_{art_match.group(1)}" if art_match else None

        return ScrapeItem(
            project_name=title,
            bidding_type="公开招标",
            publish_platform_name="金华市公共资源交易网",
            region=f'["浙江省","金华市","{county}"]',
            external_no=external_no,
            source_url=full_url,
            publish_date=publish_date,
            description=(
                f"来源: ggzyjy.jinhua.gov.cn\n"
                f"类型: {ann_type}\n"
                f"县区: {county}\n"
                f"原始链接: {full_url}"
            ),
        )
```

- [ ] **Step 3：Python REPL 端到端验证（fetch → normalize 全链路）**

```bash
cd backend && python -c "
from app.scrapers.jhggzy import JhggzyScraper
from datetime import date, timedelta
s = JhggzyScraper()
# 用今天或昨天试抓（站点可能无当天数据，回退一天）
for offset in range(0, 8):
    d = date.today() - timedelta(days=offset)
    raws = s.fetch(d)
    print(f'{d}: raw_count={len(raws)}')
    if raws:
        normalized = [s.normalize(r) for r in raws]
        kept = [n for n in normalized if n]
        print(f'  kept_after_filter={len(kept)}')
        for n in kept[:3]:
            print(f'    - [{n.region}] {n.project_name[:50]}')
        break
"
```

Expected：能跑完不抛异常。`raw_count >= 0`；若找到当天有更新的日期，应能看到 `kept_after_filter` 数量（受关键词过滤影响，可能为 0 也正常）。看到至少一条 `kept` 输出格式正确即可。

确认点：
- `region` 格式为 `["浙江省","金华市","<县区>"]`
- `external_no` 形如 `art_<32hex>`
- `source_url` 是完整 URL（以 `http://` 开头）

- [ ] **Step 4：commit**

```bash
git add backend/app/scrapers/jhggzy.py
git commit -m "feat：jhggzy 实现 fetch + normalize — 遍历 33 数据源 + 关键词/结果过滤 + ScrapeItem 字段映射"
```

---

## Task 6：注册到 ScraperRegistry + 重启后端

**Files:**
- Modify: `backend/app/scrapers/__init__.py:23-28`（在 `_load_all` 的列表追加一项）

- [ ] **Step 1：编辑 `backend/app/scrapers/__init__.py`**

把 `_load_all` 里的列表从 4 项扩为 5 项：

```python
        for module_name, class_name in [
            ("ccgp", "CcgpScraper"),
            ("ggzy", "GgzyScraper"),
            ("jhygcg", "JhygcgScraper"),
            ("jhzjcs", "JhzjcsScraper"),
            ("jhggzy", "JhggzyScraper"),
        ]:
```

- [ ] **Step 2：重启 uvicorn**（按附录 A 操作）

- [ ] **Step 3：Python REPL 验证 registry 含 jhggzy**

```bash
cd backend && python -c "
from app.scrapers import ScraperRegistry
ScraperRegistry.reload()
names = [s.name for s in ScraperRegistry.all()]
print('all_scrapers=', names)
assert 'jhggzy' in names, 'jhggzy 未注册'
print('OK')
"
```

Expected：`all_scrapers= ['ccgp', 'ggzy', 'jhygcg', 'jhzjcs', 'jhggzy']`（顺序可能不同），最后输出 `OK`。

- [ ] **Step 4：验证后端启动日志无报错**

检查 uvicorn 输出，应看到：
```
INFO:app.scrapers:Loaded scraper: jhggzy
```

不应有 `Scraper jhggzy 加载失败` 警告。

- [ ] **Step 5：commit**

```bash
git add backend/app/scrapers/__init__.py
git commit -m "feat：注册 jhggzy scraper 到 ScraperRegistry"
```

---

## Task 7：端到端验证（真实抓取入库）

**Files:** 无改动（仅验证）

- [ ] **Step 1：确认后端运行中**

```bash
curl -s http://localhost:8000/docs -o /dev/null -w "%{http_code}\n"
```

Expected：`200`。若不是 200，按附录 A 重启。

- [ ] **Step 2：以 admin 身份登录拿 token**

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
echo "token_len=${#TOKEN}"
```

Expected：`token_len > 50`。

- [ ] **Step 3：触发抓取**

```bash
RUN_ID=$(curl -s -X POST http://localhost:8000/api/scrape/run \
  -H "Authorization: Bearer $TOKEN" | python -c "import sys,json; print(json.load(sys.stdin)['run_id'])")
echo "run_id=$RUN_ID"
```

Expected：返回 `run_id=<数字>`。若返回 409 表示已有 run 在跑，等几秒重试。若返回 403 表示非 admin。

- [ ] **Step 4：轮询抓取状态直到完成**

```bash
for i in $(seq 1 60); do
  STATUS=$(curl -s http://localhost:8000/api/scrape/status/$RUN_ID | python -c "import sys,json; d=json.load(sys.stdin); print(d.get('status','?'))")
  echo "[$i] status=$STATUS"
  [ "$STATUS" = "success" ] || [ "$STATUS" = "partial" ] || [ "$STATUS" = "failed" ] && break
  sleep 5
done
```

Expected：最终状态为 `success` / `partial` / `failed` 之一。jhggzy 单站点失败不影响整体（其它 4 站可能成功）。

- [ ] **Step 5：查 scrape_runs 表里 jhggzy 的统计**

```bash
curl -s http://localhost:8000/api/scrape/runs/$RUN_ID \
  -H "Authorization: Bearer $TOKEN" | python -c "
import sys, json
d = json.load(sys.stdin)
ss = d.get('sites_summary', {}) or {}
jh = ss.get('jhggzy', {})
print('jhggzy 统计:', jh)
print('整体 status:', d.get('status'))
print('整体 created/skipped/failed:', d.get('created_count'), d.get('skipped_count'), d.get('failed_count'))
"
```

Expected：`jhggzy 统计` 字典含 `fetched` / `created` / `skipped` / `failed` 4 个键（即使数据为 0 也要有键）。若 `fetched > 0` 且 `created = 0`，看 §Spec 风险表 — 多半是当天 33 个数据源都没新增。

- [ ] **Step 6：抽查入库的项目（若有 created）**

```bash
curl -s "http://localhost:8000/api/projects?source=jhggzy&page_size=5" \
  -H "Authorization: Bearer $TOKEN" | python -c "
import sys, json
d = json.load(sys.stdin)
for p in d.get('items', []):
    print(f\"id={p['id']} source={p.get('source')} region={p.get('region')} name={p['project_name'][:40]}\")
"
```

Expected：每条 `source=jhggzy`，`region` 含县区名，`project_name` 命中关键词。

> 本任务无代码改动，不 commit。

---

## Task 8：更新 CLAUDE.md

**Files:**
- Modify: `CLAUDE.md`（scrapers 段落 + 关键技术说明段）

- [ ] **Step 1：在 `scrapers/` 段落补充 jhggzy 模块说明**

定位 CLAUDE.md 里 `**\`scrapers/\`**` 段落（描述 BaseScraper 和站点模块的那段），把站点模块列表更新为：

> Site modules: `ccgp.py` (scrapling/curl_cffi), `ggzy.py` (requests + WAF), `jhygcg.py` (requests), `jhzjcs.py` (requests POST JSON API, direct `getComparePublicList` call), `jhggzy.py` (requests GET AJAX API, 11 县区 × 3 公告类型 = 33 数据源).

- [ ] **Step 2：在「Site-specific fetch details」段落追加 jhggzy 条目**

在该段末尾追加：

> - **jhggzy**: 金华市公共资源交易网 `ggzyjy.jinhua.gov.cn`（HTTP only，HTTPS 返回 410）。覆盖 11 县区分站（市本级/婺城/金东/兰溪/义乌/东阳/永康/浦江/武义/磐安/开发区）× 3 公告类型（招标文件预公示 / 招标公告 / 政府采购公告）= 33 个数据源，配置表硬编码在 `SOURCES`。API: `GET /api-gateway/jpaas-publish-server/front/page/build/unit` + `webId=3818` + `tplSetId=LpcyxkYSwRoJNKPT7EX2v` + `tagId=概览信息列表` + `paramJson={pageNo,pageSize}`，返回 `data.html` 为 HTML 片段，正则解析标题/URL/日期。**pageId 处理**：顶级栏目（预公告、采购公告）URL `/col/col<colId>/index.html` 的 pageId 直接 = colId；子路径栏目（招标公告）URL `/col/col<parent>/<sub>/index.html` 的 pageId 是 jcms 生成的哈希，需先 fetch 静态页从 `querydata` 属性解析，缓存到实例。当日增量模式：翻页直到 `publish_date < today` 终止。三类公告统一映射 `BiddingType.public`，差异写入 `description`。去重用 `external_no` = `art_<32hex>`（URL 里的文章 ID）。

- [ ] **Step 3：commit**

```bash
git add CLAUDE.md
git commit -m "docs：CLAUDE.md 增加 jhggzy scraper 说明"
```

---

## 附录 A：重启 uvicorn

后端 .py 改动后必须手动重启（不依赖 `--reload`，遵循用户偏好）。

```bash
# 1) 找到并杀掉占用 8000 端口的旧进程
PID=$(netstat -ano | grep ":8000 " | grep LISTENING | awk '{print $5}' | head -1)
if [ -n "$PID" ]; then
  echo "killing old uvicorn PID=$PID"
  taskkill //F //PID $PID
  sleep 2
fi

# 2) 后台启动新的 uvicorn
cd backend
nohup python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 > /tmp/uvicorn.log 2>&1 &
sleep 3

# 3) 验证启动成功
curl -s -o /dev/null -w "backend_http_code=%{http_code}\n" http://localhost:8000/docs
```

Expected：`backend_http_code=200`。若 502/拒绝连接，看 `/tmp/uvicorn.log` 排查（通常是语法错误或 import 失败）。

---

## 验收清单（全部 Task 完成后核对）

参考 Spec §8：

- [ ] `JhggzyScraper` 注册成功，`/api/scrape/run` 触发后 `scrape_runs.sites_summary` 含 `jhggzy` 键
- [ ] `JhggzyScraper().fetch(today)` 不抛异常（即使返回空列表）
- [ ] 至少一条公告走完入库流程（前提是当天有更新），项目列表可见 `source=jhggzy`、`source_url` 可点击、`region` 含县区
- [ ] 重复触发去重正确（同一 `external_no` 第二次抓取时被 `skipped`）
- [ ] 单个数据源失败（如某县区栏目临时 502）不影响其它 32 个，抓取历史详情中可看到对应失败记录
- [ ] `CLAUDE.md` 已更新 jhggzy 说明
