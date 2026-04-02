<template>
  <div>
    <div style="margin-bottom: 16px">
      <el-page-header @back="$router.push('/results')">
        <template #content><span>投标结果 - {{ data.project_name || '' }}</span></template>
      </el-page-header>
    </div>

    <!-- 关联投标信息 (只读) -->
    <el-card style="margin-bottom: 16px">
      <template #header><span>关联投标信息</span></template>
      <el-descriptions :column="3" border>
        <el-descriptions-item label="项目名称">{{ data.project_name }}</el-descriptions-item>
        <el-descriptions-item label="投标方式">{{ data.bid_method || '-' }}</el-descriptions-item>
        <el-descriptions-item label="投标状态">{{ data.bid_status || '-' }}</el-descriptions-item>
      </el-descriptions>
    </el-card>

    <!-- 投标结果表单 -->
    <el-card>
      <el-form ref="formRef" :model="form" label-width="110px" style="max-width: 800px">
        <el-form-item label="我方投标报价">
          <el-input-number v-model="form.our_price" :min="0" :precision="2" :controls="false" style="width: 200px" />
          <span style="margin-left: 8px; color: #999">元</span>
        </el-form-item>

        <!-- 参标单位及报价 -->
        <el-form-item label="参标单位报价">
          <div v-for="(comp, idx) in form.competitors" :key="idx" style="display: flex; gap: 8px; margin-bottom: 8px; width: 100%">
            <OrgSelector v-model="comp.org_id" style="flex: 1" />
            <el-input-number v-model="comp.price" :min="0" :precision="2" :controls="false" placeholder="报价" style="width: 150px" />
            <el-button type="danger" link @click="form.competitors.splice(idx, 1)"><el-icon><Delete /></el-icon></el-button>
          </div>
          <el-button type="primary" link @click="form.competitors.push({ org_id: null, price: 0 })">+ 添加参标单位</el-button>
        </el-form-item>

        <!-- 评分情况 -->
        <el-form-item label="评分情况">
          <div v-for="(score, idx) in form.scoring_details" :key="idx" style="display: flex; gap: 8px; margin-bottom: 8px; width: 100%">
            <el-input v-model="score.name" placeholder="单位名称" style="flex: 1" />
            <el-input-number v-model="score.score" :min="0" :controls="false" placeholder="分数" style="width: 120px" />
            <el-button type="danger" link @click="form.scoring_details.splice(idx, 1)"><el-icon><Delete /></el-icon></el-button>
          </div>
          <el-button type="primary" link @click="form.scoring_details.push({ name: '', score: 0 })">+ 添加评分记录</el-button>
        </el-form-item>

        <el-form-item label="保证金状态">
          <el-select v-model="form.deposit_status" clearable placeholder="未设置">
            <el-option label="未收回" value="未收回" />
            <el-option label="已收回" value="已收回" />
          </el-select>
        </el-form-item>

        <el-form-item label="是否中标">
          <el-radio-group v-model="form.is_won">
            <el-radio :label="true">已中标</el-radio>
            <el-radio :label="false">未中标</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item v-if="!form.is_won" label="未中标分析">
          <el-input v-model="form.lost_analysis" type="textarea" :rows="3" placeholder="分析未中标原因" />
        </el-form-item>

        <template v-if="form.is_won">
          <el-form-item label="合同编号">
            <el-input v-model="form.contract_number" />
          </el-form-item>
          <el-form-item label="合同金额">
            <el-input-number v-model="form.contract_amount" :min="0" :precision="2" :controls="false" style="width: 200px" />
            <span style="margin-left: 8px; color: #999">元</span>
          </el-form-item>
          <el-form-item label="合同状态">
            <el-select v-model="form.contract_status">
              <el-option label="无" value="无" />
              <el-option label="未签订" value="未签订" />
              <el-option label="已签订未收回" value="已签订未收回" />
              <el-option label="已签订已收回" value="已签订已收回" />
            </el-select>
          </el-form-item>
        </template>

        <el-form-item label="备注">
          <el-input v-model="form.notes" type="textarea" :rows="2" />
        </el-form-item>

        <el-form-item>
          <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Delete } from '@element-plus/icons-vue'
import { getResult, updateResult } from '../../api/result'
import { getBid } from '../../api/bid'
import OrgSelector from '../../components/OrgSelector.vue'

const route = useRoute()
const router = useRouter()
const saving = ref(false)

const data = ref({})
const defaultForm = {
  our_price: 0, competitors: [], scoring_details: [],
  deposit_status: null, is_won: false, lost_analysis: '',
  contract_number: '', contract_status: '无', contract_amount: 0, notes: '',
}
const form = ref({ ...defaultForm })

function parseJson(val, fallback = []) {
  if (Array.isArray(val)) return val
  if (typeof val === 'string') { try { return JSON.parse(val) } catch { return fallback } }
  return fallback
}

async function loadData() {
  try {
    const result = await getResult(route.params.id)
    data.value = result
    form.value = {
      our_price: result.our_price || 0,
      competitors: parseJson(result.competitors, []),
      scoring_details: parseJson(result.scoring_details, []),
      deposit_status: result.deposit_status || null,
      is_won: result.is_won || false,
      lost_analysis: result.lost_analysis || '',
      contract_number: result.contract_number || '',
      contract_status: result.contract_status || '无',
      contract_amount: result.contract_amount || 0,
      notes: result.notes || '',
    }
    // Load bid info for display
    if (result.bid_info_id) {
      const bid = await getBid(result.bid_info_id)
      data.value.bid_method = bid.bid_method
      data.value.bid_status = bid.bid_status
    }
  } catch {
    ElMessage.error('投标结果不存在')
    router.push('/results')
  }
}

async function handleSave() {
  saving.value = true
  try {
    await updateResult(route.params.id, form.value)
    ElMessage.success('保存成功')
    loadData()
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

onMounted(() => loadData())
</script>
