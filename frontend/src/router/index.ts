import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { guest: true }
  },
  {
    path: '/',
    component: () => import('@/views/Layout.vue'),
    meta: { requiresAuth: true },
    children: [
      { path: '', redirect: '/ip' },
      { path: 'ip', name: 'IPManage', component: () => import('@/views/IPManage.vue') },
      { path: 'users', name: 'UserManage', component: () => import('@/views/UserManage.vue'), meta: { admin: true } },
      { path: 'switches', name: 'SwitchManage', component: () => import('@/views/SwitchManage.vue'), meta: { admin: true } },
      { path: 'scan', name: 'ScanManage', component: () => import('@/views/ScanManage.vue'), meta: { admin: true } },
      { path: 'logs', name: 'LogQuery', component: () => import('@/views/LogQuery.vue'), meta: { admin: true } },
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach(async (to, _from, next) => {
  const auth = useAuthStore()

  // 有 token 但 user 信息丢失（页面刷新），先恢复用户信息
  if (auth.isLoggedIn && !auth.user) {
    await auth.fetchCurrentUser()
  }

  const requiresAuth = to.matched.some(record => record.meta.requiresAuth)
  const isGuest = to.matched.some(record => record.meta.guest)
  const requiresAdmin = to.matched.some(record => record.meta.admin)

  if (requiresAuth && !auth.isLoggedIn) {
    next('/login')
  } else if (isGuest && auth.isLoggedIn) {
    next('/ip')
  } else if (requiresAdmin && auth.user?.role !== 'admin') {
    next('/ip')
  } else {
    next()
  }
})

export default router
