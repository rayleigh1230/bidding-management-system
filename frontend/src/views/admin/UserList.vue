<template>
  <div>
    <div style="display: flex; justify-content: flex-end; margin-bottom: 16px">
      <el-button type="primary" @click="openDialog(null)"><el-icon><Plus /></el-icon> 新增用户</el-button>
    </div>

    <el-table :data="tableData" v-loading="loading" border stripe>
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="username" label="用户名" width="120" />
      <el-table-column prop="display_name" label="显示名" width="120" />
      <el-table-column prop="role" label="角色" width="100">
        <template #default="{ row }">
          <el-tag :type="row.role === 'admin' ? 'danger' : 'info'">{{ row.role === 'admin' ? '管理员' : '普通用户' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="phone" label="电话" width="140" />
      <el-table-column prop="is_active" label="状态" width="80">
        <template #default="{ row }">
          <el-tag :type="row.is_active ? 'success' : 'warning'">{{ row.is_active ? '启用' : '禁用' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="100" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openDialog(row)">编辑</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑用户' : '新增用户'" width="500px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" :disabled="!!editingId" />
        </el-form-item>
        <el-form-item v-if="!editingId" label="密码" prop="password">
          <el-input v-model="form.password" type="password" show-password />
        </el-form-item>
        <el-form-item v-if="editingId" label="密码">
          <el-input v-model="form.password" type="password" show-password placeholder="不修改则留空" />
        </el-form-item>
        <el-form-item label="显示名" prop="display_name">
          <el-input v-model="form.display_name" />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="form.role">
            <el-option label="管理员" value="admin" />
            <el-option label="普通用户" value="user" />
          </el-select>
        </el-form-item>
        <el-form-item label="电话">
          <el-input v-model="form.phone" />
        </el-form-item>
        <el-form-item v-if="editingId" label="状态">
          <el-switch v-model="form.is_active" active-text="启用" inactive-text="禁用" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { getUsers, createUser, updateUser } from '../../api/user'

const tableData = ref([])
const loading = ref(false)

const dialogVisible = ref(false)
const editingId = ref(null)
const submitting = ref(false)
const formRef = ref(null)

const defaultForm = { username: '', password: '', display_name: '', role: 'user', phone: '', is_active: true }
const form = ref({ ...defaultForm })

const createRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
  display_name: [{ required: true, message: '请输入显示名', trigger: 'blur' }],
}
const editRules = {
  display_name: [{ required: true, message: '请输入显示名', trigger: 'blur' }],
}
const rules = ref(createRules)

async function loadData() {
  loading.value = true
  try {
    tableData.value = await getUsers()
  } finally {
    loading.value = false
  }
}

function openDialog(row) {
  editingId.value = row?.id || null
  rules.value = editingId.value ? editRules : createRules
  form.value = row
    ? { username: row.username, password: '', display_name: row.display_name, role: row.role, phone: row.phone, is_active: row.is_active }
    : { ...defaultForm }
  dialogVisible.value = true
}

async function handleSubmit() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  submitting.value = true
  try {
    if (editingId.value) {
      const data = { display_name: form.value.display_name, role: form.value.role, phone: form.value.phone, is_active: form.value.is_active }
      if (form.value.password) data.password = form.value.password
      await updateUser(editingId.value, data)
      ElMessage.success('更新成功')
    } else {
      await createUser(form.value)
      ElMessage.success('新增成功')
    }
    dialogVisible.value = false
    loadData()
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '操作失败')
  } finally {
    submitting.value = false
  }
}

onMounted(() => loadData())
</script>
