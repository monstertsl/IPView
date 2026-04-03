<template>
  <div>
    <n-space style="margin-bottom: 16px" justify="space-between">
      <n-h3 prefix="bar" style="margin: 0">交换机管理</n-h3>
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
      <template #footer>
        <n-space justify="end">
          <n-button @click="showModal = false">取消</n-button>
          <n-button type="primary" @click="saveSwitch">保存</n-button>
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
</script>
