# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 语言规则

所有输出使用中文，除了代码、文件路径和技术术语（如变量名、API 路径、框架名称等）以外。

## Project Overview

招标信息收集和投标信息管理系统 — internal tool for a small team (<5 people) to manage the full bidding lifecycle. All data is stored in a single `project_infos` table with ~50 columns divided into 4 logical sections. Each stage transition is driven by flow buttons that update the project status.

## Development Commands

### Backend (FastAPI)
```bash
cd backend
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple   # install deps (Chinese mirror recommended)
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload           # dev server
```
Swagger docs available at http://localhost:8000/docs after startup.

### Frontend (Vue 3)
```bash
cd frontend
npm install
npm run dev    # dev server, proxies /api to backend:8000 via vite.config.js, listens on 0.0.0.0 (LAN accessible)
```

### Debug Chrome (政采云 CDP)
Double-click `start-debug-chrome.bat` in project root. Kills all chrome.exe, starts a debug Chrome with `--remote-debugging-port=9222 --user-data-dir=C:/chrome-debug`, auto-opens `https://b.zhengcaiyun.cn/luban/search?k=&type=1`. Required before triggering scrape (zcy scraper connects via CDP). **.bat 必须用 CRLF 换行**（LF-only 会让 cmd.exe 静默退出、窗口都起不来）。

### Database
SQLite file at `backend/data/app.db`. Auto-created on first startup. To reset: delete the file and restart the server. Default admin user `admin / admin123` and default organization "浙江意诚检测有限公司" (ID=1, org_type=ours) are created on first startup.

## Architecture

### Backend Structure (`backend/app/`)
- **`core/`** — config (pydantic-settings from `.env`), database (SQLAlchemy engine/session/Base), security (JWT via python-jose, bcrypt via passlib)
- **`models/project.py`** — Single SQLAlchemy 2.0 model with all enums and ~50 columns. All bidding lifecycle data in one table.
- **`models/organization.py`** — Organization model with `OrgType` enum (`ours`/`external`). Our company "浙江意诚检测有限公司" is marked as `ours`.
- **`schemas/project.py`** — Pydantic v2 models: `ProjectCreate`, `ProjectUpdate`, `ProjectResponse`. `model_config = {"from_attributes": True}` for ORM mode.
- **`api/projects.py`** — Single FastAPI router for all CRUD + flow operations. Price calculation helpers (`_control_type_str`, `_format_price`, `_calc_winning_amount`, etc.) live here. Shortlisting bid (入围标) skips auto-calculation of winning_price/winning_amount.
- **`api/stats.py`** — Statistics endpoints, queries single `project_infos` table directly.
- **`api/documents.py`** — Document parsing endpoints. `POST /api/documents/parse` accepts `parse_type` query (`bidding` for tender announcements, `result` for winning announcements), uploads file to Qwen-Long via DashScope, returns form fields. Also exposes `GET/DELETE /api/documents/{id}/files` (bid_documents) and `GET/DELETE /api/documents/{id}/result-files` (result_documents). Helper functions: `_save_upload`, `_match_or_create_org`, `_match_or_create_platform`, `_build_bidding_response`, `_build_result_response`.
- **`api/scrape.py`** — Auto-scrape endpoints. `POST /api/scrape/run` triggers a scrape run (admin / bid_specialist, returns `{run_id}` immediately, runs `run_scraper` via BackgroundTasks). `GET /api/scrape/status/{run_id}` for polling. `GET /api/scrape/runs` lists history. `GET /api/scrape/runs/{run_id}` returns detail with item_logs. `require_can_scrape` dependency checks `role in ("admin", "bid_specialist")`. Prevents concurrent runs (409 if another run is `running`).
- **`services/document_parser.py`** — Qwen-Long integration via OpenAI-compatible DashScope client. `QwenLongParser.upload_file()` → `parse(file_id, parse_type, control_price_type)` → `_normalize(raw, parse_type)` dispatches to `_normalize_bidding` or `_normalize_result`. `FIELD_ALIASES` / `RESULT_CANDIDATE_ALIASES` / `RESULT_TOP_ALIASES` map Chinese LLM keys to English. `_build_result_prompt()` injects price unit hint based on project's `control_price_type`.
- **`services/scrape_runner.py`** — Main scrape orchestration. 三阶段流水线：Phase 1 `_classify_one` (normalize + `classify_by_keyword` 关键词分类) → Phase 2 `_process_grey_batch` (grey 批量并发调 LLM `services/classifier.py`) → Phase 3 `_create_one` (去重 + 入库). `SKIP_CLASSIFY_SCRAPERS = {"jhzjcs"}` 跳过分类直接入库。`_find_duplicate` checks `external_no` first, then `project_name`. `_process_item` creates ProjectInfo with `status=following`. `_record_failure` / `_log_item` write to `scrape_item_logs`. Counter invariant: `total_count = created_count + skipped_count + failed_count`.
- **`services/classifier.py`** — Qwen LLM 项目分类器（单例），grey case 调 LLM 判断是否属于工程检测类业务。复用 DashScope OpenAI 兼容客户端。模型 `qwen-plus`，`response_format=json_object`，内存缓存按 `external_no`。
- **`services/org_matcher.py`** — Shared `match_or_create_org` / `match_or_create_platform` helpers, reused by both `documents.py` and `scrape_runner.py`.
- **`scrapers/`** — Bid announcement scrapers. `base.py` defines `BaseScraper` (abstract `fetch`/`normalize`, `fetch_with_retry` with 3 retries + exponential backoff), `ScrapeItem` dataclass, `SiteFetchError`, `CORE_SERVICE_KEYWORDS`/`ENGINEERING_DOMAIN_KEYWORDS`/`BLACKLIST_KEYWORDS`, `classify_by_keyword()`, `ZHEJIANG_CITIES`, `extract_region_from_text()`, `RESULT_KEYWORDS`, `is_result_announcement()`, `parse_date_safe()`. `__init__.py:ScraperRegistry` lazily imports and instantiates all scrapers via `importlib.import_module` (fault-tolerant — a broken scraper doesn't crash the run). Site modules: `ccgp.py` (scrapling/curl_cffi), `ggzy.py` (requests + WAF), `jhygcg.py` (requests), `jhzjcs.py` (requests POST JSON API, direct `getComparePublicList` call), `jhggzy.py` (requests GET AJAX API, 11 县区 × 3 公告类型 = 33 数据源), `zcy.py` (CDP-driven Chrome fetch — 唯一需要外部调试 Chrome).
- **`main.py`** — App factory: CORS middleware, startup event (auto-creates tables + default admin + default organization with org_type=ours + auto-migration), route registration. Also registers `documents_router` and auto-migrates `result_documents` JSON column. Also registers `scrape_router`, imports `scrape` model, auto-migrates `external_no`/`source`/`source_url` columns, and cleans up orphan scrape runs (status=running + finished_at=NULL) on startup.

### Frontend Structure (`frontend/src/`)
- **`api/project.js`** — Single Axios-based API module for all project operations (CRUD + flow). Includes `parseBidDocument` / `parseResultDocument` (multipart upload with `parse_type` query param, 200s timeout), `getBidDocuments` / `getResultDocuments`, `deleteBidDocument` / `deleteResultDocument`.
- **`api/scrape.js`** — Scrape API: `triggerScrape` / `getScrapeStatus` / `getScrapeRuns` / `getScrapeRunDetail`.
- **`components/`** — Shared components: `Layout.vue` (sidebar + header shell), `OrgSelector` (remote search + inline create, `excludeOurs` prop filters out our company), `PlatformSelector`/`ManagerSelector` (remote search + inline create), `RegionCascader` (省市区 picker).
- **`views/project/`** — Two pages: `ProjectList.vue` (list with collapsible advanced search panel, custom column selector per-status config, quick status filter buttons, and a "抓取招标信息" button visible to admins that triggers scrape + polls progress) and `ProjectDetail.vue` (single page with 4 card sections in 2x2 grid layout).
- **`views/scrape/ScrapeHistory.vue`** — Scrape run history list + detail drawer (all users can view).
- **`stores/user.js`** — Pinia store for auth state (token + user in localStorage).
- **`router/index.js`** — Vue Router with auth guard, lazy-loaded routes.

### Data Model (Single Table)

`project_infos` table with 4 logical sections:

| Section | Columns cover | Visible when |
|---------|--------------|-------------|
| 项目基本信息 | bidding_type, project_name, bidding_unit_id, region, manager_ids, status, parent_project_id (入围分项关联父入围标), external_no (外部公告编号，用于抓取去重), source (来源站点标识：ccgp/ggzy/jhygcg/jhzjcs/manual), source_url (原始公告链接), etc. | Always |
| 招标信息 | agency_id, publish_platform_id, tags, deadlines, budget_amount, control_price_type/upper/lower, is_prequalification (是否入围标), is_multi_lot (是否多标段), bid_documents (招标文件元信息 JSON), is_registered (虚拟字段，从 status 推导), etc. | status >= 已发公告 |
| 投标信息 | partner_ids, bid_method, is_consortium_lead, deposit fields, our_price, etc. | status >= 准备投标 |
| 投标结果 | competitors (含 org_ids/price/score/is_winning), scoring_details, is_won + is_bid_failed (三态：已中标/未中标/流标), winning_org_ids (自动推导), winning_price/amount, result_deposit_status, result_documents (中标公告文件元信息 JSON), contract fields, etc. | status >= 已投标 |

**Scrape tables**: `scrape_runs` (run-level: started_at, finished_at, triggered_by, status=running/success/partial/failed, total/created/skipped/failed counts, sites_summary JSON, error_summary JSON) and `scrape_item_logs` (per-item: source, external_no, project_name, source_url, result=created/skipped/failed, project_id, skip_reason, error_message). Both auto-created on startup via `Base.metadata.create_all`.

**Field naming for merged columns:**
- BiddingInfo.notes → `bidding_notes`
- BidInfo.notes → `bid_notes`
- BidResult.notes → `result_notes`
- BidResult.deposit_status → `result_deposit_status`

**All enums** (BiddingType, ProjectStatus, BudgetType, BidMethod, BidStatus, DepositStatus, ContractStatus, ResultDepositStatus) are defined in `models/project.py`.

### Core Business Flow (ProjectStatus enum)
```
跟进中 →(publish)→ 已发公告 →(fill deadline)→ 未报名 →(check is_registered)→ 已报名 →(prepare)→ 准备投标 →(submit)→ 已投标 →(is_won/is_bid_failed)→ 已中标/未中标/已流标
  └→(abandon)→ 已放弃 (any stage)
```
多标段父项目不参与上述流程，其状态由子标段自动推导（截止到已投标）。
Flow endpoints only change the status field — no new records are created:
- `POST /api/projects/{id}/publish` — 跟进中 → 已发公告
- `PUT /api/projects/{id}` with `registration_deadline`/`is_registered` — 已发公告 ↔ 未报名 ↔ 已报名 (auto-derive: no deadline=已发公告, deadline+unchecked=未报名, deadline+checked=已报名)
- `POST /api/projects/{id}/prepare` — 已发公告/未报名/已报名 → 准备投标
- `POST /api/projects/{id}/submit` — 准备投标 → 已投标 (+ sets `result_deposit_status=未收回` when `has_deposit=true` and `deposit_status=已缴纳`)
- `POST /api/projects/{id}/abandon` — any → 已放弃 (with reason)
- `PUT /api/projects/{id}` with `is_won`/`is_bid_failed` — 已投标/已中标/已中标/已流标 → 已中标/未中标/已流标 (auto-derives winning_org_ids/winning_price/winning_amount from competitors' is_winning flag, except for 入围标 which uses manual input)

### API Response Conventions
- List endpoints return `{"items": [...], "total": N, "page": P, "page_size": S}`
- Flow endpoints return `{"message": "..."}`
- All endpoints use `model_dump(exclude_unset=True)` for partial updates
- `enrich_project()` populates all related names and computed display fields

### Advanced Search (`GET /api/projects`)
`list_projects` endpoint supports 26 query parameters for filtering:
- **Basic**: `keyword` (project name, with `keyword_match`="fuzzy"/"exact"), `status`, `bidding_type`
- **Organization**: `bidding_unit_id`, `agency_id`, `publish_platform_id`, `manager_id` (JSON array via `json_each`), `partner_id` (JSON array via `json_each`)
- **Specialist (我的项目)**: `bid_specialist_id` (filter by 投标专员), `include_unassigned_specialist` (OR 未指派), `exclude_abandoned` (排除已放弃)
- **Enum/Bool**: `bid_method`, `is_prequalification`, `is_multi_lot`, `is_won`
- **Date range**: `created_after`/`created_before`, `bid_deadline_after`/`bid_deadline_before`
- **Amount range**: `budget_min`/`budget_max`, `winning_amount_min`/`winning_amount_max`
- **Pagination**: `page`, `page_size`
- Frontend `ProjectList.vue` uses a `watch` on advanced filter values (not `@change` events) to auto-trigger `loadData()`. `_initialized` flag prevents double-load during state restoration. Filter state persisted in localStorage.

### Frontend-Backend Data Mapping
- Frontend sends region as `JSON.stringify(["浙江省","杭州市","西湖区"])`, stored in `String(100)` column
- JSON fields (`manager_ids`, `partner_ids`, `tags`, `competitors`, `scoring_details`, `winning_org_ids`, `bid_documents`, `result_documents`) are stored as serialized JSON strings; frontend must `JSON.parse()` on read and send arrays on write. `competitors` stores `{org_ids: [int], price, score, is_shortlisted, is_winning}` per entry (old format `{org_id, ...}` auto-converted on load). `winning_org_ids` is auto-derived from competitors where `is_winning=true`. `bid_documents` / `result_documents` store file metadata arrays `[{filename, stored_path, size, uploaded_at}]`.
- Frontend `collectSaveData()` only includes form fields from currently visible card sections to avoid sending irrelevant data (e.g., not sending `is_won` when result card isn't visible)
- **Competitors backward compat**: Old format `{org_id: 1, ...}` is auto-converted to `{org_ids: [1], ...}` in both `enrich_project()` (backend) and `loadProject()` (frontend). `is_winning` defaults to `false` for old data.

### Key Technical Notes
- **bcrypt**: Must pin `bcrypt==4.1.3`. Version 5.x is incompatible with `passlib 1.7.4` (causes `__about__` AttributeError and wrap bug ValueError).
- **JWT subject**: `sub` claim must be a string (`str(user.id)`), not an integer — `python-jose` validates this strictly.
- **JSON fields**: `manager_ids`, `partner_ids`, `tags`, `competitors`, `scoring_details`, `bid_documents`, `result_documents`, `bid_files`, `winning_org_ids` are stored as JSON columns using SQLAlchemy `JSON` type.
- **Price calculation**: `_control_type_str()` handles Python 3.13 enum str() issue (returns enum member like `BudgetType.discount_rate` instead of value). Always use this helper instead of raw comparison.
- **Winning amount formula**: 折扣率: `our_price / upper * budget`. 下浮率: `(1 - our_price/100) / (1 - upper/100) * budget`. 金额: `our_price` directly.
- **Status guard**: Backend allows bid result status change from submitted/won/lost/failed_bid states (not just submitted), so users can correct their bid result at any time.
- **Bid result tri-state**: `is_won` (bool, NOT NULL default=false) + `is_bid_failed` (bool, default=false) form three states: 已中标 (is_won=true), 未中标 (is_won=false, is_bid_failed=false), 流标 (is_bid_failed=true). 流标 disables all winning checkboxes. Frontend `bidResultType` computed maps these to radio group.
- **Registration virtual field**: `is_registered` is NOT stored in DB. Derived from `status == 已报名` in `enrich_project()`. Frontend treats status >= 准备投标 with deadline as registered (so checkbox stays checked after advancing). `ProjectUpdate.is_registered` is skipped in `setattr` loop.
- **入围标 (shortlisting)**: When `is_prequalification=true`, competitors have a "中标" checkbox that allows multi-select. When `is_prequalification=false`, the checkbox enforces single-select (radio behavior). `winning_org_ids` is auto-derived from checked competitors' `org_ids`. In won state for 入围标, winning_price/winning_amount use manual input (not auto-calculated).
- **联合体 (consortium)**: When `bid_method="联合体"`, `is_consortium_lead` field (default true) controls whether our company is the lead. Partner orgs + our company are auto-grouped as one competitor entry with `org_ids: [ourOrgId, ...partnerIds]`. Contract info only shows when `is_consortium_lead=true` AND `is_won=true`. Switching bid_method away from 联合体 auto-clears partner_ids and updates competitor entries. Partner OrgSelector excludes orgs already used in competitors (互斥).
- **配合/陪标 (cooperate/companion)**: Partner orgs can coexist with competitor orgs (no exclusion). Partner OrgSelector shows without cross-field filtering.
- **独立 (independent)**: Partner OrgSelector is hidden entirely. Only our company appears in competitors.
- **OrgType filter**: Organizations have `org_type` field (ours/external). `OrgSelector` has `excludeOurs` prop to filter out our company, and `excludeIds` prop to exclude specific IDs (used for dedup across competitor entries). `filteredOptions` always includes currently selected values even if in excludeIds, so el-select can display names instead of raw IDs.
- **Multi winning orgs**: `winning_org_ids` (JSON array) is auto-derived from competitors' `is_winning` checkboxes — no manual input needed. `winning_org_id` (single Integer) kept for backward compat.
- **Bid deposit two-state model**: `DepositStatus` enum (`无`/`未缴纳`/`已缴纳`) for bid info section's `deposit_status` field. `ResultDepositStatus` enum (`未收回`/`已收回`) for result section's `result_deposit_status` field. Submit endpoint sets `result_deposit_status=未收回` only when `deposit_status=已缴纳`. Result section's deposit UI only shows when `deposit_status=已缴纳`. `enrich_project()` computes `deposit_status_display` field: shows 缴纳状态 before 已投标, shows 收回状态 from 已投标 onward.
- **OrgMap loading**: `loadOrgNames()` uses `page_size=100` (backend max). Previously used 500 which caused 422 error and empty orgMap, breaking all org-dependent features.
- **入围分项 (shortlisting sub-item)**: `BiddingType.prequalification` bidding type. Links to a parent 入围标 project via `parent_project_id` (self-referential FK). Only shows parent selector when `bidding_type="入围分项"`. Parent selector filters projects by `is_prequalification=true` AND `status=已中标`. Competitors are initially copied from parent (via `POST /api/projects/{id}/sync-competitors`), then maintained independently. "从父项目同步参标单位" button allows manual re-sync. When bidding_type is 入围分项, the "是否入围标" switch is hidden to prevent logic conflicts.
- **多标段 (multi-lot)**: `is_multi_lot` boolean field (default=false) marks a project as a multi-lot parent container. Parent project does NOT participate in bidding — it only serves as a container/summary. Child lots are full independent projects with `parent_project_id` pointing to the parent. Key differences from 入围分项: (1) Parent's status is auto-derived from the furthest child lot status (up to 已投标; won/lost/failed_bid don't sync upward). If all children are abandoned, parent becomes 已放弃. (2) Child lots pre-fill parent's project name on creation, all other fields are independent. (3) Multi-lot parents block all flow operations (publish/prepare/submit/abandon). (4) Child lot status changes trigger `recalc_multi_lot_parent_status()` via all flow endpoints and update. (5) Deleting a multi-lot parent cascades to delete all child lots. (6) `is_multi_lot` and `is_prequalification` are mutually exclusive. (7) `GET /api/projects/{id}/lots` endpoint returns child lots for a multi-lot parent. (8) `is_multi_lot` switch appears in project basic info card during creation and while status is 跟进中. (9) ProjectList has expandable rows showing child lots; ProjectDetail uses tab-based navigation for multi-lot parents (summary tab + per-lot tabs + add lot dialog). (10) Stats/Dashboard exclude multi-lot parent projects (`is_multi_lot == False` filter). (11) Frontend uses `currentProjectId` computed property to resolve the actual project ID for save/flow operations — in a lot tab it returns the lot ID, otherwise the route ID. This prevents child lot data from being written to the parent project.
- **Region data**: `frontend/src/utils/region-data.js` contains province/city/county cascader data. Currently only 浙江省 has complete county-level coverage; other provinces have partial data (major cities/districts only). Expand as needed.
- **Selector preload**: `PlatformSelector` and `OrgSelector`/`ManagerSelector` all use `preloadOptions()` with `loaded` flag on mount + `watch(modelValue)` for lazy load. This ensures el-select always has options for displaying names (not raw IDs) after save/reload.
- **loadProject watcher guard**: `_updatingFromWinning` flag wraps `resultForm` assignment in `loadProject()` to prevent `is_won` watcher from interfering during data loading. Without this, the watcher could reset competitors' `is_winning` flags before `ensureOurCompanyInCompetitors()` runs.
- **Column config persistence**: `ProjectList.vue` uses `watch(selectedColumnKeys)` (not `@change`) to save column config to localStorage. Each status tab has its own storage key (`project_list_columns_${uid}_${status|'all'}`)。**关键**：`loadColumnConfig(status)` / `saveColumnConfig(status, keys)` 必须接收显式 status 参数，**不能在 setup 早期隐式读取 `activeStatus.value`** —— `activeStatus` 在 `selectedColumnKeys` 之后才声明，setup 阶段访问会触发 TDZ ReferenceError，被 try/catch 吞掉后静默返回默认列。`selectedColumnKeys = ref(loadColumnConfig(''))` 用空字符串初始化（即「全部」状态）。`setStatus` 切换状态时显式传新 status 重新加载列配置。
- **List state preservation**: `ProjectList.vue` 通过 `sessionStorage['projectListPage']`（JSON: `{page, activeStatus, keyword, bidding_type, myProjects}`）保存列表状态。`goToDetail(id)` 调用 `saveListState()` 后再 `router.push`。`onMounted` 用 `consumeListState()` 读取并清除，恢复所有字段后调 `loadColumnConfig(activeStatus.value)` 重载列配置。`Layout.vue` 侧边栏点击 `/projects` 时 `sessionStorage.removeItem('projectListPage')` — 即「侧边栏点击 = 回到全部第 1 页，浏览器后退 = 保留状态」。`_initialized` 标志位配合 `nextTick` 防止高级筛选恢复期间 watch 异步重置页码。
- **List UI 细节**: 单页 15 条（适配 1920×1080 无需滚动）。状态按钮含独立的「已放弃」（info 色）。「全部」模式下 `exclude_abandoned=true` 自动屏蔽已放弃项目（要看放弃项目单独点按钮）。
- **Bid result auto-trigger rules**: 未中标 cannot be manually selected via radio button (`handleBidResultChange('lost')` is a no-op). It is only auto-triggered when a non-our competitor has `is_winning` checked (via `handleWinningChange`). Conversely, when ALL `is_winning` checkboxes are unchecked, `handleWinningChange` sets `is_won=false`, and on save the backend reverts status to 已投标 regardless of previous state (已中标/未中标/已投标). Frontend `collectSaveData()` always sends `is_won`/`is_bid_failed` when result card is visible — backend handles all derivation logic.
- **Document parsing (招标公告)**: `POST /api/documents/parse?parse_type=bidding&project_id=N` uploads file → Qwen-Long extracts fields → auto-creates bidding_unit/agency/platform orgs via `_match_or_create_org` (with `org_type=external`) → returns form fields for frontend to apply. File metadata appended to `bid_documents` on save. System prompt in `document_parser.py:SYSTEM_PROMPT` asks LLM to extract bidding fields; `FIELD_ALIASES` maps Chinese keys to English.
- **Document parsing (中标公告)**: Same endpoint with `parse_type=result`. `_build_result_prompt(control_price_type)` injects price unit hint (金额=元 / 折扣率=百分比 / 下浮率=下浮百分比). Response `fields.competitors[]` contains `{org_ids, org_names, price, score, rank, is_winning}` per candidate; `_match_or_create_org` runs per org name (consortium names split by 、，;／). Response auto-derives `is_won` by checking if any winning candidate includes our company (`org_type=ours`). File metadata appended to `result_documents` on save. Frontend `applyResultFields` replaces competitors entirely but preserves our-company entry if not present in parse result.
- **Parser normalize**: `_normalize(raw, parse_type)` dispatches to `_normalize_bidding` (flat field aliases) or `_normalize_result` (nested candidates array with `RESULT_CANDIDATE_ALIASES` + `RESULT_TOP_ALIASES`). Result mode splits consortium unit names like "A公司、B公司" → `["A公司","B公司"]` via regex `[,，;；/、]`.
- **下浮率 swap**: In `_build_bidding_response`, when `control_price_type=下浮率` and `upper > lower`, the two values are swapped (semantic: 上限=最小降价幅度=较小值, 下限=最大降价幅度=较大值).
- **入围标 LLM detection**: `SYSTEM_PROMPT` field `是否资格预审` doubles as `是否入围标`. Trigger keywords include 入围 / 入围标 / 短名单 / 资格预审 / 合格供应商库 / 框架协议 / 入围候选人. `FIELD_ALIASES` maps both Chinese keys to `is_prequalification`.
- **Bid specialist auto-assign**: `ProjectDetail.vue:ensureSpecialistBeforeSave()` runs on every save path (including child lot saves via `saveCurrentLot`). Logic: (1) if `bid_specialist_id` empty → silently set to current user; (2) if already = current user → no-op; (3) if = another user → ElMessageBox confirm "是否将投标专员由 X 更换为 Y？" with cancel = keep original specialist. Triggered on save (not on bidding-card-shown watch), so specialist is written even when project is still 跟进中 and bidding card hidden. Users loaded from `/api/users` lookup for display name resolution.
- **UserRole**: `admin` / `bid_specialist` (投标专员，可触发抓取) / `user`. Startup migration auto-upgrades 3 hardcoded names (倪敏/刘阳莉/施艳荷) to `bid_specialist` (idempotent).
- **Abandon flow**: 放弃 dialog uses radio options for `abandon_reason` (资质不符 / 价格太低) + free-text `abandon_notes`. `abandon_notes` is a new column (auto-migrated on startup). Startup migration also converts old free-text `abandon_reason` → moves to `abandon_notes` and sets `abandon_reason="资质不符"` (idempotent). Abandoned card in ProjectDetail shows both fields.
- **我的项目 filter**: `ProjectList.vue` shows "我的项目" button for `bid_specialist` role only. Toggles `myProjects` ref → calls `/api/projects` with `bid_specialist_id=<self> + include_unassigned_specialist=true + exclude_abandoned=true`. So "我的项目" = 当前专员 + 未指派 - 已放弃.
- **Post-parse orgMap refresh**: `handleFileChange` / `handleResultFileChange` call `await loadOrgNames()` after `applyParsedFields` / `applyResultFields`. Required because `_match_or_create_org` creates new orgs during parse; without refresh, `getOrgName(oid)` returns '未知单位' for newly created orgs not yet in `orgMap`.
- **Auto-scrape**: `POST /api/scrape/run` (admin / bid_specialist) triggers `run_scraper(run_id, user_id)` via FastAPI BackgroundTasks. Iterates all registered scrapers (ccgp/ggzy/jhygcg/jhzjcs/jhggzy/zcy) via `ScraperRegistry.all()` (lazy-loaded, fault-tolerant). Prevents concurrent runs (409). Orphan runs cleaned on startup.
- **Scraper architecture**: `scrapers/base.py:BaseScraper` (abstract `fetch`/`normalize`, `fetch_with_retry` with 3 retries + exponential backoff, error message includes exception type). `ScraperRegistry` uses `importlib.import_module` with try/except per scraper. Six site modules: `ccgp.py` (scrapling + curl_cffi browser fingerprint), `ggzy.py` (requests + WAF bypass via session cookie warmup), `jhygcg.py` (requests POST JSON API), `jhzjcs.py` (requests POST JSON API, direct `getComparePublicList` call), `jhggzy.py` (requests GET AJAX API, 33 数据源), `zcy.py` (**CDP 驱动 Chrome fetch**，唯一需要外部调试 Chrome 进程的 scraper).
- **Result announcement filter**: `scrapers/base.py:RESULT_KEYWORDS` + `is_result_announcement()` excludes 中标/成交/开标/结果/废标/流标/终止/合同 公告/公示/记录. All six scrapers call this in `normalize()` to keep only 招标公告.
- **Keyword + LLM hybrid filter (三段式)**: `scrapers/base.py` 三层关键词 + Qwen LLM 灰度精筛，目标把误抓率从 ~50% 降到 <10%。公司业务范围：**土木工程实体/设施的检测、监测、勘察、测绘、鉴定服务**（不是做工程，是给工程做检测服务）。
  - **三态分类 `classify_by_keyword(text) → "white" | "grey" | "reject"`**：
    - `CORE_SERVICE_KEYWORDS` = [检测/监测/勘察/测绘/鉴定/试验/检验/评估/定检/年检/观测] — **必须命中至少一个**，否则直接 reject（防止纯施工/采购项目混入）
    - `ENGINEERING_DOMAIN_KEYWORDS` = [工程/建筑/桥梁/隧道/道路/市政/水利/交通/桩基/基坑/防雷/消防/智能化/节能/室内环境/沉降/抗震/可靠性/地形/竣工/...] — 工程领域信号词
    - `BLACKLIST_KEYWORDS` = [医学/医疗/药品/食品/农产品/商品/货物/电梯/车辆/保洁/保安/物业/服装/软件采购/...] — 强排除
    - 逻辑：`has_core=false → reject`；`has_core + has_black → grey`（让 LLM 裁决）；`has_core + has_eng + !has_black → white`；`has_core + !has_eng → grey`
  - **`scrape_runner.py` 三阶段流水线**（站点级）：
    - Phase 1 `_classify_one`：normalize → `is_result_announcement` 过滤 → `classify_by_keyword` 分类 → white/grey 收集、reject 直接 skip
    - Phase 2 `_process_grey_batch`：`ThreadPoolExecutor(max_workers=LLM_CONCURRENCY=10)` 批量并发调 LLM。`ENABLE_LLM_FILTER=false` 时 grey 全部 reject；LLM 单条异常 → fallback 为 white（宁多抓不漏抓）
    - Phase 3 `_create_one`：去重 + 入库（原 `_process_item` 逻辑）
  - **`SKIP_CLASSIFY_SCRAPERS = {"jhzjcs"}`**：金华中介超市整分类抓，**完全跳过关键词+LLM 分类**（它的 normalize 输出直接进 Phase 3 入库）
  - **`services/classifier.py:ProjectClassifier`**：复用 `document_parser.py` 的 DashScope OpenAI 兼容客户端，单例。`classify(title, context, external_no) → ("white"|"reject", reason)`。内存缓存按 `external_no`（同 run 内避免重复调）。模型 `QWEN_CLASSIFIER_MODEL=qwen-plus`（纯文本分类，比 turbo 推理更准）。`response_format={"type": "json_object"}` 强制 JSON，`temperature=0.1`。SYSTEM_PROMPT 用「关键判别问句」核心：*这个项目最终交付的是不是一份【检测/监测/勘察/测绘/鉴定报告或服务】*？并枚举 5 类 false 场景（设备/耗材采购、工业设备检验、医学司法食品、建设设计、非检测运维）。
  - **5 个 scraper normalize 改造**：ccgp/ggzy/jhygcg/jhggzy/zcy 全部移除 `match_keywords(title)` 硬过滤，关键词逻辑完全上移到 runner 统一做。jhzjcs 不动（本就无关键词筛选）。
  - **skip_reason 字段记录**：拒绝原因写入 `scrape_item_logs.skip_reason` —— "关键词拒绝（黑名单/不命中业务词）" / "LLM 拒绝: [类别] 原因" / "灰度拒绝（LLM 筛选已关闭）"，无需建新表。
- **Region extraction (县市级)**: `scrapers/base.py:ZHEJIANG_CITIES` 维护浙江 11 地市 → 区县映射，`extract_region_from_text(text) → JSON string | None`。返回 `["浙江省","金华市","义乌市"]` 格式，匹配不到返回 None（地区字段留空）。5 个非 jhzjcs scraper 在 normalize 里从 title 或 site-specific 区字段抽取，写入 ProjectInfo.region。jhzjcs/jhygcg/jhggzy fallback 到 `["浙江省","金华市"]`（站点本身在金华）。`match_region_zhejiang()` 已废弃不再使用（旧版只到省级）。
- **Site-specific fetch details**:
  - **ggzy**: `CATEGORIES` 配置 4 交易领域 × 各领域实际类型体系 = 共 9 个数据源（**领域间类型代码体系不同，不能套同一组**）：工程建设 3 类（`002001001` 招标公告 / `002001002` 资格预审公告 / `002001011` 招标文件公示）、政府采购 4 类（`002002001` 采购公告 / `002002005` 竞争性磋商 / `002002006` 竞争性谈判 / `002002008` 询价）、国企采购 1 类（`002011001` 交易公告 — 该领域侧栏仅「交易公告/交易结果」2 类）、小额工程 1 类（`002012001` 交易公告 — 同上）。`infoc=33` 前缀匹配浙江全省（非 330）。**不传服务端 `titlenew` 关键词**（站点分词会漏抓），改为按当天日期 `time` 字段 + `rn=100` 翻页（最多 10 页兜底）1 次拿全部，本地 `normalize` 用 `is_result_announcement` 过滤（关键词分类已上移到 runner）。去重 by `rec.id`（比 url 稳定）。source_url 拼接 `https://ggzy.zj.gov.cn` + 相对路径。
  - **jhygcg**: Searches with `classID=21` (采购公告) but API mixes in classId=22 (成交候选人) and 24 (采购结果) — `normalize()` filters `classId != "21"` out. source_url uses `/detail?bulletinId={articleId}` (no `/home/` prefix).
  - **jhzjcs**: Direct API call to `getComparePublicList` with `selectedOptionId=6bbd9b33-ad3b-4c7a-a689-4365326f2626` (工程检验检测 category). `pageSize=200` to fetch all projects in one request. **No keyword/name filter** — all projects under this category are kept. source_url uses `comparison_public.html?id={guid}`.
  - **ccgp**: Uses scrapling with curl_cffi impersonation to bypass anti-bot. Zone `330` for 浙江.
  - **jhggzy**: 金华市公共资源交易网 `ggzyjy.jinhua.gov.cn`（HTTP only，HTTPS 返回 410）。覆盖 11 县区分站（市本级/婺城/金东/兰溪/义乌/东阳/永康/浦江/武义/磐安/开发区）× 3 公告类型（预公告/招标公告/采购公告）= 33 个数据源，配置表硬编码在 `SOURCES`。API: `GET /api-gateway/jpaas-publish-server/front/page/build/unit` + `webId=3818` + `tplSetId=LpcyxkYSwRoJNKPT7EX2v` + `tagId=概览信息列表` + `paramJson={pageNo,pageSize}`，返回 `data.html` 为 HTML 片段。**pageId 处理**：顶级栏目（预公告/采购公告）URL `/col/col<colId>/index.html` 的 pageId 直接 = colId；子路径栏目（招标公告）URL `/col/col<parent>/<sub>/index.html` 的 pageId 是 jcms 生成的哈希，需先 fetch 静态页从 `queryData` 属性（注意大写 D）解析，缓存到实例。**HTML 解析**：标题优先用 `<a title="...">` 属性，日期从 `<span class="date">YYYY-MM-DD</span>` 提取（旧格式兜底从 inner text 解析）。当日增量模式：翻页直到 `publish_date < today` 终止。三类公告统一映射 `BiddingType.public`，差异写入 `description`。去重用 `external_no` = `art_<32hex>`（URL 里的文章 ID）。
  - **zcy**: 浙江企业采购信息服务网 `b.zhengcaiyun.cn`（政采云）。**唯一需要外部调试 Chrome 进程的 scraper**。阿里云 WAF + Captcha Pro 双重保护，Python requests / curl_cffi 即使带 Chrome cookie 都会被 WAF 拦截（TLS 指纹 + 浏览器头不匹配）。**唯一稳定方案：CDP 驱动 Chrome 自己 fetch**。前置：用户用 `chrome.exe --remote-debugging-port=9222 --user-data-dir=C:/chrome-debug` 启动调试 Chrome 并打开政采云页面（必要时手动过滑块），scraper 通过 `ws://localhost:9222/devtools/page/<id>` 连 page-level CDP → `Runtime.evaluate` 执行页面内 `fetch('/portal/all', ...)` → Chrome 自动处理 TLS/sec-ch-ua/cookie → 收 JSON。**关键**：(1) `suppress_origin=True` 让 websocket-client 不发 Origin（Chrome 111+ 否则 403）；(2) page-level WS（非 browser-level），因 `Network.*` / `Runtime.evaluate` 只在 page 上下文可用；(3) **必须用 `/portal/all` 统一搜索接口（搜索页 `https://b.zhengcaiyun.cn/luban/search?k=&type=1` 调用的接口），不能用 `/portal/category`** —— `/portal/category?categoryCode=ZcyAnnouncement2` 实测只覆盖 4 种 pathName（询价/公开招标/竞争性谈判/竞争性磋商），**漏抓 ZcyAnnouncement10007 / 10011 等子类**（同一公告在 `/portal/detail` 能查到但 `/portal/category` 列表不返回，疑似 API 聚合 bug 或归档规则差异）；切换到 `/portal/all` 后当日 fetched 从 210 → 1112 (5x)，覆盖公示公告下全部 7 个子类；(4) `/portal/all` 支持服务端日期过滤 `publishDateBegin`/`publishDateEnd`（Unix ms），无需客户端早停；body 含 `keyword`/`firstCode`/`secondCode`/`districtCode`/`isTitleSearch`/`order`/`leaf` 等参数，`keyword=""` + `firstCode=""` + `secondCode=""` = 拿全量；(5) `articleId` 是 base64 字符串，详情 URL 需 URL-encode（`== → %3D%3D`，`/ → %2F`）；(6) `pathName` 形如 `"公示公告 | 采购公告 | 公开招标公告"`（含 ` | ` 分隔），normalize 时按 `|` 拆分后拼接进 description。`external_no = "zcy_" + articleId`。Cookie 失效或 WAF 重触 → 抛 `SiteFetchError`，run.error_summary 提示用户刷新页面。无 Playwright runtime 依赖（用户用现有 Chrome，scraper 仅借道 CDP）。
- **Scrape dedup**: `_find_duplicate` checks `external_no` (indexed) first, then exact `project_name`. No fuzzy matching. Does NOT update existing projects on duplicate (preserves user edits).
- **Scrape project fields**: Created projects have `status=跟进中`, `source` set to scraper name, `external_no` from announcement number, `source_url` from original link. Manual projects default `source=manual`. `source_url` rendered as clickable "公告链接" field in ProjectDetail basic info card (visible only when `source_url` is non-empty).
- **org_matcher.py**: `match_or_create_org` / `match_or_create_platform` extracted from `api/documents.py` into `services/org_matcher.py` for reuse by both document parsing and scrape runner.
- **No tests**: The project has no test suite.

## Design Document
Full system design spec: `docs/superpowers/specs/2026-04-01-bidding-management-system-design.md`
Implementation plan: `docs/superpowers/plans/2026-04-02-bidding-management-system-plan.md`
Auto-fetch integration spec: `docs/superpowers/specs/2026-06-16-auto-fetch-integration-design.md`
Auto-fetch integration plan: `docs/superpowers/plans/2026-06-16-auto-fetch-integration-plan.md`
