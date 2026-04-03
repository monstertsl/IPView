import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/api'
import type { User } from '@/types'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem('access_token'))
  const user = ref<User | null>(null)

  const isLoggedIn = computed(() => !!token.value)

  async function login(username: string, password: string, totpCode?: string) {
    const res = await api.post<{ access_token: string; user: User }>('/auth/login', {
      username, password, totp_code: totpCode
    })
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
    // decode token payload (simplified - in prod use jwt decode lib)
    const payload = JSON.parse(atob(token.value.split('.')[1]))
    user.value = { id: payload.sub, username: payload.username, role: payload.role } as User
  }

  return { token, user, isLoggedIn, login, logout, fetchCurrentUser }
})
