<template>
  <div>
    <n-space style="margin-bottom: 16px" justify="space-between" align="center">
      <h3 class="page-title">
        <span class="title-bar"></span>
        交换机管理
      </h3>
      <n-button type="primary" @click="openModal()"><template #icon><n-icon><add-outline /></n-icon></template>添加交换机</n-button>
    </n-space>

    <n-data-table :columns="columns" :data="switches" :bordered="false" :row-key="(r: any) => r.id" />

    <n-modal v-model:show="showModal" preset="card" :title="editing?.id ? '编辑交换机' : '添加交换机'" style="width: 600px">
      <n-form :model="form" label-placement="top">
        <n-grid :cols="2" :x-gap="16">
          <n-gi><n-form-item label="IP 地址" required><n-input v-model:value="form.ip" placeholder="如 192.168.1.1" /></n-form-item></n-gi>
          <n-gi><n-form-item label="MAC"><n-input v-model:value="form.mac" placeholder="如 AA:BB:CC:DD:EE:FF" /></n-form-item></n-gi>
        </n-grid>
        <n-grid :cols="2" :x-gap="16">
          <n-gi>
            <n-form-item label="SNMP 版本">
              <n-select v-model:value="form.snmp_version" :options="[{ label: 'v1', value: 'v1' }, { label: 'v2c', value: 'v2c' }, { label: 'v3', value: 'v3' }]" />
            </n-form-item>
          </n-gi>
          <n-gi><n-form-item label="Community"><n-input v-model:value="form.community" placeholder="public" /></n-form-item></n-gi>
        </n-grid>
        <n-grid v-if="form.snmp_version === 'v3'" :cols="2" :x-gap="16">
          <n-gi><n-form-item label="v3 用户名"><n-input v-model:value="form.snmp_v3_config.username" /></n-form-item></n-gi>
          <n-gi><n-form-item label="认证密码"><n-input v-model:value="form.snmp_v3_config.auth_password" /></n-form-item></n-gi>
          <n-gi><n-form-item label="加密密码"><n-input v-model:value="form.snmp_v3_config.priv_password" /></n-form-item></n-gi>
          <n-gi>
            <n-form-item label="认证协议">
              <n-select v-model:value="form.snmp_v3_config.auth_protocol" :options="[{ label: 'SHA', value: 'SHA' }, { label: 'MD5', value: 'MD5' }]" />
            </n-form-item>
          </n-gi>
        </n-grid>
        <n-grid :cols="2" :x-gap="16">
          <n-gi><n-form-item label="位置"><n-input v-model:value="form.location" /></n-form-item></n-gi>
          <n-gi><n-form-item label="描述"><n-input v-model:value="form.description" /></n-form-item></n-gi>
        </n-grid>
        <n-form-item v-if="editing?.id" label="启用状态"><n-switch v-model:value="form.is_active" /></n-form-item>
      </n-form>

      <!-- Test connection result -->
      <div class="test-result-area" :class="{ 'test-success': testResult?.success, 'test-error': testResult !== null && !testResult?.success }">
        <n-text v-if="testResult === null" depth="3" style="font-size: 13px;">测试信息回显</n-text>
        <n-text v-else-if="testResult.success" type="success" style="font-size: 13px; word-break: break-all;">{{ testResult.message }}</n-text>
        <n-text v-else type="error" style="font-size: 13px; word-break: break-all;">{{ testResult.message }}</n-text>
      </div>

      <template #footer>
        <n-space justify="space-between" align="center">
          <n-button :loading="testing" @click="testConnection" type="info" ghost>
            测试连接
          </n-button>
          <n-space>
            <n-button @click="showModal = false">取消</n-button>
            <n-button type="primary" @click="saveSwitch">保存</n-button>
          </n-space>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useMessage, NTag, NSpace, NButton } from 'naive-ui'
import { h } from 'vue'
import api from '@/api'
import type { Switch } from '@/types'
import { AddOutline } from '@vicons/ionicons5'

const message = useMessage()
const switches = ref<Switch[]>([])
const showModal = ref(false)
const editing = ref<Switch | null>(null)
const testing = ref(false)
const testResult = ref<{ success: boolean; message: string } | null>(null)
const form = reactive({
  ip: '', mac: '', snmp_version: 'v2c', community: 'public',
  location: '', description: '', is_active: true,
  snmp_v3_config: { username: '', auth_password: '', priv_password: '', auth_protocol: 'SHA' }
})

const columns = [
  { title: 'IP', key: 'ip' },
  { title: 'MAC', key: 'mac' },
  { title: 'SNMP', key: 'snmp_version' },
  { title: '位置', key: 'location' },
  { title: '状态', key: 'is_active', render: (r: Switch) => h(NTag, { type: r.is_active ? 'success' : 'error', size: 'small' }, { default: () => r.is_active ? '启用' : '禁用' }) },
  { title: '操作', key: 'actions', width: 120, render: (r: Switch) => h(NSpace, { size: 6 }, { default: () => [
    h(NButton, { text: true, size: 'tiny', onClick: () => openModal(r) }, { default: () => '编辑' }),
    h(NButton, { text: true, size: 'tiny', type: 'error', onClick: () => deleteSwitch(r) }, { default: () => '删除' }),
  ]})}
]

onMounted(async () => { await loadSwitches() })

async function loadSwitches() {
  try {
    const res = await api.get<Switch[]>('/switches')
    switches.value = res.data
  } catch { message.error('加载失败') }
}

function openModal(s?: Switch) {
  editing.value = s || null
  testResult.value = null
  if (s) {
    Object.assign(form, { ...s, snmp_v3_config: s.snmp_v3_config || { username: '', auth_password: '', priv_password: '', auth_protocol: 'SHA' } })
  } else {
    Object.assign(form, { ip: '', mac: '', snmp_version: 'v2c', community: 'public', location: '', description: '', is_active: true, snmp_v3_config: { username: '', auth_password: '', priv_password: '', auth_protocol: 'SHA' } })
  }
  showModal.value = true
}

async function saveSwitch() {
  try {
    const payload = { ...form }
    if (payload.snmp_version !== 'v3') delete payload.snmp_v3_config
    if (editing.value?.id) {
      await api.patch(`/switches/${editing.value.id}`, payload)
    } else {
      await api.post('/switches', payload)
    }
    message.success('保存成功')
    showModal.value = false
    await loadSwitches()
  } catch (e: any) { message.error(e.response?.data?.detail || '保存失败') }
}

async function deleteSwitch(s: Switch) {
  try {
    await api.delete(`/switches/${s.id}`)
    message.success('删除成功')
    await loadSwitches()
  } catch (e: any) { message.error(e.response?.data?.detail || '删除失败') }
}

async function testConnection() {
  if (!form.ip) {
    message.warning('请先输入 IP 地址')
    return
  }
  testing.value = true
  testResult.value = null
  try {
    const payload: any = { ...form }
    if (payload.snmp_version !== 'v3') delete payload.snmp_v3_config
    const res = await api.post<{ success: boolean; message: string }>('/switches/test', payload)
    testResult.value = res.data
  } catch (e: any) {
    testResult.value = { success: false, message: e.response?.data?.detail || '测试连接失败' }
  } finally {
    testing.value = false
  }
}
</script>

<style scoped>
.test-result-area {
  margin-top: 12px;
  padding: 12px 16px;
  border: 1px dashed #3a4459;
  border-radius: 6px;
  min-height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: border-color 0.3s;
}

.test-result-area.test-success {
  border-color: #10b981;
  border-style: solid;
}

.test-result-area.test-error {
  border-color: #ef4444;
  border-style: solid;
}

html:not(.dark) .test-result-area {
  border-color: #e5e7eb;
}

html:not(.dark) .test-result-area.test-success {
  border-color: #10b981;
}

html:not(.dark) .test-result-area.test-error {
  border-color: #ef4444;
}

/* 页面标题样式 */
.page-title {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 0;
  font-size: 18px;
  font-weight: 500;
  color: #fff;
}

html:not(.dark) .page-title {
  color: #1f2937;
}

.title-bar {
  width: 4px;
  height: 18px;
  background: #10b981;
  border-radius: 2px;
}

:deep(.n-data-table) {
  --n-th-color: #242b3d;
  --n-td-color: #1a1f2e;
  --n-border-color: #3a4459;
  --n-th-text-color: #a0aec0;
  --n-td-text-color: #fff;
}

/* 浅色模式下的表格样式 */
html:not(.dark) :deep(.n-data-table) {
  --n-th-color: #f8fafc;
  --n-td-color: #ffffff;
  --n-border-color: #e5e7eb;
  --n-th-text-color: #6b7280;
  --n-td-text-color: #1f2937;
}

:deep(.n-button--primary-type) {
  --n-color: #10b981;
  --n-color-hover: #059669;
  --n-color-pressed: #047857;
}

:deep(.n-modal .n-card) {
  --n-color: #242b3d;
  --n-title-text-color: #fff;
  --n-close-icon-color: #a0aec0;
  --n-border-color: #3a4459;
}

/* 浅色模式下的弹窗样式 */
html:not(.dark) :deep(.n-modal .n-card) {
  --n-color: #ffffff;
  --n-title-text-color: #1f2937;
  --n-close-icon-color: #6b7280;
  --n-border-color: #e5e7eb;
}

:deep(.n-form-item .n-form-item-label) {
  --n-label-text-color: #a0aec0;
}

html:not(.dark) :deep(.n-form-item .n-form-item-label) {
  --n-label-text-color: #6b7280;
}

:deep(.n-input) {
  --n-color: #1a1f2e;
  --n-color-focus: #1a1f2e;
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
  --n-color: #1a1f2e;
  --n-border: 1px solid #3a4459;
  --n-text-color: #fff;
}

/* 浅色模式下的选择框样式 */
html:not(.dark) :deep(.n-select) {
  --n-color: #ffffff;
  --n-border: 1px solid #e5e7eb;
  --n-text-color: #1f2937;
}
</style>
