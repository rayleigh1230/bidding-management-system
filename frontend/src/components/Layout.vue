<template>
  <el-container style="height: 100vh">
    <el-aside width="220px" style="background-color: #304156; display: flex; flex-direction: column">
      <div style="height: 60px; display: flex; align-items: center; justify-content: center; color: #fff; font-size: 16px; font-weight: bold; flex-shrink: 0">
        招标管理系统
      </div>
      <div style="flex: 1; overflow-y: auto">
        <el-menu
          :default-active="activeMenu"
          background-color="#304156"
          text-color="#bfcbd9"
          active-text-color="#409eff"
          @select="handleMenuSelect"
        >
          <el-menu-item index="/dashboard">
            <el-icon><DataBoard /></el-icon>
            <span>工作台</span>
          </el-menu-item>

          <el-menu-item index="/projects">
            <el-icon><Document /></el-icon>
            <span>项目管理</span>
          </el-menu-item>

          <el-menu-item index="/statistics">
            <el-icon><TrendCharts /></el-icon>
            <span>数据分析</span>
          </el-menu-item>

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

          <el-menu-item index="/scrape/history">
            <el-icon><Download /></el-icon>
            <span>抓取记录</span>
          </el-menu-item>

          <el-menu-item index="/logs">
            <el-icon><Notebook /></el-icon>
            <span>操作日志</span>
          </el-menu-item>
        </el-menu>
      </div>
      <SidebarHelp />
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
import SidebarHelp from './SidebarHelp.vue'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const activeMenu = computed(() => {
  const path = route.path
  if (path.startsWith('/projects')) return '/projects'
  return path
})

const currentTitle = computed(() => route.meta.title || '招标管理系统')

function handleLogout() {
  userStore.logout()
  router.push('/login')
}

function handleMenuSelect(index) {
  // 点击侧边栏"项目管理"时清除保存的页码，让列表回到第 1 页
  // 这样从详情返回（浏览器后退）会保留页码，而点侧边栏会回到第 1 页
  if (index === '/projects') {
    sessionStorage.removeItem('projectListPage')
  }
  router.push(index)
}
</script>
