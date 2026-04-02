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
          <el-link type="primary" @click="$router.push(`/biddings/${row.id}`)">{{ row.project_name }}</el-link>
        </template>
      </el-table-column>
      <el-table-column prop="agency_name" label="代理单位" min-width="150" show-overflow-tooltip />
      <el-table-column prop="platform_name" label="发布平台" width="120" />
      <el-table-column prop="registration_deadline" label="报名截止" width="110" />
      <el-table-column prop="bid_deadline" label="投标截止" width="110" />
      <el-table-column prop="budget_amount" label="预算金额" width="120">
        <template #default="{ row }">{{ row.budget_amount ? row.budget_amount.toLocaleString() : '-' }}</template>
      </el-table-column>
      <el-table-column prop="specialist_name" label="投标专员" width="100" />
      <el-table-column label="操作" width="100" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="$router.push(`/biddings/${row.id}`)">查看</el-button>
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
import { getBiddings } from '../../api/bidding'

const tableData = ref([])
const loading = ref(false)
const keyword = ref('')
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)

async function loadData() {
  loading.value = true
  try {
    const res = await getBiddings({ keyword: keyword.value, page: page.value, page_size: pageSize.value })
    tableData.value = res.items
    total.value = res.total
  } finally {
    loading.value = false
  }
}

onMounted(() => loadData())
</script>
