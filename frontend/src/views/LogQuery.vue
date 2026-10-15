<template>
  <div class="log-query">
    <n-tabs type="line" animated class="custom-tabs">
      <!-- Login logs -->
      <n-tab-pane name="login" tab="登录日志">
        <n-card :bordered="false" size="small" class="log-card">
          <n-space style="margin-bottom: 16px" :wrap="true" align="center">
            <n-input v-model:value="loginQ.username" placeholder="用户名" clearable style="width: 140px" @keyup.enter="loadLoginLogs" />
            <n-select v-model:value="loginQ.success" :options="successOptions" placeholder="状态" clearable style="width: 120px" />
            <n-input v-model:value="loginQ.ip_address" placeholder="IP 地址" clearable style="width: 140px" @keyup.enter="loadLoginLogs" />
            <n-date-picker v-model:value="loginQ.range" type="daterange" clearable style="width: 280px" />
            <n-button type="primary" @click="loadLoginLogs" :loading="loadingLogin">
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
            :remote="true"
            class="log-table"
            @update:page="(p: number) => { loginPagination.page = p; loadLoginLogs() }"
            @update:page-size="(ps: number) => { loginPagination.pageSize = ps; loginPagination.page = 1; loadLoginLogs() }"
          />
        </n-card>
      </n-tab-pane>

      <!-- Scan logs -->
      <n-tab-pane name="scan" tab="扫描日志">
        <n-card :bordered="false" size="small" class="log-card">
          <n-space style="margin-bottom: 16px" :wrap="true" align="center">
            <n-select v-model:value="scanQ.status" :options="scanStatusOptions" placeholder="状态" clearable style="width: 120px" />
            <n-select v-model:value="scanQ.triggered_by" :options="scanTriggerOptions" placeholder="触发方式" clearable style="width: 120px" />
            <n-date-picker v-model:value="scanQ.range" type="daterange" clearable style="width: 280px" />
            <n-button type="primary" @click="loadScanLogs" :loading="loadingScan">
              <template #icon><n-icon><search-outline /></n-icon></template>
              查询
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
            :remote="true"
            class="log-table"
            @update:page="(p: number) => { scanPagination.page = p; loadScanLogs() }"
            @update:page-size="(ps: number) => { scanPagination.pageSize = ps; scanPagination.page = 1; loadScanLogs() }"
          />
        </n-card>
      </n-tab-pane>

      <!-- System logs -->
      <n-tab-pane name="system" tab="系统日志">
        <n-card :bordered="false" size="small" class="log-card">
          <n-space style="margin-bottom: 16px" :wrap="true" align="center">
            <n-select v-model:value="sysQ.action" :options="sysActionOptions" placeholder="操作类型" clearable style="width: 140px" />
            <n-select v-model:value="sysQ.target_type" :options="sysTargetOptions" placeholder="目标类型" clearable style="width: 120px" />
            <n-input v-model:value="sysQ.operator" placeholder="操作者" clearable style="width: 120px" @keyup.enter="loadSystemLogs" />
            <n-date-picker v-model:value="sysQ.range" type="daterange" clearable style="width: 280px" />
            <n-button type="primary" @click="loadSystemLogs" :loading="loadingSystem">
              <template #icon><n-icon><search-outline /></n-icon></template>
              查询
            </n-button>
            <n-button type="warning" @click="cleanupLogs('system')" :loading="cleaning">清理旧日志</n-button>
          </n-space>
          <n-data-table 
            :columns="systemColumns" 
            :data="systemLogs" 
            :bordered="false" 
            size="small"
            :loading="loadingSystem"
            :pagination="systemPagination"
            :remote="true"
            class="log-table"
            @update:page="(p: number) => { systemPagination.page = p; loadSystemLogs() }"
            @update:page-size="(ps: number) => { systemPagination.pageSize = ps; systemPagination.page = 1; loadSystemLogs() }"
          />
        </n-card>
      </n-tab-pane>
    </n-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, h } from 'vue'
import { useMessage, NTag, NIcon } from 'naive-ui'
import { SearchOutline } from '@vicons/ionicons5'
import { formatDateTime } from '@/utils/time'
import api from '@/api'

const message = useMessage()
const cleaning = ref(false)
const loadingLogin = ref(false)
const loadingScan = ref(false)
const loadingSystem = ref(false)

// Data
const loginLogs = ref<any[]>([])
const scanLogs = ref<any[]>([])
const systemLogs = ref<any[]>([])

// Login query
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

// Scan query
const scanQ = reactive({
  status: null as string | null,
  triggered_by: null as string | null,
  range: null as null | [number, number],
})

const scanStatusOptions = [
  { label: '运行中', value: 'RUNNING' },
  { label: '成功', value: 'SUCCESS' },
  { label: '部分成功', value: 'PARTIAL' },
  { label: '失败', value: 'FAILED' },
]

const scanTriggerOptions = [
  { label: '系统', value: 'SYSTEM' },
  { label: '手动', value: 'MANUAL' },
]

// System query
const sysQ = reactive({
  action: null as string | null,
  target_type: null as string | null,
  operator: '' as string,
  range: null as null | [number, number],
})

const sysActionOptions = [
  { label: '创建', value: 'create' },
  { label: '修改', value: 'update' },
  { label: '删除', value: 'delete' },
  { label: '重置密码', value: 'reset_password' },
  { label: '自动禁用', value: 'auto_disable' },
]

const sysTargetOptions = [
  { label: '用户', value: 'user' },
  { label: '交换机', value: 'switch' },
]

// Pagination
// 注意：远程分页时总条数必须放在 pagination.itemCount 里，
// n-data-table 没有 row-count 这个 prop，缺了它分页器只会算出 1 页、翻页按钮点不动。
function createPagination() {
  return reactive({
    page: 1,
    pageSize: 20,
    itemCount: 0,
    showSizePicker: true,
    pageSizes: [20, 50, 100],
  })
}

const loginPagination = createPagination()
const scanPagination = createPagination()
const systemPagination = createPagination()

// Columns
const loginColumns = [
  { title: '用户名', key: 'username', width: 120 },
  { 
    title: '状态', 
    key: 'success', 
    width: 80,
    render: (r: any) => h(NTag, { 
      type: r.success ? 'success' : 'error', 
      size: 'small', bordered: false
    }, { default: () => r.success ? '成功' : '失败' }) 
  },
  { title: 'IP 地址', key: 'ip_address', width: 140 },
  { title: 'User-Agent', key: 'user_agent', ellipsis: { tooltip: true } },
  { title: '消息', key: 'message', ellipsis: { tooltip: true } },
  { title: '时间', key: 'created_at', width: 180, render: (r: any) => formatDateTime(r.created_at) },
]

const scanColumns = [
  { 
    title: '状态', key: 'status', width: 90,
    render: (r: any) => h(NTag, { 
      type: r.status === 'SUCCESS' ? 'success' : r.status === 'PARTIAL' ? 'warning' : r.status === 'FAILED' ? 'error' : 'info', 
      size: 'small', bordered: false
    }, { default: () => r.status }) 
  },
  { title: '触发', key: 'triggered_by', width: 90 },
  { title: '总 IPs', key: 'total_ips', width: 80 },
  { title: '更新', key: 'updated_ips', width: 80 },
  { title: '耗时(s)', key: 'duration', width: 80 },
  { 
    title: '消息', key: 'message',
    ellipsis: { tooltip: true },
    render: (r: any) => {
      if (r.error_message) return r.error_message
      if (r.status === 'SUCCESS') return `扫描完成，共 ${r.total_ips} 个 IP，更新 ${r.updated_ips} 个`
      return '-'
    }
  },
  { title: '时间', key: 'created_at', width: 180, render: (r: any) => formatDateTime(r.created_at) },
]

const actionLabelMap: Record<string, string> = {
  create: '创建', update: '修改', delete: '删除',
  reset_password: '重置密码', auto_disable: '自动禁用',
}

const targetTypeMap: Record<string, string> = {
  user: '用户', switch: '交换机',
}

const systemColumns = [
  { 
    title: '操作', key: 'action', width: 100,
    render: (r: any) => h(NTag, { 
      type: r.action === 'create' ? 'success' : r.action === 'delete' ? 'error' : r.action === 'auto_disable' ? 'warning' : 'info',
      size: 'small', bordered: false
    }, { default: () => actionLabelMap[r.action] || r.action })
  },
  { 
    title: '目标类型', key: 'target_type', width: 90,
    render: (r: any) => targetTypeMap[r.target_type] || r.target_type
  },
  { title: '详情', key: 'detail', ellipsis: { tooltip: true } },
  { title: '操作者', key: 'operator', width: 100 },
  { title: 'IP', key: 'ip_address', width: 130 },
  { title: '时间', key: 'created_at', width: 180, render: (r: any) => formatDateTime(r.created_at) },
]

onMounted(async () => {
  await Promise.all([loadLoginLogs(), loadScanLogs(), loadSystemLogs()])
})

async function loadLoginLogs() {
  loadingLogin.value = true
  try {
    const params: any = {
      page: loginPagination.page,
      page_size: loginPagination.pageSize,
    }
    if (loginQ.username) params.username = loginQ.username
    if (loginQ.success !== null) params.success = loginQ.success
    if (loginQ.ip_address) params.ip_address = loginQ.ip_address
    if (loginQ.range) {
      params.start_date = new Date(loginQ.range[0]).toISOString()
      params.end_date = new Date(loginQ.range[1] + 86400000 - 1).toISOString()
    }
    const res = await api.get('/logs/login', { params })
    loginLogs.value = res.data?.items || []
    loginPagination.itemCount = res.data?.total || 0
  } catch (e: any) { 
    message.error(e.response?.data?.detail || '加载登录日志失败') 
    loginLogs.value = []
    loginPagination.itemCount = 0
  } finally {
    loadingLogin.value = false
  }
}

async function loadScanLogs() {
  loadingScan.value = true
  try {
    const params: any = {
      page: scanPagination.page,
      page_size: scanPagination.pageSize,
    }
    if (scanQ.status) params.status = scanQ.status
    if (scanQ.triggered_by) params.triggered_by = scanQ.triggered_by
    if (scanQ.range) {
      params.start_time = new Date(scanQ.range[0]).toISOString()
      params.end_time = new Date(scanQ.range[1] + 86400000 - 1).toISOString()
    }
    const res = await api.get('/scan/tasks', { params })
    scanLogs.value = res.data?.items || []
    scanPagination.itemCount = res.data?.total || 0
  } catch (e: any) { 
    message.error(e.response?.data?.detail || '加载扫描日志失败')
    scanLogs.value = []
    scanPagination.itemCount = 0
  } finally {
    loadingScan.value = false
  }
}

async function loadSystemLogs() {
  loadingSystem.value = true
  try {
    const params: any = {
      page: systemPagination.page,
      page_size: systemPagination.pageSize,
    }
    if (sysQ.action) params.action = sysQ.action
    if (sysQ.target_type) params.target_type = sysQ.target_type
    if (sysQ.operator) params.operator = sysQ.operator
    if (sysQ.range) {
      params.start_date = new Date(sysQ.range[0]).toISOString()
      params.end_date = new Date(sysQ.range[1] + 86400000 - 1).toISOString()
    }
    const res = await api.get('/logs/system', { params })
    systemLogs.value = res.data?.items || []
    systemPagination.itemCount = res.data?.total || 0
  } catch (e: any) { 
    message.error(e.response?.data?.detail || '加载系统日志失败')
    systemLogs.value = []
    systemPagination.itemCount = 0
  } finally {
    loadingSystem.value = false
  }
}

async function cleanupLogs(type: 'login' | 'scan' | 'system') {
  const typeLabel = type === 'login' ? '登录' : type === 'scan' ? '扫描' : '系统'
  const days = parseInt(prompt(`请输入保留天数（删除 ${typeLabel} 日志中早于此天数的记录）：`, '90') || '0')
  if (!days || days <= 0) {
    message.warning('请输入有效的天数')
    return
  }
  cleaning.value = true
  try {
    const res = await api.post('/logs/cleanup', { type, days })
    message.success(res.data.message || '清理成功')
    if (type === 'login') await loadLoginLogs()
    else if (type === 'scan') await loadScanLogs()
    else await loadSystemLogs()
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
