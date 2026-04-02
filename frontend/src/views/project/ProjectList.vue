<template>
  <div>
    <div style="display: flex; justify-content: space-between; margin-bottom: 16px; flex-wrap: wrap; gap: 8px">
      <div style="display: flex; gap: 8px; flex-wrap: wrap">
        <el-input v-model="filters.keyword" placeholder="搜索项目名称" clearable style="width: 200px" @clear="loadData" @keyup.enter="loadData" />
        <el-select v-model="filters.status" placeholder="项目状态" clearable style="width: 140px" @change="loadData">
          <el-option label="跟进中" value="跟进中" />
          <el-option label="已发公告" value="已发公告" />
          <el-option label="准备投标" value="准备投标" />
          <el-option label="已投标" value="已投标" />
          <el-option label="已中标" value="已中标" />
          <el-option label="未中标" value="未中标" />
          <el-option label="已放弃" value="已放弃" />
        </el-select>
        <el-select v-model="filters.bidding_type" placeholder="招标类型" clearable style="width: 140px" @change="loadData">
          <el-option label="公开招标" value="公开招标" />
          <el-option label="邀请招标" value="邀请招标" />
          <el-option label="中介超市" value="中介超市" />
          <el-option label="入围分项" value="入围分项" />
        </el-select>
        <el-button @click="loadData"><el-icon><Search /></el-icon> 搜索</el-button>
      </div>
      <el-button type="primary" @click="$router.push('/projects/new')"><el-icon><Plus /></el-icon> 新增项目</el-button>
    </div>

    <el-table :data="tableData" v-loading="loading" border stripe>
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="project_name" label="项目名称" min-width="200" show-overflow-tooltip>
        <template #default="{ row }">
          <el-link type="primary" @click="$router.push(`/projects/${row.id}`)">{{ row.project_name }}</el-link>
        </template>
      </el-table-column>
      <el-table-column prop="bidding_type" label="招标类型" width="80" />
      <el-table-column prop="bidding_unit_name" label="招标单位" min-width="150" show-overflow-tooltip />
      <el-table-column prop="manager_names" label="负责人" width="120">
        <template #default="{ row }">{{ (row.manager_names || []).join(', ') }}</template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="statusType(row.status)">{{ statusLabel(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="170">
        <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="140" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="$router.push(`/projects/${row.id}`)">查看</el-button>
          <el-popconfirm title="确定删除？" @confirm="handleDelete(row.id)">
            <template #reference>
              <el-button link type="danger">删除</el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
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
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, Plus } from '@element-plus/icons-vue'
import { getProjects, deleteProject } from '../../api/project'

const tableData = ref([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)

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
