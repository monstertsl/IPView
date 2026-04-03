<template>
  <div class="login-container">
    <n-card class="login-card" :bordered="false">
      <n-h2 prefix="bar" type="info">登录</n-h2>
      <n-form ref="formRef" :model="form" :rules="rules" size="large">
        <n-form-item path="username" label="用户名">
          <n-input v-model:value="form.username" placeholder="请输入用户名" />
        </n-form-item>
        <n-form-item path="password" label="密码">
          <n-input v-model:value="form.password" type="password" show-password-on="mousedown" placeholder="请输入密码" />
        </n-form-item>
        <n-form-item v-if="showTotp" path="totpCode" label="TOTP 验证码">
          <n-input v-model:value="form.totpCode" placeholder="请输入验证码" maxlength="6" />
        </n-form-item>
        <n-button type="primary" block :loading="loading" @click="handleLogin">登录</n-button>
      </n-form>
      <n-divider />
      <n-text depth-3 style="font-size:12px">默认账号: admin / admin123</n-text>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useMessage } from 'naive-ui'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const message = useMessage()
const auth = useAuthStore()

const formRef = ref()
const loading = ref(false)
const showTotp = ref(false)
const form = reactive({ username: '', password: '', totpCode: '' })
const rules = {
  username: { required: true, message: '请输入用户名', trigger: 'blur' },
  password: { required: true, message: '请输入密码', trigger: 'blur' }
}

async function handleLogin() {
  loading.value = true
  try {
    await auth.login(form.username, form.password, form.totpCode || undefined)
    message.success('登录成功')
    router.push('/ip')
  } catch (e: any) {
    const detail = e.response?.data?.detail || '登录失败'
    if (detail === 'TOTP code required') {
      showTotp.value = true
      message.warning('请输入 TOTP 验证码')
    } else {
      message.error(detail)
    }
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-container {
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
}
.login-card {
  width: 400px;
  background: rgba(255,255,255,0.05);
  backdrop-filter: blur(10px);
}
</style>
