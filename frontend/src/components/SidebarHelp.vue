<template>
  <!-- 底部触发条 -->
  <div class="help-trigger" @click="drawerVisible = true">
    <el-icon><QuestionFilled /></el-icon>
    <span>使用帮助</span>
    <el-icon style="margin-left: auto"><ArrowRight /></el-icon>
  </div>

  <!-- 右侧抽屉 -->
  <el-drawer
    v-model="drawerVisible"
    title="使用手册"
    direction="rtl"
    size="520px"
    :append-to-body="true"
  >
    <el-collapse v-model="activeSections" class="help-collapse">
      <!-- ==================== 一、系统概述 ==================== -->
      <el-collapse-item title="一、系统概述" name="overview">
        <div class="help-content">
          <p>本系统用于管理公司招标信息，涵盖从项目发现、跟进、投标到中标结果录入的全生命周期管理。</p>

          <h4>界面布局</h4>
          <!-- 界面布局模拟图 -->
          <div class="mock-layout">
            <div class="mock-sidebar">
              <div class="mock-sidebar-title">招标管理系统</div>
              <div class="mock-menu-item active"><span class="mock-dot blue"></span>工作台</div>
              <div class="mock-menu-item"><span class="mock-dot blue"></span>项目管理</div>
              <div class="mock-menu-item"><span class="mock-dot blue"></span>数据分析</div>
              <div class="mock-menu-item"><span class="mock-dot blue"></span>基础数据 ▾</div>
              <div class="mock-menu-item"><span class="mock-dot blue"></span>操作日志</div>
              <div class="mock-help-badge">? 使用帮助</div>
            </div>
            <div class="mock-main">
              <div class="mock-header">
                <span>页面标题</span>
                <span class="mock-user">用户名 [退出]</span>
              </div>
              <div class="mock-body">
                <p style="text-align:center;color:#999;margin-top:40px">主内容工作区</p>
              </div>
            </div>
          </div>
          <div class="layout-legend">
            <span class="legend-item"><span class="legend-dot" style="background:#304156"></span>左侧导航栏 — 切换功能模块</span>
            <span class="legend-item"><span class="legend-dot" style="background:#fff;border:1px solid #ddd"></span>顶部标题栏 — 显示页面名称</span>
            <span class="legend-item"><span class="legend-dot" style="background:#f0f2f5"></span>右侧内容区 — 主要操作区域</span>
          </div>

          <h4>导航菜单说明</h4>
          <table class="help-table">
            <thead><tr><th>菜单项</th><th>功能说明</th></tr></thead>
            <tbody>
              <tr><td><span class="mock-tag primary">工作台</span></td><td>数据概览、待办提醒、保证金未收回提醒</td></tr>
              <tr><td><span class="mock-tag primary">项目管理</span></td><td>项目列表、搜索筛选、创建新项目、查看详情</td></tr>
              <tr><td><span class="mock-tag primary">数据分析</span></td><td>中标率统计、投标趋势、竞争对手分析、保证金跟踪</td></tr>
              <tr><td><span class="mock-tag info">基础数据</span></td><td>单位库、平台、负责人、用户的增删改查</td></tr>
              <tr><td><span class="mock-tag info">操作日志</span></td><td>系统操作记录查询与追溯</td></tr>
            </tbody>
          </table>
        </div>
      </el-collapse-item>

      <!-- ==================== 二、核心业务流程 ==================== -->
      <el-collapse-item title="二、核心业务流程" name="flow">
        <div class="help-content">
          <h4>项目全生命周期</h4>
          <!-- SVG 状态流转图 -->
          <div class="flow-svg-wrap">
            <svg viewBox="0 0 460 260" xmlns="http://www.w3.org/2000/svg" class="flow-svg">
              <!-- 主线 -->
              <defs>
                <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                  <path d="M 0 0 L 10 5 L 0 10 z" fill="#c0c4cc"/>
                </marker>
                <marker id="arrow-red" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                  <path d="M 0 0 L 10 5 L 0 10 z" fill="#f56c6c"/>
                </marker>
              </defs>
              <!-- Row 1: 跟进中 → 已发公告 → 已报名/未报名 -->
              <circle cx="60" cy="50" r="30" fill="#909399" opacity="0.15" stroke="#909399" stroke-width="2"/>
              <text x="60" y="54" text-anchor="middle" fill="#909399" font-size="12" font-weight="bold">跟进中</text>
              <line x1="92" y1="50" x2="138" y2="50" stroke="#c0c4cc" stroke-width="2" marker-end="url(#arrow)"/>
              <circle cx="170" cy="50" r="30" fill="#409eff" opacity="0.15" stroke="#409eff" stroke-width="2"/>
              <text x="170" y="54" text-anchor="middle" fill="#409eff" font-size="11" font-weight="bold">已发公告</text>
              <line x1="202" y1="50" x2="248" y2="50" stroke="#c0c4cc" stroke-width="2" marker-end="url(#arrow)"/>
              <circle cx="280" cy="50" r="30" fill="#409eff" opacity="0.15" stroke="#409eff" stroke-width="2"/>
              <text x="280" y="54" text-anchor="middle" fill="#409eff" font-size="11" font-weight="bold">已报名</text>
              <line x1="312" y1="50" x2="358" y2="50" stroke="#c0c4cc" stroke-width="2" marker-end="url(#arrow)"/>

              <!-- Row 1 right: 准备投标 -->
              <circle cx="390" cy="50" r="30" fill="#e6a23c" opacity="0.15" stroke="#e6a23c" stroke-width="2"/>
              <text x="390" y="54" text-anchor="middle" fill="#e6a23c" font-size="10" font-weight="bold">准备投标</text>

              <!-- Arrow down from 准备投标 to 已投标 -->
              <line x1="390" y1="82" x2="390" y2="118" stroke="#c0c4cc" stroke-width="2" marker-end="url(#arrow)"/>

              <!-- Row 2: 已投标 center, with branches -->
              <circle cx="390" cy="150" r="30" fill="#67c23a" opacity="0.15" stroke="#67c23a" stroke-width="2"/>
              <text x="390" y="154" text-anchor="middle" fill="#67c23a" font-size="12" font-weight="bold">已投标</text>

              <!-- Arrow down-left to 已中标 -->
              <line x1="365" y1="172" x2="200" y2="218" stroke="#c0c4cc" stroke-width="2" marker-end="url(#arrow)"/>
              <!-- Arrow down to 已流标 -->
              <line x1="390" y1="182" x2="390" y2="218" stroke="#c0c4cc" stroke-width="2" marker-end="url(#arrow)"/>
              <!-- Arrow down-right to 未中标 -->
              <line x1="415" y1="172" x2="400" y2="218" stroke="none"/>

              <!-- Branch: 已中标 -->
              <circle cx="170" cy="230" r="26" fill="#67c23a" opacity="0.15" stroke="#67c23a" stroke-width="2"/>
              <text x="170" y="234" text-anchor="middle" fill="#67c23a" font-size="11" font-weight="bold">已中标</text>

              <!-- Branch: 已流标 -->
              <circle cx="390" cy="230" r="26" fill="#e6a23c" opacity="0.15" stroke="#e6a23c" stroke-width="2"/>
              <text x="390" y="234" text-anchor="middle" fill="#e6a23c" font-size="11" font-weight="bold">已流标</text>

              <!-- Branch: 未中标 -->
              <circle cx="60" cy="230" r="26" fill="#f56c6c" opacity="0.15" stroke="#f56c6c" stroke-width="2"/>
              <text x="60" y="234" text-anchor="middle" fill="#f56c6c" font-size="11" font-weight="bold">未中标</text>

              <!-- 已放弃 (dashed) -->
              <rect x="430" y="140" width="50" height="24" rx="12" fill="#f56c6c" opacity="0.1" stroke="#f56c6c" stroke-width="1.5" stroke-dasharray="4 2"/>
              <text x="455" y="156" text-anchor="middle" fill="#f56c6c" font-size="9">已放弃</text>
              <line x1="420" y1="152" x2="428" y2="152" stroke="#f56c6c" stroke-width="1.5" stroke-dasharray="4 2" marker-end="url(#arrow-red)"/>
              <text x="445" y="178" text-anchor="middle" fill="#f56c6c" font-size="8" opacity="0.7">任何阶段可放弃</text>

              <!-- 中标/流标 arrows from 已投标 -->
              <line x1="370" y1="178" x2="190" y2="210" stroke="#c0c4cc" stroke-width="2" marker-end="url(#arrow)"/>
              <line x1="390" y1="182" x2="390" y2="202" stroke="#c0c4cc" stroke-width="2" marker-end="url(#arrow)"/>
              <line x1="370" y1="178" x2="80" y2="212" stroke="#c0c4cc" stroke-width="2" marker-end="url(#arrow)"/>
            </svg>
          </div>

          <h4>分步操作示例</h4>
          <p class="example-intro">以"杭州市环境检测服务项目"为例，展示完整操作流程：</p>

          <div class="step-list">
            <div class="step-item">
              <div class="step-num" style="background:#909399">1</div>
              <div class="step-body">
                <div class="step-title">创建项目</div>
                <div class="step-desc">
                  进入「项目管理」→ 点击「新增项目」<br/>
                  填写招标类型：<span class="mock-tag primary">公开招标</span><br/>
                  填写项目名称：<code>杭州市环境检测服务项目</code><br/>
                  选择招标单位、经办人 → 点击「创建项目」
                </div>
              </div>
            </div>
            <div class="step-item">
              <div class="step-num" style="background:#409eff">2</div>
              <div class="step-body">
                <div class="step-title">发布公告</div>
                <div class="step-desc">
                  在项目详情页点击底部「已发公告」按钮 → 状态变为 <span class="mock-tag primary">已发公告</span><br/>
                  此时「招标信息」卡片出现，补充发布平台、预算金额、控制价、报名截止日期等信息
                </div>
              </div>
            </div>
            <div class="step-item">
              <div class="step-num" style="background:#409eff">3</div>
              <div class="step-body">
                <div class="step-title">确认报名</div>
                <div class="step-desc">
                  填写报名截止日期后，勾选「已报名」复选框<br/>
                  状态自动变为 <span class="mock-tag primary">已报名</span>
                </div>
              </div>
            </div>
            <div class="step-item">
              <div class="step-num" style="background:#e6a23c">4</div>
              <div class="step-body">
                <div class="step-title">准备投标</div>
                <div class="step-desc">
                  点击底部「准备投标」按钮<br/>
                  填写投标方式（独立/联合体/配合/陪标）、合作单位、保证金信息等<br/>
                  状态变为 <span class="mock-tag warning">准备投标</span>
                </div>
              </div>
            </div>
            <div class="step-item">
              <div class="step-num" style="background:#67c23a">5</div>
              <div class="step-body">
                <div class="step-title">提交投标</div>
                <div class="step-desc">
                  填写我方报价后，点击底部「提交投标」按钮<br/>
                  状态变为 <span class="mock-tag success">已投标</span>
                </div>
              </div>
            </div>
            <div class="step-item">
              <div class="step-num" style="background:#67c23a">6</div>
              <div class="step-body">
                <div class="step-title">录入投标结果</div>
                <div class="step-desc">
                  在投标结果卡片添加参标单位，录入各方报价<br/>
                  勾选中标单位 → 状态自动变为 <span class="mock-tag success">已中标</span><br/>
                  或标记流标 → 状态变为 <span class="mock-tag warning">已流标</span>
                </div>
              </div>
            </div>
          </div>

          <h4>项目详情页展开规则</h4>
          <p>项目详情采用田字布局，卡片按状态逐步显示：</p>
          <div class="mock-detail-grid">
            <div class="mock-grid-cell always">
              <span class="cell-label">项目基本信息</span>
              <span class="cell-status">始终显示</span>
            </div>
            <div class="mock-grid-cell from-published">
              <span class="cell-label">招标信息</span>
              <span class="cell-status">已发公告起</span>
            </div>
            <div class="mock-grid-cell from-preparing">
              <span class="cell-label">投标信息</span>
              <span class="cell-status">准备投标起</span>
            </div>
            <div class="mock-grid-cell from-submitted">
              <span class="cell-label">投标结果</span>
              <span class="cell-status">已投标起</span>
            </div>
          </div>
        </div>
      </el-collapse-item>

      <!-- ==================== 三、各模块使用说明 ==================== -->
      <el-collapse-item title="三、各模块使用说明" name="modules">
        <div class="help-content">
          <h4>3.1 工作台</h4>
          <p>登录后默认进入工作台，展示关键业务数据：</p>
          <!-- 模拟工作台统计卡片 -->
          <div class="mock-dashboard">
            <div class="mock-stat-card">
              <div class="stat-num" style="color:#909399">5</div>
              <div class="stat-label">跟进中</div>
            </div>
            <div class="mock-stat-card">
              <div class="stat-num" style="color:#e6a23c">3</div>
              <div class="stat-label">准备投标</div>
            </div>
            <div class="mock-stat-card">
              <div class="stat-num" style="color:#67c23a">12</div>
              <div class="stat-label">已投标</div>
            </div>
            <div class="mock-stat-card">
              <div class="stat-num" style="color:#67c23a">8</div>
              <div class="stat-label">已中标</div>
            </div>
          </div>
          <ul>
            <li><strong>待办提醒</strong>：本周截止投标的项目列表，点击可跳转详情</li>
            <li><strong>保证金提醒</strong>：未收回保证金列表，标注超期天数</li>
            <li><strong>统计卡片</strong>：各状态项目数量一览</li>
          </ul>

          <h4>3.2 项目管理</h4>
          <p>核心功能模块，管理所有招标项目：</p>
          <!-- 模拟筛选按钮 -->
          <div class="mock-filter-bar">
            <span class="mock-btn active">全部</span>
            <span class="mock-btn">跟进中</span>
            <span class="mock-btn" style="border-color:#67c23a;color:#67c23a">已中标</span>
            <span class="mock-btn" style="border-color:#f56c6c;color:#f56c6c">未中标</span>
            <span class="mock-btn" style="border-color:#e6a23c;color:#e6a23c">已流标</span>
          </div>
          <!-- 模拟表格 -->
          <div class="mock-table">
            <div class="mock-table-header">
              <span class="col-name">项目名称</span>
              <span class="col-type">招标类型</span>
              <span class="col-status">状态</span>
              <span class="col-region">地区</span>
            </div>
            <div class="mock-table-row">
              <span class="col-name">杭州市环境检测服务项目</span>
              <span class="col-type">公开招标</span>
              <span class="col-status"><span class="mock-tag success">已中标</span></span>
              <span class="col-region">浙江省杭州市</span>
            </div>
            <div class="mock-table-row alt">
              <span class="col-name">温州市水质监测项目</span>
              <span class="col-type">邀请招标</span>
              <span class="col-status"><span class="mock-tag warning">准备投标</span></span>
              <span class="col-region">浙江省温州市</span>
            </div>
          </div>
          <ul>
            <li><strong>快捷筛选</strong>：点击状态按钮快速过滤项目</li>
            <li><strong>搜索</strong>：输入项目名称关键词搜索</li>
            <li><strong>列设置</strong>：点击「列设置」按钮自定义显示列，配置按状态独立记忆</li>
            <li><strong>新增项目</strong>：点击右上角「新增项目」创建新项目</li>
          </ul>

          <h4>3.3 数据分析</h4>
          <p>提供四个维度的数据分析（标签页切换）：</p>
          <!-- 模拟标签页 -->
          <div class="mock-tabs">
            <div class="mock-tab active">中标率统计</div>
            <div class="mock-tab">投标趋势</div>
            <div class="mock-tab">竞争对手分析</div>
            <div class="mock-tab">保证金跟踪</div>
          </div>
          <ul>
            <li><strong>中标率统计</strong>：按月/季/年查看中标率，支持图表可视化</li>
            <li><strong>投标趋势</strong>：投标数量与中标率走势</li>
            <li><strong>竞争对手分析</strong>：遭遇次数、对方中标率对比</li>
            <li><strong>保证金跟踪</strong>：保证金状态、超期天数，红色高亮超期项</li>
          </ul>

          <h4>3.4 基础数据</h4>
          <p>在「基础数据」子菜单中管理系统参考信息：</p>
          <table class="help-table">
            <thead><tr><th>子模块</th><th>功能</th><th>使用场景</th></tr></thead>
            <tbody>
              <tr><td>单位库管理</td><td>维护投标相关单位信息</td><td>招标单位、代理机构、合作方、竞争对手</td></tr>
              <tr><td>平台管理</td><td>维护招标发布平台</td><td>发布招标公告时选择平台</td></tr>
              <tr><td>负责人管理</td><td>维护项目负责人信息</td><td>创建项目时选择经办人</td></tr>
              <tr><td>用户管理</td><td>管理系统用户账号</td><td>新增用户、设置角色、启用/禁用</td></tr>
            </tbody>
          </table>

          <h4>3.5 操作日志</h4>
          <p>记录所有关键操作（创建、更新、删除、状态流转等），支持按以下条件筛选：</p>
          <ul>
            <li>实体类型（项目、招标信息、投标信息、投标结果）</li>
            <li>操作类型（创建、更新、删除、发布、放弃）</li>
            <li>时间范围</li>
          </ul>
        </div>
      </el-collapse-item>

      <!-- ==================== 四、投标方式详解 ==================== -->
      <el-collapse-item title="四、投标方式详解" name="bid-method">
        <div class="help-content">
          <h4>四种投标方式对比</h4>
          <table class="help-table">
            <thead>
              <tr><th>方式</th><th>合作单位</th><th>参标单位</th><th>适用场景</th></tr>
            </thead>
            <tbody>
              <tr>
                <td><span class="mock-tag primary">独立</span></td>
                <td>隐藏</td>
                <td>仅显示我方</td>
                <td>我方独立参与投标</td>
              </tr>
              <tr>
                <td><span class="mock-tag warning">联合体</span></td>
                <td>可选择</td>
                <td>我方+合作方合并为一条</td>
                <td>与其他单位组成联合体投标</td>
              </tr>
              <tr>
                <td><span class="mock-tag success">配合</span></td>
                <td>可选择</td>
                <td>合作方独立出现在参标列表</td>
                <td>合作单位配合我方投标</td>
              </tr>
              <tr>
                <td><span class="mock-tag info">陪标</span></td>
                <td>可选择</td>
                <td>合作方独立出现在参标列表</td>
                <td>参与投标但不以中标为目的</td>
              </tr>
            </tbody>
          </table>

          <h4>联合体投标示例</h4>
          <p>选择「联合体」方式时，我方与合作单位自动合并为一条参标记录：</p>
          <div class="mock-competitor-list">
            <div class="mock-competitor highlight">
              <span class="mock-tag primary">联合体</span>
              <span class="competitor-orgs">浙江意诚检测有限公司 + 杭州XX环保公司</span>
              <span class="competitor-price">报价: 85.00万</span>
              <span class="mock-tag success">中标 ✓</span>
            </div>
            <div class="mock-competitor">
              <span class="competitor-orgs">宁波YY检测公司</span>
              <span class="competitor-price">报价: 92.00万</span>
            </div>
            <div class="mock-competitor">
              <span class="competitor-orgs">温州ZZ科技</span>
              <span class="competitor-price">报价: 88.50万</span>
            </div>
          </div>
          <p>联合体模式下，可指定我方是否为<strong>牵头方</strong>。仅当牵头方+中标时，才显示合同信息录入区域。</p>

          <h4>入围标与入围分项</h4>
          <div class="mock-relation-diagram">
            <div class="mock-project-card parent">
              <div class="card-label">入围标（父项目）</div>
              <div class="card-title">2026年度检测服务框架协议</div>
              <div class="card-status"><span class="mock-tag success">已中标</span></div>
            </div>
            <div class="relation-arrow">
              <svg width="40" height="24" viewBox="0 0 40 24">
                <defs><marker id="arrow-blue" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M 0 0 L 10 5 L 0 10 z" fill="#409eff"/></marker></defs>
                <line x1="0" y1="12" x2="32" y2="12" stroke="#409eff" stroke-width="2" marker-end="url(#arrow-blue)"/>
              </svg>
            </div>
            <div class="mock-project-card child">
              <div class="card-label">入围分项（子项目）</div>
              <div class="card-title">西湖区水质检测子项目</div>
              <div class="card-status"><span class="mock-tag warning">准备投标</span></div>
            </div>
          </div>
          <ul>
            <li><strong>入围标</strong>：资格预审类项目（如年度框架协议），创建时勾选「是否入围标」</li>
            <li><strong>入围分项</strong>：入围标产生的具体子项目，招标类型选「入围分项」并关联父项目</li>
            <li>入围分项可从父项目同步参标单位（点击「从父项目同步参标单位」按钮）</li>
            <li>入围标的中标勾选支持多选（可多家中标），非入围标为单选</li>
          </ul>
        </div>
      </el-collapse-item>

      <!-- ==================== 五、保证金管理 ==================== -->
      <el-collapse-item title="五、保证金管理" name="deposit">
        <div class="help-content">
          <h4>保证金全流程</h4>
          <!-- 保证金生命周期流程图 -->
          <div class="deposit-flow">
            <div class="deposit-step">
              <div class="deposit-icon" style="background:#e6a23c">💰</div>
              <div class="deposit-label">缴纳保证金</div>
              <div class="deposit-note">投标信息卡片中<br/>设置「有保证金」</div>
            </div>
            <div class="deposit-arrow">→</div>
            <div class="deposit-step">
              <div class="deposit-icon" style="background:#409eff">📋</div>
              <div class="deposit-label">投标使用</div>
              <div class="deposit-note">提交投标后<br/>状态变为「未收回」</div>
            </div>
            <div class="deposit-arrow">→</div>
            <div class="deposit-step">
              <div class="deposit-icon" style="background:#67c23a">✅</div>
              <div class="deposit-label">保证金收回</div>
              <div class="deposit-note">投标结果卡片中<br/>标记「已收回」</div>
            </div>
          </div>

          <h4>操作示例</h4>
          <div class="step-list">
            <div class="step-item">
              <div class="step-num" style="background:#e6a23c">1</div>
              <div class="step-body">
                <div class="step-title">在投标信息中设置保证金</div>
                <div class="step-desc">
                  开启「有保证金」开关 → 选择状态 <span class="mock-tag success">已缴纳</span><br/>
                  填写金额：<code>50,000 元</code>，缴纳日期：<code>2026-04-01</code>
                </div>
              </div>
            </div>
            <div class="step-item">
              <div class="step-num" style="background:#409eff">2</div>
              <div class="step-body">
                <div class="step-title">提交投标后自动跟踪</div>
                <div class="step-desc">
                  点击「提交投标」后，系统自动设置保证金状态为 <span class="mock-tag warning">未收回</span><br/>
                  工作台首页会出现「保证金未收回」提醒
                </div>
              </div>
            </div>
            <div class="step-item">
              <div class="step-num" style="background:#67c23a">3</div>
              <div class="step-body">
                <div class="step-title">标记保证金收回</div>
                <div class="step-desc">
                  在投标结果卡片中，将保证金状态改为 <span class="mock-tag success">已收回</span><br/>
                  填写退还日期：<code>2026-05-15</code>
                </div>
              </div>
            </div>
          </div>
        </div>
      </el-collapse-item>

      <!-- ==================== 六、常见问题 ==================== -->
      <el-collapse-item title="六、常见问题" name="faq">
        <div class="help-content">
          <div class="faq-item">
            <div class="faq-q" style="border-left-color:#409eff">
              <strong>Q1：</strong>如何创建新项目？
            </div>
            <div class="faq-a">
              进入「项目管理」→ 点击右上角「新增项目」按钮 → 选择招标类型 → 填写项目名称 → 选择招标单位和负责人 → 点击「创建项目」。<br/>
              新建项目默认为<span class="mock-tag info">跟进中</span>状态。
            </div>
          </div>

          <div class="faq-item">
            <div class="faq-q" style="border-left-color:#67c23a">
              <strong>Q2：</strong>项目状态如何推进？
            </div>
            <div class="faq-a">
              在项目详情页底部会显示当前可用的操作按钮：<br/>
              <span class="mock-tag info">跟进中</span> → 点击「已发公告」<br/>
              <span class="mock-tag primary">已发公告/已报名</span> → 点击「准备投标」<br/>
              <span class="mock-tag warning">准备投标</span> → 点击「提交投标」<br/>
              每次推进前会自动保存当前信息。任何阶段都可以点击「放弃项目」退出流程。
            </div>
          </div>

          <div class="faq-item">
            <div class="faq-q" style="border-left-color:#e6a23c">
              <strong>Q3：</strong>如何录入投标结果？
            </div>
            <div class="faq-a">
              提交投标后，项目详情页会显示「投标结果」卡片：<br/>
              1. 点击「添加参标单位」录入各参标单位名称和报价<br/>
              2. 勾选中标单位（入围标可多选，普通项目单选）<br/>
              3. 系统自动推导中标状态和金额<br/>
              4. 点击「保存」完成录入
            </div>
          </div>

          <div class="faq-item">
            <div class="faq-q" style="border-left-color:#f56c6c">
              <strong>Q4：</strong>中标金额如何计算？
            </div>
            <div class="faq-a">
              根据控制价类型自动计算：<br/>
              <table class="help-table compact">
                <thead><tr><th>类型</th><th>计算公式</th><th>示例</th></tr></thead>
                <tbody>
                  <tr><td><span class="mock-tag primary">金额</span></td><td>中标金额 = 我方报价</td><td>报价 80 万 → 中标 80 万</td></tr>
                  <tr><td><span class="mock-tag warning">折扣率</span></td><td>中标金额 = 报价÷上限×预算</td><td>报价 85, 上限 100, 预算 120万 → 102万</td></tr>
                  <tr><td><span class="mock-tag success">下浮率</span></td><td>中标金额 = (1-报价/100)÷(1-上限/100)×预算</td><td>报价 12%, 上限 15%, 预算 100万 → 96.47万</td></tr>
                </tbody>
              </table>
            </div>
          </div>

          <div class="faq-item">
            <div class="faq-q" style="border-left-color:#909399">
              <strong>Q5：</strong>保证金如何管理？
            </div>
            <div class="faq-a">
              在投标信息卡片中开启「有保证金」并填写金额和缴纳日期。提交投标后，系统自动在结果卡片中跟踪保证金状态（未收回/已收回）。工作台首页会提醒未收回的保证金。
            </div>
          </div>

          <div class="faq-item">
            <div class="faq-q" style="border-left-color:#409eff">
              <strong>Q6：</strong>什么是入围标/入围分项？
            </div>
            <div class="faq-a">
              <strong>入围标</strong>是资格预审类项目（如年度框架协议），创建时勾选「是否入围标」。<br/>
              <strong>入围分项</strong>是入围标下产生的具体子项目，招标类型选「入围分项」并关联父入围标项目。创建后可从父项目同步参标单位，后续独立维护。
            </div>
          </div>
        </div>
      </el-collapse-item>
    </el-collapse>
  </el-drawer>
</template>

<script setup>
import { ref } from 'vue'

const drawerVisible = ref(false)
const activeSections = ref(['overview'])
</script>

<style scoped>
/* 底部触发条 */
.help-trigger {
  flex-shrink: 0;
  height: 40px;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 20px;
  color: #bfcbd9;
  background-color: #263445;
  cursor: pointer;
  font-size: 13px;
  transition: background-color 0.2s;
}
.help-trigger:hover {
  background-color: #1f2d3d;
  color: #fff;
}

/* 折叠面板样式 */
.help-collapse {
  border: none;
}

/* 内容区通用 */
.help-content {
  font-size: 15px;
  color: #606266;
  line-height: 1.8;
}
.help-content h4 {
  margin: 18px 0 8px;
  font-size: 16px;
  color: #303133;
  font-weight: 600;
}
.help-content p {
  margin: 6px 0;
}
.help-content ul {
  padding-left: 20px;
  margin: 6px 0;
}
.help-content li {
  line-height: 2;
}
.help-content code {
  background: #f5f7fa;
  padding: 1px 6px;
  border-radius: 3px;
  font-size: 14px;
  color: #409eff;
}

/* 模拟标签 (对应 el-tag) */
.mock-tag {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 4px;
  font-size: 13px;
  line-height: 22px;
}
.mock-tag.primary { background: #ecf5ff; color: #409eff; }
.mock-tag.success { background: #f0f9eb; color: #67c23a; }
.mock-tag.warning { background: #fdf6ec; color: #e6a23c; }
.mock-tag.danger { background: #fef0f0; color: #f56c6c; }
.mock-tag.info { background: #f4f4f5; color: #909399; }

/* 模拟按钮 */
.mock-btn {
  display: inline-block;
  padding: 5px 14px;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  font-size: 13px;
  color: #606266;
  background: #fff;
  margin-right: 4px;
}
.mock-btn.active {
  background: #409eff;
  color: #fff;
  border-color: #409eff;
}

/* 表格 */
.help-table {
  width: 100%;
  border-collapse: collapse;
  margin: 8px 0;
  font-size: 14px;
}
.help-table th {
  background: #f5f7fa;
  padding: 8px 10px;
  text-align: left;
  border: 1px solid #ebeef5;
  color: #909399;
  font-weight: 500;
}
.help-table td {
  padding: 8px 10px;
  border: 1px solid #ebeef5;
  color: #606266;
}
.help-table.compact td,
.help-table.compact th {
  padding: 6px 8px;
  font-size: 13px;
}

/* ===== 一、界面布局模拟 ===== */
.mock-layout {
  display: flex;
  border: 1px solid #dcdfe6;
  border-radius: 6px;
  overflow: hidden;
  height: 180px;
  margin: 8px 0;
}
.mock-sidebar {
  width: 90px;
  background: #304156;
  color: #bfcbd9;
  font-size: 10px;
  padding: 0;
  flex-shrink: 0;
}
.mock-sidebar-title {
  height: 22px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  color: #fff;
  font-size: 9px;
  border-bottom: 1px solid #3a4a5f;
}
.mock-menu-item {
  padding: 4px 6px;
  color: #bfcbd9;
  font-size: 9px;
}
.mock-menu-item.active {
  color: #409eff;
  background: rgba(64,158,255,0.1);
}
.mock-help-badge {
  position: absolute;
  bottom: 0;
  width: 90px;
  background: #263445;
  padding: 4px 0;
  text-align: center;
  font-size: 9px;
  color: #bfcbd9;
  position: relative;
  margin-top: auto;
}
.mock-main {
  flex: 1;
  display: flex;
  flex-direction: column;
}
.mock-header {
  height: 22px;
  background: #fff;
  border-bottom: 1px solid #e6e6e6;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 8px;
  font-size: 9px;
  color: #333;
}
.mock-user { color: #666; font-size: 8px; }
.mock-body {
  flex: 1;
  background: #f0f2f5;
}
.layout-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin: 6px 0;
  font-size: 13px;
}
.legend-item {
  display: flex;
  align-items: center;
  gap: 4px;
  color: #909399;
}
.legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 2px;
  display: inline-block;
  flex-shrink: 0;
}

/* ===== 二、流程图 ===== */
.flow-svg-wrap {
  margin: 8px 0;
  text-align: center;
}
.flow-svg {
  width: 100%;
  max-width: 460px;
}

/* 步骤列表 */
.step-list {
  margin: 8px 0;
}
.step-item {
  display: flex;
  gap: 10px;
  margin-bottom: 10px;
}
.step-num {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: bold;
  flex-shrink: 0;
}
.step-body {
  flex: 1;
}
.step-title {
  font-weight: 600;
  color: #303133;
  margin-bottom: 2px;
}
.step-desc {
  color: #606266;
  font-size: 14px;
  line-height: 1.8;
}
.example-intro {
  color: #909399;
  font-size: 14px;
  font-style: italic;
  margin-bottom: 4px !important;
}

/* 田字布局示意 */
.mock-detail-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
  margin: 8px 0;
}
.mock-grid-cell {
  padding: 10px;
  border-radius: 4px;
  text-align: center;
  border: 1px solid;
}
.mock-grid-cell.always {
  background: #f0f9eb;
  border-color: #b3e19d;
}
.mock-grid-cell.from-published {
  background: #ecf5ff;
  border-color: #a0cfff;
}
.mock-grid-cell.from-preparing {
  background: #fdf6ec;
  border-color: #f3d19e;
}
.mock-grid-cell.from-submitted {
  background: #ecf5ff;
  border-color: #a0cfff;
}
.cell-label {
  display: block;
  font-weight: 600;
  font-size: 14px;
  color: #303133;
}
.cell-status {
  display: block;
  font-size: 12px;
  color: #909399;
  margin-top: 2px;
}

/* ===== 三、模拟工作台统计 ===== */
.mock-dashboard {
  display: flex;
  gap: 6px;
  margin: 8px 0;
}
.mock-stat-card {
  flex: 1;
  text-align: center;
  padding: 10px 0;
  border: 1px solid #ebeef5;
  border-radius: 4px;
  background: #fff;
}
.stat-num {
  font-size: 22px;
  font-weight: bold;
}
.stat-label {
  font-size: 13px;
  color: #999;
  margin-top: 2px;
}

/* 模拟筛选条 */
.mock-filter-bar {
  margin: 8px 0;
}

/* 模拟表格 */
.mock-table {
  border: 1px solid #ebeef5;
  border-radius: 4px;
  overflow: hidden;
  margin: 8px 0;
  font-size: 13px;
}
.mock-table-header {
  display: flex;
  background: #f5f7fa;
  padding: 6px 8px;
  font-weight: 500;
  color: #909399;
}
.mock-table-row {
  display: flex;
  padding: 6px 8px;
  border-top: 1px solid #ebeef5;
}
.mock-table-row.alt {
  background: #fafafa;
}
.col-name { flex: 2; }
.col-type { flex: 1; text-align: center; }
.col-status { flex: 1; text-align: center; }
.col-region { flex: 1; text-align: center; }

/* 模拟标签页 */
.mock-tabs {
  display: flex;
  border-bottom: 2px solid #e4e7ed;
  margin: 8px 0;
}
.mock-tab {
  padding: 6px 12px;
  font-size: 14px;
  color: #909399;
  cursor: default;
}
.mock-tab.active {
  color: #409eff;
  border-bottom: 2px solid #409eff;
  margin-bottom: -2px;
  font-weight: 500;
}

/* ===== 四、联合体示例 ===== */
.mock-competitor-list {
  border: 1px solid #ebeef5;
  border-radius: 4px;
  overflow: hidden;
  margin: 8px 0;
}
.mock-competitor {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border-bottom: 1px solid #f2f6fc;
  font-size: 14px;
}
.mock-competitor.highlight {
  background: #f0f9eb;
}
.competitor-orgs {
  flex: 1;
  font-weight: 500;
}
.competitor-price {
  color: #909399;
  font-size: 13px;
}

/* 父子项目关系图 */
.mock-relation-diagram {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  margin: 12px 0;
}
.mock-project-card {
  border: 1px solid #dcdfe6;
  border-radius: 6px;
  padding: 10px;
  width: 160px;
  text-align: center;
}
.mock-project-card.parent {
  border-color: #67c23a;
  background: #f0f9eb;
}
.mock-project-card.child {
  border-color: #e6a23c;
  background: #fdf6ec;
}
.card-label {
  font-size: 12px;
  color: #909399;
  margin-bottom: 4px;
}
.card-title {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
  margin-bottom: 4px;
}
.card-status {
  margin-top: 2px;
}
.relation-arrow {
  flex-shrink: 0;
}

/* ===== 五、保证金流程 ===== */
.deposit-flow {
  display: flex;
  align-items: flex-start;
  justify-content: center;
  gap: 4px;
  margin: 12px 0;
}
.deposit-step {
  text-align: center;
  width: 110px;
}
.deposit-icon {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 6px;
  font-size: 18px;
}
.deposit-label {
  font-weight: 600;
  font-size: 14px;
  color: #303133;
}
.deposit-note {
  font-size: 12px;
  color: #909399;
  margin-top: 2px;
  line-height: 1.5;
}
.deposit-arrow {
  color: #c0c4cc;
  font-size: 18px;
  margin-top: 14px;
}

/* ===== 六、FAQ ===== */
.faq-item {
  margin-bottom: 12px;
}
.faq-q {
  padding-left: 10px;
  border-left: 3px solid #409eff;
  margin-bottom: 4px;
  font-size: 15px;
  color: #303133;
}
.faq-a {
  padding-left: 13px;
  font-size: 14px;
  color: #606266;
  line-height: 1.8;
}
</style>
