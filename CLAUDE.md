# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

招标信息收集和投标信息管理系统 — internal tool for a small team (<5 people) to manage the full bidding lifecycle: 项目信息 → 招标信息 → 投标信息 → 投标结果. Each stage transition is driven by flow buttons that auto-create the next stage record and update project status.

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
npm run dev    # dev server, proxies /api to backend:8000 via vite.config.js
```

### Database
SQLite file at `backend/data/app.db`. Auto-created on first startup. To reset: delete the file and restart the server. Default admin user `admin / admin123` is created on first startup.

## Architecture

### Backend Structure (`backend/app/`)
- **`core/`** — config (pydantic-settings from `.env`), database (SQLAlchemy engine/session/Base), security (JWT via python-jose, bcrypt via passlib)
- **`models/`** — SQLAlchemy 2.0 declarative models using `Mapped` + `mapped_column`. Each table in its own file. Enums defined alongside their models.
- **`schemas/`** — Pydantic v2 models for request/response validation. `model_config = {"from_attributes": True}` for ORM mode.
- **`api/`** — FastAPI routers, one file per resource. All routes require JWT auth via `Depends(get_current_user)`.
- **`main.py`** — App factory: CORS middleware, startup event (auto-creates tables + default admin), route registration.

### Frontend Structure (`frontend/src/`)
- **`api/`** — Axios-based API modules, one per backend resource. `index.js` is the shared Axios instance with JWT interceptor and 401 redirect.
- **`components/`** — Shared components: `Layout.vue` (sidebar + header shell), `OrgSelector`/`PlatformSelector`/`ManagerSelector` (remote search + inline create), `RegionCascader` (省市区 picker).
- **`views/`** — Page components organized by domain: `project/`, `bidding/`, `bid/`, `result/`, `admin/`, `stats/`.
- **`stores/user.js`** — Pinia store for auth state (token + user in localStorage).
- **`router/index.js`** — Vue Router with auth guard, lazy-loaded routes.
- **`utils/region-data.js`** — China administrative division data (省/市/区).

### Data Model Relationships
```
Organization ←── ProjectInfo.bidding_unit_id
                       │
                       ├── BiddingInfo.project_id (1:1)
                       │        │
                       │        └── BidInfo.bidding_info_id (1:1)
                       │                 │
                       │                 └── BidResult.bid_info_id (1:1)
                       │
Manager ←───── ProjectInfo.manager_ids (JSON array of IDs)
Platform ←──── BiddingInfo.publish_platform_id
User ←──────── ProjectInfo.created_by, BidInfo.created_by, BiddingInfo.bid_specialist_id
```

### Core Business Flow (ProjectStatus enum)
```
跟进中 →(publish)→ 已发公告 →(prepare)→ 准备投标 →(submit)→ 已投标 →(result)→ 已中标/未中标
  └→(abandon)→ 已放弃 (any stage)
```
Flow operations live in the API files (e.g., `POST /api/projects/{id}/publish` in `projects.py`). Each flow endpoint auto-creates the next-stage record and updates the project status.

### API Response Conventions
- List endpoints return `{"items": [...], "total": N, "page": P, "page_size": S}`
- Flow endpoints return `{"message": "...", "<entity>_id": N}` (e.g., `{"message": "发布公告成功", "bidding_info_id": 1}`)
- All endpoints use `model_dump(exclude_unset=True)` for partial updates

### Frontend-Backend Data Mapping
- Frontend sends region as `JSON.stringify(["浙江省","杭州市","西湖区"])`, stored in `String(100)` column
- JSON fields (`manager_ids`, `partner_ids`, `tags`, `competitors`, `scoring_details`) are stored as serialized JSON strings; frontend must `JSON.parse()` on read and send arrays on write
- Flow buttons on detail pages call the flow endpoint then `router.push()` to the newly created entity

### Key Technical Notes
- **bcrypt**: Must pin `bcrypt==4.1.3`. Version 5.x is incompatible with `passlib 1.7.4` (causes `__about__` AttributeError and wrap bug ValueError).
- **JWT subject**: `sub` claim must be a string (`str(user.id)`), not an integer — `python-jose` validates this strictly.
- **JSON fields**: `manager_ids`, `partner_ids`, `tags`, `competitors`, `scoring_details`, `bid_documents`, `bid_files` are stored as JSON columns. Some use SQLAlchemy `JSON` type, others use `String` with serialized JSON. Always check the model definition before assuming which format is used.
- **Enriched responses**: List/detail endpoints return joined data (e.g., `project_name`, `bidding_unit_name`, `manager_names`) populated by `enrich_*()` helper functions in the API files, not via SQLAlchemy relationships.
- **No tests**: The project has no test suite.

## Design Document
Full system design spec: `docs/superpowers/specs/2026-04-01-bidding-management-system-design.md`
Implementation plan: `docs/superpowers/plans/2026-04-02-bidding-management-system-plan.md`
