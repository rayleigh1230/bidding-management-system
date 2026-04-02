<template>
  <div>
    <div style="margin-bottom: 16px">
      <el-page-header @back="$router.push('/bids')">
        <template #content><span>投标信息 - {{ data.project_name || '' }}</span></template>
      </el-page-header>
    </div>

    <!-- 关联招标信息 (只读) -->
    <el-card style="margin-bottom: 16px">
      <template #header><span>关联招标信息</span></template>
      <el-descriptions :column="3" border>
        <el-descriptions-item label="项目名称">{{ data.project_name }}</el-descriptions-item>
        <el-descriptions-item label="代理单位">{{ data.agency_name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="投标截止">{{ data.bid_deadline || '-' }}</el-descriptions-item>
      </el-descriptions>
    </el-card>

    <!-- 投标信息表单 -->
    <el-card>
      <el-form ref="formRef" :model="form" label-width="110px" style="max-width: 750px">
        <el-form-item label="合作单位">
          <OrgSelector v-model="form.partner_ids" :multiple="true" />
        </el-form-item>
        <el-form-item label="投标方式">
          <el-select v-model="form.bid_method">
            <el-option label="独立" value="独立" />
            <el-option label="联合体" value="联合体" />
            <el-option label="配合" value="配合" />
            <el-option label="陪标" value="陪标" />
          </el-select>
        </el-form-item>
        <el-form-item label="投标状态">
          <el-select v-model="form.bid_status">
            <el-option label="不投标" value="不投标" />
            <el-option label="未报名" value="未报名" />
            <el-option label="已报名" value="已报名" />
          </el-select>
        </el-form-item>

        <!-- 保证金区域 -->
        <el-form-item label="是否有保证金">
          <el-switch v-model="form.has_deposit" />
        </el-form-item>
        <template v-if="form.has_deposit">
          <el-form-item label="保证金金额">
            <el-input-number v-model="form.deposit_amount" :min="0" :precision="2" :controls="false" style="width: 200px" />
            <span style="margin-left: 8px; color: #999">元</span>
          </el-form-item>
          <el-form-item label="缴纳日期">
            <el-date-picker v-model="form.deposit_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
          </el-form-item>
          <el-form-item label="保证金状态">
            <el-select v-model="form.deposit_status">
              <el-option label="已缴纳" value="已缴纳" />
              <el-option label="未收回" value="未收回" />
              <el-option label="已收回" value="已收回" />
            </el-select>
          </el-form-item>
          <el-form-item label="收回日期">
            <el-date-picker v-model="form.deposit_return_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
          </el-form-item>
        </template>

        <el-form-item label="备注">
          <el-input v-model="form.notes" type="textarea" :rows="3" />
        </el-form-item>

        <el-form-item>
          <div style="display: flex; gap: 8px">
            <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
            <el-button type="warning" @click="handleAbandon">放弃</el-button>
            <el-button type="success" @click="handleSubmit">已投标</el-button>
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
import { getBid, updateBid, submitBid, abandonBid } from '../../api/bid'
import { getBidding } from '../../api/bidding'
import OrgSelector from '../../components/OrgSelector.vue'

const route = useRoute()
const router = useRouter()
const saving = ref(false)

const data = ref({})
const defaultForm = {
  partner_ids: [], bid_method: '独立', bid_status: '未报名',
  has_deposit: false, deposit_status: '无', deposit_amount: 0,
  deposit_date: null, deposit_return_date: null, notes: '',
}
const form = ref({ ...defaultForm })

function parseJson(val, fallback = []) {
  if (Array.isArray(val)) return val
  if (typeof val === 'string') { try { return JSON.parse(val) } catch { return fallback } }
  return fallback
}

async function loadData() {
  try {
    const bid = await getBid(route.params.id)
    data.value = bid
    form.value = {
      partner_ids: parseJson(bid.partner_ids, []),
      bid_method: bid.bid_method || '独立',
      bid_status: bid.bid_status || '未报名',
      has_deposit: bid.has_deposit || false,
      deposit_status: bid.deposit_status || '无',
      deposit_amount: bid.deposit_amount || 0,
      deposit_date: bid.deposit_date,
      deposit_return_date: bid.deposit_return_date,
      notes: bid.notes || '',
    }
    // Load bidding info for display
    if (bid.bidding_info_id) {
      const bidding = await getBidding(bid.bidding_info_id)
      data.value.agency_name = bidding.agency_name
      data.value.bid_deadline = bidding.bid_deadline
    }
  } catch {
    ElMessage.error('投标信息不存在')
    router.push('/bids')
  }
}

async function handleSave() {
  saving.value = true
  try {
    await updateBid(route.params.id, form.value)
    ElMessage.success('保存成功')
    loadData()
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

async function handleSubmit() {
  try {
    await ElMessageBox.confirm('确认已提交投标？将自动保存当前信息并创建投标结果记录。', '确认')
    // Auto-save current bid info first
    await updateBid(route.params.id, form.value)
    // Then execute flow
    const res = await submitBid(route.params.id)
    ElMessage.success('提交投标成功')
    router.push(`/results/${res.bid_result_id}`)
  } catch (err) {
    if (err !== 'cancel') {
      ElMessage.error(err.response?.data?.detail || '操作失败')
    }
  }
}

async function handleAbandon() {
  try {
    await ElMessageBox.confirm('确认放弃该投标？将同时放弃关联项目。', '确认', { type: 'warning' })
    await abandonBid(route.params.id)
    ElMessage.success('已放弃')
    router.push('/bids')
  } catch (err) {
    if (err !== 'cancel') {
      ElMessage.error(err.response?.data?.detail || '操作失败')
    }
  }
}

onMounted(() => loadData())
</script>
