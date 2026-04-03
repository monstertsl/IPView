<template>
  <n-layout has-sider sider-placed="left" :width="collapsed ? 64 : 220" style="height: 100vh">
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
      style="background: #141c31"
    >
      <div class="logo-area" :class="{ collapsed }">
        <n-icon size="24" color="#18a058"><grid-outline /></n-icon>
        <span v-if="!collapsed" class="logo-text">IPVIEW</span>
      </div>
      <n-menu
        v-model:value="activeKey"
        :collapsed="collapsed"
        :collapsed-width="64"
        :collapsed-icon-size="22"
        :options="menuOptions"
        @update:value="handleMenuChange"
      />
    </n-layout-sider>

    <!-- Main content -->
    <n-layout>
      <!-- Header -->
      <n-layout-header bordered style="height: 56px; padding: 0 24px; display: flex; align-items: center; justify-content: space-between; background: #141c31">
        <n-text strong style="font-size: 16px">{{ currentRouteTitle }}</n-text>
        <n-space>
          <n-dropdown :options="userMenuOptions" @select="handleUserMenu">
            <n-button text style="font-size: 14px">
              <n-icon><person-outline /></n-icon>
              {{ auth.user?.username }}
            </n-button>
          </n-dropdown>
        </n-space>
      </n-layout-header>

      <!-- Page content -->
      <n-layout-content :content-style="{ padding: '16px' }" :native-scrollbar="false" style="background: #0f1523; min-height: calc(100vh - 56px)">
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
} from '@vicons/ionicons5'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const collapsed = ref(false)
const activeKey = ref(route.name as string)

const menuOptions: MenuOption[] = [
  { label: 'IP 管理', key: 'IPManage', icon: renderIcon(GridOutline) },
  { label: '用户管理', key: 'UserManage', icon: renderIcon(PeopleOutline), show: auth.user?.role === 'admin' },
  { label: '交换机管理', key: 'SwitchManage', icon: renderIcon(BusinessOutline), show: auth.user?.role === 'admin' },
  { label: '扫描管理', key: 'ScanManage', icon: renderIcon(ScanOutline), show: auth.user?.role === 'admin' },
  { label: '日志查询', key: 'LogQuery', icon: renderIcon(DocumentTextOutline), show: auth.user?.role === 'admin' },
]

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

function handleUserMenu(key: string) {
  if (key === 'logout') {
    auth.logout()
    router.push('/login')
  }
}
</script>

<style scoped>
.logo-area {
  height: 56px;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 20px;
  border-bottom: 1px solid rgba(255,255,255,0.06);
}
.logo-area.collapsed { justify-content: center; padding: 0; }
.logo-text { font-size: 18px; font-weight: 700; color: #18a058; letter-spacing: 2px; }
.fade-enter-active, .fade-leave-active { transition: opacity 0.15s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
