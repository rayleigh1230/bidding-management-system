<template>
  <div>
    <div style="display: flex; justify-content: space-between; margin-bottom: 16px">
      <el-input v-model="keyword" placeholder="搜索单位名称" clearable style="width: 300px" @clear="loadData" @keyup.enter="loadData">
        <template #append>
          <el-button @click="loadData"><el-icon><Search /></el-icon></el-button>
        </template>
      </el-input>
      <el-button type="primary" @click="openDialog(null)"><el-icon><Plus /></el-icon> 新增单位</el-button>
    </div>

    <el-table :data="tableData" v-loading="loading" border stripe>
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="name" label="单位名称" min-width="200" />
      <el-table-column prop="short_name" label="简称" width="120" />
      <el-table-column prop="contact_person" label="联系人" width="100" />
      <el-table-column prop="contact_phone" label="联系电话" width="140" />
      <el-table-column prop="notes" label="备注" min-width="150" show-overflow-tooltip />
      <el-table-column label="操作" width="140" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openDialog(row)">编辑</el-button>
          <el-popconfirm title="确定删除？" @confirm="handleDelete(row.id)">
            <template #reference>
              <el-button link type="danger">删除</el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>

    <div style="display: flex; justify-content: flex-end; margin-top: 16px">
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        layout="total, prev, pager, next"
        @current-change="loadData"
      />
    </div>

    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑单位' : '新增单位'" width="500px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item label="单位名称" prop="name">
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="简称">
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
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, Plus } from '@element-plus/icons-vue'
import { getOrganizations, createOrganization, updateOrganization, deleteOrganization } from '../../api/dict'

const tableData = ref([])
const loading = ref(false)
const keyword = ref('')
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)

const dialogVisible = ref(false)
const editingId = ref(null)
const submitting = ref(false)
const formRef = ref(null)

const defaultForm = { name: '', short_name: '', contact_person: '', contact_phone: '', notes: '' }
const form = ref({ ...defaultForm })
const rules = { name: [{ required: true, message: '请输入单位名称', trigger: 'blur' }] }

async function loadData() {
  loading.value = true
  try {
    const res = await getOrganizations({ keyword: keyword.value, page: page.value, page_size: pageSize.value })
    tableData.value = res.items
    total.value = res.total
  } finally {
    loading.value = false
  }
}

function openDialog(row) {
  editingId.value = row?.id || null
  form.value = row ? { ...row } : { ...defaultForm }
  dialogVisible.value = true
}

async function handleSubmit() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  submitting.value = true
  try {
    if (editingId.value) {
      await updateOrganization(editingId.value, form.value)
      ElMessage.success('更新成功')
    } else {
      await createOrganization(form.value)
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

async function handleDelete(id) {
  try {
    await deleteOrganization(id)
    ElMessage.success('删除成功')
    loadData()
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '删除失败')
  }
}

onMounted(() => loadData())
</script>
