<template>
  <div class="pdf-viewer-area">
    <!-- 流式工具栏 -->
    <div class="stage-toolbar" v-if="source">
      <div class="zoom-controls">
        <el-button-group>
          <el-button size="small" :icon="ZoomOut" @click="handleZoom(-0.1)" class="brand-ctrl-btn" />
          <el-button size="small" class="zoom-text brand-ctrl-btn">{{ Math.round(scale * 100) }}%</el-button>
          <el-button size="small" :icon="ZoomIn" @click="handleZoom(0.1)" class="brand-ctrl-btn" />
        </el-button-group>
      </div>
      <div class="pdf-navigation" v-if="totalPages > 0">
        <el-button size="small" :disabled="page <= 1" @click="$emit('changePage', -1)" class="brand-ctrl-btn">← 上一页</el-button>
        <span class="page-info">{{ page }} / {{ totalPages }}</span>
        <el-input-number 
          v-model="jumpPage" 
          :min="1" 
          :max="totalPages" 
          :controls="false"
          size="small"
          class="page-jump-input brand-input"
          @keyup.enter="handleJumpPage"
          placeholder="跳转"
        />
        <el-button size="small" type="primary" @click="handleJumpPage" class="brand-btn">跳转</el-button>
        <el-button size="small" :disabled="page >= totalPages" @click="$emit('changePage', 1)" class="brand-ctrl-btn">下一页 →</el-button>
      </div>
    </div>

    <!-- 内容区 -->
    <div class="pdf-wrapper" ref="pdfViewRef" @mouseup="handleTextSelection">
      <!-- PPTX 直预览 -->
      <template v-if="isPptxFile && source">
        <div ref="pptxContainer" class="pptx-preview-container"></div>
      </template>

      <!-- PPT 文件预览（不含 .pptx，.pptx 走上方直预览） -->
      <template v-else-if="isPptFile && !isPptxFile && source">
        <template v-if="canUseOfficePreview">
          <iframe :src="getPptPreviewUrl()" class="ppt-iframe" frameborder="0" allowfullscreen title="PPT 预览"></iframe>
        </template>
        <div v-else class="empty-state">
          <el-empty image-size="100">
            <template #description>
              <p class="empty-title">PPT 正在转换为可预览格式，请稍候…</p>
              <p class="empty-sub">转换完成后将自动显示</p>
            </template>
            <el-button type="primary" plain class="brand-btn-outline" @click="openInNewTab">先下载原文件查看</el-button>
          </el-empty>
        </div>
      </template>

      <!-- PDF 单页预览：有 Paddle 分块时用 LessonPdfCanvas，否则 PDF.js + 公式层 -->
      <template v-else-if="source">
        <div style="display:none">
          <VuePdfEmbed :key="source" :source="source" @loaded="onLoaded" />
        </div>
        <div :class="['pdf-center-wrapper', isLandscapePdf ? 'landscape-mode' : 'portrait-mode']" v-if="totalPages > 0">
          <div class="pdf-page-wrapper glass-page-shadow" :style="{ transform: `scale(${scale})`, transformOrigin: 'center center' }">
            <LessonPdfCanvas
              v-if="usePaddleOverlay"
              ref="lessonCanvasRef"
              :pdf-url="source"
              :page-num="page"
              :render-width="pdfRenderWidth"
              :zoom="1"
              :ocr-page="currentOcrPage"
              :selected-block-id="selectedBlockId"
              @block-click="onPaddleBlockClick"
            />
            <template v-else>
              <VuePdfEmbed
                :key="source + '-p' + page"
                :source="source"
                :page="page"
                :width="pdfRenderWidth"
                :text-layer="true"
                :annotation-layer="true"
                class="pdf-content"
                @rendered="onPageRendered"
              />
              <div class="formula-overlay-layer">
                <div
                  v-for="(region, index) in formulaRegions"
                  :key="index"
                  class="formula-region"
                  :class="{ 'hovered': hoveredFormulaIndex === index }"
                  :style="{ left: region.left + 'px', top: region.top + 'px', width: region.width + 'px', height: region.height + 'px' }"
                  @mouseenter="hoveredFormulaIndex = index"
                  @mouseleave="hoveredFormulaIndex = -1"
                  @click="handleFormulaClick(region)"
                >
                  <div class="formula-tooltip" v-if="hoveredFormulaIndex === index">点击提问此公式</div>
                </div>
              </div>
            </template>
          </div>
        </div>
      </template>

      <!-- 空状态 -->
      <div v-else class="empty-state">
        <el-empty description="暂无课件，请点击右上角导入" image-size="120">
          <el-button type="primary" class="brand-btn" @click="$emit('upload')">上传 PDF</el-button>
        </el-empty>
      </div>

      <!-- 加载遮罩 -->
      <div v-if="loading" class="upload-mask">
        <div class="loading-box">
          <el-icon class="is-loading brand-primary-text" :size="48"><Loading /></el-icon>
          <p class="loading-text">AI 正在解析文档结构...</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
// JS 逻辑保持与原文件一致，颜色系统已在 CSS 中重构
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue'
import VuePdfEmbed from 'vue-pdf-embed'
import LessonPdfCanvas from '@/components/LessonPdfCanvas.vue'
import 'vue-pdf-embed/dist/styles/annotationLayer.css'
import 'vue-pdf-embed/dist/styles/textLayer.css'
import { init as initPptxPreview } from 'pptx-preview'
import { ZoomIn, ZoomOut, Loading } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const props = defineProps(['source', 'page', 'loading', 'paddlePages'])
const emit = defineEmits(['changePage', 'upload', 'textSelected', 'formulaSelected', 'imageSelected'])

const scale = ref(1.0); const totalPages = ref(0); const jumpPage = ref(null); const pptxContainer = ref(null); const pdfViewRef = ref(null); const pdfRenderWidth = ref(800); const pdfAspectRatio = ref(null); let pptxPreviewer = null; let resizeTimer = null; let measureRetryTimer = null; let containerObserver = null;
const formulaRegions = ref([]); const hoveredFormulaIndex = ref(-1);
const selectedBlockId = ref(null)
const lessonCanvasRef = ref(null)

const isLandscapePdf = computed(() => pdfAspectRatio.value !== null && pdfAspectRatio.value >= 1)
const isPptFile = computed(() => { if (!props.source) return false; const s = String(props.source).toLowerCase(); return s.endsWith('.ppt') || s.endsWith('.pptx') })
const isPptxFile = computed(() => { if (!props.source) return false; return String(props.source).toLowerCase().endsWith('.pptx') })
const isPdfFile = computed(() => { if (!props.source) return false; return String(props.source).toLowerCase().endsWith('.pdf') })

const paddlePagesList = computed(() => (Array.isArray(props.paddlePages) ? props.paddlePages : []))
const usePaddleOverlay = computed(() => isPdfFile.value && paddlePagesList.value.length > 0)
const currentOcrPage = computed(() => paddlePagesList.value.find((p) => p.page_num === props.page) ?? null)

const onPaddleBlockClick = (block) => {
  selectedBlockId.value = block?.id || null
  const t = String(block?.type || '').toLowerCase()
  const lbl = String(block?.label || block?.block_label || '').toLowerCase()
  const isFigure = t === 'figure' || /figure|image|chart|picture/.test(lbl)
  if (isFigure && lessonCanvasRef.value?.cropBlockToDataURL) {
    const dataUrl = lessonCanvasRef.value.cropBlockToDataURL(block)
    if (dataUrl) {
      emit('imageSelected', {
        imageBase64: dataUrl,
        page: props.page,
        blockId: block?.id,
        block
      })
      ElMessage.success('已截取配图，正在调用通义千问视觉解读…')
      return
    }
    ElMessage.warning('无法截取该区域，请稍后重试')
    return
  }
  const text = (block?.text || '').trim()
  if (text) {
    emit('textSelected', {
      text,
      page: props.page,
      blockId: block?.id,
      fromPaddleBlock: true
    })
    ElMessage.success('已选中该区域，可向 AI 提问')
  }
}

const getPptPreviewUrl = () => { if (!props.source) return ''; let fullUrl = props.source; if (fullUrl.startsWith('/')) fullUrl = `http://localhost:8989${fullUrl}`; return `https://view.officeapps.live.com/op/embed.aspx?src=${encodeURIComponent(fullUrl)}` }
const canUseOfficePreview = computed(() => { if (!props.source || !isPptFile.value || isPptxFile.value) return false; if (props.source.startsWith('/')) return false; try { const host = new URL(String(props.source)).hostname.toLowerCase(); return !['localhost', '127.0.0.1'].includes(host) && !host.startsWith('192.168.') && !host.startsWith('10.') && !host.startsWith('172.') } catch { return false } })
const openInNewTab = () => { if (props.source) window.open(props.source, '_blank') }

const recalcPdfWidth = () => { if (!pdfViewRef.value) return; const rect = pdfViewRef.value.getBoundingClientRect(); if (rect.width < 10) return; const pad = 24; const aspect = pdfAspectRatio.value; if (aspect !== null && aspect >= 1) { const maxByWidth = Math.floor(rect.width - pad); const maxByHeight = Math.floor((rect.height - pad) * aspect); pdfRenderWidth.value = Math.max(Math.min(maxByWidth, maxByHeight), 300); } else { pdfRenderWidth.value = Math.floor(rect.width - pad); } }
const onLoaded = async (doc) => { totalPages.value = doc.numPages; try { const p = await doc.getPage(1); const vp = p.getViewport({ scale: 1 }); pdfAspectRatio.value = vp.width / vp.height; recalcPdfWidth(); } catch { recalcPdfWidth(); } }
const renderPptxPreview = async () => { if (!isPptxFile.value || !props.source || !pptxContainer.value) return; try { const rect = pptxContainer.value.getBoundingClientRect(); if (rect.width < 300 || rect.height < 240) { if (measureRetryTimer) clearTimeout(measureRetryTimer); measureRetryTimer = setTimeout(() => renderPptxPreview(), 220); return; } pptxContainer.value.innerHTML = ''; const containerWidth = Math.max(560, Math.floor(rect.width - 8)); const maxHeight = Math.max(360, Math.floor(rect.height - 8)); const fitHeight = Math.min(maxHeight, Math.floor((containerWidth * 9) / 16)); pptxPreviewer = initPptxPreview(pptxContainer.value, { width: containerWidth, height: fitHeight, mode: 'list' }); const resp = await fetch(props.source); const buf = await resp.arrayBuffer(); await pptxPreviewer.preview(buf); } catch (e) { ElMessage.warning('PPTX 直预览失败，请稍后重试'); } }
const handleWindowResize = () => { if (resizeTimer) clearTimeout(resizeTimer); resizeTimer = setTimeout(() => { if (isPptxFile.value) renderPptxPreview(); else if (isPdfFile.value) recalcPdfWidth(); }, 180); }
const handleZoom = (delta) => { const v = scale.value + delta; if (v >= 0.5 && v <= 3.0) scale.value = Number(v.toFixed(1)); }
const handleJumpPage = () => {
  if (!jumpPage.value || jumpPage.value < 1 || jumpPage.value > totalPages.value) {
    ElMessage.warning('请输入有效的页码')
    return
  }
  const targetPage = Number(jumpPage.value)
  const delta = targetPage - props.page
  emit('changePage', delta)
  jumpPage.value = null
}
const handleTextSelection = () => { const selection = window.getSelection(); const selectedText = selection?.toString().trim(); if (selectedText && selectedText.length > 3) { setTimeout(() => { emit('textSelected', { text: selectedText, page: props.page, isFormula: false }); selection.removeAllRanges() }, 300) } }
const onPageRendered = async () => { await nextTick(); setTimeout(() => { detectFormulas() }, 500) }
const detectFormulas = () => { formulaRegions.value = []; if (!pdfViewRef.value) return; const textLayer = pdfViewRef.value.querySelector('.textLayer'); if (!textLayer) return; const textSpans = textLayer.querySelectorAll('span'); const mathSymbols = /[∫∑∏√∂∇±×÷≈≠≤≥∞αβγδεθλμπσφψω]/; const mathPatterns = [ /[A-Z][a-z]?\s*[=≈]\s*/, /\s*[=≈]\s*[A-Z]/, /\d+\s*[×÷]\s*\d+/, /[A-Z]_[a-z]/, /[A-Z]\^[0-9]/, /\([A-Za-z0-9\s+\-*/]+\)/, /\b(sin|cos|tan|log|ln|exp|sqrt)\b/i, /\d+\s*\/\s*\d+/, /[EI][A-Z]_[a-z]/ ]; const pdfContent = pdfViewRef.value.querySelector('.pdf-content'); if (!pdfContent) return; const containerRect = pdfContent.getBoundingClientRect(); textSpans.forEach((span) => { const text = span.textContent || ''; const hasSymbol = mathSymbols.test(text); const matchesPattern = mathPatterns.some(pattern => pattern.test(text)); if (hasSymbol || matchesPattern) { const rect = span.getBoundingClientRect(); const region = { text: text, left: rect.left - containerRect.left, top: rect.top - containerRect.top, width: Math.max(rect.width, 30), height: Math.max(rect.height, 20) }; formulaRegions.value.push(region); } }) }
const handleFormulaClick = (region) => { emit('textSelected', { text: region.text, page: props.page, isFormula: true }); ElMessage.success('已选中公式'); }

watch(() => props.source, async () => {
  totalPages.value = 0
  scale.value = 1.0
  pdfAspectRatio.value = null
  formulaRegions.value = []
  selectedBlockId.value = null
  await nextTick()
  if (isPptxFile.value) await renderPptxPreview()
  else if (isPdfFile.value) recalcPdfWidth()
}, { immediate: true })
watch(() => props.page, async () => {
  formulaRegions.value = []
  hoveredFormulaIndex.value = -1
  selectedBlockId.value = null
})

onMounted(() => { window.addEventListener('resize', handleWindowResize); recalcPdfWidth(); containerObserver = new ResizeObserver(() => handleWindowResize()); if (pptxContainer.value) containerObserver.observe(pptxContainer.value); if (pdfViewRef.value) containerObserver.observe(pdfViewRef.value); })
onUnmounted(() => { if (resizeTimer) clearTimeout(resizeTimer); if (measureRetryTimer) clearTimeout(measureRetryTimer); if (containerObserver) containerObserver.disconnect(); window.removeEventListener('resize', handleWindowResize); })
</script>

<style scoped>
/* 严格遵循品牌四色 */
.pdf-viewer-area {
  --primary-blue: #307AE3;
  --dark-blue: #1442D3;
  --light-blue: #D2E6FE;
  --bg-dark: #F8FAFC;
  --text-main: #1E293B;
  
  flex: 1; 
  display: flex; 
  flex-direction: column; 
  background: var(--bg-dark); 
  overflow: hidden; /* 核心：防止容器产生滚动条 */
}

/* 按钮通用映射 */
.brand-btn { background: linear-gradient(135deg, var(--primary-blue), var(--dark-blue)) !important; border: none !important; box-shadow: 0 4px 12px rgba(48, 122, 227, 0.2) !important; color: #FFF !important; font-weight: 600; border-radius: 12px !important; }
.brand-btn:hover { transform: translateY(-1px); box-shadow: 0 6px 16px rgba(20, 66, 211, 0.3) !important; }
.brand-btn-outline { border: 1px solid var(--primary-blue) !important; color: var(--primary-blue) !important; background: transparent !important; border-radius: 12px !important; padding: 10px 24px !important; font-weight: 700;}
.brand-btn-outline:hover { background: rgba(48, 122, 227, 0.1) !important; color: var(--primary-blue) !important; }
.brand-ctrl-btn { color: #1E293B !important; font-weight: 600 !important; background: #FFFFFF !important; border: 1px solid #E2E8F0 !important;}
.brand-ctrl-btn:hover { color: var(--primary-blue) !important; background: var(--light-blue) !important; border-color: var(--primary-blue) !important;}
.brand-input :deep(.el-input__wrapper) { box-shadow: 0 0 0 1px #E2E8F0 inset; border-radius: 6px; }
.brand-input :deep(.el-input__wrapper.is-focus) { box-shadow: 0 0 0 1px var(--primary-blue) inset; }

.stage-toolbar { 
  display: flex; align-items: center; gap: 16px; padding: 12px 20px; flex-shrink: 0; background: #FFFFFF; min-height: 56px; border-bottom: 1px solid var(--light-blue); box-shadow: 0 2px 8px rgba(20, 66, 211, 0.05); z-index: 10;
}
.zoom-controls { background: #FFFFFF; padding: 4px; border-radius: 8px; display: flex; align-items: center; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);}
.zoom-text { min-width: 48px; text-align: center; }
.pdf-navigation { background: #FFFFFF; padding: 6px 16px; border-radius: 8px; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05); display: flex; align-items: center; gap: 12px; }
.page-info { font-size: 14px; color: var(--dark-blue); font-weight: 800; white-space: nowrap; }
.page-jump-input { width: 80px; }
.page-jump-input :deep(.el-input__inner) { text-align: center; font-weight: 600; color: var(--text-main);}

/* 核心：隐藏滚动条并移除右侧竖线 */
.pdf-wrapper { 
  flex: 1; 
  position: relative; 
  width: 100%; 
  overflow: hidden; /* 彻底移除滚动条区域 */
}

.pdf-center-wrapper {
  position: absolute;
  inset: 0;
  display: flex;
  justify-content: center;
  padding: 24px;
  background: var(--bg-dark);
}

.pdf-center-wrapper.landscape-mode {
  align-items: center;
  overflow: auto;
}

/* 纵向文档保留可滚动阅读，避免新版「全部 hidden」导致长页无法浏览 */
.pdf-center-wrapper.portrait-mode {
  align-items: flex-start;
  overflow-y: auto;
  overflow-x: hidden;
}

.pdf-page-wrapper {
  width: 100%;
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid #d2e6fe;
  margin: 0 auto;
  position: relative;
}

.glass-page-shadow {
  box-shadow: 0 8px 24px rgba(20, 66, 211, 0.15);
  transition: all 0.3s ease;
}

.pptx-preview-container { position: absolute; inset: 0; overflow: hidden; background: var(--bg-dark); }
.ppt-iframe { position: absolute; inset: 0; width: 100%; height: 100%; border-radius: 0; }

.empty-state { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; background: var(--bg-dark);}
:deep(.el-empty__description p) { color: #94A3B8; font-size: 15px; font-weight: 500;}
.empty-title { color: #ACB1EC; font-size: 16px; font-weight: 600;}
.empty-sub { color: #64748B; font-size: 13px; margin-top: 6px;}

.upload-mask { position: absolute; inset: 0; background: rgba(248, 250, 252, 0.85); backdrop-filter: blur(8px); display: flex; justify-content: center; align-items: center; z-index: 20; color: #fff; }
.loading-box { text-align: center; padding: 24px; background: #FFFFFF; border-radius: 20px; box-shadow: 0 8px 24px rgba(20, 66, 211, 0.1); border: 1px solid #D2E6FE;}
.loading-text { margin-top: 16px; font-size: 15px; font-weight: 600; color: #1442D3; letter-spacing: 1px;}

.formula-overlay-layer { position: absolute; top: 0; left: 0; right: 0; bottom: 0; pointer-events: none; z-index: 20; }
.formula-region { position: absolute; pointer-events: auto; cursor: pointer; transition: all 0.2s ease; border-radius: 8px; border: 2px solid transparent; }
.formula-region:hover { background: rgba(48, 122, 227, 0.15); border-color: rgba(48, 122, 227, 0.5); z-index: 21; }
.formula-tooltip { position: absolute; bottom: calc(100% + 8px); left: 50%; transform: translateX(-50%); background: #FFFFFF; color: var(--primary-blue); border: 1px solid var(--light-blue); padding: 6px 12px; border-radius: 8px; font-size: 12px; white-space: nowrap; z-index: 100; box-shadow: 0 4px 12px rgba(48, 122, 227, 0.1); font-weight: 600; }
.formula-tooltip::after { content: ''; position: absolute; top: 100%; left: 50%; transform: translateX(-50%); border: 6px solid transparent; border-top-color: #FFFFFF; }

.pdf-content {
  user-select: text;
  -webkit-user-select: text;
}

.pdf-content :deep(.textLayer) {
  position: absolute;
  left: 0;
  top: 0;
  right: 0;
  bottom: 0;
  overflow: hidden;
  opacity: 1;
  line-height: 1;
  user-select: text;
  -webkit-user-select: text;
}

.pdf-content :deep(.textLayer span) {
  color: transparent;
  position: absolute;
  white-space: pre;
  cursor: text;
  transform-origin: 0% 0%;
}

.pdf-content :deep(.textLayer ::selection) {
  background: rgba(48, 122, 227, 0.2);
}

.pdf-content :deep(.textLayer ::-moz-selection) {
  background: rgba(48, 122, 227, 0.2);
}

@media (max-width: 1024px) {
  .stage-toolbar { padding: 8px 12px; gap: 8px; flex-wrap: wrap; }
  .zoom-controls, .pdf-navigation { padding: 3px 6px; gap: 6px; }
  .page-info { font-size: 12px; }
}

@media (max-width: 768px) {
  .pdf-viewer-area { background: #F8FAFC; }
  .stage-toolbar { padding: 6px 10px; gap: 6px; height: auto; min-height: 44px; }
  .pdf-center-wrapper { padding: 8px; }
}
</style>