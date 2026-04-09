# 招标信息收集和投标信息管理系统 — 设计文档

## 1. 项目概述

为经营中心团队（<5人）设计一套内部使用的招标信息收集和投标信息管理系统。系统覆盖从项目发现、招标公告、投标执行到结果跟踪的完整业务流程。

### 1.1 核心业务流程

```
项目信息（未发招标公告）→ 招标信息（已发公告）→ 投标信息 → 投标结果
```

每个阶段由流程按钮驱动，点击后自动创建下一阶段记录并跳转，项目状态自动更新。

### 1.2 技术选型

| 层 | 技术 | 说明 |
|----|------|------|
| 前端 | Vue 3 + Element Plus + Vite | 企业级UI组件库，国内生态成熟 |
| 后端 | FastAPI + SQLAlchemy | 现代Python框架，自带API文档 |
| 数据库 | SQLite | 轻量级文件数据库，内网部署无需额外服务 |
| 图表 | ECharts | 中文文档齐全，图表丰富 |
| 认证 | JWT Token | 无状态认证，简单有效 |
| 部署 | 内网服务器 | 局域网访问，数据安全可控 |

### 1.3 项目结构

```
经营中心信息管理/
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI 入口
│   │   ├── core/
│   │   │   ├── config.py     # 配置
│   │   │   ├── security.py   # JWT认证
│   │   │   └── database.py   # 数据库连接
│   │   ├── models/           # SQLAlchemy 数据模型
│   │   │   ├── user.py
│   │   │   ├── organization.py
│   │   │   ├── platform.py
│   │   │   ├── manager.py
│   │   │   ├── project.py
│   │   │   ├── bidding_info.py
│   │   │   ├── bid_info.py
│   │   │   ├── bid_result.py
│   │   │   └── operation_log.py
│   │   ├── schemas/          # Pydantic 数据校验
│   │   ├── api/              # API 路由
│   │   │   ├── auth.py
│   │   │   ├── projects.py
│   │   │   ├── bidding_infos.py
│   │   │   ├── bid_infos.py
│   │   │   ├── bid_results.py
│   │   │   ├── organizations.py
│   │   │   ├── platforms.py
│   │   │   ├── managers.py
│   │   │   ├── users.py
│   │   │   ├── stats.py
│   │   │   └── logs.py
│   │   └── services/         # 业务逻辑
│   ├── uploads/              # 上传文件目录
│   ├── data/                 # SQLite 数据库文件
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── views/            # 页面组件
│   │   │   ├── Login.vue
│   │   │   ├── Dashboard.vue
│   │   │   ├── project/
│   │   │   │   ├── ProjectList.vue
│   │   │   │   ├── ProjectDetail.vue
│   │   │   │   └── ProjectInfoList.vue
│   │   │   ├── bidding/
│   │   │   │   ├── BiddingList.vue
│   │   │   │   └── BiddingDetail.vue
│   │   │   ├── bid/
│   │   │   │   ├── BidList.vue
│   │   │   │   └── BidDetail.vue
│   │   │   ├── result/
│   │   │   │   ├── ResultList.vue
│   │   │   │   └── ResultDetail.vue
│   │   │   ├── stats/
│   │   │   │   └── Statistics.vue
│   │   │   └── admin/
│   │   │       ├── OrganizationList.vue
│   │   │       ├── PlatformList.vue
│   │   │       ├── ManagerList.vue
│   │   │       └── UserList.vue
│   │   ├── components/       # 通用组件
│   │   │   ├── Layout.vue
│   │   │   ├── OrgSelector.vue      # 单位模糊搜索选择器
│   │   │   ├── PlatformSelector.vue # 平台模糊搜索选择器
│   │   │   ├── ManagerSelector.vue  # 负责人模糊搜索选择器
│   │   │   └── RegionCascader.vue   # 地区级联选择器
│   │   ├── api/              # Axios API 调用
│   │   ├── stores/           # Pinia 状态管理
│   │   ├── router/           # Vue Router
│   │   └── utils/            # 工具函数
│   └── package.json
└── docs/
    └── superpowers/
        └── specs/
```

## 2. 数据模型

### 2.1 字典表（可复用实体）

#### 2.1.1 单位库 (Organization)

招标单位、代理单位、合作单位、参标单位共用此表。

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer PK | 自增ID |
| name | String(200) UNIQUE | 单位全称 |
| short_name | String(100) | 简称（搜索用） |
| contact_person | String(50) | 联系人 |
| contact_phone | String(20) | 联系电话 |
| notes | Text | 备注 |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

#### 2.1.2 发布平台库 (Platform)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer PK | 自增ID |
| name | String(200) UNIQUE | 平台名称 |
| url | String(500) | 平台网址 |
| created_at | DateTime | 创建时间 |

#### 2.1.3 项目负责人库 (Manager)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer PK | 自增ID |
| name | String(50) UNIQUE | 姓名 |
| phone | String(20) | 联系电话 |
| company | String(200) | 所属单位 |
| notes | Text | 备注 |
| created_at | DateTime | 创建时间 |

### 2.2 核心业务表

#### 2.2.1 用户 (User)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer PK | 自增ID |
| username | String(50) UNIQUE | 登录用户名 |
| password_hash | String(200) | 密码哈希（bcrypt） |
| display_name | String(50) | 显示名称 |
| role | Enum | admin / user |
| phone | String(20) | 联系电话 |
| is_active | Boolean | 是否启用 |
| created_at | DateTime | 创建时间 |

#### 2.2.2 项目信息 (ProjectInfo) — 未发招标公告阶段

统一项目状态在此表上跟踪。

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer PK | 自增ID |
| bidding_type | Enum | 招标类型：公开招标/邀请招标/中介超市/入围分项 |
| project_name | String(300) | 项目名称 |
| bidding_unit_id | Integer FK → Organization | 招标单位（甲方） |
| region | String(100) | 所属地区（省/市/区，JSON格式） |
| manager_ids | JSON | 项目负责人ID数组，关联 Manager |
| status | Enum | 状态：跟进中/已发公告/准备投标/已投标/已中标/未中标/已放弃 |
| description | Text | 项目简要描述 |
| created_by | Integer FK → User | 创建人 |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

#### 2.2.3 招标信息 (BiddingInfo) — 已发招标公告

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer PK | 自增ID |
| project_id | Integer FK → ProjectInfo UNIQUE | 关联项目信息（一对一） |
| agency_id | Integer FK → Organization | 代理单位（招标代理机构） |
| publish_platform_id | Integer FK → Platform | 发布平台 |
| tags | JSON | 项目标签数组（如 ["信息化","安防"]） |
| registration_deadline | Date | 报名截止日期 |
| bid_deadline | Date | 投标截止日期 |
| budget_amount | Decimal(15,2) | 预算金额 |
| control_price_type | Enum | 招标控制价类型：金额/折扣率/下浮率 |
| control_price_upper | Decimal(15,2) | 控制价上限（nullable） |
| control_price_lower | Decimal(15,2) | 控制价下限（nullable） |
| is_prequalification | Boolean | 是否入围标 |
| bid_specialist_id | Integer FK → User | 投标专员（系统用户，主要录入人和流程推进者） |
| bid_documents | JSON | 招标文件附件路径数组 |
| notes | Text | 备注 |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

#### 2.2.4 投标信息 (BidInfo) — 投标执行

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer PK | 自增ID |
| bidding_info_id | Integer FK → BiddingInfo UNIQUE | 关联招标信息（一对一） |
| partner_ids | JSON | 合作单位ID数组，关联 Organization |
| bid_method | Enum | 投标方式：独立/联合体/配合/陪标 |
| bid_status | Enum | 阶段内状态：不投标/未报名/已报名/已投标（点击"已投标"流程按钮时自动设为"已投标"并创建投标结果） |
| has_deposit | Boolean | 是否有投标保证金 |
| deposit_status | Enum | 保证金状态：无/未缴纳/已缴纳/未收回/已收回 |
| deposit_amount | Decimal(15,2) | 保证金金额 |
| deposit_date | Date | 缴纳日期 |
| deposit_return_date | Date | 退回日期 |
| bid_files | JSON | 投标文件附件路径数组 |
| our_price | Decimal(15,2) | 我方投标报价（default=0） |
| notes | Text | 备注 |
| created_by | Integer FK → User | 创建人 |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

投标状态与流程按钮关系：
- `bid_status` 记录阶段内的报名进度（不投标/未报名/已报名）
- 点击"已投标"流程按钮时：自动将 `bid_status` 置为"已投标"，同时创建投标结果记录，推进项目状态
- `bid_status` 不与项目全局状态冲突，它是阶段内的细节跟踪

保证金状态流转规则：
- has_deposit=false → deposit_status=无
- has_deposit=true → 未缴纳 → 已缴纳 → 投标后自动变"未收回" → 已收回

#### 2.2.5 投标结果 (BidResult) — 开标结果

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer PK | 自增ID |
| bid_info_id | Integer FK → BidInfo UNIQUE | 关联投标信息（一对一） |
| competitors | JSON | 参标单位及报价，格式：`[{"org_id": 1, "price": 100000}]` |
| scoring_details | JSON | 评分情况（如有），格式：`[{"org_id": 1, "score": 85.5}]` |
| deposit_status | Enum | 保证金状态（继承）：未收回/已收回 |
| is_won | Boolean | 是否中标 |
| winning_org_id | Integer FK → Organization (nullable) | 中标单位ID |
| winning_price | Decimal(15,2) (nullable) | 中标价格 |
| lost_analysis | Text | 未中标分析（is_won=false时填写） |
| contract_number | String(100) | 合同编号（中标后填写） |
| contract_status | Enum | 合同状态：无/未签订/已签订未收回/已签订已收回 |
| contract_amount | Decimal(15,2) | 合同金额 |
| notes | Text | 备注 |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

#### 2.2.6 操作日志 (OperationLog)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer PK | 自增ID |
| user_id | Integer FK → User | 操作用户 |
| action | String(50) | 操作类型（create/update/delete/advance/abandon） |
| entity_type | String(50) | 实体类型（project/bidding_info/bid_info/bid_result） |
| entity_id | Integer | 实体ID |
| detail | Text | 操作详情（JSON格式记录变更内容） |
| created_at | DateTime | 操作时间 |

### 2.3 实体关系

```
Organization ←─── bidding_unit_id ─── ProjectInfo
       ↑                                  │
       │                          project_id (1:1)
       │                                  ↓
       ├─── agency_id ──────────── BiddingInfo
       │                                  │
       │                       bidding_info_id (1:1)
       │                                  ↓
       └─── partner_ids ──────────── BidInfo
                                          │
                              bid_info_id (1:1)
                                          ↓
                                    BidResult ──── competitors (org_ids)
                                               ──── winning_org_id → Organization

Platform ←─── publish_platform_id ─── BiddingInfo
Manager  ←─── manager_ids ─────────── ProjectInfo
User     ←─── bid_specialist_id ───── BiddingInfo
         ←─── created_by ──────────── ProjectInfo, BidInfo
```

## 3. 流程设计

### 3.1 状态流转（流程按钮驱动）

```
┌──────────┐  [已发公告]  ┌──────────┐  [准备投标]  ┌──────────┐  [已投标]  ┌──────────┐
│ 项目信息  │ ──────────→ │ 招标信息  │ ──────────→ │ 投标信息  │ ────────→ │ 投标结果  │
│          │             │          │             │          │           │          │
│ status:  │             │ status:  │             │ status:  │           │ status:  │
│ 跟进中   │             │ 已发公告  │             │ 准备投标  │           │ 已投标   │
└──────────┘             └──────────┘             └──────────┘           └──────────┘
     │                        │                        │
     │ [放弃]                 │ [放弃]                 │ [放弃]
     ↓                        ↓                        ↓
  已放弃                    已放弃                    已放弃
```

**流程按钮行为：**
- 点击"放弃"：弹出确认框，填写放弃原因，项目状态更新为"已放弃"
- 点击流程推进按钮：自动创建下一阶段记录，项目状态自动更新，页面跳转到下一阶段

**投标结果阶段完成后：**
- is_won=true → 状态更新为"已中标"
- is_won=false → 状态更新为"未中标"

### 3.2 项目完整状态枚举

```
跟进中 → 已发公告 → 准备投标 → 已投标 → 已中标
                                         → 未中标
任意阶段 → 已放弃
```

## 4. 页面与功能设计

### 4.1 页面结构

```
├── /login                    登录页
├── /dashboard                工作台（首页仪表盘）
├── /projects                 项目管理
│   ├── /projects             项目列表
│   └── /projects/:id         项目详情（含流程按钮）
├── /project-info             项目信息（跟进中项目快速查看）
├── /biddings                 招标信息
│   ├── /biddings             招标列表
│   └── /biddings/:id         招标详情（含流程按钮）
├── /bids                     投标信息
│   ├── /bids                 投标列表
│   └── /bids/:id             投标详情（含流程按钮）
├── /results                  投标结果
│   ├── /results              结果列表
│   └── /results/:id          结果详情
├── /stats                    数据分析
├── /admin                    基础数据管理
│   ├── /admin/organizations  单位库
│   ├── /admin/platforms      平台管理
│   ├── /admin/managers       负责人管理
│   └── /admin/users          用户管理
└── /logs                     操作日志
```

### 4.2 列表页通用功能

- **搜索**：项目名称/招标单位关键字搜索
- **筛选**：按状态/地区/时间范围/招标类型筛选
- **排序**：按截止时间/创建时间/金额排序
- **分页**：每页20条，支持跳页
- **导出**：Excel导出当前筛选结果

### 4.3 模糊搜索控件（OrgSelector / PlatformSelector / ManagerSelector）

用于单位库、平台库、负责人库的选择。

交互流程：
1. 用户输入 ≥1 个字符触发搜索
2. 下拉列表显示匹配项（显示名称+附加信息）
3. 点击选中已有记录
4. 下拉底部显示"+ 新增"按钮
5. 点击"+ 新增"弹出快速新增对话框（仅必填字段）
6. 新增成功后自动选中新记录并关闭下拉
7. 已选中的值显示为标签，支持清空

### 4.4 地区级联选择器（RegionCascader）

使用 Element Plus Cascader 组件，省/市/区三级联动。数据为前端内置的中国行政区划JSON数据。存储格式为 `[ province, city, district ]` 文本数组。

### 4.5 首页仪表盘

- **待办提醒**：本周截止投标的项目、保证金未收回的记录
- **项目统计卡片**：各状态项目数量（跟进中/已发公告/准备投标/已投标）
- **中标概览**：本月投标数、中标数、中标率
- **最近活动**：最近操作记录摘要

### 4.6 数据分析页面

1. **中标率统计**：按月/季度/年维度，支持按招标类型、地区、项目负责人筛选
2. **投标趋势图**：柱状图+折线图，展示投标数量和中标率趋势
3. **竞争对手分析**：频繁遇到的参标单位、其中标率对比
4. **保证金跟踪**：各状态汇总，超期未收回提醒

## 5. 后端 API 设计

### 5.1 认证

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/auth/login | 登录，返回JWT |
| POST | /api/auth/logout | 登出 |
| GET | /api/auth/me | 获取当前用户信息 |

### 5.2 核心业务 CRUD

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/projects | 项目列表（分页、筛选、搜索，支持 `status` 过滤） |
| POST | /api/projects | 创建项目 |
| GET | /api/projects/{id} | 项目详情（含关联的 BiddingInfo + BidInfo + BidResult） |
| PUT | /api/projects/{id} | 更新项目 |
| DELETE | /api/projects/{id} | 删除项目（级联删除关联的 BidResult/BidInfo/BiddingInfo） |
| GET | /api/biddings | 招标信息列表（支持 `status` 过滤） |
| POST | /api/biddings | 创建招标信息 |
| GET | /api/biddings/{id} | 招标信息详情 |
| PUT | /api/biddings/{id} | 更新招标信息 |
| GET | /api/bids | 投标信息列表（支持 `status` 过滤） |
| POST | /api/bids | 创建投标信息 |
| GET | /api/bids/{id} | 投标信息详情 |
| PUT | /api/bids/{id} | 更新投标信息 |
| GET | /api/results | 投标结果列表 |
| POST | /api/results | 创建投标结果 |
| GET | /api/results/{id} | 投标结果详情 |
| PUT | /api/results/{id} | 更新投标结果 |

### 5.3 流程操作

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/projects/{id}/publish | 项目→招标信息（已发公告） |
| POST | /api/projects/{id}/abandon | 项目放弃 |
| POST | /api/biddings/{id}/prepare | 招标→投标信息（准备投标） |
| POST | /api/biddings/{id}/abandon | 招标放弃 |
| POST | /api/bids/{id}/submit | 投标→投标结果（已投标） |
| POST | /api/bids/{id}/abandon | 投标放弃 |

### 5.4 字典表

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/organizations | 单位列表（支持搜索） |
| POST | /api/organizations | 新增单位 |
| PUT | /api/organizations/{id} | 更新单位 |
| DELETE | /api/organizations/{id} | 删除单位 |
| GET | /api/platforms | 平台列表 |
| POST | /api/platforms | 新增平台 |
| PUT | /api/platforms/{id} | 更新平台 |
| DELETE | /api/platforms/{id} | 删除平台 |
| GET | /api/managers | 负责人列表 |
| POST | /api/managers | 新增负责人 |
| PUT | /api/managers/{id} | 更新负责人 |
| DELETE | /api/managers/{id} | 删除负责人 |

### 5.5 统计与系统

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/stats/overview | 仪表盘概览数据 |
| GET | /api/stats/win-rate | 中标率统计 |
| GET | /api/stats/competitors | 竞争对手分析 |
| GET | /api/stats/deposits | 保证金跟踪 |
| GET | /api/users | 用户列表 |
| POST | /api/users | 新增用户 |
| PUT | /api/users/{id} | 更新用户 |
| GET | /api/logs | 操作日志（分页） |

## 6. 技术细节

### 6.1 前端

- **UI框架**：Element Plus
- **状态管理**：Pinia
- **HTTP客户端**：Axios（带JWT拦截器）
- **路由**：Vue Router 4（路由守卫鉴权）
- **图表**：ECharts 5
- **导出**：SheetJS（xlsx）
- **地区数据**：前端内置中国行政区划三级数据

### 6.2 后端

- **框架**：FastAPI + Uvicorn
- **ORM**：SQLAlchemy 2.0（同步模式）
- **数据校验**：Pydantic v2
- **认证**：python-jose（JWT）+ passlib（bcrypt）
- **文件上传**：上传至 backend/uploads/ 目录
- **CORS**：允许前端开发服务器跨域

### 6.4 数据库迁移

`backend/migrate_db.py` 是数据库迁移脚本，用于处理数据模型变更。当前版本执行以下操作：

1. 在 `bid_infos` 表添加 `our_price` 列（从 `bid_results` 移过来）
2. 在 `bid_results` 表添加 `winning_org_id` 和 `winning_price` 列
3. 将已有 `bid_results.our_price` 数据复制到 `bid_infos.our_price`
4. 尝试删除 `bid_results.our_price` 旧列（需 SQLite 3.35+）

脚本幂等设计：会先检查列是否存在再执行 ALTER TABLE，可安全重复运行。

**使用方式**：拉取代码后，在启动服务器之前运行 `python backend/migrate_db.py`。

### 6.3 部署

- 内网服务器部署
- 前端构建后由后端静态文件服务或 Nginx 代理
- SQLite 数据库文件存放在 backend/data/ 目录
- 附件上传至 backend/uploads/ 目录

## 7. 数据默认值

系统初始化时创建：
- 一个管理员账号（admin/admin123，首次登录提示修改密码）
- SQLite 数据库文件自动创建
- 必要的数据库表自动迁移
