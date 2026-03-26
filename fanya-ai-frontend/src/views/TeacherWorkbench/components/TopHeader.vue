<template>
  <div>
    <header class="header">
      <div class="header-left" @click="$emit('nav', 'home')">
        <div class="logo-icon-wrapper">
          <el-icon :size="24"><Monitor /></el-icon>
        </div>
        <span class="logo-text hide-on-mobile">AI 智课创作中心</span>
      </div>

      <div class="header-right">
        <el-button type="primary" text size="small" class="nav-btn brand-link-btn hide-on-mobile" @click="$emit('nav', 'home')">
          <el-icon class="el-icon--left"><HomeFilled /></el-icon>
          主页
        </el-button>
        <el-divider direction="vertical" class="custom-divider hide-on-mobile" />

        <el-dropdown trigger="click" @command="handleCommand">
          <div class="user-profile">
            <el-avatar :size="32" :src="userInfo.avatar || 'https://cube.elemecdn.com/0/88/03b0d39583f48206768a7534e55bcpng.png'" class="brand-avatar" />
            <span class="user-name hide-on-mobile">{{ userInfo.nickname || userInfo.username || '教师' }}</span>
            <el-icon class="arrow-icon hide-on-mobile"><ArrowDown /></el-icon>
          </div>
          <template #dropdown>
            <el-dropdown-menu class="brand-dropdown-menu">
              <el-dropdown-item command="profile">个人中心</el-dropdown-item>
              <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </header>

    <el-dialog v-model="showProfileDialog" title="个人中心" :width="dialogWidth" center align-center class="brand-dialog">
      <div class="profile-dialog-content">
        <div class="avatar-upload-section">
          <el-avatar :size="72" :src="profileForm.avatar || 'https://cube.elemecdn.com/0/88/03b0d39583f48206768a7534e55bcpng.png'" class="brand-avatar-large" />
          <p class="role-badge">当前身份：教师</p>
        </div>

        <el-form :model="profileForm" label-width="80px" label-position="left" class="brand-form">
          <el-form-item label="登录账号">
            <el-input v-model="profileForm.username" disabled class="brand-input" />
          </el-form-item>
          <el-form-item label="用户昵称">
            <el-input v-model="profileForm.nickname" placeholder="请输入您的昵称" class="brand-input" />
          </el-form-item>
          <el-form-item label="头像地址">
            <el-input v-model="profileForm.avatar" placeholder="请输入头像图片URL地址" class="brand-input" />
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="showProfileDialog = false" class="brand-btn-outline">取消</el-button>
          <el-button type="primary" :loading="saveLoading" @click="saveProfile" class="brand-btn-primary">确认修改</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed, onUnmounted } from 'vue'
import { Monitor, ArrowDown, HomeFilled } from '@element-plus/icons-vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { updateUserProfile } from '@/api/user'

const emit = defineEmits(['nav'])
const router = useRouter()

const isMobile = ref(window.innerWidth <= 768)
const checkMobile = () => { isMobile.value = window.innerWidth <= 768 }
const dialogWidth = computed(() => isMobile.value ? '90%' : '420px')

const userInfo = ref({ nickname: '', avatar: '', username: '' })
const showProfileDialog = ref(false)
const saveLoading = ref(false)
const profileForm = reactive({ username: '', nickname: '', avatar: '' })

onMounted(() => {
  window.addEventListener('resize', checkMobile)
  const cachedUser = localStorage.getItem('userInfo')
  if (cachedUser) { userInfo.value = JSON.parse(cachedUser) }
})

onUnmounted(() => { window.removeEventListener('resize', checkMobile) })

const handleCommand = (command) => {
  if (command === 'logout') handleLogout()
  else if (command === 'profile') openProfile()
}

const handleLogout = () => {
  ElMessageBox.confirm('确定要退出登录吗？', '提示', { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' }).then(() => {
    localStorage.removeItem('token'); localStorage.removeItem('userInfo')
    router.push('/login'); ElMessage.success('已安全退出')
  }).catch(() => {})
}

const openProfile = () => {
  profileForm.username = userInfo.value.username || '未登录'
  profileForm.nickname = userInfo.value.nickname
  profileForm.avatar = userInfo.value.avatar
  showProfileDialog.value = true
}

const saveProfile = async () => {
  if (!profileForm.nickname.trim()) return ElMessage.warning('昵称不能为空')
  saveLoading.value = true
  try {
    await updateUserProfile({ username: userInfo.value.username, nickname: profileForm.nickname, avatar: profileForm.avatar })
    userInfo.value.nickname = profileForm.nickname; userInfo.value.avatar = profileForm.avatar
    localStorage.setItem('userInfo', JSON.stringify(userInfo.value))
    ElMessage.success('个人信息已更新'); showProfileDialog.value = false
  } catch (error) { console.error("保存失败", error) } 
  finally { saveLoading.value = false }
}
</script>

<style scoped>
.header {
  --primary-blue: #307AE3;
  --dark-blue: #1442D3;
  --light-blue: #D2E6FE;
  --bg-color: #F8FAFC;
  --text-main: #1E293B;
  --text-sub: #64748B;

  height: 64px; 
  background: rgba(255, 255, 255, 0.9); 
  backdrop-filter: blur(16px);
  border-bottom: 1px solid var(--light-blue);
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 32px;
  flex-shrink: 0;
  z-index: 200;
  box-shadow: 0 4px 24px rgba(48, 122, 227, 0.08);
}

.header-left { display: flex; align-items: center; gap: 12px; cursor: pointer; transition: all 0.3s; }
.header-left:hover { transform: scale(1.02); }

.logo-icon-wrapper {
  background: linear-gradient(135deg, var(--dark-blue), var(--primary-blue));
  width: 36px;
  height: 36px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #FFF;
  box-shadow: 0 4px 12px rgba(20, 66, 211, 0.2);
}

.logo-text {
  font-size: 20px;
  font-weight: 800;
  color: var(--dark-blue);
  letter-spacing: 1px;
}

.header-right { display: flex; align-items: center; gap: 16px; }
.custom-divider { height: 20px; border-color: var(--light-blue); }

.brand-link-btn { color: var(--primary-blue) !important; font-weight: 700; transition: all 0.3s; padding: 8px 16px; border-radius: 8px; }
.brand-link-btn:hover { color: var(--dark-blue) !important; background: var(--light-blue) !important; }

.user-profile {
  display: flex; align-items: center; gap: 12px; cursor: pointer; outline: none; padding: 6px 16px; border-radius: 20px;
  transition: all 0.3s; background: transparent; border: 1px solid transparent;
}
.user-profile:hover { background: var(--light-blue); border-color: transparent; box-shadow: 0 4px 12px rgba(48, 122, 227, 0.1); }
.brand-avatar { border: 2px solid var(--light-blue); }
.user-name { font-size: 14px; color: var(--dark-blue); font-weight: 700; }
.arrow-icon { font-size: 14px; color: var(--primary-blue); transition: transform 0.3s; }
.user-profile:hover .arrow-icon { transform: rotate(180deg); }
.brand-dropdown-menu { border-radius: 12px; border: 1px solid var(--light-blue); box-shadow: 0 8px 24px rgba(48, 122, 227, 0.1); }

.brand-dialog :deep(.el-dialog) {
  background: #FFFFFF; 
  border-radius: 20px; 
  border: 1px solid var(--light-blue); 
  box-shadow: 0 24px 64px rgba(20, 66, 211, 0.15); 
  overflow: hidden;
  display: flex;
  flex-direction: column;
  max-height: 80vh;
}
.brand-dialog :deep(.el-dialog__header) {
  padding: 24px;
  border-bottom: 1px solid var(--light-blue);
  flex-shrink: 0;
}
.brand-dialog :deep(.el-dialog__body) {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  min-height: 0;
}
.brand-dialog :deep(.el-dialog__footer) {
  padding: 16px 24px;
  background: #F8FAFC;
  border-top: 1px solid var(--light-blue);
  flex-shrink: 0;
  display: flex;
  justify-content: center;
  gap: 16px;
}
.profile-dialog-content { display: flex; flex-direction: column; align-items: center; padding: 10px 0; }
.brand-avatar-large { border: 4px solid var(--light-blue); }
.role-badge { font-size: 13px; color: var(--primary-blue); margin-top: 12px; background: var(--light-blue); padding: 6px 18px; border-radius: 10px; font-weight: 700; }

.brand-form { margin-top: 24px; width: 100%; }
.brand-form :deep(.el-form-item__label) { font-weight: 700; color: var(--dark-blue); }
.brand-input :deep(.el-input__wrapper) {
  background: var(--bg-color) !important; border-radius: 12px !important; box-shadow: 0 0 0 1px var(--light-blue) inset !important; transition: all 0.3s;
}
.brand-input :deep(.el-input__wrapper.is-focus) { box-shadow: 0 0 0 2px var(--primary-blue) inset !important; background: #FFFFFF !important; }

.dialog-footer { display: flex; justify-content: center; gap: 16px; }
.brand-btn-outline { background: #FFFFFF !important; border: 1px solid var(--light-blue) !important; color: var(--primary-blue) !important; border-radius: 12px; font-weight: 700; transition: all 0.3s; }
.brand-btn-outline:hover { background: var(--light-blue) !important; color: var(--dark-blue) !important; border-color: var(--primary-blue) !important; }
.brand-btn-primary { background: linear-gradient(135deg, var(--primary-blue) 0%, var(--dark-blue) 100%) !important; border: none !important; border-radius: 12px; font-weight: 700; transition: all 0.3s; }
.brand-btn-primary:hover { transform: translateY(-2px); box-shadow: 0 8px 24px rgba(48, 122, 227, 0.3) !important; }

@media screen and (max-width: 768px) {
  .hide-on-mobile { display: none !important; }
  .header { 
    padding: 0 12px;
    height: 56px;
  }
  .header-left { gap: 8px; }
  .logo-icon-wrapper {
    width: 32px;
    height: 32px;
  }
  .header-right { gap: 6px; }
  .user-profile {
    padding: 4px 8px;
    gap: 6px;
  }
  :deep(.brand-avatar) { width: 28px !important; height: 28px !important; }
}

@media screen and (max-width: 480px) {
  .header { 
    padding: 0 8px;
    height: 52px;
  }
  .logo-icon-wrapper {
    width: 28px;
    height: 28px;
  }
  :deep(.el-icon) { font-size: 18px !important; }
  .user-profile {
    padding: 2px 4px;
  }
  :deep(.brand-avatar) { width: 24px !important; height: 24px !important; }
}
</style>