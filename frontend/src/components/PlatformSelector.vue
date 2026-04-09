<template>
  <el-select
    :model-value="modelValue"
    placeholder="输入关键词搜索平台"
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
      <el-button type="primary" link size="small" @click="showDialog = true">+ 新增平台</el-button>
    </template>
  </el-select>

  <el-dialog v-model="showDialog" title="新增平台" width="450px" append-to-body>
    <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
      <el-form-item label="平台名称" prop="name">
        <el-input v-model="form.name" />
      </el-form-item>
      <el-form-item label="网址">
        <el-input v-model="form.url" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="showDialog = false">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="handleCreate">确定</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getPlatforms, createPlatform } from '../api/dict'

const props = defineProps({
  modelValue: { type: [Number, null], default: null },
})
const emit = defineEmits(['update:modelValue', 'change'])

const options = ref([])
const loading = ref(false)
const showDialog = ref(false)
const submitting = ref(false)
const formRef = ref(null)

const form = ref({ name: '', url: '' })
const rules = { name: [{ required: true, message: '请输入平台名称', trigger: 'blur' }] }

let searchTimer = null

async function handleSearch(query) {
  clearTimeout(searchTimer)
  if (!query) { options.value = []; return }
  searchTimer = setTimeout(async () => {
    loading.value = true
    try {
      const res = await getPlatforms({ keyword: query, page_size: 50 })
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
    const platform = await createPlatform(form.value)
    ElMessage.success('新增成功')
    showDialog.value = false
    options.value = [platform, ...options.value]
    emit('update:modelValue', platform.id)
    emit('change', platform)
    form.value = { name: '', url: '' }
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

onMounted(() => handleSearch(''))
</script>
