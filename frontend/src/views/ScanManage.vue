<template>
  <div>
    <n-grid :cols="2" :x-gap="16" :y-gap="16">
      <!-- Scan config -->
      <n-gi>
        <n-card title="扫描配置" :bordered="false">
          <n-form :model="config" label-placement="top" v-if="config">
            <n-divider title-placement="left" style="font-size:12px;margin:8px 0">IP 状态阈值</n-divider>
            <n-grid :cols="3" :x-gap="12">
              <n-gi><n-form-item label="在线阈值（天）"><n-input-number v-model:value="config.online_days" :min="1" :max="365" /></n-form-item></n-gi>
              <n-gi><n-form-item label="离线阈值（天）"><n-input-number v-model:value="config.offline_days" :min="1" :max="365" /></n-form-item></n-gi>
              <n-gi><n-form-item label="清理阈值（天）"><n-input-number v-model:value="config.cleanup_days" :min="1" :max="365" /></n-form-item></n-gi>
            </n-grid>
            <n-divider title-placement="left" style="font-size:12px;margin:8px 0">安全策略</n-divider>
            <n-grid :cols="2" :x-gap="12">
              <n-gi><n-form-item label="登录失败限制（次）"><n-input-number v-model:value="config.login_fail_limit" :min="1" :max="20" /></n-form-item></n-gi>
              <n-gi><n-form-item label="长期未登录禁用（天）"><n-input-number v-model:value="config.inactive_days_limit" :min="7" :max="365" /></n-form-item></n-gi>
            </n-grid>
            <n-divider title-placement="left" style="font-size:12px;margin:8px 0">日志保留策略</n-divider>
            <n-grid :cols="2" :x-gap="12">
              <n-gi><n-form-item label="登录日志保留（天）"><n-input-number v-model:value="config.log_retention_days_login" :min="7" :max="365" /></n-form-item></n-gi>
              <n-gi><n-form-item label="扫描日志保留（天）"><n-input-number v-model:value="config.log_retention_days_scan" :min="7" :max="365" /></n-form-item></n-gi>
            </n-grid>
            <n-divider title-placement="left" style="font-size:12px;margin:8px 0">扫描频率</n-divider>
            <n-grid :cols="2" :x-gap="12">
              <n-gi>
                <n-form-item label="扫描时间">
                  <n-select v-model:value="config.scan_interval" :options="scanIntervalOptions" />
                </n-form-item>
              </n-gi>
              <n-gi>
                <n-form-item label="执行时间">
                  <n-time-picker v-model:formatted-value="config.scan_time" format="HH:mm" :disabled="config.scan_interval === 'every_1h'" />
                </n-form-item>
              </n-gi>
            </n-grid>
            <n-button type="primary" @click="saveConfig" style="margin-top:8px">保存配置</n-button>
          </n-form>
        </n-card>
      </n-gi>

      <!-- Scan control + Subnet Management (same column) -->
      <n-gi>
        <n-space vertical :size="16">
          <!-- Scan control -->
          <n-card title="扫描控制" :bordered="false">
            <n-space vertical>
              <n-button type="primary" size="large" block @click="triggerScan" :loading="scanning">
                <template #icon><n-icon><flash-outline /></n-icon></template>
                立即扫描
              </n-button>
              <n-alert v-if="lastTask" :type="lastTask.status === 'SUCCESS' ? 'success' : lastTask.status === 'PARTIAL' ? 'warning' : lastTask.status === 'FAILED' ? 'error' : 'info'"
                :title="`上次扫描: ${lastTask.status}`">
                <template #default>
                  <n-text v-if="lastTask.triggered_by">触发方式：{{ lastTask.triggered_by }}</n-text><br/>
                  <n-text>更新 IPs：{{ lastTask.updated_ips }}，耗时：{{ lastTask.duration ?? '-' }}s</n-text>
                  <n-text v-if="lastTask.error_message" :type="lastTask.status === 'FAILED' ? 'error' : lastTask.status === 'PARTIAL' ? 'warning' : 'success'"><br/>{{ lastTask.error_message }}</n-text>
                </template>
              </n-alert>
            </n-space>
          </n-card>

          <!-- Subnet Management (moved under scan control) -->
          <n-card title="入库网段管理" :bordered="false">
            <template #header-extra>
              <n-space>
                <n-button type="primary" size="small" @click="showAddSubnet = true">
                  <template #icon><n-icon><add-outline /></n-icon></template>
                  添加网段
                </n-button>
                <n-button quaternary size="small" @click="loadSubnets">
                  <template #icon><n-icon><refresh-outline /></n-icon></template>
                </n-button>
              </n-space>
            </template>
            <n-alert type="info" title="说明" closable style="margin-bottom: 12px">
              只有匹配已配置网段的 IP 地址才会被入库。若未配置任何网段，则允许所有 IP 入库。
            </n-alert>
            <n-data-table :columns="subnetColumns" :data="subnets" :bordered="false" size="small" :max-height="200" />
          </n-card>
        </n-space>
      </n-gi>
    </n-grid>

    <!-- Add Subnet Modal -->
    <n-modal v-model:show="showAddSubnet" preset="card" title="添加入库网段" style="width: 480px">
      <n-form :model="subnetForm" label-placement="left" label-width="80">
        <n-form-item label="网段 CIDR" required>
          <n-input v-model:value="subnetForm.cidr" placeholder="如 10.10.0.0/16 或 192.168.1.0/24" />
        </n-form-item>
        <n-form-item label="描述">
          <n-input v-model:value="subnetForm.description" placeholder="可选，用于标记网段用途" />
        </n-form-item>
      </n-form>
      <template #footer>
        <div style="display: flex; justify-content: flex-end; gap: 12px;">
          <n-button @click="showAddSubnet = false">取消</n-button>
          <n-button type="primary" @click="addSubnet" :loading="subnetLoading">添加</n-button>
        </div>
      </template>
    </n-modal>

    <!-- Edit Subnet Modal -->
    <n-modal v-model:show="showEditSubnet" preset="card" title="编辑入库网段" style="width: 480px">
      <n-form :model="editSubnetForm" label-placement="left" label-width="80">
        <n-form-item label="网段 CIDR">
          <n-input :value="editSubnetForm.cidr" disabled />
        </n-form-item>
        <n-form-item label="描述">
          <n-input v-model:value="editSubnetForm.description" placeholder="可选，用于标记网段用途" />
        </n-form-item>
        <n-form-item label="状态">
          <n-switch v-model:value="editSubnetForm.is_active" />
          <span style="margin-left: 8px; color: #6b7280">{{ editSubnetForm.is_active ? '启用' : '禁用' }}</span>
        </n-form-item>
      </n-form>
      <template #footer>
        <div style="display: flex; justify-content: flex-end; gap: 12px;">
          <n-button @click="showEditSubnet = false">取消</n-button>
          <n-button type="primary" @click="updateSubnet" :loading="subnetLoading">保存</n-button>
        </div>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useMessage, useDialog, NTag, NSpace, NButton, NText } from 'naive-ui'
import { h } from 'vue'
import api from '@/api'
import type { ScanTask, ScanSubnet } from '@/types'
import { formatDateTime } from '@/utils/time'
import { FlashOutline, AddOutline, RefreshOutline } from '@vicons/ionicons5'

const message = useMessage()
const dialog = useDialog()
const config = ref<any>(null)
const tasks = ref<ScanTask[]>([])
const lastTask = ref<ScanTask | null>(null)
const scanning = ref(false)

const scanIntervalOptions = [
  { label: '每1小时', value: 'every_1h' },
  { label: '每6小时', value: 'every_6h' },
  { label: '每12小时', value: 'every_12h' },
  { label: '每天', value: 'every_day' },
]

// Subnet management
const subnets = ref<ScanSubnet[]>([])
const showAddSubnet = ref(false)
const showEditSubnet = ref(false)
const subnetLoading = ref(false)
const subnetForm = ref({ cidr: '', description: '' })
const editSubnetForm = ref<{ id: string; cidr: string; description: string; is_active: boolean }>({
  id: '', cidr: '', description: '', is_active: true
})

const subnetColumns = [
  {
    title: '网段 CIDR',
    key: 'cidr',
    width: 180,
    render: (row: ScanSubnet) => h('span', { style: { fontFamily: 'monospace' } }, row.cidr)
  },
  {
    title: '描述',
    key: 'description',
    ellipsis: { tooltip: true },
    render: (row: ScanSubnet) => row.description || '-'
  },
  {
    title: '状态',
    key: 'is_active',
    width: 100,
    render: (row: ScanSubnet) => h(NTag, {
      type: row.is_active ? 'success' : 'default',
      size: 'small'
    }, { default: () => row.is_active ? '启用' : '禁用' })
  },
  {
    title: '创建时间',
    key: 'created_at',
    width: 160,
    render: (row: ScanSubnet) => formatDateTime(row.created_at)
  },
  {
    title: '操作',
    key: 'actions',
    width: 150,
    render: (row: ScanSubnet) => h(NSpace, { size: 'small' }, {
      default: () => [
        h(NButton, {
          size: 'small',
          quaternary: true,
          onClick: () => openEditSubnet(row)
        }, { default: () => '编辑' }),
        h(NButton, {
          size: 'small',
          quaternary: true,
          type: 'error',
          onClick: () => confirmDeleteSubnet(row)
        }, { default: () => '删除' })
      ]
    })
  }
]

onMounted(async () => {
  await loadConfig()
  await loadTasks()
  await loadSubnets()
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
    const res = await api.get('/scan/tasks', { params: { page: 1, page_size: 1 } })
    const items = res.data?.items || res.data || []
    tasks.value = items
    if (items.length > 0) lastTask.value = items[0]
  } catch { /* ignore */ }
}

async function triggerScan() {
  scanning.value = true
  try {
    await api.post('/scan/tasks/now')
    message.success('扫描任务已加入队列')
    setTimeout(loadTasks, 2000)
  } catch (e: any) { message.error(e.response?.data?.detail || '启动失败') }
  finally { scanning.value = false }
}

// Subnet management functions
async function loadSubnets() {
  try {
    const res = await api.get<ScanSubnet[]>('/scan/subnets')
    subnets.value = res.data
  } catch { /* ignore */ }
}

async function addSubnet() {
  if (!subnetForm.value.cidr) {
    message.warning('请输入网段 CIDR')
    return
  }
  subnetLoading.value = true
  try {
    await api.post('/scan/subnets', subnetForm.value)
    message.success('网段添加成功')
    showAddSubnet.value = false
    subnetForm.value = { cidr: '', description: '' }
    await loadSubnets()
  } catch (e: any) {
    message.error(e.response?.data?.detail || '添加失败')
  } finally {
    subnetLoading.value = false
  }
}

function openEditSubnet(subnet: ScanSubnet) {
  editSubnetForm.value = {
    id: subnet.id,
    cidr: subnet.cidr,
    description: subnet.description || '',
    is_active: subnet.is_active
  }
  showEditSubnet.value = true
}

async function updateSubnet() {
  subnetLoading.value = true
  try {
    await api.patch(`/scan/subnets/${editSubnetForm.value.id}`, {
      description: editSubnetForm.value.description,
      is_active: editSubnetForm.value.is_active
    })
    message.success('网段更新成功')
    showEditSubnet.value = false
    await loadSubnets()
  } catch (e: any) {
    message.error(e.response?.data?.detail || '更新失败')
  } finally {
    subnetLoading.value = false
  }
}

function confirmDeleteSubnet(subnet: ScanSubnet) {
  dialog.warning({
    title: '确认删除',
    content: `确定要删除网段 "${subnet.cidr}" 吗？删除后该网段内的 IP 将不再自动入库。`,
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await api.delete(`/scan/subnets/${subnet.id}`)
        message.success('网段已删除')
        await loadSubnets()
      } catch (e: any) {
        message.error(e.response?.data?.detail || '删除失败')
      }
    }
  })
}
</script>

<style scoped>
/* 卡片样式 */
:deep(.n-card) {
  --n-color: #1a1f2e;
  --n-border-color: transparent;
  --n-title-text-color: #fff;
}

html:not(.dark) :deep(.n-card) {
  --n-color: #ffffff;
  --n-border-color: #e5e7eb;
  --n-title-text-color: #1f2937;
}

/* 表格样式 */
:deep(.n-data-table) {
  --n-th-color: #242b3d;
  --n-td-color: #1a1f2e;
  --n-border-color: #3a4459;
  --n-th-text-color: #a0aec0;
  --n-td-text-color: #fff;
}

html:not(.dark) :deep(.n-data-table) {
  --n-th-color: #f8fafc;
  --n-td-color: #ffffff;
  --n-border-color: #e5e7eb;
  --n-th-text-color: #6b7280;
  --n-td-text-color: #1f2937;
}

/* 输入框样式 */
:deep(.n-input),
:deep(.n-input-number) {
  --n-color: #242b3d;
  --n-color-focus: #242b3d;
  --n-border: 1px solid #3a4459;
  --n-border-hover: 1px solid #10b981;
  --n-border-focus: 1px solid #10b981;
  --n-text-color: #fff;
  --n-placeholder-color: #64748b;
}

html:not(.dark) :deep(.n-input),
html:not(.dark) :deep(.n-input-number) {
  --n-color: #ffffff;
  --n-color-focus: #ffffff;
  --n-border: 1px solid #e5e7eb;
  --n-border-hover: 1px solid #10b981;
  --n-border-focus: 1px solid #10b981;
  --n-text-color: #1f2937;
  --n-placeholder-color: #9ca3af;
}

/* 表单标签样式 */
:deep(.n-form-item .n-form-item-label) {
  --n-label-text-color: #a0aec0;
}

html:not(.dark) :deep(.n-form-item .n-form-item-label) {
  --n-label-text-color: #6b7280;
}

/* 分割线样式 */
:deep(.n-divider) {
  --n-color: #3a4459;
  --n-text-color: #a0aec0;
}

html:not(.dark) :deep(.n-divider) {
  --n-color: #e5e7eb;
  --n-text-color: #6b7280;
}

/* 按钮样式 */
:deep(.n-button--primary-type) {
  --n-color: #10b981;
  --n-color-hover: #059669;
  --n-color-pressed: #047857;
}

/* 弹窗样式 */
:deep(.n-modal .n-card) {
  --n-color: #242b3d;
  --n-title-text-color: #fff;
  --n-close-icon-color: #a0aec0;
  --n-border-color: #3a4459;
}

html:not(.dark) :deep(.n-modal .n-card) {
  --n-color: #ffffff;
  --n-title-text-color: #1f2937;
  --n-close-icon-color: #6b7280;
  --n-border-color: #e5e7eb;
}

/* 警告框样式 */
:deep(.n-alert) {
  --n-color: rgba(16, 185, 129, 0.1);
  --n-title-text-color: #10b981;
}

html:not(.dark) :deep(.n-alert) {
  --n-color: rgba(16, 185, 129, 0.1);
  --n-title-text-color: #059669;
}
</style>
