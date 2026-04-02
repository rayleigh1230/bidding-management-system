<template>
  <div>
    <div style="display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap">
      <el-select v-model="filters.entity_type" placeholder="实体类型" clearable style="width: 140px" @change="loadData">
        <el-option label="项目" value="project" />
        <el-option label="招标信息" value="bidding_info" />
        <el-option label="投标信息" value="bid_info" />
        <el-option label="投标结果" value="bid_result" />
      </el-select>
      <el-select v-model="filters.action" placeholder="操作类型" clearable style="width: 140px" @change="loadData">
        <el-option label="创建" value="create" />
        <el-option label="更新" value="update" />
        <el-option label="删除" value="delete" />
        <el-option label="发布" value="publish" />
        <el-option label="放弃" value="abandon" />
      </el-select>
      <el-date-picker
        v-model="dateRange"
        type="daterange"
        range-separator="至"
        start-placeholder="开始日期"
        end-placeholder="结束日期"
        value-format="YYYY-MM-DD"
        style="width: 280px"
        @change="handleDateChange"
      />
    </div>

    <el-table :data="tableData" v-loading="loading" border stripe>
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="created_at" label="操作时间" width="170" />
      <el-table-column prop="username" label="操作人" width="100" />
      <el-table-column prop="action" label="操作类型" width="80">
        <template #default="{ row }">
          <el-tag size="small" :type="actionType(row.action)">{{ row.action }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="entity_type" label="实体类型" width="100" />
      <el-table-column prop="entity_id" label="实体ID" width="80" />
      <el-table-column prop="detail" label="详情" min-width="250" show-overflow-tooltip />
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
import { getLogs } from '../api/log'

const tableData = ref([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const dateRange = ref(null)

const filters = reactive({ entity_type: '', action: '' })

function actionType(action) {
  const map = { create: 'success', update: '', delete: 'danger', publish: 'warning', abandon: 'info' }
  return map[action] || ''
}

function handleDateChange(val) {
  if (val) {
    filters.start_date = val[0]
    filters.end_date = val[1]
  } else {
    filters.start_date = ''
    filters.end_date = ''
  }
  loadData()
}

async function loadData() {
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize.value }
    if (filters.entity_type) params.entity_type = filters.entity_type
    if (filters.action) params.action = filters.action
    if (filters.start_date) params.start_date = filters.start_date
    if (filters.end_date) params.end_date = filters.end_date
    const res = await getLogs(params)
    tableData.value = res.items
    total.value = res.total
  } finally {
    loading.value = false
  }
}

onMounted(() => loadData())
</script>
