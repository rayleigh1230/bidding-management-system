<template>
  <el-select
    :model-value="modelValue"
    placeholder="输入关键词搜索单位"
    filterable
    remote
    :remote-method="handleSearch"
    :loading="loading"
    clearable
    @update:model-value="$emit('update:modelValue', $event)"
    @change="handleChange"
  >
    <el-option v-for="item in options" :key="item.id" :label="item.name" :value="item.id" />
    <template #footer>
      <el-button type="primary" link size="small" @click="showDialog = true">+ 新增单位</el-button>
    </template>
  </el-select>

  <el-dialog v-model="showDialog" title="新增单位" width="450px" append-to-body>
    <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
      <el-form-item label="单位名称" prop="name">
        <el-input v-model="form.name" />
      </el-form-item>
      <el-form-item label="简称" prop="short_name">
        <el-input v-model="form.short_name" />
      </el-form-item>
      <el-form-item label="联系人">
        <el-input v-model="form.contact_person" />
      </el-form-item>
      <el-form-item label="联系电话">
        <el-input v-model="form.contact_phone" />
      </el-form-item>
      <el-form-item label="备注">
        <el-input v-model="form.notes" type="textarea" :rows="2" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="showDialog = false">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="handleCreate">确定</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { getOrganizations, createOrganization } from '../api/dict'

const props = defineProps({
  modelValue: { type: [Number, null], default: null },
})
const emit = defineEmits(['update:modelValue', 'change'])

const options = ref([])
const loading = ref(false)
const showDialog = ref(false)
const submitting = ref(false)
const formRef = ref(null)

const form = ref({ name: '', short_name: '', contact_person: '', contact_phone: '', notes: '' })
const rules = { name: [{ required: true, message: '请输入单位名称', trigger: 'blur' }] }

let searchTimer = null
let loaded = false

async function preloadOptions() {
  if (loaded) return
  loaded = true
  try {
    const res = await getOrganizations({ page_size: 100 })
    options.value = res.items
  } catch { /* ignore */ }
}

async function handleSearch(query) {
  clearTimeout(searchTimer)
  if (!query) { return }
  searchTimer = setTimeout(async () => {
    loading.value = true
    try {
      const res = await getOrganizations({ keyword: query, page_size: 50 })
      options.value = res.items
    } finally {
      loading.value = false
    }
  }, 300)
}

async function handleCreate() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  submitting.value = true
  try {
    const org = await createOrganization(form.value)
    ElMessage.success('新增成功')
    showDialog.value = false
    options.value = [org, ...options.value]
    emit('update:modelValue', org.id)
    emit('change', org)
    form.value = { name: '', short_name: '', contact_person: '', contact_phone: '', notes: '' }
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '新增失败')
  } finally {
    submitting.value = false
  }
}

function handleChange(val) {
  const selected = options.value.find((o) => o.id === val)
  emit('change', selected || null)
}

watch(() => props.modelValue, (val) => {
  if (val && !loaded) preloadOptions()
}, { immediate: true })
</script>
