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
- **`main.py`** — App factory: CORS middleware, startup event (auto-creates tables + default admin + default organization with org_type=ours + auto-migration), route registration.

### Frontend Structure (`frontend/src/`)
- **`api/project.js`** — Single Axios-based API module for all project operations (CRUD + flow).
- **`components/`** — Shared components: `Layout.vue` (sidebar + header shell), `OrgSelector` (remote search + inline create, `excludeOurs` prop filters out our company), `PlatformSelector`/`ManagerSelector` (remote search + inline create), `RegionCascader` (省市区 picker).
- **`views/project/`** — Two pages: `ProjectList.vue` (list with custom column selector per-status config and quick status filter buttons) and `ProjectDetail.vue` (single page with 4 card sections in 2x2 grid layout).
- **`stores/user.js`** — Pinia store for auth state (token + user in localStorage).
- **`router/index.js`** — Vue Router with auth guard, lazy-loaded routes.

### Data Model (Single Table)

`project_infos` table with 4 logical sections:

| Section | Columns cover | Visible when |
|---------|--------------|-------------|
| 项目基本信息 | bidding_type, project_name, bidding_unit_id, region, manager_ids, status, parent_project_id (入围分项关联父入围标), etc. | Always |
| 招标信息 | agency_id, publish_platform_id, tags, deadlines, budget_amount, control_price_type/upper/lower, is_prequalification (是否入围标), is_registered (虚拟字段，从 status 推导), etc. | status >= 已发公告 |
| 投标信息 | partner_ids, bid_method, is_consortium_lead, deposit fields, our_price, etc. | status >= 准备投标 |
| 投标结果 | competitors (含 org_ids/price/score/is_winning), scoring_details, is_won + is_bid_failed (三态：已中标/未中标/流标), winning_org_ids (自动推导), winning_price/amount, result_deposit_status, contract fields, etc. | status >= 已投标 |

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

### Frontend-Backend Data Mapping
- Frontend sends region as `JSON.stringify(["浙江省","杭州市","西湖区"])`, stored in `String(100)` column
- JSON fields (`manager_ids`, `partner_ids`, `tags`, `competitors`, `scoring_details`, `winning_org_ids`) are stored as serialized JSON strings; frontend must `JSON.parse()` on read and send arrays on write. `competitors` stores `{org_ids: [int], price, score, is_shortlisted, is_winning}` per entry (old format `{org_id, ...}` auto-converted on load). `winning_org_ids` is auto-derived from competitors where `is_winning=true`.
- Frontend `collectSaveData()` only includes form fields from currently visible card sections to avoid sending irrelevant data (e.g., not sending `is_won` when result card isn't visible)
- **Competitors backward compat**: Old format `{org_id: 1, ...}` is auto-converted to `{org_ids: [1], ...}` in both `enrich_project()` (backend) and `loadProject()` (frontend). `is_winning` defaults to `false` for old data.

### Key Technical Notes
- **bcrypt**: Must pin `bcrypt==4.1.3`. Version 5.x is incompatible with `passlib 1.7.4` (causes `__about__` AttributeError and wrap bug ValueError).
- **JWT subject**: `sub` claim must be a string (`str(user.id)`), not an integer — `python-jose` validates this strictly.
- **JSON fields**: `manager_ids`, `partner_ids`, `tags`, `competitors`, `scoring_details`, `bid_documents`, `bid_files`, `winning_org_ids` are stored as JSON columns using SQLAlchemy `JSON` type.
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
- **Selector preload**: `PlatformSelector` and `OrgSelector`/`ManagerSelector` all use `preloadOptions()` with `loaded` flag on mount + `watch(modelValue)` for lazy load. This ensures el-select always has options for displaying names (not raw IDs) after save/reload.
- **loadProject watcher guard**: `_updatingFromWinning` flag wraps `resultForm` assignment in `loadProject()` to prevent `is_won` watcher from interfering during data loading. Without this, the watcher could reset competitors' `is_winning` flags before `ensureOurCompanyInCompetitors()` runs.
- **Column config persistence**: `ProjectList.vue` uses `watch(selectedColumnKeys)` (not `@change`) to save column config to localStorage. Each status tab has its own storage key (`project_list_columns_${status}`).
- **Bid result auto-trigger rules**: 未中标 cannot be manually selected via radio button (`handleBidResultChange('lost')` is a no-op). It is only auto-triggered when a non-our competitor has `is_winning` checked (via `handleWinningChange`). Conversely, when ALL `is_winning` checkboxes are unchecked, `handleWinningChange` sets `is_won=false`, and on save the backend reverts status to 已投标 regardless of previous state (已中标/未中标/已投标). Frontend `collectSaveData()` always sends `is_won`/`is_bid_failed` when result card is visible — backend handles all derivation logic.
- **No tests**: The project has no test suite.

## Design Document
Full system design spec: `docs/superpowers/specs/2026-04-01-bidding-management-system-design.md`
Implementation plan: `docs/superpowers/plans/2026-04-02-bidding-management-system-plan.md`
