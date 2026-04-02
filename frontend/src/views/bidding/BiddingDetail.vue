<template>
  <div>
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px">
      <el-page-header @back="$router.push('/biddings')">
        <template #content>
          <span>招标信息 - {{ data.project_name || '' }}</span>
        </template>
      </el-page-header>
    </div>

    <!-- 关联项目信息 (只读) -->
    <el-card style="margin-bottom: 16px">
      <template #header><span>关联项目</span></template>
      <el-descriptions :column="3" border>
        <el-descriptions-item label="项目名称">{{ data.project_name }}</el-descriptions-item>
        <el-descriptions-item label="招标单位">{{ data.bidding_unit_name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="项目负责人">{{ data.manager_names?.join(', ') || '-' }}</el-descriptions-item>
      </el-descriptions>
    </el-card>

    <!-- 招标信息表单 -->
    <el-card>
      <el-form ref="formRef" :model="form" label-width="110px" style="max-width: 750px">
        <el-form-item label="代理单位">
          <OrgSelector v-model="form.agency_id" />
        </el-form-item>
        <el-form-item label="发布平台">
          <PlatformSelector v-model="form.publish_platform_id" />
        </el-form-item>
        <el-form-item label="项目标签">
          <el-select v-model="form.tags" multiple filterable allow-create default-first-option placeholder="输入标签后回车" style="width: 100%" />
        </el-form-item>
        <el-form-item label="报名截止日期">
          <el-date-picker v-model="form.registration_deadline" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
        </el-form-item>
        <el-form-item label="投标截止日期">
          <el-date-picker v-model="form.bid_deadline" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
        </el-form-item>
        <el-form-item label="预算类型">
          <el-radio-group v-model="form.budget_type">
            <el-radio value="总金额">总金额</el-radio>
            <el-radio value="单价">单价</el-radio>
            <el-radio value="其他">其他</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="预算金额">
          <el-input-number v-model="form.budget_amount" :min="0" :precision="2" :controls="false" style="width: 200px" />
          <span style="margin-left: 8px; color: #999">元</span>
        </el-form-item>
        <el-form-item label="是否入围标">
          <el-switch v-model="form.is_prequalification" />
        </el-form-item>
        <el-form-item label="投标专员">
          <el-select v-model="form.bid_specialist_id" placeholder="选择投标专员" clearable filterable style="width: 100%">
            <el-option v-for="u in users" :key="u.id" :label="u.display_name || u.username" :value="u.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.notes" type="textarea" :rows="3" />
        </el-form-item>

        <el-form-item>
          <div style="display: flex; gap: 8px">
            <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
            <el-button type="warning" @click="handleAbandon">放弃</el-button>
            <el-button type="success" @click="handlePrepare">准备投标</el-button>
          </div>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getBidding, updateBidding, prepareBid, abandonBidding } from '../../api/bidding'
import { getProject } from '../../api/project'
import { getUsers } from '../../api/user'
import OrgSelector from '../../components/OrgSelector.vue'
import PlatformSelector from '../../components/PlatformSelector.vue'

const route = useRoute()
const router = useRouter()
const formRef = ref(null)
const saving = ref(false)

const data = ref({})
const defaultForm = {
  agency_id: null, publish_platform_id: null, tags: [],
  registration_deadline: null, bid_deadline: null,
  budget_type: '总金额', budget_amount: 0,
  is_prequalification: false, bid_specialist_id: null, notes: '',
}
const form = ref({ ...defaultForm })
const users = ref([])

function parseJson(val, fallback = []) {
  if (Array.isArray(val)) return val
  if (typeof val === 'string') { try { return JSON.parse(val) } catch { return fallback } }
  return fallback
}

async function loadData() {
  try {
    const bidding = await getBidding(route.params.id)
    data.value = bidding
    form.value = {
      agency_id: bidding.agency_id,
      publish_platform_id: bidding.publish_platform_id,
      tags: parseJson(bidding.tags, []),
      registration_deadline: bidding.registration_deadline,
      bid_deadline: bidding.bid_deadline,
      budget_type: bidding.budget_type || '总金额',
      budget_amount: bidding.budget_amount || 0,
      is_prequalification: bidding.is_prequalification || false,
      bid_specialist_id: bidding.bid_specialist_id,
      notes: bidding.notes || '',
    }
    // Load project info for display
    if (bidding.project_id) {
      const project = await getProject(bidding.project_id)
      data.value.bidding_unit_name = project.bidding_unit_name
      data.value.manager_names = project.manager_names
    }
  } catch {
    ElMessage.error('招标信息不存在')
    router.push('/biddings')
  }
}

async function loadUsers() {
  try { users.value = await getUsers() } catch { /* ignore */ }
}

async function handleSave() {
  saving.value = true
  try {
    const payload = { ...form.value, tags: form.value.tags }
    await updateBidding(route.params.id, payload)
    ElMessage.success('保存成功')
    loadData()
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

async function handlePrepare() {
  try {
    await ElMessageBox.confirm('确认准备投标？将自动保存当前信息并创建投标信息记录。', '确认')
    // Auto-save current bidding info first
    const payload = { ...form.value, tags: form.value.tags }
    await updateBidding(route.params.id, payload)
    // Then execute flow
    const res = await prepareBid(route.params.id)
    ElMessage.success('准备投标成功')
    router.push(`/bids/${res.bid_info_id}`)
  } catch (err) {
    if (err !== 'cancel') {
      ElMessage.error(err.response?.data?.detail || '操作失败')
    }
  }
}

async function handleAbandon() {
  try {
    await ElMessageBox.confirm('确认放弃该招标？将同时放弃关联项目。', '确认', { type: 'warning' })
    await abandonBidding(route.params.id)
    ElMessage.success('已放弃')
    router.push('/biddings')
  } catch (err) {
    if (err !== 'cancel') {
      ElMessage.error(err.response?.data?.detail || '操作失败')
    }
  }
}

onMounted(() => { loadData(); loadUsers() })
</script>
