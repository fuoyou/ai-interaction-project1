<template>
  <div class="editor-container">
    <!-- 左侧：PDF 预览 -->
    <div class="left-panel" :style="{ flex: `0 0 ${leftPanelWidth}px` }">
      <!-- 合并点：使用 V1 的 glass-panel 样式 -->
      <div class="preview-card glass-panel">
        <div class="card-header">
          <span class="file-name">实时课件预览 (共 {{ pdfPageCount }} 页)</span>
        </div>
        
        <div class="pdf-stage">
          <!-- 合并点：使用 V1 的 glass-toolbar 样式 -->
          <div class="stage-toolbar glass-toolbar">
            <div class="zoom-controls">
              <el-button-group>
                <el-button size="small" :icon="ZoomOut" @click="handleZoom(-0.1)" class="brand-ctrl-btn" />
                <el-button size="small" class="zoom-text brand-ctrl-btn">{{ Math.round(scale * 100) }}%</el-button>
                <el-button size="small" :icon="ZoomIn" @click="handleZoom(0.1)" class="brand-ctrl-btn" />
              </el-button-group>
            </div>
            <div class="pdf-navigation" v-if="pdfPageCount > 0">
              <el-button size="small" :disabled="props.currentSlide === 0" @click="goToPrevPage" class="brand-ctrl-btn">← 上一页</el-button>
              <span class="page-info">{{ props.currentSlide + 1 }} / {{ pdfPageCount }}</span>
              <el-button size="small" :disabled="props.currentSlide >= pdfPageCount - 1" @click="goToNextPage" class="brand-ctrl-btn">下一页 →</el-button>
            </div>
            <span class="semantic-tag hide-on-mobile">已完成跨页语义关联</span>
          </div>

          <div class="pdf-page-view" ref="pdfViewRef">
            <template v-if="pdfSource && isPdfSource">
              <div style="display:none">
                <VuePdfEmbed :key="pdfSource" :source="pdfSource" @loaded="handlePdfLoaded" />
              </div>
              <div class="pdf-center-wrapper" v-if="pdfPageCount > 0">
                <div class="pdf-page-wrapper glass-page-shadow" :style="{ transform: `scale(${scale})`, transformOrigin: 'top center' }">
                  <LessonPdfCanvas
                    v-if="useBlockOverlay"
                    :pdf-url="pdfSource"
                    :page-num="props.currentSlide + 1"
                    :render-width="pdfRenderWidth"
                    :zoom="1"
                    :ocr-page="currentOcrPage"
                    :selected-block-id="selectedBlockId"
                    @block-click="onBlockClick"
                  />
                  <VuePdfEmbed
                    v-else
                    :key="pdfSource + '-' + (props.currentSlide + 1)"
                    :source="pdfSource"
                    :page="props.currentSlide + 1"
                    :width="pdfRenderWidth"
                    class="pdf-content"
                  />
                </div>
              </div>
            </template>
            <template v-else-if="pdfSource && isPptxSource">
              <div ref="pptxContainer" class="pptx-preview-container"></div>
            </template>
            <template v-else-if="pdfSource && isPptSource">
              <div class="placeholder">
                当前仅支持 `.pptx` 直预览；`.ppt` 请等待后台转换为 PDF 后查看。
              </div>
            </template>
            <div v-else class="placeholder">等待课件载入...</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 拖动分隔符：视觉上弱化，保留拖动 -->
    <div v-if="!isMobile" class="panel-divider" @mousedown="startDragDivider"></div>

    <!-- 右侧：脚本编辑 -->
    <!-- 合并点：使用 V1 的 glass-panel 样式 -->
    <div class="right-panel glass-panel" :style="{ flex: `1 1 auto` }">
      <div class="panel-tabs">
        <el-tabs v-model="activeTab" class="brand-tabs">
          <el-tab-pane :label="`讲课脚本 (${localSlides.length})`" name="script" />
          <el-tab-pane label="知识库" name="knowledge-base" />
          <el-tab-pane label="测验" name="quiz" />
          <el-tab-pane label="思维导图" name="mindmap" />
          <el-tab-pane label="知识图谱" name="knowledge" />
        </el-tabs>
      </div>
      
      <div class="scroll-area">
        <!-- 讲课脚本标签页 -->
        <div v-if="activeTab === 'script'">
          <div
            v-for="(item, index) in localSlides"
            :key="index"
            :id="`script-card-${index}`"
            :class="['script-card', 'glass-item', { active: props.currentSlide === index }]"
            @click="scrollToPage(index)"
          >
            <div class="card-meta">
              <span class="page-title">第 {{ index + 1 }} 页</span>
              <el-button v-if="item.audioUrl" link type="primary" size="small" :icon="Microphone" @click.stop="handleSpeak(item.audioUrl)">试听</el-button>
              <el-button v-else link type="primary" size="small" :icon="Microphone" @click.stop="handleTTS(item.script)">播放</el-button>
            </div>
            <div class="card-content">
              <el-input 
                v-if="props.currentSlide === index" 
                v-model="item.script" 
                type="textarea" 
                :autosize="{ minRows: 4, maxRows: 12 }"
                class="active-editor glass-textarea" 
                placeholder="AI 正在生成本页讲稿..."
                @input="handleScriptChange(index)"
              />
              <p v-else class="preview-text">{{ item.script || '（等待 AI 生成本页讲稿...）' }}</p>
            </div>
          </div>
        </div>

        <!-- 知识库标签页 -->
        <div v-else-if="activeTab === 'knowledge-base'" class="knowledge-base-container">
          <div v-if="loadingKnowledge" class="kb-loading">
            <el-icon class="is-loading" :size="24" color="#2196F3"><Loading /></el-icon>
            <span>正在加载知识库...</span>
          </div>
          <div v-else-if="!localCategoryKnowledge || localCategoryKnowledge.length === 0" class="kb-empty">
            <el-empty description="该分类暂无知识库资料" :image-size="60" />
            <p class="kb-tip">请在主页的分类中上传知识库资料，上传后AI将自动构建RAG索引</p>
          </div>
          <div v-else class="kb-content">
            <div class="kb-header">
              <div class="kb-header-left">
                <span class="kb-title">知识库资料</span>
                <span class="kb-count">共 {{ localCategoryKnowledge.length }} 个文件</span>
              </div>
              <div class="kb-header-right">
                <el-button link type="primary" size="small" @click="toggleAllKnowledge">
                  {{ selectedKnowledge.length === localCategoryKnowledge.length ? '取消全选' : '全选' }}
                </el-button>
                <span class="kb-selected-count">已选 {{ selectedKnowledge.length }} 个</span>
              </div>
            </div>
            <p class="kb-desc">勾选要结合的知识库资料，AI 将参考这些内容生成讲稿和测验题</p>
            <div class="kb-list">
              <div
                v-for="doc in localCategoryKnowledge"
                :key="doc.id"
                class="kb-item"
                :class="{ selected: selectedKnowledge.includes(doc.id) }"
                @click="toggleKnowledge(doc.id)"
              >
                <el-checkbox :model-value="selectedKnowledge.includes(doc.id)" @change="toggleKnowledge(doc.id)" @click.stop />
                <div class="kb-item-info">
                  <el-icon color="#67c23a"><DocumentCopy /></el-icon>
                  <div class="kb-item-text">
                    <span class="kb-item-name">{{ doc.name }}</span>
                    <span class="kb-item-meta">
                      <span v-if="doc.fileType" class="kb-item-type">{{ doc.fileType.toUpperCase() }}</span>
                      <span v-if="doc.hasRag" class="kb-item-rag">RAG已就绪</span>
                      <span v-else class="kb-item-rag kb-item-rag--pending">索引构建中</span>
                    </span>
                  </div>
                </div>
              </div>
            </div>
            <div class="kb-actions">
              <el-button
                type="primary"
                :loading="isGeneratingWithKB"
                :disabled="selectedKnowledge.length === 0"
                @click="generateScriptWithKnowledge"
              >
                <el-icon class="el-icon--left"><MagicStick /></el-icon>
                结合知识库生成讲稿
              </el-button>
              <p class="kb-hint" v-if="selectedKnowledge.length === 0">请至少勾选一个资料</p>
              <p class="kb-hint kb-hint--success" v-else>已选 {{ selectedKnowledge.length }} 个资料，生成测验题时将自动使用</p>
            </div>
          </div>
        </div>

        <!-- 测验标签页 - 新的测验管理组件 -->
        <div v-else-if="activeTab === 'quiz'" class="quiz-container">
          <Quiz :lesson-id="props.courseId" :knowledge-doc-ids="selectedKnowledge" />
        </div>

        <!-- 思维导图标签页 -->
        <div v-else-if="activeTab === 'mindmap'" class="mindmap-container">
          <div class="mindmap-content glass-item">
            <div v-if="!mindmapData" class="mindmap-placeholder">
              <el-icon class="mindmap-icon" size="48"><svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3v18h18"/><path d="M18 17V9"/><path d="M13 17V5"/><path d="M8 17v-3"/></svg></el-icon>
              <h3>思维导图</h3>
              <p>基于当前课件内容生成的结构化思维导图</p>
              <el-button type="primary" size="small" @click="generateMindmap" :loading="isGeneratingMindmap">生成思维导图</el-button>
            </div>
            <div v-else class="mindmap-visualization">
              <div class="mindmap-loading" v-if="isGeneratingMindmap">
                <el-icon class="is-loading"><Loading /></el-icon>
                <span>正在生成思维导图...</span>
              </div>
              <div v-else class="mindmap-canvas">
                <!-- 合并点：使用 V2 强大的自适应 SVG -->
                <svg class="mindmap-svg" :viewBox="computedMindmapViewBox" preserveAspectRatio="xMidYMid meet" @wheel="handleSvgWheel">
                  <g class="mindmap-lines">
                    <path v-for="(branch, index) in mindmapData.branches" 
                          :key="'line-'+index"
                          :d="getBranchLinePath(branch)"
                          :stroke="branch.color"
                          stroke-width="2.5"
                          fill="none"
                          class="mindmap-line"
                    />
                    <path v-for="(line, index) in subLines" 
                          :key="'subline-'+index"
                          :d="line.path"
                          :stroke="line.color"
                          stroke-width="1.5"
                          fill="none"
                          class="mindmap-line"
                    />
                  </g>
                  <g v-if="mindmapData.center" class="mindmap-center">
                    <rect 
                      :x="mindmapData.center.x - mindmapData.center.width / 2" 
                      :y="mindmapData.center.y - mindmapData.center.height / 2"
                      :width="mindmapData.center.width"
                      :height="mindmapData.center.height"
                      rx="15" ry="15" 
                      fill="#2196F3" 
                      class="mindmap-center-node" />
                    <text 
                      :x="mindmapData.center.x" 
                      :y="mindmapData.center.y" 
                      text-anchor="middle" 
                      dominant-baseline="middle"
                    >{{ mindmapData.center.label }}</text>
                  </g>
                  <g v-for="(branch, index) in mindmapData.branches" :key="'branch-'+index" class="mindmap-branch">
                    <rect 
                      :x="branch.x - branch.width / 2" 
                      :y="branch.y - branch.height / 2"
                      :width="branch.width"
                      :height="branch.height"
                      rx="25" ry="25"
                      :fill="branch.color" 
                      class="mindmap-branch-node"/>
                    <text 
                      :x="branch.x" 
                      :y="branch.y" 
                      text-anchor="middle"
                      dominant-baseline="middle" 
                    >{{ branch.label }}</text>
                    <g v-for="(sub, subIndex) in branch.children" :key="'sub-'+index+'-'+subIndex" class="mindmap-sub">
                      <text 
                        :x="sub.x" 
                        :y="sub.y" 
                        text-anchor="start"
                        dominant-baseline="middle"
                      >{{ sub.label }}</text>
                    </g>
                  </g>
                </svg>
              </div>
            </div>
          </div>
        </div>
        
        <!-- 知识图谱标签页 -->
        <div v-else-if="activeTab === 'knowledge'" class="knowledge-graph-container">
          <div class="knowledge-graph-content glass-item">
            <div v-if="!knowledgeGraphData" class="knowledge-graph-placeholder">
              <el-icon class="knowledge-graph-icon" size="48"><svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="18" cy="5" r="3"></circle><circle cx="6" cy="12" r="3"></circle><circle cx="18" cy="19" r="3"></circle><line x1="8.59" y1="13.51" x2="15.42" y2="17.49"></line><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"></line></svg></el-icon>
              <h3>知识图谱</h3>
              <p>基于当前课件内容生成的关联知识网络</p>
              <el-button type="primary" size="small" @click="generateKnowledgeGraph" :loading="isGeneratingGraph">生成知识图谱</el-button>
            </div>
            <div v-else class="knowledge-graph-visualization">
              <div class="knowledge-graph-loading" v-if="isGeneratingGraph">
                <el-icon class="is-loading"><Loading /></el-icon>
                <span>正在生成知识图谱...</span>
              </div>
              <div v-else class="knowledge-graph-canvas">
                <!-- 合并点：使用 V2 的自适应 SVG 和布局引擎 -->
                <svg class="knowledge-graph-svg" :viewBox="computedGraphViewBox" preserveAspectRatio="xMidYMid meet" @wheel="handleSvgWheel">
                  <!-- 连线 -->
                  <g class="knowledge-graph-edges">
                    <g v-for="(edge, index) in knowledgeGraphData.edges" :key="'edge-'+index">
                      <line 
                        :x1="edge.x1" :y1="edge.y1" 
                        :x2="edge.x2" :y2="edge.y2" 
                        stroke="#BDBDBD" stroke-width="2" 
                        class="knowledge-graph-line"
                      />
                      <!-- 连线标签 -->
                      <g v-if="edge.label" :transform="`translate(${edge.mx}, ${edge.my}) rotate(${edge.angle})`">
                        <text text-anchor="middle" dominant-baseline="central" font-size="14" fill="none" stroke="#ffffff" stroke-width="5" stroke-linejoin="round">{{ edge.label }}</text>
                        <text text-anchor="middle" dominant-baseline="central" font-size="14" fill="#666666" class="edge-text">{{ edge.label }}</text>
                      </g>
                    </g>
                  </g>
                  <!-- 节点 -->
                  <g class="knowledge-graph-nodes">
                    <g v-for="node in knowledgeGraphData.nodes" :key="'node-'+node.id" class="knowledge-graph-node">
                      <circle :cx="node.x" :cy="node.y" :r="node.size" :fill="node.color" class="knowledge-graph-node-circle" />
                      <text :x="node.x" :y="node.y" text-anchor="middle" dominant-baseline="central" :fill="node.textColor" font-size="16" font-weight="600">
                        <tspan v-for="(line, i) in node.lines" :key="i" :x="node.x" :dy="i === 0 ? (node.lines.length === 1 ? 0 : -10) : 20">
                          {{ line }}
                        </tspan>
                      </text>
                    </g>
                  </g>
                </svg>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 批量润色面板（固定在底部）-->
      <div v-if="activeTab === 'script'" class="polish-panel-wrapper">
        <PolishPanel
          :total-pages="localSlides.length"
          :current-page="props.currentSlide"
          :slides="localSlides"
          :course-id="props.courseId"
          @update:slides="onPolishUpdate"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onUnmounted, onMounted, nextTick, computed } from 'vue'
import VuePdfEmbed from 'vue-pdf-embed'
import LessonPdfCanvas from '@/components/LessonPdfCanvas.vue'
import { init as initPptxPreview } from 'pptx-preview'
import { Microphone, Loading, ZoomIn, ZoomOut, DocumentCopy } from '@element-plus/icons-vue'
import { ElMessage, ElLoading } from 'element-plus'
import { polishPage, generateSingleTTS } from '@/api/course'
import { getMindmap, getKnowledgeGraph, generateQuiz, listKnowledgeDocs, regenerateScriptWithKnowledge, getRegenerateStatus } from '@/api/lesson'
import Quiz from '../Quiz.vue'
import PolishPanel from './PolishPanel.vue'

const props = defineProps(['pdfSource', 'slides', 'currentSlide', 'courseId', 'categoryKnowledge', 'categoryId', 'paddlePages'])
const emit = defineEmits(['update:currentSlide', 'update:slides'])

// 拖动分隔符相关
const leftPanelWidth = ref(600)
let isDragging = false
let startX = 0

// 移动端检测
const isMobile = ref(false)

const checkMobile = () => {
  isMobile.value = window.innerWidth <= 768
}

const initializePanelWidth = () => {
  if (!isMobile.value) {
    const containerWidth = window.innerWidth - 32
    leftPanelWidth.value = Math.max(400, Math.floor(containerWidth / 2))
  }
}

const onWindowResizeLayout = () => {
  checkMobile()
  initializePanelWidth()
}

onMounted(() => {
  onWindowResizeLayout()
  window.addEventListener('resize', onWindowResizeLayout)
  window.addEventListener('resize', handleWindowResize)
  updatePdfRenderWidth()
  containerObserver = new ResizeObserver(() => handleWindowResize())
  if (pptxContainer.value) containerObserver.observe(pptxContainer.value)
  if (pdfViewRef.value) containerObserver.observe(pdfViewRef.value)
})

const startDragDivider = (e) => {
  isDragging = true
  startX = e.clientX
  document.addEventListener('mousemove', handleDragDivider)
  document.addEventListener('mouseup', stopDragDivider)
}

const handleDragDivider = (e) => {
  if (!isDragging) return
  const delta = e.clientX - startX
  const newWidth = Math.max(400, Math.min(leftPanelWidth.value + delta, window.innerWidth - 300))
  leftPanelWidth.value = newWidth
  startX = e.clientX
}

const stopDragDivider = () => {
  isDragging = false
  document.removeEventListener('mousemove', handleDragDivider)
  document.removeEventListener('mouseup', stopDragDivider)
}

const activeTab = ref('script')
const pdfPageCount = ref(0)
const localSlides = ref([]) 
const scale = ref(1.0)
const currentAudio = ref(null)
const pptxContainer = ref(null)
const pdfViewRef = ref(null)
const pdfRenderWidth = ref(900)

const mindmapData = ref(null)
const isGeneratingMindmap = ref(false)
const knowledgeGraphData = ref(null)
const isGeneratingGraph = ref(false)

let pptxPreviewer = null
let isSyncing = false 
let resizeTimer = null
let measureRetryTimer = null
let containerObserver = null
let autoFitDone = false 
let pdfAspectRatio = null 

// 根据容器尺寸和 PDF 宽高比，计算让幻灯片恰好填满容器的渲染宽度
const recalcPdfWidth = () => {
  if (!pdfViewRef.value) return
  const rect = pdfViewRef.value.getBoundingClientRect()
  if (rect.width < 10 || rect.height < 10) return
  const pad = 24 
  if (pdfAspectRatio) {
    const maxByWidth = Math.floor(rect.width - pad)
    const maxByHeight = Math.floor((rect.height - pad) * pdfAspectRatio)
    pdfRenderWidth.value = Math.max(Math.min(maxByWidth, maxByHeight), 300)
  } else {
    pdfRenderWidth.value = Math.floor(rect.width - pad)
  }
}

// PDF @loaded 后读取真实宽高比，再精确计算渲染宽度
const autoFitPdfWidth = async (doc) => {
  if (autoFitDone) return
  autoFitDone = true
  try {
    const page = await doc.getPage(1)
    const viewport = page.getViewport({ scale: 1 })
    pdfAspectRatio = viewport.width / viewport.height
    recalcPdfWidth()
  } catch (e) {
    console.error('PDF auto-fit error', e)
  }
}

const updatePdfRenderWidth = recalcPdfWidth

const isPdfSource = computed(() => String(props.pdfSource || '').toLowerCase().endsWith('.pdf'))
const paddlePagesList = computed(() => (Array.isArray(props.paddlePages) ? props.paddlePages : []))
const useBlockOverlay = computed(() => isPdfSource.value && paddlePagesList.value.length > 0)
const currentOcrPage = computed(() => paddlePagesList.value.find((p) => p.page_num === props.currentSlide + 1) ?? null)
const selectedBlockId = ref(null)

const onBlockClick = (block) => {
  selectedBlockId.value = block?.id || null
}
const isPptxSource = computed(() => String(props.pdfSource || '').toLowerCase().endsWith('.pptx'))
const isPptSource = computed(() => String(props.pdfSource || '').toLowerCase().endsWith('.ppt'))

const renderPptxPreview = async () => {
  if (!isPptxSource.value || !pptxContainer.value || !props.pdfSource) return
  try {
    const rect = pptxContainer.value.getBoundingClientRect()
    if (rect.width < 300 || rect.height < 240) {
      if (measureRetryTimer) clearTimeout(measureRetryTimer)
      measureRetryTimer = setTimeout(() => renderPptxPreview(), 220)
      return
    }

    pptxContainer.value.innerHTML = ''
    const containerWidth = Math.max(640, Math.floor(rect.width - 8))
    const maxHeight = Math.max(420, Math.floor(rect.height - 8))
    const fitHeight = Math.min(maxHeight, Math.floor((containerWidth * 9) / 16))
    pptxPreviewer = initPptxPreview(pptxContainer.value, {
      width: containerWidth,
      height: fitHeight,
      mode: 'list'
    })
    const resp = await fetch(props.pdfSource)
    const buf = await resp.arrayBuffer()
    await pptxPreviewer.preview(buf)
  } catch (e) {
    console.error('[PPTX预览] 失败:', e)
    ElMessage.warning('PPTX 直预览失败，请等待后台转换为 PDF')
  }
}

const handleWindowResize = () => {
  if (resizeTimer) clearTimeout(resizeTimer)
  resizeTimer = setTimeout(() => {
    if (isPptxSource.value) {
      renderPptxPreview()
    } else if (isPdfSource.value) {
      recalcPdfWidth() 
    }
  }, 180)
}

const syncSlidesData = () => {
  if (isSyncing) return
  isSyncing = true
  
  const serverSlides = props.slides || []
  const targetCount = Math.max(pdfPageCount.value, serverSlides.length)
  
  if (localSlides.value.length === 0 && serverSlides.length > 0) {
    localSlides.value = serverSlides.map(s => ({
      page: s.page,
      script: s.script || '',
      audioUrl: s.audioUrl || ''
    }))
  } else {
    if (localSlides.value.length < targetCount) {
      for (let i = localSlides.value.length; i < targetCount; i++) {
        localSlides.value.push({ page: i + 1, script: '', audioUrl: '' })
      }
    }
    
    serverSlides.forEach((s, i) => {
      if (localSlides.value[i]) {
        if (!localSlides.value[i].script && s.script) {
          localSlides.value[i].script = s.script
        }
        if (s.audioUrl) {
          localSlides.value[i].audioUrl = s.audioUrl
        }
      }
    })
  }
  
  nextTick(() => { isSyncing = false })
}

const handleScriptChange = (index) => {
  if (!isSyncing) {
    emit('update:slides', [...localSlides.value])
  }
}

watch(() => props.pdfSource, async () => { 
  pdfPageCount.value = 0
  localSlides.value = []
  scale.value = 1.0
  autoFitDone = false   
  pdfAspectRatio = null 
  await nextTick()
  if (isPptxSource.value) {
    await renderPptxPreview()
  } else if (isPdfSource.value) {
    updatePdfRenderWidth() 
  }
}, { immediate: true })

watch(() => props.slides, syncSlidesData, { deep: true })
watch(pdfPageCount, syncSlidesData)

watch(() => props.currentSlide, (newSlide) => {
  if (newSlide >= 0) {
    nextTick(() => {
      const el = document.getElementById(`script-card-${newSlide}`)
      if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' })
    })
  }
})

const handlePdfLoaded = async (doc) => {
  pdfPageCount.value = doc.numPages
  await autoFitPdfWidth(doc)
}
const handleZoom = (d) => { if (scale.value + d >= 0.5 && scale.value + d <= 2.5) scale.value = Number((scale.value + d).toFixed(1)) }
const goToPrevPage = () => { if (props.currentSlide > 0) scrollToPage(props.currentSlide - 1) }
const goToNextPage = () => { if (props.currentSlide < pdfPageCount.value - 1) scrollToPage(props.currentSlide + 1) }
const scrollToPage = (index) => {
  emit('update:currentSlide', index)
  nextTick(() => {
    const el = document.getElementById(`script-card-${index}`)
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' })
  })
}
const handleSpeak = (url) => {
  if (currentAudio.value) currentAudio.value.pause()
  currentAudio.value = new Audio(url); currentAudio.value.play()
}
const handleTTS = async (text) => {
  if (!text) {
    ElMessage.warning('暂无讲稿内容')
    return
  }
  try {
    ElMessage.info('正在生成语音...')
    const res = await generateSingleTTS(text)
    if (res.data?.audioUrl) {
      handleSpeak(res.data.audioUrl)
      ElMessage.success('语音已生成')
    } else {
      ElMessage.error('语音生成失败')
    }
  } catch (e) {
    ElMessage.error('语音生成失败')
  }
}

// 测验相关状态
const quizData = ref([])
const isGeneratingQuiz = ref(false)
const editingQuestionIndex = ref(-1)

const generateQuizQuestions = async () => {
  if (!props.courseId) { ElMessage.warning('请先选择课件'); return }
  isGeneratingQuiz.value = true
  try {
    const res = await generateQuiz(props.courseId, { questionCount: 10 })
    if (res.data && res.data.questions && res.data.questions.length > 0) {
      quizData.value = res.data.questions.map(q => ({
        type: q.type || 'multiple_choice',
        content: q.content || q.question || '',
        options: q.options || [],
        answer: q.answer || '',
        explanation: q.explanation || ''
      }))
      ElMessage.success('测验题目生成成功')
    } else {
      ElMessage.warning('暂无生成的题目')
    }
  } catch (e) {
    console.error('生成测验失败:', e)
    ElMessage.error('生成测验失败，请重试')
  } finally {
    isGeneratingQuiz.value = false
  }
}

const getQuestionTypeLabel = (type) => {
  const map = {
    'multiple_choice': '选择题',
    'fill_blank': '填空题',
    'true_false': '判断题',
    'short_answer': '问答题'
  }
  return map[type] || type
}

const deleteQuestion = (index) => {
  quizData.value.splice(index, 1)
  ElMessage.success('题目已删除')
}

const saveQuiz = () => {
  if (quizData.value.length === 0) { ElMessage.warning('请先生成测验题目'); return }
  // 保存到 localStorage
  const key = `quiz_${props.courseId}`
  localStorage.setItem(key, JSON.stringify(quizData.value))
  ElMessage.success('测验已保存')
}

const exportQuiz = () => {
  if (quizData.value.length === 0) { ElMessage.warning('请先生成测验题目'); return }
  // 简单的文本导出，实际可集成 docx 库
  let content = '测验题目\n\n'
  quizData.value.forEach((q, i) => {
    content += `第${i + 1}题 (${getQuestionTypeLabel(q.type)})\n`
    content += `${q.content}\n`
    if (q.options && q.options.length > 0) {
      q.options.forEach((opt, j) => {
        content += `${String.fromCharCode(65 + j)}. ${opt}\n`
      })
    }
    content += `答案：${q.answer}\n`
    if (q.explanation) content += `解析：${q.explanation}\n`
    content += '\n'
  })
  const blob = new Blob([content], { type: 'text/plain' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `quiz_${props.courseId}.txt`
  a.click()
  URL.revokeObjectURL(url)
  ElMessage.success('已导出为文本文件')
}

// 批量润色更新回调
const onPolishUpdate = (updatedSlides) => {
  localSlides.value = updatedSlides
  emit('update:slides', [...updatedSlides])
}

// 知识库选择状态
const selectedKnowledge = ref([])       // 已勾选的文档ID列表
const isGeneratingWithKB = ref(false)
const localCategoryKnowledge = ref([])  // 从后端加载的知识库文档列表
const loadingKnowledge = ref(false)

// localStorage key: 与课件ID绑定，记忆勾选状态
const getKbSelectionKey = () => `kb_selection_${props.courseId}`

// 从后端加载当前分类的知识库文档
const loadKnowledgeDocs = async () => {
  const catId = props.categoryId
  if (!catId || catId === 'uncategorized') {
    localCategoryKnowledge.value = []
    return
  }
  loadingKnowledge.value = true
  try {
    const res = await listKnowledgeDocs(catId)
    localCategoryKnowledge.value = res.data || []
    // 恢复上次的勾选状态
    const saved = localStorage.getItem(getKbSelectionKey())
    if (saved) {
      try {
        const savedIds = JSON.parse(saved)
        // 只保留仍然存在的文档ID
        const validIds = localCategoryKnowledge.value.map(d => d.id)
        selectedKnowledge.value = savedIds.filter(id => validIds.includes(id))
      } catch (e) {
        selectedKnowledge.value = []
      }
    } else {
      // 默认全选
      selectedKnowledge.value = localCategoryKnowledge.value.map(d => d.id)
    }
  } catch (e) {
    console.error('[知识库] 加载失败:', e)
    localCategoryKnowledge.value = []
  } finally {
    loadingKnowledge.value = false
  }
}

// 切换勾选并持久化
const toggleKnowledge = (docId) => {
  const idx = selectedKnowledge.value.indexOf(docId)
  if (idx === -1) {
    selectedKnowledge.value.push(docId)
  } else {
    selectedKnowledge.value.splice(idx, 1)
  }
  // 持久化到 localStorage
  localStorage.setItem(getKbSelectionKey(), JSON.stringify(selectedKnowledge.value))
}

// 全选 / 取消全选
const toggleAllKnowledge = () => {
  if (selectedKnowledge.value.length === localCategoryKnowledge.value.length) {
    selectedKnowledge.value = []
  } else {
    selectedKnowledge.value = localCategoryKnowledge.value.map(d => d.id)
  }
  localStorage.setItem(getKbSelectionKey(), JSON.stringify(selectedKnowledge.value))
}

// 当 categoryId 或 courseId 变化时重新加载知识库
watch(() => [props.categoryId, props.courseId], () => {
  loadKnowledgeDocs()
}, { immediate: true })

const generateScriptWithKnowledge = async () => {
  if (!props.courseId) { ElMessage.warning('请先选择课件'); return }
  if (selectedKnowledge.value.length === 0) { ElMessage.warning('请至少勾选一个知识库资料'); return }

  isGeneratingWithKB.value = true
  try {
    // 发起后端异步任务
    const res = await regenerateScriptWithKnowledge(props.courseId, selectedKnowledge.value)
    
    // 开始轮询
    let pollCount = 0
    const maxPolls = 300 // 最多轮询5分钟（每秒一次）
    const pollInterval = setInterval(async () => {
      pollCount++
      if (pollCount > maxPolls) {
        clearInterval(pollInterval)
        isGeneratingWithKB.value = false
        ElMessage.error('讲稿生成超时，请稍后重试')
        return
      }
      
      try {
        const statusRes = await getRegenerateStatus(props.courseId)
        const { taskStatus, script } = statusRes.data
        
        // 实时更新讲稿显示（逐页更新）
        if (script && Array.isArray(script) && script.length > 0) {
          localSlides.value = script.map(item => ({
            page: item.page,
            script: item.content || '',
            audioUrl: ''
          }))
          emit('update:slides', [...localSlides.value])
        }
        
        if (taskStatus === 'regen_completed') {
          clearInterval(pollInterval)
          ElMessage.success('讲稿已更新')
          activeTab.value = 'script'
          isGeneratingWithKB.value = false
        } else if (taskStatus === 'regen_failed') {
          clearInterval(pollInterval)
          isGeneratingWithKB.value = false
          ElMessage.error('讲稿生成失败，请重试')
        }
        // 其他状态继续轮询，不显示进度提示
      } catch (e) {
        console.error('轮询失败:', e)
      }
    }, 1000)
    
  } catch (e) {
    isGeneratingWithKB.value = false
    ElMessage.error('提交任务失败: ' + (e.message || '请重试'))
  }
}

// --- V2 思维导图核心算法 ---
const convertMindmapData = (backendData) => {
  if (!backendData || !backendData.root) return null;
  const root = backendData.root;
  const colors = ['#307AE3', '#ACB1EC', '#73B4E3', '#1442D3', '#D2E6FE'];
  const calcWidth = (text) => Math.max(140, (text.length * 16) + 40);

  const numBranches = root.children ? root.children.length : 0;
  const ySpacing = 120;
  const totalHeight = ySpacing * (numBranches - 1);
  const startY = (600 - totalHeight) / 2;

  const branches = root.children ? root.children.map((child, index) => {
    const label = child.text || child.label || '分支';
    const branchWidth = calcWidth(label); 
    const branchX = 450;
    const branchY = startY + index * ySpacing;
    
    const children = child.children ? child.children.map((sub, subIndex) => {
        const numChildren = child.children.length;
        const childYOffset = (subIndex - (numChildren - 1) / 2) * 25;
        return {
            x: branchX + (branchWidth / 2) + 60, 
            y: branchY + childYOffset,
            label: sub.text || sub.label || '子项'
        };
    }) : [];
    
    return {
      x: branchX, y: branchY, width: branchWidth, height: 45,
      label: label, color: colors[index % colors.length], children: children
    };
  }) : [];
  
  return {
    center: {
      label: root.text || root.label || '课件主题',
      x: 160, y: 300, width: Math.min(260, (root.text?.length || 8) * 16 + 40), height: 60
    },
    branches: branches
  };
};

const getBranchLinePath = (branch) => {
    if (!mindmapData.value || !mindmapData.value.center) return '';
    const center = mindmapData.value.center;
    const startX = center.x + (center.width / 2);
    const startY = center.y;
    const endX = branch.x - (branch.width / 2);
    const endY = branch.y;
    const c1x = startX + (endX - startX) * 0.5;
    const c1y = startY;
    const c2x = startX + (endX - startX) * 0.5;
    const c2y = endY;
    return `M ${startX} ${startY} C ${c1x} ${c1y}, ${c2x} ${c2y}, ${endX} ${endY}`;
};

const subLines = computed(() => {
    if (!mindmapData.value) return [];
    const lines = [];
    mindmapData.value.branches.forEach(branch => {
        if (branch.children) {
            const startX = branch.x + branch.width / 2;
            const startY = branch.y;
            branch.children.forEach(child => {
                const endX = child.x - 5;
                const endY = child.y;
                const c1x = startX + 40;
                const c1y = startY;
                const c2x = endX - 40;
                const c2y = endY;
                lines.push({
                    path: `M ${startX} ${startY} C ${c1x} ${c1y}, ${c2x} ${c2y}, ${endX} ${endY}`,
                    color: branch.color
                });
            });
        }
    });
    return lines;
});

const computedMindmapViewBox = computed(() => {
    if (!mindmapData.value) return '0 0 1000 600';
    
    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    
    const center = mindmapData.value.center;
    minX = Math.min(minX, center.x - center.width / 2);
    maxX = Math.max(maxX, center.x + center.width / 2);
    minY = Math.min(minY, center.y - center.height / 2);
    maxY = Math.max(maxY, center.y + center.height / 2);
    
    mindmapData.value.branches.forEach(branch => {
        minX = Math.min(minX, branch.x - branch.width / 2);
        maxX = Math.max(maxX, branch.x + branch.width / 2);
        minY = Math.min(minY, branch.y - branch.height / 2);
        maxY = Math.max(maxY, branch.y + branch.height / 2);
        
        if (branch.children) {
            branch.children.forEach(sub => {
                const textWidth = (sub.label || '').length * 16; 
                maxX = Math.max(maxX, sub.x + textWidth);
                minY = Math.min(minY, sub.y - 15);
                maxY = Math.max(maxY, sub.y + 15);
            });
        }
    });
    
    const padding = 80;
    let w = maxX - minX + padding * 2;
    let h = maxY - minY + padding * 2;
    
    w = Math.max(w, 800);
    h = Math.max(h, 500);
    
    const cx = (minX + maxX) / 2;
    const cy = (minY + maxY) / 2;
    
    return `${cx - w/2} ${cy - h/2} ${w} ${h}`;
});

const generateMindmap = async () => {
  if (!props.courseId) { ElMessage.warning('请先选择课程'); return; }
  isGeneratingMindmap.value = true
  try {
    const res = await getMindmap(props.courseId)
    if (res.data) {
      mindmapData.value = convertMindmapData(res.data)
      ElMessage.success('思维导图生成成功')
    } else {
      ElMessage.warning('暂无思维导图数据')
    }
  } catch (e) {
    ElMessage.error('生成思维导图失败')
  } finally {
    isGeneratingMindmap.value = false
  }
}

// --- V2 知识图谱核心算法 (力导向布局防重叠) ---
const convertKnowledgeGraphData = (backendData) => {
  if (!backendData || !backendData.nodes || backendData.nodes.length === 0) return null;
  const rawNodes = backendData.nodes;
  const rawEdges = backendData.edges || [];

  const colors = ['#307AE3', '#ACB1EC', '#73B4E3', '#1442D3', '#D2E6FE'];
  const nodesMap = {};
  
  const degreeMap = {};
  rawNodes.forEach(n => degreeMap[n.id] = 0);
  rawEdges.forEach(e => {
      if(degreeMap[e.source] !== undefined) degreeMap[e.source]++;
      if(degreeMap[e.target] !== undefined) degreeMap[e.target]++;
  });

  let rootId = rawNodes[0].id;
  let maxDegree = -1;
  for (const id in degreeMap) {
      if (degreeMap[id] > maxDegree) { maxDegree = degreeMap[id]; rootId = id; }
  }

  rawNodes.forEach(n => { nodesMap[n.id] = { ...n, level: 99, children: [] }; });
  nodesMap[rootId].level = 0;
  const queue = [rootId];
  while (queue.length > 0) {
      const currentId = queue.shift();
      const currentLevel = nodesMap[currentId].level;
      rawEdges.forEach(e => {
          let neighborId = null;
          if (e.source === currentId) neighborId = e.target;
          else if (e.target === currentId) neighborId = e.source;

          if (neighborId && nodesMap[neighborId] && nodesMap[neighborId].level > currentLevel + 1) {
              nodesMap[neighborId].level = currentLevel + 1;
              nodesMap[neighborId].parentId = currentId;
              nodesMap[currentId].children.push(neighborId);
              queue.push(neighborId);
          }
      });
  }

  const formatTextLines = (text) => {
      if (!text) return [];
      if (text.length <= 4) return [text];
      const mid = Math.ceil(text.length / 2);
      return [text.slice(0, mid), text.slice(mid)];
  };

  const getTextColor = (hexColor) => hexColor === '#F3D288' ? '#333333' : '#FFFFFF';

  const nodes = [];
  rawNodes.forEach(rawNode => {
      const node = nodesMap[rawNode.id];
      node.x = 400 + (Math.random() - 0.5) * 400;
      node.y = 300 + (Math.random() - 0.5) * 400;
      node.vx = 0;
      node.vy = 0;
      
      if (node.level === 0) {
          node.size = 85; 
          node.color = '#83B2D5'; 
      } else if (node.level === 1) {
          node.size = 65;
          const siblings = rawNodes.filter(n => nodesMap[n.id].level === 1);
          const index = siblings.findIndex(n => n.id === node.id);
          node.assignedColor = colors[index % colors.length];
          node.color = node.assignedColor;
      } else {
          node.size = 50;
          const parent = nodesMap[node.parentId] || nodesMap[rootId];
          node.color = parent.assignedColor || '#83B2D5';
      }
      
      node.textColor = getTextColor(node.color);
      node.lines = formatTextLines(node.name || node.label || '未命名');
      nodes.push(node);
  });

  const iterations = 150; 
  const k = 220; 
  const centerGravity = 0.02; 
  
  for (let i = 0; i < iterations; i++) {
      const temp = 1 - i / iterations; 
      
      for (let j = 0; j < nodes.length; j++) {
          for (let m = j + 1; m < nodes.length; m++) {
              let u = nodes[j];
              let v = nodes[m];
              let dx = u.x - v.x;
              let dy = u.y - v.y;
              let dist = Math.sqrt(dx * dx + dy * dy);
              if (dist === 0) dist = 0.1; 
              
              let minAllowedDist = u.size + v.size + 40; 
              if (dist < minAllowedDist * 2.5) {
                  let f = (k * k) / dist; 
                  if (dist < minAllowedDist) f *= 8; 
                  
                  let fx = (dx / dist) * f;
                  let fy = (dy / dist) * f;
                  u.vx += fx; u.vy += fy;
                  v.vx -= fx; v.vy -= fy;
              }
          }
      }

      rawEdges.forEach(e => {
          let u = nodesMap[e.source];
          let v = nodesMap[e.target];
          if(u && v) {
              let dx = v.x - u.x;
              let dy = v.y - u.y;
              let dist = Math.sqrt(dx * dx + dy * dy);
              if (dist === 0) dist = 0.1;
              
              let f = (dist * dist) / (k * 1.5);
              let fx = (dx / dist) * f;
              let fy = (dy / dist) * f;
              u.vx += fx; u.vy += fy;
              v.vx -= fx; v.vy -= fy;
          }
      });

      nodes.forEach(u => {
          u.vx += (400 - u.x) * centerGravity;
          u.vy += (300 - u.y) * centerGravity;
          
          let speed = Math.sqrt(u.vx * u.vx + u.vy * u.vy);
          let maxMove = 40 * temp;
          if (speed > maxMove) {
              u.vx = (u.vx / speed) * maxMove;
              u.vy = (u.vy / speed) * maxMove;
          }
          u.x += u.vx;
          u.y += u.vy;
          u.vx = 0; u.vy = 0;
      });
  }

  const processedEdges = rawEdges.map(e => {
      const sourceNode = nodesMap[e.source];
      const targetNode = nodesMap[e.target];
      if(!sourceNode || !targetNode) return null;

      const x1 = sourceNode.x, y1 = sourceNode.y;
      const x2 = targetNode.x, y2 = targetNode.y;
      const mx = (x1 + x2) / 2;
      const my = (y1 + y2) / 2;
      
      let angle = Math.atan2(y2 - y1, x2 - x1) * 180 / Math.PI;
      if (angle > 90 || angle < -90) angle += 180;

      return {
          id: `${e.source}-${e.target}`,
          x1, y1, x2, y2, mx, my, angle,
          label: e.label || e.relation || e.name || ''
      };
  }).filter(e => e !== null);

  return { nodes, edges: processedEdges };
}

const computedGraphViewBox = computed(() => {
    if (!knowledgeGraphData.value || !knowledgeGraphData.value.nodes.length) {
        return '0 0 800 600';
    }
    const nodes = knowledgeGraphData.value.nodes;
    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    
    nodes.forEach(n => {
        if (n.x - n.size < minX) minX = n.x - n.size;
        if (n.x + n.size > maxX) maxX = n.x + n.size;
        if (n.y - n.size < minY) minY = n.y - n.size;
        if (n.y + n.size > maxY) maxY = n.y + n.size;
    });
    
    if (minX === Infinity) return '0 0 800 600';
    
    const padding = 120;
    let w = maxX - minX + padding * 2;
    let h = maxY - minY + padding * 2;
    
    w = Math.max(w, 800);
    h = Math.max(h, 600);
    
    const cx = (minX + maxX) / 2;
    const cy = (minY + maxY) / 2;
    return `${cx - w/2} ${cy - h/2} ${w} ${h}`;
});

const generateKnowledgeGraph = async () => {
  if (!props.courseId) { ElMessage.warning('请先选择课程'); return }
  isGeneratingGraph.value = true
  try {
    const res = await getKnowledgeGraph(props.courseId)
    if (res.data && res.data.nodes && res.data.nodes.length > 0) {
      knowledgeGraphData.value = convertKnowledgeGraphData(res.data)
      ElMessage.success('知识图谱生成成功')
    } else {
      ElMessage.warning('暂无知识图谱数据')
    }
  } catch (e) {
    ElMessage.error('生成知识图谱失败')
  } finally {
    isGeneratingGraph.value = false
  }
}

// 通用 SVG 缩放支持
let svgScaleValue = 1
const handleSvgWheel = (e) => {
  if (e.ctrlKey || e.metaKey) {
    e.preventDefault()
    const svg = e.target.closest('svg')
    if (svg) {
      svgScaleValue += e.deltaY > 0 ? -0.1 : 0.1
      svgScaleValue = Math.max(0.2, Math.min(svgScaleValue, 4)) 
      svg.style.transform = `scale(${svgScaleValue})`
      svg.style.transformOrigin = 'center'
    }
  }
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

const handlePolish = async (item, prompt = '') => {
  const loading = ElLoading.service({ target: '.right-panel' })
  try {
    let polishQuestion = '请帮我优化这段讲稿内容：\n' + item.script
    if (prompt) {
      polishQuestion += '\n\n优化要求：' + prompt
    }
    
    const res = await polishPage(props.courseId, { 
      pageNum: item.page, 
      content: item.script,
      question: polishQuestion
    })
    item.script = cleanScriptContent(res.data.answerContent)
    item.audioUrl = res.data.audioUrl
    emit('update:slides', [...localSlides.value])
    ElMessage.success('润色成功')
  } catch (e) { 
    ElMessage.error('润色失败') 
  } finally { 
    loading.close() 
  }
}

onUnmounted(() => {
  if (currentAudio.value) currentAudio.value.pause()
  if (resizeTimer) clearTimeout(resizeTimer)
  if (measureRetryTimer) clearTimeout(measureRetryTimer)
  if (containerObserver) containerObserver.disconnect()
  window.removeEventListener('resize', handleWindowResize)
  window.removeEventListener('resize', onWindowResizeLayout)
})
</script>

<style scoped>
/* Element Plus — 与新版工作台品牌色一致 */
:deep(.el-button--primary) {
  --el-button-bg-color: #307ae3;
  --el-button-border-color: #307ae3;
  --el-button-hover-bg-color: #1442d3;
  --el-button-hover-border-color: #1442d3;
}
:deep(.el-button--primary.is-link),
:deep(.el-button--primary.is-plain) {
  --el-button-text-color: #307ae3;
}
:deep(.el-tabs__item.is-active) {
  color: #307ae3 !important;
  font-weight: bold;
}
:deep(.el-tabs__active-bar) {
  background-color: #307ae3 !important;
  height: 3px;
  border-radius: 3px;
}
:deep(.brand-tabs .el-tabs__nav-wrap::after) {
  background-color: #d2e6fe;
}

.brand-btn {
  background: linear-gradient(135deg, #307ae3, #1442d3) !important;
  color: #fff !important;
  border-radius: 12px !important;
  border: none !important;
}
.brand-ctrl-btn {
  color: #1e293b !important;
  font-weight: 600 !important;
  background: #ffffff !important;
  border: 1px solid #e2e8f0 !important;
}
.brand-ctrl-btn:hover {
  color: #307ae3 !important;
  background: #d2e6fe !important;
  border-color: #307ae3 !important;
}

/* 基础布局（与新版一致：无多余外边距，由外层工作台控制） */
.editor-container {
  display: flex;
  height: 100%;
  gap: 0;
  padding: 0;
  overflow: hidden;
  background: transparent;
}
.left-panel {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: #f8fafc;
}

.panel-divider {
  width: 8px;
  background: transparent;
  cursor: col-resize;
  position: relative;
  flex-shrink: 0;
  z-index: 5;
  transition: background 0.2s;
}
.panel-divider:hover {
  background: rgba(48, 122, 227, 0.1);
}
.panel-divider::after {
  display: none;
}

/* 2. 玻璃面板通用样式 */
.glass-panel {
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(33, 150, 243, 0.2);
  border-radius: 12px;
  box-shadow: 0 8px 24px rgba(33, 150, 243, 0.1);
}
.glass-item {
  background: rgba(255, 255, 255, 0.95);
  border: 1px solid rgba(33, 150, 243, 0.15);
  border-radius: 8px;
}

.preview-card { flex: 1; display: flex; flex-direction: column; overflow: hidden; padding: 12px; }
.pdf-stage { flex: 1; display: flex; flex-direction: column; overflow: hidden; background: transparent; }

/* 流式工具栏 */
.glass-toolbar { 
  display: flex; align-items: center; gap: 12px; padding: 8px 16px; flex-shrink: 0; 
  background: linear-gradient(90deg, #FFFFFF 0%, #F8FBFE 100%); backdrop-filter: blur(4px); border-bottom: 1px solid rgba(33, 150, 243, 0.15);
  min-height: 48px;
  box-shadow: 0 2px 6px rgba(33, 150, 243, 0.08);
}
.zoom-controls { background: #FFFFFF; padding: 4px 8px; border-radius: 8px; box-shadow: 0 2px 4px rgba(33, 150, 243, 0.08); display: flex; align-items: center; border: 1px solid rgba(33, 150, 243, 0.15); }
.pdf-navigation { background: #FFFFFF; padding: 4px 14px; border-radius: 8px; box-shadow: 0 2px 4px rgba(33, 150, 243, 0.08); display: flex; align-items: center; gap: 10px; border: 1px solid rgba(33, 150, 243, 0.15); }
.semantic-tag { margin-left: auto; color: #1976D2; font-size: 11px; white-space: nowrap; font-weight: 500; }

.pdf-page-view { flex: 1; position: relative; overflow: hidden; width: 100%; }
.pdf-center-wrapper { position: absolute; inset: 0; display: flex; justify-content: center; align-items: center; overflow: auto; padding: 12px; }
.pdf-page-wrapper { background: #ffffff; }
.glass-page-shadow { box-shadow: 0 12px 32px rgba(33, 150, 243, 0.15), 0 2px 8px rgba(0,0,0,0.05); border-radius: 4px;}

.pptx-preview-container { position: absolute; inset: 0; overflow: auto; background: transparent; border-radius: 0; }

/* 右侧：脚本编辑 */
.right-panel { width: 400px; display: flex; flex-direction: column; padding: 12px; overflow: hidden; }
.panel-tabs { padding: 0 12px; flex-shrink: 0; }
.scroll-area { flex: 1; overflow-y: auto; padding: 12px; min-height: 0; }
.polish-panel-wrapper { flex-shrink: 0; padding: 0 12px 8px; }

/* 卡片样式 */
.script-card { margin-bottom: 15px; padding: 12px; cursor: pointer; transition: all 0.3s ease; border-radius: 8px; border: 1px solid rgba(33, 150, 243, 0.15); }
.script-card:hover { background: rgba(255,255,255,0.98); box-shadow: 0 2px 6px rgba(33, 150, 243, 0.1); }
.script-card.active { border-color: #2196F3; background: rgba(33, 150, 243, 0.08); box-shadow: 0 4px 12px rgba(33, 150, 243, 0.15); }

.card-meta { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.page-title { font-weight: 600; font-size: 14px; color: #1565C0; }
.card-content { margin: 10px 0; }

/* 深度覆写输入框为蓝色主题 */
.active-editor :deep(.el-textarea__inner),
.glass-input :deep(.el-input__wrapper) { 
  background: #FFFFFF !important;
  backdrop-filter: blur(2px);
  border: none !important;
  box-shadow: 0 0 0 1px rgba(33, 150, 243, 0.2) inset !important;
  transition: all 0.3s;
}
.active-editor :deep(.el-textarea__inner:focus),
.glass-input :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1.5px #2196F3 inset !important;
  background: #F8FBFE !important;
}

.preview-text { font-size: 14px; line-height: 1.6; color: #606266; white-space: pre-wrap; word-break: break-word; min-height: 60px; }

.ai-actions { display: flex; flex-direction: column; gap: 8px; margin-top: 12px; padding-top: 12px; border-top: 1px solid rgba(33, 150, 243, 0.15); }
.polish-input-container { width: 100%; }

/* 麦克风按钮 */
.voice-button { margin: 0; padding: 0 2px; min-width: 24px; width: 24px; height: 24px; border: none; background: transparent; display: flex; align-items: center; justify-content: center; transition: all 0.2s; }
.voice-button:hover { background: rgba(33, 150, 243, 0.1); color: #2196F3; }
.is-listening { color: #2196F3; animation: pulse 1.5s infinite; }
@keyframes pulse { 0% { transform: scale(1); } 50% { transform: scale(1.1); } 100% { transform: scale(1); } }

.polish-button { align-self: flex-end; border-radius: 6px; }

/* 知识库标签页 */
.knowledge-base-container { padding: 10px; }
.kb-loading { display: flex; align-items: center; gap: 10px; justify-content: center; padding: 40px 20px; color: #2196F3; font-size: 13px; }
.kb-empty { display: flex; flex-direction: column; align-items: center; padding: 40px 20px; }
.kb-tip { font-size: 12px; color: #999; margin-top: 8px; text-align: center; }
.kb-content { display: flex; flex-direction: column; gap: 12px; }
.kb-header { display: flex; justify-content: space-between; align-items: center; padding: 10px 12px; background: rgba(33,150,243,0.04); border-radius: 8px; border: 1px solid rgba(33,150,243,0.12); }
.kb-header-left { display: flex; align-items: center; gap: 8px; }
.kb-header-right { display: flex; align-items: center; gap: 10px; }
.kb-title { font-size: 14px; font-weight: 600; color: #1565c0; }
.kb-count { font-size: 12px; color: #999; }
.kb-desc { font-size: 12px; color: #666; margin: 0; padding: 8px 12px; background: rgba(33,150,243,0.05); border-radius: 6px; border-left: 3px solid #2196F3; }
.kb-list { display: flex; flex-direction: column; gap: 8px; max-height: 320px; overflow-y: auto; }
.kb-item { display: flex; align-items: center; gap: 10px; padding: 10px 12px; border: 1.5px solid rgba(33,150,243,0.15); border-radius: 8px; cursor: pointer; transition: all 0.2s; background: rgba(255,255,255,0.9); }
.kb-item:hover { border-color: #2196F3; background: rgba(33,150,243,0.04); }
.kb-item.selected { border-color: #2196F3; background: rgba(33,150,243,0.08); }
.kb-item-info { display: flex; align-items: center; gap: 8px; flex: 1; overflow: hidden; }
.kb-item-text { display: flex; flex-direction: column; flex: 1; overflow: hidden; }
.kb-item-name { font-size: 13px; font-weight: 500; color: #333; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.kb-item-meta { display: flex; align-items: center; gap: 6px; margin-top: 3px; }
.kb-item-type { font-size: 10px; background: #e3f2fd; color: #1565c0; padding: 1px 6px; border-radius: 3px; font-weight: 600; }
.kb-item-rag { font-size: 10px; background: rgba(103,194,58,0.12); color: #67c23a; padding: 1px 6px; border-radius: 3px; }
.kb-item-rag--pending { background: rgba(255,152,0,0.1); color: #FF9800; }
.kb-selected-count { font-size: 12px; color: #1565c0; font-weight: 500; }
.kb-actions { display: flex; flex-direction: column; gap: 8px; padding: 12px; background: rgba(33,150,243,0.03); border-radius: 8px; border: 1px solid rgba(33,150,243,0.1); }
.kb-hint { font-size: 12px; color: #999; margin: 0; }
.kb-hint--success { color: #67c23a; }

/* 测验标签页 */
.quiz-container { padding: 10px; }
.quiz-empty { display: flex; flex-direction: column; align-items: center; padding: 40px 20px; }
.quiz-icon { margin-bottom: 16px; color: #2196F3; }
.quiz-content { display: flex; flex-direction: column; gap: 12px; }
.quiz-header { display: flex; justify-content: space-between; align-items: center; padding: 12px; background: rgba(33,150,243,0.03); border-radius: 8px; border: 1px solid rgba(33,150,243,0.1); }
.quiz-count { font-size: 13px; color: #1565c0; font-weight: 500; }
.quiz-list { display: flex; flex-direction: column; gap: 12px; max-height: 500px; overflow-y: auto; }
.quiz-item { border: 1px solid rgba(33,150,243,0.15); border-radius: 8px; padding: 12px; background: rgba(255,255,255,0.9); }
.quiz-item.editing { border-color: #2196F3; background: rgba(33,150,243,0.05); }
.question-header { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }
.question-number { font-size: 13px; font-weight: 600; color: #1565c0; }
.question-type { font-size: 11px; background: #e3f2fd; color: #1565c0; padding: 2px 8px; border-radius: 4px; }
.question-edit { padding: 12px; background: rgba(33,150,243,0.02); border-radius: 6px; }
.option-edit { display: flex; gap: 8px; margin-bottom: 8px; }
.question-preview { }
.question-content { font-size: 13px; color: #333; margin: 0 0 8px 0; line-height: 1.5; }
.options-preview { margin: 8px 0; }
.option-item { font-size: 12px; color: #666; margin: 4px 0; }
.option-label { font-weight: 600; color: #1565c0; margin-right: 4px; }
.answer-preview { font-size: 12px; color: #333; margin: 8px 0; }
.explanation-preview { font-size: 12px; color: #666; margin: 8px 0; font-style: italic; }
.quiz-actions { display: flex; gap: 8px; padding: 12px; background: rgba(33,150,243,0.03); border-radius: 8px; border-top: 1px solid rgba(33,150,243,0.1); }

/* 知识图谱/思维导图 */
.knowledge-graph-container, .mindmap-container { height: 100%; padding: 10px; }
.knowledge-graph-content, .mindmap-content { height: 100%; padding: 20px; display: flex; flex-direction: column;}
.knowledge-graph-placeholder, .mindmap-placeholder { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 400px; text-align: center; color: #666; }
.knowledge-graph-icon, .mindmap-icon { margin-bottom: 16px; color: #2196F3; }
.knowledge-graph-visualization, .mindmap-visualization { height: 100%; position: relative; border-radius: 6px; border: 1px solid rgba(33, 150, 243, 0.2); overflow: hidden; background: rgba(255,255,255,0.6);}
.knowledge-graph-loading, .mindmap-loading { display: flex; align-items: center; justify-content: center; height: 100%; color: #2196F3; font-weight: 500; }
.knowledge-graph-canvas, .mindmap-canvas { width: 100%; height: 100%; overflow: auto; display: flex; align-items: center; justify-content: center; }
.knowledge-graph-svg, .mindmap-svg { width: 100%; height: 100%; max-width: none; max-height: none; cursor: grab; }
.knowledge-graph-svg:active, .mindmap-svg:active { cursor: grabbing; }

/* SVG 新风格 */
.mindmap-svg text, .knowledge-graph-svg text { font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif; pointer-events: none; }
.mindmap-center-node { filter: drop-shadow(0 4px 8px rgba(0,0,0,0.1)); transition: all 0.3s ease; }
.mindmap-center-node:hover { filter: drop-shadow(0 6px 12px rgba(0,0,0,0.15)); transform: scale(1.02); }
.mindmap-center text { font-size: 20px; font-weight: bold; fill: white; }
.mindmap-branch-node { filter: drop-shadow(0 2px 4px rgba(0,0,0,0.1)); transition: all 0.3s ease; }
.mindmap-branch:hover .mindmap-branch-node { transform: scale(1.05); filter: drop-shadow(0 4px 8px rgba(0,0,0,0.2)); }
.mindmap-branch text { font-size: 16px; font-weight: 500; fill: white; }
.mindmap-sub text { font-size: 14px; fill: #444; transition: all 0.3s ease; }
.mindmap-branch:hover .mindmap-sub text { fill: #000; }
.mindmap-line { stroke-linecap: round; opacity: 0.8; transition: all 0.3s ease; }
.mindmap-branch:hover ~ .mindmap-lines .mindmap-line { opacity: 0.3; }
.mindmap-branch:hover .mindmap-line { opacity: 1; }
.knowledge-graph-node-circle { cursor: pointer; transition: all 0.3s; filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.15)); }
.knowledge-graph-node-circle:hover { transform: scale(1.08); filter: drop-shadow(0 4px 8px rgba(0, 0, 0, 0.25)); }
.edge-text { font-family: 'PingFang SC', sans-serif; letter-spacing: 1px; }

/* 响应式移动端适配 */
@media screen and (max-width: 768px) {
  .editor-container { flex-direction: column; overflow-y: auto; padding: 8px; gap: 8px; }
  .left-panel { flex: none; height: auto; min-height: 200px; max-height: 50vh; }
  .panel-divider { display: none; }
  .right-panel { width: 100%; flex: 1; min-height: 40vh; }
  .preview-card { padding: 8px; }
  .scroll-area { padding: 10px; }
  .stage-toolbar { flex-wrap: wrap; gap: 8px; padding: 8px 12px; }
  .semantic-tag { display: none; }
  .zoom-controls { flex-shrink: 0; }
  .pdf-navigation { flex-shrink: 0; }
  .ai-actions { flex-direction: column; }
  .polish-button { align-self: stretch; width: 100%; }
}

/* 平板端适配 */
@media screen and (min-width: 769px) and (max-width: 1024px) {
  .right-panel { width: 320px; }
}

/* 移动端隐藏类 */
.hide-on-mobile { }
@media screen and (max-width: 768px) {
  .hide-on-mobile { display: none !important; }
}

/* 滚动条美化 */
::-webkit-scrollbar { width: 6px; height: 6px;}
::-webkit-scrollbar-thumb { background: rgba(33, 150, 243, 0.3); border-radius: 4px; }
::-webkit-scrollbar-track { background: transparent; }
</style>