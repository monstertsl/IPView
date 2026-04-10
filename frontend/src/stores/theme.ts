import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'

export type ThemeMode = 'light' | 'dark'

export const useThemeStore = defineStore('theme', () => {
  // 从 localStorage 读取主题，默认为浅色
  const storedTheme = localStorage.getItem('theme') as ThemeMode | null
  const mode = ref<ThemeMode>(storedTheme || 'light')

  const isDark = computed(() => mode.value === 'dark')

  function toggleTheme() {
    mode.value = mode.value === 'light' ? 'dark' : 'light'
    localStorage.setItem('theme', mode.value)
  }

  function setTheme(newMode: ThemeMode) {
    mode.value = newMode
    localStorage.setItem('theme', mode.value)
  }

  // 监听主题变化，更新 body 类名
  watch(mode, (newMode) => {
    if (newMode === 'dark') {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  }, { immediate: true })

  return { mode, isDark, toggleTheme, setTheme }
})
