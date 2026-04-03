<template>
  <div>
    <n-space style="margin-bottom: 16px" justify="space-between">
      <n-h3 prefix="bar" style="margin: 0">用户管理</n-h3>
      <n-button type="primary" @click="showAdd = true"><template #icon><n-icon><add-outline /></n-icon></template>添加用户</n-button>
    </n-space>

    <n-data-table :columns="columns" :data="users" :bordered="false" :row-key="(r: any) => r.id" />

    <!-- Add/Edit modal -->
    <n-modal v-model:show="showAdd" preset="card" :title="editingUser ? '编辑用户' : '添加用户'" style="width: 500px">
      <n-form :model="form" label-placement="top">
        <n-form-item label="用户名" required>
          <n-input v-model:value="form.username" :disabled="!!editingUser" />
        </n-form-item>
        <n-form-item v-if="!editingUser" label="密码">
          <n-input v-model:value="form.password" type="password" />
        </n-form-item>
        <n-form-item label="角色">
          <n-select v-model:value="form.role" :options="[{ label: '管理员', value: 'admin' }, { label: '普通用户', value: 'user' }]" />
        </n-form-item>
        <n-form-item label="认证方式">
          <n-select v-model:value="form.auth_mode" :options="[{ label: '仅密码', value: 'PASSWORD_ONLY' }, { label: '仅 TOTP', value: 'TOTP_ONLY' }, { label: '密码+TOTP', value: 'PASSWORD_AND_TOTP' }]" />
        </n-form-item>
        <n-form-item label="启用状态">
          <n-switch v-model:value="form.is_active" />
        </n-form-item>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button @click="closeModal">取消</n-button>
          <n-button type="primary" @click="saveUser">保存</n-button>
        </n-space>
      </template>
    </n-modal>

    <!-- TOTP QR modal -->
    <n-modal v-model:show="showTotp" preset="card" title="绑定 TOTP" style="width: 400px">
      <n-space vertical align="center" style="width: 100%">
        <n-qr-code :value="totpData?.uri || ''" size="200" />
        <n-text>密钥：{{ totpData?.secret }}</n-text>
        <n-text depth-3 style="font-size:12px">请使用 authenticator app 扫描上方二维码或输入密钥</n-text>
      </n-space>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useMessage, NButton, NIcon, NTag, NSpace } from 'naive-ui'
import { h } from 'vue'
import api from '@/api'
import type { User } from '@/types'
import { AddOutline } from '@vicons/ionicons5'

const message = useMessage()
const users = ref<User[]>([])
const showAdd = ref(false)
const showTotp = ref(false)
const editingUser = ref<User | null>(null)
const totpData = ref<{ secret: string; uri: string } | null>(null)

const form = reactive({
  username: '', password: '', role: 'user' as 'admin' | 'user',
  auth_mode: 'PASSWORD_ONLY' as string, is_active: true
})

const columns = [
  { title: '用户名', key: 'username' },
  { title: '角色', key: 'role', render: (r: User) => h(NTag, { type: r.role === 'admin' ? 'error' : 'info', size: 'small' }, { default: () => r.role === 'admin' ? '管理员' : '用户' }) },
  { title: '认证', key: 'auth_mode', render: (r: User) => r.auth_mode },
  { title: 'TOTP', key: 'totp_enabled', render: (r: User) => h(NTag, { type: r.totp_enabled ? 'success' : 'default', size: 'small' }, { default: () => r.totp_enabled ? '已启用' : '未启用' }) },
  { title: '状态', key: 'is_active', render: (r: User) => h(NTag, { type: r.is_active ? 'success' : 'error', size: 'small' }, { default: () => r.is_active ? '启用' : '禁用' }) },
  { title: '操作', key: 'actions', render: (r: User) => h(NSpace, { size: 6 }, { default: () => [
    h(NButton, { text: true, size: 'tiny', onClick: () => editUser(r) }, { default: () => '编辑' }),
    h(NButton, { text: true, size: 'tiny', type: r.totp_enabled ? 'warning' : 'success', onClick: () => r.totp_enabled ? disableTotp(r) : enableTotp(r) }, { default: () => r.totp_enabled ? '关闭TOTP' : '启用TOTP' }),
    h(NButton, { text: true, size: 'tiny', type: 'error', onClick: () => deleteUser(r) }, { default: () => '删除' }),
  ]})}
]

onMounted(async () => { await loadUsers() })

async function loadUsers() {
  try {
    const res = await api.get<User[]>('/users')
    users.value = res.data
  } catch { message.error('加载用户失败') }
}

function closeModal() { showAdd.value = false; editingUser.value = null; Object.assign(form, { username: '', password: '', role: 'user', auth_mode: 'PASSWORD_ONLY', is_active: true }) }

function editUser(u: User) {
  editingUser.value = u
  Object.assign(form, { username: u.username, password: '', role: u.role, auth_mode: u.auth_mode, is_active: u.is_active })
  showAdd.value = true
}

async function saveUser() {
  try {
    if (editingUser.value) {
      await api.patch(`/users/${editingUser.value.id}`, { role: form.role, auth_mode: form.auth_mode, is_active: form.is_active })
      message.success('更新成功')
    } else {
      await api.post('/users', form)
      message.success('添加成功')
    }
    await loadUsers()
    closeModal()
  } catch (e: any) { message.error(e.response?.data?.detail || '操作失败') }
}

async function deleteUser(u: User) {
  try {
    await api.delete(`/users/${u.id}`)
    message.success('删除成功')
    await loadUsers()
  } catch (e: any) { message.error(e.response?.data?.detail || '删除失败') }
}

async function enableTotp(u: User) {
  try {
    const res = await api.post<{ secret: string; uri: string }>(`/users/${u.id}/totp/enable`)
    totpData.value = res.data
    showTotp.value = true
  } catch (e: any) { message.error(e.response?.data?.detail || '启用失败') }
}

async function disableTotp(u: User) {
  const code = prompt('请输入 TOTP 验证码以禁用：')
  if (!code) return
  try {
    await api.post(`/users/${u.id}/totp/disable`, { code })
    message.success('TOTP 已禁用')
    await loadUsers()
  } catch (e: any) { message.error(e.response?.data?.detail || '禁用失败') }
}
</script>
