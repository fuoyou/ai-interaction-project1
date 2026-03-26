<template>
  <div class="input-area">
    <!-- 讲解模式：快捷操作区 -->
    <div class="quick-actions" v-if="mode === 'lecture'">
      <el-button class="glass-btn brand-btn-outline" round size="small" @click="$emit('replay')">
        <el-icon><RefreshLeft /></el-icon> 重讲本页
      </el-button>
      <el-button class="glass-btn-primary brand-btn" round size="small" type="primary" @click="$emit('switchToChat')">
        <el-icon><QuestionFilled /></el-icon> 我有疑问
      </el-button>
    </div>
    
    <!-- 问答模式：预设问题 + 输入框 -->
    <div v-else class="chat-input-wrapper">
      <!-- 预设问题：移动端可以横向滚动 -->
      <div class="preset-questions">
        <el-tag 
          v-for="(question, index) in presetQuestions" 
          :key="index"
          class="question-tag glass-tag brand-tag"
          @click="handlePresetQuestion(question)"
          effect="plain"
          size="small"
        >
          {{ question }}
        </el-tag>
      </div>
      
      <!-- 输入框区域 -->
      <div class="input-box-wrapper">
        <!-- 语音录制遮罩 -->
        <div v-if="isRecording" class="recording-overlay glass-overlay">
          <div class="recording-wave"></div>
          <p>正在聆听...</p>
          <span class="recording-hint">松开结束</span>
        </div>

        <el-input 
          v-model="internalValue" 
          :placeholder="isRecording ? '正在识别...' : placeholder" 
          @keyup.enter="handleSend"
          class="input-field glass-input"
        >
          <template #prefix>
            <el-tooltip content="长按录音提问" placement="top">
              <el-icon 
                class="mic-icon" 
                :class="{ 'is-active': isRecording }"
                @mousedown="startRealRecording" 
                @mouseup="stopRealRecording"
                @mouseleave="stopRealRecording"
                @touchstart="startRealRecording"
                @touchend="stopRealRecording"
              >
                <Microphone />
              </el-icon>
            </el-tooltip>
          </template>
          <template #suffix>
            <el-button class="send-btn brand-btn-circle" circle type="primary" @click="handleSend" :disabled="!internalValue.trim()">
              <el-icon><Position /></el-icon>
            </el-button>
          </template>
        </el-input>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { RefreshLeft, QuestionFilled, Microphone, Position } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const props = defineProps(['modelValue', 'mode', 'placeholder'])
const emit = defineEmits(['update:modelValue', 'send', 'replay', 'switchToChat'])

const internalValue = ref(props.modelValue)
const isRecording = ref(false)

const presetQuestions = ref([
  '这个知识点能再讲详细一点吗？',
  '能举个例子说明吗？',
  '这一页的重点是什么？',
  '我不太理解，能换个说法吗？'
])

let recognition = null
onMounted(() => {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
  if (SpeechRecognition) {
    recognition = new SpeechRecognition()
    recognition.continuous = false
    recognition.lang = 'zh-CN'
    recognition.interimResults = true
    recognition.onresult = (event) => {
      internalValue.value = event.results[event.results.length - 1][0].transcript
    }
    recognition.onend = () => { isRecording.value = false }
  }
})

watch(() => props.modelValue, (val) => internalValue.value = val)
watch(internalValue, (val) => emit('update:modelValue', val))

const handleSend = () => { if (internalValue.value.trim()) emit('send') }
const handlePresetQuestion = (question) => { internalValue.value = question; emit('send') }

const startRealRecording = (e) => {
  e.preventDefault()
  if (!recognition) return ElMessage.warning('不支持语音识别')
  isRecording.value = true
  internalValue.value = ''
  recognition.start()
}
const stopRealRecording = () => { if (recognition && isRecording.value) recognition.stop() }
</script>

<style scoped>
/* 严格遵循品牌四色 */
.input-area {
  --primary-blue: #307AE3;
  --dark-blue: #1442D3;
  --light-blue: #D2E6FE;
  --lavender: #ACB1EC;
  
  padding: 20px; 
  background: #FFFFFF; 
  border-top: 1px solid var(--light-blue); 
  flex-shrink: 0; 
}

/* 按钮通用类 */
.brand-btn { 
  background: linear-gradient(135deg, var(--primary-blue), var(--dark-blue)) !important; 
  border: none !important; 
  box-shadow: 0 4px 12px rgba(48, 122, 227, 0.2) !important; 
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
}
.brand-btn-outline:hover { 
  background: var(--primary-blue) !important; 
  color: #fff !important; 
}

/* 讲解模式快捷操作 */
.quick-actions { 
  display: flex; 
  gap: 16px; 
  justify-content: center;
  flex-wrap: wrap;
}

.glass-btn, .glass-btn-primary {
  font-weight: 700;
  border-radius: 16px !important;
  padding: 10px 24px !important;
  transition: all 0.3s ease;
  font-size: 14px !important;
}

/* 问答模式预设问题 */
.preset-questions{
  display: flex; 
  overflow-x: auto; 
  gap: 10px; 
  margin-bottom: 16px; 
  padding-bottom: 5px; 
  scrollbar-width: none;
}
.preset-questions::-webkit-scrollbar { display: none; }

.brand-tag {
  cursor: pointer; 
  white-space: nowrap;
  border: 1px solid var(--light-blue) !important;
  color: var(--dark-blue) !important;
  background: #F8FAFC !important;
  border-radius: 12px !important;
  padding: 6px 14px !important;
  transition: all 0.3s ease;
  font-weight: 600;
  font-size: 13px;
}

.brand-tag:hover { 
  border-color: var(--primary-blue) !important; 
  color: var(--primary-blue) !important; 
  background: var(--light-blue) !important;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(48, 122, 227, 0.1);
}

/* 输入框区域 */
.input-box-wrapper {
  position: relative;
}

.glass-input :deep(.el-input__wrapper) { 
  background: #F8FAFC;
  border-radius: 24px; 
  padding: 10px 20px;
  box-shadow: 0 0 0 1px var(--light-blue) inset !important; 
  transition: all 0.3s ease;
  border: none !important;
  height: 56px;
}

.glass-input :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 2px var(--primary-blue) inset !important;
  background: #FFFFFF !important;
}

.glass-input :deep(.el-input__inner) {
  font-size: 15px;
  color: #1E293B;
  font-weight: 500;
}

/* 麦克风图标 */
.mic-icon { 
  cursor: pointer; 
  color: var(--lavender); 
  font-size: 22px; 
  transition: all 0.2s ease; 
  padding: 5px; 
}

.mic-icon:hover { 
  color: var(--primary-blue);
  transform: scale(1.1);
}

.mic-icon.is-active { 
  color: var(--primary-blue); 
  transform: scale(1.2);
  animation: mic-pulse 1s infinite ease-in-out;
}

@keyframes mic-pulse {
  0%, 100% { transform: scale(1.2); }
  50% { transform: scale(1.4); }
}

/* 发送按钮 */
.brand-btn-circle {
  background: linear-gradient(135deg, var(--primary-blue), var(--dark-blue)) !important; 
  border: none !important;
  box-shadow: 0 4px 12px rgba(48, 122, 227, 0.2) !important;
  border-radius: 50% !important;
  width: 40px;
  height: 40px;
  min-width: 40px;
  transition: all 0.3s ease !important;
}

.brand-btn-circle:hover {
  box-shadow: 0 6px 16px rgba(20, 66, 211, 0.3) !important;
  transform: translateY(-2px);
}

.brand-btn-circle:disabled {
  background: var(--lavender) !important;
  box-shadow: none !important;
  transform: none !important;
}

/* 录音遮罩 */
.glass-overlay {
  position: absolute; 
  bottom: 80px; 
  left: 50%; 
  transform: translateX(-50%);
  padding: 24px; 
  border-radius: 20px; 
  width: 180px; 
  text-align: center;
  background: linear-gradient(135deg, rgba(20, 66, 211, 0.95) 0%, rgba(48, 122, 227, 0.85) 100%);
  backdrop-filter: blur(16px);
  color: #fff;
  box-shadow: 0 12px 32px rgba(20, 66, 211, 0.3);
  border: 1px solid rgba(255, 255, 255, 0.1);
  z-index: 10;
}

.recording-wave {
  width: 56px; 
  height: 56px; 
  background: #FFFFFF; 
  border-radius: 50%; 
  margin: 0 auto 16px;
  animation: pulse 1s infinite cubic-bezier(0.4, 0, 0.6, 1);
  opacity: 0.9;
}

@keyframes pulse {
  0% { transform: scale(0.9); box-shadow: 0 0 0 0 rgba(255, 255, 255, 0.7); }
  70% { transform: scale(1.1); box-shadow: 0 0 0 20px rgba(48, 122, 227, 0); }
  100% { transform: scale(0.9); box-shadow: 0 0 0 0 rgba(48, 122, 227, 0); }
}

.recording-hint {
  font-size: 13px;
  opacity: 0.8;
  margin-top: 6px;
  display: block;
  font-weight: 600;
}

/* 响应式适配 */
@media screen and (max-width: 768px) {
  .input-area { padding: 16px; }
  .glass-btn, .glass-btn-primary { padding: 8px 16px !important; }
  .glass-input :deep(.el-input__wrapper) { height: 48px; }
}
</style>