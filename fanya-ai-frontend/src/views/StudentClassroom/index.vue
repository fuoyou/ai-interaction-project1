<template>
  <div class="student-app">
    <!-- 1. 顶部导航 -->
    <header class="header">
      <div class="header-left">
        <el-button link @click="handleExit" class="back-btn hide-on-mobile">
          <el-icon><ArrowLeft /></el-icon> 退出
        </el-button>
        <el-divider direction="vertical" class="hide-on-mobile" />
        <el-button link class="menu-btn" @click="showSidebarDrawer = true" title="课件列表">
          <el-icon><Menu /></el-icon>
          <span class="hide-on-mobile">课件列表</span>
        </el-button>
        <el-divider direction="vertical" class="hide-on-mobile" />
        <span class="course-title">{{ currentFileName || '正在加载...' }}</span>
        
        <!-- 【功能】：可视化进度节点（小圆点），结合 NLP 闪烁状态 (移动端隐藏) -->
        <div class="knowledge-nodes hide-on-mobile" v-if="fullAiScript.length > 0">
          <div 
            v-for="(item, index) in Math.min(10, fullAiScript.length)"  
            :key="index"  
            :class="[
              'node-item', 
              { active: currentPage > (index * (fullAiScript.length / 10)) }, 
              { current: Math.floor(currentPage / (fullAiScript.length / 10)) === index },
              { 'warning-blink': Math.floor(currentPage / (fullAiScript.length / 10)) === index && isRhythmAdjusting }
            ]"
          >
            <el-tooltip :content="'阶段 ' + (index + 1)" placement="bottom"><span></span></el-tooltip>
          </div>
        </div>
      </div>

      <div class="header-right">
        <!-- 【功能】：可视化进度百分比 -->
        <el-tag v-if="fullAiScript.length > 0" type="primary" effect="light" round size="small" class="progress-tag">
          进度：{{ Math.round((currentPage / fullAiScript.length) * 100) }}%
        </el-tag>
        
        <el-tag type="success" effect="plain" round size="small" class="hide-on-mobile" style="margin-left: 10px;">
          <div class="tag-inner"><div class="dot"></div>AI 助教已就绪</div>
        </el-tag>
        
        <!-- 用户头像下拉菜单 -->
        <el-dropdown trigger="click" @command="handleUserCommand" class="user-dropdown">
          <div class="user-profile">
            <el-avatar 
              :size="28" 
              :src="userInfo.avatar || 'https://cube.elemecdn.com/3/7c/3ea6beec64369c2642b92c6726f1epng.png'" 
              class="clickable-avatar"
            />
            <span class="user-name-label hide-on-mobile">{{ userInfo.nickname || userInfo.username }}</span>
            <el-icon class="arrow-down hide-on-mobile"><ArrowDown /></el-icon>
          </div>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="history">学习记录</el-dropdown-item>
              <el-dropdown-item divided command="back">返回课程</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </header>

    <!-- 课件列表抽屉 -->
    <el-drawer 
      v-model="showSidebarDrawer" 
      title="课件列表" 
      direction="ltr"
      :size="isMobile ? '80%' : '320px'"
      class="course-drawer"
    >
      <div class="drawer-content">
        <div class="upload-box">
          <el-upload
            action="#"
            :auto-upload="false"
            :on-change="onFileChange"
            :show-file-list="false"
            accept=".pdf,.ppt,.pptx"
          >
            <el-button type="primary" class="upload-btn">
              <el-icon class="el-icon--left"><Upload /></el-icon>
              导入私有课件
            </el-button>
          </el-upload>
        </div>
        <div class="search-box">
          <el-input v-model="searchKeyword" placeholder="搜索课件..." clearable>
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
        </div>
        <div class="file-list" v-loading="loadingCourses">
          <el-empty v-if="!loadingCourses && filteredCourses.length === 0" description="暂无课件" :image-size="60" />
          <div
            v-for="item in filteredCourses"
            :key="item.id"
            :class="courseItemClass(item)"
            @click="onCourseItemClick(item)"
          >
            <div class="file-icon-wrapper">
              <span class="file-type-tag">{{ getFileType(item.courseName).toUpperCase() }}</span>
            </div>
            <div class="file-text-info">
              <div class="file-name">{{ item.courseName }}</div>
              <div class="file-meta">{{ item.teacherName || '我的课件' }}</div>
            </div>
          </div>
        </div>
      </div>
    </el-drawer>

    <!-- 2. 主体工作区 -->
    <main class="main-container" @mouseup="stopResize" @mousemove="handleResize">
      <div class="content-area">
        <!-- 左侧/中间部分：PDF 视图 -->
        <div v-if="showPdf" class="pdf-container" :style="pdfContainerStyle">
          <div v-if="showParsingBanner" class="parsing-hint-row">
            <el-icon class="is-loading parsing-hint-icon"><Loading /></el-icon>
            <span class="parsing-hint-text">{{ parseParsingPhaseUi.label }}</span>
            <el-progress
              v-if="parseParsingPhaseUi.showProgress"
              :percentage="parseParsingPhaseUi.percentage"
              :indeterminate="parseParsingPhaseUi.indeterminate"
              :stroke-width="4"
              class="parsing-hint-progress"
            />
          </div>
          <div class="pdf-viewer-wrap">
            <PdfViewer 
              v-loading="loading"
              :source="pdfSource" 
              :page="currentPage"
              :paddle-pages="coursePaddlePages"
              @changePage="handlePageChange" 
              @upload="showSidebarDrawer = true"
              @textSelected="handleTextSelected"
            />
          </div>
        </div>
        
        <!-- 处理中：转 PDF / Paddle / 讲稿 -->
        <div v-else-if="showLessonPending" class="pdf-placeholder" :style="pdfContainerStyle">
          <div class="placeholder-content parse-wait">
            <el-icon :size="56" class="is-loading"><Loading /></el-icon>
            <p v-if="parseParsingPhaseUi.label" class="parse-title">{{ parseParsingPhaseUi.label }}</p>
            <el-progress
              v-if="parseParsingPhaseUi.showProgress"
              :percentage="parseParsingPhaseUi.percentage"
              :indeterminate="parseParsingPhaseUi.indeterminate"
              :stroke-width="10"
              class="parse-progress-bar"
            />
            <p class="parse-hint">处理完成后将自动进入课件学习</p>
          </div>
        </div>
        <!-- 解析失败 -->
        <div v-else-if="showLessonFailed" class="pdf-placeholder" :style="pdfContainerStyle">
          <div class="placeholder-content">
            <el-icon :size="60" color="#F56C6C"><CircleClose /></el-icon>
            <p class="placeholder-text">课件处理失败，无法学习本课件</p>
            <p v-if="parseErrorMessage" class="parse-error">{{ parseErrorMessage }}</p>
          </div>
        </div>
        <!-- 未选择课件 -->
        <div v-else class="pdf-placeholder" :style="pdfContainerStyle">
          <div class="placeholder-content">
            <el-icon :size="60" color="#909399"><Document /></el-icon>
            <p class="placeholder-text">请选择一门已就绪的课件开始学习</p>
            <el-button type="primary" round @click="showSidebarDrawer = true">
              <el-icon class="el-icon--left"><Menu /></el-icon>
              课件列表
            </el-button>
          </div>
        </div>
        
        <!-- 拖拽拉伸条 -->
        <div v-if="!isMobile" class="resizer" @mousedown="startResize">
          <div class="resizer-handle"></div>
        </div>

        <!-- 右侧部分：AI 对话框 (移动端时变为下方区域) -->
        <div class="right-panel" :style="rightPanelStyle">
          <!-- 拖拽把手区 -->
          <div class="dialog-drag-handle">
            <span class="dialog-title">AI 助教互动区</span>
            <el-button 
              link 
              size="small" 
              @click="toggleRhythmPanel"
              style="color: #2196F3; font-size: 14px; font-weight: 600;"
            >
              <el-icon><TrendCharts /></el-icon> {{ showRhythmPanel ? '隐藏诊断' : 'AI 诊断' }}
            </el-button>
          </div>
          
          <!-- 节奏诊断面板（可折叠） -->
          <transition name="slide-down">
            <div v-show="showRhythmPanel" class="rhythm-panel-container">
              <RhythmPanel 
                ref="rhythmPanelRef"
                :lessonId="currentCourseId" 
                @reviewSection="handleReviewSection"
              />
            </div>
          </transition>
          
          <!-- 聊天与讲解区 -->
          <AiSidebar 
            v-show="!showRhythmPanel"
            ref="aiSidebarRef"
            style="flex: 1; overflow: hidden; display: flex; flex-direction: column;"
            :width="'100%'" 
            v-model:mode="currentMode" 
            :script="currentScript" 
            :audioUrl="currentAudioUrl"
            :history="chatHistory" 
            :isChatLoading="isChatLoading"
            :courseId="currentCourseId"
            @sendMessage="onSendMessage" 
            @replay="startLecture" 
            @resolve="handleResolveSupplement" 
            @speakContent="handleSpeakContent"
            @jumpToPage="handleJumpToPage"
            @chatTextSelected="handleChatTextSelected"
            @pauseAudio="handlePauseAudio"
            @resumeAudio="handleResumeAudio"
          ></AiSidebar>
        </div>

        <!-- 数字人悬浮球（支持自由拖拽） -->
        <div 
          class="avatar-floating-ball" 
          :style="{ left: ballPos.x + 'px', top: ballPos.y + 'px', bottom: 'auto', right: 'auto' }"
          @mousedown="startDragBall"
          @touchstart="startDragBall"
          @click="toggleAvatarWindow"
        >
          <div class="ball-inner">
            <el-icon><VideoCamera /></el-icon>
          </div>
          <div v-if="isSpeakingGlobal" class="ball-pulse"></div>
        </div>

        <!-- 数字人浮窗（可拖动，无背景） -->
        <div 
          v-show="showAvatarWindow"
          class="avatar-floating-window"
          :class="{ 'audio-only-window': !showAvatar }"
          :style="{ left: isMobile ? '5%' : avatarWindowPos.x + 'px', top: isMobile ? '20%' : avatarWindowPos.y + 'px' }"
          @mousedown="!isMobile && startDragAvatarWindow($event)"
        >
          <div class="avatar-window-header" @mousedown.stop="!isMobile && startDragAvatarWindow($event)">
            <span class="avatar-window-title">{{ showAvatar ? 'AI 数字讲师' : 'AI 语音伴读' }}</span>
            <div class="header-actions">
              <el-icon class="close-btn" @click.stop="closeAvatarWindow"><Close /></el-icon>
            </div>
          </div>
          <div class="avatar-window-content">
            <DigitalAvatar 
              ref="digitalAvatarRef"
              :script="currentScript" 
              :page="currentPage"
              :speakText="digitalHumanText" 
              :mode="currentMode"
              :totalPages="fullAiScript.length"
              :isRhythmAdjusting="isRhythmAdjusting"
              :showAvatar="showAvatar"
              :showWindow="showAvatarWindow"
              @autoNextPage="handleAutoNextPage"
              @speaking="isSpeakingGlobal = $event"
            />
          </div>
        </div>
      </div>
    </main>

    <!-- 3. 学习记录抽屉 -->
    <el-drawer v-model="showHistoryDrawer" title="学习互动足迹" direction="rtl" :size="isMobile ? '100%' : '400px'">
      <div v-loading="historyLoading">
        <el-empty v-if="historyList.length === 0" description="尚无互动记录" />
        <el-timeline v-else style="padding: 10px">
          <el-timeline-item v-for="(item, index) in historyList" :key="index" :timestamp="formatTime(item.createTime)" :type="item.action === 'CONTINUE' ? 'primary' : 'warning'" hollow>
            <div class="history-card">
              <div class="history-page-tag">第 {{ item.pageNum }} 页</div>
              <div class="history-q"><strong>问：</strong>{{ item.question }}</div>
              <div class="history-a"><p>{{ item.aiReply }}</p></div>
            </div>
          </el-timeline-item>
        </el-timeline>
      </div>
    </el-drawer>

    <!-- 5. 智能插旗考点弹窗 -->
    <CheckpointDialog 
      v-model="showCheckpointDialog" 
      :checkpoint="currentCheckpoint"
      :lesson-id="currentCourseId"
      @continue="handleCheckpointContinue"
    />
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElNotification } from 'element-plus'
import { ArrowLeft, ArrowDown, Upload, Document, VideoCamera, Close, TrendCharts, Search, Menu, Loading, CircleClose } from '@element-plus/icons-vue'

// API 接口导入
import { diagnoseRhythm, getLearningHistory } from '@/api/rhythm' 
import { getCourseDetail, listMyStudentCourses, listTeacherCourses, uploadCourse, chatWithAI } from '@/api/course' 
import { qaInteractStream } from '@/api/qa'
import { getProgressDetail, trackProgress } from '@/api/progress' 
import { updateUserProfile } from '@/api/user'

import PdfViewer from './components/PdfViewer.vue'
import AiSidebar from './components/AiSidebar.vue'
import DigitalAvatar from './components/DigitalAvatar.vue'
import CheckpointDialog from './components/CheckpointDialog.vue'
import RhythmPanel from './components/RhythmPanel.vue'

const route = useRoute()
const router = useRouter()
const isModeSwitching = ref(false);
// --- 响应式适配状态 ---
const isMobile = ref(false)
const showSidebarDrawer = ref(false) // 课件抽屉

const checkMobile = () => {
  isMobile.value = window.innerWidth <= 768
}

// 动态计算 PDF 容器宽度
const pdfContainerStyle = computed(() => {
  if (isMobile.value) {
    return { width: '100%', height: '40%' } // 手机端上下分屏
  }
  return { width: `calc(100% - ${chatPanelWidth.value}px)` } // 桌面端左右分屏
})

// 动态计算右侧 AI 面板样式
const rightPanelStyle = computed(() => {
  if (isMobile.value) {
    return { width: '100%', height: '60%', margin: '0', borderRadius: '12px 12px 0 0' }
  }
  return { width: `${chatPanelWidth.value}px` } 
})

// --- 响应式状态 ---
const pdfSource = ref(null)
const currentPage = ref(1)
const currentFileName = ref('')
const chatPanelWidth = ref(420)
const currentMode = ref('lecture')
const loading = ref(false)
const isResizing = ref(false)
const isRhythmAdjusting = ref(false)
const currentScript = ref('')
const currentAudioUrl = ref('') 
const chatHistory = ref([{ role: 'ai', type: 'normal', content: '同学你好，欢迎进入 AI 智慧课堂。' }])

const fullAiScript = ref([])
const fullAudioScript = ref([]) 
const isChatLoading = ref(false) 
const qaSessionId = ref('')
const courseList = ref([])
const loadingCourses = ref(false)
const searchKeyword = ref('')
const currentCourseId = ref(null)
const coursePaddlePages = ref([])

/** 最近一次课件详情中的状态，用于解析进度条 */
const lessonDetail = ref({ status: null, taskStatus: null, pageCount: 0, aiScriptLen: 0 })
const parseErrorMessage = ref('')

const applyLessonDetail = (d) => {
  if (!d) return
  lessonDetail.value = {
    status: d.status,
    taskStatus: d.taskStatus,
    pageCount: d.fileInfo?.pageCount ?? 0,
    aiScriptLen: Array.isArray(d.aiScript) ? d.aiScript.length : 0
  }
}

/** 仅「解析阶段」：转 PDF、版面解析；不展示讲稿/伴学生成阶段的进度与文案 */
const parseParsingPhaseUi = computed(() => {
  const d = lessonDetail.value
  const ts = d.taskStatus
  const st = d.status
  const idle = { label: '', showProgress: false, indeterminate: true, percentage: 0 }
  if (st === 3 || st === 9) return idle
  if (ts === 'converting_pdf') {
    return {
      label: '正在将课件转换为 PDF（WPS / PowerPoint）…',
      showProgress: true,
      indeterminate: true,
      percentage: 0
    }
  }
  if (ts === 'paddle_parsing') {
    return {
      label: 'PaddleOCR-VL 正在解析版面与文字…',
      showProgress: true,
      indeterminate: true,
      percentage: 0
    }
  }
  if (ts === 'generating_script') {
    return { label: '', showProgress: false, indeterminate: true, percentage: 0 }
  }
  return { label: '课件处理中…', showProgress: false, indeterminate: true, percentage: 0 }
})

const userInfo = ref({ nickname: '', avatar: '', username: '' })
const showProfileDialog = ref(false)
const saveLoading = ref(false)

const showHistoryDrawer = ref(false)
const historyList = ref([])
const historyLoading = ref(false)

const showRhythmPanel = ref(false)
const rhythmPanelRef = ref(null)
const aiSidebarRef = ref(null)

const showCheckpointDialog = ref(false)
const currentCheckpoint = ref({
  question: '',
  type: 'choice',
  options: [],
  correctAnswer: '',
  explanation: ''
})
const checkpoints = ref([]) 
const passedCheckpoints = ref(new Set()) 

// --- 数字人悬浮球（自由拖动）逻辑 ---
const showAvatarWindow = ref(false)
const isSpeakingGlobal = ref(false)
const showAvatar = ref(false) 
const ballPos = ref({ x: -999, y: -999 }) 
const isDraggingBall = ref(false)
let hasDraggedBall = false
let ballDragOffset = { x: 0, y: 0 }

const startDragBall = (e) => {
  isDraggingBall.value = true
  hasDraggedBall = false
  const clientX = e.clientX || e.touches[0].clientX
  const clientY = e.clientY || e.touches[0].clientY
  ballDragOffset.x = clientX - ballPos.value.x
  ballDragOffset.y = clientY - ballPos.value.y
  
  document.addEventListener('mousemove', onDragBall)
  document.addEventListener('mouseup', stopDragBall)
  document.addEventListener('touchmove', onDragBall, { passive: false })
  document.addEventListener('touchend', stopDragBall)
}

const onDragBall = (e) => {
  if (!isDraggingBall.value) return
  e.preventDefault() 
  hasDraggedBall = true
  const clientX = e.clientX || e.touches[0].clientX
  const clientY = e.clientY || e.touches[0].clientY
  let newX = clientX - ballDragOffset.x
  let newY = clientY - ballDragOffset.y

  const ballSize = 60
  newX = Math.max(0, Math.min(newX, window.innerWidth - ballSize))
  newY = Math.max(0, Math.min(newY, window.innerHeight - ballSize))
  
  ballPos.value = { x: newX, y: newY }
}

const stopDragBall = () => {
  isDraggingBall.value = false
  document.removeEventListener('mousemove', onDragBall)
  document.removeEventListener('mouseup', stopDragBall)
  document.removeEventListener('touchmove', onDragBall)
  document.removeEventListener('touchend', stopDragBall)
}

// 组件引用 
const digitalAvatarRef = ref(null)

// 切换数字人窗口状态并且确保自动发声
const toggleAvatarWindow = async () => {
  if (isModeSwitching.value) return; 
  isModeSwitching.value = true;
  
  // 切换窗口显示状态
  showAvatarWindow.value = !showAvatarWindow.value;
  showAvatar.value = showAvatarWindow.value;
  
  // 切换完成后，主动触发重读本页，完美解决不能自动发声的问题
  setTimeout(() => {
    isModeSwitching.value = false;
    if (currentMode.value === 'lecture') {
        startLecture();
    }
  }, 350); 
}

// 关闭数字人窗口，回到语音伴读模式并自动发声
const closeAvatarWindow = () => {
  showAvatarWindow.value = false
  showAvatar.value = false 
  console.log('[数字人] 关闭窗口，回到语音伴读模式')
  
  // 主动触发发声
  setTimeout(() => {
    if (currentMode.value === 'lecture') {
        startLecture();
    }
  }, 350);
}

// 切换数字人/语音模式
const toggleAvatarMode = () => {
  if (isModeSwitching.value) return;
  isModeSwitching.value = true;
  
  showAvatar.value = !showAvatar.value
  ElMessage.success(showAvatar.value ? '已切换到数字人模式' : '已切换到语音伴读模式')
  
  // 【关键修复】切换模式后自动触发讲解，无需点击重讲本页
  setTimeout(() => {
    isModeSwitching.value = false;
    if (currentMode.value === 'lecture') {
      startLecture();
    }
  }, 350);
}

// --- 数字人浮窗拖动逻辑 ---
const avatarWindowPos = ref({ x: window.innerWidth - 400, y: 100 })
const isDraggingAvatarWindow = ref(false)
const dragStartPos = ref({ x: 0, y: 0 })

const startDragAvatarWindow = (e) => {
  if (isMobile.value) return 
  isDraggingAvatarWindow.value = true
  dragStartPos.value = {
    x: e.clientX - avatarWindowPos.value.x,
    y: e.clientY - avatarWindowPos.value.y
  }
  document.addEventListener('mousemove', onDragAvatarWindow)
  document.addEventListener('mouseup', stopDragAvatarWindow)
  e.preventDefault()
}

const onDragAvatarWindow = (e) => {
  if (!isDraggingAvatarWindow.value) return
  const newX = Math.max(0, Math.min(e.clientX - dragStartPos.value.x, window.innerWidth - 300))
  const newY = Math.max(0, Math.min(e.clientY - dragStartPos.value.y, window.innerHeight - 300))
  avatarWindowPos.value = { x: newX, y: newY }
}

const stopDragAvatarWindow = () => {
  isDraggingAvatarWindow.value = false
  document.removeEventListener('mousemove', onDragAvatarWindow)
  document.removeEventListener('mouseup', stopDragAvatarWindow)
}

const digitalHumanText = ref('')
const showPdf = ref(false)

/** 本地 blob 预览 URL，切换为服务端地址前需 revoke */
const studentBlobPreviewUrl = ref(null)

const revokeStudentBlobPreview = () => {
  if (studentBlobPreviewUrl.value) {
    URL.revokeObjectURL(studentBlobPreviewUrl.value)
    studentBlobPreviewUrl.value = null
  }
  if (pdfSource.value && String(pdfSource.value).startsWith('blob:')) {
    pdfSource.value = null
  }
}

const isPdfFileName = (name = '') => String(name).toLowerCase().endsWith('.pdf')
const isPptxFileName = (name = '') => String(name).toLowerCase().endsWith('.pptx')

/** 与教师端一致：≤20MB 的 PDF/PPTX 上传后先用本地 blob 预览 */
const LOCAL_PREVIEW_MAX_BYTES = 20 * 1024 * 1024

const showLessonPending = computed(() => {
  if (!currentCourseId.value || showPdf.value) return false
  const st = lessonDetail.value.status
  return st !== 9 && st !== 3
})

/** 课件区顶部提示条：讲稿生成阶段不显示（避免遮挡阅读且不再展示伴学相关进度） */
const showParsingBanner = computed(() => {
  if (!showPdf.value || !currentCourseId.value) return false
  const st = lessonDetail.value.status
  if (st === 9 || st === 3) return false
  return lessonDetail.value.taskStatus !== 'generating_script'
})

const showLessonFailed = computed(() => {
  return !!(currentCourseId.value && !showPdf.value && lessonDetail.value.status === 9)
})

const isPolling = ref(false)
let pollingTimer = null

const isPreviewableUrl = (url) => {
  if (!url) return false
  const lower = String(url).toLowerCase()
  return lower.endsWith('.pdf') || lower.endsWith('.pptx')
}

const startPollingForStudent = (courseId) => {
  if (pollingTimer) clearInterval(pollingTimer)
  isPolling.value = true
  
  pollingTimer = setInterval(async () => {
    if (currentCourseId.value !== courseId) {
      clearInterval(pollingTimer)
      isPolling.value = false
      return
    }
    try {
      const res = await getCourseDetail(courseId)
      const detailData = res.data || res
      if (detailData) {
        applyLessonDetail(detailData)
        coursePaddlePages.value = detailData.paddlePages || detailData.structurePreview?.paddlePages || []
        fullAiScript.value = detailData.aiScript || []
        fullAudioScript.value = detailData.audioScript || []
        updateCurrentScript()

        if (detailData.status === 9) {
          parseErrorMessage.value = detailData.parseError || detailData.structurePreview?.parseError || ''
          ElMessage.error(parseErrorMessage.value || '课件解析失败')
          revokeStudentBlobPreview()
          pdfSource.value = null
          showPdf.value = false
          clearInterval(pollingTimer)
          isPolling.value = false
          return
        }

        // 与教师端一致：服务端返回可预览 PDF/PPTX 后即展示，解析与讲稿可在后台继续
        const fu = detailData.fileUrl
        if (fu && isPreviewableUrl(fu)) {
          const serverSrc = `/api/v1/lesson/files/${fu}`
          if (pdfSource.value !== serverSrc) {
            revokeStudentBlobPreview()
            pdfSource.value = serverSrc
          }
          showPdf.value = true
        }

        if (detailData.status === 3) {
          parseErrorMessage.value = ''
          clearInterval(pollingTimer)
          isPolling.value = false
        }
      }
    } catch (err) {
      clearInterval(pollingTimer)
      isPolling.value = false
    }
  }, 3000) 
}

const filteredCourses = computed(() => {
  if (!searchKeyword.value) return courseList.value
  const key = searchKeyword.value.toLowerCase()
  return courseList.value.filter(item => (item.courseName || '').toLowerCase().includes(key))
})

const getFileType = (fileName) => {
  if (!fileName) return 'other'
  const ext = fileName.split('.').pop().toLowerCase()
  return ['pdf'].includes(ext) ? 'pdf' : (['ppt', 'pptx'].includes(ext) ? 'ppt' : 'other')
}

const courseItemClass = (item) => {
  const isCurrent = item.id === currentCourseId.value
  const isPending = item.status !== 3 && item.status !== 9
  return [
    'file-list-item',
    { active: isCurrent },
    { 'pending-other': isPending && !isCurrent }
  ]
}

const onCourseItemClick = (item) => {
  const isCurrent = item.id === currentCourseId.value
  const isPending = item.status !== 3 && item.status !== 9
  if (isPending && !isCurrent) {
    ElMessage.warning('该课件仍在处理中，完成后才可进入学习')
    return
  }
  selectCourse(item, { force: !!(isPending && isCurrent) })
}

const selectCourse = async (course, opts = {}) => {
  const force = opts.force === true
  if (!course || !course.id) return
  const lessonReady = (c) => c.status === 3 || c.status === 9
  if (!force && !lessonReady(course)) {
    ElMessage.warning('该课件仍在处理中，完成后才可进入学习')
    return
  }
  // 切换课件前停止所有音频
  globalAudioManager.stopAll()
  if (digitalAvatarRef.value) {
    digitalAvatarRef.value.stopAudio()
  }
  if (pollingTimer) clearInterval(pollingTimer)
  isPolling.value = false
  revokeStudentBlobPreview()

  currentCourseId.value = course.id
  currentFileName.value = course.courseName || ''
  loading.value = true
  showSidebarDrawer.value = false
  parseErrorMessage.value = ''
  
  // 重置思维导图、知识图谱和测验题数据
  if (aiSidebarRef.value) {
    aiSidebarRef.value.resetGraphData()
    aiSidebarRef.value.resetQuizData()
  }
  
  try {
    const res = await getCourseDetail(course.id)
    const detailData = res.data || res
    applyLessonDetail(detailData)
    coursePaddlePages.value = detailData.paddlePages || detailData.structurePreview?.paddlePages || []
    const fileUrl = detailData.fileUrl || course.fileUrl || ''

    const st = detailData.status
    if (st === 9) {
      revokeStudentBlobPreview()
      parseErrorMessage.value = detailData.parseError || detailData.structurePreview?.parseError || ''
      ElMessage.error(parseErrorMessage.value || '课件解析失败，无法学习本课件')
      pdfSource.value = null
      showPdf.value = false
      fullAiScript.value = detailData.aiScript || []
      fullAudioScript.value = detailData.audioScript || []
      updateCurrentScript()
      loading.value = false
      return
    }

    if (st !== 3) {
      const rawFile = opts.rawFile
      if (rawFile && (isPdfFileName(rawFile.name) || isPptxFileName(rawFile.name))) {
        studentBlobPreviewUrl.value = URL.createObjectURL(rawFile)
        pdfSource.value = studentBlobPreviewUrl.value
        showPdf.value = true
      } else if (fileUrl && isPreviewableUrl(fileUrl)) {
        pdfSource.value = `/api/v1/lesson/files/${fileUrl}`
        showPdf.value = true
      } else {
        pdfSource.value = null
        showPdf.value = false
        if (fileUrl && String(fileUrl).toLowerCase().endsWith('.ppt')) {
          ElMessage.info('PPT 正在后台转换为可预览格式，请稍候…')
        }
      }
      currentMode.value = 'lecture'
      try {
        const progressRes = await getProgressDetail(course.id)
        const progressData = progressRes.data
        if (progressData && progressData.currentSectionId) {
          const lastPage = parseInt(progressData.currentSectionId.replace('sec', ''))
          currentPage.value = lastPage || 1
        } else {
          currentPage.value = 1
        }
      } catch (err) {
        currentPage.value = 1
      }
      chatHistory.value = [{ role: 'ai', type: 'normal', content: `课件正在后台生成讲稿，您可先浏览课件。《${currentFileName.value}》` }]
      fullAiScript.value = detailData.aiScript || []
      fullAudioScript.value = detailData.audioScript || []
      checkpoints.value = detailData.checkpoints || []
      passedCheckpoints.value.clear()
      updateCurrentScript()
      startPollingForStudent(course.id)
      loading.value = false
      return
    }

    if (!fileUrl || !isPreviewableUrl(fileUrl)) {
      revokeStudentBlobPreview()
      pdfSource.value = null
      showPdf.value = false
      ElMessage.error('该课件文件暂时无法预览')
      fullAiScript.value = detailData.aiScript || []
      fullAudioScript.value = detailData.audioScript || []
      updateCurrentScript()
      loading.value = false
      return
    }

    parseErrorMessage.value = ''
    revokeStudentBlobPreview()
    pdfSource.value = `/api/v1/lesson/files/${fileUrl}`
    
    currentMode.value = 'lecture'
    
    try {
      const progressRes = await getProgressDetail(course.id)
      const progressData = progressRes.data
      if (progressData && progressData.currentSectionId) {
        const lastPage = parseInt(progressData.currentSectionId.replace('sec', ''))
        currentPage.value = lastPage || 1
      } else {
        currentPage.value = 1 
      }
    } catch (err) {
      currentPage.value = 1 
    }

    chatHistory.value =[{ role: 'ai', type: 'normal', content: `同学你好，正在学习《${currentFileName.value}》。` }]
    fullAiScript.value = detailData.aiScript || []
    fullAudioScript.value = detailData.audioScript || []
    checkpoints.value = detailData.checkpoints || []
    passedCheckpoints.value.clear() 

    updateCurrentScript()
    showPdf.value = true

  } catch (e) {
    ElMessage.error('该课件文件暂时无法预览')
  } finally {
    loading.value = false
  }
}

const updateCurrentScript = () => {
  if (fullAiScript.value.length > 0) {
    const currentSlide = fullAiScript.value.find(
      slide => slide.page === currentPage.value || slide.pageNum === currentPage.value
    )
    if (currentSlide && currentSlide.content) {
      currentScript.value = currentSlide.content
    } else {
      currentScript.value = `当前第 ${currentPage.value} 页无讲稿内容。`
    }
    const currentAudio = fullAudioScript.value.find(
      audio => audio.page === currentPage.value
    )
    currentAudioUrl.value = (currentAudio && currentAudio.audioUrl) ? currentAudio.audioUrl : ''
  } else {
    currentScript.value = "同学你好，AI 正在为你准备本页的深度解析，请稍等片刻。"
    currentAudioUrl.value = "/api/v1/lesson/audio/system_loading.mp3" 
  }
}

const handlePageChange = (delta) => { 
  if (typeof delta === 'number') {
    currentPage.value += delta
  }
  
  const checkpoint = checkpoints.value.find(cp => cp.pageNum === currentPage.value)
  
  // 只在遇到考题时才强制打断
  if (checkpoint && !passedCheckpoints.value.has(checkpoint.id)) {
    window.speechSynthesis.cancel()
    if (digitalAvatarRef.value) {
      digitalAvatarRef.value.stopAudio()
    }
    currentScript.value = '' 
    currentMode.value = 'chat'
    digitalHumanText.value = ''
    currentCheckpoint.value = checkpoint
    showCheckpointDialog.value = true
    return 
  }
  
  // 正常翻页处理
  currentMode.value = 'lecture' 
  
  if (digitalAvatarRef.value) {
    digitalAvatarRef.value.stopAudio()
  }
  
  // 增加延迟时间，确保旧音频完全停止后再开始新播放
  currentScript.value = ''
  setTimeout(() => {
    updateCurrentScript() 
  }, 300)
  
  // 跟踪进度
  if (currentCourseId.value) {
    trackProgress({
      courseId: currentCourseId.value,
      lessonId: currentCourseId.value,
      pageNum: currentPage.value,
      progressPercent: Math.round((currentPage.value / fullAiScript.value.length) * 100)
    }).catch(e => {})
  }
}

const handleAutoNextPage = () => {
  if (currentPage.value < fullAiScript.value.length) {
    handlePageChange(1);
  }
}

const handleCheckpointContinue = () => {
  passedCheckpoints.value.add(currentCheckpoint.value.id)
  showCheckpointDialog.value = false
  
  currentMode.value = 'lecture'
  
  setTimeout(() => {
    updateCurrentScript();
    // 【关键修复】更新讲稿后自动触发讲解
    if (currentMode.value === 'lecture') {
      startLecture();
    }
  }, 150)
}

const startLecture = () => {
  window.speechSynthesis.cancel()
  const tempScript = currentScript.value
  const tempAudio = currentAudioUrl.value
  currentScript.value = ''
  currentAudioUrl.value = ''
  // 使用setTimeout确保DigitalAvatar组件能够检测到变化触发监听发声
  setTimeout(() => {
    currentScript.value = tempScript
    currentAudioUrl.value = tempAudio
    console.log('[学生端] startLecture触发讲稿播放');
  }, 100)
}

const loadCourseList = async () => {
  loadingCourses.value = true
  try {
    let studentCourses = []
    let teacherCourses = []
    
    try {
      const studentRes = await listMyStudentCourses()
      studentCourses = Array.isArray(studentRes.data) ? studentRes.data : (Array.isArray(studentRes) ? studentRes : [])
    } catch (e) {
      console.error('获取学生课件失败:', e)
    }
    
    try {
      const teacherRes = await listTeacherCourses()
      teacherCourses = Array.isArray(teacherRes.data) ? teacherRes.data : (Array.isArray(teacherRes) ? teacherRes : [])
    } catch (e) {
      console.error('获取老师课件失败:', e)
    }
    
    courseList.value = [
      ...teacherCourses,
      ...studentCourses.map(c => ({ ...c, isPersonal: true }))
    ]
    
    return courseList.value
  } catch (e) {
    ElMessage.error('课件列表刷新失败')
  } finally {
    loadingCourses.value = false
  }
}

const onFileChange = async (file) => {
  if (!file || !file.raw) return
  const raw = file.raw
  const useLocalBlob =
    raw.size <= LOCAL_PREVIEW_MAX_BYTES &&
    (isPdfFileName(raw.name) || isPptxFileName(raw.name))
  loading.value = true
  try {
    const res = await uploadCourse(raw)
    const data = res.data || res
    const newId = data?.id
    const parseId = data?.parseId
    if (useLocalBlob) {
      ElMessage.success('上传成功')
    } else {
      ElMessage.success('上传成功，后台解析中…')
    }
    const newList = await loadCourseList()
    const target = newList.find(c =>
      (newId != null && String(c.id) === String(newId)) ||
      (parseId && c.parseId === parseId)
    )
    if (target) {
      await selectCourse(target, { force: true, rawFile: useLocalBlob ? raw : undefined })
    } else if (newList.length > 0) {
      await selectCourse(newList[0], { force: true, rawFile: useLocalBlob ? raw : undefined })
    }
  } catch (e) {
    ElMessage.error('课件处理失败，请检查文件格式')
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  checkMobile()
  window.addEventListener('resize', checkMobile)
  
  ballPos.value = {
    x: window.innerWidth - 100,
    y: window.innerHeight - 150
  }

  const cachedUser = localStorage.getItem('userInfo')
  if (cachedUser) userInfo.value = JSON.parse(cachedUser)

  const list = await loadCourseList()
  const routeId = route.params.id
  const firstReady = list.find(c => c.status === 3)
  if (routeId) {
    const target = list.find(c => String(c.id) === String(routeId))
    if (target) {
      const needForce = target.status !== 3 && target.status !== 9
      selectCourse(target, { force: needForce })
    }
  } else if (firstReady) {
    selectCourse(firstReady)
  }
  
  // 将全局音频管理器传递给 DigitalAvatar 组件
  if (digitalAvatarRef.value) {
    digitalAvatarRef.value.setGlobalAudioManager(globalAudioManager)
  }
})

onUnmounted(() => {
  if (pollingTimer) clearInterval(pollingTimer)
  revokeStudentBlobPreview()
  window.removeEventListener('resize', checkMobile)
  // 组件卸载时停止所有音频
  globalAudioManager.stopAll()
  // 【关键修复】同时停止数字人组件内的所有音频
  if (digitalAvatarRef.value) {
    digitalAvatarRef.value.stopAudio()
  }
})

// 全局音频管理器 - 确保任何时候只有一个声音播放
const globalAudioManager = {
  currentAudio: null,
  currentAudioUrl: null,
  
  // 停止所有音频
  stopAll() {
    // 停止 Web Speech API
    if (window.speechSynthesis) {
      window.speechSynthesis.cancel()
    }
    
    // 停止 HTML5 Audio
    if (this.currentAudio) {
      this.currentAudio.pause()
      this.currentAudio.currentTime = 0
      if (this.currentAudioUrl) {
        URL.revokeObjectURL(this.currentAudioUrl)
      }
      this.currentAudio = null
      this.currentAudioUrl = null
    }
    
    console.log('[全局音频管理器] 已停止所有音频')
  },
  
  // 播放新音频（会自动停止之前的）
  play(audio, audioUrl) {
    this.stopAll()
    this.currentAudio = audio
    this.currentAudioUrl = audioUrl
  }
}

const handleExit = () => {
  // 退出课件前停止所有音频
  globalAudioManager.stopAll()
  if (digitalAvatarRef.value) {
    digitalAvatarRef.value.stopAudio()
  }
  router.push('/student')
}

const handleUserCommand = async (cmd) => {
  if (cmd === 'history') {
    showHistoryDrawer.value = true
    await loadLearningHistory()
  }
  else if (cmd === 'back') {
    handleExit()
  }
}

const loadLearningHistory = async () => {
  if (!currentCourseId.value) {
    ElMessage.warning('请先选择一个课件')
    return
  }
  
  historyLoading.value = true
  try {
    const res = await getLearningHistory(currentCourseId.value)
    historyList.value = res.data || []
  } catch (e) {
    historyList.value = []
  } finally {
    historyLoading.value = false
  }
}

// 修改后的提问逻辑：兼容多种关键词触发降维讲解并自动播放
const onSendMessage = async (text) => {
  if (!currentCourseId.value) return ElMessage.warning('请先选择一个课件')
  if (showLessonPending.value) return ElMessage.warning('请等待课件解析完成后再提问')
  
  // 【新增】：检测表达“听不懂”和“要求重讲”的各类关键词
  const misunderstandKeywords = ['不明白', '不懂', '不会', '再讲一遍', '听不懂', '没听懂', '太难了', '重新讲', '没懂', '能再讲', '不理解'];
  const isMisunderstood = misunderstandKeywords.some(keyword => text.includes(keyword));
  
  if (isMisunderstood) {
    isRhythmAdjusting.value = true
    console.log('[节奏调整] 检测到学生没听懂，准备触发降维讲稿')
  } else {
    isRhythmAdjusting.value = true
    console.log('[节奏调整] 学生提问，立即进入节奏调整模式')
  }
  
  const historyQa = chatHistory.value
    .filter(msg => msg.role === 'user' || msg.role === 'ai')
    .slice(-6)
    .map(msg => ({ role: msg.role, content: msg.content }))

  chatHistory.value.push({ role: 'user', content: text })
  currentMode.value = 'chat'
  isChatLoading.value = true 
  
  try {
    const aiMsg = { role: 'ai', type: 'normal', content: '', audioUrl: '', streaming: true }
    chatHistory.value.push(aiMsg)
    const aiMsgIndex = chatHistory.value.length - 1
    let donePayload = null

    // 如果检测到学生不懂，在向后端请求的文字中追加特定的触发短语，保证命中后端原有判定逻辑
    const apiQuestion = isMisunderstood && !text.includes('能再讲一遍吗')
      ? `${text}，能再讲一遍吗`
      : text;

    await qaInteractStream(
      { courseId: currentCourseId.value, lessonId: currentCourseId.value, pageNum: currentPage.value, sessionId: qaSessionId.value, question: apiQuestion, historyQa, currentPageContent: currentScript.value },
      {
        onMeta: (meta) => { if (meta?.sessionId) qaSessionId.value = meta.sessionId },
        onDelta: (delta) => { chatHistory.value[aiMsgIndex].content += delta?.text || '' },
        onDone: (payload) => { donePayload = payload },
        onError: (err) => { throw new Error(err?.message || '流式回答失败') }
      }
    )

    const data = donePayload || {}
    chatHistory.value[aiMsgIndex].streaming = false
    chatHistory.value[aiMsgIndex].audioUrl = data.audioUrl || ''

    if (data.answerContent && !chatHistory.value[aiMsgIndex].content) {
      chatHistory.value[aiMsgIndex].content = data.answerContent
    }
    if (data.sessionId) qaSessionId.value = data.sessionId

    if (!chatHistory.value[aiMsgIndex].content || !chatHistory.value[aiMsgIndex].content.trim()) {
      chatHistory.value.splice(aiMsgIndex, 1)
    } else {
      const userMsg = chatHistory.value.find(m => m.role === 'user' && m.sourceType === 'text-selection' && m.sourcePage === currentPage.value)
      if (userMsg) chatHistory.value[aiMsgIndex].sourcePage = userMsg.sourcePage
    }

    // 处理降维重讲逻辑
    if (data.understandingLevel === 'none' || isMisunderstood) {
      const suppText = data.supplementContent || "看来这里有点难，没关系，我们换个简单的方式再讲一遍..."
      chatHistory.value.push({ role: 'ai', type: 'supplement', content: suppText, resolved: false })
      isRhythmAdjusting.value = true
      
      // 【关键优化】：触发降维后，强制切回讲解模式以便能自动发声
      currentMode.value = 'lecture'
      
      // 提取目标讲稿，优先使用后端结构化返回的 adjustedScript
      let targetScript = currentScript.value
      if (data.adjustedScript && data.adjustedScript.trim()) {
        targetScript = data.adjustedScript
      } else if (data.answerContent && data.answerContent.trim()) {
        targetScript = data.answerContent
      }
      
      // 【关键优化】：先清空讲稿再赋值，触发数字人组件内部的讲稿变更监听自动播放
      currentScript.value = ''
      setTimeout(() => {
        currentScript.value = targetScript
      }, 150)
      
      setTimeout(() => {
        const chatArea = document.querySelector('.chat-area')
        if (chatArea) chatArea.scrollTop = chatArea.scrollHeight
      }, 100)
    }
  } catch (e) { 
    const lastMsg = chatHistory.value[chatHistory.value.length - 1]
    if (lastMsg && lastMsg.role === 'ai' && lastMsg.streaming) chatHistory.value.pop()
    
    try {
      const res = await chatWithAI({ courseId: currentCourseId.value, pageNum: currentPage.value, question: text, historyQa, currentPageContent: currentScript.value })
      const data = res.data || res
      chatHistory.value.push({ role: 'ai', type: 'normal', content: data.answerContent || '系统忙，请稍后再试', audioUrl: data.audioUrl })
      if (data.sessionId) qaSessionId.value = data.sessionId
    } catch {
      ElMessage.error('AI 响应异常')
    }
  } finally {
    isChatLoading.value = false 
  }
}

// 【关键修复】点击“已掌握（继续讲解）”后通过加载原讲稿触发自动播放
const handleResolveSupplement = (msgIndex) => {
    chatHistory.value[msgIndex].resolved = true
    isRhythmAdjusting.value = false
    ElNotification({ title: '节奏同步成功', message: '已为您切换回原讲授节点，继续讲解。', type: 'success', duration: 2000 })
    
    if (digitalAvatarRef.value) {
        digitalAvatarRef.value.stopAudio()
    }
    
    currentMode.value = 'lecture'
    
    // 【修改】强制清除当前状态，获取回原始的完整讲解讲稿进行播放
    currentScript.value = ''
    setTimeout(() => {
        updateCurrentScript()
    }, 150)
    
    if (rhythmPanelRef.value) rhythmPanelRef.value.refreshDiagnosis()
}

const handleSpeakContent = (content) => {
  digitalHumanText.value = content;
}

const formatTime = (t) => t ? new Date(t).toLocaleString() : ''

const startResize = () => { if (!isMobile.value) isResizing.value = true }
const handleResize = (e) => {
  if (!isResizing.value || isMobile.value) return
  const w = window.innerWidth - e.clientX
  if (w > 300 && w < 800) chatPanelWidth.value = w
}
const stopResize = () => { isResizing.value = false }

const handleReviewSection = (sectionId) => {
  try {
    const pageNum = parseInt(sectionId.replace('sec', ''))
    if (pageNum && pageNum > 0 && pageNum <= fullAiScript.value.length) {
      const delta = pageNum - currentPage.value
      handlePageChange(delta)
      ElMessage.success(`已跳转到第 ${pageNum} 页`)
      showRhythmPanel.value = false
    }
  } catch (e) {
    ElMessage.warning('无法跳转到该章节')
  }
}

// 切换AI诊断面板 - 点击时关闭讲解声音
const toggleRhythmPanel = () => {
  // 如果即将打开诊断面板，先关闭声音
  if (!showRhythmPanel.value) {
    globalAudioManager.stopAll()
    if (digitalAvatarRef.value) {
      digitalAvatarRef.value.stopAudio()
    }
    window.speechSynthesis.cancel()
  }
  showRhythmPanel.value = !showRhythmPanel.value
}

const handleTextSelected = ({ text, page, isFormula }) => {
  const cleanText = text.replace(/\s+/g, ' ').trim()
  let question = isFormula ? `请详细解释第${page}页中的这个公式的含义和应用：\n\n${cleanText}` : `请解释第${page}页中的这段内容：\n\n${cleanText}`
  onSendMessage(question)
  const lastUserMsg = chatHistory.value.filter(m => m.role === 'user').pop()
  if (lastUserMsg) {
    lastUserMsg.sourceType = isFormula ? 'formula-selection' : 'text-selection'
    lastUserMsg.sourcePage = page
    lastUserMsg.sourceText = text
  }
  ElMessage.success(isFormula ? '已选中公式并生成提问' : '已自动生成提问')
}

const handleJumpToPage = (pageNum) => {
  if (pageNum && pageNum > 0 && pageNum <= fullAiScript.value.length) {
    const delta = pageNum - currentPage.value
    handlePageChange(delta)
    ElMessage.success(`已跳转到第 ${pageNum} 页`)
  } else {
    ElMessage.warning('页码超出范围')
  }
}

const handleChatTextSelected = ({ text, originalMessage }) => {
  const hasFormula = text.includes('$') || text.includes('\\(') || text.includes('\\[');
  let question = hasFormula ? `请详细解释这个公式的含义和应用：${text}` : `请进一步解释："${text.substring(0, 100)}${text.length > 100 ? '...' : ''}"`
  onSendMessage(question)
  ElMessage.success('已生成追问')
}

// 处理暂停音频（测验时）
const handlePauseAudio = () => {
  globalAudioManager.stopAll()
  if (digitalAvatarRef.value) {
    digitalAvatarRef.value.stopAudio()
  }
}

// 处理恢复音频（返回学习时）
const handleResumeAudio = () => {
  // 重新播放当前页的讲解
  startLecture()
}
</script>

<style scoped>
.student-app { 
  position: fixed; 
  inset: 0; 
  display: flex; 
  flex-direction: column; 
  overflow: hidden; 
  background: linear-gradient(135deg, #E3F2FD 0%, #F5F9FF 50%, #F0F5FF 100%); 
}

:deep(.el-button) {
  border-radius: 20px;
  transition: all 0.3s ease;
}
:deep(.el-button--primary:not(.is-plain)) {
  background: linear-gradient(135deg, #2196F3 0%, #1976D2 100%);
  border: none;
  box-shadow: 0 4px 10px rgba(33, 150, 243, 0.3);
}
:deep(.el-button--primary:not(.is-plain):hover) {
  transform: translateY(-2px);
  box-shadow: 0 6px 15px rgba(33, 150, 243, 0.4);
}

.header { 
  height: 54px; 
  background: linear-gradient(90deg, #FFFFFF 0%, #F8FBFE 100%); 
  backdrop-filter: blur(4px); 
  border-bottom: 1px solid rgba(33, 150, 243, 0.15); 
  display: flex; justify-content: space-between; align-items: center; padding: 0 20px; flex-shrink: 0;
  box-shadow: 0 2px 6px rgba(33, 150, 243, 0.08);
  z-index: 10;
}
.header-left { display: flex; align-items: center; gap: 10px; }
.menu-btn { font-weight: 600; }

.knowledge-nodes { display: flex; gap: 6px; margin-left: 15px; }
.node-item { width: 8px; height: 8px; background: rgba(33, 150, 243, 0.2); border-radius: 50%; transition: all 0.3s; cursor: pointer; }
.node-item.active { background: #64B5F6; }
.node-item.current { background: #2196F3; transform: scale(1.3); box-shadow: 0 0 8px rgba(33, 150, 243, 0.5); }
.node-item.warning-blink {
  background: #FFA726 !important; 
  animation: blink-orange 1.2s infinite ease-in-out;
  box-shadow: 0 0 12px rgba(255, 167, 38, 0.6);
}
@keyframes blink-orange {
  0% { opacity: 1; transform: scale(1.3); }
  50% { opacity: 0.4; transform: scale(1); }
  100% { opacity: 1; transform: scale(1.3); }
}

.course-title { font-size: 14px; font-weight: bold; color: #1565C0; margin-left: 5px;}
.header-right { display: flex; align-items: center; gap: 10px; }
.user-profile { display: flex; align-items: center; gap: 8px; cursor: pointer; outline: none; transition: all 0.3s; padding: 4px 12px; border-radius: 6px; }
.user-profile:hover { background: rgba(33, 150, 243, 0.1); box-shadow: 0 2px 4px rgba(33, 150, 243, 0.1); }
.user-name-label { font-size: 13px; color: #1976D2; font-weight: 500; }
.arrow-down { color: #64B5F6; }

.main-container { flex: 1; display: flex; overflow: hidden; position: relative; }
.content-area { flex: 1; display: flex; overflow: hidden; position: relative; width: 100%;}

.drawer-content { display: flex; flex-direction: column; height: 100%; padding: 10px; }
.upload-box { margin-bottom: 15px; }
.upload-btn { width: 100%; }
.search-box { margin-bottom: 12px; }
.file-list { flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 10px; padding: 0 4px 4px; scrollbar-width: thin; scrollbar-color: rgba(33, 150, 243, 0.3) transparent; }

.file-list::-webkit-scrollbar {
  width: 6px;
}

.file-list::-webkit-scrollbar-track {
  background: transparent;
}

.file-list::-webkit-scrollbar-thumb {
  background: rgba(33, 150, 243, 0.3);
  border-radius: 3px;
}

.file-list::-webkit-scrollbar-thumb:hover {
  background: rgba(33, 150, 243, 0.5);
}
.file-list-item { 
  background: rgba(255, 255, 255, 0.95); border-radius: 8px; padding: 12px; cursor: pointer; display: flex; align-items: flex-start; gap: 12px; border: 1px solid rgba(33, 150, 243, 0.15); transition: all 0.3s;
}
.file-list-item:hover { 
  background: rgba(255, 255, 255, 1); border-color: rgba(33, 150, 243, 0.3); box-shadow: 0 4px 12px rgba(33, 150, 243, 0.1); transform: translateX(2px);
}
.file-list-item.active { 
  background: rgba(33, 150, 243, 0.08); border-color: #2196F3; box-shadow: 0 4px 12px rgba(33, 150, 243, 0.15);
}
.file-list-item.pending-other {
  opacity: 0.55;
  cursor: not-allowed;
}
.file-list-item.pending-other:hover {
  transform: none;
  box-shadow: none;
}
.file-type-tag { font-size: 11px; padding: 3px 8px; border-radius: 4px; background: rgba(33, 150, 243, 0.1); color: #2196F3; font-weight: 600; }
.file-name { font-size: 14px; font-weight: 600; color: #1565C0; word-break: break-word; white-space: normal; line-height: 1.4; }
.file-meta { font-size: 12px; color: #64B5F6; margin-top: 4px;}

.pdf-container {
  flex-shrink: 0;
  height: 100%;
  overflow: hidden;
  background: transparent;
  display: flex;
  flex-direction: column;
}
.parsing-hint-row {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  padding: 6px 10px;
  background: #e8f4fc;
  border-bottom: 1px solid #b3d9f2;
  font-size: 13px;
  color: #1565c0;
}
.parsing-hint-icon {
  flex-shrink: 0;
}
.parsing-hint-text {
  flex: 1;
  min-width: 0;
  line-height: 1.4;
}
.parsing-hint-progress {
  flex: 1 1 160px;
  min-width: 120px;
  max-width: 320px;
}
.pdf-viewer-wrap {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.pdf-placeholder { flex: 1; display: flex; align-items: center; justify-content: center; background: transparent; height: 100%; }
.placeholder-content { text-align: center; display: flex; flex-direction: column; align-items: center; gap: 20px; }
.placeholder-text { font-size: 16px; color: #666; margin: 0; }
.parse-wait { max-width: 480px; padding: 0 16px; }
.parse-title { font-size: 15px; color: #1565C0; margin: 0; line-height: 1.5; }
.parse-hint { font-size: 13px; color: #78909c; margin: 0; }
.parse-progress-bar { width: min(420px, 90vw); }
.parse-error { font-size: 13px; color: #c62828; margin: 0; max-width: 420px; line-height: 1.5; }

.resizer { width: 8px; background: transparent; cursor: col-resize; position: relative; flex-shrink: 0; z-index: 5;}
.resizer:hover { background: rgba(33, 150, 243, 0.15); }
.resizer-handle { width: 4px; height: 40px; background: #64B5F6; position: absolute; top: 50%; left: 2px; transform: translateY(-50%); border-radius: 4px;}

.right-panel { 
  height: 100%; background: #FFFFFF; backdrop-filter: blur(12px); border-left: 1px solid rgba(33, 150, 243, 0.15); box-shadow: -4px 0 16px rgba(33, 150, 243, 0.08); display: flex; flex-direction: column; flex-shrink: 0; overflow: hidden; transition: width 0.3s;
}
.dialog-drag-handle {
  background: #FFFFFF; padding: 12px 16px; display: flex; align-items: center; justify-content: space-between; gap: 8px; user-select: none; flex-shrink: 0; margin-bottom: 0; border-bottom: 1px solid rgba(33, 150, 243, 0.15);
}
.dialog-title { color: #2196F3; font-size: 14px; font-weight: 600; flex: 1; }
.rhythm-panel-container { 
  flex: 1;
  overflow-y: auto; 
  border-bottom: none;
  display: flex;
  flex-direction: column;
}
.slide-down-enter-active, .slide-down-leave-active { transition: all 0.3s ease; max-height: 400px; }
.slide-down-enter-from, .slide-down-leave-to { max-height: 0; opacity: 0; overflow: hidden; }

.avatar-floating-ball {
  position: fixed; width: 60px; height: 60px; border-radius: 50%; background: linear-gradient(135deg, #2196F3 0%, #64B5F6 100%); box-shadow: 0 4px 16px rgba(33, 150, 243, 0.4); z-index: 9999; cursor: grab; display: flex; align-items: center; justify-content: center; transition: transform 0.2s, box-shadow 0.2s; touch-action: none;
}
.avatar-floating-ball:active { cursor: grabbing; transform: scale(0.95); }
.avatar-floating-ball:hover { box-shadow: 0 6px 20px rgba(33, 150, 243, 0.5); }
.ball-inner { color: #fff; font-size: 26px; display: flex; align-items: center; justify-content: center; user-select: none; pointer-events: none;}
.ball-pulse {
  position: absolute; width: 100%; height: 100%; border-radius: 50%; border: 2px solid rgba(33, 150, 243, 0.8); animation: pulse-ring 1.5s infinite; pointer-events: none;
}
@keyframes pulse-ring {
  0% { transform: scale(1); opacity: 1; }
  100% { transform: scale(1.4); opacity: 0; }
}

.avatar-floating-window {
  position: fixed; width: 380px; height: 550px; background: transparent; border-radius: 12px; z-index: 10000; display: flex; flex-direction: column; box-shadow: none;
}
.avatar-floating-window.audio-only-window {
  width: 280px;
  height: 200px;
}
.avatar-window-header { 
  background: transparent;
  padding: 12px; 
  display: flex; 
  justify-content: space-between; 
  align-items: center; 
  cursor: move; 
  user-select: none; 
  flex-shrink: 0;
  border-radius: 12px 12px 0 0;
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  z-index: 10;
  opacity: 0;
  transition: opacity 0.3s;
}
.avatar-floating-window:hover .avatar-window-header {
  opacity: 1;
}
.avatar-floating-window.audio-only-window .avatar-window-header {
  position: relative;
  opacity: 1;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 10px 15px;
}
.avatar-window-title { color: #fff; font-size: 14px; font-weight: 600; }
.header-actions { display: flex; align-items: center; gap: 10px; }
.close-btn { color: #fff; cursor: pointer; font-size: 18px; transition: color 0.3s; }
.close-btn:hover { color: #f0f0f0; }
.avatar-window-content { flex: 1; background: transparent; border-radius: 12px; overflow: hidden; }
.avatar-floating-window.audio-only-window .avatar-window-content {
  border-radius: 0 0 12px 12px;
}

.history-card { 
  background: rgba(255, 255, 255, 0.95); padding: 15px; border-radius: 8px; border: 1px solid rgba(33, 150, 243, 0.15); box-shadow: 0 2px 4px rgba(33, 150, 243, 0.08);
}
.history-q { font-size: 13px; font-weight: bold; margin-bottom: 8px; color: #1565C0; }
.history-a { font-size: 12px; color: #1976D2; line-height: 1.6; }

@media screen and (max-width: 768px) {
  .hide-on-mobile { display: none !important; }
  .header { padding: 0 10px; }
  .course-title { font-size: 13px; max-width: 150px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .progress-tag { margin-left: 5px !important; }
  .user-dropdown { margin-left: 5px !important; }
  .content-area { flex-direction: column; }
  .avatar-floating-window { width: 90vw !important; height: 60vh !important; max-height: 500px; }
  .avatar-floating-ball { width: 50px; height: 50px; }
  .ball-inner { font-size: 22px; }
  .dialog-drag-handle { padding: 10px 12px; margin-bottom: 0; }
  .right-panel { gap: 0; }
}
</style>