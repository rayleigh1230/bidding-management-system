import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '../stores/user'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
    meta: { public: true },
  },
  {
    path: '/',
    component: () => import('../components/Layout.vue'),
    redirect: '/dashboard',
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('../views/Dashboard.vue'),
        meta: { title: '工作台' },
      },
      {
        path: 'projects',
        name: 'ProjectList',
        component: () => import('../views/project/ProjectList.vue'),
        meta: { title: '项目管理' },
      },
      {
        path: 'projects/:id',
        name: 'ProjectDetail',
        component: () => import('../views/project/ProjectDetail.vue'),
        meta: { title: '项目详情' },
      },
      {
        path: 'statistics',
        name: 'Statistics',
        component: () => import('../views/stats/Statistics.vue'),
        meta: { title: '数据分析' },
      },
      {
        path: 'organizations',
        name: 'OrganizationList',
        component: () => import('../views/admin/OrganizationList.vue'),
        meta: { title: '单位库管理' },
      },
      {
        path: 'platforms',
        name: 'PlatformList',
        component: () => import('../views/admin/PlatformList.vue'),
        meta: { title: '平台管理' },
      },
      {
        path: 'managers',
        name: 'ManagerList',
        component: () => import('../views/admin/ManagerList.vue'),
        meta: { title: '负责人管理' },
      },
      {
        path: 'users',
        name: 'UserList',
        component: () => import('../views/admin/UserList.vue'),
        meta: { title: '用户管理' },
      },
      {
        path: 'logs',
        name: 'LogList',
        component: () => import('../views/LogList.vue'),
        meta: { title: '操作日志' },
      },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to, from, next) => {
  if (to.meta.public) {
    next()
    return
  }
  const userStore = useUserStore()
  if (!userStore.token) {
    next('/login')
  } else {
    next()
  }
})

export default router
