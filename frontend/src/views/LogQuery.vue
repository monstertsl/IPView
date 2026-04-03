<template>
  <div>
    <n-tabs type="line" animated>
      <!-- Login logs -->
      <n-tab-pane name="login" tab="登录日志">
        <n-card :bordered="false" size="small">
          <n-space style="margin-bottom: 12px" :wrap="false">
            <n-input v-model:value="loginQ.username" placeholder="用户名" clearable style="width: 140px" />
            <n-select v-model:value="loginQ.success" :options="successOptions" placeholder="状态" clearable style="width: 120px" />
            <n-input v-model:value="loginQ.ip_address" placeholder="IP 地址" clearable style="width: 140px" />
            <n-date-picker v-model:value="loginQ.range" type="daterange" clearable style="width: 260px" />
            <n-button @click="loadLoginLogs">查询</n-button>
            <n-button @click="cleanupLogs('login')" type="warning" :loading="cleaning">清理旧日志</n-button>
          </n-space>
          <n-data-table :columns="loginColumns" :data="loginLogs" :bordered="false" size="small" :pagination="loginPagination" />
        </n-card>
      </n-tab-pane>

      <!-- Scan logs -->
      <n-tab-pane name="scan" tab="扫描日志">
        <n-card :bordered="false" size="small">
          <n-space style="margin-bottom: 12px">
            <n-button @click="loadScanLogs">刷新</n-button>
            <n-button @click="cleanupLogs('scan')" type="warning" :loading="cleaning">清理旧日志</n-button>
          </n-space>
          <n-data-table :columns="scanColumns" :data="scanLogs" :bordered="false" size="small" />
        </n-card>
      </n-tab-pane>
    </n-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useMessage, NTag, NButton } from 'naive-ui'
import { h } from 'vue'
import api from '@/api'

const message = useMessage()
const cleaning = ref(false)
const loginLogs = ref<any[]>([])
const scanLogs = ref<any[]>([])

const loginQ = reactive({ username: '', success: null as null | boolean, ip_address: '', range: null as null | [number, number] })
const successOptions = [{ label: '成功', value: true }, { label: '失败', value: false }]
const loginPagination = { page: 1, pageSize: 20 }

const loginColumns = [
  { title: '用户名', key: 'username' },
  { title: '状态', key: 'success', render: (r: any) => h(NTag, { type: r.success ? 'success' : 'error', size: 'small' }, { default: () => r.success ? '成功' : '失败' }) },
  { title: 'IP', key: 'ip_address' },
  { title: 'User-Agent', key: 'user_agent', ellipsis: true },
  { title: '消息', key: 'message', ellipsis: true },
  { title: '时间', key: 'created_at', render: (r: any) => new Date(r.created_at).toLocaleString('zh-CN') },
]

const scanColumns = [
  { title: '任务', key: 'task_id', ellipsis: true },
  { title: '状态', key: 'status', render: (r: any) => h(NTag, { type: r.status === 'SUCCESS' ? 'success' : 'error', size: 'small' }, { default: () => r.status }) },
  { title: '消息', key: 'message', ellipsis: true },
  { title: '耗时(秒)', key: 'duration' },
  { title: '时间', key: 'created_at', render: (r: any) => new Date(r.created_at).toLocaleString('zh-CN') },
]

onMounted(async () => {
  await loadLoginLogs()
  await loadScanLogs()
})

async function loadLoginLogs() {
  try {
    const params: any = { page: loginPagination.page, page_size: loginPagination.pageSize }
    if (loginQ.username) params.username = loginQ.username
    if (loginQ.success !== null) params.success = loginQ.success
    if (loginQ.ip_address) params.ip_address = loginQ.ip_address
    if (loginQ.range) {
      params.start_date = new Date(loginQ.range[0]).toISOString()
      params.end_date = new Date(loginQ.range[1]).toISOString()
    }
    const res = await api.get('/logs/login', { params })
    loginLogs.value = res.data.items || []
  } catch { message.error('加载登录日志失败') }
}

async function loadScanLogs() {
  try {
    const res = await api.get('/scan/logs')
    scanLogs.value = res.data
  } catch { /* ignore */ }
}

async function cleanupLogs(type: 'login' | 'scan') {
  const days = parseInt(prompt(`请输入保留天数（删除 ${type} 日志中早于此天数的记录）：`, '90') || '0')
  if (!days) return
  cleaning.value = true
  try {
    const res = await api.post('/logs/cleanup', { type, days })
    message.success(res.data.message)
    if (type === 'login') await loadLoginLogs()
    else await loadScanLogs()
  } catch (e: any) { message.error(e.response?.data?.detail || '清理失败') }
  finally { cleaning.value = false }
}
</script>
