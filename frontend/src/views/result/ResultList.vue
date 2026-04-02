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
          <el-link type="primary" @click="$router.push(`/results/${row.id}`)">{{ row.project_name }}</el-link>
        </template>
      </el-table-column>
      <el-table-column prop="our_price" label="我方报价" width="120">
        <template #default="{ row }">{{ row.our_price ? row.our_price.toLocaleString() : '-' }}</template>
      </el-table-column>
      <el-table-column prop="is_won" label="是否中标" width="100">
        <template #default="{ row }">
          <el-tag :type="row.is_won ? 'success' : 'danger'">{{ row.is_won ? '已中标' : '未中标' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="contract_status" label="合同状态" width="100" />
      <el-table-column prop="deposit_status" label="保证金状态" width="100" />
      <el-table-column prop="contract_amount" label="合同金额" width="120">
        <template #default="{ row }">{{ row.contract_amount ? row.contract_amount.toLocaleString() : '-' }}</template>
      </el-table-column>
      <el-table-column label="操作" width="100" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="$router.push(`/results/${row.id}`)">查看</el-button>
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
import { getResults } from '../../api/result'

const tableData = ref([])
const loading = ref(false)
const keyword = ref('')
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)

async function loadData() {
  loading.value = true
  try {
    const res = await getResults({ keyword: keyword.value, page: page.value, page_size: pageSize.value })
    tableData.value = res.items
    total.value = res.total
  } finally {
    loading.value = false
  }
}

onMounted(() => loadData())
</script>
