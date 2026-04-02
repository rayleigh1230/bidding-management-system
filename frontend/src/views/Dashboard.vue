<template>
  <div v-loading="loading">
    <!-- 待办提醒 -->
    <el-row :gutter="16" style="margin-bottom: 16px">
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header>
            <div style="display: flex; align-items: center; gap: 8px">
              <el-icon style="color: #e6a23c"><Bell /></el-icon>
              <span>本周截止投标</span>
            </div>
          </template>
          <el-table v-if="overview.upcoming_deadlines?.length" :data="overview.upcoming_deadlines" size="small">
            <el-table-column prop="project_name" label="项目名称" show-overflow-tooltip />
            <el-table-column prop="bid_deadline" label="截止日期" width="110" />
            <el-table-column prop="budget_amount" label="预算金额" width="110">
              <template #default="{ row }">{{ row.budget_amount ? row.budget_amount.toLocaleString() : '-' }}</template>
            </el-table-column>
          </el-table>
          <el-empty v-else description="暂无即将截止的投标" :image-size="40" />
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header>
            <div style="display: flex; align-items: center; gap: 8px">
              <el-icon style="color: #f56c6c"><Warning /></el-icon>
              <span>保证金未收回</span>
            </div>
          </template>
          <el-table v-if="overview.deposit_not_returned?.length" :data="overview.deposit_not_returned" size="small">
            <el-table-column prop="project_name" label="项目名称" show-overflow-tooltip />
            <el-table-column prop="deposit_amount" label="金额" width="100">
              <template #default="{ row }">{{ row.deposit_amount?.toLocaleString() || '-' }}</template>
            </el-table-column>
            <el-table-column prop="deposit_date" label="缴纳日期" width="110" />
          </el-table>
          <el-empty v-else description="暂无未收回保证金" :image-size="40" />
        </el-card>
      </el-col>
    </el-row>

    <!-- 状态统计卡片 -->
    <el-row :gutter="16" style="margin-bottom: 16px">
      <el-col :span="6" v-for="item in statusCards" :key="item.key">
        <el-card shadow="hover" :body-style="{ textAlign: 'center', padding: '20px' }">
          <div style="font-size: 28px; font-weight: bold; color: item.color">{{ item.count }}</div>
          <div style="color: #999; margin-top: 4px">{{ item.label }}</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 本月中标概览 -->
    <el-card shadow="hover">
      <template #header>
        <span>本月中标概览</span>
      </template>
      <el-row :gutter="32" style="text-align: center">
        <el-col :span="8">
          <div style="font-size: 24px; font-weight: bold">{{ monthly.month_bids || 0 }}</div>
          <div style="color: #999">投标数</div>
        </el-col>
        <el-col :span="8">
          <div style="font-size: 24px; font-weight: bold; color: #67c23a">{{ monthly.month_wins || 0 }}</div>
          <div style="color: #999">中标数</div>
        </el-col>
        <el-col :span="8">
          <div style="font-size: 24px; font-weight: bold; color: #409eff">{{ winRatePercent }}%</div>
          <div style="color: #999">中标率</div>
        </el-col>
      </el-row>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { getOverview } from '../api/stats'

const loading = ref(false)
const overview = ref({})
const monthly = computed(() => overview.value.monthly_summary || {})
const winRatePercent = computed(() => ((monthly.value.month_win_rate || 0) * 100).toFixed(1))

const statusCards = computed(() => {
  const counts = overview.value.status_counts || {}
  return [
    { key: '跟进中', label: '跟进中', color: '#909399', count: counts['跟进中'] || 0 },
    { key: '已发公告', label: '已发公告', color: '#409eff', count: counts['已发公告'] || 0 },
    { key: '准备投标', label: '准备投标', color: '#e6a23c', count: counts['准备投标'] || 0 },
    { key: '已投标', label: '已投标', color: '#67c23a', count: counts['已投标'] || 0 },
  ]
})

async function loadData() {
  loading.value = true
  try {
    overview.value = await getOverview()
  } finally {
    loading.value = false
  }
}

onMounted(() => loadData())
</script>
