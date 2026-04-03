<template>
  <div>
    <n-grid :cols="2" :x-gap="16" :y-gap="16">
      <!-- Scan config -->
      <n-gi>
        <n-card title="扫描配置" :bordered="false">
          <n-form :model="config" label-placement="top" v-if="config">
            <n-grid :cols="2" :x-gap="12">
              <n-gi><n-form-item label="在线阈值（天）"><n-input-number v-model:value="config.online_days" :min="1" /></n-form-item></n-gi>
              <n-gi><n-form-item label="离线阈值（天）"><n-input-number v-model:value="config.offline_days" :min="1" /></n-form-item></n-gi>
              <n-gi><n-form-item label="清理阈值（天）"><n-input-number v-model:value="config.cleanup_days" :min="1" /></n-form-item></n-gi>
              <n-gi><n-form-item label="SNMP 超时（秒）"><n-input-number v-model:value="config.snmp_timeout" :min="1" /></n-form-item></n-gi>
            </n-grid>
            <n-button type="primary" @click="saveConfig">保存配置</n-button>
          </n-form>
        </n-card>
      </n-gi>

      <!-- Scan control -->
      <n-gi>
        <n-card title="扫描控制" :bordered="false">
          <n-space vertical>
            <n-button type="primary" size="large" block @click="triggerScan" :loading="scanning">
              <template #icon><n-icon><flash-outline /></n-icon></template>
              立即扫描
            </n-button>
            <n-alert v-if="lastTask" :type="lastTask.status === 'SUCCESS' ? 'success' : 'error'" :title="`上次扫描: ${lastTask.status} - ${lastTask.updated_ips} IPs 更新`" />
          </n-space>
        </n-card>
      </n-gi>

      <!-- Task list -->
      <n-gi :span="2">
        <n-card title="扫描任务历史" :bordered="false">
          <n-data-table :columns="taskColumns" :data="tasks" :bordered="false" size="small" />
        </n-card>
      </n-gi>
    </n-grid>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useMessage, NTag, NSpace, NButton } from 'naive-ui'
import { h } from 'vue'
import api from '@/api'
import type { ScanTask } from '@/types'
import { FlashOutline } from '@vicons/ionicons5'

const message = useMessage()
const config = ref<any>(null)
const tasks = ref<ScanTask[]>([])
const lastTask = ref<ScanTask | null>(null)
const scanning = ref(false)

const taskColumns = [
  { title: 'ID', key: 'id', ellipsis: true },
  { title: '状态', key: 'status', render: (r: ScanTask) => h(NTag, { type: r.status === 'SUCCESS' ? 'success' : r.status === 'FAILED' ? 'error' : 'info', size: 'small' }, { default: () => r.status }) },
  { title: '触发', key: 'triggered_by' },
  { title: '总 IPs', key: 'total_ips' },
  { title: '更新', key: 'updated_ips' },
  { title: '耗时(秒)', key: 'duration' },
  { title: '错误', key: 'error_message', ellipsis: true },
  { title: '开始', key: 'started_at', render: (r: ScanTask) => r.started_at ? new Date(r.started_at).toLocaleString('zh-CN') : '-' },
  { title: '创建', key: 'created_at', render: (r: ScanTask) => new Date(r.created_at).toLocaleString('zh-CN') },
]

onMounted(async () => {
  await loadConfig()
  await loadTasks()
})

async function loadConfig() {
  try {
    const res = await api.get('/scan/config')
    config.value = res.data
  } catch { /* ignore */ }
}

async function saveConfig() {
  try {
    await api.patch('/scan/config', config.value)
    message.success('配置已保存')
  } catch (e: any) { message.error(e.response?.data?.detail || '保存失败') }
}

async function loadTasks() {
  try {
    const res = await api.get<ScanTask[]>('/scan/tasks')
    tasks.value = res.data
    if (tasks.value.length > 0) lastTask.value = tasks.value[0]
  } catch { /* ignore */ }
}

async function triggerScan() {
  scanning.value = true
  try {
    const res = await api.post('/scan/tasks/now')
    message.success('扫描任务已加入队列')
    setTimeout(loadTasks, 2000)
  } catch (e: any) { message.error(e.response?.data?.detail || '启动失败') }
  finally { scanning.value = false }
}
</script>
