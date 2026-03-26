<template>
  <div class="login-page">
    <div class="bg-shape bg-shape-1"></div>
    <div class="bg-shape bg-shape-2"></div>
    <div class="bg-shape bg-shape-3"></div>

    <div class="login-card">
      <!-- 左侧品牌区域 -->
      <div class="brand-panel hide-on-mobile">
        <div class="brand-content">
          <div class="brand-logo">
            <img src="@/assets/logo.svg" alt="Fanya AI" class="logo-img" />
          </div>
          <div class="brand-features">
            <div class="feature-item"><span>🌊</span> 智课生成</div>
            <div class="feature-item"><span>🤖</span> 智能问答</div>
            <div class="feature-item"><span>🚀</span> 节奏自定</div>
          </div>
        </div>
      </div>

      <!-- 右侧登录区域 -->
      <div class="form-panel">
        <div class="form-inner">
          <h2 class="form-title">欢迎回来</h2>
          <p class="form-subtitle">开启您的 AI 智慧学习探索</p>

          <div class="role-tabs">
            <button :class="['tab-btn', { active: activeRole === 'student' }]" @click="switchRole('student')">学生登录</button>
            <button :class="['tab-btn', { active: activeRole === 'teacher' }]" @click="switchRole('teacher')">教师登录</button>
          </div>

          <el-form class="login-form" :model="loginForm" size="large" @keyup.enter="handleLogin">
            <el-form-item>
              <el-input v-model="loginForm.username" placeholder="请输入用户名" :prefix-icon="User" class="brand-input" />
            </el-form-item>

            <el-form-item>
              <el-input v-model="loginForm.password" type="password" placeholder="请输入密码" :prefix-icon="Lock" show-password class="brand-input" />
            </el-form-item>

            <div class="form-options">
              <el-checkbox v-model="autoLogin">记住我</el-checkbox>
              <span class="text-btn">忘记密码？</span>
            </div>

            <el-button class="login-button brand-btn" type="primary" @click="handleLogin" :loading="loading">登 录</el-button>
          </el-form>

          <div class="register-row">
            还没有账号？
            <span class="text-btn" @click="router.push('/register')">立即注册</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'
import { login } from '@/api/user'

const router = useRouter()
const loading = ref(false)
const activeRole = ref('student')
const autoLogin = ref(false)
const loginForm = reactive({ username: '', password: '' })
const switchRole = (role) => { activeRole.value = role; loginForm.password = '' }
const handleLogin = async () => {
  if (!loginForm.username || !loginForm.password) return ElMessage.warning('请输入账号和密码')
  loading.value = true
  try {
    const res = await login({ ...loginForm, role: activeRole.value })
    const data = res.data || res
    if (data.token) {
      localStorage.setItem('token', data.token)
      localStorage.setItem('userInfo', JSON.stringify({ username: loginForm.username, nickname: data.nickname || loginForm.username, avatar: data.avatar || '', role: data.role }))
      ElMessage.success('登录成功')
      router.push(activeRole.value === 'teacher' ? '/teacher' : '/student')
    }
  } catch (error) { console.error(error) } finally { loading.value = false }
}
</script>

<style scoped>
.login-page {
  --brand-deep: #1442D3; --brand-primary: #307AE3; --brand-lavender: #ACB1EC; --brand-light: #D2E6FE;
  position: fixed; inset: 0; display: flex; align-items: center; justify-content: center;
  background: linear-gradient(135deg, #E3F2FD 0%, #F5F9FF 100%); padding: 15px; overflow-y: auto;
}

.bg-shape { position: absolute; border-radius: 50%; filter: blur(100px); opacity: 0.4; z-index: 0; }
.bg-shape-1 { width: 400px; height: 400px; background: var(--brand-primary); top: -100px; left: -100px; }
.bg-shape-2 { width: 300px; height: 300px; background: var(--brand-lavender); bottom: -50px; right: 0; }

.login-card {
  display: flex; width: 100%; max-width: 900px; border-radius: 24px;
  background: rgba(255, 255, 255, 0.9); backdrop-filter: blur(20px);
  box-shadow: 0 10px 40px rgba(20, 66, 211, 0.1); overflow: hidden; z-index: 1;
}

.brand-panel {
  width: 40%; background: linear-gradient(135deg, #FFF, #F0F4FF);
  padding: 40px; display: flex; flex-direction: column; align-items: center; justify-content: center;
}
.brand-logo { width: 100%; max-width: 200px; margin-bottom: 20px; }
.logo-img { width: 100%; height: auto; }
.feature-item { 
  display: flex; align-items: center; gap: 10px; background: var(--brand-light); 
  padding: 10px 20px; border-radius: 12px; margin-bottom: 12px; font-weight: 700; color: var(--brand-deep);
}

.form-panel { flex: 1; padding: 40px; display: flex; align-items: center; justify-content: center; background: #FFF; }
.form-inner { width: 100%; max-width: 340px; }
.form-title { font-size: 24px; font-weight: 800; color: var(--brand-deep); margin-bottom: 8px; }
.form-subtitle { font-size: 13px; color: var(--brand-primary); margin-bottom: 24px; font-weight: 600;}

.role-tabs { display: flex; background: #F1F5F9; border-radius: 12px; padding: 4px; margin-bottom: 24px; }
.tab-btn { flex: 1; border: none; background: transparent; padding: 10px; cursor: pointer; color: #64748B; border-radius: 10px; font-weight: 700; }
.tab-btn.active { background: #FFFFFF; color: var(--brand-deep); box-shadow: 0 2px 8px rgba(0,0,0,0.05); }

.brand-input :deep(.el-input__wrapper) { background: #F8FAFC !important; border-radius: 12px !important; height: 48px !important; box-shadow: 0 0 0 1px #E2E8F0 inset !important; }
.brand-btn { width: 100%; height: 48px !important; border-radius: 12px !important; font-size: 16px !important; font-weight: 800 !important; background: linear-gradient(135deg, var(--brand-primary), var(--brand-deep)) !important; border: none !important; }

.text-btn { color: var(--brand-primary); cursor: pointer; font-weight: 700; }
.register-row { margin-top: 20px; text-align: center; color: #64748B; font-size: 14px; }

@media (max-width: 768px) {
  .login-card { flex-direction: column; max-width: 100%; border-radius: 20px; }
  .hide-on-mobile { display: none; }
  .form-panel { padding: 30px 20px; }
  .bg-shape { filter: blur(80px); }
}
</style>