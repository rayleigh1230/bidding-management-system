<template>
  <el-container style="height: 100vh">
    <el-aside width="220px" style="background-color: #304156">
      <div style="height: 60px; display: flex; align-items: center; justify-content: center; color: #fff; font-size: 16px; font-weight: bold">
        招标管理系统
      </div>
      <el-menu
        :default-active="activeMenu"
        background-color="#304156"
        text-color="#bfcbd9"
        active-text-color="#409eff"
        router
      >
        <el-menu-item index="/dashboard">
          <el-icon><DataBoard /></el-icon>
          <span>工作台</span>
        </el-menu-item>

        <el-sub-menu index="business">
          <template #title>
            <el-icon><Briefcase /></el-icon>
            <span>业务管理</span>
          </template>
          <el-menu-item index="/projects">
            <el-icon><Document /></el-icon>
            <span>项目管理</span>
          </el-menu-item>
          <el-menu-item index="/biddings">
            <el-icon><Bell /></el-icon>
            <span>招标信息</span>
          </el-menu-item>
          <el-menu-item index="/bids">
            <el-icon><EditPen /></el-icon>
            <span>投标信息</span>
          </el-menu-item>
          <el-menu-item index="/results">
            <el-icon><Trophy /></el-icon>
            <span>投标结果</span>
          </el-menu-item>
        </el-sub-menu>

        <el-sub-menu index="admin">
          <template #title>
            <el-icon><Setting /></el-icon>
            <span>基础数据</span>
          </template>
          <el-menu-item index="/organizations">
            <el-icon><OfficeBuilding /></el-icon>
            <span>单位库管理</span>
          </el-menu-item>
          <el-menu-item index="/platforms">
            <el-icon><Monitor /></el-icon>
            <span>平台管理</span>
          </el-menu-item>
          <el-menu-item index="/managers">
            <el-icon><User /></el-icon>
            <span>负责人管理</span>
          </el-menu-item>
          <el-menu-item index="/users">
            <el-icon><Avatar /></el-icon>
            <span>用户管理</span>
          </el-menu-item>
        </el-sub-menu>

        <el-menu-item index="/statistics">
          <el-icon><TrendCharts /></el-icon>
          <span>数据分析</span>
        </el-menu-item>

        <el-menu-item index="/logs">
          <el-icon><Notebook /></el-icon>
          <span>操作日志</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header style="display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid #e6e6e6; background: #fff">
        <span style="font-size: 16px; font-weight: 500">{{ currentTitle }}</span>
        <div style="display: flex; align-items: center; gap: 16px">
          <span style="color: #666">{{ userStore.user?.display_name }}</span>
          <el-button text @click="handleLogout">
            <el-icon><SwitchButton /></el-icon>
            退出
          </el-button>
        </div>
      </el-header>
      <el-main style="background-color: #f0f2f5; padding: 20px">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const activeMenu = computed(() => {
  const path = route.path
  if (path.startsWith('/projects')) return '/projects'
  if (path.startsWith('/biddings')) return '/biddings'
  if (path.startsWith('/bids')) return '/bids'
  if (path.startsWith('/results')) return '/results'
  return path
})

const currentTitle = computed(() => route.meta.title || '招标管理系统')

function handleLogout() {
  userStore.logout()
  router.push('/login')
}
</script>
