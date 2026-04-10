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
| 项目基本信息 | bidding_type, project_name, bidding_unit_id, region, manager_ids, status, etc. | Always |
| 招标信息 | agency_id, publish_platform_id, tags, deadlines, budget_amount, control_price_type/upper/lower, is_prequalification (是否入围标), etc. | status >= 已发公告 |
| 投标信息 | partner_ids, bid_method, bid_status, deposit fields, our_price, etc. | status >= 准备投标 |
| 投标结果 | competitors (含 price/score/is_shortlisted), scoring_details, is_won, winning_org_ids (多中标单位), winning_price/amount, result_deposit_status, contract fields, etc. | status >= 已投标 |

**Field naming for merged columns:**
- BiddingInfo.notes → `bidding_notes`
- BidInfo.notes → `bid_notes`
- BidResult.notes → `result_notes`
- BidResult.deposit_status → `result_deposit_status`

**All enums** (BiddingType, ProjectStatus, BudgetType, BidMethod, BidStatus, DepositStatus, ContractStatus, ResultDepositStatus) are defined in `models/project.py`.

### Core Business Flow (ProjectStatus enum)
```
跟进中 →(publish)→ 已发公告 →(prepare)→ 准备投标 →(submit)→ 已投标 →(is_won update)→ 已中标/未中标
  └→(abandon)→ 已放弃 (any stage)
```
Flow endpoints only change the status field — no new records are created:
- `POST /api/projects/{id}/publish` — 跟进中 → 已发公告
- `POST /api/projects/{id}/prepare` — 已发公告 → 准备投标
- `POST /api/projects/{id}/submit` — 准备投标 → 已投标 (+ sets `result_deposit_status=未收回` when `has_deposit=true` and `deposit_status=已缴纳`)
- `POST /api/projects/{id}/abandon` — any → 已放弃 (with reason)
- `PUT /api/projects/{id}` with `is_won` field — 已投标 → 已中标/未中标 (auto-calculates winning_price/winning_amount, except for 入围标 which uses manual input)

### API Response Conventions
- List endpoints return `{"items": [...], "total": N, "page": P, "page_size": S}`
- Flow endpoints return `{"message": "..."}`
- All endpoints use `model_dump(exclude_unset=True)` for partial updates
- `enrich_project()` populates all related names and computed display fields

### Frontend-Backend Data Mapping
- Frontend sends region as `JSON.stringify(["浙江省","杭州市","西湖区"])`, stored in `String(100)` column
- JSON fields (`manager_ids`, `partner_ids`, `tags`, `competitors`, `scoring_details`, `winning_org_ids`) are stored as serialized JSON strings; frontend must `JSON.parse()` on read and send arrays on write. `competitors` stores `{org_id, price, score, is_shortlisted}` per entry. `winning_org_ids` stores array of org IDs for multiple winning orgs (入围标/联合体).
- Frontend `collectSaveData()` only includes form fields from currently visible card sections to avoid sending irrelevant data (e.g., not sending `is_won` when result card isn't visible)

### Key Technical Notes
- **bcrypt**: Must pin `bcrypt==4.1.3`. Version 5.x is incompatible with `passlib 1.7.4` (causes `__about__` AttributeError and wrap bug ValueError).
- **JWT subject**: `sub` claim must be a string (`str(user.id)`), not an integer — `python-jose` validates this strictly.
- **JSON fields**: `manager_ids`, `partner_ids`, `tags`, `competitors`, `scoring_details`, `bid_documents`, `bid_files`, `winning_org_ids` are stored as JSON columns using SQLAlchemy `JSON` type.
- **Price calculation**: `_control_type_str()` handles Python 3.13 enum str() issue (returns enum member like `BudgetType.discount_rate` instead of value). Always use this helper instead of raw comparison.
- **Winning amount formula**: 折扣率: `our_price / upper * budget`. 下浮率: `(1 - our_price/100) / (1 - upper/100) * budget`. 金额: `our_price` directly.
- **Status guard**: Backend only allows is_won → status change when current status is "已投标", preventing premature status changes from partial saves.
- **入围标 (shortlisting)**: When `is_prequalification=true`, competitors have an "入围" checkbox. Checking it auto-adds the org to `winning_org_ids`. In won state, winning_price/winning_amount use manual input (not auto-calculated). Our company is auto-added to competitors when status >= 已投标 (via `ensureOurCompanyInCompetitors()` at end of `loadProject()`). Watch on `is_won` auto-toggles our company's `is_shortlisted` and `winning_org_ids` for 入围标.
- **OrgType filter**: Organizations have `org_type` field (ours/external). `OrgSelector` has `excludeOurs` prop to filter out our company from bidding_unit, agency, and partner selections, while keeping it available for competitors and winning org.
- **Multi winning orgs**: `winning_org_ids` (JSON array) supports multiple winning orgs (入围标 multiple shortlisted, 联合体 consortium). `winning_org_id` (single Integer) kept for backward compat. Frontend uses el-tag display with inline el-select search for adding orgs.
- **Bid deposit two-state model**: `DepositStatus` enum (`无`/`未缴纳`/`已缴纳`) for bid info section's `deposit_status` field. `ResultDepositStatus` enum (`未收回`/`已收回`) for result section's `result_deposit_status` field. Submit endpoint sets `result_deposit_status=未收回` only when `deposit_status=已缴纳`. Result section's deposit UI only shows when `deposit_status=已缴纳`. `enrich_project()` computes `deposit_status_display` field: shows 缴纳状态 before 已投标, shows 收回状态 from 已投标 onward.
- **OrgMap loading**: `loadOrgNames()` uses `page_size=100` (backend max). Previously used 500 which caused 422 error and empty orgMap, breaking all org-dependent features.
- **No tests**: The project has no test suite.

## Design Document
Full system design spec: `docs/superpowers/specs/2026-04-01-bidding-management-system-design.md`
Implementation plan: `docs/superpowers/plans/2026-04-02-bidding-management-system-plan.md`
