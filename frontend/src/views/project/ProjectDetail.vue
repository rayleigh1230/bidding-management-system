<template>
  <div>
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px">
      <el-page-header @back="$router.push('/projects')">
        <template #content>
          <span>{{ isNew ? '新增项目' : project.project_name }}</span>
          <el-tag v-if="!isNew" :type="statusType(project.status)" style="margin-left: 8px">{{ statusLabel(project.status) }}</el-tag>
          <el-tag v-if="isMultiLotParent" type="warning" size="small" style="margin-left: 8px">多标段</el-tag>
          <el-tag v-if="isMultiLotChild" size="small" style="margin-left: 8px">标段</el-tag>
          <el-link v-if="!isNew && projectForm.parent_project_id" type="info" :underline="false" style="margin-left: 8px; font-size: 12px" @click="$router.push(`/projects/${projectForm.parent_project_id}`)">
            父项目：{{ parentProjectName }}
          </el-link>
        </template>
      </el-page-header>
    </div>

    <!-- 多标段父项目：Tab 切换 -->
    <div v-if="isMultiLotParent && !isNew" style="margin-bottom: 16px">
      <el-tabs :model-value="activeLotTab" @tab-click="handleLotTabClick">
        <el-tab-pane name="__summary__" label="汇总" />
        <el-tab-pane
          v-for="lot in lotList"
          :key="lot.id"
          :name="String(lot.id)"
          :label="lot.project_name || `标段 #${lot.id}`"
        />
        <el-tab-pane name="__add__" label="+ 添加标段" />
      </el-tabs>
    </div>

    <!-- 多标段父项目汇总 Tab -->
    <el-card v-if="isMultiLotParent && activeLotTab === '__summary__'">
      <template #header><span>标段汇总</span></template>
      <el-table :data="lotList" border size="small">
        <el-table-column label="标段名称" min-width="120">
          <template #default="{ row: lot }">
            <el-link type="primary" @click="activeLotTab = String(lot.id); switchToLot(lot.id)">{{ lot.project_name }}</el-link>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="80">
          <template #default="{ row: lot }">
            <el-tag size="small" :type="statusType(lot.status)">{{ statusLabel(lot.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="预算金额(元)" width="110">
          <template #default="{ row: lot }">{{ lot.budget_amount?.toLocaleString() || '-' }}</template>
        </el-table-column>
        <el-table-column label="我方报价" width="90">
          <template #default="{ row: lot }">{{ lot.our_price_display || '-' }}</template>
        </el-table-column>
        <el-table-column label="中标金额" width="100">
          <template #default="{ row: lot }">{{ lot.winning_amount_display || '-' }}</template>
        </el-table-column>
        <el-table-column label="中标单位" width="120">
          <template #default="{ row: lot }">{{ (lot.winning_org_names || []).join(', ') || '-' }}</template>
        </el-table-column>
      </el-table>
      <div v-if="!lotList.length" style="color: #999; text-align: center; padding: 24px">暂无标段，点击"+ 添加标段"创建</div>
    </el-card>

    <!-- 田字布局：4个卡片（多标段父汇总时不显示） -->
    <div v-if="!(isMultiLotParent && activeLotTab === '__summary__')" class="detail-grid">
      <!-- 左上：项目基本信息 (always visible) -->
      <el-card>
        <template #header><span>项目基本信息</span></template>
        <el-form ref="projectFormRef" :model="projectForm" :rules="projectRules" label-width="100px">
          <el-row :gutter="16">
            <el-col :span="12">
              <el-form-item label="招标类型" prop="bidding_type">
                <el-select v-model="projectForm.bidding_type" placeholder="请选择招标类型" :disabled="!isNew && !isFollowing" style="width: 100%">
                  <el-option label="公开招标" value="公开招标" />
                  <el-option label="邀请招标" value="邀请招标" />
                  <el-option label="中介超市" value="中介超市" />
                  <el-option label="入围分项" value="入围分项" />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="所属地区">
                <RegionCascader v-model="projectForm.region" :disabled="!isNew && !isFollowing" style="width: 100%" />
              </el-form-item>
            </el-col>
          </el-row>
          <el-form-item v-if="projectForm.bidding_type === '入围分项'" label="关联入围标">
            <el-select
              v-model="projectForm.parent_project_id"
              filterable
              remote
              reserve-keyword
              placeholder="搜索入围标项目"
              :remote-method="searchParentProjects"
              :disabled="!isNew && !isFollowing"
              clearable
              style="width: 100%"
              @change="handleParentProjectChange"
            >
              <el-option v-for="p in parentProjectOptions" :key="p.id" :label="p.project_name" :value="p.id">
                <span>{{ p.project_name }}</span>
                <span style="float: right; color: #999; font-size: 12px">ID: {{ p.id }}</span>
              </el-option>
            </el-select>
          </el-form-item>
          <el-form-item label="项目名称" prop="project_name">
            <el-input v-model="projectForm.project_name" :disabled="!isNew && !isFollowing" />
          </el-form-item>
          <el-form-item label="招标单位">
            <OrgSelector v-model="projectForm.bidding_unit_id" :disabled="!isNew && !isFollowing" :exclude-ours style="width: 100%" />
          </el-form-item>
          <el-form-item label="项目负责人">
            <ManagerSelector v-model="projectForm.manager_ids" :multiple="true" :disabled="!isNew && !isFollowing" style="width: 100%" />
          </el-form-item>
          <el-form-item v-if="isNew || isFollowing" label="多标段项目">
            <el-switch v-model="projectForm.is_multi_lot" active-text="是（创建标段容器）" inactive-text="否" />
          </el-form-item>
          <el-form-item label="项目描述">
            <el-input v-model="projectForm.description" type="textarea" :rows="3" :disabled="!isNew && !isFollowing" />
          </el-form-item>
        </el-form>
      </el-card>

      <!-- 右上：招标信息 (status >= 已发公告) -->
      <el-card v-if="showBidding">
        <template #header><span>招标信息</span></template>
        <el-form :model="biddingForm" label-width="100px">
          <el-row :gutter="16">
            <el-col :span="12">
              <el-form-item label="代理单位">
                <OrgSelector v-model="biddingForm.agency_id" :exclude-ours style="width: 100%" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="发布平台">
                <PlatformSelector v-model="biddingForm.publish_platform_id" style="width: 100%" />
              </el-form-item>
            </el-col>
          </el-row>
          <el-form-item label="标签">
            <el-select v-model="biddingForm.tags" multiple filterable allow-create default-first-option placeholder="输入标签" style="width: 100%">
              <el-option v-for="tag in biddingForm.tags" :key="tag" :label="tag" :value="tag" />
            </el-select>
          </el-form-item>
          <el-row :gutter="16">
            <el-col :span="12">
              <el-form-item label="报名截止">
                <div style="display: flex; align-items: center; gap: 12px; width: 100%">
                  <el-date-picker v-model="biddingForm.registration_deadline" type="date" value-format="YYYY-MM-DD" format="YYYY-MM-DD" style="flex: 1" />
                  <el-checkbox v-if="biddingForm.registration_deadline" v-model="biddingForm.is_registered">已报名</el-checkbox>
                </div>
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="投标截止">
                <el-date-picker v-model="biddingForm.bid_deadline" type="date" value-format="YYYY-MM-DD" format="YYYY-MM-DD" style="width: 100%" />
              </el-form-item>
            </el-col>
          </el-row>
          <el-row :gutter="16">
            <el-col :span="12">
              <el-form-item label="预算金额">
                <div style="display: flex; align-items: center; width: 100%">
                  <el-input-number v-model="biddingForm.budget_amount" :min="0" :precision="2" :controls="false" style="flex: 1" />
                  <span style="margin-left: 4px; color: #999; white-space: nowrap">元</span>
                </div>
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="控制价类型">
                <el-select v-model="biddingForm.control_price_type" style="width: 100%">
                  <el-option label="金额" value="金额" />
                  <el-option label="折扣率" value="折扣率" />
                  <el-option label="下浮率" value="下浮率" />
                </el-select>
              </el-form-item>
            </el-col>
          </el-row>
          <el-row :gutter="16">
            <el-col :span="12">
              <el-form-item label="控制价上限">
                <div style="display: flex; align-items: center; width: 100%">
                  <el-input-number v-model="biddingForm.control_price_upper" :min="0" :precision="2" :controls="false" style="flex: 1" />
                  <span style="margin-left: 4px; color: #999; white-space: nowrap">{{ biddingForm.control_price_type !== '金额' ? '%' : '元' }}</span>
                </div>
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="控制价下限">
                <div style="display: flex; align-items: center; width: 100%">
                  <el-input-number v-model="biddingForm.control_price_lower" :min="0" :precision="2" :controls="false" style="flex: 1" />
                  <span style="margin-left: 4px; color: #999; white-space: nowrap">{{ biddingForm.control_price_type !== '金额' ? '%' : '元' }}</span>
                </div>
              </el-form-item>
            </el-col>
          </el-row>
          <el-row :gutter="16">
            <el-col :span="12">
              <el-form-item v-if="projectForm.bidding_type !== '入围分项'" label="是否入围标">
                <el-switch v-model="biddingForm.is_prequalification" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="投标专员">
                <el-select v-model="biddingForm.bid_specialist_id" clearable filterable placeholder="选择投标专员" style="width: 100%">
                  <el-option v-for="u in users" :key="u.id" :label="u.display_name" :value="u.id" />
                </el-select>
              </el-form-item>
            </el-col>
          </el-row>
          <el-form-item label="备注">
            <el-input v-model="biddingForm.bidding_notes" type="textarea" :rows="2" />
          </el-form-item>
        </el-form>
      </el-card>

      <!-- 左下：投标信息 (status >= 准备投标) -->
      <el-card v-if="showBid">
        <template #header><span>投标信息</span></template>
        <el-form :model="bidForm" label-width="100px">
          <el-row :gutter="16">
            <el-col :span="12">
              <el-form-item label="投标方式">
                <el-select v-model="bidForm.bid_method" style="width: 100%">
                  <el-option label="独立" value="独立" />
                  <el-option label="联合体" value="联合体" />
                  <el-option label="配合" value="配合" />
                  <el-option label="陪标" value="陪标" />
                </el-select>
              </el-form-item>
            </el-col>
          </el-row>
          <el-form-item v-if="bidForm.bid_method !== '独立'" label="合作单位">
            <OrgSelector v-model="bidForm.partner_ids" :multiple="true" :exclude-ours :exclude-ids="partnerExcludeIds" style="width: 100%" />
          </el-form-item>
          <el-form-item v-if="bidForm.bid_method === '联合体'" label="我方是否牵头">
            <el-switch v-model="bidForm.is_consortium_lead" active-text="是（牵头方）" inactive-text="否" />
          </el-form-item>
          <el-row :gutter="16">
            <el-col :span="12">
              <el-form-item label="有保证金">
                <el-switch v-model="bidForm.has_deposit" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="我方报价">
                <div style="display: flex; align-items: center; width: 100%">
                  <el-input-number v-model="bidForm.our_price" :min="0" :precision="2" :controls="false" style="flex: 1" />
                  <span style="margin-left: 4px; color: #999; white-space: nowrap">{{ biddingForm.control_price_type !== '金额' ? '%' : '元' }}</span>
                </div>
              </el-form-item>
            </el-col>
          </el-row>
          <template v-if="bidForm.has_deposit">
            <el-form-item label="保证金">
              <div style="display: flex; align-items: center; gap: 16px; width: 100%">
                <div style="display: flex; align-items: center">
                  <el-input-number v-model="bidForm.deposit_amount" :min="0" :precision="2" :controls="false" style="width: 140px" />
                  <span style="margin-left: 4px; color: #999; white-space: nowrap">元</span>
                </div>
                <el-date-picker v-model="bidForm.deposit_date" type="date" value-format="YYYY-MM-DD" format="YYYY-MM-DD" placeholder="缴纳日期" style="width: 160px" />
                <el-checkbox v-model="depositPaid">已缴纳</el-checkbox>
              </div>
            </el-form-item>
          </template>
          <el-form-item label="备注">
            <el-input v-model="bidForm.bid_notes" type="textarea" :rows="2" />
          </el-form-item>
        </el-form>
      </el-card>

      <!-- 右下：投标结果 (status >= 已投标) -->
      <el-card v-if="showResult">
        <template #header><span>投标结果</span></template>
        <el-form :model="resultForm" label-width="100px">
          <!-- 投标结果 -->
          <el-form-item label="投标结果">
            <el-radio-group :model-value="bidResultType" @change="handleBidResultChange">
              <el-radio value="won">已中标</el-radio>
              <el-radio value="lost">未中标</el-radio>
              <el-radio value="failed">流标</el-radio>
            </el-radio-group>
          </el-form-item>

          <!-- 参标单位报价 + 评分 + 中标勾选 -->
          <el-form-item label="参标单位">
            <div v-for="(comp, idx) in resultForm.competitors" :key="idx"
                 :style="{ display: 'flex', gap: '8px', marginBottom: '8px', width: '100%', alignItems: 'center',
                            border: comp.is_winning ? '2px solid #67c23a' : '1px solid #ddd',
                            borderRadius: '8px', padding: '8px', background: comp.is_winning ? '#f0f9eb' : '#fff' }">
              <!-- 类型标签 -->
              <el-tag size="small" :type="comp.org_ids.length > 1 ? 'warning' : 'info'" style="flex-shrink: 0">
                {{ comp.org_ids.length > 1 ? '联合体' : comp.org_ids.length === 1 ? '独立' : '待选' }}
              </el-tag>
              <!-- 单位选择/展示 -->
              <div style="display: flex; flex-wrap: wrap; gap: 4px; flex: 1; align-items: center;">
                <el-tag v-for="oid in comp.org_ids" :key="oid" size="small" :type="isOurOrg(oid) ? '' : 'info'">
                  {{ getOrgName(oid) }}
                </el-tag>
                <template v-if="!isOurEntry(comp)">
                  <el-button v-if="!comp._editing" size="small" type="primary" link @click="comp._editing = true">编辑</el-button>
                  <el-button v-if="comp._editing" size="small" type="success" link @click="comp._editing = false">完成</el-button>
                </template>
              </div>
              <!-- 编辑态：OrgSelector -->
              <div v-if="comp._editing || !comp.org_ids.length" style="flex: 1; min-width: 180px;">
                <OrgSelector v-model="comp.org_ids" :multiple="true" :exclude-ids="getExcludedOrgIds(idx)" style="width: 100%"
                  @change="syncOrgToMap" />
              </div>
              <!-- 报价 -->
              <div style="display: flex; align-items: center">
                <el-input-number v-model="comp.price" :min="0" :precision="2" :controls="false" placeholder="报价" style="width: 100px" />
                <span style="margin-left: 2px; color: #999; white-space: nowrap; font-size: 12px">{{ controlPriceType !== '金额' ? '%' : '元' }}</span>
              </div>
              <!-- 评分 -->
              <el-input-number v-model="comp.score" :min="0" :precision="1" :controls="false" placeholder="评分" style="width: 80px" />
              <!-- 中标勾选 -->
              <el-checkbox v-model="comp.is_winning" :disabled="resultForm.is_bid_failed" @change="handleWinningChange(comp)">中标</el-checkbox>
              <!-- 删除按钮（我方条目不可删除） -->
              <el-button v-if="!isOurEntry(comp)" type="danger" link @click="resultForm.competitors.splice(idx, 1)"><el-icon><Delete /></el-icon></el-button>
            </div>
            <div style="display: flex; gap: 12px; align-items: center">
              <el-button type="primary" link @click="addCompetitor">+ 添加参标单位</el-button>
              <el-button v-if="projectForm.parent_project_id" type="warning" link @click="doSyncCompetitors">从父项目同步参标单位</el-button>
            </div>
          </el-form-item>

          <!-- 保证金状态（仅已缴纳时显示收回流程） -->
          <el-row v-if="bidForm.has_deposit && depositPaid" :gutter="16">
            <el-col :span="12">
              <el-form-item label="保证金状态">
                <el-select v-model="resultForm.result_deposit_status" style="width: 100%">
                  <el-option label="未收回" value="未收回" />
                  <el-option label="已收回" value="已收回" />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col v-if="resultForm.result_deposit_status === '已收回'" :span="12">
              <el-form-item label="退回日期">
                <el-date-picker v-model="bidForm.deposit_return_date" type="date" value-format="YYYY-MM-DD" format="YYYY-MM-DD" style="width: 100%" />
              </el-form-item>
            </el-col>
          </el-row>

          <!-- 中标单位（只读展示，从参标单位勾选推导） -->
          <el-form-item label="中标单位">
            <div v-if="resultForm.winning_org_ids.length" style="display: flex; flex-wrap: wrap; gap: 6px">
              <el-tag v-for="orgId in resultForm.winning_org_ids" :key="orgId" type="success" size="large">
                {{ getOrgName(orgId) }}
              </el-tag>
            </div>
            <span v-else style="color: #999">请在参标单位中勾选中标</span>
          </el-form-item>

          <!-- 中标折扣率/下浮率 + 中标金额（同一排） -->
          <el-row :gutter="16">
            <el-col v-if="controlPriceType !== '金额'" :span="12">
              <el-form-item :label="winningPriceLabel">
                <!-- 入围标：手动输入 -->
                <template v-if="biddingForm.is_prequalification">
                  <div style="display: flex; align-items: center; width: 100%">
                    <el-input-number v-model="resultForm.winning_price" :min="0" :precision="2" :controls="false" style="flex: 1" />
                    <span style="margin-left: 4px; color: #999">%</span>
                  </div>
                </template>
                <!-- 非入围标：自动推导 -->
                <template v-else>
                  <span style="font-weight: bold">{{ derivedWinningPriceDisplay }}</span>
                  <span style="margin-left: 4px; color: #999; font-size: 12px">（自动推导）</span>
                </template>
              </el-form-item>
            </el-col>
            <el-col :span="controlPriceType !== '金额' ? 12 : 24">
              <el-form-item label="中标金额">
                <!-- 入围标：手动输入 -->
                <template v-if="biddingForm.is_prequalification">
                  <div style="display: flex; align-items: center; width: 100%">
                    <el-input-number v-model="resultForm.winning_amount" :min="0" :precision="2" :controls="false" style="flex: 1" />
                    <span style="margin-left: 4px; color: #999">元</span>
                  </div>
                </template>
                <!-- 非入围标：自动推导 -->
                <template v-else>
                  <span style="color: #409EFF; font-weight: bold">{{ derivedWinningAmountDisplay }}</span>
                  <span style="margin-left: 4px; color: #999; font-size: 12px">（自动推导）</span>
                </template>
              </el-form-item>
            </el-col>
          </el-row>

          <!-- 已中标专属：合同信息（联合体时需为牵头方） -->
          <template v-if="resultForm.is_won && (bidForm.bid_method !== '联合体' || bidForm.is_consortium_lead)">
            <el-row :gutter="16">
              <el-col :span="12">
                <el-form-item label="合同编号">
                  <el-input v-model="resultForm.contract_number" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="合同状态">
                  <el-select v-model="resultForm.contract_status" style="width: 100%">
                    <el-option label="无" value="无" />
                    <el-option label="未签订" value="未签订" />
                    <el-option label="已签订未收回" value="已签订未收回" />
                    <el-option label="已签订已收回" value="已签订已收回" />
                  </el-select>
                </el-form-item>
              </el-col>
            </el-row>
            <el-form-item label="合同金额">
              <div style="display: flex; align-items: center; width: 100%">
                <el-input-number v-model="resultForm.contract_amount" :min="0" :precision="2" :controls="false" style="width: 200px" />
                <span style="margin-left: 8px; color: #999">元</span>
              </div>
            </el-form-item>
          </template>

          <!-- 未中标专属 -->
          <template v-if="resultForm.is_won === false && !resultForm.is_bid_failed">
            <el-form-item label="未中标分析">
              <el-input v-model="resultForm.lost_analysis" type="textarea" :rows="3" placeholder="分析未中标原因" />
            </el-form-item>
          </template>

          <el-form-item label="备注">
            <el-input v-model="resultForm.result_notes" type="textarea" :rows="2" />
          </el-form-item>
        </el-form>
      </el-card>
    </div>

    <!-- 已放弃信息 -->
    <el-card v-if="isAbandoned && !isNew" style="margin-top: 16px">
      <template #header><span style="color: #E6A23C">已放弃</span></template>
      <p style="color: #666; margin: 0">{{ project.abandon_reason }}</p>
    </el-card>

    <!-- 操作按钮 -->
    <div v-if="!isAbandoned || isNew" style="margin-top: 16px; display: flex; gap: 8px">
      <el-button v-if="isNew" type="primary" :loading="saving" @click="handleSave">创建项目</el-button>
      <template v-if="!isNew">
        <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
        <template v-if="!isMultiLotParent">
          <el-button v-if="isFollowing" type="success" @click="handlePublish">已发公告</el-button>
          <el-button v-if="isPublished || isNotRegistered || isRegistered" type="warning" @click="handlePrepare">准备投标</el-button>
          <el-button v-if="isPreparing" type="primary" @click="handleSubmit">提交投标</el-button>
          <el-button v-if="canAbandon" type="danger" @click="showAbandonDialog = true">放弃</el-button>
        </template>
      </template>
    </div>

    <!-- 创建标段对话框（自动继承父项目基本信息） -->
    <el-dialog v-model="showCreateLotDialog" title="添加标段" width="520px">
      <el-form :model="newLotForm" label-width="100px">
        <el-form-item label="标段名称" required>
          <el-input v-model="newLotForm.project_name" :placeholder="projectForm.project_name + ' - 标段X'" />
        </el-form-item>
        <el-form-item label="招标单位">
          <span>{{ getOrgName(newLotForm.bidding_unit_id) || '未设置' }}</span>
          <el-tag size="small" type="info" style="margin-left: 8px">继承自父项目</el-tag>
        </el-form-item>
        <el-form-item label="所属地区">
          <span>{{ formatRegionDisplay(newLotForm.region) || '未设置' }}</span>
          <el-tag size="small" type="info" style="margin-left: 8px">继承自父项目</el-tag>
        </el-form-item>
        <el-form-item label="项目负责人">
          <span>{{ (newLotForm.manager_ids || []).map(id => getManagerName(id)).filter(Boolean).join(', ') || '未设置' }}</span>
          <el-tag size="small" type="info" style="margin-left: 8px">继承自父项目</el-tag>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateLotDialog = false">取消</el-button>
        <el-button type="primary" :loading="creatingLot" @click="handleCreateLot">创建</el-button>
      </template>
    </el-dialog>

    <!-- 放弃对话框 -->
    <el-dialog v-model="showAbandonDialog" title="放弃项目" width="400px">
      <el-form label-width="80px">
        <el-form-item label="放弃原因">
          <el-input v-model="abandonReason" type="textarea" :rows="3" placeholder="请输入放弃原因" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAbandonDialog = false">取消</el-button>
        <el-button type="danger" @click="handleAbandon">确认放弃</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete } from '@element-plus/icons-vue'
import {
  getProject, createProject, updateProject,
  publishProject, prepareProject, submitProject, abandonProject,
  getProjects, syncCompetitors, getProjectLots,
} from '../../api/project'
import { getUsers } from '../../api/user'
import { getOrganizations } from '../../api/dict'
import OrgSelector from '../../components/OrgSelector.vue'
import PlatformSelector from '../../components/PlatformSelector.vue'
import RegionCascader from '../../components/RegionCascader.vue'
import ManagerSelector from '../../components/ManagerSelector.vue'

const route = useRoute()
const router = useRouter()
const saving = ref(false)
const showAbandonDialog = ref(false)
const abandonReason = ref('')
const users = ref([])
const orgMap = ref({})  // id -> { id, name }
const parentProjectName = ref('')
const parentProjectOptions = ref([])  // 远程搜索入围标项目选项

// ---- 多标段支持 ----
const lotList = ref([])
const activeLotTab = ref('')
const showCreateLotDialog = ref(false)
const creatingLot = ref(false)
const newLotForm = ref({
  project_name: '', bidding_unit_id: null, region: [], manager_ids: [],
})

async function loadLots() {
  if (!isMultiLotParent.value) return
  try {
    const res = await getProjectLots(project.value.id)
    lotList.value = res.items || []
    if (!activeLotTab.value && lotList.value.length) {
      activeLotTab.value = '__summary__'
    }
  } catch { /* ignore */ }
}

async function saveCurrentLot() {
  const currentLotId = parseInt(activeLotTab.value)
  if (isNaN(currentLotId)) return
  try {
    const data = collectSaveData()
    await updateProject(currentLotId, data)
  } catch { /* 静默忽略 */ }
}

async function switchToLot(lotId) {
  if (isNaN(lotId)) return
  try {
    const data = await getProject(lotId)
    // 将子标段数据映射到当前表单
    project.value = data
    let region = []
    if (data.region) { try { region = JSON.parse(data.region) } catch { region = [] } }
    let managerIds = data.manager_ids || []
    if (typeof managerIds === 'string') { try { managerIds = JSON.parse(managerIds) } catch { managerIds = [] } }
    projectForm.value = {
      bidding_type: data.bidding_type, project_name: data.project_name,
      bidding_unit_id: data.bidding_unit_id, region, manager_ids: managerIds,
      description: data.description || '',
      parent_project_id: data.parent_project_id || null,
    }
    if (data.parent_project_id) {
      parentProjectName.value = data.parent_project_name || ''
      parentProjectOptions.value = [{ id: data.parent_project_id, project_name: data.parent_project_name || `项目 #${data.parent_project_id}` }]
    }
    biddingForm.value = {
      agency_id: data.agency_id, publish_platform_id: data.publish_platform_id,
      tags: parseJson(data.tags, []), registration_deadline: data.registration_deadline,
      bid_deadline: data.bid_deadline, budget_amount: data.budget_amount || 0,
      control_price_type: data.control_price_type || '金额',
      control_price_upper: data.control_price_upper, control_price_lower: data.control_price_lower,
      is_prequalification: data.is_prequalification || false,
      bid_specialist_id: data.bid_specialist_id, bidding_notes: data.bidding_notes || '',
      is_registered: data.is_registered || (statusGte(data.status, '准备投标') && !!data.registration_deadline),
    }
    bidForm.value = {
      partner_ids: parseJson(data.partner_ids, []), bid_method: data.bid_method || '独立',
      is_consortium_lead: data.is_consortium_lead !== false,
      has_deposit: data.has_deposit || false,
      deposit_status: data.deposit_status || '无', deposit_amount: data.deposit_amount || 0,
      deposit_date: data.deposit_date, deposit_return_date: data.deposit_return_date,
      our_price: data.our_price || 0, bid_notes: data.bid_notes || '',
    }
    _updatingFromWinning = true
    const rawCompetitors = parseJson(data.competitors, [])
    resultForm.value = {
      competitors: rawCompetitors.map(c => ({
        org_ids: c.org_ids || (c.org_id ? [c.org_id] : []),
        price: c.price || 0, score: c.score || 0,
        is_shortlisted: c.is_shortlisted || false, is_winning: c.is_winning || false,
      })),
      scoring_details: parseJson(data.scoring_details, []),
      result_deposit_status: data.result_deposit_status,
      is_won: data.is_won || false, is_bid_failed: data.is_bid_failed || false,
      winning_org_id: data.winning_org_id,
      winning_org_ids: parseJson(data.winning_org_ids, []),
      winning_price: data.winning_price, winning_amount: data.winning_amount,
      lost_analysis: data.lost_analysis || '', contract_number: data.contract_number || '',
      contract_status: data.contract_status || '无', contract_amount: data.contract_amount || 0,
      result_notes: data.result_notes || '',
    }
    await nextTick()
    _updatingFromWinning = false
    ensureOurCompanyInCompetitors()
  } catch { /* ignore */ }
}

async function handleLotTabClick(pane) {
  const targetName = pane.paneName || pane
  if (targetName === '__add__') {
    // 预填父项目基本信息
    newLotForm.value = {
      project_name: '',
      bidding_unit_id: projectForm.value.bidding_unit_id,
      region: [...(projectForm.value.region || [])],
      manager_ids: [...(projectForm.value.manager_ids || [])],
      description: '',
    }
    showCreateLotDialog.value = true
    // 恢复之前的 tab
    await nextTick()
    return
  }
  // 切换前保存当前标段
  if (activeLotTab.value && activeLotTab.value !== '__summary__' && activeLotTab.value !== '__add__') {
    await saveCurrentLot()
  }
  if (targetName === '__summary__') {
    activeLotTab.value = '__summary__'
    return
  }
  activeLotTab.value = targetName
  await switchToLot(parseInt(targetName))
}

async function handleCreateLot() {
  creatingLot.value = true
  try {
    const lotData = {
      ...newLotForm.value,
      bidding_type: projectForm.value.bidding_type,
      parent_project_id: project.value.id,
      is_multi_lot: false,
      region: JSON.stringify(newLotForm.value.region),
      manager_ids: newLotForm.value.manager_ids,
    }
    const created = await createProject(lotData)
    ElMessage.success('标段创建成功')
    showCreateLotDialog.value = false
    newLotForm.value = { project_name: '', bidding_unit_id: null, region: [], manager_ids: [] }
    await loadLots()
    if (lotList.value.length) {
      activeLotTab.value = String(lotList.value[lotList.value.length - 1].id)
      await switchToLot(lotList.value[lotList.value.length - 1].id)
    }
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '创建失败')
  } finally {
    creatingLot.value = false
  }
}

const isNew = computed(() => route.params.id === 'new')

// ---- Status computed ----
const statusOrder = ['跟进中', '已发公告', '未报名', '已报名', '准备投标', '已投标', '已中标', '未中标', '已流标', '已放弃']
function statusGte(current, target) {
  return statusOrder.indexOf(current) >= statusOrder.indexOf(target)
}

const project = ref({})
const isFollowing = computed(() => project.value.status === '跟进中')
const isPublished = computed(() => project.value.status === '已发公告')
const isNotRegistered = computed(() => project.value.status === '未报名')
const isRegistered = computed(() => project.value.status === '已报名')
const isPreparing = computed(() => project.value.status === '准备投标')
const isAbandoned = computed(() => project.value.status === '已放弃')
const isMultiLotParent = computed(() => project.value.is_multi_lot === true)
const isMultiLotChild = computed(() => !isNew.value && projectForm.value.parent_project_id != null && project.value.parent_is_multi_lot === true && projectForm.value.bidding_type !== '入围分项')
const canAbandon = computed(() => ['跟进中', '已发公告', '未报名', '已报名', '准备投标', '已投标'].includes(project.value.status))
const showBidding = computed(() => !isNew.value && statusGte(project.value.status, '已发公告'))
const showBid = computed(() => !isNew.value && statusGte(project.value.status, '准备投标'))
const showResult = computed(() => !isNew.value && statusGte(project.value.status, '已投标'))
const controlPriceType = computed(() => biddingForm.value.control_price_type || '金额')

const statusMap = {
  '跟进中': { label: '跟进中', type: 'info' },
  '已发公告': { label: '已发公告', type: 'primary' },
  '未报名': { label: '未报名', type: 'info' },
  '已报名': { label: '已报名', type: 'success' },
  '准备投标': { label: '准备投标', type: 'warning' },
  '已投标': { label: '已投标', type: 'primary' },
  '已中标': { label: '已中标', type: 'success' },
  '未中标': { label: '未中标', type: 'danger' },
  '已流标': { label: '已流标', type: 'warning' },
  '已放弃': { label: '已放弃', type: 'info' },
}
function statusLabel(s) { return statusMap[s]?.label || s }
function statusType(s) { return statusMap[s]?.type || 'info' }

const depositPaid = computed({
  get: () => bidForm.value.deposit_status === '已缴纳',
  set: (val) => { bidForm.value.deposit_status = val ? '已缴纳' : '未缴纳' }
})

const winningPriceLabel = computed(() => {
  const type = controlPriceType.value
  if (type === '金额') return '中标金额'
  if (type === '折扣率') return '中标折扣率'
  if (type === '下浮率') return '中标下浮率'
  return '中标价格'
})

const OUR_COMPANY_NAME = '浙江意诚检测有限公司'

// ---- Forms ----
const projectFormRef = ref(null)
const defaultProjectForm = { bidding_type: '', project_name: '', bidding_unit_id: null, region: [], manager_ids: [], description: '', parent_project_id: null, is_multi_lot: false }
const projectForm = ref({ ...defaultProjectForm })
const projectRules = {
  bidding_type: [{ required: true, message: '请选择招标类型', trigger: 'change' }],
  project_name: [{ required: true, message: '请输入项目名称', trigger: 'blur' }],
}

const defaultBiddingForm = {
  agency_id: null, publish_platform_id: null, tags: [],
  registration_deadline: null, bid_deadline: null, budget_amount: 0,
  control_price_type: '金额', control_price_upper: null, control_price_lower: null,
  is_prequalification: false, bid_specialist_id: null, bidding_notes: '',
  is_registered: false,
}
const biddingForm = ref({ ...defaultBiddingForm })

const defaultBidForm = {
  partner_ids: [], bid_method: '独立', is_consortium_lead: true,
  has_deposit: false, deposit_status: '未缴纳', deposit_amount: 0,
  deposit_date: null, deposit_return_date: null, our_price: 0, bid_notes: '',
}
const bidForm = ref({ ...defaultBidForm })

const defaultResultForm = {
  competitors: [], scoring_details: [], result_deposit_status: null,
  is_won: false, is_bid_failed: false, winning_org_id: null, winning_org_ids: [], winning_price: null, winning_amount: null,
  lost_analysis: '', contract_number: '', contract_status: '无', contract_amount: 0, result_notes: '',
}
const resultForm = ref({ ...defaultResultForm })

// ---- Competitor helpers ----

function getOrgName(orgId) {
  return orgMap.value[orgId]?.name || '未知单位'
}

function isOurOrg(orgId) {
  const ourOrgId = getOurOrgId()
  return orgId === ourOrgId
}

function isOurEntry(comp) {
  const ourOrgId = getOurOrgId()
  return ourOrgId && comp.org_ids.includes(ourOrgId)
}

function getOurOrgId() {
  const org = Object.values(orgMap.value).find(o => o.name === OUR_COMPANY_NAME)
  return org ? org.id : null
}

// ---- Winning logic ----

const bidResultType = computed(() => {
  if (resultForm.value.is_bid_failed) return 'failed'
  if (resultForm.value.is_won) return 'won'
  // is_won=false 但状态还在已投标 → 视为未选择
  if (project.value.status === '已投标') return null
  return 'lost'
})

function handleBidResultChange(val) {
  if (val === 'won') {
    resultForm.value.is_won = true
    resultForm.value.is_bid_failed = false
  } else if (val === 'lost') {
    // 未中标不能手动点选，只能通过勾选其他参标单位中标自动触发
    return
  } else if (val === 'failed') {
    resultForm.value.is_won = false
    resultForm.value.is_bid_failed = true
    // 流标时取消所有中标勾选
    resultForm.value.competitors.forEach(c => { c.is_winning = false })
    deriveWinningOrgs()
  }
}

let _updatingFromWinning = false

function handleWinningChange(comp) {
  if (resultForm.value.is_bid_failed) return  // 流标时忽略
  const isPrequalification = biddingForm.value.is_prequalification
  if (!isPrequalification) {
    // 非入围标：单选行为
    if (comp.is_winning) {
      resultForm.value.competitors.forEach(c => { c.is_winning = false })
      comp.is_winning = true
    }
  }
  deriveWinningOrgs()
  // 联动 is_won（标志不立即重置，由 is_won watch 消费）
  _updatingFromWinning = true
  const ourOrgId = getOurOrgId()
  const winningEntries = resultForm.value.competitors.filter(c => c.is_winning)
  if (winningEntries.some(c => c.org_ids.includes(ourOrgId))) {
    resultForm.value.is_won = true
  } else if (winningEntries.length > 0) {
    resultForm.value.is_won = false
  } else {
    // 所有中标勾选都取消了 → 清除 is_won，回退已投标
    resultForm.value.is_won = false
  }
}

function deriveWinningOrgs() {
  resultForm.value.winning_org_ids = resultForm.value.competitors
    .filter(c => c.is_winning || c.is_shortlisted)
    .flatMap(c => c.org_ids)
}

// ---- Derived display for winning price/amount ----

const derivedWinningPriceDisplay = computed(() => {
  const winning = resultForm.value.competitors.find(c => c.is_winning)
  if (!winning) return '-'
  const price = winning.price
  if (!price) return '-'
  const type = controlPriceType.value
  if (type === '金额') return '-'
  return `${price}%`
})

const derivedWinningAmountDisplay = computed(() => {
  const winning = resultForm.value.competitors.find(c => c.is_winning)
  if (!winning || !winning.price) return '-'
  const type = controlPriceType.value
  const price = winning.price
  const upper = parseFloat(biddingForm.value.control_price_upper) || 0
  const budget = parseFloat(biddingForm.value.budget_amount) || 0
  if (type === '金额') return `¥${price.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
  if (type === '折扣率') {
    if (!upper || !budget) return '-'
    const amount = price / upper * budget
    return `¥${amount.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
  }
  if (type === '下浮率') {
    if (!upper || !budget) return '-'
    const amount = (1 - price / 100) / (1 - upper / 100) * budget
    return `¥${amount.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
  }
  return '-'
})

// ---- Add competitor ----

function addCompetitor() {
  resultForm.value.competitors.push({
    org_ids: [], price: 0, score: 0, is_shortlisted: false, is_winning: false, _editing: true,
  })
}

function syncOrgToMap(org) {
  // Sync OrgSelector's options into orgMap so getOrgName works
  if (org && org.id && !orgMap.value[org.id]) {
    orgMap.value[org.id] = org
  }
}

// ---- Parent project (入围分项关联入围标) ----

async function searchParentProjects(keyword) {
  try {
    const res = await getProjects({
      keyword: keyword || '',
      is_prequalification: true,
      status: '已中标',
      page_size: 20,
    })
    parentProjectOptions.value = (res.items || []).map(p => ({ id: p.id, project_name: p.project_name }))
  } catch { /* ignore */ }
}

async function handleParentProjectChange(parentId) {
  if (!parentId) {
    parentProjectName.value = ''
    return
  }
  // 找到选中的项目名称
  const found = parentProjectOptions.value.find(p => p.id === parentId)
  parentProjectName.value = found ? found.project_name : ''
  // 如果当前项目还没有参标单位，自动从父项目复制
  if (!resultForm.value.competitors.length && showResult.value) {
    await doSyncCompetitors()
  }
}

async function doSyncCompetitors() {
  if (!projectForm.value.parent_project_id) {
    ElMessage.warning('请先关联入围标项目')
    return
  }
  try {
    const updated = await syncCompetitors(route.params.id)
    // 更新本地的 competitors
    const rawComps = updated.competitors || []
    resultForm.value.competitors = rawComps.map(c => ({
      org_ids: c.org_ids || [],
      price: c.price || 0,
      score: c.score || 0,
      is_shortlisted: c.is_shortlisted || false,
      is_winning: c.is_winning || false,
    }))
    // 同步新增的 org 到 orgMap
    for (const c of rawComps) {
      if (c.org_names) {
        c.org_ids.forEach((oid, i) => {
          if (oid && !orgMap.value[oid] && c.org_names[i]) {
            orgMap.value[oid] = { id: oid, name: c.org_names[i] }
          }
        })
      }
    }
    ElMessage.success('参标单位已从父项目同步')
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '同步失败')
  }
}

function getExcludedOrgIds(currentIdx) {
  const ids = []
  resultForm.value.competitors.forEach((c, i) => {
    if (i !== currentIdx) {
      c.org_ids.forEach(id => { if (!ids.includes(id)) ids.push(id) })
    }
  })
  return ids
}

// 合作单位排除规则：联合体模式下排除参标单位已有的 org_ids；配合/陪标不排除
const partnerExcludeIds = computed(() => {
  if (bidForm.value.bid_method !== '联合体') return []
  const ids = []
  resultForm.value.competitors.forEach(c => {
    c.org_ids.forEach(id => { if (!ids.includes(id)) ids.push(id) })
  })
  return ids
})

// ---- ensureOurCompanyInCompetitors ----

function ensureOurCompanyInCompetitors() {
  const ourOrgId = getOurOrgId()
  if (!ourOrgId || !showResult.value) return

  const ourEntry = resultForm.value.competitors.find(c => c.org_ids.includes(ourOrgId))
  const isConsortium = bidForm.value.bid_method === '联合体'
  const expectedOrgIds = isConsortium
    ? [ourOrgId, ...(bidForm.value.partner_ids || [])]
    : [ourOrgId]

  if (ourEntry) {
    // Update org_ids based on current bid_method
    ourEntry.org_ids = expectedOrgIds
    return
  }

  // Create new entry
  resultForm.value.competitors.push({
    org_ids: expectedOrgIds,
    price: bidForm.value.our_price || 0, score: 0,
    is_shortlisted: false, is_winning: false,
  })
}

// ---- Watchers ----

watch(() => resultForm.value.is_won, (newVal) => {
  // 跳过由 handleWinningChange 触发的更新，避免循环
  if (_updatingFromWinning) {
    _updatingFromWinning = false
    return
  }
  if (newVal === null) return  // 未选择，不操作
  const ourOrgId = getOurOrgId()
  if (!ourOrgId) return
  const ourComp = resultForm.value.competitors.find(c => c.org_ids.includes(ourOrgId))
  if (newVal) {
    // 已中标：自动勾选我方条目（单选行为）
    resultForm.value.competitors.forEach(c => { c.is_winning = false })
    if (ourComp) ourComp.is_winning = true
  } else {
    // 未中标：取消所有勾选
    resultForm.value.competitors.forEach(c => { c.is_winning = false })
  }
  deriveWinningOrgs()
})

watch(() => bidForm.value.our_price, (newPrice) => {
  const ourOrgId = getOurOrgId()
  if (!ourOrgId) return
  const ourComp = resultForm.value.competitors.find(c => c.org_ids.includes(ourOrgId))
  if (ourComp) ourComp.price = newPrice
})

watch(() => bidForm.value.partner_ids, () => {
  ensureOurCompanyInCompetitors()
}, { deep: true })

watch(() => bidForm.value.bid_method, (newVal) => {
  // 切换为非联合体时清空合作单位，联动参标单位更新
  if (newVal !== '联合体') {
    bidForm.value.partner_ids = []
  }
  ensureOurCompanyInCompetitors()
  deriveWinningOrgs()
})

watch(() => bidForm.value.has_deposit, (newVal) => {
  if (newVal && bidForm.value.deposit_status === '已缴纳' && !resultForm.value.result_deposit_status) {
    resultForm.value.result_deposit_status = '未收回'
  }
})

// ---- Helpers ----
function parseJson(val, fallback = []) {
  if (Array.isArray(val)) return val
  if (typeof val === 'string') { try { return JSON.parse(val) } catch { return fallback } }
  return fallback
}

function formatRegionDisplay(region) {
  if (!region || !region.length) return ''
  return Array.isArray(region) ? region.join(' ') : region
}

function getManagerName(mid) {
  // managers are not stored in a local map; use the project's enriched data
  const idx = (projectForm.value.manager_ids || []).indexOf(mid)
  if (idx >= 0 && project.value.manager_names && project.value.manager_names[idx]) {
    return project.value.manager_names[idx]
  }
  return ''
}

// ---- Load ----
async function loadProject() {
  if (isNew.value) return
  try {
    const data = await getProject(route.params.id)
    project.value = data

    // Fill project form
    let region = []
    if (data.region) { try { region = JSON.parse(data.region) } catch { region = [] } }
    let managerIds = data.manager_ids || []
    if (typeof managerIds === 'string') { try { managerIds = JSON.parse(managerIds) } catch { managerIds = [] } }
    projectForm.value = {
      bidding_type: data.bidding_type, project_name: data.project_name,
      bidding_unit_id: data.bidding_unit_id, region, manager_ids: managerIds,
      description: data.description || '',
      parent_project_id: data.parent_project_id || null,
      is_multi_lot: data.is_multi_lot || false,
    }
    parentProjectName.value = data.parent_project_name || ''
    if (data.parent_project_id) {
      // 预加载父项目选项，确保 select 能显示名称
      parentProjectOptions.value = [{ id: data.parent_project_id, project_name: data.parent_project_name || `项目 #${data.parent_project_id}` }]
    }

    // Fill bidding form
    biddingForm.value = {
      agency_id: data.agency_id, publish_platform_id: data.publish_platform_id,
      tags: parseJson(data.tags, []), registration_deadline: data.registration_deadline,
      bid_deadline: data.bid_deadline, budget_amount: data.budget_amount || 0,
      control_price_type: data.control_price_type || '金额',
      control_price_upper: data.control_price_upper, control_price_lower: data.control_price_lower,
      is_prequalification: data.is_prequalification || false,
      bid_specialist_id: data.bid_specialist_id, bidding_notes: data.bidding_notes || '',
      is_registered: data.is_registered || (statusGte(data.status, '准备投标') && !!data.registration_deadline),
    }

    // Fill bid form
    bidForm.value = {
      partner_ids: parseJson(data.partner_ids, []), bid_method: data.bid_method || '独立',
      is_consortium_lead: data.is_consortium_lead !== false,
      has_deposit: data.has_deposit || false,
      deposit_status: data.deposit_status || '无', deposit_amount: data.deposit_amount || 0,
      deposit_date: data.deposit_date, deposit_return_date: data.deposit_return_date,
      our_price: data.our_price || 0, bid_notes: data.bid_notes || '',
    }

    // Fill result form (use _updatingFromWinning to prevent watcher interference)
    _updatingFromWinning = true
    const rawCompetitors = parseJson(data.competitors, [])
    resultForm.value = {
      competitors: rawCompetitors.map(c => ({
        org_ids: c.org_ids || (c.org_id ? [c.org_id] : []),
        price: c.price || 0,
        score: c.score || 0,
        is_shortlisted: c.is_shortlisted || false,
        is_winning: c.is_winning || false,
      })),
      scoring_details: parseJson(data.scoring_details, []),
      result_deposit_status: data.result_deposit_status || (data.has_deposit && data.deposit_status === '已缴纳' && statusGte(data.status, '已投标') ? '未收回' : null),
      is_won: data.is_won || false,
      is_bid_failed: data.is_bid_failed || false,
      winning_org_id: data.winning_org_id,
      winning_org_ids: parseJson(data.winning_org_ids, []),
      winning_price: data.winning_price, winning_amount: data.winning_amount,
      lost_analysis: data.lost_analysis || '', contract_number: data.contract_number || '',
      contract_status: data.contract_status || '无', contract_amount: data.contract_amount || 0,
      result_notes: data.result_notes || '',
    }
    // Reset flag after next tick so watcher processes normally from here on
    await nextTick()
    _updatingFromWinning = false
  } catch {
    ElMessage.error('项目不存在')
    router.push('/projects')
  }
  ensureOurCompanyInCompetitors()
  if (isMultiLotParent.value) {
    await loadLots()
  }
}

async function loadUsers() {
  try {
    const res = await getUsers()
    users.value = res.items || res
  } catch { /* ignore */ }
}

async function loadOrgNames() {
  try {
    const res = await getOrganizations({ page_size: 500 })
    for (const org of (res.items || [])) {
      orgMap.value[org.id] = org
    }
  } catch { /* ignore */ }
}

// ---- Save ----
function collectSaveData() {
  const data = {
    ...projectForm.value,
    region: JSON.stringify(projectForm.value.region),
    manager_ids: projectForm.value.manager_ids,
  }
  if (showBidding.value) {
    Object.assign(data, { ...biddingForm.value, tags: biddingForm.value.tags })
  }
  if (showBid.value) {
    Object.assign(data, { ...bidForm.value, partner_ids: bidForm.value.partner_ids })
  }
  if (showResult.value) {
    Object.assign(data, {
      ...resultForm.value,
      competitors: resultForm.value.competitors.map(c => ({
        org_ids: c.org_ids, price: c.price, score: c.score,
        is_shortlisted: c.is_shortlisted, is_winning: c.is_winning,
      })),
      scoring_details: resultForm.value.scoring_details,
    })
    // 始终发送 is_won/is_bid_failed，让后端根据中标勾选情况推导状态
    // 无中标勾选时后端会自动回退到已投标
  }
  return data
}

async function handleSave() {
  if (isNew.value) {
    const valid = await projectFormRef.value.validate().catch(() => false)
    if (!valid) return
  }
  saving.value = true
  try {
    const data = collectSaveData()
    if (isNew.value) {
      const created = await createProject(data)
      ElMessage.success('创建成功')
      await router.replace(`/projects/${created.id}`)
      await loadProject()
    } else {
      await updateProject(route.params.id, data)
      ElMessage.success('保存成功')
      await loadProject()
    }
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '操作失败')
  } finally {
    saving.value = false
  }
}

// ---- Flow handlers ----
async function handlePublish() {
  try {
    await ElMessageBox.confirm('确认已发布招标公告？将自动保存当前信息。', '确认')
    saving.value = true
    const data = collectSaveData()
    await updateProject(route.params.id, data)
    await publishProject(route.params.id)
    ElMessage.success('发布成功')
    await loadProject()
  } catch (err) {
    if (err !== 'cancel') ElMessage.error(err.response?.data?.detail || '发布失败')
  } finally {
    saving.value = false
  }
}

async function handlePrepare() {
  try {
    await ElMessageBox.confirm('确认准备投标？将自动保存当前信息。', '确认')
    saving.value = true
    const data = collectSaveData()
    await updateProject(route.params.id, data)
    await prepareProject(route.params.id)
    ElMessage.success('进入准备投标')
    await loadProject()
  } catch (err) {
    if (err !== 'cancel') ElMessage.error(err.response?.data?.detail || '操作失败')
  } finally {
    saving.value = false
  }
}

async function handleSubmit() {
  try {
    await ElMessageBox.confirm('确认提交投标？将自动保存当前信息。', '确认')
    saving.value = true
    const data = collectSaveData()
    await updateProject(route.params.id, data)
    await submitProject(route.params.id)
    ElMessage.success('已提交投标')
    await loadProject()
  } catch (err) {
    if (err !== 'cancel') ElMessage.error(err.response?.data?.detail || '操作失败')
  } finally {
    saving.value = false
  }
}

async function handleAbandon() {
  try {
    await abandonProject(route.params.id, abandonReason.value)
    ElMessage.success('已放弃')
    showAbandonDialog.value = false
    await loadProject()
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '操作失败')
  }
}

onMounted(async () => {
  await Promise.all([loadOrgNames(), loadUsers()])
  await loadProject()
  if (isMultiLotParent.value) {
    await loadLots()
  }
})
</script>

<style scoped>
.detail-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.detail-grid > .el-card {
  /* Ensure cards in the grid stretch properly */
  min-width: 0;
}

/* When only 1 card is visible (new project), don't waste space */
.detail-grid:has(> .el-card:only-child) {
  grid-template-columns: 1fr;
}
</style>
