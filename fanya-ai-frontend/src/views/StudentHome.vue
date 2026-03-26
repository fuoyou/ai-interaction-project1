<template>
  <div class="student-layout" :class="{ 'sidebar-collapsed': sidebarCollapsed && !isMobile }">
    <!-- 背景粒子与光影装饰 (适配海洋主题) -->
    <div class="bg-decor">
      <div class="blob b1"></div>
      <div class="blob b2"></div>
      <div class="blob b3"></div>
      <div class="grid-pattern"></div>
    </div>

    <!-- 移动端顶栏 -->
    <header class="mobile-topbar" v-if="isMobile">
      <button class="hamburger" @click="mobileMenuOpen = !mobileMenuOpen" :class="{ active: mobileMenuOpen }">
        <span></span><span></span><span></span>
      </button>
      <h1 class="topbar-logo">问潮知海</h1>
      <el-avatar :size="32" :src="userInfo.avatar || ''" class="topbar-avatar" />
    </header>

    <!-- 移动端遮罩 -->
    <transition name="fade-overlay">
      <div class="overlay" v-if="mobileMenuOpen && isMobile" @click="mobileMenuOpen = false"></div>
    </transition>

    <!-- 侧边栏 -->
    <transition name="slide-sidebar">
      <aside
        class="sidebar"
        :class="{ collapsed: sidebarCollapsed && !isMobile, 'mobile-open': mobileMenuOpen && isMobile }"
        v-show="!isMobile || mobileMenuOpen"
      >
        <!-- 折叠按钮（桌面端） -->
        <button v-if="!isMobile" class="collapse-toggle" @click="sidebarCollapsed = !sidebarCollapsed">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
            <polyline :points="sidebarCollapsed ? '9 18 15 12 9 6' : '15 18 9 12 15 6'" />
          </svg>
        </button>

        <!-- Logo -->
        <div class="sidebar-brand">
          <div class="brand-icon">
            <img src="@/assets/logo.svg" alt="Fanya AI" class="logo-img" />
          </div>
        </div>

        <!-- 用户卡片 -->
        <div class="user-card" @click="openProfileDialog">
          <el-avatar :size="sidebarCollapsed && !isMobile ? 36 : 48" :src="userInfo.avatar || ''" class="user-avatar" />
          <transition name="fade-text">
            <div class="user-meta" v-show="!sidebarCollapsed || isMobile">
              <span class="user-name">{{ userInfo.nickname || userInfo.username || '同学' }}</span>
              <span class="user-badge">🎓 学生</span>
            </div>
          </transition>
        </div>

        <!-- 导航列表 -->
        <nav class="nav-list">
          <div class="nav-section-title" v-show="!sidebarCollapsed || isMobile">学习空间</div>
          <button
            v-for="item in navItems"
            :key="item.key"
            :class="['nav-btn', { active: activeNav === item.key, danger: item.danger }]"
            @click="handleNav(item)"
            :title="sidebarCollapsed ? item.label : ''"
          >
            <span class="nav-icon" v-html="item.icon"></span>
            <transition name="fade-text">
              <span class="nav-label" v-show="!sidebarCollapsed || isMobile">{{ item.label }}</span>
            </transition>
            <span class="nav-indicator" v-if="activeNav === item.key && (!sidebarCollapsed || isMobile)"></span>
          </button>
        </nav>

        <!-- 底部版本 -->
        <div class="sidebar-footer" v-show="!sidebarCollapsed || isMobile">
          <span>v2.0 · AI 智慧学习</span>
        </div>
      </aside>
    </transition>

    <!-- 主区域 -->
    <main class="main-area">
      <!-- 顶部工具栏 -->
      <div class="toolbar">
        <div class="toolbar-left">
          <button v-if="!isMobile" class="toolbar-menu-btn" @click="sidebarCollapsed = !sidebarCollapsed">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="15" y2="12"/><line x1="3" y1="18" x2="18" y2="18"/></svg>
          </button>
          <div class="breadcrumb">
            <span class="bc-icon">{{ activeNav === 'knowledge' ? '📚' : '🌊' }}</span>
            <span class="bc-text">{{ activeNav === 'knowledge' ? '我的知识库' : 'AI智慧课程中心' }}</span>
          </div>
        </div>
        <div class="toolbar-right">
          <div class="search-box" :class="{ expanded: searchFocused }">
            <svg class="search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
            <input
              v-model="searchKeyword"
              :placeholder="activeNav === 'knowledge' ? '搜索课程以管理知识库…' : '搜索课程...'"
              @focus="searchFocused = true"
              @blur="searchFocused = false"
            />
          </div>
          <el-select v-model="termSelect" placeholder="学期" class="term-filter" size="default">
            <el-option label="全部学期" value="all" />
            <el-option label="2026年春夏学期" value="2026年春夏学期" />
            <el-option label="2025年秋冬学期" value="2025年秋冬学期" />
          </el-select>
          <button v-if="activeNav === 'courses'" class="action-btn primary" @click="showCreateCourseDialog = true">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
            <span class="btn-label">新建课程</span>
          </button>
        </div>
      </div>

      <!-- 统计卡片 (统一使用品牌四色) -->
      <div class="stats-row" v-if="activeNav === 'courses'">
        <div class="stat-card" v-for="(s, i) in statsData" :key="i" :style="{ '--delay': i * 0.1 + 's' }">
          <div class="stat-icon" :class="s.colorClass">
            <component :is="s.icon" class="s-icon" />
          </div>
          <div class="stat-info">
            <span class="stat-value">{{ s.value }}</span>
            <span class="stat-label">{{ s.label }}</span>
          </div>
        </div>
      </div>

      <!-- 课程网格 -->
      <div class="content-scroll" v-if="activeNav === 'courses'">
        <div v-if="loadingCourses" class="state-empty">
          <div class="loader"></div>
          <p>海浪正在推卷课程数据...</p>
        </div>

        <div v-else-if="filteredCourses.length === 0" class="state-empty">
          <div class="empty-art">📭</div>
          <p>海面平静，暂无课程，点击上方按钮新建</p>
        </div>

        <div v-else class="course-grid">
          <div
            v-for="(course, idx) in filteredCourses"
            :key="course.id"
            class="course-card"
            :style="{ '--idx': idx }"
            @click="openCourseDrawer(course)"
          >
            <!-- 卡片顶部视觉区 (海洋流体风格) -->
            <div class="card-cover" :class="'theme-' + (idx % 4)">
              <div class="fluid-shape f1"></div>
              <div class="fluid-shape f2"></div>
              
              <img v-if="course.coverUrl" :src="course.coverUrl" class="cover-img" :alt="course.name" />
              <div v-else class="cover-letter">{{ (course.name || '课')[0] }}</div>
              <div class="cover-badge">{{ course.term || '2026年春夏' }}</div>
            </div>

            <!-- 卡片内容 -->
            <div class="card-body">
              <h3 class="card-title">{{ course.name }}</h3>
              <div class="card-meta">
                <span class="meta-teacher">{{ course.source === 'personal' ? '📁 本地' : '👨‍🏫 ' + course.teacher }}</span>
                <span class="meta-tag">AI智课</span>
              </div>
              <div class="card-footer">
                <span class="cw-count">{{ course.coursewares?.length || 0 }} 份课件</span>
                <span class="card-arrow">→</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 我的知识库（独立页：左侧选课程，右侧管理资料） -->
      <div class="content-scroll kb-page-wrap" v-else-if="activeNav === 'knowledge'">
        <div v-if="loadingCourses" class="state-empty">
          <div class="loader"></div>
          <p>加载课程列表...</p>
        </div>
        <template v-else>
          <p class="kb-page-lead">同一门课程（同一课程分类）下，<strong>教师端与学生端共用一套补充资料</strong>：任一方上传的资料，另一方在选中该课程后都能看到；在「互动答疑」中开启「启用课程知识库」后，AI 会检索本分类下全部资料并支持溯源。</p>
          <div v-if="filteredCourses.length === 0" class="state-empty kb-page-empty">
            <div class="empty-art">📭</div>
            <p>暂无课程，请先在「我的课程库」中新建课程</p>
          </div>
          <div v-else class="kb-page-layout">
            <aside class="kb-page-courses">
              <div class="kb-page-aside-title">选择课程</div>
              <button
                v-for="c in filteredCourses"
                :key="c.id"
                type="button"
                :class="['kb-page-course-btn', { active: kbTargetCourse?.id === c.id }]"
                @click="selectKbCourse(c)"
              >
                <span class="kb-page-course-name">{{ c.name }}</span>
                <span class="kb-page-course-meta">{{ c.coursewares?.length || 0 }} 份课件</span>
              </button>
            </aside>
            <section class="kb-page-panel kb-page-panel--glass" v-if="kbTargetCourse">
              <div class="kb-page-panel-head">
                <div class="kb-page-panel-title-wrap">
                  <h2 class="kb-page-panel-title">{{ kbTargetCourse.name }}</h2>
                  <p class="kb-page-panel-sub">共 {{ kbDocs.length }} 份资料 · 点击标题可预览原文</p>
                </div>
                <el-button type="primary" size="small" class="upload-trigger" @click="openKbUploadDialog">
                  <el-icon><Upload /></el-icon> 添加资料
                </el-button>
              </div>
              <div class="kb-list kb-page-doc-list" v-loading="kbLoading">
                <div v-if="!kbDocs.length" class="cw-empty kb-empty">暂无补充资料，可上传 PDF / Word / TXT</div>
                <div
                  v-for="doc in kbDocs"
                  :key="doc.id"
                  class="kb-item"
                  :class="{ 'kb-item--processing': kbDocStatus(doc) === 'processing' }"
                >
                  <div class="kb-icon-wrap" aria-hidden="true">
                    <span class="kb-icon">{{ doc.fileType === 'pdf' ? '📕' : doc.fileType === 'txt' ? '📝' : '📘' }}</span>
                  </div>
                  <div class="kb-info">
                    <button type="button" class="kb-name-btn" @click="openKbDoc(doc)">
                      <span class="kb-name">{{ doc.name }}</span>
                      <span class="kb-open-hint">预览</span>
                    </button>
                    <div class="kb-meta">
                      {{ doc.fileType?.toUpperCase() || '—' }} · {{ kbStatusLabel(doc) }} · {{ doc.createTime }}
                    </div>
                    <div v-if="kbDocStatus(doc) === 'processing'" class="kb-progress-block">
                      <el-progress :indeterminate="true" :duration="2.5" :stroke-width="5" :show-text="false" />
                      <span class="kb-progress-text">正在解析与建索引，请稍候…</span>
                    </div>
                  </div>
                  <el-button
                    v-if="doc.canDelete"
                    type="danger"
                    link
                    size="small"
                    class="kb-del"
                    @click.stop="removeKbDoc(doc)"
                  >删除</el-button>
                </div>
              </div>
            </section>
            <section class="kb-page-panel kb-page-panel--empty" v-else>
              <p>请从左侧选择一门课程</p>
            </section>
          </div>
        </template>
      </div>
    </main>

    <!-- 课程详情抽屉 -->
    <el-drawer v-model="drawerVisible" :title="activeCourse?.name" :size="drawerSize" class="course-drawer" direction="rtl" destroy-on-close>
      <div class="drawer-body" v-if="activeCourse">
        <div class="drawer-info-bar">
          <div class="info-chip" v-for="info in courseInfoChips" :key="info.label">
            <span class="chip-label">{{ info.label }}</span>
            <span class="chip-value">{{ info.value }}</span>
          </div>
        </div>

        <div class="drawer-section-header">
          <span>📎 课件列表 ({{ activeCourse.coursewares?.length || 0 }})</span>
          <el-button type="primary" size="small" class="upload-trigger" @click="openUploadDialog">
             <el-icon><Upload /></el-icon> 上传课件
          </el-button>
        </div>

        <div class="cw-list">
          <div v-if="!activeCourse.coursewares?.length" class="cw-empty">海面空空如也，点击上方按钮上传课件</div>
          <div v-for="cw in activeCourse.coursewares" :key="cw.id" class="cw-item" @click="enterCourse(cw)">
            <div class="cw-icon brand-primary-text">📄</div>
            <div class="cw-info">
              <div class="cw-name">{{ cw.courseName || cw.name || '未命名课件' }}</div>
              <div class="cw-hint">点击开始学习</div>
            </div>
            <button class="cw-go">进入学习 →</button>
          </div>
        </div>
      </div>
    </el-drawer>

    <!-- 新建课程对话框 -->
    <el-dialog v-model="showCreateCourseDialog" title="✨ 新建课程" width="500px" custom-class="fancy-dialog" destroy-on-close>
      <el-form :model="courseForm" label-position="top" size="large">
        <el-form-item label="课程名称">
          <el-input v-model="courseForm.name" placeholder="例如：高等数学 A" />
        </el-form-item>
        <el-form-item label="所属学期">
          <el-select v-model="courseForm.term" style="width:100%">
            <el-option label="2026年春夏学期" value="2026年春夏学期" />
            <el-option label="2025年秋冬学期" value="2025年秋冬学期" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="dlg-footer">
          <el-button size="large" @click="showCreateCourseDialog = false" round>取消</el-button>
          <el-button size="large" type="primary" :loading="creating" @click="submitCreateCourse" round class="brand-btn">确认创建</el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 知识库资料上传 -->
    <el-dialog v-model="showKbUploadDialog" title="📚 上传知识库资料" width="500px" custom-class="fancy-dialog" destroy-on-close>
      <el-form label-position="top" size="large">
        <el-form-item label="资料名称">
          <el-input v-model="kbForm.name" placeholder="例如：课程补充阅读" />
        </el-form-item>
        <el-form-item label="简介（可选）">
          <el-input v-model="kbForm.description" type="textarea" rows="2" placeholder="简要说明用途" />
        </el-form-item>
      </el-form>
      <el-upload class="fancy-uploader" drag :auto-upload="false" :limit="1" :on-change="handleKbFileSelect" accept=".pdf,.doc,.docx,.txt">
        <el-icon class="el-icon--upload brand-primary-text"><Upload /></el-icon>
        <div class="el-upload__text">拖拽文件到此处，或 <em class="brand-primary-text">点击选择</em></div>
        <template #tip><div class="el-upload__tip">支持 PDF、Word、TXT；解析与索引使用与智课一致的 Paddle/文本管线</div></template>
      </el-upload>
      <template #footer>
        <div class="dlg-footer">
          <el-button size="large" @click="showKbUploadDialog = false" round>取消</el-button>
          <el-button size="large" type="primary" :loading="kbUploading" @click="submitKbUpload" round class="brand-btn">上传并索引</el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 上传课件对话框 -->
    <el-dialog v-model="showUploadDialog" title="📤 上传课件" width="500px" custom-class="fancy-dialog" destroy-on-close>
      <el-upload class="fancy-uploader" drag :auto-upload="false" :limit="1" :on-change="handleFileSelect" accept=".pdf,.pptx,.ppt,.doc,.docx">
        <el-icon class="el-icon--upload brand-primary-text"><Upload /></el-icon>
        <div class="el-upload__text">拖拽文件到此处，或 <em class="brand-primary-text">点击选择</em></div>
        <template #tip><div class="el-upload__tip">支持 PDF / PPT / Word</div></template>
      </el-upload>
      <template #footer>
        <div class="dlg-footer">
          <el-button size="large" @click="showUploadDialog = false" round>取消</el-button>
          <el-button size="large" type="primary" :loading="uploading" @click="submitUpload" round class="brand-btn">确认上传</el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 个人资料对话框 -->
    <el-dialog v-model="showProfileDialog" title="👤 账户信息" width="500px" custom-class="fancy-dialog" destroy-on-close>
      <div class="profile-top">
        <el-avatar :size="72" :src="profileForm.avatar || ''" class="brand-avatar" />
        <p class="profile-hint">当前学生身份不可修改账号</p>
      </div>
      <el-form :model="profileForm" label-position="top" size="large">
        <el-form-item label="用户名">
          <el-input v-model="profileForm.username" disabled />
        </el-form-item>
        <el-form-item label="昵称">
          <el-input v-model="profileForm.nickname" placeholder="请输入昵称" />
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="dlg-footer">
          <el-button size="large" @click="showProfileDialog = false" round>取消</el-button>
          <el-button size="large" type="primary" :loading="saveLoading" @click="saveProfile" round class="brand-btn">同步信息</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, markRaw, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Upload, Collection, Document, Avatar, Files } from '@element-plus/icons-vue' // 引入图标用于统计卡片
import { updateUserProfile } from '@/api/user'
import {
  listAllCategories,
  listMyCourses,
  listTeacherCourses,
  createCategory,
  uploadCourseToCategory,
  listKnowledgeDocs,
  uploadKnowledgeDoc,
  deleteKnowledgeDoc,
  fetchKnowledgeDocFile
} from '@/api/lesson'

const router = useRouter()

/* ---- 响应式状态 ---- */
const isMobile = ref(false)
const mobileMenuOpen = ref(false)
const sidebarCollapsed = ref(false)
const searchFocused = ref(false)
const activeNav = ref('courses')

const courses = ref([])
const loadingCourses = ref(false)
const searchKeyword = ref('')
const filterType = ref('')
const termSelect = ref('all')
const userInfo = ref({ nickname: '', avatar: '', username: '' })

const drawerVisible = ref(false)
const activeCourse = ref(null)

const showCreateCourseDialog = ref(false)
const creating = ref(false)
const courseForm = reactive({ name: '', term: '2026年春夏学期' })

const showUploadDialog = ref(false)
const uploading = ref(false)
const uploadFile = ref(null)

const kbTargetCourse = ref(null)
const kbDocs = ref([])
const kbLoading = ref(false)
const showKbUploadDialog = ref(false)
const kbUploading = ref(false)
const kbUploadFile = ref(null)
const kbForm = reactive({ name: '', description: '' })

/** @type {ReturnType<typeof setInterval> | null} */
let kbPollTimer = null

const showProfileDialog = ref(false)
const saveLoading = ref(false)
const profileForm = reactive({ username: '', nickname: '', avatar: '' })

/* ---- 导航项 ---- */
const navItems = [
  { key: 'courses', label: '我的课程库', icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>' },
  { key: 'knowledge', label: '我的知识库', icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="9" y1="15" x2="15" y2="15"/><line x1="12" y1="12" x2="12" y2="18"/></svg>' },
  { key: 'interactive', label: '互动课堂', icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="23 7 16 12 23 17 23 7"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>' },
  { key: 'profile', label: '账户信息', icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>' },
  { key: 'logout', label: '安全退出', icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>', danger: true },
]

/* ---- 统计数据 (映射到4种品牌色) ---- */
const statsData = computed(() => [
  { icon: markRaw(Collection), value: courses.value.length, label: '全部课程', colorClass: 'bg-primary' },
  { icon: markRaw(Document), value: courses.value.reduce((s, c) => s + (c.coursewares?.length || 0), 0), label: '课件总数', colorClass: 'bg-lavender' },
  { icon: markRaw(Avatar), value: courses.value.filter(c => c.source === 'teacher').length, label: '教师课程', colorClass: 'bg-deep' },
  { icon: markRaw(Files), value: courses.value.filter(c => c.source === 'personal').length, label: '个人课程', colorClass: 'bg-light' },
])

/* ---- 课程详情chips ---- */
const courseInfoChips = computed(() => {
  if (!activeCourse.value) return []
  return [
    { label: activeCourse.value.source === 'personal' ? '来源' : '教师', value: activeCourse.value.source === 'personal' ? '本地上传' : activeCourse.value.teacher },
    { label: '学期', value: activeCourse.value.term || '2026年春夏学期' },
    { label: '课件', value: (activeCourse.value.coursewares?.length || 0) + ' 份' },
  ]
})

/* ---- 计算属性 ---- */
const drawerSize = computed(() => {
  if (typeof window === 'undefined') return '600px'
  const w = window.innerWidth
  if (w <= 480) return '100%'
  if (w <= 768) return '92%'
  if (w <= 1024) return '70%'
  return '560px'
})

const filteredCourses = computed(() => {
  let r = courses.value
  if (termSelect.value && termSelect.value !== 'all') r = r.filter(c => c.term === termSelect.value)
  if (searchKeyword.value) { const k = searchKeyword.value.toLowerCase(); r = r.filter(c => (c.name || '').toLowerCase().includes(k)) }
  if (filterType.value === 'teacher') r = r.filter(c => c.source === 'teacher')
  else if (filterType.value === 'personal') r = r.filter(c => c.source === 'personal')
  return r
})

/* ---- 导航处理 ---- */
const handleNav = (item) => {
  mobileMenuOpen.value = false
  if (item.key === 'courses') {
    activeNav.value = 'courses'
  } else if (item.key === 'knowledge') {
    activeNav.value = 'knowledge'
    const list = filteredCourses.value
    if (list.length && (!kbTargetCourse.value || !list.some((c) => c.id === kbTargetCourse.value.id))) {
      kbTargetCourse.value = list[0]
    }
    if (kbTargetCourse.value?.id) loadKbDocs()
  } else if (item.key === 'interactive') {
    activeNav.value = 'interactive'
    goToInteractiveClassroom()
  } else if (item.key === 'profile') {
    openProfileDialog()
  } else if (item.key === 'logout') {
    logout()
  }
}

const selectKbCourse = (course) => {
  kbTargetCourse.value = course
  loadKbDocs()
}

/* ---- 业务逻辑（全部保留原始功能） ---- */
const openProfileDialog = () => {
  profileForm.username = userInfo.value.username
  profileForm.nickname = userInfo.value.nickname
  profileForm.avatar = userInfo.value.avatar
  showProfileDialog.value = true
}
const openCourseDrawer = (course) => { activeCourse.value = course; drawerVisible.value = true }

const submitCreateCourse = async () => {
  if (!courseForm.name.trim()) return ElMessage.warning('请输入课程名称')
  creating.value = true
  try {
    const userName = userInfo.value.nickname || userInfo.value.username || '学生'
    const descJson = JSON.stringify({ teacher: userName, term: courseForm.term, source: 'student' })
    await createCategory(courseForm.name, descJson)
    ElMessage.success('课程创建成功')
    showCreateCourseDialog.value = false
    courseForm.name = ''
    await loadCourses()
  } catch (e) { ElMessage.error('创建失败') } finally { creating.value = false }
}

const openUploadDialog = () => { if (!activeCourse.value) return; uploadFile.value = null; showUploadDialog.value = true }
const handleFileSelect = (file) => { uploadFile.value = file.raw }

const submitUpload = async () => {
  if (!uploadFile.value) return ElMessage.warning('请选择要上传的文件')
  if (!activeCourse.value) return
  uploading.value = true
  try {
    const res = await uploadCourseToCategory(uploadFile.value, activeCourse.value.id)
    console.log('上传响应:', res)
    ElMessage.success('课件上传成功，AI 正在后台进行深度解析')
    showUploadDialog.value = false
    await loadCourses()
    if (activeCourse.value) {
      const updated = courses.value.find(c => c.id === activeCourse.value.id)
      if (updated) activeCourse.value = { ...updated }
    }
  } catch (error) { console.error('上传失败:', error); ElMessage.error('上传失败') } finally { uploading.value = false }
}

const saveProfile = async () => {
  saveLoading.value = true
  try {
    await updateUserProfile(profileForm)
    Object.assign(userInfo.value, profileForm)
    localStorage.setItem('userInfo', JSON.stringify(userInfo.value))
    ElMessage.success('账户信息已更新')
    showProfileDialog.value = false
  } catch (e) { ElMessage.error('同步失败') } finally { saveLoading.value = false }
}

const loadCourses = async () => {
  loadingCourses.value = true
  try {
    const catRes = await listAllCategories()
    const categories = catRes.data || []
    const [myCoursesRes, teacherCoursesRes] = await Promise.all([listMyCourses(), listTeacherCourses()])
    const myCoursewares = Array.isArray(myCoursesRes.data) ? myCoursesRes.data : (myCoursesRes.data || [])
    const teacherCoursewares = Array.isArray(teacherCoursesRes.data) ? teacherCoursesRes.data : (teacherCoursesRes.data || [])
    const allCoursewares = [...myCoursewares, ...teacherCoursewares]
    const courseList = []
    for (const cat of categories) {
      const coursewares = allCoursewares.filter(cw => {
        const cwCourseId = cw.courseId || cw.category_id || cw.categoryId || cw.course_id
        return cwCourseId === cat.id || cwCourseId === String(cat.id)
      })
      let teacher = '未知教师', term = '2026年春夏学期', source = 'teacher'
      const teacherCourseware = coursewares.find(cw => cw.teacherName)
      if (teacherCourseware?.teacherName) teacher = teacherCourseware.teacherName
      try {
        if (cat.description?.startsWith('{')) {
          const d = JSON.parse(cat.description)
          if (teacher === '未知教师') teacher = d.teacher || teacher
          term = d.term || term
          if (d.source === 'student') source = 'personal'
        }
      } catch (e) {}
      if (source === 'teacher') {
        source = coursewares.some(cw => cw.teacherName || cw.isShared) ? 'teacher' : 'personal'
      }
      courseList.push({ id: cat.id, name: cat.name, teacher, term, source, coursewares })
    }
    courses.value = courseList
    if (drawerVisible.value && activeCourse.value) {
      const u = courses.value.find(c => c.id === activeCourse.value.id)
      if (u) activeCourse.value = { ...u }
    }
    if (activeNav.value === 'knowledge') {
      await nextTick()
      const list = filteredCourses.value
      if (list.length) {
        const cur = kbTargetCourse.value
        const still = cur && list.some((c) => c.id === cur.id)
        if (!still) kbTargetCourse.value = list[0]
        loadKbDocs()
      } else {
        kbTargetCourse.value = null
        kbDocs.value = []
      }
    }
  } catch (error) { console.error('加载课程失败:', error); ElMessage.error('加载课程数据失败') } finally { loadingCourses.value = false }
}

const kbDocStatus = (doc) => {
  if (doc.indexStatus) return doc.indexStatus
  if (doc.hasRag) return 'ready'
  return 'empty'
}

const kbStatusLabel = (doc) => {
  const s = kbDocStatus(doc)
  if (s === 'processing') return '解析与建索引中'
  if (s === 'ready') return '已索引'
  if (s === 'failed') return '索引失败'
  return '未建立索引'
}

const clearKbPoll = () => {
  if (kbPollTimer != null) {
    clearInterval(kbPollTimer)
    kbPollTimer = null
  }
}

const loadKbDocs = async (silent = false) => {
  const cid = kbTargetCourse.value?.id
  if (!cid) {
    kbDocs.value = []
    return
  }
  if (!silent) kbLoading.value = true
  try {
    const res = await listKnowledgeDocs(cid)
    kbDocs.value = Array.isArray(res.data) ? res.data : []
  } catch (e) {
    kbDocs.value = []
  } finally {
    if (!silent) kbLoading.value = false
  }
}

const openKbUploadDialog = () => {
  if (!kbTargetCourse.value) {
    ElMessage.warning('请先在左侧选择一门课程')
    return
  }
  kbForm.name = ''
  kbForm.description = ''
  kbUploadFile.value = null
  showKbUploadDialog.value = true
}

const handleKbFileSelect = (file) => {
  kbUploadFile.value = file.raw
  if (!kbForm.name.trim() && file.name) {
    kbForm.name = file.name.replace(/\.[^.]+$/, '')
  }
}

const submitKbUpload = async () => {
  if (!kbUploadFile.value) return ElMessage.warning('请选择文件')
  if (!kbForm.name.trim()) return ElMessage.warning('请填写资料名称')
  if (!kbTargetCourse.value?.id) return
  kbUploading.value = true
  try {
    await uploadKnowledgeDoc(kbUploadFile.value, kbTargetCourse.value.id, kbForm.name.trim(), kbForm.description.trim())
    ElMessage.success('资料已添加，解析进度见右侧列表')
    showKbUploadDialog.value = false
    kbUploadFile.value = null
    await loadKbDocs()
  } catch (e) {
    ElMessage.error('上传失败')
  } finally {
    kbUploading.value = false
  }
}

const openKbDoc = async (doc) => {
  try {
    const res = await fetchKnowledgeDocFile(doc.id)
    const blob = res.data
    if (blob instanceof Blob && blob.type && blob.type.includes('application/json')) {
      const text = await blob.text()
      try {
        const j = JSON.parse(text)
        ElMessage.error(j.msg || '无法打开文件')
      } catch {
        ElMessage.error('无法打开文件')
      }
      return
    }
    const ext = (doc.fileType || '').toLowerCase()
    if (ext === 'doc' || ext === 'docx') {
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = ext && !String(doc.name).toLowerCase().endsWith(`.${ext}`) ? `${doc.name}.${ext}` : doc.name
      a.rel = 'noopener'
      a.click()
      URL.revokeObjectURL(url)
      return
    }
    const url = URL.createObjectURL(blob)
    window.open(url, '_blank', 'noopener')
    setTimeout(() => URL.revokeObjectURL(url), 120000)
  } catch (e) {
    ElMessage.error('无法打开文件')
  }
}

const removeKbDoc = async (doc) => {
  try {
    await ElMessageBox.confirm(`确定删除「${doc.name}」？`, '删除知识库资料')
    await deleteKnowledgeDoc(doc.id)
    ElMessage.success('已删除')
    await loadKbDocs()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('删除失败')
  }
}

watch(
  () => [activeNav.value, kbTargetCourse.value?.id],
  () => {
    if (activeNav.value === 'knowledge' && kbTargetCourse.value?.id) loadKbDocs()
  }
)

watch(filteredCourses, (list) => {
  if (activeNav.value !== 'knowledge' || loadingCourses.value) return
  if (!list.length) {
    kbTargetCourse.value = null
    kbDocs.value = []
    return
  }
  if (!kbTargetCourse.value || !list.some((c) => c.id === kbTargetCourse.value.id)) {
    kbTargetCourse.value = list[0]
    loadKbDocs()
  }
})

watch(
  () => ({
    processing:
      activeNav.value === 'knowledge' &&
      kbDocs.value.some((d) => kbDocStatus(d) === 'processing'),
    cid: kbTargetCourse.value?.id
  }),
  (v) => {
    clearKbPoll()
    if (!v.processing || !v.cid) return
    kbPollTimer = setInterval(() => {
      loadKbDocs(true)
    }, 2500)
  }
)

const enterCourse = (cw) => router.push(`/student/classroom/${cw.id}`)
const goToInteractiveClassroom = () => router.push('/student/interactive-classroom')
const logout = () => ElMessageBox.confirm('退出系统？').then(() => { localStorage.clear(); router.push('/login') })

/* ---- 响应式检测 ---- */
const checkMobile = () => { isMobile.value = window.innerWidth <= 768 }
onMounted(() => {
  const cached = localStorage.getItem('userInfo')
  if (cached) userInfo.value = JSON.parse(cached)
  checkMobile()
  window.addEventListener('resize', checkMobile)
  loadCourses()
})
onUnmounted(() => {
  window.removeEventListener('resize', checkMobile)
  clearKbPoll()
})
</script>

<style scoped>
/* ================================================================
   品牌色彩与设计系统
   ================================================================ */
.student-layout {
  --brand-deep: #1442D3;
  --brand-primary: #307AE3;
  --brand-lavender: #ACB1EC;
  --brand-light: #D2E6FE;
  
  --c-bg: #F8FAFC;
  --c-surface: #FFFFFF;
  --c-text: #1E293B;
  --c-text2: #64748B;
  --c-border: #E2E8F0;
  
  --grad: linear-gradient(135deg, var(--brand-primary), var(--brand-deep));
  --grad-soft: linear-gradient(135deg, #F8FAFC, #EFF6FF);
  
  --r-sm: 10px;
  --r-md: 14px;
  --r-lg: 20px;
  --r-xl: 24px;
  --sidebar-w: 260px;
  --sidebar-cw: 76px;
  --topbar-h: 56px;

  position: fixed; inset: 0;
  display: flex;
  background: var(--c-bg);
  overflow: hidden;
  font-family: 'PingFang SC', 'Microsoft YaHei', -apple-system, BlinkMacSystemFont, sans-serif;
  color: var(--c-text);
}

/* 工具类提取 */
.brand-primary-text { color: var(--brand-primary) !important; }
.brand-deep-text { color: var(--brand-deep) !important; }

/* ================================================================
   背景海洋光影装饰
   ================================================================ */
.bg-decor { position: absolute; inset: 0; pointer-events: none; z-index: 0; overflow: hidden; }
.blob { position: absolute; border-radius: 50%; filter: blur(120px); opacity: 0.25; mix-blend-mode: multiply; }
.b1 { width: 500px; height: 500px; background: var(--brand-primary); top: -150px; right: -100px; animation: float 18s ease-in-out infinite; }
.b2 { width: 450px; height: 450px; background: var(--brand-light); bottom: -150px; left: -100px; animation: float 22s ease-in-out infinite reverse; opacity: 0.5; }
.b3 { width: 350px; height: 350px; background: var(--brand-lavender); top: 40%; left: 30%; animation: float 15s ease-in-out infinite 2s; opacity: 0.2; }

@keyframes float {
  0%, 100% { transform: translate(0, 0) scale(1); }
  33% { transform: translate(40px, -30px) scale(1.1); }
  66% { transform: translate(-30px, 20px) scale(0.9); }
}
.grid-pattern {
  position: absolute; inset: 0;
  background-image:
    linear-gradient(rgba(48,122,227,0.04) 1px, transparent 1px),
    linear-gradient(90deg, rgba(48,122,227,0.04) 1px, transparent 1px);
  background-size: 40px 40px;
}

/* ================================================================
   移动端顶栏
   ================================================================ */
.mobile-topbar {
  position: fixed; top: 0; left: 0; right: 0; height: var(--topbar-h);
  background: rgba(255,255,255,0.9); backdrop-filter: blur(16px);
  border-bottom: 1px solid var(--c-border);
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 16px; z-index: 200;
}
.hamburger {
  width: 32px; height: 32px; background: none; border: none; cursor: pointer;
  display: flex; flex-direction: column; justify-content: center; gap: 5px; padding: 4px;
}
.hamburger span {
  display: block; height: 2px; background: var(--brand-deep); border-radius: 2px;
  transition: all 0.3s cubic-bezier(0.4,0,0.2,1); transform-origin: center;
}
.hamburger.active span:nth-child(1) { transform: translateY(7px) rotate(45deg); }
.hamburger.active span:nth-child(2) { opacity: 0; transform: scaleX(0); }
.hamburger.active span:nth-child(3) { transform: translateY(-7px) rotate(-45deg); }
.topbar-logo {
  font-size: 18px; font-weight: 800; letter-spacing: 1px;
  background: var(--grad); -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.topbar-avatar { border: 2px solid var(--brand-light); flex-shrink: 0; }

/* 遮罩 */
.overlay { position: fixed; inset: 0; z-index: 299; background: rgba(20,66,211,0.15); backdrop-filter: blur(4px); }
.fade-overlay-enter-active, .fade-overlay-leave-active { transition: opacity 0.3s; }
.fade-overlay-enter-from, .fade-overlay-leave-to { opacity: 0; }

/* ================================================================
   侧边栏
   ================================================================ */
.sidebar {
  width: var(--sidebar-w); height: 100%;
  background: rgba(255,255,255,0.85); backdrop-filter: blur(24px);
  border-right: 1px solid rgba(48,122,227,0.1);
  display: flex; flex-direction: column;
  padding: 32px 16px; z-index: 300; flex-shrink: 0;
  transition: width 0.35s cubic-bezier(0.4,0,0.2,1), padding 0.35s;
  position: relative; overflow: hidden;
}
.sidebar.collapsed { width: var(--sidebar-cw); padding: 32px 10px; }

.collapse-toggle {
  position: absolute; top: 36px; right: -1px;
  width: 24px; height: 48px;
  background: var(--c-surface); border: 1px solid var(--c-border);
  border-right: none; border-radius: 8px 0 0 8px;
  cursor: pointer; display: flex; align-items: center; justify-content: center;
  color: var(--brand-primary); z-index: 5;
  transition: all 0.25s; opacity: 0;
  box-shadow: -2px 0 8px rgba(48,122,227,0.05);
}
.sidebar:hover .collapse-toggle { opacity: 1; }
.collapse-toggle:hover { background: var(--brand-light); color: var(--brand-deep); }
.collapse-toggle svg { width: 14px; height: 14px; }

.sidebar-brand {
  display: flex; align-items: center; gap: 12px; margin-bottom: -20px; padding: 0 4px;
  justify-content: center;
}
.brand-icon {
  width: 200px; height: 200px; flex-shrink: 0;
  background: transparent; border-radius: 12px;
  display: flex; align-items: center; justify-content: center;
  box-shadow: none;
  transition: transform 0.3s;
  overflow: hidden;
}
.brand-icon:hover { transform: scale(1.05); }
.logo-img { width: 100%; height: 100%; object-fit: contain; }
.brand-label {
  font-size: 22px; font-weight: 800; white-space: nowrap; letter-spacing: 1px;
  background: var(--grad); -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}

.user-card {
  display: flex; align-items: center; gap: 12px;
  padding: 12px; border-radius: 16px;
  background: var(--brand-light); cursor: pointer;
  margin-bottom: 24px; transition: all 0.3s;
  overflow: hidden; border: 1px solid transparent;
}
.user-card:hover { 
  transform: translateY(-2px); 
  box-shadow: 0 8px 20px rgba(48,122,227,0.15); 
  border-color: #A9D1FE;
}
.user-avatar { border: 2px solid #FFF; flex-shrink: 0; background: #FFF; }
.user-meta { display: flex; flex-direction: column; min-width: 0; }
.user-name {
  font-size: 15px; font-weight: 700; color: var(--brand-deep);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.user-badge {
  font-size: 11px; font-weight: 700; color: #FFF;
  background: var(--brand-primary); padding: 2px 8px; border-radius: 8px;
  margin-top: 4px; width: fit-content;
}

/* 导航 */
.nav-list { flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 4px; }
.nav-list::-webkit-scrollbar { width: 0; }
.nav-section-title {
  font-size: 12px; font-weight: 700; color: var(--brand-primary); opacity: 0.7;
  padding: 16px 12px 8px; white-space: nowrap; letter-spacing: 1px;
}
.nav-btn {
  display: flex; align-items: center; gap: 12px;
  padding: 14px 16px; border-radius: 16px;
  border: none; background: none; cursor: pointer;
  color: var(--c-text2); font-size: 15px; font-weight: 600;
  position: relative; overflow: hidden;
  transition: all 0.3s cubic-bezier(0.4,0,0.2,1);
  width: 100%; text-align: left;
}
.nav-icon { width: 20px; height: 20px; flex-shrink: 0; display: flex; align-items: center; }
.nav-icon :deep(svg) { width: 20px; height: 20px; }
.nav-label { white-space: nowrap; }
.nav-indicator {
  position: absolute; right: 14px; width: 6px; height: 6px;
  border-radius: 50%; background: var(--brand-primary);
  animation: pulse-dot 2s ease-in-out infinite;
}
@keyframes pulse-dot { 0%, 100% { transform: scale(1); opacity: 1; } 50% { transform: scale(1.5); opacity: 0.5; } }

.nav-btn:hover { background: #F1F5F9; color: var(--brand-primary); transform: translateX(4px); }
.nav-btn.active { background: var(--brand-light); color: var(--brand-deep); box-shadow: 0 4px 12px rgba(48,122,227,0.1); }
.nav-btn.active::before {
  content: ''; position: absolute; left: 0; top: 20%; bottom: 20%;
  width: 4px; background: var(--brand-deep); border-radius: 0 4px 4px 0;
}
.nav-btn.danger:hover { color: #DC2626; background: #FEE2E2; }

.sidebar-footer {
  padding: 16px 12px 0; font-size: 12px; color: var(--brand-lavender);
  border-top: 1px solid var(--c-border); margin-top: auto; font-weight: 600;
}

/* 文字过渡 */
.fade-text-enter-active, .fade-text-leave-active { transition: opacity 0.2s, transform 0.2s; }
.fade-text-enter-from, .fade-text-leave-to { opacity: 0; transform: translateX(-8px); }

/* ================================================================
   主区域
   ================================================================ */
.main-area {
  flex: 1; display: flex; flex-direction: column;
  position: relative; z-index: 1; overflow: hidden;
  padding: 32px 40px;
}

/* 工具栏 */
.toolbar {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 32px; flex-shrink: 0; gap: 16px; flex-wrap: wrap;
}
.toolbar-left { display: flex; align-items: center; gap: 16px; }
.toolbar-menu-btn {
  width: 40px; height: 40px; border: 1px solid var(--c-border); border-radius: 12px;
  background: var(--c-surface); cursor: pointer; display: flex; align-items: center; justify-content: center;
  color: var(--c-text2); transition: all 0.3s;
}
.toolbar-menu-btn:hover { border-color: var(--brand-primary); color: var(--brand-primary); background: var(--brand-light); }
.toolbar-menu-btn svg { width: 20px; height: 20px; }
.breadcrumb { display: flex; align-items: center; gap: 10px; }
.bc-icon { font-size: 22px; }
.bc-text { font-size: 22px; font-weight: 800; color: var(--brand-deep); letter-spacing: 0.5px; }

.toolbar-right { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.search-box {
  display: flex; align-items: center; gap: 8px;
  background: var(--c-surface); border: 1px solid var(--c-border);
  border-radius: 20px; padding: 0 16px; height: 40px;
  width: 220px; transition: all 0.3s cubic-bezier(0.4,0,0.2,1);
}
.search-box.expanded { width: 300px; border-color: var(--brand-primary); box-shadow: 0 0 0 3px rgba(48,122,227,0.15); }
.search-icon { width: 18px; height: 18px; color: var(--brand-primary); flex-shrink: 0; }
.search-box input {
  border: none; outline: none; background: none; flex: 1;
  font-size: 14px; color: var(--c-text); min-width: 0;
}
.search-box input::placeholder { color: #94A3B8; }

.term-filter { width: 140px; }
:deep(.term-filter .el-input__wrapper) {
  border-radius: 20px !important; height: 40px !important;
  box-shadow: none !important; border: 1px solid var(--c-border) !important;
  transition: all 0.3s;
}
:deep(.term-filter .el-input__wrapper.is-focus) {
  border-color: var(--brand-primary) !important; box-shadow: 0 0 0 3px rgba(48,122,227,0.1) !important;
}

.action-btn {
  display: flex; align-items: center; gap: 8px;
  height: 40px; padding: 0 20px; border: none; border-radius: 20px;
  font-size: 14px; font-weight: 600; cursor: pointer;
  transition: all 0.3s;
}
.action-btn.primary {
  background: var(--grad); color: #fff;
  box-shadow: 0 6px 16px rgba(20,66,211,0.25);
}
.action-btn.primary:hover { transform: translateY(-2px); box-shadow: 0 8px 24px rgba(20,66,211,0.35); }
.action-btn svg { width: 18px; height: 18px; }

/* ================================================================
   统计卡片 (映射品牌色)
   ================================================================ */
.stats-row {
  display: grid; grid-template-columns: repeat(4, 1fr);
  gap: 20px; margin-bottom: 32px; flex-shrink: 0;
}
.stat-card {
  background: var(--c-surface); border-radius: var(--r-xl);
  padding: 20px 24px; display: flex; align-items: center; gap: 16px;
  border: 1px solid var(--c-border);
  box-shadow: 0 4px 12px rgba(0,0,0,0.02);
  transition: all 0.3s cubic-bezier(0.4,0,0.2,1);
  animation: card-in 0.5s ease-out both;
  animation-delay: var(--delay); cursor: default;
}
@keyframes card-in { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
.stat-card:hover { transform: translateY(-6px); box-shadow: 0 12px 32px rgba(20,66,211,0.1); border-color: var(--brand-light); }
.stat-icon {
  width: 48px; height: 48px; border-radius: 14px;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.s-icon { width: 24px; height: 24px; }

/* 颜色映射 */
.bg-primary { background: var(--brand-primary); color: #FFF; }
.bg-lavender { background: var(--brand-lavender); color: var(--brand-deep); }
.bg-deep { background: var(--brand-deep); color: #FFF; }
.bg-light { background: var(--brand-light); color: var(--brand-primary); }

.stat-info { display: flex; flex-direction: column; }
.stat-value { font-size: 26px; font-weight: 800; color: var(--c-text); line-height: 1.2; }
.stat-label { font-size: 13px; color: var(--c-text2); margin-top: 4px; font-weight: 500; }

/* ================================================================
   滚动区
   ================================================================ */
.content-scroll { flex: 1; overflow-y: auto; overflow-x: hidden; padding: 4px 4px 40px 0; }
.content-scroll::-webkit-scrollbar { width: 6px; }
.content-scroll::-webkit-scrollbar-thumb { background: var(--brand-lavender); border-radius: 10px; }
.content-scroll::-webkit-scrollbar-thumb:hover { background: var(--brand-primary); }

.state-empty {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  padding: 100px 20px; color: var(--brand-primary);
}
.loader {
  width: 36px; height: 36px; border: 4px solid var(--brand-light);
  border-top-color: var(--brand-deep); border-radius: 50%;
  animation: spin 0.8s linear infinite; margin-bottom: 16px;
}
@keyframes spin { to { transform: rotate(360deg); } }
.empty-art { font-size: 56px; margin-bottom: 16px; opacity: 0.8; }

/* ================================================================
   课程卡片 (流体海洋设计)
   ================================================================ */
.course-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 24px;
}
.course-card {
  background: var(--c-surface); border-radius: 24px;
  overflow: hidden; cursor: pointer;
  border: 1px solid var(--c-border);
  box-shadow: 0 4px 16px rgba(0,0,0,0.02);
  transition: all 0.4s cubic-bezier(0.2, 0.8, 0.2, 1);
  animation: card-in 0.5s ease-out both;
  animation-delay: calc(var(--idx) * 0.08s);
}
.course-card:hover {
  transform: translateY(-8px);
  box-shadow: 0 24px 48px rgba(20,66,211,0.12);
  border-color: var(--brand-light);
}

.card-cover {
  height: 160px; position: relative; overflow: hidden;
  display: flex; align-items: center; justify-content: center;
}
/* 严格使用 4 种品牌色进行流体搭配 */
.theme-0 { background: var(--brand-light); }
.theme-0 .f1 { background: var(--brand-primary); opacity: 0.1; }
.theme-0 .f2 { background: var(--brand-deep); opacity: 0.05; }
.theme-0 .cover-letter { color: var(--brand-primary); }

.theme-1 { background: var(--brand-lavender); }
.theme-1 .f1 { background: var(--brand-deep); opacity: 0.15; }
.theme-1 .f2 { background: #FFF; opacity: 0.2; }
.theme-1 .cover-letter { color: var(--brand-deep); }

.theme-2 { background: var(--brand-primary); }
.theme-2 .f1 { background: var(--brand-light); opacity: 0.2; }
.theme-2 .f2 { background: var(--brand-deep); opacity: 0.3; }
.theme-2 .cover-letter { color: #FFF; }

.theme-3 { background: var(--brand-deep); }
.theme-3 .f1 { background: var(--brand-primary); opacity: 0.4; }
.theme-3 .f2 { background: var(--brand-lavender); opacity: 0.2; }
.theme-3 .cover-letter { color: var(--brand-light); }

/* 流体形状 */
.fluid-shape {
  position: absolute;
  width: 200%; height: 200%;
  border-radius: 40% 60% 70% 30% / 40% 50% 60% 50%;
  animation: waveMotion 12s linear infinite;
}
.f1 { top: -50%; left: -50%; animation-duration: 15s; }
.f2 { bottom: -80%; right: -50%; animation-duration: 10s; animation-direction: reverse; }

@keyframes waveMotion { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }

.cover-img { width: 100%; height: 100%; object-fit: cover; position: relative; z-index: 1; transition: transform 0.6s; }
.course-card:hover .cover-img { transform: scale(1.08); }

.cover-letter {
  font-size: 56px; font-weight: 900;
  position: relative; z-index: 1;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  text-shadow: 0 4px 12px rgba(0,0,0,0.1);
}
.course-card:hover .cover-letter { transform: scale(1.15); text-shadow: 0 8px 24px rgba(0,0,0,0.15); }

.cover-badge {
  position: absolute; bottom: 0; left: 0; z-index: 2;
  background: rgba(255,255,255,0.9); backdrop-filter: blur(8px);
  color: var(--brand-deep); font-size: 11px; font-weight: 700;
  padding: 6px 16px; border-top-right-radius: 16px;
  box-shadow: 2px -2px 10px rgba(0,0,0,0.05);
}

.card-body { padding: 20px 24px 24px; }
.card-title {
  font-size: 18px; font-weight: 800; color: var(--c-text);
  margin-bottom: 12px; line-height: 1.4;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
  transition: color 0.3s;
}
.course-card:hover .card-title { color: var(--brand-primary); }

.card-meta { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.meta-teacher { font-size: 13px; color: var(--c-text2); font-weight: 500; }
.meta-tag {
  font-size: 11px; font-weight: 700; letter-spacing: 0.5px;
  color: var(--brand-primary); background: var(--brand-light);
  padding: 4px 10px; border-radius: 8px;
}

.card-footer {
  display: flex; justify-content: space-between; align-items: center;
  padding-top: 14px; border-top: 1px dashed var(--c-border);
}
.cw-count { font-size: 13px; color: var(--brand-lavender); font-weight: 600; }
.card-arrow {
  font-size: 18px; color: var(--brand-primary); font-weight: 800;
  transition: transform 0.3s;
}
.course-card:hover .card-arrow { transform: translateX(6px); color: var(--brand-deep); }

/* ================================================================
   抽屉
   ================================================================ */
.course-drawer :deep(.el-drawer__header) {
  font-size: 20px; font-weight: 800; color: var(--brand-deep);
  padding: 24px 28px; margin-bottom: 0;
  border-bottom: 1px solid var(--brand-light);
}
.drawer-body { padding: 24px 28px; }

.drawer-info-bar { display: flex; flex-wrap: wrap; gap: 12px; margin-bottom: 28px; }
.info-chip {
  background: var(--brand-light); border-radius: 12px;
  padding: 12px 18px; display: flex; gap: 8px; align-items: center;
  border: 1px solid rgba(255,255,255,0.5);
}
.chip-label { font-size: 13px; color: var(--brand-primary); }
.chip-value { font-size: 14px; font-weight: 800; color: var(--brand-deep); }

.drawer-section-header {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 16px; font-size: 16px; font-weight: 800; color: var(--c-text);
}
.upload-trigger { border-radius: 16px !important; font-weight: 600 !important; background: var(--grad) !important; border: none !important; color: #fff !important; }

.cw-list { display: flex; flex-direction: column; gap: 12px; }
.cw-empty { text-align: center; color: var(--brand-lavender); padding: 60px 0; font-size: 14px; font-weight: 600; }
.cw-item {
  display: flex; align-items: center; gap: 16px;
  padding: 18px 20px; background: #FFFFFF;
  border-radius: 16px; border: 1px solid var(--c-border);
  cursor: pointer; transition: all 0.3s;
}
.cw-item:hover { border-color: var(--brand-primary); background: #F8FAFC; transform: translateX(6px); box-shadow: 0 8px 20px rgba(48,122,227,0.08); }
.cw-icon { font-size: 24px; flex-shrink: 0; }
.cw-info { flex: 1; min-width: 0; }
.cw-name { font-size: 15px; font-weight: 700; color: var(--c-text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.cw-hint { font-size: 12px; color: var(--c-text2); margin-top: 4px; }
.cw-go {
  background: var(--brand-light); color: var(--brand-deep); border: none;
  padding: 8px 16px; border-radius: 12px; font-size: 13px; font-weight: 700;
  cursor: pointer; white-space: nowrap; transition: all 0.3s;
}
.cw-item:hover .cw-go { background: var(--brand-primary); color: #FFF; transform: scale(1.05); }

.kb-list { display: flex; flex-direction: column; gap: 12px; min-height: 48px; }
.kb-empty { padding: 28px 0 !important; }
.kb-item {
  display: flex; align-items: flex-start; gap: 14px;
  padding: 16px 18px;
  background: linear-gradient(145deg, rgba(255,255,255,0.95), rgba(248,250,255,0.98));
  border-radius: var(--r-md);
  border: 1px solid rgba(48, 122, 227, 0.12);
  box-shadow: 0 2px 12px rgba(20, 66, 211, 0.04);
  transition: border-color 0.25s, box-shadow 0.25s, transform 0.2s;
}
.kb-item:hover {
  border-color: rgba(48, 122, 227, 0.28);
  box-shadow: 0 8px 24px rgba(48, 122, 227, 0.1);
}
.kb-item--processing {
  border-color: rgba(48, 122, 227, 0.35);
  background: linear-gradient(145deg, rgba(210,230,254,0.35), rgba(255,255,255,0.95));
}
.kb-icon-wrap {
  width: 44px; height: 44px; border-radius: 12px;
  background: var(--brand-light);
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
  border: 1px solid rgba(48, 122, 227, 0.12);
}
.kb-icon { font-size: 22px; line-height: 1; }
.kb-info { flex: 1; min-width: 0; }
.kb-name-btn {
  display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
  width: 100%; text-align: left;
  padding: 0; margin: 0; border: none; background: none; cursor: pointer;
  font: inherit;
}
.kb-name-btn:hover .kb-name { color: var(--brand-primary); text-decoration: underline; text-underline-offset: 3px; }
.kb-name {
  font-size: 15px; font-weight: 700; color: var(--c-text);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  flex: 1; min-width: 0;
}
.kb-open-hint {
  font-size: 12px; font-weight: 700; color: var(--brand-primary);
  flex-shrink: 0; opacity: 0.85;
}
.kb-meta { font-size: 12px; color: var(--c-text2); margin-top: 6px; line-height: 1.45; }
.kb-progress-block { margin-top: 10px; max-width: 420px; }
.kb-progress-block :deep(.el-progress-bar__outer) { border-radius: 6px; }
.kb-progress-text { display: block; font-size: 11px; color: var(--brand-primary); margin-top: 6px; font-weight: 600; }
.kb-del { flex-shrink: 0; margin-top: 2px; }

.kb-page-wrap { padding: 0 8px 24px; }
.kb-page-lead {
  font-size: 13px; color: var(--c-text2); line-height: 1.55; max-width: 720px; margin: 0 0 20px 4px;
}
.kb-page-empty { padding: 48px 0 !important; }
.kb-page-layout {
  display: grid;
  grid-template-columns: minmax(200px, 280px) 1fr;
  gap: 20px;
  align-items: start;
  min-height: 320px;
}
@media (max-width: 768px) {
  .kb-page-layout { grid-template-columns: 1fr; }
}
.kb-page-courses {
  background: var(--c-surface);
  border-radius: var(--r-lg);
  border: 1px solid var(--c-border);
  padding: 14px;
  max-height: min(70vh, 560px);
  overflow-y: auto;
}
.kb-page-aside-title {
  font-size: 12px; font-weight: 800; color: var(--brand-primary); text-transform: uppercase; letter-spacing: 0.04em;
  margin-bottom: 12px; padding-left: 4px;
}
.kb-page-course-btn {
  display: flex; flex-direction: column; align-items: flex-start; gap: 4px;
  width: 100%; text-align: left;
  padding: 12px 14px; margin-bottom: 8px; border: 1px solid var(--c-border);
  border-radius: var(--r-md); background: #fff; cursor: pointer;
  transition: border-color 0.2s, background 0.2s, box-shadow 0.2s;
}
.kb-page-course-btn:last-child { margin-bottom: 0; }
.kb-page-course-btn:hover {
  border-color: var(--brand-primary); background: rgba(48, 122, 227, 0.04);
}
.kb-page-course-btn.active {
  border-color: var(--brand-primary); background: linear-gradient(135deg, rgba(48,122,227,0.1), rgba(20,66,211,0.06));
  box-shadow: 0 4px 14px rgba(48, 122, 227, 0.12);
}
.kb-page-course-name { font-size: 14px; font-weight: 700; color: var(--c-text); line-height: 1.3; }
.kb-page-course-meta { font-size: 11px; color: var(--c-text2); }
.kb-page-panel {
  background: var(--c-surface);
  border-radius: var(--r-lg);
  border: 1px solid var(--c-border);
  padding: 20px 22px;
  min-height: 320px;
}
.kb-page-panel--glass {
  background: linear-gradient(165deg, rgba(255,255,255,0.98) 0%, rgba(248,250,255,0.99) 100%);
  box-shadow: 0 12px 40px rgba(20, 66, 211, 0.06);
  border: 1px solid rgba(48, 122, 227, 0.14);
}
.kb-page-panel-title-wrap { min-width: 0; }
.kb-page-panel-sub {
  margin: 6px 0 0;
  font-size: 12px;
  color: var(--c-text2);
  font-weight: 500;
}
.kb-page-panel--empty {
  display: flex; align-items: center; justify-content: center;
  color: var(--c-text2); font-size: 14px;
}
.kb-page-panel-head {
  display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap;
  margin-bottom: 18px; padding-bottom: 14px; border-bottom: 1px solid var(--c-border);
}
.kb-page-panel-title { margin: 0; font-size: 18px; font-weight: 800; color: var(--brand-deep); }
.kb-page-doc-list { min-height: 120px; }

/* ================================================================
   对话框 & 表单
   ================================================================ */
:deep(.fancy-dialog) {
  border-radius: 24px !important; overflow: hidden;
  box-shadow: 0 24px 64px rgba(20,66,211,0.15) !important;
}
:deep(.fancy-dialog .el-dialog__header) { padding: 32px 32px 16px !important; margin-right: 0 !important; }
:deep(.fancy-dialog .el-dialog__title) { font-size: 22px !important; font-weight: 800 !important; color: var(--brand-deep) !important; }
:deep(.fancy-dialog .el-dialog__body) { padding: 16px 32px 32px !important; }

.profile-top { text-align: center; margin-bottom: 24px; }
.profile-hint { font-size: 13px; color: var(--brand-lavender); margin-top: 12px; font-weight: 600; }
.brand-avatar { border: 4px solid var(--brand-light); }

:deep(.fancy-uploader .el-upload-dragger) {
  border-radius: 20px !important; padding: 48px !important;
  background: var(--brand-light) !important; border: 2px dashed var(--brand-lavender) !important;
  transition: all 0.3s;
}
:deep(.fancy-uploader .el-upload-dragger:hover) { border-color: var(--brand-primary) !important; background: #E0F0FF !important; }
:deep(.fancy-uploader .el-icon--upload) { font-size: 56px !important; margin-bottom: 16px !important; }

:deep(.el-form-item__label) { font-size: 15px !important; font-weight: 700 !important; color: var(--brand-deep) !important; }
:deep(.el-input__wrapper), :deep(.el-select .el-input__wrapper) {
  border-radius: 12px !important; background: #F8FAFC !important; box-shadow: 0 0 0 1px var(--c-border) inset !important;
}
:deep(.el-input__wrapper.is-focus) { box-shadow: 0 0 0 2px var(--brand-primary) inset !important; }

.dlg-footer { display: flex; gap: 16px; justify-content: flex-end; }
.brand-btn {
  background: var(--grad) !important; border: none !important;
  box-shadow: 0 6px 16px rgba(48,122,227,0.3) !important; transition: all 0.3s !important;
}
.brand-btn:hover { transform: translateY(-2px); box-shadow: 0 8px 24px rgba(20,66,211,0.4) !important; }

/* ================================================================
   响应式适配
   ================================================================ */
@media (max-width: 1024px) {
  .stats-row { grid-template-columns: repeat(2, 1fr); }
  .main-area { padding: 24px 28px; }
  .action-btn .btn-label { display: none; }
}

@media (max-width: 768px) {
  .sidebar {
    position: fixed; top: 0; left: 0; bottom: 0;
    width: 280px; padding: 24px 16px;
    box-shadow: 8px 0 32px rgba(20,66,211,0.15);
  }
  .main-area { padding: calc(var(--topbar-h) + 16px) 16px 24px; width: 100%; }
  .toolbar { flex-direction: column; align-items: stretch; gap: 12px; margin-bottom: 24px; }
  .toolbar-left { display: none; }
  .toolbar-right { flex-direction: column; width: 100%; }
  .toolbar-right > * { width: 100% !important; }
  .search-box, .search-box.expanded { width: 100% !important; }
  .term-filter { width: 100% !important; }
  .action-btn { width: 100%; justify-content: center; }
  .action-btn .btn-label { display: inline; }

  .stats-row { grid-template-columns: repeat(2, 1fr); gap: 12px; margin-bottom: 24px; }
  .stat-card { padding: 16px; }
  .stat-icon { width: 40px; height: 40px; }
  .s-icon { width: 20px; height: 20px; }
  .stat-value { font-size: 20px; }

  .course-grid { grid-template-columns: 1fr; gap: 16px; }
  .card-cover { height: 140px; }
  .card-body { padding: 16px 20px 20px; }
  .cover-letter { font-size: 48px; }

  .blob { opacity: 0.15; }
  .b3 { display: none; }
}

@media (max-width: 380px) {
  .stats-row { grid-template-columns: 1fr 1fr; gap: 10px; }
  .main-area { padding: calc(var(--topbar-h) + 12px) 12px 20px; }
}
</style>