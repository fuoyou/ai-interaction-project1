<template>
  <div class="chat-area" ref="scrollRef">
    <!-- 1. 讲解模式 -->
    <div v-if="mode === 'lecture'" class="ai-message">
      <div class="avatar"><img src="https://cdn-icons-png.flaticon.com/512/4712/4712027.png" /></div>
      <div class="message-content">
        <div class="ai-name">AI 讲师</div>
        <div class="bubble lecture-bubble">
          <p v-html="displayContent"></p>
        </div>
      </div>
    </div>

    <!-- 2. 问答模式 -->
    <div v-else class="chat-list">
      <div v-for="(msg, index) in history" :key="index" :class="['message-row', msg.role]">
        <!-- AI 头像：仅连续 AI 气泡的第一条显示，避免流式/多段回复重复头像 -->
        <div class="avatar" v-if="msg.role === 'ai' && showAiAvatar(index)">
          <img src="https://cdn-icons-png.flaticon.com/512/4712/4712027.png" />
        </div>
        <div
          v-else-if="msg.role === 'ai'"
          class="avatar-spacer"
          aria-hidden="true"
        ></div>
        
        <div class="msg-content-wrapper" @mouseup="handleChatTextSelection($event, msg)">
          <!-- 普通文本消息 -->
          <div v-if="msg.type !== 'supplement'" class="bubble">
            <div v-if="msg.role === 'ai' && msg.visionModel" class="vision-model-tag">
              通义千问视觉 · {{ msg.visionModel }}
            </div>
            <div v-html="formatMarkdown(msg.content)"></div>
            <!-- 【新增】如果消息来自文本选中，显示跳转按钮 -->
            <div v-if="msg.role === 'ai' && msg.sourcePage" class="jump-to-page">
              <el-button 
                size="small" 
                type="primary" 
                class="brand-btn"
                @click="$emit('jumpToPage', msg.sourcePage)"
              >
                <el-icon><Position /></el-icon> 跳转到第 {{ msg.sourcePage }} 页
              </el-button>
            </div>
            <div v-if="msg.role === 'ai' && (msg.coursewareCitations?.length || msg.knowledgeCitations?.length)" class="citation-chips" aria-label="回答溯源标记">
              <span v-if="msg.coursewareCitations?.length" class="citation-chips-label">课件</span>
              <button
                v-for="c in msg.coursewareCitations"
                :key="'cw-' + c.ref"
                type="button"
                class="citation-chip citation-chip--cw"
                :title="(c.sourceName || '') + '，点击查看原文片段'"
                @click.stop="openCitationDetail(c, 'cw')"
              >[片段{{ c.ref }}]</button>
              <span v-if="msg.knowledgeCitations?.length" class="citation-chips-label">知识库</span>
              <button
                v-for="c in msg.knowledgeCitations"
                :key="'kb-' + (c.docId || c.ref)"
                type="button"
                class="citation-chip citation-chip--kb"
                :title="(c.sourceName || '') + '，点击查看原文片段'"
                @click.stop="openCitationDetail(c, 'kb')"
              >[资料{{ c.ref }}]</button>
            </div>
          </div>
          
          <!-- 降维讲解卡片 -->
          <div v-else class="supplement-card">
            <div class="card-header">
              <el-icon><MagicStick /></el-icon> 节奏调整：AI 降维解析
            </div>
            <div class="card-body" v-html="formatMarkdown(msg.content)"></div>
            <div class="card-action">
              <el-button size="small" type="primary" class="brand-btn-outline" @click="$emit('resolve', index)"  v-if="!msg.resolved">
                我理解了，继续讲解
              </el-button>
              <span v-else class="resolved-txt"><el-icon><Select /></el-icon> 已掌握</span>
            </div>
          </div>
        </div>

        <!-- 用户头像：同上，连续用户消息只保留第一条头像 -->
        <div class="avatar" v-if="msg.role === 'user' && showUserAvatar(index)">
          <el-avatar :size="32" src="https://cube.elemecdn.com/3/7c/3ea6beec64369c2642b92c6726f1epng.png" class="brand-avatar-mini" />
        </div>
        <div
          v-else-if="msg.role === 'user'"
          class="avatar-spacer"
          aria-hidden="true"
        ></div>
      </div>

      <!-- 【新增】正在回答时的动效提示 -->
      <div v-if="isChatLoading" class="message-row ai loading-row">
        <div class="avatar" v-if="showLoadingAvatar">
          <img src="https://cdn-icons-png.flaticon.com/512/4712/4712027.png" />
        </div>
        <div v-else class="avatar-spacer" aria-hidden="true"></div>
        <div class="msg-content-wrapper">
          <div class="bubble loading-bubble">
            <span class="loading-dot"></span>
            <span class="loading-dot"></span>
            <span class="loading-dot"></span>
            <span class="loading-text">AI 正在深度思考...</span>
          </div>
        </div>
      </div>

    </div>

    <el-dialog
      v-model="citationDialogVisible"
      :title="citationDialogTitle"
      width="min(560px, 94vw)"
      align-center
      destroy-on-close
      class="citation-detail-dialog"
      append-to-body
    >
      <div class="citation-dialog-source">
        <span class="citation-dialog-source-label">来源</span>
        <span class="citation-dialog-source-name">{{ citationDialogSourceName }}</span>
      </div>
      <div class="citation-dialog-snippet-wrap">
        <div class="citation-dialog-snippet-label">引用片段</div>
        <div class="citation-dialog-snippet">{{ citationDialogSnippet }}</div>
      </div>
    </el-dialog>
  </div>
</template>


<script setup>
import { ref, watch, onUnmounted, nextTick, computed } from 'vue'
import { MagicStick, Select, Position } from '@element-plus/icons-vue'
import katex from 'katex'
import 'katex/dist/katex.min.css'

const props = defineProps(['mode', 'script', 'audioUrl', 'history', 'isChatLoading'])

/** 连续同角色消息只在第一条显示头像，其余用 avatar-spacer 对齐气泡 */
const showAiAvatar = (index) => {
  const h = props.history
  if (!h?.length || index < 0 || h[index]?.role !== 'ai') return false
  if (index === 0) return true
  return h[index - 1]?.role !== 'ai'
}

const showUserAvatar = (index) => {
  const h = props.history
  if (!h?.length || index < 0 || h[index]?.role !== 'user') return false
  if (index === 0) return true
  return h[index - 1]?.role !== 'user'
}

/** 加载条若接在上一条 AI 之后，不再重复机器人头像 */
const showLoadingAvatar = computed(() => {
  const h = props.history || []
  if (h.length === 0) return true
  return h[h.length - 1]?.role !== 'ai'
})

const displayContent = ref('')
const scrollRef = ref(null)

const citationDialogVisible = ref(false)
const citationDialogTitle = ref('')
const citationDialogSourceName = ref('')
const citationDialogSnippet = ref('')

const openCitationDetail = (c, kind) => {
  const isKb = kind === 'kb'
  const refLabel = isKb ? `资料${c?.ref}` : `片段${c?.ref}`
  const typeLabel = isKb ? '课程知识库' : '课件检索'
  citationDialogTitle.value = `[${refLabel}] · ${typeLabel}`
  citationDialogSourceName.value = (c?.sourceName || '').trim() || '—'
  const snip = (c?.snippet || '').trim()
  citationDialogSnippet.value = snip || '暂无片段正文，请结合课件或知识库原文核对。'
  citationDialogVisible.value = true
}

let typeTimer = null
let currentAudio = null
const emit = defineEmits(['resolve', 'speakContent', 'jumpToPage', 'chatTextSelected'])
// --- 断点记录状态 ---
const pausedTime = ref(0)
const pausedIndex = ref(0)
const lastAudioUrl = ref('')

// --- 防抖：避免重复触发文本选择 ---
let textSelectionTimeout = null
const isProcessingSelection = ref(false)

// --- 处理聊天消息文本选择 ---
const handleChatTextSelection = (event, msg) => {
  // 只处理AI消息的选择
  if (msg.role !== 'ai') return
  
  // 如果正在处理选择，忽略
  if (isProcessingSelection.value) return
  
  const selection = window.getSelection()
  const selectedText = selection?.toString().trim()
  
  if (selectedText && selectedText.length > 3) {
    // 阻止事件冒泡
    event.stopPropagation()
    
    // 清除之前的定时器
    if (textSelectionTimeout) {
      clearTimeout(textSelectionTimeout)
    }
    
    isProcessingSelection.value = true
    
    textSelectionTimeout = setTimeout(() => {
      // 尝试从原始内容中提取对应的文本（包括LaTeX公式）
      let textToSend = selectedText
      
      // 如果原始消息包含公式标记，尝试匹配并保留
      if (msg.content.includes('$')) {
        // 简单策略：如果选中的文本看起来像公式符号，尝试从原始内容中查找
        const originalContent = msg.content
        
        // 查找是否有匹配的LaTeX公式
        const formulaRegex = /\$([^\$]+?)\$/g
        let match
        while ((match = formulaRegex.exec(originalContent)) !== null) {
          const latexFormula = match[1]
          // 渲染这个公式看看是否匹配选中的文本
          try {
            const rendered = katex.renderToString(latexFormula, { 
              throwOnError: false, 
              displayMode: false 
            })
            // 创建临时元素来提取纯文本
            const tempDiv = document.createElement('div')
            tempDiv.innerHTML = rendered
            const renderedText = tempDiv.textContent || tempDiv.innerText
            
            // 如果选中的文本包含这个渲染后的公式，替换为LaTeX格式
            if (selectedText.includes(renderedText.trim())) {
              textToSend = textToSend.replace(renderedText.trim(), `$${latexFormula}$`)
            }
          } catch (e) {
            // 忽略错误
          }
        }
      }
      
      emit('chatTextSelected', {
        text: textToSend,
        originalMessage: msg.content
      })
      selection.removeAllRanges()
      
      // 重置处理状态
      setTimeout(() => {
        isProcessingSelection.value = false
      }, 500)
    }, 300)
  }
}

// --- Markdown格式化函数 ---
const formatMarkdown = (text) => {
  if (!text) return ''
  
  let formatted = text
  
  // 临时占位符，用于保护公式和代码块不被其他规则处理
  const protectedContent = []
  let placeholderIndex = 0
  
  // 0. 先提取代码块（保护特殊符号）
  formatted = formatted.replace(/```([^`]+)```/g, (match, code) => {
    const placeholder = `__PROTECTED_${placeholderIndex}__`
    protectedContent[placeholderIndex] = `<pre style="background: #F8FAFC; padding: 12px; border-radius: 8px; overflow-x: auto; margin: 0.5em 0; border: 1px solid #D2E6FE;"><code>${code.trim()}</code></pre>`
    placeholderIndex++
    return placeholder
  })
  
  // 行内代码
  formatted = formatted.replace(/`([^`]+)`/g, (match, code) => {
    const placeholder = `__PROTECTED_${placeholderIndex}__`
    protectedContent[placeholderIndex] = `<code style="background: #D2E6FE; color: #1442D3; padding: 2px 6px; border-radius: 4px; font-family: monospace;">${code}</code>`
    placeholderIndex++
    return placeholder
  })
  
  // 1. 提取并保存所有公式
  // 处理 \[ ... \] 块级公式
  formatted = formatted.replace(/\\\[([^\]]+?)\\\]/g, (match, formula) => {
    try {
      const rendered = katex.renderToString(formula.trim(), { 
        throwOnError: false, 
        displayMode: true 
      })
      const placeholder = `__PROTECTED_${placeholderIndex}__`
      protectedContent[placeholderIndex] = rendered
      placeholderIndex++
      return placeholder
    } catch (e) {
      console.error('KaTeX块级公式渲染失败:', e, formula)
      return match
    }
  })
  
  // 处理 \( ... \) 行内公式
  formatted = formatted.replace(/\\\(([^\)]+?)\\\)/g, (match, formula) => {
    try {
      const rendered = katex.renderToString(formula.trim(), { 
        throwOnError: false, 
        displayMode: false 
      })
      const placeholder = `__PROTECTED_${placeholderIndex}__`
      protectedContent[placeholderIndex] = rendered
      placeholderIndex++
      return placeholder
    } catch (e) {
      console.error('KaTeX行内公式渲染失败:', e, formula)
      return match
    }
  })
  
  // 处理块级公式 $$...$$
  formatted = formatted.replace(/\$\$([^\$]+?)\$\$/g, (match, formula) => {
    try {
      const rendered = katex.renderToString(formula.trim(), { 
        throwOnError: false, 
        displayMode: true 
      })
      const placeholder = `__PROTECTED_${placeholderIndex}__`
      protectedContent[placeholderIndex] = rendered
      placeholderIndex++
      return placeholder
    } catch (e) {
      console.error('KaTeX块级公式渲染失败:', e, formula)
      return match
    }
  })
  
  // 处理行内公式 $...$
  formatted = formatted.replace(/\$([^\$\n]+?)\$/g, (match, formula) => {
    try {
      const rendered = katex.renderToString(formula.trim(), { 
        throwOnError: false, 
        displayMode: false 
      })
      const placeholder = `__PROTECTED_${placeholderIndex}__`
      protectedContent[placeholderIndex] = rendered
      placeholderIndex++
      return placeholder
    } catch (e) {
      console.error('KaTeX行内公式渲染失败:', e, formula)
      return match
    }
  })
  
  // 2. 处理加粗 **text** 或 __text__
  formatted = formatted.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
  // 注意：不处理 __ 作为加粗，因为它可能是占位符的一部分
  
  // 3. 处理斜体 *text* 或 _text_
  formatted = formatted.replace(/\*([^*]+?)\*/g, '<em>$1</em>')
  // 注意：不处理 _ 作为斜体，因为它可能是占位符的一部分
  
  // 4. 处理换行（在恢复占位符之前）
  formatted = formatted.replace(/\n/g, '<br>')
  
  // 5. 处理列表项 - 数字列表
  formatted = formatted.replace(/^(\d+)\.\s+(.+)$/gm, '<div style="margin-left: 1em; margin-top: 0.5em;">$1. $2</div>')
  
  // 6. 处理列表项 - 无序列表
  formatted = formatted.replace(/^[-*]\s+(.+)$/gm, '<div style="margin-left: 1em; margin-top: 0.5em;">• $1</div>')
  
  // 7. 最后恢复所有受保护的内容（公式和代码块）
  protectedContent.forEach((content, index) => {
    const placeholder = `__PROTECTED_${index}__`
    formatted = formatted.replace(new RegExp(placeholder, 'g'), content)
  })
  
  return formatted
}

// --- 打字机效果（恢复流式输出） ---
const startTyping = (fullText, startIndex = 0) => {
  if (!fullText) return;
  
  if (startIndex === 0) {
    displayContent.value = '';
  }
  
  let i = startIndex;
  if (typeTimer) clearInterval(typeTimer);
  
  typeTimer = setInterval(() => {
    const rawText = fullText.slice(0, i + 1);
    displayContent.value = formatMarkdown(rawText);
    i++;
    
    pausedIndex.value = i;

    scrollToBottom();
    if (i >= fullText.length) {
      clearInterval(typeTimer);
      // 【关键修改】打字机完成后不清空断点，保留位置
      // clearBreakPoint();
      console.log(`[打字机] 完成，保留断点位置: ${pausedIndex.value}`);
    }
  }, 50);
}

// 清除断点
const clearBreakPoint = () => {
  pausedTime.value = 0;
  pausedIndex.value = 0;
}

const scrollToBottom = () => {
  nextTick(() => {
    if (scrollRef.value) {
      scrollRef.value.scrollTop = scrollRef.value.scrollHeight;
    }
  });
}

// --- 模式切换监听 ---
watch(() => props.mode, (newMode, oldMode) => {
  if (oldMode === 'lecture' && newMode === 'chat') {
    if (currentAudio) {
      pausedTime.value = currentAudio.currentTime;
      currentAudio.pause();
    }
    if (typeTimer) clearInterval(typeTimer);
    console.log(`[打断] 已记录位置：时间 ${pausedTime.value}s, 索引 ${pausedIndex.value}`);
  } 
  
  else if (newMode === 'lecture') {
    if (props.script) {
      console.log(`[恢复] 显示讲解内容`);
      startTyping(props.script, pausedIndex.value);
    }
  }
});

// --- 翻页监听 ---
watch(() => props.audioUrl, (newUrl) => {
  if (newUrl !== lastAudioUrl.value) {
    // 只有真正翻页时才清空断点
    clearBreakPoint();
    lastAudioUrl.value = newUrl;
    if (props.mode === 'lecture' && newUrl) {
      startTyping(props.script, 0);
    }
  }
}, { immediate: true });

// --- 问答历史监听 ---
watch(() => props.history, () => {
  if (props.mode === 'chat') {
    scrollToBottom();
  }
}, { deep: true });

// --- 讲稿内容监听（不触发数字人播放，由 DigitalAvatar 组件的 watch 处理）---
watch(() => props.script, (newVal) => {
  // 1. 如果收到了空字符串（由 index.vue 的 startLecture 触发）
  if (newVal === '') {
    if (currentAudio) currentAudio.pause();
    if (typeTimer) clearInterval(typeTimer);
    
    clearBreakPoint();
    displayContent.value = '';
    return;
  }

  // 2. 如果是正常的内容加载或恢复（使用打字机效果）
  if (props.mode === 'lecture' && newVal) {
    startTyping(newVal, pausedIndex.value);
  }
}, { immediate: true });


onUnmounted(() => {
  if (currentAudio) currentAudio.pause();
  if (typeTimer) clearInterval(typeTimer);
});
</script>

<style scoped>
/* 严格遵循品牌四色 */
.chat-area {
  --primary-blue: #307AE3;
  --dark-blue: #1442D3;
  --light-blue: #D2E6FE;
  --lavender: #ACB1EC;
  --bg-color: #FFFFFF;
  --text-main: #1E293B;
  --text-sub: #64748B;
  
  flex: 1; 
  overflow-y: auto; 
  padding: 24px; 
  background-color: var(--bg-color); 
  scroll-behavior: smooth; 
  margin-top: 0; 
}

/* 通用按钮/组件映射 */
.brand-btn { 
  background: linear-gradient(135deg, var(--primary-blue), var(--dark-blue)) !important; 
  border: none !important; 
  box-shadow: 0 4px 12px rgba(48, 122, 227, 0.2) !important; 
  border-radius: 12px !important; 
  color: #FFF !important;
}
.brand-btn:hover { 
  transform: translateY(-2px); 
  box-shadow: 0 6px 16px rgba(20, 66, 211, 0.3) !important; 
}
.brand-btn-outline { 
  border: 1px solid var(--primary-blue) !important; 
  color: var(--primary-blue) !important; 
  background: transparent !important; 
  border-radius: 12px !important; 
}
.brand-btn-outline:hover { 
  background: var(--primary-blue) !important; 
  color: #fff !important; 
}
.brand-avatar-mini { 
  border: 2px solid var(--light-blue); 
}

/* 基础布局样式 */
.ai-message { 
  display: flex; 
  gap: 14px; 
}
.avatar img { 
  width: 36px; 
  height: 36px; 
  border-radius: 50%; 
  box-shadow: 0 4px 12px rgba(48, 122, 227, 0.15); 
  border: 2px solid var(--light-blue);
}

/* 与 .avatar 同宽，用于对齐连续消息的气泡，不占视觉头像 */
.avatar-spacer {
  width: 36px;
  min-width: 36px;
  flex-shrink: 0;
  align-self: flex-start;
}
.message-row.user .avatar-spacer {
  align-self: flex-start;
  width: 32px;
  min-width: 32px;
}
.message-content { 
  flex: 1; 
}
.ai-name { 
  font-size: 13px; 
  color: var(--text-sub); 
  margin-bottom: 6px; 
  font-weight: 600; 
  padding-left: 4px;
}

/* 消息气泡核心样式 */
.bubble { 
  padding: 14px 18px; 
  border-radius: 16px; 
  font-size: 15px; 
  line-height: 1.6; 
  background: #FFFFFF; 
  word-wrap: break-word;
  user-select: text;
  -webkit-user-select: text;
  -moz-user-select: text;
  cursor: text;
  box-shadow: 0 4px 16px rgba(48, 122, 227, 0.05);
  transition: all 0.3s ease;
  border: 1px solid var(--light-blue); 
  font-weight: 500;
  color: var(--text-main);
}
.bubble:hover {
  box-shadow: 0 6px 20px rgba(48, 122, 227, 0.1);
  border-color: var(--primary-blue);
}

/* Markdown格式化样式 */
.bubble :deep(strong) { font-weight: 800; color: var(--dark-blue); }
.bubble :deep(em) { font-style: italic; color: var(--text-sub); }
.bubble :deep(br) { display: block; content: ""; margin: 0.5em 0; }
.bubble :deep(.katex) { font-size: 1.1em; user-select: text; cursor: text; color: var(--dark-blue); font-weight: 600;}
.bubble :deep(.katex-display) { margin: 1em 0; text-align: center; }

/* 讲解模式气泡 */
.lecture-bubble { 
  border-radius: 0 16px 16px 16px; 
  background: #F8FAFC; 
  border-color: var(--light-blue); 
}

/* 聊天列表样式 */
.message-row { 
  display: flex; 
  gap: 14px; 
  margin-bottom: 24px; 
  align-items: flex-start; 
}
.message-row.user { 
  flex-direction: row-reverse; 
}
.message-row.user .bubble { 
  background: linear-gradient(135deg, var(--primary-blue), var(--dark-blue)); 
  color: #FFFFFF; 
  border-radius: 16px 0 16px 16px; 
  border: none;
  box-shadow: 0 6px 16px rgba(20, 66, 211, 0.25); 
  font-weight: 600;
}
.message-row.user .bubble:hover {
  box-shadow: 0 8px 24px rgba(20, 66, 211, 0.35);
}

.msg-content-wrapper { 
  max-width: 85%; 
}

/* 降维讲解卡片 - 使用薰衣草蓝作为底色，突出AI的柔和辅导 */
.supplement-card { 
  background: #F8FAFC; 
  border: 1px solid var(--lavender); 
  border-radius: 16px; 
  padding: 20px; 
  box-shadow: 0 6px 16px rgba(172, 177, 236, 0.15); 
  transition: all 0.3s ease;
}
.supplement-card:hover {
  box-shadow: 0 8px 24px rgba(172, 177, 236, 0.25);
  border-color: var(--primary-blue);
}
.card-header { 
  color: var(--primary-blue); 
  font-weight: 800; 
  font-size: 15px; 
  margin-bottom: 12px; 
  display: flex; 
  align-items: center; 
  gap: 8px; 
}
.card-body { 
  font-size: 15px; 
  color: var(--text-main); 
  line-height: 1.6; 
  font-weight: 500;
}
.card-action { 
  display: flex; 
  justify-content: flex-end; 
  margin-top: 16px; 
}

/* 已掌握状态文本 */
.resolved-txt { 
  font-size: 14px; 
  color: var(--primary-blue); 
  font-weight: 700; 
  display: flex; 
  align-items: center; 
  gap: 6px; 
  padding: 8px 16px;
  background: var(--light-blue);
  border-radius: 12px;
}

/* 跳转按钮样式 */
.jump-to-page {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--light-blue);
}

.vision-model-tag {
  font-size: 11px;
  color: var(--primary-blue);
  font-weight: 600;
  margin-bottom: 8px;
  padding: 4px 10px;
  background: rgba(48, 122, 227, 0.08);
  border-radius: 8px;
  display: inline-block;
}
/* 溯源：仅冒泡标记，正文不展开 */
.citation-chips {
  margin-top: 10px;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px 8px;
  text-align: left;
}
.citation-chips-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-sub);
  margin-right: 2px;
}
.citation-chip {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  font-size: 12px;
  font-weight: 700;
  border-radius: 999px;
  line-height: 1.2;
  cursor: pointer;
  border: 1px solid transparent;
  font-family: inherit;
  margin: 0;
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}
.citation-chip:focus-visible {
  outline: 2px solid var(--primary-blue);
  outline-offset: 2px;
}
.citation-chip:hover {
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(48, 122, 227, 0.15);
}
.citation-chip--cw {
  color: var(--dark-blue);
  background: rgba(48, 122, 227, 0.1);
  border-color: rgba(48, 122, 227, 0.25);
}
.citation-chip--kb {
  color: #15803d;
  background: rgba(20, 120, 80, 0.1);
  border-color: rgba(20, 120, 80, 0.22);
}
.citation-chip--kb:hover {
  box-shadow: 0 2px 8px rgba(20, 120, 80, 0.12);
}

.citation-dialog-source {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 8px;
  margin-bottom: 14px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--light-blue, #D2E6FE);
}
.citation-dialog-source-label {
  font-size: 12px;
  font-weight: 700;
  color: var(--text-sub, #64748B);
  flex-shrink: 0;
}
.citation-dialog-source-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-main, #1E293B);
  word-break: break-word;
}
.citation-dialog-snippet-label {
  font-size: 12px;
  font-weight: 700;
  color: var(--text-sub, #64748B);
  margin-bottom: 8px;
}
.citation-dialog-snippet {
  font-size: 14px;
  line-height: 1.65;
  color: var(--text-main, #1E293B);
  white-space: pre-wrap;
  word-break: break-word;
  max-height: min(50vh, 360px);
  overflow-y: auto;
  padding: 12px 14px;
  background: #F8FAFC;
  border-radius: 12px;
  border: 1px solid rgba(48, 122, 227, 0.12);
}

/* 加载中动画样式 */
.loading-row { 
  margin-top: 10px; 
}
.loading-bubble { 
  display: flex; 
  align-items: center; 
  gap: 10px; 
  padding: 14px 24px; 
  background: var(--bg-color) !important; 
  color: var(--text-sub); 
  font-size: 14px; 
  border-radius: 16px;
  border: 1px solid var(--light-blue);
}
.loading-dot {
  width: 8px; 
  height: 8px; 
  background-color: var(--primary-blue); 
  border-radius: 50%;
  animation: bounce 1.4s infinite ease-in-out both;
}
.loading-dot:nth-child(1) { animation-delay: -0.32s; }
.loading-dot:nth-child(2) { animation-delay: -0.16s; }
.loading-text { 
  margin-left: 6px; 
  color: var(--primary-blue); 
  font-size: 14px; 
  font-weight: 600;
}

@keyframes bounce {
  0%, 80%, 100% { transform: scale(0); }
  40% { transform: scale(1); }
}

/* 响应式适配 */
@media (max-width: 768px) {
  .chat-area {
    padding: 16px;
  }
  .msg-content-wrapper {
    max-width: 90%;
  }
  .bubble {
    padding: 12px 16px;
    font-size: 14px;
  }
  .supplement-card {
    padding: 16px;
  }
}
</style>