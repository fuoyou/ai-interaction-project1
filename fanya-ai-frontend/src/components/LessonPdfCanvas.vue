<script setup>
import { ref, watch, nextTick, onBeforeUnmount, shallowRef } from 'vue'
import * as pdfjsLib from 'pdfjs-dist'
import workerUrl from 'pdfjs-dist/build/pdf.worker.min.mjs?url'

pdfjsLib.GlobalWorkerOptions.workerSrc = workerUrl

const props = defineProps({
  pdfUrl: { type: String, default: '' },
  pageNum: { type: Number, default: 1 },
  /** 与 vue-pdf-embed 一致的渲染宽度（px） */
  renderWidth: { type: Number, default: 900 },
  /** 外层缩放（与教师端一致） */
  zoom: { type: Number, default: 1 },
  /** 当前页对应 Paddle 版面：{ page_num, page_width, page_height, blocks } */
  ocrPage: { type: Object, default: null },
  selectedBlockId: { type: String, default: null },
})

const emit = defineEmits(['block-click'])

const canvasRef = ref(null)
const vw = ref(0)
const vh = ref(0)
const renderError = ref('')

const pdfDoc = shallowRef(null)
let loadingTask = null

let currentRenderTask = null
let renderGeneration = 0

function cancelOngoingRender() {
  if (currentRenderTask && typeof currentRenderTask.cancel === 'function') {
    try {
      currentRenderTask.cancel()
    } catch {
      /* ignore */
    }
  }
  currentRenderTask = null
}

async function loadDoc(url) {
  if (loadingTask && typeof loadingTask.destroy === 'function') {
    loadingTask.destroy()
  }
  loadingTask = null
  pdfDoc.value = null
  if (!url?.trim()) return

  try {
    loadingTask = pdfjsLib.getDocument({ url: url.trim(), withCredentials: false })
    pdfDoc.value = await loadingTask.promise
  } catch (e) {
    renderError.value = e?.message || String(e)
    pdfDoc.value = null
  }
}

async function render() {
  cancelOngoingRender()
  const gen = ++renderGeneration
  renderError.value = ''
  const el = canvasRef.value
  if (!el || !pdfDoc.value) {
    vw.value = 0
    vh.value = 0
    return
  }

  try {
    const page = await pdfDoc.value.getPage(props.pageNum)
    if (gen !== renderGeneration) return

    const base = page.getViewport({ scale: 1 })
    const renderScale = Math.max(0.2, (props.renderWidth / base.width) * (props.zoom || 1))
    const viewport = page.getViewport({ scale: renderScale })

    el.width = viewport.width
    el.height = viewport.height
    vw.value = viewport.width
    vh.value = viewport.height

    const ctx = el.getContext('2d')
    const task = page.render({ canvasContext: ctx, viewport })
    currentRenderTask = task
    await task.promise
    if (gen !== renderGeneration) return
    currentRenderTask = null
  } catch (e) {
    currentRenderTask = null
    const msg = e?.message || String(e)
    if (/cancel|cancell?ed|aborted/i.test(msg)) return
    renderError.value = msg
  }
}

watch(
  () => props.pdfUrl,
  async (url) => {
    await loadDoc(url)
    await nextTick()
    render()
  },
  { immediate: true },
)

watch(
  () => [props.pageNum, props.renderWidth, props.zoom, pdfDoc.value],
  async () => {
    await nextTick()
    render()
  },
  { flush: 'post' },
)

onBeforeUnmount(() => {
  cancelOngoingRender()
  if (loadingTask && typeof loadingTask.destroy === 'function') {
    loadingTask.destroy()
  }
})

function blockStyle(block) {
  const bbox = block.bbox
  const pw = props.ocrPage?.page_width
  const ph = props.ocrPage?.page_height
  if (!bbox || pw == null || ph == null || !vw.value || !vh.value) {
    return { display: 'none' }
  }
  const [x1, y1, x2, y2] = bbox
  const sx = vw.value / pw
  const sy = vh.value / ph
  return {
    left: `${x1 * sx}px`,
    top: `${y1 * sy}px`,
    width: `${(x2 - x1) * sx}px`,
    height: `${(y2 - y1) * sy}px`,
  }
}

function onBlockClick(block) {
  emit('block-click', block)
}

/** 按 Paddle bbox 从当前页 canvas 裁剪配图，供千问视觉 API（JPEG 压缩，最大边约 1024） */
function cropBlockToDataURL(block) {
  const el = canvasRef.value
  if (!el || !block?.bbox || !props.ocrPage?.page_width || !props.ocrPage?.page_height) return null
  const bbox = block.bbox
  if (!Array.isArray(bbox) || bbox.length < 4) return null
  const [x1, y1, x2, y2] = bbox
  const pw = props.ocrPage.page_width
  const ph = props.ocrPage.page_height
  if (!vw.value || !vh.value) return null
  const sx = vw.value / pw
  const sy = vh.value / ph
  const px = Math.max(0, Math.floor(x1 * sx))
  const py = Math.max(0, Math.floor(y1 * sy))
  const cw = Math.max(2, Math.ceil((x2 - x1) * sx))
  const ch = Math.max(2, Math.ceil((y2 - y1) * sy))
  try {
    const maxD = 1024
    /** 通义 VL 要求宽、高均须明显大于 10px，过小会拒识 */
    const minModel = 12
    let destW = cw
    let destH = ch
    if (destW > maxD || destH > maxD) {
      const s = Math.min(maxD / destW, maxD / destH, 1)
      destW = Math.max(2, Math.floor(destW * s))
      destH = Math.max(2, Math.floor(destH * s))
    }
    destW = Math.max(destW, minModel)
    destH = Math.max(destH, minModel)
    const out = document.createElement('canvas')
    out.width = destW
    out.height = destH
    const octx = out.getContext('2d')
    octx.fillStyle = '#ffffff'
    octx.fillRect(0, 0, destW, destH)
    octx.drawImage(el, px, py, cw, ch, 0, 0, destW, destH)
    return out.toDataURL('image/jpeg', 0.8)
  } catch {
    return null
  }
}

defineExpose({ cropBlockToDataURL })

function blockClass(block) {
  return [
    'block-hit',
    block.type === 'figure' ? 'block-hit--figure' : '',
    block.id === props.selectedBlockId ? 'block-hit--active' : '',
  ]
}
</script>

<template>
  <div class="lesson-pdf-canvas">
    <p v-if="renderError" class="pdf-page__err">{{ renderError }}</p>
    <div class="pdf-page__inner">
      <canvas ref="canvasRef" class="pdf-page__canvas" />
      <div
        v-if="ocrPage?.blocks?.length && vw && ocrPage?.page_width"
        class="pdf-page__overlay"
        :style="{ width: `${vw}px`, height: `${vh}px` }"
      >
        <button
          v-for="b in ocrPage.blocks"
          :key="b.id"
          type="button"
          :class="blockClass(b)"
          :style="blockStyle(b)"
          :title="(b.text || '').slice(0, 80)"
          @click="onBlockClick(b)"
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
.lesson-pdf-canvas {
  display: inline-block;
}
.pdf-page__err {
  color: #b91c1c;
  font-size: 0.85rem;
  margin: 0 0 0.5rem;
}
.pdf-page__inner {
  position: relative;
  display: inline-block;
  line-height: 0;
  box-shadow: 0 1px 4px rgb(0 0 0 / 12%);
}
.pdf-page__canvas {
  display: block;
}
.pdf-page__overlay {
  position: absolute;
  left: 0;
  top: 0;
  pointer-events: none;
}
.block-hit {
  position: absolute;
  pointer-events: auto;
  margin: 0;
  padding: 0;
  border: 1px solid transparent;
  background: transparent;
  cursor: pointer;
  border-radius: 2px;
}
.block-hit:focus {
  outline: none;
}
.block-hit:focus-visible:not(.block-hit--active) {
  border-color: rgb(37 99 235 / 0.5);
  background: rgb(37 99 235 / 0.08);
}
.block-hit:hover:not(.block-hit--active) {
  border-color: rgb(37 99 235 / 0.55);
  background: rgb(37 99 235 / 0.1);
}
.block-hit--figure:hover:not(.block-hit--active) {
  border-color: rgb(202 138 4 / 0.6);
  background: rgb(234 179 8 / 0.12);
}
.block-hit--active {
  border-color: rgb(37 99 235 / 0.9);
  background: rgb(37 99 235 / 0.16);
}
.block-hit--figure.block-hit--active {
  border-color: rgb(202 138 4 / 0.95);
  background: rgb(234 179 8 / 0.2);
}
</style>
