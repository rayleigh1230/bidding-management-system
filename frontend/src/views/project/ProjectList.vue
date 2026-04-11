<template>
  <div>
    <!-- 快捷筛选按钮 -->
    <div style="display: flex; gap: 8px; margin-bottom: 12px; flex-wrap: wrap">
      <el-button :type="activeStatus === '' ? 'primary' : ''" @click="setStatus('')">全部</el-button>
      <el-button :type="activeStatus === '跟进中' ? 'primary' : ''" @click="setStatus('跟进中')">跟进中</el-button>
      <el-button :type="activeStatus === '已发公告' ? 'primary' : ''" @click="setStatus('已发公告')">已发公告</el-button>
      <el-button :type="activeStatus === '未报名' ? 'primary' : ''" @click="setStatus('未报名')">未报名</el-button>
      <el-button :type="activeStatus === '已报名' ? 'primary' : ''" @click="setStatus('已报名')">已报名</el-button>
      <el-button :type="activeStatus === '准备投标' ? 'primary' : ''" @click="setStatus('准备投标')">准备投标</el-button>
      <el-button :type="activeStatus === '已投标' ? 'primary' : ''" @click="setStatus('已投标')">已投标</el-button>
      <el-button :type="activeStatus === '已中标' ? 'success' : ''" @click="setStatus('已中标')">已中标</el-button>
      <el-button :type="activeStatus === '未中标' ? 'danger' : ''" @click="setStatus('未中标')">未中标</el-button>
      <el-button :type="activeStatus === '已流标' ? 'warning' : ''" @click="setStatus('已流标')">已流标</el-button>
    </div>

    <div style="display: flex; justify-content: space-between; margin-bottom: 16px; flex-wrap: wrap; gap: 8px">
      <div style="display: flex; gap: 8px; flex-wrap: wrap; align-items: center">
        <el-dropdown trigger="click" @command="v => { keywordMatch = v; loadData() }">
          <el-button size="default" style="padding: 8px 10px">{{ keywordMatch === 'fuzzy' ? '模糊' : '精确' }}</el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="fuzzy">模糊匹配</el-dropdown-item>
              <el-dropdown-item command="exact">精确匹配</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
        <el-input v-model="filters.keyword" placeholder="搜索项目名称" clearable style="width: 200px" @clear="loadData" @keyup.enter="loadData" />
        <el-select v-model="filters.bidding_type" placeholder="招标类型" clearable style="width: 140px" @change="loadData">
          <el-option label="公开招标" value="公开招标" />
          <el-option label="邀请招标" value="邀请招标" />
          <el-option label="中介超市" value="中介超市" />
          <el-option label="入围分项" value="入围分项" />
        </el-select>
        <el-button @click="loadData"><el-icon><Search /></el-icon> 搜索</el-button>
        <el-link type="primary" :underline="false" @click="showAdvanced = !showAdvanced" style="font-size: 13px">
          高级搜索 <el-icon style="margin-left: 2px"><ArrowDown v-if="!showAdvanced" /><ArrowUp v-else /></el-icon>
        </el-link>
      </div>
      <div style="display: flex; gap: 8px; align-items: center">
        <el-popover placement="bottom-end" :width="280" trigger="click">
          <template #reference>
            <el-button><el-icon><Setting /></el-icon> 列设置</el-button>
          </template>
          <div style="max-height: 400px; overflow-y: auto; padding: 4px 0">
            <el-checkbox-group v-model="selectedColumnKeys">
              <div v-for="col in configurableColumns" :key="col.key" style="padding: 2px 0">
                <el-checkbox :value="col.key">{{ col.label }}</el-checkbox>
              </div>
            </el-checkbox-group>
          </div>
          <div style="border-top: 1px solid var(--el-border-color-lighter); padding-top: 8px; margin-top: 4px; text-align: right">
            <el-button size="small" @click="resetColumns">恢复默认</el-button>
          </div>
        </el-popover>
        <el-button type="primary" @click="$router.push('/projects/new')"><el-icon><Plus /></el-icon> 新增项目</el-button>
      </div>
    </div>

    <!-- 高级搜索面板 -->
    <transition name="el-zoom-in-top">
      <div v-if="showAdvanced" style="margin-bottom: 12px; padding: 16px; background: var(--el-fill-color-lighter); border-radius: 6px;">
        <el-row :gutter="16">
          <el-col :xs="24" :sm="12" :md="8" style="margin-bottom: 12px">
            <div style="font-size: 12px; color: #909399; margin-bottom: 4px">地区</div>
            <RegionCascader v-model="filters.region" style="width: 100%" />
          </el-col>
          <el-col :xs="24" :sm="12" :md="8" style="margin-bottom: 12px">
            <div style="font-size: 12px; color: #909399; margin-bottom: 4px">招标单位</div>
            <OrgSelector v-model="filters.bidding_unit_id" :excludeOurs="false" style="width: 100%" />
          </el-col>
          <el-col :xs="24" :sm="12" :md="8" style="margin-bottom: 12px">
            <div style="font-size: 12px; color: #909399; margin-bottom: 4px">代理单位</div>
            <OrgSelector v-model="filters.agency_id" :excludeOurs="false" style="width: 100%" />
          </el-col>
          <el-col :xs="24" :sm="12" :md="8" style="margin-bottom: 12px">
            <div style="font-size: 12px; color: #909399; margin-bottom: 4px">负责人</div>
            <ManagerSelector v-model="filters.manager_id" style="width: 100%" />
          </el-col>
          <el-col :xs="24" :sm="12" :md="8" style="margin-bottom: 12px">
            <div style="font-size: 12px; color: #909399; margin-bottom: 4px">发布平台</div>
            <PlatformSelector v-model="filters.publish_platform_id" style="width: 100%" />
          </el-col>
          <el-col :xs="24" :sm="12" :md="8" style="margin-bottom: 12px">
            <div style="font-size: 12px; color: #909399; margin-bottom: 4px">合作单位</div>
            <OrgSelector v-model="filters.partner_id" :excludeOurs="false" style="width: 100%" />
          </el-col>
          <el-col :xs="24" :sm="12" :md="8" style="margin-bottom: 12px">
            <div style="font-size: 12px; color: #909399; margin-bottom: 4px">投标方式</div>
            <el-select v-model="filters.bid_method" placeholder="全部" clearable style="width: 100%">
              <el-option label="独立" value="独立" />
              <el-option label="联合体" value="联合体" />
              <el-option label="配合" value="配合" />
              <el-option label="陪标" value="陪标" />
            </el-select>
          </el-col>
          <el-col :xs="24" :sm="12" :md="8" style="margin-bottom: 12px">
            <div style="font-size: 12px; color: #909399; margin-bottom: 4px">是否入围标</div>
            <el-select v-model="filters.is_prequalification" placeholder="全部" clearable style="width: 100%">
              <el-option label="是" :value="true" />
              <el-option label="否" :value="false" />
            </el-select>
          </el-col>
          <el-col :xs="24" :sm="12" :md="8" style="margin-bottom: 12px">
            <div style="font-size: 12px; color: #909399; margin-bottom: 4px">开标时间</div>
            <el-date-picker v-model="bidDeadlineDateRange" type="daterange" range-separator="至" start-placeholder="开始" end-placeholder="结束" value-format="YYYY-MM-DD" style="width: 100%" />
          </el-col>
          <el-col :xs="24" :sm="12" :md="8" style="margin-bottom: 12px">
            <div style="font-size: 12px; color: #909399; margin-bottom: 4px">预算金额（万元）</div>
            <div style="display: flex; align-items: center; gap: 4px">
              <el-input-number v-model="filters.budget_min" :controls="false" placeholder="最低" style="width: 50%" />
              <span style="color: #c0c4cc">~</span>
              <el-input-number v-model="filters.budget_max" :controls="false" placeholder="最高" style="width: 50%" />
            </div>
          </el-col>
          <el-col :xs="24" :sm="12" :md="8" style="margin-bottom: 12px">
            <div style="font-size: 12px; color: #909399; margin-bottom: 4px">中标金额（万元）</div>
            <div style="display: flex; align-items: center; gap: 4px">
              <el-input-number v-model="filters.winning_amount_min" :controls="false" placeholder="最低" style="width: 50%" />
              <span style="color: #c0c4cc">~</span>
              <el-input-number v-model="filters.winning_amount_max" :controls="false" placeholder="最高" style="width: 50%" />
            </div>
          </el-col>
        </el-row>
        <div style="text-align: right; margin-top: 4px">
          <el-button @click="resetAdvancedFilters">重置</el-button>
        </div>
      </div>
    </transition>

    <el-table :data="tableData" v-loading="loading" border stripe :header-cell-style="{ whiteSpace: 'nowrap' }">
      <template v-for="col in visibleColumns" :key="col.key">
        <!-- ID -->
        <el-table-column v-if="col.key === 'id'" prop="id" label="ID" width="50" />
        <!-- 项目名称（唯一弹性列） -->
        <el-table-column v-else-if="col.key === 'project_name'" prop="project_name" label="项目名称" min-width="100" show-overflow-tooltip>
          <template #default="{ row }">
            <el-link type="primary" @click="$router.push(`/projects/${row.id}`)">{{ row.project_name }}</el-link>
          </template>
        </el-table-column>
        <!-- 状态 -->
        <el-table-column v-else-if="col.key === 'status'" prop="status" label="状态" width="80">
          <template #default="{ row }">
            <el-tag size="small" :type="statusType(row.status)">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <!-- 负责人 -->
        <el-table-column v-else-if="col.key === 'manager_names'" prop="manager_names" label="负责人" width="90" show-overflow-tooltip>
          <template #default="{ row }">{{ (row.manager_names || []).join(', ') || '-' }}</template>
        </el-table-column>
        <!-- 所属地区 -->
        <el-table-column v-else-if="col.key === 'region'" label="所属地区" width="110" show-overflow-tooltip>
          <template #default="{ row }">{{ formatRegion(row.region) }}</template>
        </el-table-column>
        <!-- 预算金额 -->
        <el-table-column v-else-if="col.key === 'budget_amount'" label="预算金额" width="100" show-overflow-tooltip>
          <template #default="{ row }">{{ row.budget_amount ? row.budget_amount.toLocaleString() + ' 元' : '-' }}</template>
        </el-table-column>
        <!-- 日期类字段 -->
        <el-table-column v-else-if="col.key === 'registration_deadline'" label="报名截止" width="100">
          <template #default="{ row }">{{ formatDate(row.registration_deadline) }}</template>
        </el-table-column>
        <el-table-column v-else-if="col.key === 'bid_deadline'" label="投标截止" width="100">
          <template #default="{ row }">{{ formatDate(row.bid_deadline) }}</template>
        </el-table-column>
        <!-- 创建时间 -->
        <el-table-column v-else-if="col.key === 'created_at'" prop="created_at" label="创建时间" width="150">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <!-- 保证金状态 -->
        <el-table-column v-else-if="col.key === 'deposit_status_display'" label="保证金状态" width="90">
          <template #default="{ row }">
            <span v-if="!row.deposit_status_display || row.deposit_status_display === '无'" style="color: #999">无</span>
            <el-tag v-else-if="row.deposit_status_display === '未缴纳'" size="small" type="info">未缴纳</el-tag>
            <el-tag v-else-if="row.deposit_status_display === '已缴纳'" size="small" type="success">已缴纳</el-tag>
            <el-tag v-else-if="row.deposit_status_display === '未收回'" size="small" type="warning">未收回</el-tag>
            <el-tag v-else-if="row.deposit_status_display === '已收回'" size="small" type="success">已收回</el-tag>
          </template>
        </el-table-column>
        <!-- 保证金金额 -->
        <el-table-column v-else-if="col.key === 'deposit_amount'" label="保证金" width="100" show-overflow-tooltip>
          <template #default="{ row }">{{ row.deposit_amount ? row.deposit_amount.toLocaleString() + ' 元' : '-' }}</template>
        </el-table-column>
        <!-- 合作单位 -->
        <el-table-column v-else-if="col.key === 'partner_names'" label="合作单位" width="120" show-overflow-tooltip>
          <template #default="{ row }">{{ (row.partner_names || []).join(', ') || '-' }}</template>
        </el-table-column>
        <!-- 中标单位 -->
        <el-table-column v-else-if="col.key === 'winning_org_names'" label="中标单位" width="140" show-overflow-tooltip>
          <template #default="{ row }">{{ (row.winning_org_names || []).join(', ') || '-' }}</template>
        </el-table-column>
        <!-- 操作 -->
        <el-table-column v-else-if="col.key === 'actions'" label="操作" width="100">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="$router.push(`/projects/${row.id}`)">查看</el-button>
            <el-popconfirm title="确定删除？" @confirm="handleDelete(row.id)">
              <template #reference>
                <el-button link type="danger" size="small">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
        <!-- 通用文本列 -->
        <el-table-column v-else :prop="col.prop || col.key" :label="col.label" :width="col.width" show-overflow-tooltip>
          <template #default="{ row }">{{ row[col.prop || col.key] || '-' }}</template>
        </el-table-column>
      </template>
    </el-table>

    <div style="display: flex; justify-content: flex-end; margin-top: 16px">
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        layout="total, prev, pager, next"
        @current-change="loadData"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, Plus, Setting, ArrowDown, ArrowUp } from '@element-plus/icons-vue'
import { getProjects, deleteProject } from '../../api/project'
import RegionCascader from '../../components/RegionCascader.vue'
import ManagerSelector from '../../components/ManagerSelector.vue'
import PlatformSelector from '../../components/PlatformSelector.vue'
import OrgSelector from '../../components/OrgSelector.vue'

const STORAGE_PREFIX = 'project_list_columns'

// ---- 列配置 ----
// 原则：只有 project_name 是弹性列（无固定 width），其余都用 width 固定
// 表格总宽 = 容器宽度，project_name 自动伸缩填充剩余空间
const allColumns = [
  { key: 'id', label: 'ID', width: 50, alwaysShow: false, defaultShow: true },
  { key: 'project_name', label: '项目名称', alwaysShow: true, defaultShow: true },
  { key: 'bidding_type', label: '招标类型', width: 85, alwaysShow: false, defaultShow: true, prop: 'bidding_type' },
  { key: 'bidding_unit_name', label: '招标单位', width: 120, alwaysShow: false, defaultShow: true, prop: 'bidding_unit_name' },
  { key: 'manager_names', label: '负责人', width: 90, alwaysShow: false, defaultShow: true },
  { key: 'status', label: '状态', width: 80, alwaysShow: false, defaultShow: true },
  { key: 'region', label: '所属地区', width: 110, alwaysShow: false, defaultShow: false },
  { key: 'agency_name', label: '代理单位', width: 120, alwaysShow: false, defaultShow: false, prop: 'agency_name' },
  { key: 'platform_name', label: '发布平台', width: 120, alwaysShow: false, defaultShow: false, prop: 'platform_name' },
  { key: 'registration_deadline', label: '报名截止', width: 100, alwaysShow: false, defaultShow: false },
  { key: 'bid_deadline', label: '投标截止', width: 100, alwaysShow: false, defaultShow: false },
  { key: 'budget_amount', label: '预算金额', width: 100, alwaysShow: false, defaultShow: false },
  { key: 'control_price_type', label: '控制价类型', width: 100, alwaysShow: false, defaultShow: false, prop: 'control_price_type' },
  { key: 'partner_names', label: '合作单位', width: 120, alwaysShow: false, defaultShow: false },
  { key: 'bid_method', label: '投标方式', width: 90, alwaysShow: false, defaultShow: false, prop: 'bid_method' },
  { key: 'our_price_display', label: '我方报价', width: 90, alwaysShow: false, defaultShow: true, prop: 'our_price_display' },
  { key: 'deposit_status_display', label: '保证金状态', width: 90, alwaysShow: false, defaultShow: true },
  { key: 'deposit_amount', label: '保证金', width: 100, alwaysShow: false, defaultShow: false },
  { key: 'winning_org_names', label: '中标单位', width: 140, alwaysShow: false, defaultShow: true },
  { key: 'winning_amount_display', label: '中标金额', width: 100, alwaysShow: false, defaultShow: false, prop: 'winning_amount_display' },
  { key: 'created_at', label: '创建时间', width: 150, alwaysShow: false, defaultShow: true },
  { key: 'actions', label: '操作', width: 100, alwaysShow: true, defaultShow: true },
]

const configurableColumns = computed(() => allColumns.filter(c => !c.alwaysShow))

const defaultKeys = allColumns.filter(c => c.defaultShow).map(c => c.key)

function getStorageKey() {
  return `${STORAGE_PREFIX}_${activeStatus.value || 'all'}`
}

function loadColumnConfig() {
  try {
    const saved = localStorage.getItem(getStorageKey())
    if (saved) return JSON.parse(saved)
  } catch { /* ignore */ }
  return [...defaultKeys]
}

const selectedColumnKeys = ref(loadColumnConfig())

function saveColumnConfig(keys) {
  localStorage.setItem(getStorageKey(), JSON.stringify(keys))
}

// 用 watch 确保任何变化都保存（比 @change 更可靠）
watch(selectedColumnKeys, (newKeys) => {
  saveColumnConfig(newKeys)
}, { deep: true })

function resetColumns() {
  selectedColumnKeys.value = [...defaultKeys]
}

const alwaysShowKeys = computed(() => allColumns.filter(c => c.alwaysShow).map(c => c.key))

const visibleColumns = computed(() => {
  const activeKeys = new Set([...selectedColumnKeys.value, ...alwaysShowKeys.value])
  return allColumns.filter(c => activeKeys.has(c.key))
})

// ---- 数据 ----
const tableData = ref([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const activeStatus = ref('')

const filters = reactive({
  keyword: '', status: '', bidding_type: '',
  region: [], manager_id: null, bidding_unit_id: null, agency_id: null,
  publish_platform_id: null, partner_id: null, bid_method: '',
  is_prequalification: null,
  bid_deadline_after: '', bid_deadline_before: '',
  budget_min: null, budget_max: null,
  winning_amount_min: null, winning_amount_max: null,
})
const keywordMatch = ref('fuzzy')
const showAdvanced = ref(false)
const bidDeadlineDateRange = ref(null)
let _initialized = false

const ADVANCED_STORAGE_KEY = 'project_list_advanced_filters'
const ADVANCED_OPEN_KEY = 'project_list_advanced_open'

function saveAdvancedState() {
  const state = {
    region: filters.region,
    manager_id: filters.manager_id,
    bidding_unit_id: filters.bidding_unit_id,
    agency_id: filters.agency_id,
    publish_platform_id: filters.publish_platform_id,
    partner_id: filters.partner_id,
    bid_method: filters.bid_method,
    is_prequalification: filters.is_prequalification,
    bid_deadline_after: filters.bid_deadline_after,
    bid_deadline_before: filters.bid_deadline_before,
    budget_min: filters.budget_min,
    budget_max: filters.budget_max,
    winning_amount_min: filters.winning_amount_min,
    winning_amount_max: filters.winning_amount_max,
    keywordMatch: keywordMatch.value,
  }
  localStorage.setItem(ADVANCED_STORAGE_KEY, JSON.stringify(state))
}

function loadAdvancedState() {
  try {
    const saved = localStorage.getItem(ADVANCED_STORAGE_KEY)
    if (saved) return JSON.parse(saved)
  } catch { /* ignore */ }
  return null
}

function resetAdvancedFilters() {
  filters.region = []
  filters.manager_id = null
  filters.bidding_unit_id = null
  filters.agency_id = null
  filters.publish_platform_id = null
  filters.partner_id = null
  filters.bid_method = ''
  filters.is_prequalification = null
  filters.bid_deadline_after = ''
  filters.bid_deadline_before = ''
  filters.budget_min = null
  filters.budget_max = null
  filters.winning_amount_min = null
  filters.winning_amount_max = null
  bidDeadlineDateRange.value = null
  page.value = 1
  loadData()
}

// 监听高级筛选值变化 → 自动触发搜索
watch(
  () => [
    filters.region, filters.manager_id, filters.bidding_unit_id,
    filters.agency_id, filters.publish_platform_id, filters.partner_id,
    filters.bid_method, filters.is_prequalification,
    bidDeadlineDateRange.value,
    filters.budget_min, filters.budget_max,
    filters.winning_amount_min, filters.winning_amount_max,
  ],
  () => {
    if (!_initialized) return
    // 同步日期范围到 filters
    if (bidDeadlineDateRange.value) {
      filters.bid_deadline_after = bidDeadlineDateRange.value[0]
      filters.bid_deadline_before = bidDeadlineDateRange.value[1]
    } else {
      filters.bid_deadline_after = ''
      filters.bid_deadline_before = ''
    }
    page.value = 1
    loadData()
  },
  { deep: true }
)

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
function formatTime(t) { return t ? t.replace('T', ' ').slice(0, 16) : '-' }
function formatDate(d) { return d || '-' }
function formatRegion(r) {
  if (!r) return '-'
  try {
    const arr = typeof r === 'string' ? JSON.parse(r) : r
    return Array.isArray(arr) ? arr.join(' ') : r
  } catch { return r }
}

function setStatus(status) {
  activeStatus.value = status
  filters.status = status
  page.value = 1
  selectedColumnKeys.value = loadColumnConfig()
  loadData()
}

async function loadData() {
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize.value }
    // 基本筛选
    if (filters.keyword) { params.keyword = filters.keyword; params.keyword_match = keywordMatch.value }
    if (filters.status) params.status = filters.status
    if (filters.bidding_type) params.bidding_type = filters.bidding_type
    // 高级筛选
    if (filters.region && filters.region.length > 0) {
      params.region = filters.region[filters.region.length - 1]
    }
    if (filters.manager_id) params.manager_id = filters.manager_id
    if (filters.bidding_unit_id) params.bidding_unit_id = filters.bidding_unit_id
    if (filters.agency_id) params.agency_id = filters.agency_id
    if (filters.publish_platform_id) params.publish_platform_id = filters.publish_platform_id
    if (filters.partner_id) params.partner_id = filters.partner_id
    if (filters.bid_method) params.bid_method = filters.bid_method
    if (filters.is_prequalification !== null && filters.is_prequalification !== '') params.is_prequalification = filters.is_prequalification
    if (filters.bid_deadline_after) params.bid_deadline_after = filters.bid_deadline_after
    if (filters.bid_deadline_before) params.bid_deadline_before = filters.bid_deadline_before
    if (filters.budget_min != null) params.budget_min = filters.budget_min
    if (filters.budget_max != null) params.budget_max = filters.budget_max
    if (filters.winning_amount_min != null) params.winning_amount_min = filters.winning_amount_min
    if (filters.winning_amount_max != null) params.winning_amount_max = filters.winning_amount_max

    saveAdvancedState()
    const res = await getProjects(params)
    tableData.value = res.items
    total.value = res.total
  } finally {
    loading.value = false
  }
}

async function handleDelete(id) {
  try {
    await deleteProject(id)
    ElMessage.success('删除成功')
    loadData()
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '删除失败')
  }
}

onMounted(() => {
  // 恢复高级搜索展开状态
  try {
    const savedOpen = localStorage.getItem(ADVANCED_OPEN_KEY)
    if (savedOpen) showAdvanced.value = JSON.parse(savedOpen)
  } catch { /* ignore */ }
  // 恢复高级筛选值
  const saved = loadAdvancedState()
  if (saved) {
    if (saved.region) filters.region = saved.region
    if (saved.manager_id) filters.manager_id = saved.manager_id
    if (saved.bidding_unit_id) filters.bidding_unit_id = saved.bidding_unit_id
    if (saved.agency_id) filters.agency_id = saved.agency_id
    if (saved.publish_platform_id) filters.publish_platform_id = saved.publish_platform_id
    if (saved.partner_id) filters.partner_id = saved.partner_id
    if (saved.bid_method) filters.bid_method = saved.bid_method
    if (saved.is_prequalification !== undefined && saved.is_prequalification !== null) filters.is_prequalification = saved.is_prequalification
    if (saved.bid_deadline_after) filters.bid_deadline_after = saved.bid_deadline_after
    if (saved.bid_deadline_before) filters.bid_deadline_before = saved.bid_deadline_before
    if (saved.budget_min != null) filters.budget_min = saved.budget_min
    if (saved.budget_max != null) filters.budget_max = saved.budget_max
    if (saved.winning_amount_min != null) filters.winning_amount_min = saved.winning_amount_min
    if (saved.winning_amount_max != null) filters.winning_amount_max = saved.winning_amount_max
    if (saved.keywordMatch) keywordMatch.value = saved.keywordMatch
    if (saved.bid_deadline_after && saved.bid_deadline_before) {
      bidDeadlineDateRange.value = [saved.bid_deadline_after, saved.bid_deadline_before]
    }
  }
  _initialized = true
  loadData()
})

watch(showAdvanced, (val) => {
  localStorage.setItem(ADVANCED_OPEN_KEY, JSON.stringify(val))
})
</script>
