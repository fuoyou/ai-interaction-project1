<template>
  <div class="course-center-container">
    
    <!-- 顶部标题与操作栏 -->
    <div class="page-header">
      <div class="header-left">
        <h1 class="page-title">AI智慧课程中心</h1>
        <div class="page-tabs">
          <div class="tab-item active">我教的课</div>
        </div>
      </div>
      
      <div class="header-right">
        <el-select v-model="termSelect" placeholder="全部学期" class="filter-select" clearable>
          <el-option label="全部学期" value="all" />
          <el-option label="2026年春夏学期" value="2026年春夏学期" />
          <el-option label="2025年秋冬学期" value="2025年秋冬学期" />
        </el-select>

        <el-input
          v-model="searchQuery"
          placeholder="输入课程名称"
          class="search-input"
          :prefix-icon="Search"
          clearable
        />

        <el-button type="primary" class="main-btn" @click="showCreateCourseDialog = true">
          <el-icon><Plus /></el-icon>新建课程
        </el-button>
      </div>
    </div>

    <!-- 课程卡片网格区域 -->
    <div class="scroll-area" v-loading="loadingCourses">
      <div v-if="filteredCourses.length === 0" class="empty-state">
        <el-empty description="暂无课程，请点击右上角新建课程" />
      </div>

      <div v-else class="course-grid">
        <div 
          v-for="course in filteredCourses" 
          :key="course.id" 
          class="course-card"
          @click="openCourseDrawer(course)"
        >
          <div class="card-cover">
            <div class="cover-bg"></div>
            <div class="term-tag">{{ course.term || '2026年春夏学期' }}</div>
          </div>
          
          <div class="card-info">
            <h3 class="course-title" :title="course.name">{{ course.name }}</h3>
            <div class="course-meta">
              <span class="teacher-name">{{ course.teacher }}</span>
              <div class="tags">
                <span v-if="course.hasGraph" class="tag-normal">图谱</span>
                <span class="tag-ai">AI智课</span>
              </div>
            </div>
          </div>

          <div class="card-action" @click.stop>
             <el-dropdown trigger="click" @command="(cmd) => handleCourseAction(cmd, course)">
                <el-icon class="more-icon"><MoreFilled /></el-icon>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="edit">编辑课程信息</el-dropdown-item>
                    <el-dropdown-item command="delete" class="danger-text">删除课程</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
          </div>
        </div>
      </div>
    </div>

    <!-- 抽屉：课程详情 -->
    <el-drawer
      v-model="drawerVisible"
      :title="activeCourse?.name || '课程详情'"
      :size="drawerSize"
      class="course-detail-drawer glass-drawer"
    >
      <div v-if="activeCourse" class="drawer-content">
        <el-tabs v-model="activeTab" class="custom-tabs">
          <el-tab-pane label="教学课件" name="courseware">
            <div class="tab-header">
              <span class="count-info">共 {{ activeCourse.coursewares?.length || 0 }} 份课件</span>
              <el-button type="primary" plain size="small" @click="openUploadDialog('courseware')">
                <el-icon><Upload /></el-icon> 上传课件
              </el-button>
            </div>
            
            <div class="file-list">
              <div v-if="!activeCourse.coursewares?.length" class="empty-list">暂无教学课件</div>
              <div 
                v-for="cw in activeCourse.coursewares" 
                :key="cw.id" 
                class="file-item clickable" 
                @click="goToCoursewareDetail(cw)"
              >
                <div class="file-icon blue"><el-icon><Document /></el-icon></div>
                <div class="file-info">
                  <div class="file-name">{{ cw.name || cw.courseName || '未命名课件' }}</div>
                  <div class="file-time">课件解析已完成</div>
                </div>
                <el-button type="danger" link @click.stop="deleteItem('courseware', cw.id)">删除</el-button>
              </div>
            </div>
          </el-tab-pane>

          <el-tab-pane label="底层知识库" name="knowledge">
            <div class="tab-header">
              <span class="count-info">共 {{ activeCourse.knowledge?.length || 0 }} 份补充资料（学生端同课程下可见并共用）</span>
              <el-button type="primary" plain size="small" @click="openUploadDialog('knowledge')">
                <el-icon><DocumentAdd /></el-icon> 补充资料
              </el-button>
            </div>
            <div class="ai-tip"><el-icon><InfoFilled /></el-icon> AI 将自动学习此列表中的文档用于答疑和生成内容。</div>
            
            <div class="file-list">
              <div v-if="!activeCourse.knowledge?.length" class="empty-list">暂无底层知识库资料</div>
              <div v-for="doc in activeCourse.knowledge" :key="doc.id" class="file-item knowledge-doc-row">
                <div class="file-icon accent"><el-icon><DocumentCopy /></el-icon></div>
                <div class="file-info">
                  <button type="button" class="knowledge-name-hit" @click="openKnowledgeDoc(doc)">
                    <span class="file-name">{{ doc.name }}</span>
                    <span class="knowledge-preview-pill">预览</span>
                  </button>
                  <div class="file-desc">{{ knowledgeDocMetaLine(doc) }}</div>
                  <div v-if="knowledgeIndexStatus(doc) === 'processing'" class="knowledge-progress">
                    <el-progress :indeterminate="true" :duration="2.5" :stroke-width="4" :show-text="false" />
                    <span class="knowledge-progress-label">正在解析与建索引…</span>
                  </div>
                </div>
                <el-button type="danger" link @click.stop="deleteItem('knowledge', doc.id)">删除</el-button>
              </div>
            </div>
          </el-tab-pane>
        </el-tabs>
      </div>
    </el-drawer>

    <!-- 对话框：新建课程 -->
    <el-dialog v-model="showCreateCourseDialog" title="新建课程" width="500px" align-center class="glass-dialog">
      <el-form :model="courseForm" label-position="top">
        <el-form-item label="课程名称 (必填)">
          <el-input v-model="courseForm.name" placeholder="请输入课程名称" class="glass-input" />
        </el-form-item>
        <el-form-item label="所属学期">
          <el-input v-model="courseForm.term" placeholder="例如：2026年春夏学期" class="glass-input" />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showCreateCourseDialog = false" class="glass-btn">取消</el-button>
          <el-button type="primary" :loading="creating" @click="submitCreateCourse" class="glass-btn-primary">确认创建</el-button>
        </span>
      </template>
    </el-dialog>

    <!-- 对话框：编辑课程 -->
    <el-dialog v-model="showEditCourseDialog" title="编辑课程信息" width="500px" align-center class="glass-dialog">
      <el-form :model="editCourseForm" label-position="top">
        <el-form-item label="课程名称 (必填)">
          <el-input v-model="editCourseForm.name" placeholder="请输入课程名称" class="glass-input" />
        </el-form-item>
        <el-form-item label="所属学期">
          <el-input v-model="editCourseForm.term" placeholder="例如：2026年春夏学期" class="glass-input" />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showEditCourseDialog = false" class="glass-btn">取消</el-button>
          <el-button type="primary" :loading="editing" @click="submitEditCourse" class="glass-btn-primary">保存修改</el-button>
        </span>
      </template>
    </el-dialog>

    <!-- 对话框：统一上传入口 -->
    <el-dialog v-model="showUploadDialog" :title="uploadType === 'courseware' ? '上传教学课件' : '补充知识库资料'" width="500px" align-center class="glass-dialog">
      <el-form label-position="top">
        <el-form-item :label="uploadType === 'courseware' ? '课件文件' : '资料文件'">
          <el-upload drag action="#" :auto-upload="false" :on-change="handleFileSelect" class="custom-uploader" :accept="uploadType === 'courseware' ? '.pdf,.ppt,.pptx' : '.pdf,.doc,.docx,.txt'">
            <el-icon class="el-icon--upload" color="#307AE3"><UploadFilled /></el-icon>
            <div class="el-upload__text">将文件拖到此处，或 <em>点击上传</em></div>
          </el-upload>
        </el-form-item>
        <el-form-item v-if="uploadType === 'knowledge'" label="资料备注 (选填)">
          <el-input v-model="uploadDesc" placeholder="简单描述该资料用途" class="glass-input" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showUploadDialog = false" class="glass-btn">取消</el-button>
        <el-button type="primary" :loading="uploading" @click="submitUpload" class="glass-btn-primary">确认上传并解析</el-button>
      </template>
    </el-dialog>

  </div>
</template>

<script setup>
import { ref, computed, reactive, onMounted, onUnmounted, watch } from 'vue'
import { Plus, Search, MoreFilled, Upload, DocumentAdd, Document, DocumentCopy, UploadFilled, InfoFilled } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { listCategories, createCategory, updateCategory, deleteCategory, listMyCourses, uploadCourseToCategory, listKnowledgeDocs, uploadKnowledgeDoc, deleteKnowledgeDoc, deleteCourseware, fetchKnowledgeDocFile } from '@/api/lesson'

const emit = defineEmits(['selectCourse'])

const getRealTeacherName = () => {
  try {
    const userInfoStr = localStorage.getItem('userInfo') || localStorage.getItem('user')
    if (userInfoStr) {
      const user = JSON.parse(userInfoStr)
      if (user.nickname) return user.nickname
      if (user.name) return user.name
      if (user.realName) return user.realName
      if (user.username) return user.username
    }
  } catch (e) {}
  const name1 = localStorage.getItem('userName')
  const name2 = localStorage.getItem('username')
  const name3 = localStorage.getItem('teacherName')
  if (name1) return name1
  if (name2) return name2
  if (name3) return name3
  return '当前教师'
}

const currentTeacherName = ref(getRealTeacherName())
const courses = ref([])
const loadingCourses = ref(false)
const termSelect = ref('all')
const searchQuery = ref('')
const drawerVisible = ref(false)
const activeCourse = ref(null)
const activeTab = ref('courseware')
const showCreateCourseDialog = ref(false)
const creating = ref(false)
const courseForm = reactive({ name: '', term: '2026年春夏学期' })
const showEditCourseDialog = ref(false)
const editing = ref(false)
const editCourseForm = reactive({ id: '', name: '', term: '' })
const showUploadDialog = ref(false)
const uploadType = ref('courseware') 
const uploadFile = ref(null)
const uploadDesc = ref('')
const uploading = ref(false)

/** @type {ReturnType<typeof setInterval> | null} */
let knowledgePollTimer = null

const clearKnowledgePoll = () => {
  if (knowledgePollTimer != null) {
    clearInterval(knowledgePollTimer)
    knowledgePollTimer = null
  }
}

const knowledgeIndexStatus = (doc) => {
  if (doc.indexStatus) return doc.indexStatus
  if (doc.hasRag) return 'ready'
  return 'empty'
}

const knowledgeStatusText = (doc) => {
  const s = knowledgeIndexStatus(doc)
  if (s === 'processing') return '解析与建索引中'
  if (s === 'ready') return '已索引'
  if (s === 'failed') return '索引失败'
  return '未建立索引'
}

const knowledgeDocMetaLine = (doc) => {
  const ft = doc.fileType?.toUpperCase() || '—'
  const st = knowledgeStatusText(doc)
  const t = doc.createTime || ''
  const desc = doc.description ? ` · ${doc.description}` : ''
  return `${ft} · ${st}${t ? ' · ' + t : ''}${desc}`
}

const openKnowledgeDoc = async (doc) => {
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

const filteredCourses = computed(() => {
  let result = courses.value
  if (termSelect.value && termSelect.value !== 'all') {
    result = result.filter(c => c.term === termSelect.value)
  }
  if (searchQuery.value) {
    const q = searchQuery.value.toLowerCase()
    result = result.filter(c => c.name.toLowerCase().includes(q))
  }
  return result
})

const drawerSize = computed(() => {
  if (typeof window === 'undefined') return '600px'
  const width = window.innerWidth
  if (width <= 480) return '100%'
  if (width <= 768) return '90%'
  if (width <= 1024) return '75%'
  return '600px'
})

const loadCourses = async () => {
  loadingCourses.value = true
  try {
    const catRes = await listCategories()
    const backendCategories = catRes.data || []
    let allCoursewares = []
    try {
      const courseRes = await listMyCourses()
      allCoursewares = courseRes.data || []
    } catch (e) { }
    const courseList = []
    for (const cat of backendCategories) {
      const coursewares = allCoursewares.filter(cw => {
        const cwCourseId = cw.courseId || cw.category_id || cw.categoryId || cw.course_id
        return cwCourseId === cat.id || cwCourseId === String(cat.id)
      })
      let knowledge = []
      try {
        const kRes = await listKnowledgeDocs(cat.id)
        knowledge = kRes.data || []
      } catch (e) { }
      let teacher = currentTeacherName.value
      let term = '2026年春夏学期'
      try {
        if (cat.description && cat.description.startsWith('{')) {
          const descObj = JSON.parse(cat.description)
          term = descObj.term || term
        }
      } catch (e) {}
      courseList.push({
        id: cat.id, name: cat.name, rawDescription: cat.description, teacher, term, hasGraph: true, coursewares, knowledge
      })
    }
    courses.value = courseList
    if (drawerVisible.value && activeCourse.value) {
      const updatedActive = courses.value.find(c => c.id === activeCourse.value.id)
      if (updatedActive) activeCourse.value = updatedActive
    }
  } catch (error) { ElMessage.error('加载课程数据失败') } 
  finally { loadingCourses.value = false }
}

const submitCreateCourse = async () => {
  if (!courseForm.name.trim()) return ElMessage.warning('请输入课程名称')
  creating.value = true
  try {
    const descJson = JSON.stringify({ teacher: currentTeacherName.value, term: courseForm.term })
    await createCategory(courseForm.name, descJson)
    ElMessage.success('课程创建成功')
    showCreateCourseDialog.value = false
    courseForm.name = ''
    await loadCourses()
  } catch (e) { ElMessage.error('创建失败') } 
  finally { creating.value = false }
}

const openCourseDrawer = (course) => {
  activeCourse.value = course
  drawerVisible.value = true
  activeTab.value = 'courseware'
}

const goToCoursewareDetail = (courseware) => {
  if (!activeCourse.value) return
  emit('selectCourse', courseware, activeCourse.value.knowledge || [], activeCourse.value.id)
  drawerVisible.value = false
}

const handleCourseAction = (command, course) => {
  if (command === 'edit') {
    editCourseForm.id = course.id
    editCourseForm.name = course.name
    editCourseForm.term = course.term
    showEditCourseDialog.value = true
  } 
  else if (command === 'delete') {
    ElMessageBox.confirm(`确定要彻底删除课程「${course.name}」吗？相关所有课件和资料也将被清除！`, '高危操作警告', { type: 'error', confirmButtonText: '确定删除' })
      .then(async () => {
        try {
          await deleteCategory(course.id)
          ElMessage.success('课程已成功删除')
          await loadCourses()
        } catch (e) { ElMessage.error('删除课程失败') }
      })
  }
}

const submitEditCourse = async () => {
  if (!editCourseForm.name.trim()) return ElMessage.warning('课程名称不能为空')
  editing.value = true
  try {
    const descJson = JSON.stringify({ teacher: currentTeacherName.value, term: editCourseForm.term })
    await updateCategory(editCourseForm.id, editCourseForm.name, descJson)
    ElMessage.success('课程信息已更新')
    showEditCourseDialog.value = false
    await loadCourses()
  } catch (e) { ElMessage.error('更新失败') } 
  finally { editing.value = false }
}

const openUploadDialog = (type) => {
  uploadType.value = type
  uploadFile.value = null
  uploadDesc.value = ''
  showUploadDialog.value = true
}

const handleFileSelect = (file) => { uploadFile.value = file.raw }

const submitUpload = async () => {
  if (!uploadFile.value) return ElMessage.warning('请选择要上传的文件')
  if (!activeCourse.value) return
  uploading.value = true
  try {
    if (uploadType.value === 'courseware') {
      await uploadCourseToCategory(uploadFile.value, activeCourse.value.id)
      ElMessage.success('课件上传成功，AI 正在后台进行深度解析')
    } else {
      const fileName = uploadFile.value.name.replace(/\.[^.]+$/, '') || uploadFile.value.name
      await uploadKnowledgeDoc(uploadFile.value, activeCourse.value.id, fileName, uploadDesc.value)
      ElMessage.success('资料已添加，解析进度见列表')
    }
    showUploadDialog.value = false
    await loadCourses()
    if (activeCourse.value) {
      const updated = courses.value.find(c => c.id === activeCourse.value.id)
      if (updated) { activeCourse.value = { ...updated } }
    }
  } catch (error) { ElMessage.error('上传失败，请检查网络或文件大小') } 
  finally { uploading.value = false }
}

const deleteItem = (type, id) => {
  ElMessageBox.confirm('确定要删除这份文件吗？该操作不可逆。', '删除确认', { type: 'warning' }).then(async () => {
    try {
      if (type === 'courseware') {
        await deleteCourseware(id)
        activeCourse.value.coursewares = activeCourse.value.coursewares.filter(item => item.id !== id)
        ElMessage.success('课件已成功删除')
      } else {
        await deleteKnowledgeDoc(id)
        activeCourse.value.knowledge = activeCourse.value.knowledge.filter(item => item.id !== id)
        ElMessage.success('知识库资料已彻底删除')
      }
    } catch (e) { ElMessage.error(e.response?.data?.msg || e.message || '删除失败') }
  }).catch(() => {})
}

watch(
  [drawerVisible, activeTab, activeCourse],
  () => {
    clearKnowledgePoll()
    if (!drawerVisible.value || activeTab.value !== 'knowledge' || !activeCourse.value) return
    const list = activeCourse.value.knowledge || []
    const proc = list.some((d) => knowledgeIndexStatus(d) === 'processing')
    if (!proc) return
    knowledgePollTimer = setInterval(() => loadCourses(), 2800)
  },
  { deep: true }
)

onMounted(() => {
  loadCourses()
  window.addEventListener('resize', () => { drawerSize.value })
})
onUnmounted(() => {
  window.removeEventListener('resize', () => {})
  clearKnowledgePoll()
})
</script>

<style scoped>
/* 全局覆盖 Element 颜色 */
:deep(.el-button--primary) {
  --el-button-bg-color: #307AE3;
  --el-button-border-color: #307AE3;
  --el-button-hover-bg-color: #1442D3;
  --el-button-hover-border-color: #1442D3;
}
:deep(.el-tabs__item.is-active) { color: #307AE3 !important; font-weight: bold; }
:deep(.el-tabs__active-bar) { background-color: #307AE3 !important; }

.course-center-container { display: flex; flex-direction: column; width: 100%; height: 100%; background-color: transparent; overflow: hidden; }
.page-header { display: flex; justify-content: space-between; align-items: flex-end; padding: 24px 32px 16px; flex-shrink: 0; }
.header-left .page-title { font-size: 30px; font-weight: 800; color: #1442D3; margin: 0 0 16px 0; letter-spacing: 1px;}
.page-tabs { display: flex; gap: 20px; }
.tab-item { font-size: 16px; font-weight: bold; color: #ACB1EC; cursor: pointer; padding: 6px 20px; border-radius: 24px; transition: all 0.3s; }
.tab-item:hover { color: #307AE3; background: rgba(210, 230, 254, 0.4); }
.tab-item.active { background-color: #307AE3; color: #FFF; box-shadow: 0 4px 12px rgba(48, 122, 227, 0.3); }

.header-right { display: flex; align-items: center; gap: 16px; padding-bottom: 4px; }
.filter-select { width: 140px; }
.search-input { width: 260px; border-radius: 20px; }
:deep(.search-input .el-input__wrapper) { border-radius: 20px; box-shadow: 0 0 0 1px #D2E6FE inset; }
:deep(.search-input .el-input__wrapper.is-focus) { box-shadow: 0 0 0 1px #307AE3 inset; }
.main-btn { border-radius: 20px; border: none; padding: 8px 24px; font-weight: bold; }

/* 滚动区域与网格 */
.scroll-area { flex: 1; overflow-y: auto; padding: 16px 32px 40px; }
.course-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 28px; }

/* 卡片样式 */
.course-card { background: rgba(255, 255, 255, 0.85); backdrop-filter: blur(10px); border-radius: 16px; overflow: hidden; cursor: pointer; transition: all 0.4s cubic-bezier(0.25, 0.8, 0.25, 1); border: 1px solid #D2E6FE; position: relative; }
.course-card:hover { transform: translateY(-6px); box-shadow: 0 16px 32px rgba(48, 122, 227, 0.15); border-color: #ACB1EC; }
.card-cover { height: 150px; position: relative; background: linear-gradient(135deg, #D2E6FE 0%, #ACB1EC 100%); overflow: hidden; }
.cover-bg { position: absolute; top: -50px; left: -50px; right: -50px; bottom: 0; background: radial-gradient(circle at 80% 20%, rgba(255,255,255,0.4) 0%, rgba(255,255,255,0) 60%); }
.term-tag { position: absolute; bottom: 0; left: 0; background: rgba(20, 66, 211, 0.7); backdrop-filter: blur(4px); color: white; font-size: 12px; padding: 6px 16px; border-top-right-radius: 16px; font-weight: bold; }
.card-info { padding: 20px; }
.course-title { margin: 0 0 12px 0; font-size: 18px; color: #1442D3; font-weight: bold; line-height: 1.4; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; height: 50px; }
.course-meta { display: flex; justify-content: space-between; align-items: center; }
.teacher-name { font-size: 14px; color: #307AE3; font-weight: 500; }
.tags { display: flex; gap: 8px; }
.tag-normal { font-size: 12px; color: #307AE3; background-color: #D2E6FE; padding: 4px 10px; border-radius: 6px; font-weight: bold;}
.tag-ai { font-size: 12px; color: #FFF; background-color: #ACB1EC; padding: 4px 10px; border-radius: 6px; font-weight: bold; }
.card-action { position: absolute; top: 12px; right: 12px; z-index: 10; }
.more-icon { color: #FFF; font-size: 20px; background: rgba(20, 66, 211, 0.3); border-radius: 50%; padding: 6px; transition: all 0.3s; }
.more-icon:hover { background: rgba(20, 66, 211, 0.7); transform: scale(1.1); }
.danger-text { color: #f56c6c !important; }

/* 抽屉样式 */
:deep(.glass-drawer .el-drawer) { background: rgba(255,255,255,0.95) !important; backdrop-filter: blur(20px) !important; border-left: 1px solid #D2E6FE !important; }
.drawer-content { padding: 0 24px; }
.tab-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; margin-top: 10px; }
.count-info { font-size: 15px; color: #1442D3; font-weight: bold; }
.ai-tip { font-size: 13px; color: #307AE3; background: rgba(210, 230, 254, 0.5); padding: 12px 16px; border-radius: 8px; margin-bottom: 20px; display: flex; align-items: center; gap: 8px; font-weight: 500; border: 1px solid #D2E6FE; }
.file-list { display: flex; flex-direction: column; gap: 14px; }
.file-item { display: flex; align-items: center; padding: 16px; background: #FFFFFF; border-radius: 12px; border: 1px solid #D2E6FE; transition: all 0.3s; }
.file-item.clickable { cursor: pointer; }
.file-item.clickable:hover { border-color: #307AE3; box-shadow: 0 4px 16px rgba(48, 122, 227, 0.1); transform: translateX(4px); }
.file-icon { width: 42px; height: 42px; border-radius: 10px; display: flex; justify-content: center; align-items: center; font-size: 22px; margin-right: 16px; }
.file-icon.blue { background: #D2E6FE; color: #307AE3; }
.file-icon.accent { background: rgba(172, 177, 236, 0.2); color: #ACB1EC; }
.file-info { flex: 1; overflow: hidden; }
.file-name { font-size: 15px; font-weight: bold; color: #1442D3; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.file-time, .file-desc { font-size: 13px; color: #ACB1EC; margin-top: 6px; }
.knowledge-doc-row { align-items: flex-start; }
.knowledge-name-hit {
  display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
  width: 100%; padding: 0; margin: 0; border: none; background: none; cursor: pointer;
  font: inherit; text-align: left;
}
.knowledge-name-hit:hover .file-name { color: #307AE3; text-decoration: underline; text-underline-offset: 3px; }
.knowledge-preview-pill {
  font-size: 12px; font-weight: 700; color: #307AE3; background: rgba(210, 230, 254, 0.6);
  padding: 2px 10px; border-radius: 999px;
}
.knowledge-progress { margin-top: 10px; max-width: 360px; }
.knowledge-progress-label { display: block; font-size: 12px; color: #307AE3; margin-top: 6px; font-weight: 600; }
.empty-list { text-align: center; color: #ACB1EC; padding: 40px 0; font-weight: bold; }
:deep(.custom-uploader .el-upload-dragger) { border-radius: 12px; border-color: #D2E6FE; }
:deep(.custom-uploader .el-upload-dragger:hover) { border-color: #307AE3; }

/* 弹窗及输入框高级样式 */
:deep(.glass-dialog .el-dialog) { background: rgba(255,255,255,0.95) !important; backdrop-filter: blur(20px) !important; border-radius: 16px !important; border: 1px solid #D2E6FE !important; box-shadow: 0 20px 60px rgba(48, 122, 227, 0.15) !important; }
:deep(.glass-input .el-input__wrapper) { background: rgba(210, 230, 254, 0.2) !important; border-radius: 10px !important; box-shadow: 0 0 0 1px #D2E6FE inset !important; transition: all 0.3s; }
:deep(.glass-input .el-input__wrapper.is-focus) { box-shadow: 0 0 0 2px #307AE3 inset !important; background: #FFFFFF !important; }

.dialog-footer { display: flex; justify-content: flex-end; gap: 12px; }
.glass-btn { background: #FFFFFF !important; border: 1px solid #D2E6FE !important; color: #1442D3 !important; border-radius: 8px; font-weight: bold; transition: all 0.3s; }
.glass-btn:hover { background: #D2E6FE !important; color: #307AE3 !important; border-color: #307AE3 !important; }
.glass-btn-primary { background: linear-gradient(135deg, #307AE3 0%, #1442D3 100%) !important; border: none !important; border-radius: 8px; font-weight: bold; transition: all 0.3s; }
.glass-btn-primary:hover { transform: translateY(-2px); box-shadow: 0 8px 24px rgba(48, 122, 227, 0.3) !important; }

/* 响应式移动端适配... */
@media (max-width: 768px) {
  .page-header { padding: 12px 16px; flex-direction: column; align-items: flex-start; gap: 12px; }
  .header-right { width: 100%; flex-wrap: wrap; }
  .filter-select, .search-input { width: 100%; }
}
</style>