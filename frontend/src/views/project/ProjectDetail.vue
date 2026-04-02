<template>
  <div>
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px">
      <el-page-header @back="$router.push('/projects')">
        <template #content>
          <span>{{ isNew ? '新增项目' : project.project_name }}</span>
          <el-tag v-if="!isNew" :type="statusType(project.status)" style="margin-left: 8px">{{ statusLabel(project.status) }}</el-tag>
        </template>
      </el-page-header>
    </div>

    <el-card>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px" style="max-width: 700px">
        <el-form-item label="招标类型" prop="bidding_type">
          <el-select v-model="form.bidding_type" placeholder="请选择招标类型" :disabled="!isNew && !isFollowing">
            <el-option label="公开招标" value="公开招标" />
            <el-option label="邀请招标" value="邀请招标" />
            <el-option label="中介超市" value="中介超市" />
            <el-option label="入围分项" value="入围分项" />
          </el-select>
        </el-form-item>
        <el-form-item label="项目名称" prop="project_name">
          <el-input v-model="form.project_name" :disabled="!isNew && !isFollowing" />
        </el-form-item>
        <el-form-item label="招标单位">
          <OrgSelector v-model="form.bidding_unit_id" :disabled="!isNew && !isFollowing" />
        </el-form-item>
        <el-form-item label="所属地区">
          <RegionCascader v-model="form.region" :disabled="!isNew && !isFollowing" />
        </el-form-item>
        <el-form-item label="项目负责人">
          <ManagerSelector v-model="form.manager_ids" :multiple="true" :disabled="!isNew && !isFollowing" />
        </el-form-item>
        <el-form-item label="项目描述">
          <el-input v-model="form.description" type="textarea" :rows="3" :disabled="!isNew && !isFollowing" />
        </el-form-item>

        <el-form-item>
          <div style="display: flex; gap: 8px">
            <el-button v-if="isNew || isFollowing" type="primary" :loading="saving" @click="handleSave">
              {{ isNew ? '创建项目' : '保存修改' }}
            </el-button>
            <template v-if="!isNew">
              <el-button v-if="isFollowing" type="warning" @click="showAbandonDialog = true">放弃</el-button>
              <el-button v-if="isFollowing" type="success" @click="handlePublish">已发公告</el-button>
            </template>
          </div>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- Abandon dialog -->
    <el-dialog v-model="showAbandonDialog" title="放弃项目" width="400px">
      <el-form label-width="80px">
        <el-form-item label="放弃原因">
          <el-input v-model="abandonReason" type="textarea" :rows="3" placeholder="请输入放弃原因" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAbandonDialog = false">取消</el-button>
        <el-button type="danger" @click="handleAbandon">确认放弃</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getProject, createProject, updateProject, publishProject, abandonProject } from '../../api/project'
import OrgSelector from '../../components/OrgSelector.vue'
import RegionCascader from '../../components/RegionCascader.vue'
import ManagerSelector from '../../components/ManagerSelector.vue'

const route = useRoute()
const router = useRouter()
const formRef = ref(null)
const saving = ref(false)
const showAbandonDialog = ref(false)
const abandonReason = ref('')

const isNew = computed(() => route.params.id === 'new')
const project = ref({})
const defaultForm = { bidding_type: '', project_name: '', bidding_unit_id: null, region: [], manager_ids: [], description: '' }
const form = ref({ ...defaultForm })

const rules = {
  bidding_type: [{ required: true, message: '请选择招标类型', trigger: 'change' }],
  project_name: [{ required: true, message: '请输入项目名称', trigger: 'blur' }],
}

const isFollowing = computed(() => project.value.status === '跟进中')

const statusMap = {
  '跟进中': { label: '跟进中', type: 'info' },
  '已发公告': { label: '已发公告', type: 'primary' },
  '准备投标': { label: '准备投标', type: 'warning' },
  '已投标': { label: '已投标', type: 'primary' },
  '已中标': { label: '已中标', type: 'success' },
  '未中标': { label: '未中标', type: 'danger' },
  '已放弃': { label: '已放弃', type: 'info' },
}
function statusLabel(s) { return statusMap[s]?.label || s }
function statusType(s) { return statusMap[s]?.type || 'info' }

async function loadProject() {
  if (isNew.value) return
  try {
    const data = await getProject(route.params.id)
    project.value = data
    // Parse region from JSON string
    let region = []
    if (data.region) {
      try { region = JSON.parse(data.region) } catch { region = [] }
    }
    // Parse manager_ids
    let managerIds = data.manager_ids || []
    if (typeof managerIds === 'string') {
      try { managerIds = JSON.parse(managerIds) } catch { managerIds = [] }
    }
    form.value = {
      bidding_type: data.bidding_type,
      project_name: data.project_name,
      bidding_unit_id: data.bidding_unit_id,
      region,
      manager_ids: managerIds,
      description: data.description || '',
    }
  } catch {
    ElMessage.error('项目不存在')
    router.push('/projects')
  }
}

async function handleSave() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    const data = {
      ...form.value,
      region: JSON.stringify(form.value.region),
    }
    if (isNew.value) {
      const created = await createProject(data)
      ElMessage.success('创建成功')
      router.replace(`/projects/${created.id}`)
    } else {
      await updateProject(route.params.id, data)
      ElMessage.success('保存成功')
      loadProject()
    }
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '操作失败')
  } finally {
    saving.value = false
  }
}

async function handlePublish() {
  try {
    await ElMessageBox.confirm('确认已发布招标公告？将自动保存当前信息并创建招标信息记录。', '确认')
    // Auto-save current project info first
    const saveData = {
      ...form.value,
      region: JSON.stringify(form.value.region),
    }
    await updateProject(route.params.id, saveData)
    // Then execute flow
    const res = await publishProject(route.params.id)
    ElMessage.success('发布成功')
    router.push(`/biddings/${res.bidding_info_id}`)
  } catch (err) {
    if (err !== 'cancel') {
      ElMessage.error(err.response?.data?.detail || '发布失败')
    }
  }
}

async function handleAbandon() {
  try {
    await abandonProject(route.params.id, abandonReason.value)
    ElMessage.success('已放弃')
    router.push('/projects')
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '操作失败')
  }
}

onMounted(() => loadProject())
</script>
