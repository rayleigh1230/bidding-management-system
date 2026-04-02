<template>
  <div>
    <el-tabs v-model="activeTab" @tab-change="handleTabChange">
      <!-- Tab 1: 中标率统计 -->
      <el-tab-pane label="中标率统计" name="winrate">
        <div style="display: flex; gap: 12px; margin-bottom: 16px">
          <el-select v-model="winRateParams.period" style="width: 120px" @change="loadWinRate">
            <el-option label="按月" value="month" />
            <el-option label="按季" value="quarter" />
            <el-option label="按年" value="year" />
          </el-select>
        </div>
        <div ref="winRateChartRef" style="height: 400px; width: 100%"></div>
      </el-tab-pane>

      <!-- Tab 2: 投标趋势 -->
      <el-tab-pane label="投标趋势" name="trend">
        <div ref="trendChartRef" style="height: 400px; width: 100%"></div>
      </el-tab-pane>

      <!-- Tab 3: 竞争对手分析 -->
      <el-tab-pane label="竞争对手分析" name="competitors">
        <el-table :data="competitors" v-loading="competitorsLoading" border stripe>
          <el-table-column prop="org_name" label="竞争单位" min-width="200" />
          <el-table-column prop="encounter_count" label="遭遇次数" width="120" />
          <el-table-column prop="win_count" label="对方中标次数" width="120" />
          <el-table-column prop="win_rate" label="对方中标率" width="120">
            <template #default="{ row }">{{ (row.win_rate * 100).toFixed(1) }}%</template>
          </el-table-column>
        </el-table>
        <div ref="competitorChartRef" style="height: 350px; width: 100%; margin-top: 16px"></div>
      </el-tab-pane>

      <!-- Tab 4: 保证金跟踪 -->
      <el-tab-pane label="保证金跟踪" name="deposits">
        <el-table :data="deposits" v-loading="depositsLoading" border stripe>
          <el-table-column prop="project_name" label="项目名称" min-width="200" show-overflow-tooltip />
          <el-table-column prop="deposit_amount" label="保证金金额" width="120">
            <template #default="{ row }">{{ row.deposit_amount?.toLocaleString() || '-' }}</template>
          </el-table-column>
          <el-table-column prop="deposit_status" label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="row.deposit_status === '已收回' ? 'success' : row.days_overdue > 0 ? 'danger' : 'warning'">
                {{ row.deposit_status }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="deposit_date" label="缴纳日期" width="110" />
          <el-table-column prop="deposit_return_date" label="收回日期" width="110" />
          <el-table-column prop="days_overdue" label="超期天数" width="100">
            <template #default="{ row }">
              <span v-if="row.days_overdue > 0" style="color: #f56c6c; font-weight: bold">{{ row.days_overdue }}天</span>
              <span v-else>-</span>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, onBeforeUnmount } from 'vue'
import * as echarts from 'echarts'
import { getWinRate, getCompetitors, getDeposits } from '../../api/stats'

const activeTab = ref('winrate')
const winRateParams = ref({ period: 'month' })
const winRateData = ref([])
const competitors = ref([])
const deposits = ref([])
const competitorsLoading = ref(false)
const depositsLoading = ref(false)

const winRateChartRef = ref(null)
const trendChartRef = ref(null)
const competitorChartRef = ref(null)

let winRateChart = null
let trendChart = null
let competitorChart = null

function initChart(ref_el) {
  if (!ref_el) return null
  const chart = echarts.init(ref_el)
  return chart
}

async function loadWinRate() {
  winRateData.value = await getWinRate(winRateParams.value)
  await nextTick()
  if (!winRateChart) winRateChart = initChart(winRateChartRef.value)
  if (!winRateChart) return

  const xData = winRateData.value.map((d) => d.period_label)
  const totalBids = winRateData.value.map((d) => d.total_bids)
  const wins = winRateData.value.map((d) => d.wins)
  const rates = winRateData.value.map((d) => (d.win_rate * 100).toFixed(1))

  winRateChart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['投标数', '中标数', '中标率'] },
    xAxis: { type: 'category', data: xData },
    yAxis: [
      { type: 'value', name: '数量' },
      { type: 'value', name: '中标率(%)', max: 100 },
    ],
    series: [
      { name: '投标数', type: 'bar', data: totalBids },
      { name: '中标数', type: 'bar', data: wins },
      { name: '中标率', type: 'line', yAxisIndex: 1, data: rates },
    ],
  })
}

async function loadTrend() {
  // Reuse win-rate data with month period for trend
  const data = await getWinRate({ period: 'month' })
  await nextTick()
  if (!trendChart) trendChart = initChart(trendChartRef.value)
  if (!trendChart) return

  const xData = data.map((d) => d.period_label)
  const totalBids = data.map((d) => d.total_bids)
  const rates = data.map((d) => (d.win_rate * 100).toFixed(1))

  trendChart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['投标数量', '中标率'] },
    xAxis: { type: 'category', data: xData },
    yAxis: [
      { type: 'value', name: '数量' },
      { type: 'value', name: '中标率(%)', max: 100 },
    ],
    series: [
      { name: '投标数量', type: 'bar', data: totalBids, itemStyle: { color: '#409eff' } },
      { name: '中标率', type: 'line', yAxisIndex: 1, data: rates, smooth: true, itemStyle: { color: '#67c23a' } },
    ],
  })
}

async function loadCompetitors() {
  competitorsLoading.value = true
  try {
    competitors.value = await getCompetitors()
    await nextTick()
    if (!competitorChart) competitorChart = initChart(competitorChartRef.value)
    if (!competitorChart) return

    const top10 = competitors.value.slice(0, 10)
    competitorChart.setOption({
      tooltip: { trigger: 'axis' },
      legend: { data: ['遭遇次数', '对方中标次数'] },
      xAxis: { type: 'category', data: top10.map((d) => d.org_name), axisLabel: { rotate: 30 } },
      yAxis: { type: 'value' },
      series: [
        { name: '遭遇次数', type: 'bar', data: top10.map((d) => d.encounter_count), itemStyle: { color: '#409eff' } },
        { name: '对方中标次数', type: 'bar', data: top10.map((d) => d.win_count), itemStyle: { color: '#f56c6c' } },
      ],
    })
  } finally {
    competitorsLoading.value = false
  }
}

async function loadDeposits() {
  depositsLoading.value = true
  try {
    deposits.value = await getDeposits()
  } finally {
    depositsLoading.value = false
  }
}

function handleTabChange(tab) {
  if (tab === 'winrate') loadWinRate()
  else if (tab === 'trend') loadTrend()
  else if (tab === 'competitors') loadCompetitors()
  else if (tab === 'deposits') loadDeposits()
}

function handleResize() {
  winRateChart?.resize()
  trendChart?.resize()
  competitorChart?.resize()
}

onMounted(() => {
  loadWinRate()
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  winRateChart?.dispose()
  trendChart?.dispose()
  competitorChart?.dispose()
})
</script>
