# 招标信息自动抓取集成系统 — 设计文档

## 1. 项目背景与目标

经营中心信息管理系统当前依赖人工录入招标项目信息。团队此前在 Claude Code REPL 中使用 `/scrape` skill（位于 `.superpowers/skills/bid-scraper/`）从 4 个招标网站抓取当日新增公告，但 skill 只能在开发者终端中运行，无法让普通团队成员使用。

本设计将 `/scrape` skill 集成到系统中，实现：

- 在系统 UI 中点击按钮触发抓取
- 后台自动从 4 个招标网站抓取当日新增公告
- 关键词 + 地区（浙江省）过滤后，自动创建新项目入库
- 抓取历史可追溯，失败原因可排查

### 1.1 关键决策（已与用户确认）

| 决策点 | 选择 | 理由 |
|--------|------|------|
| 触发方式 | 按钮触发（非定时） | 团队规模小，每天人工点一次即可；不引入 APScheduler 复杂度 |
| 入库方式 | 全自动入库（非审核队列） | 抓取的项目初始状态为「跟进中」，用户可在列表中自行跟进或放弃 |
| 去重策略 | 项目编号优先，名称兜底 | 项目编号是最稳定的标识；名称仅做精确匹配，不做模糊匹配（避免误杀） |
| 站点范围 | 保留全部 4 个站点 | 接受 Playwright 重依赖（仅 jhzjcs 站点使用，延迟导入避免影响后端启动） |
| 进度反馈 | scrape_runs 表 + 历史页面 | 用户希望看到每次抓取的统计与失败原因 |
| 实施方案 | 方案 A — 每站点一个模块 + FastAPI BackgroundTasks | 与现有代码风格一致，不引入 Celery/Redis |

### 1.2 不在本期范围

- 不做定时任务（未来如需定时，再加 APScheduler）
- 不做邮件/IM 推送通知
- 不做反爬虫升级（UA 轮换、IP 代理池等）
- 不做模糊匹配去重（避免误杀，事后人工处理）

---

## 2. 数据模型

### 2.1 `project_infos` 表新增 3 字段

通过 `main.py` `on_startup` 自动迁移（ALTER TABLE，与现有迁移块风格一致）：

| 字段 | 类型 | 说明 |
|------|------|------|
| `external_no` | String(100), indexed (`ix_project_external_no`) | 外部公告编号，来自抓取站点，用于去重 |
| `source` | String(50) | 来源站点标识：`ccgp` / `ggzy` / `jhzjcs` / `jhygcg` / `manual` |
| `source_url` | String(500) | 原始公告链接 |

约束：
- 手动新建项目时 `source` 默认 `manual`，`external_no` / `source_url` 留空
- `ProjectResponse` schema 暴露这 3 字段（只读）
- 已存在历史项目的这 3 字段在迁移时默认为 NULL / `manual`（由迁移 SQL 处理）

### 2.2 新表 `scrape_runs`

记录每次抓取运行的整体状态。

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | Integer PK | |
| `started_at` | DateTime | 开始时间 |
| `finished_at` | DateTime nullable | 结束时间（NULL 表示未完成） |
| `triggered_by` | Integer FK→users.id | 触发用户 |
| `status` | String(20) | `running` / `success` / `partial` / `failed` |
| `total_count` | Integer default 0 | 抓取到的公告总数 |
| `created_count` | Integer default 0 | 新建入库数 |
| `skipped_count` | Integer default 0 | 去重跳过数 |
| `failed_count` | Integer default 0 | 入库失败数 |
| `sites_summary` | Text (JSON) | 每站点统计，如 `{"ccgp": {"fetched": 12, "created": 8, "skipped": 4, "failed": 0}}` |
| `error_summary` | Text (JSON) | 每站点的失败原因，如 `{"ccgp": "connection timeout after 3 retries"}` |

### 2.3 新表 `scrape_item_logs`

记录本次 run 中每条公告的处理明细。

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | Integer PK | |
| `run_id` | Integer FK→scrape_runs.id (ON DELETE CASCADE) | |
| `source` | String(50) | 站点标识 |
| `external_no` | String(100) nullable | 公告编号 |
| `project_name` | String(200) | 项目名称 |
| `source_url` | String(500) nullable | 原始链接 |
| `result` | String(20) | `created` / `skipped` / `failed` |
| `project_id` | Integer FK→project_infos.id nullable | 关联创建的项目（created 时填） |
| `skip_reason` | String(100) nullable | skipped 原因 |
| `error_message` | Text nullable | failed 时的错误信息 |
| `processed_at` | DateTime | 处理时间 |

两个新表通过 `main.py` `on_startup` 的 `Base.metadata.create_all` 自动创建（与现有 user/organization 等表创建逻辑一致）。

---

## 3. 抓取流程

### 3.1 整体流程

```
[前端按钮] → POST /api/scrape/run
                ↓
        立即返回 {run_id}（状态 running）
                ↓
        FastAPI BackgroundTasks 异步执行 run_scraper(run_id, user_id)
                ↓
        前端每 2 秒轮询 GET /api/scrape/status/{run_id}
                ↓
        run 完成 → 前端展示最终统计
```

为什么用 BackgroundTasks 而不是 Celery：
- 单进程内即可异步执行，不引入消息中间件
- 抓取任务串行执行（不要求并发），BackgroundTasks 足够
- 进程重启时通过孤儿 run 清理逻辑兜底

### 3.2 `BaseScraper` 抽象基类

位于 `backend/app/scrapers/base.py`：

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
import time

class SiteFetchError(Exception):
    """站点级抓取失败异常。"""

@dataclass
class ScrapeItem:
    project_name: str
    bidding_type: str = "公开招标"
    bidding_unit_name: str | None = None
    agency_name: str | None = None
    publish_platform_name: str | None = None
    region: str | None = None       # JSON 字符串，如 '["浙江省","杭州市"]'
    external_no: str | None = None
    source_url: str | None = None
    budget_amount: float | None = None
    registration_deadline: date | None = None
    bid_deadline: date | None = None
    publish_date: date | None = None
    description: str | None = None  # 含项目编号 + 来源 + 原始链接

class BaseScraper(ABC):
    name: str                    # ccgp / ggzy / jhzjcs / jhygcg
    requires_playwright: bool = False

    @abstractmethod
    def fetch(self, day: date) -> list[dict]:
        """抓取指定日期的原始公告列表。"""

    @abstractmethod
    def normalize(self, raw: dict) -> ScrapeItem | None:
        """原始数据 → ScrapeItem。返回 None 表示过滤掉（非浙江、非检测类等）。"""

    MAX_RETRIES = 3
    RETRY_DELAY = 2  # 秒

    def fetch_with_retry(self, day: date) -> list[dict]:
        for attempt in range(self.MAX_RETRIES):
            try:
                return self.fetch(day)
            except Exception as e:
                if attempt == self.MAX_RETRIES - 1:
                    raise SiteFetchError(f"{self.name} 第 {attempt+1} 次失败: {e}")
                time.sleep(self.RETRY_DELAY * (attempt + 1))
```

### 3.3 站点 → 模块映射

| 站点 | 文件 | 技术 | 关键挑战 |
|------|------|------|---------|
| `ccgp.gov.cn`（中国政府采购网） | `scrapers/ccgp.py` | scrapling（curl_cffi 浏览器指纹） | 反爬较严，需模拟浏览器指纹 |
| `ggzy.zj.gov.cn`（浙江公共资源交易网） | `scrapers/ggzy.py` | requests + WAF 绕过 | WAF 拦截，需正确 UA + headers |
| `jhzjcs.ggzyjy.jinhua.gov.cn`（金华中介超市） | `scrapers/jhzjcs.py` | Playwright + 系统 Chrome | 动态渲染，必须真实浏览器 |
| `jhygcg.com`（金华阳光采购） | `scrapers/jhygcg.py` | requests | 相对简单 |

**Playwright 延迟导入策略**：playwright 仅在 `jhzjcs.py` 的 `fetch()` 方法内 `import`，避免后端启动依赖 playwright 装包。`pip install` 时如未装 playwright，后端可正常启动，只影响 jhzjcs 站点（该站点失败被记入 `error_summary`）。

### 3.4 关键词与地区过滤

位于 `scrapers/base.py` 作为共享 helper：

```python
KEYWORDS = ["检测", "人防", "防雷", "消防", "勘察", "测绘", "监测", "鉴定", "评估", "试验"]

def match_keywords(text: str) -> bool:
    """标题/描述中包含任一关键词即匹配（OR 逻辑）。"""
    return any(kw in text for kw in KEYWORDS)

def match_region_zhejiang(region_text: str | None, extra: dict | None = None) -> bool:
    """浙江地区判断。支持多种信号源：
    - 标题/地区文本含「浙江」或浙江下属市县
    - CCGP zoneId 为 330000 系列
    - GGZY infoc 含 330
    """
```

每个 scraper 在 `normalize()` 中调用这两个 helper，不匹配则返回 `None`。

### 3.5 入库主流程

位于 `backend/app/services/scrape_runner.py`：

```python
def run_scraper(run_id: int, user_id: int):
    db = SessionLocal()
    run = db.get(ScrapeRun, run_id)
    try:
        scrapers = ScraperRegistry.all()  # [ccgp, ggzy, jhzjcs, jhygcg]
        day = date.today()
        for scraper in scrapers:
            site_stat = {"fetched": 0, "created": 0, "skipped": 0, "failed": 0}
            try:
                raw_list = scraper.fetch_with_retry(day)
                site_stat["fetched"] = len(raw_list)
                for raw in raw_list:
                    _try_process_one(db, run, scraper, raw, site_stat)
                run.sites_summary[scraper.name] = site_stat
                db.commit()  # 每站点提交一次
            except SiteFetchError as e:
                run.error_summary[scraper.name] = str(e)
                logger.warning(f"{scraper.name} site failed: {e}")
        run.status = _derive_run_status(run)
        run.finished_at = datetime.now()
        db.commit()
    except Exception as e:
        run.status = "failed"
        run.error_summary["system"] = f"run_scraper crashed: {e}"
        run.finished_at = datetime.now()
        db.commit()
        logger.exception("run_scraper crashed")
    finally:
        db.close()


def _try_process_one(db, run, scraper, raw, site_stat):
    """处理单条 raw 公告。三种结果：created / skipped / failed。
    不变量（run 级）：total_count = created_count + skipped_count + failed_count。
    """
    try:
        item = scraper.normalize(raw)
    except Exception as e:
        # normalize 失败：记 failed 日志（用 raw 中可获取的信息），继续下一条
        _record_failure(db, run, scraper.name, raw, f"normalize 失败: {e}")
        site_stat["failed"] += 1
        logger.exception("normalize failed")
        return
    if item is None:
        return  # 被关键词/地区过滤，不计入任何统计
    try:
        ok = _process_item(db, run, item, scraper.name)
        site_stat["created" if ok else "skipped"] += 1
    except Exception as e:
        # 入库失败：回滚项目事务，记 failed 日志，继续下一条
        db.rollback()
        _record_failure(db, run, scraper.name, item, str(e))
        site_stat["failed"] += 1
        logger.exception("process item failed")
```

**不变量**：`run.total_count == run.created_count + run.skipped_count + run.failed_count`。`_process_item` 内部递增 `created_count`/`skipped_count`/`total_count`，`_record_failure` 递增 `failed_count`/`total_count`。具体递增点在实施时统一管理（建议在 `_process_item` 和 `_record_failure` 内部各管各的，保证不变量成立）。

**辅助 helper**：
- `_record_failure(db, run, source, item_or_raw, error_message)`：写 `scrape_item_logs` 一行（result=failed），并递增 `run.failed_count` / `run.total_count`。`item_or_raw` 可以是 `ScrapeItem`（process 阶段失败）或 `dict`（normalize 阶段失败，从中尽力提取 project_name/source_url）
- `_log_item(db, run, item, source, result, **kwargs)`：写 `scrape_item_logs` 通用函数

### 3.6 单条项目处理

```python
def _process_item(db, run, item: ScrapeItem, source: str) -> bool:
    """返回 True=created, False=skipped。失败时抛异常由调用方处理。
    注意：run 的 counter 递增由调用方 _try_process_one 统一管理（见不变量说明）。"""
    # 1) 去重
    dup = _find_duplicate(db, item)
    if dup:
        _log_item(db, run, item, source, "skipped",
                  skip_reason=_skip_reason_for(dup, item))
        return False
    # 2) 匹配/创建组织
    bidding_unit_id = _match_or_create_org(db, item.bidding_unit_name, "external")
    agency_id = _match_or_create_org(db, item.agency_name, "external")
    platform_id = _match_or_create_platform(db, item.publish_platform_name)
    # 3) 创建项目（初始状态：跟进中）
    project = ProjectInfo(
        bidding_type=item.bidding_type,
        project_name=item.project_name,
        bidding_unit_id=bidding_unit_id,
        agency_id=agency_id,
        publish_platform_id=platform_id,
        region=item.region,
        external_no=item.external_no,
        source=source,
        source_url=item.source_url,
        budget_amount=item.budget_amount,
        registration_deadline=item.registration_deadline,
        bid_deadline=item.bid_deadline,
        publish_date=item.publish_date,
        description=item.description,
        status=ProjectStatus.following,
    )
    db.add(project)
    db.flush()
    _log_item(db, run, item, source, "created", project_id=project.id)
    return True
```

**复用已有 helper**：
- `_match_or_create_org` / `_match_or_create_platform` 已在 `api/documents.py` 实现，如签名不完全匹配则提取到 `services/org_matcher.py` 共享
- `ProjectStatus.following` 等枚举已定义在 `models/project.py`

---

## 4. 去重逻辑

### 4.1 算法

```python
def _find_duplicate(db, item: ScrapeItem) -> ProjectInfo | None:
    # 1) 项目编号精确匹配（最高优先级）
    if item.external_no:
        dup = db.query(ProjectInfo).filter(
            ProjectInfo.external_no == item.external_no
        ).first()
        if dup:
            return dup
    # 2) 项目名称精确匹配（兜底）
    if item.project_name:
        dup = db.query(ProjectInfo).filter(
            ProjectInfo.project_name == item.project_name
        ).first()
        if dup:
            return dup
    return None
```

`external_no` 字段有索引 `ix_project_external_no`，查询性能 OK。项目名称当前无索引，数据量小（每天几十条）不必加。

### 4.2 边界处理

| 场景 | 行为 | skip_reason |
|------|------|-------------|
| 项目编号相同 | 跳过 | `external_no 重复` |
| 项目编号为空 + 名称完全相同 | 跳过 | `名称重复` |
| 项目编号为空 + 名称仅相似 | **不判重**，创建新项目 | — |
| 之前抓取失败没入库，本次重试 | 正常检查，无重复则创建 | — |
| 已放弃（status=已放弃）的同编号项目 | 仍判重，跳过 | `external_no 重复（已放弃）` |

**为什么不做模糊匹配**：
- 「XY 检测」vs「XY 检测服务」可能确实是不同标段
- 模糊匹配算法（如 Levenshtein）需要调阈值，误判风险高
- 系统数据量小，事后人工去重成本低
- 跳过项都记录在 `scrape_item_logs`，可追溯补救

### 4.3 不更新策略

**发现重复时，不更新已有项目的任何字段。**

理由：
1. 用户可能已手动修改（跟进状态、负责人、备注等），覆盖会丢失人工数据
2. 招标公告可能二次修正，但用户已跟进的项目以实际跟进信息为准
3. 需查最新信息可从 `scrape_item_logs.source_url` 跳转原始公告

如未来确实需要更新，再加单独的「同步最新公告」按钮，显式触发。

---

## 5. API 设计

新增 `backend/app/api/scrape.py`：

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| `POST` | `/api/scrape/run` | 触发一次抓取，立即返回 `{run_id}`，后台异步执行 | 管理员 |
| `GET` | `/api/scrape/status/{run_id}` | 查询某次 run 状态（轮询用） | 登录用户 |
| `GET` | `/api/scrape/runs` | 抓取历史列表（分页，按 started_at desc） | 登录用户 |
| `GET` | `/api/scrape/runs/{run_id}` | 单次 run 详情（含 item_logs） | 登录用户 |

### 5.1 触发端点

```python
@router.post("/run")
def trigger_scrape(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    # 防止并发：如果已有 running 状态的 run，拒绝
    existing = db.query(ScrapeRun).filter(ScrapeRun.status == "running").first()
    if existing:
        raise HTTPException(409, f"已有抓取任务进行中 (run_id={existing.id})")
    run = ScrapeRun(
        started_at=datetime.now(),
        triggered_by=user.id,
        status="running",
        total_count=0, created_count=0, skipped_count=0, failed_count=0,
        sites_summary={},
        error_summary={},
    )
    db.add(run); db.commit(); db.refresh(run)
    request.app.background_tasks.add_task(run_scraper, run.id, user.id)
    return {"run_id": run.id, "status": "running"}
```

注：FastAPI BackgroundTasks 通过函数参数 `bg: BackgroundTasks` 注入（FastAPI 自动识别类型并实例化），任务会在响应发送给客户端后执行。这是 FastAPI 的标准用法，无需 `request.app.state` 或手动管理。

### 5.2 状态推导

```python
def _derive_run_status(run: ScrapeRun) -> str:
    failed_sites = len(run.error_summary)
    total_sites = 4
    if failed_sites == total_sites:
        return "failed"
    if failed_sites > 0:
        return "partial"
    return "success"
```

注意：`error_summary` 仅在 `fetch_with_retry` 抛 `SiteFetchError` 时填充。项目级失败（normalize 异常、DB 写入失败）不进 `error_summary`，只反映在 `failed_count` 和 `scrape_item_logs`。

### 5.3 防并发

同一时刻只允许一个 `running` 状态的 run。触发端点检查 `ScrapeRun.status == "running"`，若存在则返回 409。

理由：抓取本身是 IO 密集（网络请求 + Playwright），并发跑两个会加倍被反爬风险，且 DB 写入串行更安全。

---

## 6. UI 集成

### 6.1 抓取按钮（ProjectList.vue）

项目列表页工具栏新增按钮：

```
[+ 新建项目] [↓ 抓取招标信息] [⚙ 列设置]    搜索框 [____________]
```

交互流程：
1. 点击按钮 → 弹确认对话框「将抓取 4 个站点今日新增的招标公告，预计 1-2 分钟，期间不要关闭页面」
2. 确认后 `POST /api/scrape/run`，按钮变 loading 状态
3. 每 2 秒轮询 `GET /api/scrape/status/{run_id}`
4. 进度展示：

```
正在抓取... ███████░░░ 3/4 站点
已入库: 8 | 重复跳过: 4 | 失败: 0 | 已用时 0:45
```

5. 完成时按钮恢复，进度条按状态变色：
   - `success` → 绿色
   - `partial` → 橙色（显示「N 个站点失败」）
   - `failed` → 红色
6. 提供链接「查看抓取记录」跳转历史页
7. localStorage 存 `lastRunId`，离开页面再回来时恢复轮询

### 6.2 抓取历史页（新建 `/scrape/history`）

侧边栏新增菜单「抓取记录」（所有登录用户可见，便于普通用户了解抓取来源）。

列表页字段：

| 开始时间 | 触发用户 | 总数 | 入库 | 跳过 | 失败 | 耗时 | 状态 | 操作 |
|---------|---------|-----|-----|-----|-----|-----|------|------|
| 2026-06-16 14:30 | admin | 16 | 8 | 4 | 0 | 1:23 | 成功 | 详情 |
| 2026-06-15 14:30 | 001 | 12 | 5 | 3 | 0 | 1:15 | 成功 | 详情 |
| 2026-06-14 14:30 | 001 | 0 | 0 | 0 | 12 | 0:30 | 失败 | 详情 |

详情页（点击「详情」展开或跳新路由）：
- 顶部展示 run 整体信息 + 每站点统计 + 失败原因
- 表格列出所有 `scrape_item_logs`：项目名、源链接（可点击新窗打开）、处理结果（created/skipped/failed）、跳过/失败原因

### 6.3 前端文件改动

| 文件 | 改动 |
|------|------|
| `frontend/src/api/scrape.js` | 新建：`triggerScrape` / `getScrapeStatus` / `getScrapeRuns` / `getScrapeRunDetail` |
| `frontend/src/views/project/ProjectList.vue` | 工具栏加抓取按钮 + 进度条 + 轮询逻辑（基于 `lastRunId` 恢复） |
| `frontend/src/views/scrape/ScrapeHistory.vue` | 新建：历史列表 + 详情展开 |
| `frontend/src/router/index.js` | 加 `/scrape/history` 路由 |
| `frontend/src/components/Layout.vue` | 侧边栏加「抓取记录」菜单项 |

### 6.4 权限

- **触发抓取按钮**：仅管理员可见（v-if="userStore.user.is_admin"）
- **查看抓取历史**：所有登录用户可见

---

## 7. 错误处理

### 7.1 错误分级

| 级别 | 场景 | 处理 | run 状态影响 |
|------|------|------|-------------|
| 站点级 | 某站点 3 次重试全失败 | 跳过该站点，记入 `error_summary`，其他站点继续 | `partial` |
| 站点全失败 | 4 站点全部失败 | 整体标记 `failed` | `failed` |
| 项目级 | 单条 normalize 失败 / 字段缺失 | 记 `scrape_item_logs` failed，继续下一条 | 不影响 |
| 入库失败 | DB 写入异常（约束冲突、字段类型错误） | 回滚当前项目事务，记 failed，继续下一条 | 不影响 |
| 进程崩溃 | worker OOM / 重启 | `on_startup` 清理孤儿 run | `failed` |

### 7.2 重试策略

`BaseScraper.fetch_with_retry`：
- 最多 3 次
- 指数退避：2s → 4s → 6s
- 超时统一 30 秒（requests / playwright 均设 `timeout=30`）
- 第 3 次失败抛 `SiteFetchError`

项目级失败**不重试**（数据问题重试也没用，直接跳过）。

### 7.3 Playwright 特殊处理

`jhzjcs.py` 是唯一用 Playwright 的站点，最容易出问题：

- **浏览器启动失败**：捕获 `playwright.async_api.Error`，标记站点失败
- **页面加载超时**：`page.goto(url, timeout=30000)`，超时截图存 `backend/data/scrape_screenshots/` 供排查（截图功能可选，先实现日志即可）
- **必须 headless 模式**：生产环境一定 `headless=True`，避免占用桌面
- **用系统 Chrome**：`channel="chrome"` 调系统已安装的 Chrome，避免下载 Chromium 200MB+
- **延迟导入**：`from playwright.sync_api import sync_playwright` 写在 `fetch()` 方法内

### 7.4 孤儿 run 清理

`main.py` `on_startup` 增加：

```python
def cleanup_orphan_runs(db: Session):
    """启动时清理上次未完成的抓取任务。"""
    orphans = db.query(ScrapeRun).filter(
        ScrapeRun.status == "running",
        ScrapeRun.finished_at.is_(None),
    ).all()
    for run in orphans:
        run.status = "failed"
        run.error_summary = {"system": "服务重启中断"}
        run.finished_at = datetime.now()
    if orphans:
        db.commit()
        logger.warning(f"清理了 {len(orphans)} 个孤儿 scrape run")
```

防止服务重启后 `scrape_runs` 表残留 `running` 状态的脏数据。

### 7.5 日志分层

| 层级 | 存储位置 | 用途 |
|------|---------|------|
| Run 级 | `scrape_runs` 表 | 每次抓取的统计 |
| 站点级 | `scrape_runs.error_summary` JSON | 每站点失败原因 |
| 项目级 | `scrape_item_logs` 表 | 每条公告处理结果 |
| 调试 | uvicorn 控制台 logging | 开发期排查 |

### 7.6 用户可见错误反馈

- **按钮触发的同步错误**（如未登录、已有 run 进行中）：`ElMessage.error`
- **轮询发现 run 失败**：进度条变红，展示「抓取失败：ccgp.gov.cn 连接超时；ggzy.zj.gov.cn WAF 拦截...」
- **部分成功**：进度条变橙，「3/4 站点成功，共入库 5 条，1 个站点失败，点击查看」

---

## 8. 文件清单

### 8.1 后端

| 文件 | 类型 | 说明 |
|------|------|------|
| `backend/app/scrapers/__init__.py` | 新建 | 包初始化 + `ScraperRegistry.all()` |
| `backend/app/scrapers/base.py` | 新建 | `BaseScraper` / `ScrapeItem` / `SiteFetchError` / `KEYWORDS` / `match_keywords` / `match_region_zhejiang` |
| `backend/app/scrapers/ccgp.py` | 新建 | 中国政府采购网（scrapling） |
| `backend/app/scrapers/ggzy.py` | 新建 | 浙江公共资源交易网（requests + WAF） |
| `backend/app/scrapers/jhzjcs.py` | 新建 | 金华中介超市（playwright，延迟导入） |
| `backend/app/scrapers/jhygcg.py` | 新建 | 金华阳光采购（requests） |
| `backend/app/services/scrape_runner.py` | 新建 | `run_scraper` / `_process_item` / `_find_duplicate` / `_log_item` / `_derive_run_status` |
| `backend/app/services/org_matcher.py` | 新建/重构 | 从 `api/documents.py` 提取 `_match_or_create_org` / `_match_or_create_platform` 共享 |
| `backend/app/api/scrape.py` | 新建 | 4 个 scrape API 端点 |
| `backend/app/models/scrape.py` | 新建 | `ScrapeRun` / `ScrapeItemLog` 模型 |
| `backend/app/models/project.py` | 修改 | 加 `external_no` / `source` / `source_url` 字段 |
| `backend/app/schemas/scrape.py` | 新建 | `ScrapeRunResponse` / `ScrapeItemLogResponse` |
| `backend/app/schemas/project.py` | 修改 | `ProjectResponse` 暴露新 3 字段 |
| `backend/app/main.py` | 修改 | 注册 scrape_router + on_startup 加 3 字段迁移 + 孤儿 run 清理 |
| `backend/requirements.txt` | 修改 | 加 `requests` / `scrapling`。`playwright` 标注为可选注释（延迟导入，未安装时仅 jhzjcs 站点失败，不影响后端启动） |

### 8.2 前端

| 文件 | 类型 | 说明 |
|------|------|------|
| `frontend/src/api/scrape.js` | 新建 | 4 个 API 调用 |
| `frontend/src/views/project/ProjectList.vue` | 修改 | 抓取按钮 + 进度条 + 轮询 |
| `frontend/src/views/scrape/ScrapeHistory.vue` | 新建 | 历史列表 + 详情 |
| `frontend/src/router/index.js` | 修改 | 加 `/scrape/history` 路由 |
| `frontend/src/components/Layout.vue` | 修改 | 侧边栏加菜单 |

### 8.3 文档

| 文件 | 类型 | 说明 |
|------|------|------|
| `CLAUDE.md` | 修改 | 新增 scrape 相关说明（scrapers 模块、scrape_runs / scrape_item_logs 表、4 个 API、去重策略、Playwright 延迟导入、孤儿清理等） |

---

## 9. 测试方案

本项目无自动化测试套件（CLAUDE.md 已记录 "No tests"），采用**手动端到端验证**。

### 9.1 阶段化验证

| 阶段 | 验证点 | 方法 |
|------|--------|------|
| 数据模型 | 3 新字段 + 2 新表自动创建 | 启动后端，看 `/docs` schema + 用 DB Browser 打开 `app.db` 确认表结构 |
| 单站点 scraper | 4 scraper 各自能 fetch 当天数据 + normalize 成 `ScrapeItem` | 写临时脚本 `backend/test_scraper.py`（不提交），分别调用每个 scraper 打印结果 |
| 去重逻辑 | `_find_duplicate` 在有/无 `external_no`、有/无重名时表现正确 | 临时脚本，预先插入几条测试项目再跑 scraper |
| 端到端 run | `POST /api/scrape/run` 返回 run_id，BackgroundTasks 完整跑通，数据库新增项目 | curl 或 Swagger 调用接口，轮询 status，查 DB |
| UI 按钮 | 按钮 → 进度 → 完成提示 | 浏览器手动 |
| 历史页 | 列表 + 详情正确展示 | 浏览器手动 |

### 9.2 上线前完整清单

```
□ 触发抓取，run 正常开始（返回 run_id）
□ 4 站点至少 3 个返回数据（部分失败可接受）
□ 入库项目能在项目列表看到
□ 项目详情中 source / source_url 字段正确显示
□ 已存在项目（手动造一条重复的）被抓取跳过，skipped_count 正确
□ 失败站点在 error_summary 有清晰说明
□ 抓取记录页能看到本次 run 的详情
□ 关闭浏览器后，后台 BackgroundTasks 仍跑完
□ 重启后端后，孤儿 run 被清理为 failed
□ 权限：普通用户（001/002/003）看不到抓取按钮，但能看到历史页
□ 同一天连续触发 2 次，第二次全部 skipped
```

### 9.3 风险点专项

| 风险 | 验证方法 |
|------|---------|
| Playwright 在 Windows Server 上无法启动 | 单独跑 `jhzjcs.py`，确认 Chrome 能被调起 |
| GGZY WAF 高频拦截 | 连续触发 3 次抓取，观察被封概率；如高发，考虑加 UA 轮换 |
| 抓取期间 DB 锁 | 抓取过程中同时操作前端（新建/修改项目），确认无 `database is locked` |
| 大数据量超时 | 周一补周末数据，确认 2 分钟内能跑完 |
| 重复抓取 | 同一天连续触发 2 次，确认第二次全部 skipped |

---

## 10. 实施顺序

writing-plans 技能将细化为可执行步骤。大致顺序：

1. **数据模型层**：models/scrape.py + project.py 加字段 + main.py 迁移 + 孤儿清理
2. **scraper 模块**：base.py → ccgp/ggzy/jhygcg → jhzjcs（playwright 最后，最易失败）
3. **服务层**：org_matcher.py 提取 + scrape_runner.py
4. **API 层**：api/scrape.py + 注册路由
5. **前端 API**：api/scrape.js
6. **前端 UI**：ProjectList 按钮 + 进度 → ScrapeHistory 页 → 路由 + 菜单
7. **联调测试**：按第 9 章清单逐项验证
8. **CLAUDE.md 更新**：新增 scrape 相关说明
9. **git 提交**：feat（代码）+ docs（文档）

---

## 11. 后续可能的扩展（YAGNI — 本期不做）

列出供未来参考，**不在本期实施**：

- 定时任务（APScheduler 每日定时抓取）
- 邮件/钉钉/企微推送新抓取到的项目
- 模糊匹配去重（如启用需引入相似度算法 + 阈值配置）
- 反爬升级（UA 轮换、IP 代理池、验证码识别）
- 多日补抓（支持传 `days_back` 参数抓取历史日期）
- 抓取结果导出（Excel / CSV）
