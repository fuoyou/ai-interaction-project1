<template>
  <div class="polish-panel brand-glass-panel">
    <div class="polish-panel-header" @click="collapsed = !collapsed">
      <div class="polish-panel-title">
        <el-icon class="brand-icon"><MagicStick /></el-icon>
        <span class="brand-title-text">批量 AI 润色</span>
        <el-tag size="small" class="range-tag">{{ pageRangeLabel }}</el-tag>
      </div>
      <el-icon class="collapse-icon" :class="{ 'is-collapsed': collapsed }"><ArrowDown /></el-icon>
    </div>

    <div v-show="!collapsed" class="polish-panel-body">
      <!-- 范围选择 -->
      <div class="section">
        <div class="section-label brand-label">润色范围</div>
        <div class="range-controls">
          <el-radio-group v-model="rangeMode" size="small" class="brand-radio-group">
            <el-radio-button value="all">全部页</el-radio-button>
            <el-radio-button value="current">当前页</el-radio-button>
            <el-radio-button value="custom">自定义</el-radio-button>
          </el-radio-group>
          <template v-if="rangeMode === 'custom'">
            <div class="custom-range">
              <span class="range-label brand-text">第</span>
              <el-input-number v-model="rangeStart" :min="1" :max="totalPages" size="small" controls-position="right" class="brand-input-number" />
              <span class="range-label brand-text">页 至 第</span>
              <el-input-number v-model="rangeEnd" :min="rangeStart" :max="totalPages" size="small" controls-position="right" class="brand-input-number" />
              <span class="range-label brand-text">页</span>
            </div>
          </template>
        </div>
      </div>

      <!-- 润色要求 -->
      <div class="section">
        <div class="section-label-row">
          <span class="section-label brand-label">润色要求</span>
          <div class="template-actions">
            <el-button size="small" link class="brand-link-btn" :class="{ 'is-listening': isListening }" @click="startVoiceInput" :title="isListening ? '正在聆听...' : '语音输入'">
              <el-icon><Microphone /></el-icon>
              {{ isListening ? '聆听中...' : '语音' }}
            </el-button>
            <el-divider direction="vertical" class="brand-divider" />
            <el-dropdown trigger="click" @command="applyTemplate">
              <el-button size="small" link class="brand-link-btn">
                <el-icon><Collection /></el-icon> 选择模板
              </el-button>
              <template #dropdown>
                <el-dropdown-menu class="brand-dropdown-menu">
                  <el-dropdown-item v-for="tpl in templates" :key="tpl.id" :command="tpl">
                    <div class="tpl-item">
                      <span class="tpl-name">{{ tpl.name }}</span>
                      <el-button v-if="tpl.custom" size="small" link type="danger" @click.stop="deleteTemplate(tpl.id)">删除</el-button>
                    </div>
                  </el-dropdown-item>
                  <el-dropdown-item divided command="__new__" class="new-tpl-item">
                    <el-icon><Plus /></el-icon> 将当前要求保存为模板
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </div>
        <el-input 
          v-model="polishRequirement" 
          type="textarea" 
          :rows="3" 
          placeholder="输入润色要求，例如：语言更加生动活泼，增加教学互动性..." 
          class="polish-textarea brand-textarea" 
        />
      </div>

      <!-- 操作按钮 -->
      <div class="section section-actions">
        <div class="progress-info" v-if="polishing">
          <el-progress 
            :percentage="progressPercent" 
            :format="() => `${progressDone}/${progressTotal} 页`" 
            color="#307AE3" 
            class="brand-progress" 
          />
          <span class="progress-text brand-text">正在润色第 {{ progressDone }} / {{ progressTotal }} 页...</span>
        </div>
        <div class="action-buttons">
          <el-button class="brand-btn-primary" :loading="polishing" :disabled="!polishRequirement.trim()" @click="startPolish">
            <el-icon class="el-icon--left"><MagicStick /></el-icon>
            {{ polishing ? '润色中...' : '开始润色' }}
          </el-button>
          <el-button v-if="polishing" class="brand-btn-outline" @click="cancelPolish">取消</el-button>
          <span class="polish-hint" v-if="!polishRequirement.trim()">请先输入润色要求</span>
        </div>
      </div>
    </div>

    <!-- 保存对话框 -->
    <el-dialog v-model="showSaveTemplate" title="保存为模板" width="400px" align-center class="brand-dialog">
      <el-form label-width="80px" class="brand-form">
        <el-form-item label="模板名称" required>
          <el-input v-model="newTemplateName" placeholder="输入模板名称" class="brand-input"/>
        </el-form-item>
        <el-form-item label="润色内容">
          <el-input :model-value="polishRequirement" type="textarea" :rows="2" disabled class="brand-textarea"/>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showSaveTemplate = false" class="brand-btn-outline">取消</el-button>
        <el-button type="primary" @click="saveTemplate" class="brand-btn-primary">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
// JS 逻辑保持不变，已省略展开...
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { MagicStick, ArrowDown, Collection, Plus, Microphone } from '@element-plus/icons-vue'
import { polishPage } from '@/api/course'

const props = defineProps({ totalPages: { type: Number, default: 0 }, currentPage: { type: Number, default: 0 }, slides: { type: Array, default: () => [] }, courseId: { type: [Number, String], default: null }})
const emit = defineEmits(['update:slides'])

const collapsed = ref(true)
const rangeMode = ref('all')
const rangeStart = ref(1)
const rangeEnd = ref(props.totalPages || 1)

watch(() => props.totalPages, (v) => { rangeEnd.value = v })
watch(() => props.currentPage, (v) => { if (rangeMode.value === 'current') { rangeStart.value = v + 1; rangeEnd.value = v + 1 } })
watch(rangeMode, (mode) => {
  if (mode === 'all') { rangeStart.value = 1; rangeEnd.value = props.totalPages } 
  else if (mode === 'current') { rangeStart.value = props.currentPage + 1; rangeEnd.value = props.currentPage + 1 }
})

const pageRangeLabel = computed(() => {
  if (rangeMode.value === 'all') return `全部 ${props.totalPages} 页`
  if (rangeMode.value === 'current') return `第 ${props.currentPage + 1} 页`
  return `第 ${rangeStart.value}-${rangeEnd.value} 页`
})

const polishRequirement = ref('')
const BUILTIN_TEMPLATES = [
  { id: 'vivid', name: '生动活泼', content: '请将讲稿改写得更加生动活泼，增加生动的比喻和实例，让学生更容易理解和记忆', custom: false },
  { id: 'professional', name: '专业严谨', content: '请将讲稿改写得更加专业严谨，使用准确的学科术语，逻辑清晰，层次分明', custom: false },
  { id: 'concise', name: '简洁精炼', content: '请将讲稿压缩精炼，去掉冗余内容，保留核心知识点，每个要点用简短清晰的语言表达', custom: false },
  { id: 'interactive', name: '互动式教学', content: '请将讲稿改写为互动式教学风格，加入提问、思考题和课堂活动引导，促进学生积极参与', custom: false },
  { id: 'story', name: '故事化叙述', content: '请将讲稿改写为故事化叙述风格，通过案例和故事引入知识点，使内容更有吸引力', custom: false },
]

const STORAGE_KEY = 'polish_templates_v1'
const loadCustomTemplates = () => { try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]') } catch { return [] } }
const customTemplates = ref(loadCustomTemplates())
const templates = computed(() => [ ...BUILTIN_TEMPLATES, ...customTemplates.value ])

const applyTemplate = (tpl) => {
  if (tpl === '__new__') {
    if (!polishRequirement.value.trim()) { ElMessage.warning('请先输入润色要求再保存为模板'); return }
    newTemplateName.value = ''; showSaveTemplate.value = true; return
  }
  polishRequirement.value = tpl.content
}

const deleteTemplate = (id) => {
  customTemplates.value = customTemplates.value.filter(t => t.id !== id)
  localStorage.setItem(STORAGE_KEY, JSON.stringify(customTemplates.value))
  ElMessage.success('模板已删除')
}

const showSaveTemplate = ref(false); const newTemplateName = ref('')
const saveTemplate = () => {
  if (!newTemplateName.value.trim()) { ElMessage.warning('请输入模板名称'); return }
  const tpl = { id: 'custom_' + Date.now(), name: newTemplateName.value.trim(), content: polishRequirement.value, custom: true }
  customTemplates.value.push(tpl); localStorage.setItem(STORAGE_KEY, JSON.stringify(customTemplates.value))
  showSaveTemplate.value = false; ElMessage.success('模板已保存')
}

const polishing = ref(false); const progressDone = ref(0); const progressTotal = ref(0)
const progressPercent = computed(() => progressTotal.value ? Math.round((progressDone.value / progressTotal.value) * 100) : 0 )
let cancelled = false
const cancelPolish = () => { cancelled = true; polishing.value = false; ElMessage.info('已取消润色') }

const isListening = ref(false)
const startVoiceInput = () => {
  if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) { ElMessage.warning('您的浏览器不支持语音输入'); return }
  if (isListening.value) return
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
  const recognition = new SpeechRecognition(); recognition.lang = 'zh-CN'; recognition.continuous = false; recognition.interimResults = false; isListening.value = true
  recognition.onresult = (event) => {
    const transcript = event.results[0][0].transcript
    polishRequirement.value = polishRequirement.value ? polishRequirement.value + '，' + transcript : transcript
    ElMessage.success('语音输入成功')
  }
  recognition.onerror = () => { ElMessage.error('语音识别失败，请重试') }
  recognition.onend = () => { isListening.value = false }
  recognition.start()
}

const cleanScriptContent = (text) => {
  if (!text) return text
  let s = text.trim()
  s = s.replace(/^#{1,6}\s+.+\n?/gm, '')
  s = s.replace(/\*\*(.+?)\*\*/g, '$1')
  s = s.replace(/\*(.+?)\*/g, '$1')
  s = s.replace(/^(当然[，,]?|好的[，,]?|以下是[^\n]*[：:]|根据[^\n]*[：:]|下面是[^\n]*[：:]|如下[：:]|优化后的讲稿[：:])[\s\S]*?\n\n?/i, '')
  s = s.replace(/^\*\*.+\*\*\n?/gm, '')
  return s.trim()
}

const startPolish = async () => {
  if (!props.courseId) { ElMessage.warning('请先选择课件'); return }
  if (!polishRequirement.value.trim()) { ElMessage.warning('请输入润色要求'); return }

  let targetIndices = []
  if (rangeMode.value === 'all') targetIndices = props.slides.map((_, i) => i)
  else if (rangeMode.value === 'current') targetIndices = [props.currentPage]
  else { for (let i = rangeStart.value - 1; i <= rangeEnd.value - 1; i++) if (i >= 0 && i < props.slides.length) targetIndices.push(i) }

  if (targetIndices.length === 0) { ElMessage.warning('没有可润色的页面'); return }
  polishing.value = true; cancelled = false; progressDone.value = 0; progressTotal.value = targetIndices.length

  const updatedSlides = props.slides.map(s => ({ ...s }))
  for (const idx of targetIndices) {
    if (cancelled) break
    const item = updatedSlides[idx]
    if (!item || !item.script?.trim()) { progressDone.value++; continue }
    try {
      const prevScript = idx > 0 && updatedSlides[idx - 1]?.script ? `【上一页结尾】${updatedSlides[idx - 1].script.slice(-120)}` : ''
      const nextScript = idx < updatedSlides.length - 1 && updatedSlides[idx + 1]?.script ? `【下一页开头】${updatedSlides[idx + 1].script.slice(0, 120)}` : ''
      const contextHint = [prevScript, nextScript].filter(Boolean).join('\n')
      const fullQuestion = contextHint ? `${polishRequirement.value}\n\n以下是前后页内容供参考，请确保本页讲稿与前后页衔接自然、逻辑连贯：\n${contextHint}` : polishRequirement.value
      const res = await polishPage(props.courseId, { pageNum: item.page, content: item.script, question: fullQuestion })
      if (res.data?.answerContent) { updatedSlides[idx] = { ...item, script: cleanScriptContent(res.data.answerContent) } }
    } catch (e) { console.error(`第${item.page}页润色失败:`, e) }
    progressDone.value++
    emit('update:slides', updatedSlides.map(s => ({ ...s })))
  }
  if (!cancelled) ElMessage.success(`润色完成，共处理 ${progressDone.value} 页`)
  polishing.value = false
}
</script>

<style scoped>
/* 严格遵循海洋品牌四色 */
.polish-panel {
  --primary-blue: #307AE3;
  --dark-blue: #1442D3;
  --light-blue: #D2E6FE;
  --lavender: #ACB1EC;
  --bg-color: #F8FAFC;
  --text-main: #1E293B;
  --text-sub: #64748B;
}

/* 玻璃质感主容器 */
.brand-glass-panel {
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(12px);
  border: 1px solid var(--light-blue);
  border-radius: 16px;
  box-shadow: 0 8px 24px rgba(20, 66, 211, 0.08);
  overflow: hidden;
  flex-shrink: 0;
  margin-bottom: 20px;
  transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
}

.brand-glass-panel:hover {
  box-shadow: 0 12px 32px rgba(20, 66, 211, 0.12);
  border-color: var(--primary-blue);
}

/* 头部样式 */
.polish-panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  cursor: pointer;
  background: linear-gradient(90deg, rgba(210, 230, 254, 0.4) 0%, rgba(255,255,255,0) 100%);
  border-bottom: 1px solid var(--light-blue);
  user-select: none;
  transition: background 0.3s;
}

.polish-panel-header:hover {
  background: rgba(210, 230, 254, 0.7);
}

.polish-panel-title {
  display: flex;
  align-items: center;
  gap: 10px;
}

.brand-icon {
  color: var(--primary-blue);
  font-size: 18px;
}

.brand-title-text {
  font-weight: 800;
  font-size: 16px;
  color: var(--dark-blue);
  letter-spacing: 0.5px;
}

.range-tag {
  background: var(--light-blue);
  color: var(--dark-blue);
  border: none;
  font-weight: 700;
  border-radius: 6px;
}

.collapse-icon {
  transition: transform 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
  color: var(--primary-blue);
  font-weight: bold;
  font-size: 16px;
}

.collapse-icon.is-collapsed {
  transform: rotate(-90deg);
}

/* 主体内容区 */
.polish-panel-body {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.section {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.brand-label {
  font-size: 14px;
  font-weight: 700;
  color: var(--dark-blue);
}

.section-label-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.template-actions {
  display: flex;
  align-items: center;
  gap: 6px;
}

.brand-link-btn {
  color: var(--primary-blue) !important;
  font-weight: 600 !important;
  font-size: 13px !important;
  transition: color 0.3s;
}
.brand-link-btn:hover {
  color: var(--dark-blue) !important;
}

.brand-divider {
  border-left-color: var(--light-blue);
}

/* 范围选择器重构 */
.range-controls {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
}

/* 重构 el-radio-group 为品牌样式 */
.brand-radio-group :deep(.el-radio-button__inner) {
  font-weight: 600;
  color: var(--text-sub);
  background: var(--bg-color);
  border: 1px solid var(--light-blue);
  box-shadow: none !important;
  transition: all 0.3s;
}

.brand-radio-group :deep(.el-radio-button:first-child .el-radio-button__inner) {
  border-radius: 8px 0 0 8px;
}
.brand-radio-group :deep(.el-radio-button:last-child .el-radio-button__inner) {
  border-radius: 0 8px 8px 0;
}

.brand-radio-group :deep(.el-radio-button__original-radio:checked + .el-radio-button__inner) {
  background-color: var(--primary-blue);
  border-color: var(--primary-blue);
  color: #FFF;
  box-shadow: -1px 0 0 0 var(--primary-blue) !important;
}

.brand-radio-group :deep(.el-radio-button__inner:hover) {
  color: var(--primary-blue);
}

.custom-range {
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--bg-color);
  padding: 4px 12px;
  border-radius: 8px;
  border: 1px solid var(--light-blue);
}

.brand-text {
  font-size: 13px;
  color: var(--text-main);
  font-weight: 600;
}

.brand-input-number {
  width: 90px !important;
}
.brand-input-number :deep(.el-input__wrapper) {
  box-shadow: none !important;
  border-bottom: 1px solid var(--primary-blue);
  border-radius: 0;
  background: transparent;
  padding-left: 0;
  padding-right: 32px;
}
.brand-input-number :deep(.el-input__inner) {
  color: var(--primary-blue);
  font-weight: 800;
  text-align: center;
}

/* 输入框重构 */
.brand-textarea :deep(.el-textarea__inner) {
  border-radius: 12px;
  border: 1px solid var(--light-blue);
  font-size: 14px;
  line-height: 1.6;
  resize: vertical;
  background: var(--bg-color);
  color: var(--text-main);
  font-weight: 500;
  transition: all 0.3s;
  padding: 12px;
}

.brand-textarea :deep(.el-textarea__inner:focus) {
  border-color: var(--primary-blue);
  box-shadow: 0 0 0 3px rgba(48, 122, 227, 0.1);
  background: #FFF;
}

.brand-textarea :deep(.el-textarea__inner::placeholder) {
  color: #94A3B8;
}

/* 下拉菜单 */
.tpl-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  width: 100%;
  min-width: 200px;
}
.tpl-name {
  font-weight: 600;
  color: var(--text-main);
}
.new-tpl-item {
  color: var(--primary-blue) !important;
  font-weight: 700 !important;
}

/* 进度条与操作区 */
.section-actions {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-top: 8px;
  padding-top: 16px;
  border-top: 1px dashed var(--light-blue);
}

.progress-info {
  display: flex;
  flex-direction: column;
  gap: 8px;
  background: rgba(48, 122, 227, 0.05);
  padding: 12px 16px;
  border-radius: 12px;
}

.brand-progress :deep(.el-progress-bar__outer) {
  background-color: var(--light-blue);
  border-radius: 4px;
}

.progress-text {
  font-size: 13px;
  color: var(--primary-blue);
  font-weight: 700;
  text-align: right;
}

.action-buttons {
  display: flex;
  align-items: center;
  gap: 16px;
}

/* 核心操作按钮 */
.brand-btn-primary {
  background: linear-gradient(135deg, var(--primary-blue) 0%, var(--dark-blue) 100%) !important;
  border: none !important;
  border-radius: 12px !important;
  font-weight: 800 !important;
  padding: 10px 24px !important;
  color: #FFF !important;
  box-shadow: 0 6px 16px rgba(20, 66, 211, 0.2) !important;
  transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1) !important;
}

.brand-btn-primary:hover:not(.is-disabled) {
  transform: translateY(-2px);
  box-shadow: 0 10px 24px rgba(20, 66, 211, 0.3) !important;
}

.brand-btn-primary.is-disabled {
  background: var(--lavender) !important;
  box-shadow: none !important;
  opacity: 0.7;
}

.brand-btn-outline {
  background: #FFF !important;
  border: 1px solid var(--primary-blue) !important;
  color: var(--primary-blue) !important;
  border-radius: 12px !important;
  font-weight: 700 !important;
  padding: 10px 24px !important;
  transition: all 0.3s ease !important;
}

.brand-btn-outline:hover {
  background: var(--light-blue) !important;
  color: var(--dark-blue) !important;
}

.polish-hint {
  font-size: 13px;
  color: var(--lavender);
  font-weight: 600;
}

/* 语音输入动画 */
.is-listening {
  color: var(--primary-blue) !important;
  animation: listeningPulse 1.5s infinite;
  background: rgba(48, 122, 227, 0.1);
  padding: 4px 10px !important;
  border-radius: 8px;
}

@keyframes listeningPulse {
  0% { transform: scale(1); box-shadow: 0 0 0 0 rgba(48, 122, 227, 0.4); }
  50% { transform: scale(1.05); box-shadow: 0 0 0 6px rgba(48, 122, 227, 0); }
  100% { transform: scale(1); box-shadow: 0 0 0 0 rgba(48, 122, 227, 0); }
}

/* 弹窗及输入框高级样式 */
:deep(.brand-dialog .el-dialog) {
  background: #FFFFFF;
  border-radius: 20px;
  border: 1px solid var(--light-blue);
  box-shadow: 0 24px 64px rgba(20, 66, 211, 0.15);
  overflow: hidden;
}

:deep(.brand-dialog .el-dialog__header) {
  padding: 24px;
  background: var(--bg-color);
  border-bottom: 1px solid var(--light-blue);
  margin-right: 0;
}

:deep(.brand-dialog .el-dialog__title) {
  font-size: 18px;
  font-weight: 800;
  color: var(--dark-blue);
}

:deep(.brand-dialog .el-dialog__body) {
  padding: 24px;
}

:deep(.brand-dialog .el-dialog__footer) {
  padding: 16px 24px 24px;
  background: var(--bg-color);
  border-top: 1px solid var(--light-blue);
}

.brand-form :deep(.el-form-item__label) {
  font-weight: 700;
  color: var(--dark-blue);
}

.brand-input :deep(.el-input__wrapper) {
  background: var(--bg-color) !important;
  border-radius: 12px !important;
  box-shadow: 0 0 0 1px var(--light-blue) inset !important;
  transition: all 0.3s;
}

.brand-input :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 2px var(--primary-blue) inset !important;
  background: #FFFFFF !important;
}

/* 移动端适配 */
@media (max-width: 768px) {
  .polish-panel {
    border-radius: 12px;
    margin-bottom: 12px;
  }
  .polish-panel-header {
    padding: 12px 14px;
  }
  .polish-panel-title {
    gap: 8px;
    flex-wrap: wrap;
  }
  .brand-icon {
    font-size: 16px;
  }
  .brand-title-text {
    font-size: 14px;
  }
  .range-tag {
    font-size: 11px;
    padding: 2px 6px;
  }
  .collapse-icon {
    font-size: 14px;
  }
  .polish-panel-body {
    padding: 14px 12px;
    gap: 16px;
  }
  .brand-label {
    font-size: 13px;
  }
  .section-label-row {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }
  .template-actions {
    width: 100%;
    justify-content: flex-start;
    gap: 4px;
    background: var(--bg-color);
    padding: 6px 8px;
    border-radius: 8px;
  }
  .brand-link-btn {
    font-size: 12px !important;
    padding: 4px 8px !important;
  }
  .range-controls {
    flex-direction: column;
    align-items: stretch;
    gap: 12px;
  }
  .brand-radio-group {
    width: 100%;
  }
  .brand-radio-group :deep(.el-radio-button__inner) {
    font-size: 12px;
    padding: 6px 10px;
  }
  .custom-range {
    width: 100%;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 6px;
    padding: 8px;
  }
  .brand-text {
    font-size: 12px;
  }
  .brand-input-number {
    width: 70px !important;
  }
  .brand-input-number :deep(.el-input__inner) {
    font-size: 12px;
  }
  .brand-textarea :deep(.el-textarea__inner) {
    font-size: 13px;
    padding: 10px;
    min-height: 80px;
  }
  .section-actions {
    gap: 12px;
    padding-top: 12px;
  }
  .progress-info {
    padding: 10px 12px;
    gap: 6px;
  }
  .progress-text {
    font-size: 12px;
  }
  .action-buttons {
    flex-direction: column;
    align-items: stretch;
    gap: 10px;
  }
  .brand-btn-primary, .brand-btn-outline {
    width: 100%;
    padding: 10px 16px !important;
    font-size: 13px;
  }
  .brand-btn-primary :deep(.el-icon), 
  .brand-btn-outline :deep(.el-icon) {
    font-size: 14px;
  }
  .polish-hint {
    text-align: center;
    font-size: 12px;
  }
  :deep(.brand-dialog .el-dialog) {
    width: 90% !important;
    border-radius: 12px;
  }
  :deep(.brand-dialog .el-dialog__header) {
    padding: 16px;
  }
  :deep(.brand-dialog .el-dialog__title) {
    font-size: 16px;
  }
  :deep(.brand-dialog .el-dialog__body) {
    padding: 16px;
  }
  :deep(.brand-dialog .el-dialog__footer) {
    padding: 12px 16px 16px;
  }
  .brand-form :deep(.el-form-item) {
    margin-bottom: 14px;
  }
  .brand-form :deep(.el-form-item__label) {
    font-size: 12px;
    width: 60px !important;
  }
}

@media (max-width: 480px) {
  .polish-panel {
    margin-bottom: 10px;
  }
  .polish-panel-header {
    padding: 10px 12px;
  }
  .brand-title-text {
    font-size: 13px;
  }
  .range-tag {
    font-size: 10px;
    padding: 2px 4px;
  }
  .polish-panel-body {
    padding: 12px 10px;
    gap: 14px;
  }
  .brand-label {
    font-size: 12px;
  }
  .brand-radio-group :deep(.el-radio-button__inner) {
    font-size: 11px;
    padding: 4px 8px;
  }
  .custom-range {
    padding: 6px;
  }
  .brand-input-number {
    width: 60px !important;
  }
  .brand-textarea :deep(.el-textarea__inner) {
    font-size: 12px;
    padding: 8px;
    min-height: 70px;
  }
  .brand-btn-primary, .brand-btn-outline {
    padding: 8px 12px !important;
    font-size: 12px;
  }
}
</style>