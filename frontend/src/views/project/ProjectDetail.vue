<template>
  <div>
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px">
      <el-page-header @back="$router.push('/projects')">
        <template #content>
          <span>{{ isNew ? '新增项目' : project.project_name }}</span>
          <el-tag v-if="!isNew" :type="statusType(project.status)" style="margin-left: 8px">{{ statusLabel(project.status) }}</el-tag>
        </template>
      </el-page-header>
    </div>

    <!-- 田字布局：4个卡片 -->
    <div class="detail-grid">
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
          <el-form-item label="项目名称" prop="project_name">
            <el-input v-model="projectForm.project_name" :disabled="!isNew && !isFollowing" />
          </el-form-item>
          <el-form-item label="招标单位">
            <OrgSelector v-model="projectForm.bidding_unit_id" :disabled="!isNew && !isFollowing" :exclude-ours style="width: 100%" />
          </el-form-item>
          <el-form-item label="项目负责人">
            <ManagerSelector v-model="projectForm.manager_ids" :multiple="true" :disabled="!isNew && !isFollowing" style="width: 100%" />
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
                <el-date-picker v-model="biddingForm.registration_deadline" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="投标截止">
                <el-date-picker v-model="biddingForm.bid_deadline" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
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
              <el-form-item label="是否入围标">
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
              <el-form-item label="投标状态">
                <el-select v-model="bidForm.bid_status" style="width: 100%">
                  <el-option label="未报名" value="未报名" />
                  <el-option label="已报名" value="已报名" />
                  <el-option label="已投标" value="已投标" />
                </el-select>
              </el-form-item>
            </el-col>
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
          <el-form-item label="合作单位">
            <OrgSelector v-model="bidForm.partner_ids" :multiple="true" :exclude-ours style="width: 100%" />
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
                <el-date-picker v-model="bidForm.deposit_date" type="date" value-format="YYYY-MM-DD" placeholder="缴纳日期" style="width: 160px" />
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
          <!-- 是否中标 -->
          <el-form-item label="是否中标">
            <el-radio-group v-model="resultForm.is_won">
              <el-radio :label="true">已中标</el-radio>
              <el-radio :label="false">未中标</el-radio>
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
              <el-checkbox v-model="comp.is_winning" @change="handleWinningChange(comp)">中标</el-checkbox>
              <!-- 删除按钮（我方条目不可删除） -->
              <el-button v-if="!isOurEntry(comp)" type="danger" link @click="resultForm.competitors.splice(idx, 1)"><el-icon><Delete /></el-icon></el-button>
            </div>
            <el-button type="primary" link @click="addCompetitor">+ 添加参标单位</el-button>
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
                <el-date-picker v-model="bidForm.deposit_return_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
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
          <template v-if="!resultForm.is_won">
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
        <el-button v-if="isFollowing" type="success" @click="handlePublish">已发公告</el-button>
        <el-button v-if="isPublished" type="warning" @click="handlePrepare">准备投标</el-button>
        <el-button v-if="isPreparing" type="primary" @click="handleSubmit">提交投标</el-button>
        <el-button v-if="canAbandon" type="danger" @click="showAbandonDialog = true">放弃</el-button>
      </template>
    </div>

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

const isNew = computed(() => route.params.id === 'new')

// ---- Status computed ----
const statusOrder = ['跟进中', '已发公告', '准备投标', '已投标', '已中标', '未中标', '已放弃']
function statusGte(current, target) {
  return statusOrder.indexOf(current) >= statusOrder.indexOf(target)
}

const project = ref({})
const isFollowing = computed(() => project.value.status === '跟进中')
const isPublished = computed(() => project.value.status === '已发公告')
const isPreparing = computed(() => project.value.status === '准备投标')
const isAbandoned = computed(() => project.value.status === '已放弃')
const canAbandon = computed(() => ['跟进中', '已发公告', '准备投标', '已投标'].includes(project.value.status))
const showBidding = computed(() => !isNew.value && statusGte(project.value.status, '已发公告'))
const showBid = computed(() => !isNew.value && statusGte(project.value.status, '准备投标'))
const showResult = computed(() => !isNew.value && statusGte(project.value.status, '已投标'))
const controlPriceType = computed(() => biddingForm.value.control_price_type || '金额')

const statusMap = {
  '跟进中': { label: '跟进中', type: 'info' },
  '已发公告': { label: '已发公告', type: 'primary' },
  '准备投标': { label: '准备投标', type: 'warning' },
  '已投标': { label: '已投标', type: 'primary' },
  '已中标': { label: '已中标', type: 'success' },
  '未中标': { label: '未中标', type: 'danger' },
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
const defaultProjectForm = { bidding_type: '', project_name: '', bidding_unit_id: null, region: [], manager_ids: [], description: '' }
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
}
const biddingForm = ref({ ...defaultBiddingForm })

const defaultBidForm = {
  partner_ids: [], bid_method: '独立', is_consortium_lead: true, bid_status: '未报名',
  has_deposit: false, deposit_status: '未缴纳', deposit_amount: 0,
  deposit_date: null, deposit_return_date: null, our_price: 0, bid_notes: '',
}
const bidForm = ref({ ...defaultBidForm })

const defaultResultForm = {
  competitors: [], scoring_details: [], result_deposit_status: null,
  is_won: false, winning_org_id: null, winning_org_ids: [], winning_price: null, winning_amount: null,
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

let _updatingFromWinning = false

function handleWinningChange(comp) {
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

function getExcludedOrgIds(currentIdx) {
  const ids = []
  resultForm.value.competitors.forEach((c, i) => {
    if (i !== currentIdx) {
      c.org_ids.forEach(id => { if (!ids.includes(id)) ids.push(id) })
    }
  })
  return ids
}

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
    }

    // Fill bidding form
    biddingForm.value = {
      agency_id: data.agency_id, publish_platform_id: data.publish_platform_id,
      tags: parseJson(data.tags, []), registration_deadline: data.registration_deadline,
      bid_deadline: data.bid_deadline, budget_amount: data.budget_amount || 0,
      control_price_type: data.control_price_type || '金额',
      control_price_upper: data.control_price_upper, control_price_lower: data.control_price_lower,
      is_prequalification: data.is_prequalification || false, bid_specialist_id: data.bid_specialist_id,
      bidding_notes: data.bidding_notes || '',
    }

    // Fill bid form
    bidForm.value = {
      partner_ids: parseJson(data.partner_ids, []), bid_method: data.bid_method || '独立',
      is_consortium_lead: data.is_consortium_lead !== false,
      bid_status: data.bid_status || '未报名', has_deposit: data.has_deposit || false,
      deposit_status: data.deposit_status || '无', deposit_amount: data.deposit_amount || 0,
      deposit_date: data.deposit_date, deposit_return_date: data.deposit_return_date,
      our_price: data.our_price || 0, bid_notes: data.bid_notes || '',
    }

    // Fill result form
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
      winning_org_id: data.winning_org_id,
      winning_org_ids: parseJson(data.winning_org_ids, []),
      winning_price: data.winning_price, winning_amount: data.winning_amount,
      lost_analysis: data.lost_analysis || '', contract_number: data.contract_number || '',
      contract_status: data.contract_status || '无', contract_amount: data.contract_amount || 0,
      result_notes: data.result_notes || '',
    }
  } catch {
    ElMessage.error('项目不存在')
    router.push('/projects')
  }
  await nextTick()
  ensureOurCompanyInCompetitors()
}

async function loadUsers() {
  try {
    const res = await getUsers()
    users.value = res.items || res
  } catch { /* ignore */ }
}

async function loadOrgNames() {
  try {
    const res = await getOrganizations({ page_size: 100 })
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
