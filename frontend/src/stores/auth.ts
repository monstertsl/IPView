import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/api'
import type { User } from '@/types'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem('access_token'))
  const user = ref<User | null>(null)

  const isLoggedIn = computed(() => !!token.value)

  async function login(username: string, password?: string, totpCode?: string) {
    const payload: any = { username }
    if (password) payload.password = password
    if (totpCode) payload.totp_code = totpCode
    
    const res = await api.post<{ access_token: string; user: User }>('/auth/login', payload)
    token.value = res.data.access_token
    user.value = res.data.user
    localStorage.setItem('access_token', res.data.access_token)
    return res.data
  }

  function logout() {
    token.value = null
    user.value = null
    localStorage.removeItem('access_token')
  }

  async function fetchCurrentUser() {
    if (!token.value) return
    try {
      const payload = JSON.parse(atob(token.value.split('.')[1]))
      user.value = { id: payload.sub, username: payload.username, role: payload.role } as User
    } catch {
      // Token 损坏或格式无效，清理状态
      logout()
    }
  }

  return { token, user, isLoggedIn, login, logout, fetchCurrentUser }
})
