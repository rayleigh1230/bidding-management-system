<template>
  <el-select
    :model-value="modelValue"
    placeholder="输入关键词搜索负责人"
    filterable
    remote
    :remote-method="handleSearch"
    :loading="loading"
    clearable
    :multiple="multiple"
    @update:model-value="$emit('update:modelValue', $event)"
    @change="handleChange"
  >
    <el-option v-for="item in options" :key="item.id" :label="item.name + (item.phone ? ` (${item.phone})` : '')" :value="item.id" />
    <template #footer>
      <el-button type="primary" link size="small" @click="showDialog = true">+ 新增负责人</el-button>
    </template>
  </el-select>

  <el-dialog v-model="showDialog" title="新增负责人" width="450px" append-to-body>
    <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
      <el-form-item label="姓名" prop="name">
        <el-input v-model="form.name" />
      </el-form-item>
      <el-form-item label="电话">
        <el-input v-model="form.phone" />
      </el-form-item>
      <el-form-item label="所属公司">
        <el-input v-model="form.company" />
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
import { getManagers, createManager } from '../api/dict'

const props = defineProps({
  modelValue: { type: [Array, Number, null], default: null },
  multiple: { type: Boolean, default: false },
})
const emit = defineEmits(['update:modelValue', 'change'])

const options = ref([])
const loading = ref(false)
const showDialog = ref(false)
const submitting = ref(false)
const formRef = ref(null)

const form = ref({ name: '', phone: '', company: '', notes: '' })
const rules = { name: [{ required: true, message: '请输入姓名', trigger: 'blur' }] }

let searchTimer = null
let loaded = false

async function preloadOptions() {
  if (loaded) return
  loaded = true
  try {
    const res = await getManagers({ page_size: 100 })
    options.value = res.items
  } catch { /* ignore */ }
}

async function handleSearch(query) {
  clearTimeout(searchTimer)
  if (!query) { return }
  searchTimer = setTimeout(async () => {
    loading.value = true
    try {
      const res = await getManagers({ keyword: query, page_size: 50 })
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
    const manager = await createManager(form.value)
    ElMessage.success('新增成功')
    showDialog.value = false
    options.value = [manager, ...options.value]
    if (props.multiple) {
      const current = props.modelValue || []
      emit('update:modelValue', [...current, manager.id])
    } else {
      emit('update:modelValue', manager.id)
    }
    emit('change', manager)
    form.value = { name: '', phone: '', company: '', notes: '' }
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '新增失败')
  } finally {
    submitting.value = false
  }
}

function handleChange(val) {
  if (props.multiple) {
    const selected = options.value.filter((o) => val.includes(o.id))
    emit('change', selected)
  } else {
    const selected = options.value.find((o) => o.id === val)
    emit('change', selected || null)
  }
}

watch(() => props.modelValue, (val) => {
  if (val && (Array.isArray(val) ? val.length > 0 : true) && !loaded) preloadOptions()
}, { immediate: true })
</script>
