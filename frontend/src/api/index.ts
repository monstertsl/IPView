import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000
})

api.interceptors.request.use(config => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  res => {
    // M2 sliding-session: rotate token when backend returns a refreshed one.
    const refreshed = res.headers?.['x-refreshed-token'] || res.headers?.['X-Refreshed-Token']
    if (refreshed) {
      localStorage.setItem('access_token', refreshed)
    }
    return res
  },
  async error => {
    if (error.response?.status === 401) {
      const token = localStorage.getItem('access_token')
      if (token) {
        // Token expired / revoked — drop local state and go to login.
        localStorage.removeItem('access_token')
        window.location.href = '/login'
      }
      // Let login-page 401s bubble up so the caller can show the error.
    }
    return Promise.reject(error)
  }
)

export default api
