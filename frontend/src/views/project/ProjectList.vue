<template>
  <div>
    <!-- 快捷筛选按钮 -->
    <div style="display: flex; gap: 8px; margin-bottom: 12px; flex-wrap: wrap">
      <el-button :type="activeStatus === '' ? 'primary' : ''" @click="setStatus('')">全部</el-button>
      <el-button :type="activeStatus === '跟进中' ? 'primary' : ''" @click="setStatus('跟进中')">跟进中</el-button>
      <el-button :type="activeStatus === '已发公告' ? 'primary' : ''" @click="setStatus('已发公告')">已发公告</el-button>
      <el-button :type="activeStatus === '准备投标' ? 'primary' : ''" @click="setStatus('准备投标')">准备投标</el-button>
      <el-button :type="activeStatus === '已投标' ? 'primary' : ''" @click="setStatus('已投标')">已投标</el-button>
      <el-button :type="activeStatus === '已中标' ? 'success' : ''" @click="setStatus('已中标')">已中标</el-button>
      <el-button :type="activeStatus === '未中标' ? 'danger' : ''" @click="setStatus('未中标')">未中标</el-button>
    </div>

    <div style="display: flex; justify-content: space-between; margin-bottom: 16px; flex-wrap: wrap; gap: 8px">
      <div style="display: flex; gap: 8px; flex-wrap: wrap">
        <el-input v-model="filters.keyword" placeholder="搜索项目名称" clearable style="width: 200px" @clear="loadData" @keyup.enter="loadData" />
        <el-select v-model="filters.bidding_type" placeholder="招标类型" clearable style="width: 140px" @change="loadData">
          <el-option label="公开招标" value="公开招标" />
          <el-option label="邀请招标" value="邀请招标" />
          <el-option label="中介超市" value="中介超市" />
          <el-option label="入围分项" value="入围分项" />
        </el-select>
        <el-button @click="loadData"><el-icon><Search /></el-icon> 搜索</el-button>
      </div>
      <div style="display: flex; gap: 8px; align-items: center">
        <el-popover placement="bottom-end" :width="280" trigger="click">
          <template #reference>
            <el-button><el-icon><Setting /></el-icon> 列设置</el-button>
          </template>
          <div style="max-height: 400px; overflow-y: auto; padding: 4px 0">
            <el-checkbox-group v-model="selectedColumnKeys" @change="saveColumnConfig">
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
          <template #default="{ row }">{{ (row.manager_names || []).join(', ') }}</template>
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
        <!-- 是否中标 -->
        <el-table-column v-else-if="col.key === 'is_won'" label="是否中标" width="80">
          <template #default="{ row }">
            <el-tag v-if="row.is_won === true" size="small" type="success">已中标</el-tag>
            <el-tag v-else-if="row.is_won === false && row.status !== '已投标'" size="small" type="danger">未中标</el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <!-- 合作单位 -->
        <el-table-column v-else-if="col.key === 'partner_names'" label="合作单位" width="120" show-overflow-tooltip>
          <template #default="{ row }">{{ (row.partner_names || []).join(', ') || '-' }}</template>
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
        <el-table-column v-else :prop="col.prop || col.key" :label="col.label" :width="col.width" show-overflow-tooltip />
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
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, Plus, Setting } from '@element-plus/icons-vue'
import { getProjects, deleteProject } from '../../api/project'

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
  { key: 'bid_status', label: '投标状态', width: 90, alwaysShow: false, defaultShow: false, prop: 'bid_status' },
  { key: 'our_price_display', label: '我方报价', width: 90, alwaysShow: false, defaultShow: true, prop: 'our_price_display' },
  { key: 'is_won', label: '是否中标', width: 80, alwaysShow: false, defaultShow: false },
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

function resetColumns() {
  selectedColumnKeys.value = [...defaultKeys]
  saveColumnConfig(selectedColumnKeys.value)
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

const filters = reactive({ keyword: '', status: '', bidding_type: '' })

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
function formatTime(t) { return t ? t.replace('T', ' ').slice(0, 16) : '' }
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
    const res = await getProjects({ ...filters, page: page.value, page_size: pageSize.value })
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

onMounted(() => loadData())
</script>
