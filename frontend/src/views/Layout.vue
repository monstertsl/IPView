<template>
  <n-layout style="height: 100vh">
    <n-layout-header bordered class="top-header">
      <a class="brand" href="https://github.com/monstertsl/IPView" target="_blank" rel="noopener noreferrer">
        <span class="brand-name">IPVIEW</span>
      </a>
      <span class="brand-divider" aria-hidden="true" />

      <nav class="top-nav" aria-label="主导航">
        <button
          v-for="item in navigationItems"
          :key="item.key"
          type="button"
          class="nav-item"
          :class="{ active: activeKey === item.key }"
          :aria-label="item.label"
          :title="item.label"
          @click="handleMenuChange(item.key)"
        >
          <n-icon class="nav-icon" size="20"><component :is="item.icon" /></n-icon>
          <span class="nav-label">{{ item.label }}</span>
        </button>
      </nav>

      <n-dropdown :options="userMenuOptions" @select="handleUserMenu">
        <n-button text class="user-btn" :aria-label="auth.user?.username">
          <n-icon size="18"><person-outline /></n-icon>
          <span class="user-name">{{ auth.user?.username }}</span>
        </n-button>
      </n-dropdown>
    </n-layout-header>

    <n-modal v-model:show="showChangePassword" preset="card" title="修改密码" style="width: 420px" class="custom-modal">
      <n-form :model="passwordForm" label-placement="top">
        <n-form-item label="当前密码" required>
          <n-input v-model:value="passwordForm.oldPassword" type="password" show-password-on="click" placeholder="请输入当前密码" />
        </n-form-item>
        <n-form-item label="新密码" required>
          <n-input v-model:value="passwordForm.newPassword" type="password" show-password-on="click" placeholder="至少 8 位" />
        </n-form-item>
        <n-form-item label="确认新密码" required>
          <n-input v-model:value="passwordForm.confirmPassword" type="password" show-password-on="click" placeholder="再次输入新密码" @keyup.enter="savePassword" />
        </n-form-item>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button @click="showChangePassword = false">取消</n-button>
          <n-button type="primary" :loading="changingPassword" @click="savePassword">确认修改</n-button>
        </n-space>
      </template>
    </n-modal>

    <n-layout-content :content-style="{ padding: '20px 24px' }" :native-scrollbar="false" class="main-content">
      <div class="page-heading">{{ currentRouteTitle }}</div>
      <router-view v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </n-layout-content>
  </n-layout>
</template>

<script setup lang="ts">
import { ref, reactive, computed, h, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { NIcon, useMessage } from 'naive-ui'
import { useAuthStore } from '@/stores/auth'
import api from '@/api'

function renderIcon(icon: any) {
  return () => h(NIcon, null, { default: () => h(icon) })
}

import {
  GridOutline,
  PersonOutline,
  LogOutOutline,
  LockClosedOutline,
  BusinessOutline,
  ScanOutline,
  DocumentTextOutline,
  PeopleOutline,
} from '@vicons/ionicons5'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const message = useMessage()
const activeKey = ref(route.name as string)
const showChangePassword = ref(false)
const changingPassword = ref(false)
const passwordForm = reactive({ oldPassword: '', newPassword: '', confirmPassword: '' })

const navigationItems = computed(() => [
  { label: 'IP 管理', key: 'IPManage', icon: GridOutline, adminOnly: false },
  { label: '用户管理', key: 'UserManage', icon: PeopleOutline, adminOnly: true },
  { label: '交换机管理', key: 'SwitchManage', icon: BusinessOutline, adminOnly: true },
  { label: '扫描管理', key: 'ScanManage', icon: ScanOutline, adminOnly: true },
  { label: '日志查询', key: 'LogQuery', icon: DocumentTextOutline, adminOnly: true },
].filter(item => !item.adminOnly || auth.user?.role === 'admin'))

watch(() => route.name, (name) => {
  if (typeof name === 'string') activeKey.value = name
})

const currentRouteTitle = computed(() => {
  const titles: Record<string, string> = {
    IPManage: 'IP 管理',
    UserManage: '用户管理',
    SwitchManage: '交换机管理',
    ScanManage: '扫描管理',
    LogQuery: '日志查询',
  }
  return titles[activeKey.value] || 'IPVIEW'
})

const userMenuOptions = [
  { label: '修改密码', key: 'change-password', icon: renderIcon(LockClosedOutline) },
  { type: 'divider', key: 'user-menu-divider' },
  { label: '退出登录', key: 'logout', icon: renderIcon(LogOutOutline) },
]

function handleMenuChange(key: string) {
  activeKey.value = key
  router.push({ name: key })
}

async function handleUserMenu(key: string) {
  if (key === 'change-password') {
    passwordForm.oldPassword = ''
    passwordForm.newPassword = ''
    passwordForm.confirmPassword = ''
    showChangePassword.value = true
    return
  }

  if (key === 'logout') {
    await auth.logout()
    window.location.href = '/login'
  }
}

async function savePassword() {
  if (!passwordForm.oldPassword || !passwordForm.newPassword || !passwordForm.confirmPassword) {
    message.warning('请填写完整的密码信息')
    return
  }
  if (passwordForm.newPassword.length < 8) {
    message.warning('新密码至少需要 8 位')
    return
  }
  if (passwordForm.newPassword !== passwordForm.confirmPassword) {
    message.warning('两次输入的新密码不一致')
    return
  }
  if (!auth.user?.id) {
    message.error('无法获取当前用户信息，请重新登录')
    return
  }

  changingPassword.value = true
  try {
    await api.post(`/users/${auth.user.id}/password`, {
      old_password: passwordForm.oldPassword,
      new_password: passwordForm.newPassword,
    })
    message.success('密码修改成功')
    showChangePassword.value = false
  } catch (error: any) {
    message.error(error.response?.data?.detail || '密码修改失败')
  } finally {
    changingPassword.value = false
  }
}
</script>

<style scoped>
.top-header {
  height: 55px;
  padding: 0 24px;
  display: flex;
  align-items: center;
  gap: 24px;
  background: #1b6b4e !important;
  border-bottom: 1px solid #15553e !important;
}

.brand {
  display: flex;
  flex: none;
  align-items: center;
  color: inherit;
  text-decoration: none;
}

.brand-name {
  color: #ffffff;
  font-family: var(--font-mono);
  font-size: 18px;
  font-weight: 600;
}

.brand-divider {
  width: 2px;
  height: 20px;
  flex: none;
  margin-right: -12px;
  background: #0f4b35;
  border-radius: 1px;
}

.top-nav {
  display: flex;
  flex: 1;
  align-self: stretch;
  align-items: stretch;
  justify-content: flex-start;
  gap: 4px;
  min-width: 0;
}

.nav-item {
  position: relative;
  display: flex;
  flex: none;
  min-width: 0;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 0 16px;
  border: 0;
  background: transparent;
  color: rgba(255, 255, 255, 0.78);
  cursor: pointer;
  font: inherit;
  font-family: var(--font-sans);
  font-size: 16px;
  white-space: nowrap;
  transition: color 0.15s ease, background-color 0.15s ease;
}

.nav-item:hover {
  background: rgba(255, 255, 255, 0.08);
  color: #ffffff;
}

.nav-item.active {
  background: transparent;
  color: #ffffff;
  font-weight: 600;
}

.nav-icon {
  display: none;
}

.top-header .user-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #ffffff !important;
  white-space: nowrap;
  --n-text-color: #ffffff;
  --n-text-color-hover: #ffffff;
  --n-text-color-pressed: #ffffff;
  --n-text-color-focus: #ffffff;
}

.top-header .user-btn:hover {
  color: #ffffff !important;
}

.top-header .user-btn:active,
.top-header .user-btn:focus {
  color: #ffffff !important;
}

.top-header :deep(.user-btn .n-button__content),
.top-header :deep(.user-btn .n-icon) {
  color: #ffffff !important;
}

.main-content {
  min-height: calc(100vh - 55px);
}

.page-heading {
  margin-bottom: 16px;
  color: #1f2937;
  font-family: var(--font-sans);
  font-size: 18px;
  font-weight: 600;
}

@media (max-width: 900px), (orientation: portrait) {
  .top-header {
    height: 55px;
    gap: 8px;
    padding: 0 12px;
  }

  .brand {
    gap: 0;
  }

  .brand-divider {
    margin-left: 8px;
  }

  .user-name {
    display: none;
  }

  .top-nav {
    justify-content: center;
    gap: 2px;
  }

  .nav-item {
    flex: 1 1 40px;
    min-width: 36px;
    max-width: 60px;
    padding: 0 4px;
  }

  .nav-icon {
    display: inline-flex;
  }

  .nav-label {
    display: none;
  }

  .top-header .user-btn {
    padding: 6px;
  }

  .main-content {
    min-height: calc(100vh - 55px);
  }
}

@media (max-width: 480px) {
  .top-header {
    gap: 4px;
    padding: 0 8px;
  }

  .top-nav {
    gap: 0;
  }

  .nav-item {
    min-width: 26px;
    max-width: 42px;
    padding: 0 2px;
  }
}

.sidebar {
  background: #1a1f2e !important;
  border-right: 1px solid #2d3548 !important;
  transition: background-color 0.3s ease;
}

/* Light mode sidebar */
html:not(.dark) .sidebar {
  background: #ffffff !important;
  border-right: 1px solid #e5e7eb !important;
}

.logo-area {
  height: 56px;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 20px;
  border-bottom: 1px solid #2d3548;
  background: linear-gradient(135deg, #242b3d 0%, #1a1f2e 100%);
}

html:not(.dark) .logo-area {
  border-bottom: 1px solid #e5e7eb;
  background: linear-gradient(135deg, #f8fafc 0%, #ffffff 100%);
}

.logo-area.collapsed { 
  justify-content: center; 
  padding: 0; 
}

.logo-icon {
  color: #10b981;
  display: flex;
  align-items: center;
  justify-content: center;
}

.logo-icon img {
  width: 32px;
  height: 24px;
  object-fit: contain;
  border-radius: 4px;
}

.logo-text {
  font-family: var(--font-sans);
  font-size: 18px; 
  font-weight: 600; 
  color: #fff; 
  letter-spacing: 2px; 
}

html:not(.dark) .logo-text {
  color: #1f2937;
}

.header {
  height: 56px;
  padding: 0 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #1a1f2e !important;
  border-bottom: 1px solid #2d3548 !important;
  transition: background-color 0.3s ease, border-color 0.3s ease;
}

/* Light mode header */
.header-light {
  background: #ffffff !important;
  border-bottom: 1px solid #e5e7eb !important;
}

.header-title {
  font-size: 16px;
  color: #fff;
}

.header-light .header-title {
  color: #1f2937 !important;
}

.user-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #a0aec0 !important;
  font-size: 14px;
}

.user-btn:hover {
  color: #10b981 !important;
}

html:not(.dark) .user-btn {
  color: #6b7280 !important;
}

html:not(.dark) .user-btn:hover {
  color: #10b981 !important;
}

.main-content {
  background: #141820 !important;
  min-height: calc(100vh - 56px);
  transition: background-color 0.3s ease;
}

html:not(.dark) .main-content {
  background: #f5f7fa !important;
}

/* Menu styles */
:deep(.sidebar-menu) {
  --n-item-color-active: rgba(16, 185, 129, 0.1);
  --n-item-color-hover: rgba(16, 185, 129, 0.05);
  --n-item-text-color: #a0aec0;
  --n-item-text-color-active: #10b981;
  --n-item-text-color-hover: #fff;
  --n-item-icon-color: #64748b;
  --n-item-icon-color-active: #10b981;
  --n-item-icon-color-hover: #fff;
  --n-arrow-color: #64748b;
  --n-arrow-color-active: #10b981;
  background: transparent;
}

html:not(.dark) :deep(.sidebar-menu) {
  --n-item-text-color: #6b7280;
  --n-item-text-color-hover: #1f2937;
  --n-item-icon-color: #9ca3af;
  --n-item-icon-color-hover: #1f2937;
}

:deep(.n-menu-item-content--selected) {
  border-right: 3px solid #10b981;
}

:deep(.n-layout-sider__border) {
  background-color: #2d3548 !important;
}

html:not(.dark) :deep(.n-layout-sider__border) {
  background-color: #e5e7eb !important;
}

:deep(.n-layout-sider-scroll-container) {
  background: #1a1f2e;
}

html:not(.dark) :deep(.n-layout-sider-scroll-container) {
  background: #ffffff;
}

:deep(.n-layout-toggle-button) {
  background: #242b3d !important;
  color: #a0aec0 !important;
  border: 1px solid #3a4459 !important;
}

:deep(.n-layout-toggle-button:hover) {
  color: #10b981 !important;
  border-color: #10b981 !important;
}

html:not(.dark) :deep(.n-layout-toggle-button) {
  background: #ffffff !important;
  color: #6b7280 !important;
  border: 1px solid #e5e7eb !important;
}

html:not(.dark) :deep(.n-layout-toggle-button:hover) {
  color: #10b981 !important;
  border-color: #10b981 !important;
}

/* Dropdown styles */
:deep(.n-dropdown-option) {
  --n-option-color-hover: rgba(16, 185, 129, 0.1);
  --n-option-text-color: #a0aec0;
  --n-option-text-color-hover: #10b981;
}

/* Transitions */
.fade-enter-active, .fade-leave-active { 
  transition: opacity 0.15s ease; 
}
.fade-enter-from, .fade-leave-to { 
  opacity: 0; 
}
</style>
