<template>
  <div class="login-container">
    <div class="login-box">
      <div class="login-header">
        <div class="logo">
          <img src="/logo.svg" alt="" class="logo-mark" />
          <span class="logo-text">IPVIEW</span>
        </div>
      </div>

      <div class="login-content">
        <h2 class="login-title">
          <span class="title-bar"></span>
          {{ stepTitle }}
        </h2>

        <!-- Step 1: Username -->
        <div v-if="step === 1" class="step-content username-step">
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
            <span class="login-action-label">下一步</span>
            <n-icon size="20"><chevron-forward-outline /></n-icon>
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

  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useMessage } from 'naive-ui'
import { useAuthStore } from '@/stores/auth'
import { PersonOutline, LockClosedOutline, KeyOutline, ChevronForwardOutline } from '@vicons/ionicons5'
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
  if (step.value === 1) return '账户登录'
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
  box-sizing: border-box;
  padding: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-sans);
  background-color: #32c89a;
  background-image: url('/login-background.webp');
  background-position: center;
  background-size: cover;
  background-repeat: no-repeat;
  position: relative;
  overflow: hidden;
}

.login-box {
  width: min(420px, 100%);
  box-sizing: border-box;
  background: #ffffff;
  border-radius: 8px;
  box-shadow: 0 16px 44px rgba(6, 32, 22, 0.28);
  z-index: 10;
  overflow: hidden;
}

.login-header {
  display: flex;
  justify-content: center;
  padding: 17px 32px 7px;
  background: #ffffff;
}

.logo {
  display: flex;
  align-items: center;
  gap: 12px;
  color: #10b981;
}

.logo-mark {
  width: 52px;
  height: 32px;
  object-fit: contain;
}

.logo-text {
  font-family: var(--font-mono);
  font-size: 18px;
  font-weight: 600;
  letter-spacing: 2px;
  color: #000000;
}

.login-content {
  padding: 20px 32px 32px;
}

.login-title {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 0 0 28px;
  font-size: 18px;
  font-weight: 600;
  color: #1f2937;
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

.username-step .form-item label {
  display: none;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  background: #f2f5f3;
  border-radius: 6px;
  color: #64736c;
  font-size: 14px;
}

.user-info span {
  flex: 1;
  color: #173a33;
}

.form-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-item label {
  font-size: 14px;
  color: #34453d;
}

.hint-text {
  display: block;
  text-align: center;
  font-family: var(--font-mono);
  font-size: 12px;
  color: #000000;
}

/* Override naive-ui styles */
:deep(.n-input) {
  --n-height: 40px;
  --n-font-size: 16px;
  --n-color: #ffffff;
  --n-color-focus: #ffffff;
  --n-border: 1px solid #d8e0dc;
  --n-border-hover: 1px solid #10b981;
  --n-border-focus: 1px solid #10b981;
  --n-text-color: #173a33;
  --n-placeholder-color: #9aa7a1;
  --n-caret-color: #10b981;
}

.username-step :deep(.n-input) {
  --n-font-size: 15px;
}

:deep(.n-input .n-input__prefix) {
  color: #9aa7a1;
}

:deep(.n-button--primary-type) {
  --n-height: 40px;
  --n-font-size: 16px;
  --n-border-radius: 6px;
  --n-color: #10b981;
  --n-color-hover: #059669;
  --n-color-pressed: #047857;
  --n-color-focus: #10b981;
  --n-text-color: #fff;
  --n-border: none;
}

:deep(.n-button--primary-type:disabled) {
  --n-color-disabled: #34a879;
  --n-text-color-disabled: #ffffff;
}

:deep(.n-divider) {
  --n-color: #e2e9e5;
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
  color: #059669 !important;
}

.login-action-label {
  margin-right: 8px;
}

@media (max-width: 600px) {
  .login-container {
    padding: 16px;
  }

  .login-header {
    padding: 15px 24px 3px;
  }

  .logo-mark {
    width: 48px;
    height: 29px;
  }

  .logo-text {
    font-size: 17px;
  }

  .login-content {
    padding: 18px 24px 24px;
  }

  .login-title {
    margin-bottom: 24px;
    font-size: 18px;
  }

  :deep(.n-input) {
    --n-height: 46px;
  }

  :deep(.n-button--primary-type) {
    --n-height: 46px;
  }
}

</style>
