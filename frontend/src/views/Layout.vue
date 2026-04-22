<template>
  <n-layout has-sider sider-placed="left" style="height: 100vh">
    <!-- Sidebar -->
    <n-layout-sider
      bordered
      collapse-mode="width"
      :collapsed-width="64"
      :width="220"
      :collapsed="collapsed"
      show-trigger
      @collapse="collapsed = true"
      @expand="collapsed = false"
      :native-scrollbar="false"
      class="sidebar"
    >
      <div class="logo-area" :class="{ collapsed }">
        <div class="logo-icon">
          <svg viewBox="0 0 24 24" width="28" height="28" fill="currentColor">
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z"/>
          </svg>
        </div>
        <span v-if="!collapsed" class="logo-text">IPVIEW</span>
      </div>
      <n-menu
        v-model:value="activeKey"
        :collapsed="collapsed"
        :collapsed-width="64"
        :collapsed-icon-size="22"
        :options="menuOptions"
        @update:value="handleMenuChange"
        class="sidebar-menu"
      />
    </n-layout-sider>

    <!-- Main content -->
    <n-layout>
      <!-- Header -->
      <n-layout-header bordered class="header" :class="{ 'header-light': !themeStore.isDark }">
        <n-text strong class="header-title">{{ currentRouteTitle }}</n-text>
        <n-space align="center" :size="16">
          <!-- Theme Toggle Button -->
          <n-tooltip trigger="hover">
            <template #trigger>
              <n-button text class="theme-toggle-btn" @click="themeStore.toggleTheme">
                <n-icon size="20">
                  <sunny-outline v-if="themeStore.isDark" />
                  <moon-outline v-else />
                </n-icon>
              </n-button>
            </template>
            {{ themeStore.isDark ? '切换到浅色模式' : '切换到深色模式' }}
          </n-tooltip>
          
          <n-dropdown :options="userMenuOptions" @select="handleUserMenu">
            <n-button text class="user-btn">
              <n-icon size="18"><person-outline /></n-icon>
              <span>{{ auth.user?.username }}</span>
            </n-button>
          </n-dropdown>
        </n-space>
      </n-layout-header>

      <!-- Page content -->
      <n-layout-content :content-style="{ padding: '20px 24px' }" :native-scrollbar="false" class="main-content">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </n-layout-content>
    </n-layout>
  </n-layout>
</template>

<script setup lang="ts">
import { ref, computed, h } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { NIcon, type MenuOption } from 'naive-ui'
import { useAuthStore } from '@/stores/auth'
import { useThemeStore } from '@/stores/theme'

function renderIcon(icon: any) {
  return () => h(NIcon, null, { default: () => h(icon) })
}

import {
  GridOutline,
  PersonOutline,
  LogOutOutline,
  BusinessOutline,
  ScanOutline,
  DocumentTextOutline,
  PeopleOutline,
  SunnyOutline,
  MoonOutline,
} from '@vicons/ionicons5'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const themeStore = useThemeStore()
const collapsed = ref(false)
const activeKey = ref(route.name as string)

const menuOptions = computed<MenuOption[]>(() => [
  { label: 'IP 管理', key: 'IPManage', icon: renderIcon(GridOutline) },
  { label: '用户管理', key: 'UserManage', icon: renderIcon(PeopleOutline), show: auth.user?.role === 'admin' },
  { label: '交换机管理', key: 'SwitchManage', icon: renderIcon(BusinessOutline), show: auth.user?.role === 'admin' },
  { label: '扫描管理', key: 'ScanManage', icon: renderIcon(ScanOutline), show: auth.user?.role === 'admin' },
  { label: '日志查询', key: 'LogQuery', icon: renderIcon(DocumentTextOutline), show: auth.user?.role === 'admin' },
])

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
  { label: '退出登录', key: 'logout', icon: renderIcon(LogOutOutline) }
]

function handleMenuChange(key: string) {
  activeKey.value = key
  router.push({ name: key })
}

async function handleUserMenu(key: string) {
  if (key === 'logout') {
    await auth.logout()
    window.location.href = '/login'
  }
}
</script>

<style scoped>
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

.logo-text { 
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

/* Theme toggle button */
.theme-toggle-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fcd34d !important;
}

.theme-toggle-btn:hover {
  color: #fde68a !important;
}

html:not(.dark) .theme-toggle-btn {
  color: #6b7280 !important;
}

html:not(.dark) .theme-toggle-btn:hover {
  color: #374151 !important;
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
