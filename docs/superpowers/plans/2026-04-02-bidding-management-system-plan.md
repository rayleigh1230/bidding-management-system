# 招标信息管理系统 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建招标信息收集和投标信息管理系统，覆盖项目信息→招标信息→投标信息→投标结果的完整流程。

**Architecture:** FastAPI 后端 + Vue 3 前端前后端分离，SQLite 文件数据库，JWT 认证，单体应用内网部署。

**Tech Stack:** Python 3.10+, FastAPI, SQLAlchemy 2.0, Pydantic v2, Vue 3, Element Plus, Pinia, ECharts

**设计文档:** `docs/superpowers/specs/2026-04-01-bidding-management-system-design.md`

---

## 实现后变更记录（2026-04-08）

> 以下变更在初始实现计划全部完成后进行，记录了数据模型、API 和前端的重要调整。

### 数据模型变更

1. **BiddingInfo** — `budget_type`（枚举：单价/总金额）替换为 `control_price_type`（枚举：金额/折扣率/下浮率），并新增 `control_price_upper` 和 `control_price_lower` 两个可空字段，支持招标控制价范围录入。
2. **BidInfo** — 新增 `our_price` 字段（Decimal(15,2)，默认0），从 BidResult 移过来。投标报价录入在投标信息阶段完成。
3. **BidResult** — 删除 `our_price`（移到 BidInfo），新增 `winning_org_id`（外键→Organization）和 `winning_price`（Decimal(15,2)），用于记录中标单位和中标价格。

### API 变更

- `enrich_project()` 新增 `include_related` 参数，`GET /api/projects/{id}` 现在一次性返回完整关联链（bidding_info、bid_info、bid_result），前端无需多次请求。
- 项目删除从"阻断式"（有关联则报错）改为级联删除（自动删除 BidResult→BidInfo→BiddingInfo→Project）。
- `enrich_bid_result()` 增强为完整链路遍历，自动计算 `our_price_display`（我方报价格式化显示）和 `winning_price_display`（中标价格格式化显示）。
- 列表接口（projects、biddings、bids）均新增 `status` 查询参数，支持按项目状态过滤，使用 `try/except` 安全解析枚举。

### 前端变更

- **新增页面** `ProjectInfoList.vue`（路由 `/project-info`）：只显示"跟进中"状态的项目，提供快速访问入口。
- **ProjectDetail.vue 大幅重写**：新建时单列布局，编辑时两列布局（项目信息+招标信息 并排）；底部追加投标信息和投标结果卡片；放弃的项目以只读 `el-descriptions` 展示。
- **BiddingDetail.vue**：`budget_type` 替换为 `control_price_type` + 控制价范围输入，标签和单位根据类型动态切换。
- **BidDetail.vue**：新增 `our_price` 字段，标签和单位根据 `control_price_type` 动态显示。
- **ResultDetail.vue**：`our_price` 改为只读显示（来自 BidInfo，格式化后展示）；未中标时可录入中标单位和中标价格。
- **各列表页**：BiddingList 默认过滤"已发公告"，BidList 默认过滤"准备投标"，ResultList 新增"中标单位"列。
- **Layout.vue**：侧边栏新增"项目信息"菜单项。

### 新增文件

- `backend/migrate_db.py` — 数据库迁移脚本（将 our_price 从 bid_results 迁移到 bid_infos，添加 winning_org_id 和 winning_price）
- `frontend/src/views/project/ProjectInfoList.vue` — 跟进中项目快速查看页

---

## Phase 1: 后端基础

### Task 1: 后端项目脚手架 + 数据库配置

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/app/__init__.py`
- Create: `backend/app/main.py`
- Create: `backend/app/core/__init__.py`
- Create: `backend/app/core/config.py`
- Create: `backend/app/core/database.py`
- Create: `backend/data/.gitkeep`
- Create: `backend/uploads/.gitkeep`

- [ ] **Step 1: 创建 backend 目录结构和 requirements.txt**

`backend/requirements.txt`:
```
fastapi==0.115.0
uvicorn[standard]==0.30.0
sqlalchemy==2.0.35
pydantic==2.9.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.9
```

- [ ] **Step 2: 创建 core/config.py — 应用配置**

使用 pydantic-settings 管理配置（数据库路径、JWT密钥等）。

- [ ] **Step 3: 创建 core/database.py — SQLAlchemy 引擎和会话**

SQLite 连接、`SessionLocal`、`Base` 声明基类、`get_db` 依赖注入。

- [ ] **Step 4: 创建 main.py — FastAPI 应用入口**

包含 CORS 中间件、启动时自动建表、路由挂载占位。

- [ ] **Step 5: 安装依赖并验证启动**

Run: `cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload`
Expected: 服务启动，访问 http://localhost:8000/docs 看到 Swagger 文档页面

- [ ] **Step 6: Commit**

---

### Task 2: 全部 SQLAlchemy 数据模型

**Files:**
- Create: `backend/app/models/__init__.py`
- Create: `backend/app/models/user.py`
- Create: `backend/app/models/organization.py`
- Create: `backend/app/models/platform.py`
- Create: `backend/app/models/manager.py`
- Create: `backend/app/models/project.py`
- Create: `backend/app/models/bidding_info.py`
- Create: `backend/app/models/bid_info.py`
- Create: `backend/app/models/bid_result.py`
- Create: `backend/app/models/operation_log.py`

- [ ] **Step 1: 创建字典表模型 — Organization, Platform, Manager**

三个模型各自独立文件，`__init__.py` 统一导入。字段严格按照设计文档 2.1 节。

- [ ] **Step 2: 创建 User 模型**

包含 username, password_hash, display_name, role (admin/user), phone, is_active。

- [ ] **Step 3: 创建 ProjectInfo 模型**

包含 bidding_type (4种枚举), project_name, bidding_unit_id (FK→Organization), region (JSON), manager_ids (JSON), status (7种枚举), description, created_by (FK→User)。

- [ ] **Step 4: 创建 BiddingInfo 模型**

包含 project_id (FK→ProjectInfo, unique), agency_id (FK→Organization), publish_platform_id (FK→Platform), tags (JSON), 两个日期字段, budget_type/budget_amount, is_prequalification, bid_specialist_id (FK→User), bid_documents (JSON)。

- [ ] **Step 5: 创建 BidInfo 模型**

包含 bidding_info_id (FK→BiddingInfo, unique), partner_ids (JSON), bid_method (4种枚举), bid_status (4种枚举), 保证金相关5个字段, bid_files (JSON)。

- [ ] **Step 6: 创建 BidResult 模型**

包含 bid_info_id (FK→BidInfo, unique), our_price, competitors (JSON), scoring_details (JSON), deposit_status (2种枚举), is_won, lost_analysis, contract_number, contract_status (4种枚举), contract_amount。

- [ ] **Step 7: 创建 OperationLog 模型**

包含 user_id (FK→User), action, entity_type, entity_id, detail。

- [ ] **Step 8: 验证模型创建成功**

重启服务，检查 SQLite 文件中是否自动创建了所有表。
Run: `uvicorn app.main:app --reload`

- [ ] **Step 9: Commit**

---

### Task 3: 认证系统 (JWT + 登录)

**Files:**
- Create: `backend/app/core/security.py`
- Create: `backend/app/schemas/__init__.py`
- Create: `backend/app/schemas/auth.py`
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/api/auth.py`
- Create: `backend/app/services/__init__.py`

- [ ] **Step 1: 创建 core/security.py — JWT工具函数**

实现 `create_access_token()`, `verify_token()`, `get_password_hash()`, `verify_password()` 四个函数。使用 python-jose + passlib.bcrypt。

- [ ] **Step 2: 创建 schemas/auth.py — 请求/响应模型**

`LoginRequest(username, password)`, `TokenResponse(access_token, token_type)`, `CurrentUser(id, username, display_name, role)`。

- [ ] **Step 3: 创建 api/auth.py — 认证路由**

POST `/api/auth/login` — 验证用户名密码，返回 JWT
GET `/api/auth/me` — 获取当前用户信息（需认证）

- [ ] **Step 4: 在 main.py 添加认证路由和启动时创建默认管理员**

启动时检查是否存在 admin 用户，不存在则创建 (admin/admin123)。

- [ ] **Step 5: 验证认证流程**

Run: 启动服务，用 Swagger 测试登录接口，获取 token。

- [ ] **Step 6: Commit**

---

### Task 4: 字典表 CRUD API

**Files:**
- Create: `backend/app/schemas/dict.py`
- Create: `backend/app/api/organizations.py`
- Create: `backend/app/api/platforms.py`
- Create: `backend/app/api/managers.py`

- [ ] **Step 1: 创建 schemas/dict.py — 字典表 Pydantic schemas**

OrganizationCreate, OrganizationUpdate, OrganizationResponse, 同理 Platform 和 Manager。列表接口统一支持 `keyword` 搜索参数和分页。

- [ ] **Step 2: 创建 organizations API**

GET (列表+搜索+分页), POST (新增), PUT/{id} (更新), DELETE/{id} (删除)。

- [ ] **Step 3: 创建 platforms API**

同上模式。

- [ ] **Step 4: 创建 managers API**

同上模式。

- [ ] **Step 5: 在 main.py 注册路由**

- [ ] **Step 6: 验证 CRUD**

Run: 用 Swagger 测试各字典表的增删改查和搜索。

- [ ] **Step 7: Commit**

---

### Task 5: 核心业务 CRUD API

**Files:**
- Create: `backend/app/schemas/project.py`
- Create: `backend/app/schemas/bidding.py`
- Create: `backend/app/schemas/bid.py`
- Create: `backend/app/schemas/result.py`
- Create: `backend/app/api/projects.py`
- Create: `backend/app/api/bidding_infos.py`
- Create: `backend/app/api/bid_infos.py`
- Create: `backend/app/api/bid_results.py`

- [ ] **Step 1: 创建项目相关 schemas**

ProjectCreate, ProjectUpdate, ProjectResponse (含关联的招标单位名称、负责人名称等展开字段)。

- [ ] **Step 2: 创建 projects API**

GET (列表+多条件筛选+分页), POST, GET/{id} (详情含关联数据), PUT/{id}, DELETE/{id}。

- [ ] **Step 3: 创建招标信息 schemas 和 API**

BiddingInfoCreate, BiddingInfoUpdate, BiddingInfoResponse。API 同上模式。

- [ ] **Step 4: 创建投标信息 schemas 和 API**

BidInfoCreate, BidInfoUpdate, BidInfoResponse。API 同上模式。

- [ ] **Step 5: 创建投标结果 schemas 和 API**

BidResultCreate, BidResultUpdate, BidResultResponse。API 同上模式。

- [ ] **Step 6: 在 main.py 注册路由**

- [ ] **Step 7: 验证全部 CRUD 接口**

Run: Swagger 测试完整流程：创建项目 → 查看列表 → 查看详情 → 更新。

- [ ] **Step 8: Commit**

---

### Task 6: 流程操作 + 操作日志

**Files:**
- Create: `backend/app/services/flow.py`
- Create: `backend/app/services/logger.py`
- Create: `backend/app/api/logs.py`

- [ ] **Step 1: 创建 services/logger.py — 操作日志服务**

`log_operation(db, user_id, action, entity_type, entity_id, detail)` 函数，写入 OperationLog 表。

- [ ] **Step 2: 创建 services/flow.py — 流程推进服务**

实现三个核心流程：
- `publish_project(project_id)` — 创建 BiddingInfo 记录，更新项目状态为"已发公告"
- `prepare_bid(bidding_info_id)` — 创建 BidInfo 记录，更新项目状态为"准备投标"
- `submit_bid(bid_info_id)` — 创建 BidResult 记录，更新 bid_status 为"已投标"，更新项目状态为"已投标"，如有保证金自动变"未收回"

- [ ] **Step 3: 添加流程 API 路由到各业务 api 文件**

POST `/api/projects/{id}/publish`
POST `/api/projects/{id}/abandon`
POST `/api/biddings/{id}/prepare`
POST `/api/biddings/{id}/abandon`
POST `/api/bids/{id}/submit`
POST `/api/bids/{id}/abandon`

- [ ] **Step 4: 创建 api/logs.py — 日志查询 API**

GET `/api/logs` — 分页查询操作日志。

- [ ] **Step 5: 在所有 CRUD 和流程操作中嵌入日志记录**

- [ ] **Step 6: 验证完整流程**

Swagger 测试：创建项目 → 发布公告 → 准备投标 → 提交投标 → 查看日志。

- [ ] **Step 7: Commit**

---

### Task 7: 统计 API + 用户管理 API

**Files:**
- Create: `backend/app/api/stats.py`
- Create: `backend/app/schemas/user.py`
- Create: `backend/app/api/users.py`

- [ ] **Step 1: 创建 stats.py — 4个统计接口**

- GET `/api/stats/overview` — 仪表盘数据（各状态项目数、本月中标情况、待办提醒）
- GET `/api/stats/win-rate` — 中标率统计（按时间维度）
- GET `/api/stats/competitors` — 竞争对手分析
- GET `/api/stats/deposits` — 保证金跟踪

- [ ] **Step 2: 创建用户管理 schemas 和 API**

UserCreate, UserUpdate, UserResponse。GET (列表), POST (新增), PUT/{id} (更新)。

- [ ] **Step 3: 在 main.py 注册路由**

- [ ] **Step 4: 验证统计和用户管理接口**

- [ ] **Step 5: Commit**

---

## Phase 2: 前端基础

### Task 8: 前端项目脚手架 + 布局 + 路由

**Files:**
- Create: `frontend/` (Vue 3 + Vite 项目)
- Create: `frontend/src/components/Layout.vue`
- Create: `frontend/src/router/index.js`
- Create: `frontend/src/stores/user.js`
- Create: `frontend/src/api/index.js`

- [ ] **Step 1: 用 Vite 创建 Vue 3 项目**

Run: `cd E:/经营中心信息管理 && npm create vite@latest frontend -- --template vue`
然后安装依赖: `cd frontend && npm install element-plus @element-plus/icons-vue vue-router@4 pinia axios echarts`

- [ ] **Step 2: 配置 main.js — 注册 Element Plus, Pinia, Router**

- [ ] **Step 3: 创建 Layout.vue — 左侧菜单 + 顶部导航 + 内容区**

左侧菜单项：工作台、项目管理、招标信息、投标信息、投标结果、数据分析、基础数据管理、操作日志。

- [ ] **Step 4: 创建 router/index.js — 全部路由定义**

包含所有页面路由，添加路由守卫（未登录跳转登录页）。

- [ ] **Step 5: 创建 api/index.js — Axios 实例**

配置 baseURL、JWT 拦截器（请求头加 token）、401 响应拦截跳转登录。

- [ ] **Step 6: 创建 stores/user.js — 用户状态管理**

存储 token 和用户信息，登录/登出方法。

- [ ] **Step 7: 创建各页面占位 Vue 文件**

所有 views 下的页面先创建空壳 `<template><div>页面名</div></template>`。

- [ ] **Step 8: 验证前端启动和路由跳转**

Run: `cd frontend && npm run dev`
Expected: 所有菜单可点击，路由跳转正常，未登录自动跳转登录页。

- [ ] **Step 9: Commit**

---

### Task 9: 登录页

**Files:**
- Create: `frontend/src/views/Login.vue`
- Create: `frontend/src/api/auth.js`

- [ ] **Step 1: 创建 api/auth.js — 认证 API 调用**

`login(username, password)`, `getCurrentUser()`

- [ ] **Step 2: 创建 Login.vue**

居中登录框，用户名+密码表单，Element Plus 的 el-form 校验，调用登录 API，存储 token 和用户信息到 store，跳转工作台。

- [ ] **Step 3: 验证登录流程**

启动前后端，测试登录成功跳转、错误提示、token 存储。

- [ ] **Step 4: Commit**

---

### Task 10: 通用模糊搜索组件 + 地区选择器

**Files:**
- Create: `frontend/src/components/OrgSelector.vue`
- Create: `frontend/src/components/PlatformSelector.vue`
- Create: `frontend/src/components/ManagerSelector.vue`
- Create: `frontend/src/components/RegionCascader.vue`
- Create: `frontend/src/api/dict.js`
- Create: `frontend/src/utils/region-data.js`

- [ ] **Step 1: 创建 api/dict.js — 字典表 API**

`searchOrganizations(keyword)`, `createOrganization(data)`, 同理 platform 和 manager。

- [ ] **Step 2: 创建 OrgSelector.vue**

基于 el-select + el-option 的远程搜索组件。输入≥1字符触发搜索，下拉底部"+新增"按钮，弹窗快速新增后自动选中。支持 v-model。

- [ ] **Step 3: 创建 PlatformSelector.vue**

同 OrgSelector 模式。

- [ ] **Step 4: 创建 ManagerSelector.vue**

同 OrgSelector 模式，支持多选（项目负责人可多个）。

- [ ] **Step 5: 创建 RegionCascader.vue**

使用 el-cascader，加载中国行政区划三级数据（省/市/区）。数据内置于 `utils/region-data.js`（可从 npm 包 `china-division` 或静态 JSON 获取）。

- [ ] **Step 6: 验证组件交互**

在任意页面临时引入组件测试：模糊搜索、新增、选中、清空。

- [ ] **Step 7: Commit**

---

## Phase 3: 业务页面

### Task 11: 基础数据管理页面（单位库/平台/负责人/用户）

**Files:**
- Create: `frontend/src/views/admin/OrganizationList.vue`
- Create: `frontend/src/views/admin/PlatformList.vue`
- Create: `frontend/src/views/admin/ManagerList.vue`
- Create: `frontend/src/views/admin/UserList.vue`

- [ ] **Step 1: 创建 OrganizationList.vue**

表格展示 + 搜索框 + 新增/编辑弹窗。弹窗包含 name, short_name, contact_person, contact_phone, notes 字段。

- [ ] **Step 2: 创建 PlatformList.vue**

表格展示 + 新增/编辑弹窗。字段：name, url。

- [ ] **Step 3: 创建 ManagerList.vue**

表格展示 + 搜索 + 新增/编辑弹窗。字段：name, phone, company, notes。

- [ ] **Step 4: 创建 UserList.vue**

表格展示 + 新增/编辑弹窗。字段：username, display_name, role, phone, is_active。新增时设置密码。

- [ ] **Step 5: 验证四个管理页面的增删改查**

- [ ] **Step 6: Commit**

---

### Task 12: 项目信息页面（列表 + 详情）

**Files:**
- Create: `frontend/src/api/project.js`
- Create: `frontend/src/views/project/ProjectList.vue`
- Create: `frontend/src/views/project/ProjectDetail.vue`

- [ ] **Step 1: 创建 api/project.js**

`getProjects(params)`, `getProject(id)`, `createProject(data)`, `updateProject(id, data)`, `publishProject(id)`, `abandonProject(id, reason)`

- [ ] **Step 2: 创建 ProjectList.vue**

el-table 展示项目列表：项目名称、招标类型、招标单位、地区、负责人、状态、创建时间。支持搜索、状态筛选、分页。操作列：查看详情、删除。顶部"新增项目"按钮。

- [ ] **Step 3: 创建 ProjectDetail.vue**

el-form 表单：
- 招标类型 (el-select, 4个固定选项)
- 项目名称 (el-input)
- 招标单位 (OrgSelector)
- 所属地区 (RegionCascader)
- 项目负责人 (ManagerSelector, 多选)
- 项目描述 (el-input textarea)

底部流程按钮区：[放弃] [已发公告]
- 放弃：弹框输入原因，调用 abandon API
- 已发公告：调用 publish API，跳转到新创建的招标信息页面

- [ ] **Step 4: 验证项目页面完整流程**

新增项目 → 查看列表 → 编辑项目 → 点击"已发公告" → 跳转招标信息页。

- [ ] **Step 5: Commit**

---

### Task 13: 招标信息页面（列表 + 详情）

**Files:**
- Create: `frontend/src/api/bidding.js`
- Create: `frontend/src/views/bidding/BiddingList.vue`
- Create: `frontend/src/views/bidding/BiddingDetail.vue`

- [ ] **Step 1: 创建 api/bidding.js**

`getBiddings(params)`, `getBidding(id)`, `createBidding(data)`, `updateBidding(id, data)`, `prepareBid(id)`, `abandonBidding(id, reason)`

- [ ] **Step 2: 创建 BiddingList.vue**

表格展示：项目名称(关联)、代理单位、发布平台、报名截止、投标截止、预算金额、投标专员、状态。支持搜索筛选分页。

- [ ] **Step 3: 创建 BiddingDetail.vue**

el-form 表单：
- 关联项目信息（只读展示，从 project 带入）
- 代理单位 (OrgSelector)
- 发布平台 (PlatformSelector)
- 项目标签 (el-select 可输入新增 tag)
- 报名截止日期、投标截止日期 (el-date-picker)
- 预算类型 (el-radio) + 预算金额 (el-input-number)
- 是否入围标 (el-switch)
- 投标专员 (el-select, 数据源为系统用户列表)
- 招标文件上传 (el-upload)
- 备注

底部流程按钮：[放弃] [准备投标]

- [ ] **Step 4: 验证招标信息页面流程**

从项目详情点"已发公告"跳转过来 → 填写招标信息 → 点"准备投标" → 跳转投标信息页。

- [ ] **Step 5: Commit**

---

### Task 14: 投标信息页面（列表 + 详情）

**Files:**
- Create: `frontend/src/api/bid.js`
- Create: `frontend/src/views/bid/BidList.vue`
- Create: `frontend/src/views/bid/BidDetail.vue`

- [ ] **Step 1: 创建 api/bid.js**

`getBids(params)`, `getBid(id)`, `updateBid(id, data)`, `submitBid(id)`, `abandonBid(id, reason)`

- [ ] **Step 2: 创建 BidList.vue**

表格展示：项目名称(关联)、投标方式、投标状态、保证金状态、合作单位。支持搜索筛选分页。

- [ ] **Step 3: 创建 BidDetail.vue**

el-form 表单：
- 关联招标信息（只读展示）
- 合作单位 (OrgSelector, 多选)
- 投标方式 (el-select: 独立/联合体/配合/陪标)
- 投标状态 (el-select: 不投标/未报名/已报名)
- 保证金区域：是否有保证金 → 展开：金额、缴纳日期、状态
- 投标文件上传
- 备注

底部流程按钮：[放弃] [已投标]
- 点击"已投标"：自动将 bid_status 设为"已投标"，保证金如有自动变"未收回"，跳转投标结果页。

- [ ] **Step 4: 验证投标信息页面流程**

- [ ] **Step 5: Commit**

---

### Task 15: 投标结果页面（列表 + 详情）

**Files:**
- Create: `frontend/src/api/result.js`
- Create: `frontend/src/views/result/ResultList.vue`
- Create: `frontend/src/views/result/ResultDetail.vue`

- [ ] **Step 1: 创建 api/result.js**

`getResults(params)`, `getResult(id)`, `updateResult(id, data)`

- [ ] **Step 2: 创建 ResultList.vue**

表格展示：项目名称、我方报价、是否中标、合同状态、保证金状态。支持筛选分页。

- [ ] **Step 3: 创建 ResultDetail.vue**

el-form 表单：
- 关联投标信息（只读展示）
- 我方投标报价 (el-input-number)
- 参标单位及报价（动态表单行，每行：OrgSelector选择单位 + 金额输入）
- 评分情况（动态表单行，每行：单位 + 分数）
- 保证金状态（继承，el-select: 未收回/已收回）
- 是否中标 (el-radio)
- 未中标分析（条件显示，el-input textarea）
- 合同编号、合同金额（中标后填写）
- 合同状态 (el-select)
- 备注

保存后根据 is_won 自动更新项目状态为"已中标"或"未中标"。

- [ ] **Step 4: 验证投标结果页面完整流程**

- [ ] **Step 5: Commit**

---

## Phase 4: 分析与收尾

### Task 16: 工作台仪表盘

**Files:**
- Create: `frontend/src/api/stats.js`
- Create: `frontend/src/views/Dashboard.vue`

- [ ] **Step 1: 创建 api/stats.js**

`getOverview()`, `getWinRate(params)`, `getCompetitors(params)`, `getDeposits(params)`

- [ ] **Step 2: 创建 Dashboard.vue**

- 顶部：待办提醒卡片（本周截止投标、保证金未收回）
- 中部：4个状态统计卡片（跟进中/已发公告/准备投标/已投标的数量）
- 中部：本月中标概览（投标数、中标数、中标率）
- 底部：最近操作记录表格

- [ ] **Step 3: 验证仪表盘数据展示**

- [ ] **Step 4: Commit**

---

### Task 17: 数据分析页面

**Files:**
- Create: `frontend/src/views/stats/Statistics.vue`

- [ ] **Step 1: 创建 Statistics.vue**

4个 Tab 面板：
1. **中标率统计** — 时间维度选择器（月/季/年）+ ECharts 柱状图
2. **投标趋势** — ECharts 混合图（柱状+折线），投标数量和中标率趋势
3. **竞争对手分析** — 表格 + ECharts 对比图，显示参标单位次数和中标率
4. **保证金跟踪** — 表格汇总各状态，超期未收回高亮提醒

- [ ] **Step 2: 验证数据分析页面图表渲染**

- [ ] **Step 3: Commit**

---

### Task 18: 操作日志页面

**Files:**
- Create: `frontend/src/api/log.js`
- Create: `frontend/src/views/LogList.vue`

- [ ] **Step 1: 创建 api/log.js**

`getLogs(params)`

- [ ] **Step 2: 创建 LogList.vue**

表格展示：操作时间、操作人、操作类型、实体类型、详情。支持分页和时间范围筛选。

- [ ] **Step 3: Commit**

---

### Task 19: 前端 Vite 代理配置 + 集成验证

**Files:**
- Modify: `frontend/vite.config.js`

- [ ] **Step 1: 配置 Vite 代理**

在 vite.config.js 中配置 `/api` 请求代理到后端 `http://localhost:8000`。

- [ ] **Step 2: 端到端流程验证**

完整走通：登录 → 新增项目 → 已发公告 → 填写招标信息 → 准备投标 → 填写投标信息 → 已投标 → 填写投标结果 → 仪表盘查看统计 → 查看操作日志。

- [ ] **Step 3: Commit**

---

## 验证清单

- [ ] 后端所有 API 可通过 Swagger 文档正常测试
- [ ] 前端所有页面可正常访问和操作
- [ ] 完整流程可走通（项目→招标→投标→结果）
- [ ] 流程按钮正确驱动状态流转
- [ ] 模糊搜索组件可搜索+新增+复用
- [ ] 仪表盘数据与实际数据一致
- [ ] 操作日志记录完整
