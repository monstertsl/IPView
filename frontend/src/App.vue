<template>
  <n-config-provider :theme="currentTheme" :theme-overrides="themeOverrides">
    <n-message-provider>
      <n-dialog-provider>
        <n-notification-provider>
          <router-view />
        </n-notification-provider>
      </n-dialog-provider>
    </n-message-provider>
  </n-config-provider>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { darkTheme, type GlobalThemeOverrides } from 'naive-ui'
import { useThemeStore } from '@/stores/theme'

const themeStore = useThemeStore()

// 根据主题状态返回对应主题
const currentTheme = computed(() => themeStore.isDark ? darkTheme : null)

// 浅色主题样式覆盖
const lightThemeOverrides: GlobalThemeOverrides = {
  common: {
    primaryColor: '#10b981',
    primaryColorHover: '#34d399',
    primaryColorPressed: '#059669',
    borderRadius: '6px',
    borderRadiusSmall: '4px',
  },
  Card: {
    color: '#ffffff',
    colorModal: '#ffffff',
    borderRadius: '8px',
  },
  DataTable: {
    thColor: '#f8fafc',
    tdColor: '#ffffff',
    thTextColor: '#374151',
    tdTextColor: '#1f2937',
    borderColor: '#e5e7eb',
    thColorHover: '#f1f5f9',
    tdColorHover: '#f8fafc',
  },
  Button: {
    borderRadiusMedium: '6px',
  },
  Menu: {
    itemColorActive: 'rgba(16, 185, 129, 0.15)',
    itemTextColorActive: '#10b981',
    itemIconColorActive: '#10b981',
    itemTextColorActiveHover: '#10b981',
    itemIconColorActiveHover: '#10b981',
  },
  Tag: {
    borderRadius: '4px',
  }
}

// 深色主题样式覆盖
const darkThemeOverrides: GlobalThemeOverrides = {
  common: {
    primaryColor: '#10b981',
    primaryColorHover: '#34d399',
    primaryColorPressed: '#059669',
    borderRadius: '6px',
    borderRadiusSmall: '4px',
  },
  Card: {
    color: '#1e293b',
    colorModal: '#1e293b',
    borderRadius: '8px',
  },
  DataTable: {
    thColor: '#1e293b',
    tdColor: '#0f172a',
    thTextColor: '#e2e8f0',
    tdTextColor: '#f1f5f9',
    borderColor: '#334155',
    thColorHover: '#334155',
    tdColorHover: '#1e293b',
  },
  Button: {
    borderRadiusMedium: '6px',
  },
  Menu: {
    itemColorActive: 'rgba(16, 185, 129, 0.15)',
    itemTextColorActive: '#10b981',
    itemIconColorActive: '#10b981',
    itemTextColorActiveHover: '#10b981',
    itemIconColorActiveHover: '#10b981',
  },
  Tag: {
    borderRadius: '4px',
  }
}

const themeOverrides = computed(() => themeStore.isDark ? darkThemeOverrides : lightThemeOverrides)
</script>

<style>
/* Global styles */
body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  transition: background-color 0.3s ease, color 0.3s ease;
}

/* 浅色主题默认背景 */
html:not(.dark) body {
  background-color: #f5f7fa;
  color: #1f2937;
}

/* 深色主题背景 */
html.dark body {
  background-color: #0f172a;
  color: #f1f5f9;
}

/* Custom scrollbar */
::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}
::-webkit-scrollbar-track {
  background: transparent;
}
::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.15);
  border-radius: 3px;
}
::-webkit-scrollbar-thumb:hover {
  background: rgba(0, 0, 0, 0.25);
}

html.dark ::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.15);
}
html.dark ::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.25);
}
</style>
