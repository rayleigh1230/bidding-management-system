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
- **`api/scrape.py`** — Auto-scrape endpoints. `POST /api/scrape/run` triggers a scrape run (admin only, returns `{run_id}` immediately, runs `run_scraper` via BackgroundTasks). `GET /api/scrape/status/{run_id}` for polling. `GET /api/scrape/runs` lists history. `GET /api/scrape/runs/{run_id}` returns detail with item_logs. `require_admin` dependency checks `role == "admin"`. Prevents concurrent runs (409 if another run is `running`).
- **`services/document_parser.py`** — Qwen-Long integration via OpenAI-compatible DashScope client. `QwenLongParser.upload_file()` → `parse(file_id, parse_type, control_price_type)` → `_normalize(raw, parse_type)` dispatches to `_normalize_bidding` or `_normalize_result`. `FIELD_ALIASES` / `RESULT_CANDIDATE_ALIASES` / `RESULT_TOP_ALIASES` map Chinese LLM keys to English. `_build_result_prompt()` injects price unit hint based on project's `control_price_type`.
- **`services/scrape_runner.py`** — Main scrape orchestration. `run_scraper(run_id, user_id)` iterates all scrapers, calls `fetch_with_retry` → `normalize` → `_process_item`. `_find_duplicate` checks `external_no` first, then `project_name`. `_process_item` creates ProjectInfo with `status=following`. `_record_failure` / `_log_item` write to `scrape_item_logs`. Counter invariant: `total_count = created_count + skipped_count + failed_count`.
- **`services/org_matcher.py`** — Shared `match_or_create_org` / `match_or_create_platform` helpers, reused by both `documents.py` and `scrape_runner.py`.
- **`scrapers/`** — Bid announcement scrapers. `base.py` defines `BaseScraper` (abstract `fetch`/`normalize`, `fetch_with_retry` with 3 retries + exponential backoff), `ScrapeItem` dataclass, `SiteFetchError`, `KEYWORDS`, `match_keywords()`, `match_region_zhejiang()`, `parse_date_safe()`. `__init__.py:ScraperRegistry` lazily imports and instantiates all scrapers via `importlib.import_module` (fault-tolerant — a broken scraper doesn't crash the run). Site modules: `ccgp.py` (scrapling/curl_cffi), `ggzy.py` (requests + WAF), `jhygcg.py` (requests), `jhzjcs.py` (requests POST JSON API, direct `getComparePublicList` call), `jhggzy.py` (requests GET AJAX API, 11 县区 × 3 公告类型 = 33 数据源).
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
`list_projects` endpoint supports 23 query parameters for filtering:
- **Basic**: `keyword` (project name, with `keyword_match`="fuzzy"/"exact"), `status`, `bidding_type`
- **Organization**: `bidding_unit_id`, `agency_id`, `publish_platform_id`, `manager_id` (JSON array via `json_each`), `partner_id` (JSON array via `json_each`)
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
- **Column config persistence**: `ProjectList.vue` uses `watch(selectedColumnKeys)` (not `@change`) to save column config to localStorage. Each status tab has its own storage key (`project_list_columns_${status}`).
- **Bid result auto-trigger rules**: 未中标 cannot be manually selected via radio button (`handleBidResultChange('lost')` is a no-op). It is only auto-triggered when a non-our competitor has `is_winning` checked (via `handleWinningChange`). Conversely, when ALL `is_winning` checkboxes are unchecked, `handleWinningChange` sets `is_won=false`, and on save the backend reverts status to 已投标 regardless of previous state (已中标/未中标/已投标). Frontend `collectSaveData()` always sends `is_won`/`is_bid_failed` when result card is visible — backend handles all derivation logic.
- **Document parsing (招标公告)**: `POST /api/documents/parse?parse_type=bidding&project_id=N` uploads file → Qwen-Long extracts fields → auto-creates bidding_unit/agency/platform orgs via `_match_or_create_org` (with `org_type=external`) → returns form fields for frontend to apply. File metadata appended to `bid_documents` on save. System prompt in `document_parser.py:SYSTEM_PROMPT` asks LLM to extract bidding fields; `FIELD_ALIASES` maps Chinese keys to English.
- **Document parsing (中标公告)**: Same endpoint with `parse_type=result`. `_build_result_prompt(control_price_type)` injects price unit hint (金额=元 / 折扣率=百分比 / 下浮率=下浮百分比). Response `fields.competitors[]` contains `{org_ids, org_names, price, score, rank, is_winning}` per candidate; `_match_or_create_org` runs per org name (consortium names split by 、，;／). Response auto-derives `is_won` by checking if any winning candidate includes our company (`org_type=ours`). File metadata appended to `result_documents` on save. Frontend `applyResultFields` replaces competitors entirely but preserves our-company entry if not present in parse result.
- **Parser normalize**: `_normalize(raw, parse_type)` dispatches to `_normalize_bidding` (flat field aliases) or `_normalize_result` (nested candidates array with `RESULT_CANDIDATE_ALIASES` + `RESULT_TOP_ALIASES`). Result mode splits consortium unit names like "A公司、B公司" → `["A公司","B公司"]` via regex `[,，;；/、]`.
- **下浮率 swap**: In `_build_bidding_response`, when `control_price_type=下浮率` and `upper > lower`, the two values are swapped (semantic: 上限=最小降价幅度=较小值, 下限=最大降价幅度=较大值).
- **入围标 LLM detection**: `SYSTEM_PROMPT` field `是否资格预审` doubles as `是否入围标`. Trigger keywords include 入围 / 入围标 / 短名单 / 资格预审 / 合格供应商库 / 框架协议 / 入围候选人. `FIELD_ALIASES` maps both Chinese keys to `is_prequalification`.
- **Bid specialist auto-follow**: `ProjectDetail.vue` has `watch(showBidding)` that defaults `biddingForm.bid_specialist_id` to `userStore.user.id` when bidding card first becomes visible (status ≥ 已发公告) AND field is empty. Uses Pinia `useUserStore` (loaded from localStorage via `/api/auth/me` after login).
- **Post-parse orgMap refresh**: `handleFileChange` / `handleResultFileChange` call `await loadOrgNames()` after `applyParsedFields` / `applyResultFields`. Required because `_match_or_create_org` creates new orgs during parse; without refresh, `getOrgName(oid)` returns '未知单位' for newly created orgs not yet in `orgMap`.
- **Auto-scrape**: `POST /api/scrape/run` (admin only) triggers `run_scraper(run_id, user_id)` via FastAPI BackgroundTasks. Iterates all registered scrapers (ccgp/ggzy/jhygcg/jhzjcs/jhggzy) via `ScraperRegistry.all()` (lazy-loaded, fault-tolerant). Prevents concurrent runs (409). Orphan runs cleaned on startup.
- **Scraper architecture**: `scrapers/base.py:BaseScraper` (abstract `fetch`/`normalize`, `fetch_with_retry` with 3 retries + exponential backoff, error message includes exception type). `ScraperRegistry` uses `importlib.import_module` with try/except per scraper. All five site modules use `requests` (no Playwright runtime dependency): `ccgp.py` (scrapling + curl_cffi browser fingerprint), `ggzy.py` (requests + WAF bypass via session cookie warmup), `jhygcg.py` (requests POST JSON API), `jhzjcs.py` (requests POST JSON API, direct `getComparePublicList` call), `jhggzy.py` (requests GET AJAX API, 33 数据源).
- **Result announcement filter**: `scrapers/base.py:RESULT_KEYWORDS` + `is_result_announcement()` excludes 中标/成交/开标/结果/废标/流标/终止/合同 公告/公示/记录. All five scrapers call this in `normalize()` to keep only 招标公告.
- **Keyword + region filter**: `scrapers/base.py:KEYWORDS` = [检测/人防/防雷/消防/勘察/测绘/监测/鉴定/评估/试验], OR match. `match_region_zhejiang()` checks title for 浙江 city names, or CCGP zoneId / GGZY infoc starting with 330. jhygcg/jhzjcs/jhggzy are inherently 金华市, skip region check.
- **Site-specific fetch details**:
  - **ggzy**: `categorynum=002001001` (招标公告, NOT 002001003 which is 中标候选人公示). `infoc=330` filters 浙江全省. source_url prepends `https://ggzy.zj.gov.cn` when API returns relative path starting with `/`.
  - **jhygcg**: Searches with `classID=21` (采购公告) but API mixes in classId=22 (成交候选人) and 24 (采购结果) — `normalize()` filters `classId != "21"` out. source_url uses `/detail?bulletinId={articleId}` (no `/home/` prefix).
  - **jhzjcs**: Direct API call to `getComparePublicList` with `selectedOptionId=6bbd9b33-ad3b-4c7a-a689-4365326f2626` (工程检验检测 category). `pageSize=200` to fetch all projects in one request. **No keyword/name filter** — all projects under this category are kept. source_url uses `comparison_public.html?id={guid}`.
  - **ccgp**: Uses scrapling with curl_cffi impersonation to bypass anti-bot. Zone `330` for 浙江.
  - **jhggzy**: 金华市公共资源交易网 `ggzyjy.jinhua.gov.cn`（HTTP only，HTTPS 返回 410）。覆盖 11 县区分站（市本级/婺城/金东/兰溪/义乌/东阳/永康/浦江/武义/磐安/开发区）× 3 公告类型（预公告/招标公告/采购公告）= 33 个数据源，配置表硬编码在 `SOURCES`。API: `GET /api-gateway/jpaas-publish-server/front/page/build/unit` + `webId=3818` + `tplSetId=LpcyxkYSwRoJNKPT7EX2v` + `tagId=概览信息列表` + `paramJson={pageNo,pageSize}`，返回 `data.html` 为 HTML 片段。**pageId 处理**：顶级栏目（预公告/采购公告）URL `/col/col<colId>/index.html` 的 pageId 直接 = colId；子路径栏目（招标公告）URL `/col/col<parent>/<sub>/index.html` 的 pageId 是 jcms 生成的哈希，需先 fetch 静态页从 `queryData` 属性（注意大写 D）解析，缓存到实例。**HTML 解析**：标题优先用 `<a title="...">` 属性，日期从 `<span class="date">YYYY-MM-DD</span>` 提取（旧格式兜底从 inner text 解析）。当日增量模式：翻页直到 `publish_date < today` 终止。三类公告统一映射 `BiddingType.public`，差异写入 `description`。去重用 `external_no` = `art_<32hex>`（URL 里的文章 ID）。
- **Scrape dedup**: `_find_duplicate` checks `external_no` (indexed) first, then exact `project_name`. No fuzzy matching. Does NOT update existing projects on duplicate (preserves user edits).
- **Scrape project fields**: Created projects have `status=跟进中`, `source` set to scraper name, `external_no` from announcement number, `source_url` from original link. Manual projects default `source=manual`. `source_url` rendered as clickable "公告链接" field in ProjectDetail basic info card (visible only when `source_url` is non-empty).
- **org_matcher.py**: `match_or_create_org` / `match_or_create_platform` extracted from `api/documents.py` into `services/org_matcher.py` for reuse by both document parsing and scrape runner.
- **No tests**: The project has no test suite.

## Design Document
Full system design spec: `docs/superpowers/specs/2026-04-01-bidding-management-system-design.md`
Implementation plan: `docs/superpowers/plans/2026-04-02-bidding-management-system-plan.md`
Auto-fetch integration spec: `docs/superpowers/specs/2026-06-16-auto-fetch-integration-design.md`
Auto-fetch integration plan: `docs/superpowers/plans/2026-06-16-auto-fetch-integration-plan.md`
