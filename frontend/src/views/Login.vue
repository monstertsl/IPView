<template>
  <div class="login-container">
    <div class="login-box">
      <div class="login-header">
        <div class="logo">
          <svg viewBox="0 0 24 24" width="32" height="32" fill="currentColor">
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z"/>
          </svg>
          <span class="logo-text">IPVIEW</span>
        </div>
      </div>

      <div class="login-content">
        <h2 class="login-title">
          <span class="title-bar"></span>
          {{ stepTitle }}
        </h2>

        <!-- Step 1: Username -->
        <div v-if="step === 1" class="step-content">
          <div class="form-item">
            <label>用户名</label>
            <n-input 
              v-model:value="form.username" 
              placeholder="请输入用户名"
              size="large"
              @keyup.enter="checkUser"
            >
              <template #prefix>
                <n-icon><person-outline /></n-icon>
              </template>
            </n-input>
          </div>
          <n-button 
            type="primary" 
            block 
            size="large" 
            :loading="loading"
            :disabled="!form.username"
            @click="checkUser"
          >
            下一步
          </n-button>
        </div>

        <!-- Step 2: Password (for PASSWORD_ONLY or PASSWORD_AND_TOTP) -->
        <div v-else-if="step === 2" class="step-content">
          <div class="user-info">
            <n-icon size="18"><person-outline /></n-icon>
            <span>{{ form.username }}</span>
            <n-button text size="tiny" class="switch-user-btn" @click="goBack">切换用户</n-button>
          </div>

          <div v-if="needPassword" class="form-item">
            <label>密码</label>
            <n-input 
              v-model:value="form.password" 
              type="password"
              placeholder="请输入密码"
              size="large"
              show-password-on="click"
              @keyup.enter="handleNext"
            >
              <template #prefix>
                <n-icon><lock-closed-outline /></n-icon>
              </template>
            </n-input>
          </div>

          <div v-if="needTotp && !needPassword" class="form-item">
            <label>TOTP 验证码</label>
            <n-input 
              v-model:value="form.totpCode" 
              placeholder="请输入6位验证码"
              size="large"
              maxlength="6"
              @keyup.enter="handleLogin"
            >
              <template #prefix>
                <n-icon><key-outline /></n-icon>
              </template>
            </n-input>
          </div>

          <n-button 
            type="primary" 
            block 
            size="large" 
            :loading="loading"
            :disabled="needPassword ? !form.password : !form.totpCode"
            @click="handleNext"
          >
            {{ needPassword && needTotp ? '下一步' : '登录' }}
          </n-button>
        </div>

        <!-- Step 3: TOTP (for PASSWORD_AND_TOTP after password) -->
        <div v-else-if="step === 3" class="step-content">
          <div class="user-info">
            <n-icon size="18"><person-outline /></n-icon>
            <span>{{ form.username }}</span>
            <n-button text size="tiny" class="switch-user-btn" @click="goBack">切换用户</n-button>
          </div>

          <div class="form-item">
            <label>TOTP 验证码</label>
            <n-input 
              v-model:value="form.totpCode" 
              placeholder="请输入6位验证码"
              size="large"
              maxlength="6"
              @keyup.enter="handleLogin"
            >
              <template #prefix>
                <n-icon><key-outline /></n-icon>
              </template>
            </n-input>
          </div>

          <n-button 
            type="primary" 
            block 
            size="large" 
            :loading="loading"
            :disabled="!form.totpCode"
            @click="handleLogin"
          >
            登录
          </n-button>
        </div>

        <n-divider />
        <n-text class="hint-text"><a href="https://github.com/monstertsl/IPView" target="_blank" style="color: inherit; text-decoration: none;">关于 IPView</a></n-text>
      </div>
    </div>

    <!-- Background decoration -->
    <div class="bg-decoration">
      <div class="circle circle-1"></div>
      <div class="circle circle-2"></div>
      <div class="circle circle-3"></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useMessage } from 'naive-ui'
import { useAuthStore } from '@/stores/auth'
import { PersonOutline, LockClosedOutline, KeyOutline } from '@vicons/ionicons5'
import api from '@/api'

const router = useRouter()
const message = useMessage()
const auth = useAuthStore()

const step = ref(1)
const loading = ref(false)
const authMode = ref('')
const totpEnabled = ref(false)

const form = reactive({ 
  username: '', 
  password: '', 
  totpCode: '' 
})

const needPassword = computed(() => 
  authMode.value === 'PASSWORD_ONLY' || authMode.value === 'PASSWORD_AND_TOTP'
)

const needTotp = computed(() => 
  authMode.value === 'TOTP_ONLY' || authMode.value === 'PASSWORD_AND_TOTP'
)

const stepTitle = computed(() => {
  if (step.value === 1) return '登录'
  if (step.value === 2) {
    if (authMode.value === 'TOTP_ONLY') return '验证身份'
    return '输入密码'
  }
  return '两步验证'
})

async function checkUser() {
  if (!form.username) {
    message.warning('请输入用户名')
    return
  }
  
  loading.value = true
  try {
    const res = await api.post('/auth/check-user', { username: form.username })
    if (res.data.exists) {
      authMode.value = res.data.auth_mode
      totpEnabled.value = res.data.totp_enabled
    } else {
      // 用户不存在，默认密码模式（不提示用户不存在）
      authMode.value = 'PASSWORD_ONLY'
    }
    step.value = 2
  } catch (e: any) {
    // API 调用失败，默认密码模式继续
    authMode.value = 'PASSWORD_ONLY'
    step.value = 2
  } finally {
    loading.value = false
  }
}

async function handleNext() {
  if (needPassword.value && !form.password) {
    message.warning('请输入密码')
    return
  }
  
  // 如果需要密码和 TOTP，先验证完密码再进入 TOTP 步骤
  if (needPassword.value && needTotp.value) {
    step.value = 3
    return
  }
  
  // 否则直接登录
  await handleLogin()
}

async function handleLogin() {
  loading.value = true
  try {
    await auth.login(
      form.username, 
      form.password || undefined, 
      form.totpCode || undefined
    )
    message.success('登录成功')
    router.push('/ip')
  } catch (e: any) {
    const data = e.response?.data
    // 后端返回需要TOTP验证码的特殊响应
    if (data?.need_totp) {
      authMode.value = data.auth_mode || 'PASSWORD_AND_TOTP'
      if (step.value === 2 && form.password) {
        // 已输入密码，跳到TOTP步骤
        step.value = 3
      } else {
        // TOTP_ONLY模式，直接在step2显示TOTP输入
        needTotp.value
        step.value = 2
      }
      message.info('请输入TOTP验证码')
    } else {
      const detail = data?.detail || '登录失败'
      message.error(detail)
    }
  } finally {
    loading.value = false
  }
}

function goBack() {
  step.value = 1
  form.password = ''
  form.totpCode = ''
  authMode.value = ''
}
</script>

<style scoped>
.login-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #1a1f2e;
  position: relative;
  overflow: hidden;
}

.login-box {
  width: 420px;
  background: #242b3d;
  border-radius: 8px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
  z-index: 10;
  overflow: hidden;
}

.login-header {
  padding: 24px 32px;
  background: linear-gradient(135deg, #2d3548 0%, #1e2433 100%);
  border-bottom: 1px solid #3a4459;
}

.logo {
  display: flex;
  align-items: center;
  gap: 12px;
  color: #10b981;
}

.logo svg {
  color: #10b981;
}

.logo-text {
  font-size: 20px;
  font-weight: 600;
  letter-spacing: 2px;
  color: #fff;
}

.login-content {
  padding: 32px;
}

.login-title {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 0 0 28px;
  font-size: 20px;
  font-weight: 500;
  color: #fff;
}

.title-bar {
  width: 4px;
  height: 20px;
  background: #10b981;
  border-radius: 2px;
}

.step-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  background: #1a1f2e;
  border-radius: 6px;
  color: #a0aec0;
  font-size: 14px;
}

.user-info span {
  flex: 1;
  color: #fff;
}

.form-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-item label {
  font-size: 14px;
  color: #a0aec0;
}

.hint-text {
  display: block;
  text-align: center;
  font-size: 12px;
  color: #64748b;
}

/* Override naive-ui styles */
:deep(.n-input) {
  --n-color: #1a1f2e;
  --n-color-focus: #1a1f2e;
  --n-border: 1px solid #3a4459;
  --n-border-hover: 1px solid #10b981;
  --n-border-focus: 1px solid #10b981;
  --n-text-color: #fff;
  --n-placeholder-color: #64748b;
  --n-caret-color: #10b981;
}

:deep(.n-input .n-input__prefix) {
  color: #64748b;
}

:deep(.n-button--primary-type) {
  --n-color: #10b981;
  --n-color-hover: #059669;
  --n-color-pressed: #047857;
  --n-color-focus: #10b981;
  --n-text-color: #fff;
  --n-border: none;
}

:deep(.n-button--primary-type:disabled) {
  --n-color-disabled: #1e4d3d;
  --n-text-color-disabled: #64748b;
}

:deep(.n-divider) {
  --n-color: #3a4459;
}

:deep(.n-button[text]) {
  --n-text-color: #10b981;
  --n-text-color-hover: #34d399;
}

.switch-user-btn {
  color: #10b981 !important;
  font-size: 13px !important;
  font-weight: 500;
}

.switch-user-btn:hover {
  color: #34d399 !important;
}

/* Background decoration */
.bg-decoration {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  pointer-events: none;
  overflow: hidden;
}

.circle {
  position: absolute;
  border-radius: 50%;
  background: linear-gradient(135deg, rgba(16, 185, 129, 0.1) 0%, rgba(16, 185, 129, 0.02) 100%);
}

.circle-1 {
  width: 600px;
  height: 600px;
  top: -200px;
  right: -200px;
}

.circle-2 {
  width: 400px;
  height: 400px;
  bottom: -100px;
  left: -100px;
}

.circle-3 {
  width: 300px;
  height: 300px;
  top: 50%;
  left: 10%;
  transform: translateY(-50%);
}
</style>
