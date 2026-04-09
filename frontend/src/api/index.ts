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
  res => res,
  async error => {
    if (error.response?.status === 401) {
      const token = localStorage.getItem('access_token')
      if (token) {
        // Token 过期/失效，清理并跳转登录
        localStorage.removeItem('access_token')
        window.location.href = '/login'
      }
      // 无 token（如登录请求的 401）不跳转，让调用方 catch 处理
    }
    return Promise.reject(error)
  }
)

export default api
