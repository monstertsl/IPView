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
import api from '@/api'

const message = useMessage()
const cleaning = ref(false)
const loadingLogin = ref(false)
const loadingScan = ref(false)
const loginLogs = ref<any[]>([])
const scanLogs = ref<any[]>([])

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

const loginPagination = reactive({ 
  page: 1, 
  pageSize: 20,
  showSizePicker: true,
  pageSizes: [10, 20, 50, 100],
  onChange: (page: number) => {
    loginPagination.page = page
    loadLoginLogs()
  },
  onUpdatePageSize: (pageSize: number) => {
    loginPagination.pageSize = pageSize
    loginPagination.page = 1
    loadLoginLogs()
  }
})

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
    render: (r: any) => r.created_at ? new Date(r.created_at).toLocaleString('zh-CN') : '-'
  },
]

const scanColumns = [
  { title: '任务 ID', key: 'task_id', ellipsis: { tooltip: true }, width: 300 },
  { 
    title: '状态', 
    key: 'status', 
    width: 100,
    render: (r: any) => h(NTag, { 
      type: r.status === 'SUCCESS' ? 'success' : 'error', 
      size: 'small',
      bordered: false
    }, { default: () => r.status }) 
  },
  { title: '消息', key: 'message', ellipsis: { tooltip: true } },
  { title: '耗时(秒)', key: 'duration', width: 100 },
  { 
    title: '时间', 
    key: 'created_at', 
    width: 180,
    render: (r: any) => r.created_at ? new Date(r.created_at).toLocaleString('zh-CN') : '-'
  },
]

onMounted(async () => {
  await loadLoginLogs()
  await loadScanLogs()
})

async function loadLoginLogs() {
  loadingLogin.value = true
  try {
    const params: any = { 
      page: loginPagination.page, 
      page_size: loginPagination.pageSize 
    }
    if (loginQ.username) params.username = loginQ.username
    if (loginQ.success !== null) params.success = loginQ.success
    if (loginQ.ip_address) params.ip_address = loginQ.ip_address
    if (loginQ.range) {
      params.start_date = new Date(loginQ.range[0]).toISOString()
      params.end_date = new Date(loginQ.range[1]).toISOString()
    }
    const res = await api.get('/logs/login', { params })
    
    // 处理返回数据
    if (res.data && res.data.items) {
      loginLogs.value = res.data.items
    } else if (Array.isArray(res.data)) {
      loginLogs.value = res.data
    } else {
      loginLogs.value = []
    }
  } catch (e: any) { 
    console.error('加载登录日志失败:', e)
    message.error(e.response?.data?.detail || '加载登录日志失败') 
    loginLogs.value = []
  } finally {
    loadingLogin.value = false
  }
}

async function loadScanLogs() {
  loadingScan.value = true
  try {
    const res = await api.get('/scan/logs')
    scanLogs.value = Array.isArray(res.data) ? res.data : []
  } catch (e: any) { 
    console.error('加载扫描日志失败:', e)
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
.log-query {
  padding: 0;
}

.log-card {
  background: #1a1f2e !important;
  border-radius: 8px;
}

/* 浅色模式下的卡片样式 */
html:not(.dark) .log-card {
  background: #ffffff !important;
}

.log-table {
  border-radius: 6px;
  overflow: hidden;
}

:deep(.custom-tabs .n-tabs-tab) {
  --n-tab-text-color: #a0aec0;
  --n-tab-text-color-active: #10b981;
  --n-tab-text-color-hover: #fff;
}

/* 浅色模式下的标签样式 */
html:not(.dark) :deep(.custom-tabs .n-tabs-tab) {
  --n-tab-text-color: #6b7280;
  --n-tab-text-color-active: #10b981;
  --n-tab-text-color-hover: #1f2937;
}

:deep(.custom-tabs .n-tabs-bar) {
  background-color: #10b981;
}

:deep(.n-card) {
  --n-color: #1a1f2e;
  --n-border-color: transparent;
}

/* 浅色模式下的卡片边框 */
html:not(.dark) :deep(.n-card) {
  --n-color: #ffffff;
  --n-border-color: #e5e7eb;
}

:deep(.n-data-table) {
  --n-th-color: #242b3d;
  --n-td-color: #1a1f2e;
  --n-border-color: #2d3548;
  --n-th-text-color: #a0aec0;
  --n-td-text-color: #e2e8f0;
}

/* 浅色模式下的表格样式 */
html:not(.dark) :deep(.n-data-table) {
  --n-th-color: #f8fafc;
  --n-td-color: #ffffff;
  --n-border-color: #e5e7eb;
  --n-th-text-color: #6b7280;
  --n-td-text-color: #1f2937;
}

:deep(.n-input) {
  --n-color: #242b3d;
  --n-color-focus: #242b3d;
  --n-border: 1px solid #3a4459;
  --n-border-hover: 1px solid #10b981;
  --n-border-focus: 1px solid #10b981;
  --n-text-color: #fff;
  --n-placeholder-color: #64748b;
}

/* 浅色模式下的输入框样式 */
html:not(.dark) :deep(.n-input) {
  --n-color: #ffffff;
  --n-color-focus: #ffffff;
  --n-border: 1px solid #e5e7eb;
  --n-border-hover: 1px solid #10b981;
  --n-border-focus: 1px solid #10b981;
  --n-text-color: #1f2937;
  --n-placeholder-color: #9ca3af;
}

:deep(.n-select) {
  --n-color: #242b3d;
  --n-border: 1px solid #3a4459;
  --n-text-color: #fff;
}

/* 浅色模式下的选择框样式 */
html:not(.dark) :deep(.n-select) {
  --n-color: #ffffff;
  --n-border: 1px solid #e5e7eb;
  --n-text-color: #1f2937;
}

:deep(.n-date-picker) {
  --n-panel-color: #242b3d;
}

/* 浅色模式下的日期选择器样式 */
html:not(.dark) :deep(.n-date-picker) {
  --n-panel-color: #ffffff;
}

:deep(.n-button--primary-type) {
  --n-color: #10b981;
  --n-color-hover: #059669;
  --n-color-pressed: #047857;
}

:deep(.n-button--warning-type) {
  --n-color: #f59e0b;
  --n-color-hover: #d97706;
  --n-color-pressed: #b45309;
}

:deep(.n-pagination) {
  --n-item-color: transparent;
  --n-item-color-hover: rgba(16, 185, 129, 0.1);
  --n-item-color-active: #10b981;
  --n-item-text-color: #a0aec0;
  --n-item-text-color-active: #fff;
  --n-item-border-color: #3a4459;
}

/* 浅色模式下的分页样式 */
html:not(.dark) :deep(.n-pagination) {
  --n-item-color: transparent;
  --n-item-color-hover: rgba(16, 185, 129, 0.1);
  --n-item-color-active: #10b981;
  --n-item-text-color: #6b7280;
  --n-item-text-color-active: #fff;
  --n-item-border-color: #e5e7eb;
}
</style>
