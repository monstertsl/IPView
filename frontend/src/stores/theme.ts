import { defineStore } from 'pinia'
import { computed } from 'vue'

export const useThemeStore = defineStore('theme', () => {
  localStorage.removeItem('theme')
  document.documentElement.classList.remove('dark')

  const isDark = computed(() => false)

  return { isDark }
})
