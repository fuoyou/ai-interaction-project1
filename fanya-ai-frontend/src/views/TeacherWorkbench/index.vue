<template>
  <div class="teacher-app">
    <TopHeader @nav="handleNavigation" @showCourseList="courseListDrawerVisible = true" />

    <!-- 主页视图 -->
    <Home v-if="viewMode === 'home'" @selectCourse="handleSelectCourseFromHome" />

    <div class="main-viewport" v-else-if="viewMode === 'workbench'">
      <!-- 桌面端：左侧侧边栏 -->
      <aside class="left-sidebar glass-panel sidebar-desktop" style="display: none;">
        <div class="upload-section">
          <el-upload
            action="#"
            :auto-upload="false"
            :on-change="handleFileUpload"
            :show-file-list="false"
            accept=".pdf,.ppt,.pptx"
            class="full-width-upload"
          >
            <el-button class="upload-btn" :loading="isUploading">
              <el-icon class="el-icon--left"><Plus /></el-icon>
              {{ isUploading ? '正在上传...' : '上传文件' }}
            </el-button>
          </el-upload>
        </div>
        <div class="search-box">
          <el-input v-model="searchKeyword" placeholder="搜索文件..." :prefix-icon="Search" class="glass-search" />
        </div>
        <div class="list-header">文件列表</div>

        <div class="file-list">
          <div v-if="loadingList" class="loading-state">
            <el-icon class="is-loading" color="#307AE3" :size="24"><Loading /></el-icon>
          </div>
          <div
            v-for="item in filteredList"
            :key="item.id"
            :class="['file-list-item', 'glass-item', { active: currentCourseId === item.id }]"
            @click="selectCourse(item)"
          >
            <div class="active-bar" v-if="currentCourseId === item.id"></div>
            <div class="file-card-content">
              <div class="file-icon-wrapper">
                <el-icon :size="24" color="#307AE3"><Document /></el-icon>
              </div>
              <div class="file-text-info">
                <div class="file-name" :title="item.courseName">{{ item.courseName }}</div>
                <div class="file-date">日期：{{ formatDate(item.updateTime) }}</div>
              </div>
            </div>
          </div>
          <el-empty v-if="!loadingList && filteredList.length === 0" description="暂无文件" :image-size="60" />
        </div>
      </aside>

      <!-- 移动端：抽屉菜单 -->
      <el-drawer
        v-model="sidebarDrawerVisible"
        title="文件列表"
        direction="ltr"
        size="280px"
        :lock-scroll="true"
        class="sidebar-drawer glass-drawer"
        @close="sidebarDrawerVisible = false"
      >
        <div class="drawer-content">
          <div class="upload-section">
            <el-upload
              action="#"
              :auto-upload="false"
              :on-change="handleFileUpload"
              :show-file-list="false"
              accept=".pdf,.ppt,.pptx"
              class="full-width-upload"
            >
              <el-button class="upload-btn" :loading="isUploading" size="small">
                <el-icon class="el-icon--left"><Plus /></el-icon>
                {{ isUploading ? '上传中...' : '上传文件' }}
              </el-button>
            </el-upload>
          </div>
          <div class="search-box">
            <el-input v-model="searchKeyword" placeholder="搜索文件..." :prefix-icon="Search" class="glass-search" size="small" />
          </div>

          <div class="file-list drawer-file-list">
            <div v-if="loadingList" class="loading-state">
              <el-icon class="is-loading" color="#307AE3" :size="24"><Loading /></el-icon>
            </div>
            <div
              v-for="item in filteredList"
              :key="item.id"
              :class="['file-list-item', { active: currentCourseId === item.id }]"
              @click="selectCourseAndClose(item)"
            >
              <div class="file-card-content">
                <div class="file-icon-wrapper">
                  <el-icon :size="20" color="#307AE3"><Document /></el-icon>
                </div>
                <div class="file-text-info">
                  <div class="file-name" :title="item.courseName">{{ item.courseName }}</div>
                  <div class="file-date">{{ formatDate(item.updateTime) }}</div>
                </div>
              </div>
            </div>
            <el-empty v-if="!loadingList && filteredList.length === 0" description="暂无文件" :image-size="60" />
          </div>
        </div>
      </el-drawer>

      <!-- 桌面端：课件列表抽屉 -->
      <el-drawer
        v-model="courseListDrawerVisible"
        title="课件列表"
        direction="ltr"
        size="320px"
        :lock-scroll="true"
        class="course-list-drawer glass-drawer"
      >
        <div class="drawer-content">
          <div class="upload-section">
            <el-upload
              action="#"
              :auto-upload="false"
              :on-change="handleFileUpload"
              :show-file-list="false"
              accept=".pdf,.ppt,.pptx"
              class="full-width-upload"
            >
              <el-button class="upload-btn" :loading="isUploading">
                <el-icon class="el-icon--left"><Plus /></el-icon>
                {{ isUploading ? '上传中...' : '上传文件' }}
              </el-button>
            </el-upload>
          </div>
          <div class="search-box">
            <el-input v-model="searchKeyword" placeholder="搜索文件..." :prefix-icon="Search" class="glass-search" />
          </div>

          <div class="file-list drawer-file-list">
            <div v-if="loadingList" class="loading-state">
              <el-icon class="is-loading" color="#307AE3" :size="24"><Loading /></el-icon>
            </div>
            <div
              v-for="item in filteredList"
              :key="item.id"
              :class="['file-list-item', { active: currentCourseId === item.id }]"
              @click="selectCourse(item); courseListDrawerVisible = false"
            >
              <div class="file-card-content">
                <div class="file-icon-wrapper">
                  <el-icon :size="24" color="#307AE3"><Document /></el-icon>
                </div>
                <div class="file-text-info">
                  <div class="file-name" :title="item.courseName">{{ item.courseName }}</div>
                  <div class="file-date">日期：{{ formatDate(item.updateTime) }}</div>
                </div>
              </div>
            </div>
            <el-empty v-if="!loadingList && filteredList.length === 0" description="暂无文件" :image-size="60" />
          </div>
        </div>
      </el-drawer>
      
      <main class="main-content glass-panel">
        <!-- 移动端菜单按钮 -->
        <button class="mobile-menu-btn" @click="toggleSidebar" v-if="isMobile">
          <el-icon :size="24"><Menu /></el-icon>
        </button>

        <template v-if="currentCourseId">
          <header class="editor-header">
            <div class="course-title">
              <span class="title-text">{{ currentCourseName || '课件预览' }}</span>
            </div>
          </header>

          <div class="editor-body">
            <!-- 加载蒙层 -->
            <div v-if="loadingDetail" class="status-mask">
               <el-icon class="is-loading" :size="32" color="#307AE3"><Loading /></el-icon>
               <p style="margin-top:12px; color:#1442D3; font-weight: bold;">正在获取课件详情...</p>
            </div>

            <!-- 编辑器 -->
            <Step2_Editor
              v-else
              :pdf-source="pdfSource"
              :paddle-pages="paddlePages"
              v-model:slides="slideData"
              :course-id="currentCourseId"
              v-model:currentSlide="currentEditIndex"
              :category-knowledge="currentCategoryKnowledge"
              :category-id="currentCategoryId"
            />
            
            <!-- 轮询状态提示 -->
            <div v-if="isPolling" class="polling-toast glass-toast">
              <el-icon class="is-loading" :size="16" color="#307AE3"><Loading /></el-icon>
              <span>{{ pollingStatus }}</span>
            </div>
          </div>
        </template>
        <div v-else class="empty-workspace">
          <el-empty description="请从左侧选择文件开始阅读" />
        </div>
      </main>
    </div>

    <Dashboard v-else-if="viewMode === 'dashboard'" @back="handleNavigation('workbench')" />

    <!-- 自动保存提示 -->
    <div class="auto-save-toast glass-toast" :class="{ show: saveStatus !== 'idle' }">
      <el-icon v-if="saveStatus === 'saving'" class="is-loading" color="#307AE3"><Loading /></el-icon>
      <el-icon v-if="saveStatus === 'synced'" color="#307AE3"><CircleCheck /></el-icon>
      <el-icon v-if="saveStatus === 'error'" color="#f56c6c"><CircleClose /></el-icon>
      <span>{{ saveStatusText }}</span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { Plus, Loading, Search, CircleCheck, CircleClose, Document, Menu } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

import TopHeader from './components/TopHeader.vue'
import Step2_Editor from './components/Editor.vue'
import Dashboard from './Dashboard.vue'
import Home from './Home.vue'
import { listMyCourses, uploadCourse, getCourseDetail, updateCourseScript } from '@/api/course'

const viewMode = ref('home')
const courseList = ref([])
const loadingList = ref(false)
const searchKeyword = ref('')
const currentCourseId = ref(null)
const currentCourseName = ref('')
const pdfSource = ref(null)
const slideData = ref([])
const currentEditIndex = ref(0)
const isUploading = ref(false)
const currentCategoryKnowledge = ref([])
const currentCategoryId = ref('')
const paddlePages = ref([])

const sidebarDrawerVisible = ref(false)
const isMobile = ref(false)
const courseListDrawerVisible = ref(false)
const isPolling = ref(false)
const loadingDetail = ref(false) 
const pollingStatus = ref('等待响应...')
let pollingTimer = null
const isGeneratingAudio = ref(false)
let audioCheckTimer = null
const saveStatus = ref('idle')
let autoSaveTimer = null
let isSystemUpdating = false 

const saveStatusText = computed(() => {
  const map = { saving: '正在保存...', synced: '已同步到云端', error: '保存失败' }
  return map[saveStatus.value] || ''
})

watch(() => slideData.value, (newVal, oldVal) => {
  if (isSystemUpdating) return
  if (!currentCourseId.value || !newVal || newVal.length === 0) return
  const hasContent = newVal.some(item => item.script && item.script.trim().length > 0)
  if (!hasContent) return
  
  saveStatus.value = 'saving'
  if (autoSaveTimer) clearTimeout(autoSaveTimer)
  
  autoSaveTimer = setTimeout(async () => {
    try {
      const scriptsToSave = slideData.value.map(item => ({ page: item.page, content: item.script }))
      await updateCourseScript(currentCourseId.value, scriptsToSave)
      saveStatus.value = 'synced'
      setTimeout(() => { if(saveStatus.value === 'synced') saveStatus.value = 'idle' }, 2000)
      isSystemUpdating = true
      slideData.value.forEach(item => item.audioUrl = '') 
      nextTick(() => { isSystemUpdating = false })
      isGeneratingAudio.value = true
      waitForAudioGeneration(currentCourseId.value)
    } catch (error) {
      saveStatus.value = 'error'
      ElMessage.error('保存失败: ' + (error.message || '未知错误'))
      setTimeout(() => { if(saveStatus.value === 'error') saveStatus.value = 'idle' }, 2000)
    }
  }, 1500)
}, { deep: true })

const filteredList = computed(() => {
  if (!searchKeyword.value) return courseList.value
  return courseList.value.filter(item =>
    item.courseName.toLowerCase().includes(searchKeyword.value.toLowerCase())
  )
})

onMounted(() => fetchCourseList())

const fetchCourseList = async () => {
  loadingList.value = true
  try {
    const res = await listMyCourses()
    courseList.value = res.data || []
  } catch (error) { console.error(error) }
  finally { loadingList.value = false }
}

const isPdfName = (name = '') => String(name).toLowerCase().endsWith('.pdf')
const isPptxName = (name = '') => String(name).toLowerCase().endsWith('.pptx')

const handleFileUpload = async (file) => {
  const raw = file?.raw
  if (!raw) return
  const maxSize = 100 * 1024 * 1024
  if (raw.size > maxSize) {
    ElMessage.error('文件超过 100MB，无法上传，请压缩后重试')
    return
  }
  isUploading.value = true
  try {
    const res = await uploadCourse(raw)
    const parseId = res.data?.parseId
    await fetchCourseList()
    const newCourse = courseList.value.find(c => c.parseId === parseId)
    if (newCourse) {
      const localPreviewThreshold = 20 * 1024 * 1024
      if (raw.size > localPreviewThreshold || !isPdfName(raw.name)) {
        await selectCourse(newCourse)
        ElMessage.success('上传成功，后台解析中...')
      } else {
        await selectCourse(newCourse, raw)
        ElMessage.success('上传成功')
      }
    } else {
      ElMessage.success('上传成功，解析任务已提交')
    }
  } catch (error) { ElMessage.error('上传失败') }
  finally { isUploading.value = false }
}

const selectCourse = async (courseRow, rawFile = null) => {
  currentCourseId.value = courseRow.id
  currentCourseName.value = courseRow.courseName
  currentEditIndex.value = 0
  isSystemUpdating = true
  slideData.value = []
  paddlePages.value = []
  nextTick(() => { isSystemUpdating = false })
  if (pollingTimer) clearInterval(pollingTimer)
  if (audioCheckTimer) clearInterval(audioCheckTimer)
  isPolling.value = false
  isGeneratingAudio.value = false
  saveStatus.value = 'idle'
  
  if (rawFile) {
    if (isPdfName(rawFile.name) || isPptxName(rawFile.name)) {
      pdfSource.value = URL.createObjectURL(rawFile)
    } else {
      pdfSource.value = null
      ElMessage.info('PPT 正在后台转换为可预览格式，请稍候...')
    }
    slideData.value = []
    isSystemUpdating = false
    startPolling(courseRow.id)
    return
  }

  loadingDetail.value = true
  try {
    const res = await getCourseDetail(courseRow.id)
    const detailData = res.data
    paddlePages.value = detailData.paddlePages || detailData.structurePreview?.paddlePages || []
    if (detailData.fileUrl && (isPdfName(detailData.fileUrl) || isPptxName(detailData.fileUrl))) {
      pdfSource.value = `/api/v1/lesson/files/${detailData.fileUrl}`
    } else { pdfSource.value = null }
    const status = detailData.status
    if (status === 0 || status === 1) {
      startPolling(courseRow.id)
    } else if (status === 2) {
      parseData(detailData.aiScript, detailData.audioScript)
      isGeneratingAudio.value = true
      waitForAudioGeneration(courseRow.id)
    } else if (status === 3) {
      parseData(detailData.aiScript, detailData.audioScript)
      isGeneratingAudio.value = false
    } else if (status === 9) {
      if (detailData.aiScript && detailData.aiScript.length > 0) {
        parseData(detailData.aiScript, detailData.audioScript)
      } else {
        ElMessage.error('该课件解析失败，请尝试重新上传')
      }
    }
  } catch (error) { ElMessage.error('获取课件详情失败') }
  finally { loadingDetail.value = false }
}

const toggleSidebar = () => { sidebarDrawerVisible.value = !sidebarDrawerVisible.value }
const selectCourseAndClose = async (item) => {
  await selectCourse(item)
  sidebarDrawerVisible.value = false
}
const checkScreenSize = () => { isMobile.value = window.innerWidth <= 768 }

onMounted(() => {
  checkScreenSize()
  window.addEventListener('resize', checkScreenSize)
  fetchCourseList()
})

onUnmounted(() => {
  window.removeEventListener('resize', checkScreenSize)
  if (pollingTimer) clearInterval(pollingTimer)
  if (audioCheckTimer) clearInterval(audioCheckTimer)
  if (autoSaveTimer) clearTimeout(autoSaveTimer)
})

const startPolling = (courseId) => {
  isPolling.value = true
  pollingStatus.value = 'AI 引擎启动中...'
  pollingTimer = setInterval(async () => {
    if (currentCourseId.value !== courseId) { clearInterval(pollingTimer); isPolling.value = false; return }
    try {
      const res = await getCourseDetail(courseId)
      const course = res.data
      paddlePages.value = course.paddlePages || course.structurePreview?.paddlePages || []
      if (course.fileUrl && (isPdfName(course.fileUrl) || isPptxName(course.fileUrl))) {
        pdfSource.value = `/api/v1/lesson/files/${course.fileUrl}`
      }
      
      // 检查是否已完成
      if (course.status === 3) {
        clearInterval(pollingTimer)
        isPolling.value = false
        parseData(course.aiScript, course.audioScript)
        isGeneratingAudio.value = false
        return
      }
      
      if (course.aiScript && course.aiScript.length > 0) {
        parseData(course.aiScript, course.audioScript || [])
        if (course.status >= 2) { pollingStatus.value = '正在合成语音...' } 
        else { pollingStatus.value = `正在生成讲稿... (${course.aiScript.length}页已完成)` }
      }
      
      if (course.status === 2) {
        clearInterval(pollingTimer)
        isPolling.value = false
        parseData(course.aiScript, course.audioScript)
        isGeneratingAudio.value = true
        waitForAudioGeneration(courseId)
      } else if (course.status === 9) {
        clearInterval(pollingTimer)
        isPolling.value = false
        ElMessage.error('解析失败')
      }
    } catch (err) { console.error(err); clearInterval(pollingTimer); isPolling.value = false }
  }, 2000)
}

const waitForAudioGeneration = (courseId) => {
  if(audioCheckTimer) clearInterval(audioCheckTimer)
  audioCheckTimer = setInterval(async () => {
    if (currentCourseId.value !== courseId) { clearInterval(audioCheckTimer); return }
    try {
      const res = await getCourseDetail(courseId)
      const data = res.data
      let audioReady = false
      if (data.status === 3) audioReady = true
      else if (data.audioScript && Array.isArray(data.audioScript) && data.audioScript.length > 0) {
         audioReady = data.audioScript.some(s => s.audioUrl && s.audioUrl.length > 5)
      }
      if (audioReady) {
        clearInterval(audioCheckTimer)
        isGeneratingAudio.value = false
        parseData(data.aiScript, data.audioScript)
        ElMessage.success('语音合成已就绪')
      }
    } catch (e) { clearInterval(audioCheckTimer) }
  }, 3000)
}

const parseData = (scriptData, audioData) => {
  try {
    const textArr = typeof scriptData === 'string' ? JSON.parse(scriptData) : (scriptData || [])
    const audioArr = typeof audioData === 'string' ? JSON.parse(audioData) : (audioData || [])
    if (!Array.isArray(textArr) || textArr.length === 0) return
    let audioMap = {}
    if (Array.isArray(audioArr)) {
      audioArr.forEach(item => { if (item.page) audioMap[item.page] = item.audioUrl })
    }
    isSystemUpdating = true
    slideData.value = textArr.map(item => ({
      page: item.page, title: `第 ${item.page} 页`, script: item.content || '', audioUrl: audioMap[item.page] || '', quiz: null
    }))
    nextTick(() => { isSystemUpdating = false })
  } catch (e) { console.error('Data parse error', e) }
}

const formatDate = (dateStr) => {
  if (!dateStr) return '未知'
  return dateStr.replace('T', ' ').split('.')[0]
}

const handleNavigation = (target) => { viewMode.value = target }

const handleSelectCourseFromHome = (course, categoryKnowledge = [], categoryId = '') => {
  currentCategoryKnowledge.value = categoryKnowledge
  currentCategoryId.value = categoryId
  selectCourse(course)
  viewMode.value = 'workbench'
}
</script>

<style scoped>
/* 全局背景：采用极简淡蓝色到白色的渐变，突出中心内容 */
.teacher-app { 
  position: fixed;
  inset: 0;
  width: 100%;
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: linear-gradient(135deg, #F5F9FF 0%, #D2E6FE 100%);
}

.main-viewport { 
  flex: 1;
  display: flex;
  overflow: hidden;
  padding: 16px;
  gap: 16px;
}

/* Element Plus 全局组件重写 - 指定新颜色体系 */
:deep(.el-button--primary) {
  --el-button-bg-color: #307AE3;
  --el-button-border-color: #307AE3;
  --el-button-hover-bg-color: #1442D3;
  --el-button-hover-border-color: #1442D3;
}
:deep(.el-button--primary.is-plain) {
  --el-button-text-color: #307AE3;
  --el-button-bg-color: #D2E6FE;
  --el-button-border-color: #ACB1EC;
  --el-button-hover-text-color: #FFF;
  --el-button-hover-bg-color: #307AE3;
  --el-button-hover-border-color: #307AE3;
}

/* 玻璃拟态面板通用样式 */
.glass-panel {
  background: rgba(255, 255, 255, 0.90) !important;
  backdrop-filter: blur(16px);
  border: 1px solid rgba(255, 255, 255, 0.4);
  border-radius: 16px;
  box-shadow: 0 8px 32px rgba(48, 122, 227, 0.08);
}

.glass-item {
  background: rgba(255, 255, 255, 0.7);
  border: 1px solid rgba(210, 230, 254, 0.8);
  border-radius: 12px;
  transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
}

.glass-item:hover {
  background: #FFFFFF;
  box-shadow: 0 8px 20px rgba(48, 122, 227, 0.1);
  border-color: #ACB1EC;
  transform: translateY(-2px);
}

/* 侧边栏 */
.left-sidebar { 
  width: 280px; 
  display: flex; 
  flex-direction: column; 
  flex-shrink: 0; 
  padding: 24px 16px; 
  overflow-y: auto;
}

.upload-section { margin-bottom: 24px; }
.full-width-upload, .full-width-upload :deep(.el-upload) { width: 100%; display: block; }

.upload-btn { 
  width: 100%;
  height: 48px;
  border-radius: 12px;
  font-weight: bold;
  font-size: 15px;
  background: linear-gradient(135deg, #307AE3 0%, #ACB1EC 100%) !important; 
  border: none !important;
  color: #FFFFFF !important;
  transition: all 0.3s;
  box-shadow: 0 4px 15px rgba(48, 122, 227, 0.3);
}

.upload-btn:hover {
  box-shadow: 0 8px 25px rgba(48, 122, 227, 0.4);
  transform: translateY(-2px);
  background: linear-gradient(135deg, #1442D3 0%, #307AE3 100%) !important; 
}

.search-box { margin-bottom: 20px; }

.glass-search :deep(.el-input__wrapper) {
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.6) !important;
  box-shadow: 0 0 0 1px #D2E6FE inset !important;
  backdrop-filter: blur(4px);
  transition: all 0.3s;
}

.glass-search :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 2px #307AE3 inset !important;
  background: #FFFFFF !important;
}

.list-header {
  font-size: 14px;
  color: #1442D3;
  margin-bottom: 12px;
  padding: 0 4px;
  font-weight: bold;
}

.file-list { 
  flex: 1; 
  overflow-y: auto; 
  display: flex; 
  flex-direction: column; 
  gap: 12px; 
  padding: 4px 4px 20px 4px; 
}

/* 课件列表项 */
.file-list-item { 
  position: relative;
  padding: 16px;
  cursor: pointer;
  overflow: hidden;
}

.file-list-item.active {
  border-color: #307AE3;
  background: rgba(210, 230, 254, 0.5);
  box-shadow: 0 4px 16px rgba(48, 122, 227, 0.15);
}

.active-bar {
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 5px;
  height: 32px;
  background: #307AE3;
  border-radius: 0 4px 4px 0;
  box-shadow: 2px 0 8px rgba(48, 122, 227, 0.4);
}

.file-card-content { 
  display: flex;
  align-items: center;
  gap: 14px;
}

.file-icon-wrapper {
  flex-shrink: 0;
  width: 44px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #307AE3;
  background: #D2E6FE;
  border-radius: 10px;
  transition: all 0.3s;
}
.file-list-item:hover .file-icon-wrapper {
  background: #307AE3;
  color: #FFF;
}
.file-list-item.active .file-icon-wrapper {
  background: #1442D3;
  color: #FFF;
}

.file-text-info { 
  flex: 1;
  overflow: hidden;
}

.file-name {
  font-size: 15px;
  color: #1442D3;
  font-weight: bold;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-bottom: 6px;
}

.file-date {
  font-size: 12px;
  color: #ACB1EC;
  font-weight: 600;
}

/* 主区域编辑器 */
.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.editor-header {
  height: 64px;
  border-bottom: 1px solid rgba(210, 230, 254, 0.8);
  display: flex;
  align-items: center;
  padding: 0 24px;
  background: rgba(255, 255, 255, 0.5);
}

.title-text {
  font-weight: bold;
  color: #1442D3;
  font-size: 18px;
}

.editor-body {
  flex: 1;
  overflow: hidden;
  position: relative;
}

.status-mask {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
}

.empty-workspace {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
}

/* 浮动提示 */
.glass-toast {
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(12px);
  border: 1px solid #D2E6FE;
  color: #1442D3;
  font-weight: bold;
  box-shadow: 0 8px 24px rgba(48, 122, 227, 0.15);
  border-radius: 10px;
}

.polling-toast {
  position: absolute;
  top: 24px;
  right: 24px;
  padding: 12px 20px;
  display: flex;
  align-items: center;
  gap: 10px;
  z-index: 100;
  font-size: 14px;
}

.auto-save-toast {
  position: fixed;
  bottom: 24px;
  right: 24px;
  padding: 12px 20px;
  font-size: 14px;
  display: flex;
  align-items: center;
  gap: 10px;
  z-index: 9999;
  opacity: 0;
  transform: translateY(15px);
  transition: all 0.4s cubic-bezier(0.25, 0.8, 0.25, 1);
  pointer-events: none;
}

.auto-save-toast.show {
  opacity: 1;
  transform: translateY(0);
}

:deep(.glass-drawer .el-drawer) {
  background: rgba(255, 255, 255, 0.95) !important;
  backdrop-filter: blur(20px) !important;
  border-left: 1px solid #D2E6FE !important;
}

/* 响应式移动端适配 */
@media screen and (max-width: 768px) {
  .main-viewport { 
    flex-direction: column; 
    overflow: hidden; 
    padding: 8px;
    gap: 8px;
  }
  .sidebar-desktop { display: none; }
  .main-content { 
    width: 100%; 
    flex: 1; 
    position: relative; 
    border-radius: 12px;
    padding: 0;
    display: flex;
    flex-direction: column;
  }
  .editor-header {
    height: 56px;
    padding: 0 16px;
    font-size: 16px;
    flex-shrink: 0;
  }
  .title-text {
    font-size: 16px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .editor-body {
    flex: 1;
    overflow: hidden;
    display: flex;
    flex-direction: column;
  }
  .mobile-menu-btn { 
    display: none !important;
  }
  .polling-toast {
    top: 16px;
    right: 16px;
    padding: 10px 16px;
    font-size: 12px;
    border-radius: 8px;
  }
  .auto-save-toast {
    bottom: 16px;
    right: 16px;
    padding: 10px 16px;
    font-size: 12px;
  }
}

@media screen and (max-width: 480px) {
  .main-viewport { padding: 6px; gap: 6px; }
  .editor-header { 
    height: 52px;
    padding: 0 12px;
  }
  .title-text { font-size: 14px; }
  .polling-toast {
    top: 12px;
    right: 12px;
    padding: 8px 12px;
    font-size: 11px;
  }
  .auto-save-toast {
    bottom: 12px;
    right: 12px;
    padding: 8px 12px;
    font-size: 11px;
  }
}

@media screen and (min-width: 769px) {
  .sidebar-desktop { display: flex; }
  .sidebar-drawer { display: none; }
  .mobile-menu-btn { display: none; }
}

/* 移动端菜单按钮 */
.mobile-menu-btn {
  position: absolute;
  top: 50%;
  left: 12px;
  transform: translateY(-50%);
  z-index: 50;
  background: #FFFFFF;
  border: 1px solid #D2E6FE;
  border-radius: 10px;
  padding: 10px;
  cursor: pointer;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 12px rgba(48, 122, 227, 0.15);
  color: #307AE3;
  display: none !important;
}

/* 滚动条美化 */
::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-thumb { background: #ACB1EC; border-radius: 6px; }
::-webkit-scrollbar-thumb:hover { background: #307AE3; }
::-webkit-scrollbar-track { background: transparent; }
</style>