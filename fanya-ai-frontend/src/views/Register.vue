<template>
  <div class="register-page">
    <!-- 背景装饰 (海洋流体风格) -->
    <div class="bg-shape bg-shape-1"></div>
    <div class="bg-shape bg-shape-2"></div>
    <div class="bg-shape bg-shape-3"></div>

    <div class="register-card">
      <div class="form-panel">
        <div class="form-inner">
          <h2 class="form-title">开启学习之旅</h2>
          <p class="form-subtitle">加入 AI 智慧课堂，体验个性化教育魅力</p>

          <!-- 角色选择 Tabs -->
          <div class="role-tabs">
            <button 
              :class="['tab-btn', { active: registerForm.role === 'student' }]" 
              @click="registerForm.role = 'student'"
            >学生注册</button>
            <button 
              :class="['tab-btn', { active: registerForm.role === 'teacher' }]" 
              @click="registerForm.role = 'teacher'"
            >教师注册</button>
          </div>

          <!-- 注册表单 -->
          <el-form :model="registerForm" :rules="rules" ref="registerRef" size="large">
            <el-form-item prop="username">
              <el-input v-model="registerForm.username" placeholder="请输入手机号或登录账号" class="brand-input">
                <template #prefix><el-icon class="large-icon"><User /></el-icon></template>
              </el-input>
            </el-form-item>
            
            <el-form-item prop="password">
              <el-input v-model="registerForm.password" type="password" placeholder="请设置登录密码（6位以上）" show-password class="brand-input">
                <template #prefix><el-icon class="large-icon"><Lock /></el-icon></template>
              </el-input>
            </el-form-item>

            <el-form-item prop="nickname">
              <el-input v-model="registerForm.nickname" placeholder="请输入您的真实姓名" class="brand-input">
                <template #prefix><el-icon class="large-icon"><EditPen /></el-icon></template>
              </el-input>
            </el-form-item>

            <el-form-item prop="college">
              <el-input v-model="registerForm.college" placeholder="请输入所属院校名称" class="brand-input">
                <template #prefix><el-icon class="large-icon"><School /></el-icon></template>
              </el-input>
            </el-form-item>

            <el-form-item prop="major">
              <el-input v-model="registerForm.major" placeholder="请输入所属专业名称" class="brand-input">
                <template #prefix><el-icon class="large-icon"><Collection /></el-icon></template>
              </el-input>
            </el-form-item>
            
            <el-form-item class="submit-item">
              <el-button class="register-button brand-btn" type="primary" @click="handleRegister" :loading="loading">立 即 注 册</el-button>
            </el-form-item>
          </el-form>

          <div class="bottom-links">
            <span class="back-link" @click="router.push('/login')">已有账号？返回登录</span>
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
import { User, Lock, EditPen, School, Collection } from '@element-plus/icons-vue' 
import { register } from '@/api/user'

const router = useRouter()
const registerRef = ref(null)
const loading = ref(false)
const registerForm = reactive({ username: '', password: '', role: 'student', nickname: '', college: '', major: '' })

const rules = {
  username:[{ required: true, message: '账号不能为空', trigger: 'blur' }],
  password:[{ required: true, message: '密码不能为空', trigger: 'blur' }, { min: 6, message: '密码不能少于6位', trigger: 'blur' }],
  nickname:[{ required: true, message: '姓名不能为空', trigger: 'blur' }]
}

const handleRegister = async () => {
  if (!registerRef.value) return
  await registerRef.value.validate(async (valid) => {
    if (valid) {
      loading.value = true
      try {
        await register(registerForm)
        ElMessage.success('注册成功，请登录！')
        router.push('/login')
      } catch (err) {
        console.error(err)
      } finally { loading.value = false }
    } else { ElMessage.warning('请补充完整注册信息') }
  })
}
</script>

<style scoped>
/* 品牌配色定义 */
.register-page {
  --brand-deep: #1442D3;
  --brand-primary: #307AE3;
  --brand-lavender: #ACB1EC;
  --brand-light: #D2E6FE;
  --bg-gradient: linear-gradient(135deg, #F8FAFC 0%, #D2E6FE 100%);
  --primary-gradient: linear-gradient(135deg, var(--brand-primary), var(--brand-deep));

  position: fixed; inset: 0; display: flex; align-items: center; justify-content: center;
  background: var(--bg-gradient); padding: 20px; overflow-y: auto;
}

/* 背景流动光影 */
.bg-shape { position: absolute; border-radius: 50%; filter: blur(140px); opacity: 0.5; z-index: 0; }
.bg-shape-1 { width: 500px; height: 500px; background: var(--brand-primary); top: -150px; left: -100px; }
.bg-shape-2 { width: 400px; height: 400px; background: var(--brand-lavender); bottom: -100px; right: 50px; }
.bg-shape-3 { width: 300px; height: 300px; background: var(--brand-deep); top: 30%; right: -100px; }

/* 注册卡片 */
.register-card {
  width: 100%; max-width: 500px; background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(24px); border-radius: 32px;
  box-shadow: 0 24px 64px rgba(20, 66, 211, 0.15);
  border: 1px solid rgba(255, 255, 255, 0.5);
  z-index: 1; padding: 50px;
  transition: all 0.4s cubic-bezier(0.25, 0.8, 0.25, 1);
}

.form-title {
  font-size: 28px; font-weight: 800; margin-bottom: 8px; text-align: center;
  background: var(--primary-gradient); -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.form-subtitle { font-size: 14px; color: var(--brand-primary); margin-bottom: 32px; text-align: center; font-weight: 600;}

/* Tab切换 */
.role-tabs { display: flex; background: #F1F5F9; border-radius: 16px; padding: 4px; margin-bottom: 32px; }
.tab-btn {
  flex: 1; border: none; background: transparent; padding: 12px; cursor: pointer;
  color: #64748B; border-radius: 12px; transition: all 0.3s; font-weight: 700; font-size: 15px;
}
.tab-btn.active { background: #FFFFFF; color: var(--brand-deep); box-shadow: 0 4px 12px rgba(0,0,0,0.05); }

/* 品牌化输入框 */
.brand-input :deep(.el-input__wrapper) {
  background: #F8FAFC !important; border-radius: 14px !important; padding: 0 20px !important;
  box-shadow: 0 0 0 1px #E2E8F0 inset !important; height: 54px !important;
}
.brand-input :deep(.el-input__wrapper.is-focus) { border-color: var(--brand-primary) !important; box-shadow: 0 0 0 2px rgba(48, 122, 227, 0.1) !important; background: #FFF !important; }
.large-icon { font-size: 20px; color: var(--brand-primary); }

/* 注册按钮 */
.brand-btn {
  width: 100%; height: 56px !important; border-radius: 16px !important; font-size: 18px !important; font-weight: 800 !important;
  background: linear-gradient(135deg, var(--brand-primary), var(--brand-deep)) !important;
  border: none !important; box-shadow: 0 8px 24px rgba(48, 122, 227, 0.25) !important;
}
.brand-btn:hover { transform: translateY(-2px); box-shadow: 0 12px 32px rgba(20, 66, 211, 0.35) !important; }

/* 底部返回 */
.back-link {
  color: var(--brand-primary); cursor: pointer; font-weight: 700; font-size: 14px;
  position: relative; transition: all 0.2s;
}
.back-link:hover { color: var(--brand-deep); }
.bottom-links { margin-top: 24px; text-align: center; }

@media (max-width: 600px) {
  .register-card { padding: 30px 20px; border-radius: 24px; }
  .form-title { font-size: 24px !important; }
}
</style>