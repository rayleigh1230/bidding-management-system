<template>
  <div>
    <div style="display: flex; justify-content: space-between; margin-bottom: 16px">
      <el-input v-model="keyword" placeholder="搜索项目名称" clearable style="width: 300px" @clear="loadData" @keyup.enter="loadData">
        <template #append>
          <el-button @click="loadData"><el-icon><Search /></el-icon></el-button>
        </template>
      </el-input>
    </div>

    <el-table :data="tableData" v-loading="loading" border stripe>
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="project_name" label="项目名称" min-width="200" show-overflow-tooltip>
        <template #default="{ row }">
          <el-link type="primary" @click="$router.push(`/bids/${row.id}`)">{{ row.project_name }}</el-link>
        </template>
      </el-table-column>
      <el-table-column prop="bid_method" label="投标方式" width="100" />
      <el-table-column prop="bid_status" label="投标状态" width="100">
        <template #default="{ row }">
          <el-tag :type="bidStatusType(row.bid_status)">{{ row.bid_status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="deposit_status" label="保证金状态" width="100" />
      <el-table-column prop="partner_names" label="合作单位" min-width="150">
        <template #default="{ row }">{{ (row.partner_names || []).join(', ') || '-' }}</template>
      </el-table-column>
      <el-table-column label="操作" width="100" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="$router.push(`/bids/${row.id}`)">查看</el-button>
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
import { ref, onMounted } from 'vue'
import { Search } from '@element-plus/icons-vue'
import { getBids } from '../../api/bid'

const tableData = ref([])
const loading = ref(false)
const keyword = ref('')
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)

function bidStatusType(s) {
  if (s === '已投标') return 'success'
  if (s === '已报名') return ''
  if (s === '未报名') return 'info'
  return 'warning'
}

async function loadData() {
  loading.value = true
  try {
    const res = await getBids({ keyword: keyword.value, page: page.value, page_size: pageSize.value })
    tableData.value = res.items
    total.value = res.total
  } finally {
    loading.value = false
  }
}

onMounted(() => loadData())
</script>
