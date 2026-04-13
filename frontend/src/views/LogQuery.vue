<template>
  <div class="log-query">
    <n-tabs type="line" animated class="custom-tabs">
      <!-- Login logs -->
      <n-tab-pane name="login" tab="登录日志">
        <n-card :bordered="false" size="small" class="log-card">
          <n-space style="margin-bottom: 16px" :wrap="true" align="center">
            <n-input v-model:value="loginQ.username" placeholder="用户名" clearable style="width: 140px" />
            <n-select v-model:value="loginQ.success" :options="successOptions" placeholder="状态" clearable style="width: 120px" />
            <n-input v-model:value="loginQ.ip_address" placeholder="IP 地址" clearable style="width: 140px" />
            <n-date-picker v-model:value="loginQ.range" type="daterange" clearable style="width: 280px" />
            <n-button type="primary" @click="loadLoginLogs">
              <template #icon><n-icon><search-outline /></n-icon></template>
              查询
            </n-button>
            <n-button type="warning" @click="cleanupLogs('login')" :loading="cleaning">清理旧日志</n-button>
          </n-space>
          <n-data-table 
            :columns="loginColumns" 
            :data="loginLogs" 
            :bordered="false" 
            size="small" 
            :pagination="loginPagination"
            :loading="loadingLogin"
            class="log-table"
          />
        </n-card>
      </n-tab-pane>

      <!-- Scan logs -->
      <n-tab-pane name="scan" tab="扫描日志">
        <n-card :bordered="false" size="small" class="log-card">
          <n-space style="margin-bottom: 16px">
            <n-button type="primary" @click="loadScanLogs">
              <template #icon><n-icon><refresh-outline /></n-icon></template>
              刷新
            </n-button>
            <n-button type="warning" @click="cleanupLogs('scan')" :loading="cleaning">清理旧日志</n-button>
          </n-space>
          <n-data-table 
            :columns="scanColumns" 
            :data="scanLogs" 
            :bordered="false" 
            size="small"
            :loading="loadingScan"
            :pagination="scanPagination"
            class="log-table"
          />
        </n-card>
      </n-tab-pane>
    </n-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, h } from 'vue'
import { useMessage, NTag, NButton, NIcon } from 'naive-ui'
import { SearchOutline, RefreshOutline } from '@vicons/ionicons5'
import { formatDateTime } from '@/utils/time'
import api from '@/api'

const message = useMessage()
const cleaning = ref(false)
const loadingLogin = ref(false)
const loadingScan = ref(false)
const loginLogs = ref<any[]>([])
const scanLogs = ref<any[]>([])

function createPagination() {
  const pagination = reactive({
    page: 1,
    pageSize: 10,
    showSizePicker: true,
    pageSizes: [10, 20, 50, 100],
    onUpdatePage: (p: number) => { pagination.page = p },
    onUpdatePageSize: (ps: number) => { pagination.pageSize = ps; pagination.page = 1 },
  })
  return pagination
}

const loginPagination = createPagination()
const scanPagination = createPagination()
const loginQ = reactive({
  username: '', 
  success: null as null | boolean, 
  ip_address: '', 
  range: null as null | [number, number] 
})

const successOptions = [
  { label: '成功', value: true }, 
  { label: '失败', value: false }
]

const loginColumns = [
  { title: '用户名', key: 'username', width: 120 },
  { 
    title: '状态', 
    key: 'success', 
    width: 80,
    render: (r: any) => h(NTag, { 
      type: r.success ? 'success' : 'error', 
      size: 'small',
      bordered: false
    }, { default: () => r.success ? '成功' : '失败' }) 
  },
  { title: 'IP 地址', key: 'ip_address', width: 140 },
  { title: 'User-Agent', key: 'user_agent', ellipsis: { tooltip: true } },
  { title: '消息', key: 'message', ellipsis: { tooltip: true } },
  { 
    title: '时间', 
    key: 'created_at', 
    width: 180,
    render: (r: any) => formatDateTime(r.created_at)
  },
]

const scanColumns = [
  { 
    title: '状态', 
    key: 'status', 
    width: 90,
    render: (r: any) => h(NTag, { 
      type: r.status === 'SUCCESS' ? 'success' : r.status === 'PARTIAL' ? 'warning' : r.status === 'FAILED' ? 'error' : 'info', 
      size: 'small',
      bordered: false
    }, { default: () => r.status }) 
  },
  { title: '触发', key: 'triggered_by', width: 90 },
  { title: '总 IPs', key: 'total_ips', width: 80 },
  { title: '更新', key: 'updated_ips', width: 80 },
  { title: '耗时(s)', key: 'duration', width: 80 },
  { 
    title: '消息', 
    key: 'message',
    ellipsis: { tooltip: true },
    render: (r: any) => {
      if (r.error_message) return r.error_message
      if (r.status === 'SUCCESS') return `扫描完成，共 ${r.total_ips} 个 IP，更新 ${r.updated_ips} 个`
      return '-'
    }
  },
  { 
    title: '时间', 
    key: 'created_at', 
    width: 180,
    render: (r: any) => formatDateTime(r.created_at)
  },
]

onMounted(async () => {
  await loadLoginLogs()
  await loadScanLogs()
})

async function loadLoginLogs() {
  loadingLogin.value = true
  try {
    const params: any = {}
    if (loginQ.username) params.username = loginQ.username
    if (loginQ.success !== null) params.success = loginQ.success
    if (loginQ.ip_address) params.ip_address = loginQ.ip_address
    if (loginQ.range) {
      params.start_date = new Date(loginQ.range[0]).toISOString()
      params.end_date = new Date(loginQ.range[1]).toISOString()
    }
    const res = await api.get('/logs/login', { params })
    if (res.data?.items) {
      loginLogs.value = res.data.items
    } else if (Array.isArray(res.data)) {
      loginLogs.value = res.data
    } else {
      loginLogs.value = []
    }
  } catch (e: any) { 
    message.error(e.response?.data?.detail || '加载登录日志失败') 
    loginLogs.value = []
  } finally {
    loadingLogin.value = false
  }
}

async function loadScanLogs() {
  loadingScan.value = true
  try {
    const res = await api.get('/scan/tasks')
    scanLogs.value = res.data?.items || (Array.isArray(res.data) ? res.data : [])
  } catch (e: any) { 
    scanLogs.value = []
  } finally {
    loadingScan.value = false
  }
}

async function cleanupLogs(type: 'login' | 'scan') {
  const days = parseInt(prompt(`请输入保留天数（删除 ${type === 'login' ? '登录' : '扫描'} 日志中早于此天数的记录）：`, '90') || '0')
  if (!days || days <= 0) {
    message.warning('请输入有效的天数')
    return
  }
  cleaning.value = true
  try {
    const res = await api.post('/logs/cleanup', { type, days })
    message.success(res.data.message || '清理成功')
    if (type === 'login') await loadLoginLogs()
    else await loadScanLogs()
  } catch (e: any) { 
    message.error(e.response?.data?.detail || '清理失败') 
  } finally { 
    cleaning.value = false 
  }
}
</script>

<style scoped>
.log-query { padding: 0; }
.log-table { border-radius: 6px; overflow: hidden; }
</style>
