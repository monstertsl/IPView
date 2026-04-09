<template>
  <div class="user-manage">
    <n-space style="margin-bottom: 16px" justify="space-between" align="center">
      <h3 class="page-title">
        <span class="title-bar"></span>
        用户管理
      </h3>
      <n-button type="primary" @click="showAdd = true">
        <template #icon><n-icon><add-outline /></n-icon></template>
        添加用户
      </n-button>
    </n-space>

    <n-data-table 
      :columns="columns" 
      :data="users" 
      :bordered="false" 
      :row-key="(r: any) => r.id"
      class="data-table"
    />

    <!-- Add/Edit modal -->
    <n-modal v-model:show="showAdd" preset="card" :title="editingUser ? '编辑用户' : '添加用户'" style="width: 500px" class="custom-modal">
      <n-form :model="form" label-placement="top">
        <n-form-item label="用户名" required>
          <n-input v-model:value="form.username" :disabled="!!editingUser" placeholder="请输入用户名" />
        </n-form-item>
        <n-form-item v-if="!editingUser && form.auth_mode !== 'TOTP_ONLY'" label="密码" required>
          <n-input v-model:value="form.password" type="password" placeholder="请输入密码（至少8位）" show-password-on="click" />
        </n-form-item>
        <n-form-item v-if="!editingUser && form.auth_mode === 'TOTP_ONLY'" label="密码">
          <n-text depth="3" style="font-size: 12px;">仅 TOTP 模式无需设置密码，系统会自动生成 TOTP 密钥</n-text>
        </n-form-item>
        <n-form-item label="角色">
          <n-select v-model:value="form.role" :options="roleOptions" />
        </n-form-item>
        <n-form-item label="认证方式">
          <n-select v-model:value="form.auth_mode" :options="authModeOptions" />
          <template v-if="!editingUser">
            <n-text v-if="form.auth_mode === 'TOTP_ONLY'" depth="3" style="font-size: 12px; margin-top: 4px; display: block;">
              创建后请立即查看 TOTP 密钥并绑定到 Authenticator 应用
            </n-text>
            <n-text v-if="form.auth_mode === 'PASSWORD_AND_TOTP'" depth="3" style="font-size: 12px; margin-top: 4px; display: block;">
              创建后会自动启用 TOTP，请查看密钥并绑定
            </n-text>
          </template>
        </n-form-item>
        <n-form-item label="启用状态">
          <n-switch v-model:value="form.is_active" />
        </n-form-item>

        <!-- 编辑用户时显示修改密码和重置TOTP -->
        <template v-if="editingUser">
          <n-divider style="margin: 8px 0" />
          <n-form-item label="修改密码">
            <n-input-group>
              <n-input v-model:value="newPassword" type="password" placeholder="输入新密码（至少8位）" show-password-on="click" style="flex: 1" />
              <n-button type="warning" :loading="resettingPassword" :disabled="!newPassword || newPassword.length < 8" @click="resetPassword">
                修改密码
              </n-button>
            </n-input-group>
          </n-form-item>
          <n-form-item label="TOTP 管理">
            <n-button type="warning" @click="resetTotp" :loading="resettingTotp">
              重置 TOTP（生成新密钥）
            </n-button>
          </n-form-item>
        </template>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button @click="closeModal">取消</n-button>
          <n-button type="primary" @click="saveUser" :loading="saving">保存</n-button>
        </n-space>
      </template>
    </n-modal>

    <!-- TOTP QR modal -->
    <n-modal v-model:show="showTotp" preset="card" title="绑定 TOTP" style="width: 420px" class="custom-modal">
      <n-space vertical align="center" style="width: 100%">
        <n-qr-code :value="totpData?.uri || ''" size="200" />
        <n-text>密钥：<n-tag type="warning" size="small" style="font-family:monospace">{{ totpData?.secret }}</n-tag></n-text>
        <n-text depth="3" style="font-size: 12px; text-align: center;">
          请使用 Google Authenticator、Microsoft Authenticator 或其他 TOTP 应用扫描上方二维码，或手动输入密钥
        </n-text>
      </n-space>
      <template #footer>
        <n-space justify="center">
          <n-button type="primary" @click="showTotp = false; loadUsers()">我已绑定</n-button>
        </n-space>
      </template>
    </n-modal>

    <!-- View TOTP secret modal (admin only) -->
    <n-modal v-model:show="showTotpSecret" preset="card" title="查看 TOTP 密钥" style="width: 420px" class="custom-modal">
      <n-space vertical align="center" style="width: 100%">
        <n-qr-code :value="totpSecretData?.uri || ''" size="200" />
        <n-text>用户：<strong>{{ totpSecretUser?.username }}</strong></n-text>
        <n-text>密钥：<n-tag type="warning" size="small" style="font-family:monospace">{{ totpSecretData?.secret }}</n-tag></n-text>
        <n-text depth="3" style="font-size: 12px; text-align: center;">此密钥可手动输入到 Authenticator 应用</n-text>
      </n-space>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, h } from 'vue'
import { useMessage, NButton, NIcon, NTag, NSpace } from 'naive-ui'
import api from '@/api'
import type { User } from '@/types'
import { AddOutline } from '@vicons/ionicons5'

const message = useMessage()
const users = ref<User[]>([])
const showAdd = ref(false)
const showTotp = ref(false)
const showTotpSecret = ref(false)
const editingUser = ref<User | null>(null)
const totpData = ref<{ secret: string; uri: string } | null>(null)
const totpSecretData = ref<{ secret: string; uri: string } | null>(null)
const totpSecretUser = ref<User | null>(null)
const saving = ref(false)
const newPassword = ref('')
const resettingPassword = ref(false)
const resettingTotp = ref(false)

const form = reactive({
  username: '', password: '', role: 'user' as 'admin' | 'user',
  auth_mode: 'PASSWORD_ONLY' as string, is_active: true
})

const roleOptions = [
  { label: '管理员', value: 'admin' },
  { label: '普通用户', value: 'user' }
]

const authModeOptions = [
  { label: '仅密码', value: 'PASSWORD_ONLY' },
  { label: '仅 TOTP', value: 'TOTP_ONLY' },
  { label: '密码 + TOTP', value: 'PASSWORD_AND_TOTP' }
]

const authModeMap: Record<string, string> = {
  'PASSWORD_ONLY': '仅密码',
  'TOTP_ONLY': '仅 TOTP',
  'PASSWORD_AND_TOTP': '密码+TOTP'
}

const columns = [
  { title: '用户名', key: 'username' },
  { 
    title: '角色', 
    key: 'role', 
    render: (r: User) => h(NTag, { 
      type: r.role === 'admin' ? 'error' : 'info', 
      size: 'small',
      bordered: false
    }, { default: () => r.role === 'admin' ? '管理员' : '用户' }) 
  },
  { 
    title: '认证方式', 
    key: 'auth_mode',
    render: (r: User) => h(NTag, { 
      type: 'default', 
      size: 'small',
      bordered: false
    }, { default: () => authModeMap[r.auth_mode] || r.auth_mode })
  },
  { 
    title: 'TOTP', 
    key: 'totp_enabled', 
    render: (r: User) => h(NTag, { 
      type: r.totp_enabled ? 'success' : 'default', 
      size: 'small',
      bordered: false
    }, { default: () => r.totp_enabled ? '已启用' : '未启用' }) 
  },
  { 
    title: '状态', 
    key: 'is_active', 
    render: (r: User) => h(NTag, { 
      type: r.is_active ? 'success' : 'error', 
      size: 'small',
      bordered: false
    }, { default: () => r.is_active ? '启用' : '禁用' }) 
  },
  { 
    title: '操作', 
    key: 'actions', 
    render: (r: User) => h(NSpace, { size: 8 }, { default: () => [
      h(NButton, { text: true, size: 'tiny', type: 'info', onClick: () => editUser(r) }, { default: () => '编辑' }),
      h(NButton, { 
        text: true, 
        size: 'tiny', 
        type: r.totp_enabled ? 'warning' : 'success', 
        onClick: () => r.totp_enabled ? disableTotp(r) : enableTotp(r) 
      }, { default: () => r.totp_enabled ? '关闭TOTP' : '启用TOTP' }),
      r.totp_enabled ? h(NButton, { 
        text: true, 
        size: 'tiny', 
        type: 'info', 
        onClick: () => viewTotpSecret(r) 
      }, { default: () => '查看密钥' }) : null,
      h(NButton, { text: true, size: 'tiny', type: 'error', onClick: () => deleteUser(r) }, { default: () => '删除' }),
    ].filter(Boolean)})
  }
]

onMounted(async () => { await loadUsers() })

async function loadUsers() {
  try {
    const res = await api.get<User[]>('/users')
    users.value = res.data
  } catch { message.error('加载用户失败') }
}

function closeModal() { 
  showAdd.value = false
  editingUser.value = null
  newPassword.value = ''
  Object.assign(form, { username: '', password: '', role: 'user', auth_mode: 'PASSWORD_ONLY', is_active: true }) 
}

function editUser(u: User) {
  editingUser.value = u
  Object.assign(form, { username: u.username, password: '', role: u.role, auth_mode: u.auth_mode, is_active: u.is_active })
  showAdd.value = true
}

async function saveUser() {
  saving.value = true
  try {
    if (editingUser.value) {
      await api.patch(`/users/${editingUser.value.id}`, { 
        role: form.role, 
        auth_mode: form.auth_mode, 
        is_active: form.is_active 
      })
      message.success('更新成功')
    } else {
      // 新建用户
      const payload: any = {
        username: form.username,
        role: form.role,
        auth_mode: form.auth_mode,
        is_active: form.is_active
      }
      
      // 仅 TOTP 模式不需要密码
      if (form.auth_mode !== 'TOTP_ONLY') {
        if (!form.password || form.password.length < 8) {
          message.warning('密码至少需要8位')
          saving.value = false
          return
        }
        payload.password = form.password
      }
      
      const res = await api.post('/users', payload)
      message.success('添加成功')
      
      // 如果是 TOTP 相关模式，自动显示 TOTP 密钥
      if (form.auth_mode === 'TOTP_ONLY' || form.auth_mode === 'PASSWORD_AND_TOTP') {
        // 获取刚创建的用户的 TOTP 密钥
        try {
          const totpRes = await api.get<{ secret: string; uri: string }>(`/users/${res.data.id}/totp/secret`)
          totpData.value = totpRes.data
          showTotp.value = true
        } catch {
          message.warning('用户已创建，请手动启用 TOTP')
        }
      }
    }
    await loadUsers()
    closeModal()
  } catch (e: any) { 
    message.error(e.response?.data?.detail || '操作失败') 
  } finally {
    saving.value = false
  }
}

async function deleteUser(u: User) {
  if (!confirm(`确定要删除用户 "${u.username}" 吗？`)) return
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
    await loadUsers()
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

async function viewTotpSecret(u: User) {
  try {
    const res = await api.get<{ secret: string; uri: string }>(`/users/${u.id}/totp/secret`)
    totpSecretData.value = res.data
    totpSecretUser.value = u
    showTotpSecret.value = true
  } catch (e: any) { message.error(e.response?.data?.detail || '获取密钥失败') }
}

async function resetPassword() {
  if (!editingUser.value || !newPassword.value || newPassword.value.length < 8) {
    message.warning('密码至少需要8位')
    return
  }
  resettingPassword.value = true
  try {
    await api.put(`/users/${editingUser.value.id}/password/reset`, { new_password: newPassword.value })
    message.success('密码已重置')
    newPassword.value = ''
  } catch (e: any) {
    message.error(e.response?.data?.detail || '密码重置失败')
  } finally {
    resettingPassword.value = false
  }
}

async function resetTotp() {
  if (!editingUser.value) return
  resettingTotp.value = true
  try {
    const res = await api.post<{ secret: string; uri: string }>(`/users/${editingUser.value.id}/totp/reset`)
    totpData.value = res.data
    showTotp.value = true
    message.success('TOTP 已重置，请扫描新的二维码')
    await loadUsers()
  } catch (e: any) {
    message.error(e.response?.data?.detail || 'TOTP 重置失败')
  } finally {
    resettingTotp.value = false
  }
}
</script>

<style scoped>
.user-manage {
  padding: 0;
}

.page-title {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 0;
  font-size: 18px;
  font-weight: 500;
  color: #fff;
}

/* 浅色模式下的标题颜色 */
html:not(.dark) .page-title {
  color: #1f2937;
}

.title-bar {
  width: 4px;
  height: 18px;
  background: #10b981;
  border-radius: 2px;
}

.data-table {
  border-radius: 8px;
  overflow: hidden;
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

:deep(.n-modal.custom-modal .n-card) {
  --n-color: #242b3d;
  --n-title-text-color: #fff;
  --n-close-icon-color: #a0aec0;
  --n-border-color: #3a4459;
}

/* 浅色模式下的弹窗样式 */
html:not(.dark) :deep(.n-modal.custom-modal .n-card) {
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
