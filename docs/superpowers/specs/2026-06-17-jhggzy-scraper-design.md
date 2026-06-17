# 金华市公共资源交易网抓取模块（jhggzy）— 设计文档

## 1. 项目背景与目标

经营中心信息管理系统已集成 4 个招标信息抓取站点（ccgp / ggzy / jhygcg / jhzjcs）。本期新增第 5 个站点 — **金华市公共资源交易网**（`ggzyjy.jinhua.gov.cn`），覆盖金华市下辖 11 个县区分站的「招标文件预公示 / 招标公告 / 采购公告」三类公告。

本期目标：
- 新增 `jhggzy` scraper，纳入现有 `ScraperRegistry` 统一调度
- 复用现有抓取流程：`POST /api/scrape/run` 触发，`run_scraper` 编排，`scrape_runs` / `scrape_item_logs` 记录，`_find_duplicate` 去重
- 仅抓取**当天发布**的公告（与其它 scraper 一致的日增量模式）
- 关键词过滤后入库，状态默认 `跟进中`

### 1.1 关键决策（已与用户确认）

| 决策点 | 选择 | 理由 |
|--------|------|------|
| 抓取范围 | 全部 33 个数据源 | 11 县区 ×（预公告 + 招标公告 + 采购公告）。覆盖最全 |
| 关键词过滤 | 保留（检测/人防/防雷/消防/勘察/测绘/监测/鉴定/评估/试验） | 与 `jhygcg` 一致，过滤后剩小几条 |
| 时间范围 | 仅当天 | 与其它 scraper 一致，日增量模式 |
| Scraper 命名 | `jhggzy` | 金华公共资源交易拼音首字母，与 `jhygcg`/`jhzjcs` 风格一致 |
| 实现方式 | `requests` + AJAX API（无 Playwright） | API 返回 JSON，HTML 片段在 `data.html` 字段，无需浏览器渲染 |
| pageId 获取 | 运行时 fetch 静态页解析 `querydata` | 子路径栏目（招标公告）的 pageId 是哈希，不能 hardcode |

### 1.2 不在本期范围

- 不做历史数据回溯（仅日增量）
- 不做县区筛选 UI（数据本身按县区分，落地后用 region 字段区分）
- 不做中标/成交公告抓取（被 `is_result_announcement` 过滤）
- 不修改 `BiddingType` 枚举（三类公告统一映射 `公开招标`，差异写入 `description`）

---

## 2. 站点结构

### 2.1 栏目层级

```
金华市公共资源交易网 (ggzyjy.jinhua.gov.cn)
├── 交易信息
│   ├── 限额以下工程（11 县区分站）
│   │   └── 每县区下：预公告 + 招标公告 + 补充公告 + 中标候选人公示 + 中标结果公告
│   └── 政府采购（11 县区分站）
│       └── 每县区下：采购公告 + 中标公告 + 更正公告 + 合同公告
```

- **限额以下工程**：每个县区都有「预公告 + 招标公告」两个目标子栏目
- **政府采购**：用户明确「没有预公告，只有采购公告」，每县区仅抓「采购公告」

### 2.2 县区列表（11 个）

市本级 / 婺城区 / 金东区 / 兰溪市 / 义乌市 / 东阳市 / 永康市 / 浦江县 / 武义县 / 磐安县 / 开发区

---

## 3. 数据源映射表（33 个）

每个数据源是一个 4 元组：`(county, type, page_url, region_label)`。

### 3.1 限额以下工程 — 预公告（11 个）

| 县区 | colId | URL |
|---|---|---|
| 市本级 | 1229840390 | `/col/col1229840390/index.html` |
| 婺城区 | 1229847283 | `/col/col1229847283/index.html` |
| 金东区 | 1229847286 | `/col/col1229847286/index.html` |
| 兰溪市 | 1229847305 | `/col/col1229847305/index.html` |
| 义乌市 | 1229847289 | `/col/col1229847289/index.html` |
| 东阳市 | 1229847292 | `/col/col1229847292/index.html` |
| 永康市 | 1229847296 | `/col/col1229847296/index.html` |
| 浦江县 | 1229847308 | `/col/col1229847308/index.html` |
| 武义县 | 1229847320 | `/col/col1229847320/index.html` |
| 磐安县 | 1229847312 | `/col/col1229847312/index.html` |
| 开发区 | 1229847325 | `/col/col1229847325/index.html` |

> 预公告 URL 形如 `/col/col<colId>/index.html`（顶级栏目），`querydata.pageId = colId`，可直接用。

### 3.2 限额以下工程 — 招标公告（11 个）

| 县区 | 父 colId | 子路径 | URL |
|---|---|---|---|
| 市本级 | 1229633710 | zbggbzlm20 | `/col/col1229633710/zbggbzlm20/index.html` |
| 婺城区 | 1229633750 | zbggbzlm518 | `/col/col1229633750/zbggbzlm518/index.html` |
| 金东区 | 1229641886 | zbggbzlm521 | `/col/col1229641886/zbggbzlm521/index.html` |
| 兰溪市 | 1229641981 | zbggbzlm261 | `/col/col1229641981/zbggbzlm261/index.html` |
| 义乌市 | 1229641912 | zbggbzlm525 | `/col/col1229641912/zbggbzlm525/index.html` |
| 东阳市 | 1229641936 | zbggbzlm267 | `/col/col1229641936/zbggbzlm267/index.html` |
| 永康市 | 1229641958 | zbggbzlm603 | `/col/col1229641958/zbggbzlm603/index.html` |
| 浦江县 | 1229642012 | zbggbzlm844 | `/col/col1229642012/zbggbzlm844/index.html` |
| 武义县 | 1229642061 | zbggbzlm137 | `/col/col1229642061/zbggbzlm137/index.html` |
| 磐安县 | 1229642033 | zbggbzlm536 | `/col/col1229642033/zbggbzlm536/index.html` |
| 开发区 | 1229642081 | zbggbzlm77 | `/col/col1229642081/zbggbzlm77/index.html` |

> 招标公告 URL 形如 `/col/col<parentColId>/<subCode>/index.html`（子路径栏目），`querydata.pageId` 是 jcms 后端生成的哈希字符串（每个栏目不同），**必须 fetch 静态页解析**。

### 3.3 政府采购 — 采购公告（11 个）

| 县区 | colId | URL |
|---|---|---|
| 市本级 | 1229641558 | `/col/col1229641558/index.html` |
| 婺城区 | 1229641872 | `/col/col1229641872/index.html` |
| 金东区 | 1229641890 | `/col/col1229641890/index.html` |
| 兰溪市 | 1229641985 | `/col/col1229641985/index.html` |
| 义乌市 | 1229641916 | `/col/col1229641916/index.html` |
| 东阳市 | 1229641940 | `/col/col1229641940/index.html` |
| 永康市 | 1229641962 | `/col/col1229641962/index.html` |
| 浦江县 | 1229642016 | `/col/col1229642016/index.html` |
| 武义县 | 1229642065 | `/col/col1229642065/index.html` |
| 磐安县 | 1229642037 | `/col/col1229642037/index.html` |
| 开发区 | 1229642085 | `/col/col1229642085/index.html` |

> 采购公告 URL 形如 `/col/col<colId>/index.html`（顶级栏目），`querydata.pageId = colId`，可直接用。

---

## 4. AJAX API 协议

### 4.1 端点

```
GET http://ggzyjy.jinhua.gov.cn/api-gateway/jpaas-publish-server/front/page/build/unit
```

站点仅 HTTP（HTTPS 返回 410 Gone），需 `verify=False` + 抑制 InsecureRequestWarning。

### 4.2 请求参数（query string）

| 参数 | 值 | 说明 |
|---|---|---|
| `webId` | `3818` | 站点 ID，全站固定 |
| `pageId` | `<colId>` 或 `<hash>` | 见 §3，预公告/采购公告用 colId；招标公告需从静态页 querydata 解析 |
| `parseType` | `bulidstatic` | 固定（注意原站点拼写就是 `bulid`，不是 `build`） |
| `pageType` | `column` | 固定 |
| `tagId` | `概览信息列表` | URL 编码后的中文，固定 |
| `tplSetId` | `LpcyxkYSwRoJNKPT7EX2v` | 模板集 ID，全站固定 |
| `paramJson` | `{"pageNo":N,"pageSize":10}` | JSON 字符串 |

### 4.3 响应

```json
{
  "success": true,
  "code": "200",
  "message": "生成成功",
  "data": {
    "html": "<div class='page-content'>... <a href='/col/colXXX/art/YYYY/art_<32hex>.html' title='...'>标题</a> ... 2026-MM-DD ...</div>"
  }
}
```

`data.html` 是 HTML 片段，包含本页 10 条公告，每条含：
- `<a href="...">` 文章 URL（含 32 位 hex 的 artId，作为 external_no）
- 标题（`title` 属性或文本）
- 发布日期（`2026-MM-DD` 格式穿插在文本中）

### 4.4 pageId 解析（仅招标公告子栏目需要）

fetch 招标公告静态页 HTML，正则匹配：

```python
m = re.search(r"querydata=\"([^\"]+)\"", html)
qd = m.group(1).replace("'", '"')  # 单引号转双引号
qd_json = json.loads(qd)
page_id = qd_json['pageId']  # 哈希字符串
```

可缓存到 scraper 实例的 dict（key=URL，value=pageId），同一次 run 内复用。

---

## 5. Scraper 设计

### 5.1 文件结构

```
backend/app/scrapers/
├── jhggzy.py            ← 新增（本模块主体）
├── __init__.py          ← 改：注册 JhggzyScraper
└── base.py              ← 不改（复用 match_keywords / is_result_announcement / parse_date_safe / fetch_with_retry）
```

### 5.2 `jhggzy.py` 主要内容

#### 5.2.1 常量

```python
API_URL = "http://ggzyjy.jinhua.gov.cn/api-gateway/jpaas-publish-server/front/page/build/unit"
WEB_ID = "3818"
TPL_SET_ID = "LpcyxkYSwRoJNKPT7EX2v"
TAG_ID = "概览信息列表"
PAGE_SIZE = 10
MAX_PAGES_PER_SOURCE = 30  # 兜底，单数据源最多翻 30 页
BASE_URL = "http://ggzyjy.jinhua.gov.cn"
HEADERS = {
    "User-Agent": "Mozilla/5.0 ... Chrome/120.0 Safari/537.36",
    "Referer": BASE_URL,
    "X-Requested-With": "XMLHttpRequest",
    "Accept": "application/json",
}

# 33 个数据源（county, type, page_url）— 完整 URL 见本设计 §3.1 / §3.2 / §3.3
SOURCES = [
    # 预公告 11 行（§3.1）— URL 形如 /col/col<colId>/index.html
    ("市本级",  "预公告",   "/col/col1229840390/index.html"),
    ("婺城区",  "预公告",   "/col/col1229847283/index.html"),
    ("金东区",  "预公告",   "/col/col1229847286/index.html"),
    ("兰溪市",  "预公告",   "/col/col1229847305/index.html"),
    ("义乌市",  "预公告",   "/col/col1229847289/index.html"),
    ("东阳市",  "预公告",   "/col/col1229847292/index.html"),
    ("永康市",  "预公告",   "/col/col1229847296/index.html"),
    ("浦江县",  "预公告",   "/col/col1229847308/index.html"),
    ("武义县",  "预公告",   "/col/col1229847320/index.html"),
    ("磐安县",  "预公告",   "/col/col1229847312/index.html"),
    ("开发区",  "预公告",   "/col/col1229847325/index.html"),
    # 招标公告 11 行（§3.2）— URL 形如 /col/col<parentColId>/<subCode>/index.html
    ("市本级",  "招标公告", "/col/col1229633710/zbggbzlm20/index.html"),
    ("婺城区",  "招标公告", "/col/col1229633750/zbggbzlm518/index.html"),
    ("金东区",  "招标公告", "/col/col1229641886/zbggbzlm521/index.html"),
    ("兰溪市",  "招标公告", "/col/col1229641981/zbggbzlm261/index.html"),
    ("义乌市",  "招标公告", "/col/col1229641912/zbggbzlm525/index.html"),
    ("东阳市",  "招标公告", "/col/col1229641936/zbggbzlm267/index.html"),
    ("永康市",  "招标公告", "/col/col1229641958/zbggbzlm603/index.html"),
    ("浦江县",  "招标公告", "/col/col1229642012/zbggbzlm844/index.html"),
    ("武义县",  "招标公告", "/col/col1229642061/zbggbzlm137/index.html"),
    ("磐安县",  "招标公告", "/col/col1229642033/zbggbzlm536/index.html"),
    ("开发区",  "招标公告", "/col/col1229642081/zbggbzlm77/index.html"),
    # 采购公告 11 行（§3.3）— URL 形如 /col/col<colId>/index.html
    ("市本级",  "采购公告", "/col/col1229641558/index.html"),
    ("婺城区",  "采购公告", "/col/col1229641872/index.html"),
    ("金东区",  "采购公告", "/col/col1229641890/index.html"),
    ("兰溪市",  "采购公告", "/col/col1229641985/index.html"),
    ("义乌市",  "采购公告", "/col/col1229641916/index.html"),
    ("东阳市",  "采购公告", "/col/col1229641940/index.html"),
    ("永康市",  "采购公告", "/col/col1229641962/index.html"),
    ("浦江县",  "采购公告", "/col/col1229642016/index.html"),
    ("武义县",  "采购公告", "/col/col1229642065/index.html"),
    ("磐安县",  "采购公告", "/col/col1229642037/index.html"),
    ("开发区",  "采购公告", "/col/col1229642085/index.html"),
]
```

#### 5.2.2 `JhggzyScraper` 类

```python
class JhggzyScraper(BaseScraper):
    name = "jhggzy"
    requires_playwright = False

    def __init__(self):
        super().__init__()
        self._page_id_cache = {}  # url -> pageId（同一次进程内复用）

    def fetch(self, day: date) -> list[dict]:
        """遍历 33 个数据源，返回原始记录列表。"""
        results = []
        date_str = day.strftime("%Y-%m-%d")
        for county, ann_type, page_url in SOURCES:
            try:
                page_id = self._resolve_page_id(page_url)
                for item in self._fetch_source(page_id, date_str):
                    item["_county"] = county
                    item["_type"] = ann_type
                    item["_source_url_prefix"] = page_url
                    results.append(item)
            except Exception as e:
                logger.warning(f"jhggzy {county}/{ann_type} 抓取失败: {e}")
                continue
        return results

    def normalize(self, raw: dict) -> Optional[ScrapeItem]:
        title = (raw.get("title") or "").strip()
        if not title:
            return None
        if is_result_announcement(title):
            return None
        if not match_keywords(title):
            return None
        # ... 构造 ScrapeItem
```

#### 5.2.3 关键方法

- `_resolve_page_id(page_url) -> str`：
  - 若 URL 形如 `/col/col<colId>/index.html`（顶级），直接返回 colId（无需网络请求）
  - 若 URL 含子路径（如 `/zbggbzlm20/`），fetch 静态页 → 正则解析 querydata.pageId → 缓存
- `_fetch_source(page_id, date_str) -> iterator[dict]`：
  - 翻页 `pageNo=1,2,...`，调 AJAX API
  - 解析 `data.html` 提取 `(title, url, publish_date)`
  - **终止条件**：① 某条 publish_date < date_str（说明已翻到历史数据，停）；② API 返回空；③ 达到 MAX_PAGES_PER_SOURCE
- `_parse_html_items(html_frag) -> list[dict]`：
  - 用正则提取 `<a href="(.*?art_[a-f0-9]+\.html)"[^>]*>(.*?)</a>` + 相邻 `(\d{4}-\d{2}-\d{2})`
  - 返回 `[{title, url, publish_date}, ...]`

### 5.3 `normalize` 字段映射

```python
ScrapeItem(
    project_name=title,
    bidding_type="公开招标",   # 三类统一，不新增 enum
    publish_platform_name="金华市公共资源交易网",
    region=f'["浙江省","金华市","{county}"]',
    external_no=art_id,       # URL 中的 32 位 hex，如 art_9f52b7fdcc874cc7bc3438f2c99d073b
    source_url=full_url,      # 拼接 BASE_URL
    publish_date=parsed_date,
    description=(
        f"来源: ggzyjy.jinhua.gov.cn\n"
        f"类型: {ann_type}\n"          # 预公告 / 招标公告 / 采购公告
        f"县区: {county}\n"
        f"原始链接: {full_url}"
    ),
)
```

---

## 6. 整合到后端

### 6.1 ScraperRegistry 注册

`backend/app/scrapers/__init__.py` 在 `_load_all` 的列表中追加一行：

```python
for module_name, class_name in [
    ("ccgp", "CcgpScraper"),
    ("ggzy", "GgzyScraper"),
    ("jhygcg", "JhygcgScraper"),
    ("jhzjcs", "JhzjcsScraper"),
    ("jhggzy", "JhggzyScraper"),   # ← 新增
]:
```

注册后，`run_scraper` 自动遍历该 scraper（通过 `ScraperRegistry.all()`），无需改 `services/scrape_runner.py`。

### 6.2 不需要改动的部分

以下组件对 scraper 是透明的，**无需修改**：

| 组件 | 原因 |
|---|---|
| `api/scrape.py` | `POST /api/scrape/run` 通过 `ScraperRegistry.all()` 调度，新 scraper 自动纳入 |
| `services/scrape_runner.py` | `run_scraper` 循环每个 scraper 调用 `fetch_with_retry` → `normalize` → `_process_item`，逻辑通用 |
| `services/org_matcher.py` | 不涉及组织匹配（公告阶段无投标单位） |
| 数据库表 | 复用 `project_infos` + `scrape_runs` + `scrape_item_logs`，无 schema 变更 |
| `models/project.py` | 无需改 `BiddingType`（三类都用 `public`）|
| 前端 | 「抓取招标信息」按钮 + 抓取历史页面，新 scraper 自动出现在 `sites_summary` 统计中 |

### 6.3 去重

走 `scrape_runner._find_duplicate`：先查 `external_no`（artId，如 `art_9f52b7fdcc874cc7bc3438f2c99d073b`），再查 project_name 精确匹配。

artId 是公告级唯一标识（32 位 hex），跨县区不冲突，去重可靠。

### 6.4 错误隔离

`ScraperRegistry._load_all` 已是 try/except 包裹，单个 scraper import 失败不影响其它。`jhggzy.py` 内部对每个数据源 try/except，单个县区/类型失败不影响其它 32 个，失败记入 `scrape_item_logs`。

---

## 7. 风险与对策

| 风险 | 对策 |
|---|---|
| pageId 哈希值站点重建后变化 | 运行时 fetch 静态页解析（不 hardcode）；解析失败时该数据源跳过并告警 |
| 33 个数据源顺序抓取耗时 | 估算 33 × 平均 2 页 × ~0.5s/请求 ≈ 33s，可接受；不引入并发保持简单 |
| HTTP 站点偶发 502/超时 | `BaseScraper.fetch_with_retry` 已有 3 次重试 + 指数退避 |
| 关键词过滤误杀 | 预公告/招标公告/采购公告的标题本身含项目类型词（"检测"、"监理"等），过滤命中率高；漏抓由用户在抓取历史中查 `scrape_item_logs` 排查 |
| 部分县区栏目长期无更新 | 翻到第 1 页就发现无当天数据，立即终止该数据源，不影响整体 |

---

## 8. 验收标准

1. `JhggzyScraper` 注册成功，`/api/scrape/run` 触发后能在 `scrape_runs.sites_summary` 中看到 `jhggzy` 统计
2. 单元层面：手动调用 `JhggzyScraper().fetch(today)` 返回非空列表（前提是当天确有更新）
3. 至少一条公告走完入库流程，能在项目列表中看到 `source=jhggzy`、`source_url` 可点击、`region` 含正确县区
4. 重复触发去重正确（同一 artId 第二次抓取时被 `skipped`）
5. 单个数据源失败不影响其它 32 个
