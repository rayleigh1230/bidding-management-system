<template>
  <div>
    <el-card>
      <template #header>
        <span>抓取记录</span>
      </template>

      <el-table :data="runs" v-loading="loading" stripe>
        <el-table-column label="开始时间" width="160">
          <template #default="{ row }">
            {{ formatTime(row.started_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="triggered_by_name" label="触发用户" width="100" />
        <el-table-column prop="total_count" label="总数" width="70" align="center" />
        <el-table-column prop="created_count" label="入库" width="70" align="center">
          <template #default="{ row }">
            <span style="color: #67c23a">{{ row.created_count }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="skipped_count" label="跳过" width="70" align="center">
          <template #default="{ row }">
            <span style="color: #909399">{{ row.skipped_count }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="failed_count" label="失败" width="70" align="center">
          <template #default="{ row }">
            <span style="color: #f56c6c">{{ row.failed_count }}</span>
          </template>
        </el-table-column>
        <el-table-column label="耗时" width="80">
          <template #default="{ row }">
            {{ formatDuration(row.started_at, row.finished_at) }}
          </template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="statusTag(row.status)">{{ statusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="失败站点" min-width="200">
          <template #default="{ row }">
            <span v-if="row.error_summary && Object.keys(row.error_summary).length" style="font-size: 12px; color: #e6a23c">
              {{ formatErrors(row.error_summary) }}
            </span>
            <span v-else style="color: #c0c4cc">—</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="80" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="showDetail(row.id)">详情</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div style="margin-top: 16px; text-align: right">
        <el-pagination
          v-model:current-page="page"
          :page-size="20"
          :total="total"
          layout="total, prev, pager, next"
          @current-change="loadData"
        />
      </div>
    </el-card>

    <el-drawer v-model="detailVisible" title="抓取详情" size="70%">
      <div v-if="detail">
        <el-descriptions :column="4" border style="margin-bottom: 16px">
          <el-descriptions-item label="开始时间">{{ formatTime(detail.started_at) }}</el-descriptions-item>
          <el-descriptions-item label="结束时间">{{ formatTime(detail.finished_at) }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="statusTag(detail.status)">{{ statusText(detail.status) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="触发用户">{{ detail.triggered_by_name }}</el-descriptions-item>
          <el-descriptions-item label="入库">{{ detail.created_count }}</el-descriptions-item>
          <el-descriptions-item label="跳过">{{ detail.skipped_count }}</el-descriptions-item>
          <el-descriptions-item label="失败">{{ detail.failed_count }}</el-descriptions-item>
          <el-descriptions-item label="总数">{{ detail.total_count }}</el-descriptions-item>
        </el-descriptions>

        <el-table :data="detail.item_logs" stripe max-height="500">
          <el-table-column prop="source" label="来源" width="90" />
          <el-table-column prop="project_name" label="项目名称" min-width="250" show-overflow-tooltip />
          <el-table-column prop="external_no" label="编号" width="140" show-overflow-tooltip />
          <el-table-column label="结果" width="80">
            <template #default="{ row }">
              <el-tag :type="resultTag(row.result)" size="small">{{ resultText(row.result) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="skip_reason" label="跳过原因" width="200" show-overflow-tooltip />
          <el-table-column prop="error_message" label="错误信息" width="250" show-overflow-tooltip />
          <el-table-column label="链接" width="70">
            <template #default="{ row }">
              <el-link v-if="row.source_url" :href="row.source_url" target="_blank" type="primary">查看</el-link>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getScrapeRuns, getScrapeRunDetail } from '../../api/scrape'

const runs = ref([])
const loading = ref(false)
const page = ref(1)
const total = ref(0)

const detailVisible = ref(false)
const detail = ref(null)

async function loadData() {
  loading.value = true
  try {
    const data = await getScrapeRuns({ page: page.value, page_size: 20 })
    runs.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

async function showDetail(runId) {
  detail.value = await getScrapeRunDetail(runId)
  detailVisible.value = true
}

function formatTime(s) {
  if (!s) return '—'
  return new Date(s).toLocaleString('zh-CN', { hour12: false })
}

function formatDuration(start, end) {
  if (!start || !end) return '—'
  const sec = Math.round((new Date(end) - new Date(start)) / 1000)
  const m = Math.floor(sec / 60)
  const s = sec % 60
  return `${m}:${s.toString().padStart(2, '0')}`
}

function formatErrors(errs) {
  const entries = Object.entries(errs).filter(([k]) => k !== 'system')
  return entries.map(([k, v]) => `${k}: ${v}`).join('; ')
}

function statusText(s) {
  return { running: '进行中', success: '成功', partial: '部分成功', failed: '失败' }[s] || s
}

function statusTag(s) {
  return { running: 'warning', success: 'success', partial: 'warning', failed: 'danger' }[s] || ''
}

function resultText(r) {
  return { created: '入库', skipped: '跳过', failed: '失败' }[r] || r
}

function resultTag(r) {
  return { created: 'success', skipped: 'info', failed: 'danger' }[r] || ''
}

onMounted(loadData)
</script>
