<template>
  <!-- 最外层容器：包裹所有内容 -->
  <div class="digital-avatar-fullscreen" :class="{ 'audio-only': !showAvatar }">
    
    <!-- 1. 数字人显示区域 -->
    <div v-show="showAvatar" class="avatar-container">
      <iframe 
        ref="avatarIframe"
        :src="avatarUrl" 
        frameborder="0"
        class="avatar-iframe"
        scrolling="no"
        allow="autoplay; microphone" 
        @load="onIframeLoad"
      ></iframe>
      <div class="overlay-top"></div>
      <div class="overlay-bottom"></div>
    </div>
    
    <!-- 2. 纯语音模式指示器 -->
    <div v-show="!showAvatar" class="audio-only-indicator">
      <div class="audio-wave" v-if="isSpeaking">
        <span></span><span></span><span></span><span></span><span></span>
      </div>
      <div class="audio-icon" v-else>
        <el-icon><Microphone /></el-icon>
      </div>
      <span class="audio-text">{{ isSpeaking ? '正在语音讲解...' : '语音伴读模式' }}</span>
    </div>

    <!-- 3. 左下角主控制面板 -->
    <div class="control-panel">
      <div class="panel-header">
        <span class="title"><el-icon><VideoCamera /></el-icon> AI 数字讲师</span>
      </div>
      <div class="panel-content">
        <div class="status-info" :class="isSpeaking ? 'speaking' : (isPaused ? 'paused' : 'ready')">
          <div :class="isSpeaking ? 'pulse-dot' : 'static-dot'"></div>
          <span>{{ isSpeaking ? '正在实时讲解...' : (isPaused ? '已暂停答疑中' : 'AI 讲师已就绪') }}</span>
        </div>
        
        <!-- 手势控制按钮 -->
        <el-button 
          size="small" 
          round
          plain
          @click="toggleGesturePanel" 
          class="gesture-btn brand-btn-outline"
        >
          <el-icon><Operation /></el-icon> 手势控制
        </el-button>
      </div>
    </div>

    <!-- 4. 手势控制悬浮面板 -->
    <transition name="slide-up">
      <div v-show="showGesturePanel" class="gesture-panel">
        <div class="gesture-header">
          <span class="header-title">✨ 快捷手势</span>
          <el-icon @click="showGesturePanel = false" class="close-icon"><Close /></el-icon>
        </div>
        <div class="gesture-buttons">
          <el-button @click="setGesture('wave')" class="brand-btn-outline">
            <span class="gesture-emoji">👋</span> 挥手
          </el-button>
          <el-button @click="setGesture('pointLeft')" class="brand-btn-outline">
            <span class="gesture-emoji">👈</span> 指左
          </el-button>
          <el-button @click="setGesture('pointRight')" class="brand-btn-outline">
            <span class="gesture-emoji">👉</span> 指右
          </el-button>
          <el-button @click="setGesture('welcome')" class="brand-btn-outline">
            <span class="gesture-emoji">🤗</span> 欢迎
          </el-button>
          <el-button @click="setGesture('thinking')" class="brand-btn-outline">
            <span class="gesture-emoji">🤔</span> 思考
          </el-button>
          <el-button @click="setGesture('reset')" class="brand-btn-outline">
            <span class="gesture-emoji">↺</span> 重置
          </el-button>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, onUnmounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { VideoCamera, Operation, Close, Microphone } from '@element-plus/icons-vue'
import axios from 'axios'

// 动态计算数字人服务地址
const avatarUrl = computed(() => {
  // 获取当前主机地址，将前端地址的端口改为 3000
  const host = window.location.hostname
  return `http://${host}:3000/sentio`
})

const props = defineProps({
  script: String,
  page: Number,
  speakText: String,
  mode: String,
  totalPages: Number,
  isRhythmAdjusting: Boolean,
  showAvatar: { type: Boolean, default: true },
  showWindow: { type: Boolean, default: true }
})

const emit = defineEmits(['autoNextPage', 'speaking'])

watch(() => props.showAvatar, (newVal, oldVal) => {
  if (newVal !== oldVal) {
    let resumeTime = 0
    if (!newVal && audioOnlyPlayer.value) { resumeTime = audioOnlyPlayer.value.currentTime || 0 }
    if (globalAudioManager.value) globalAudioManager.value.stopAll()
    if (audioOnlyPlayer.value) { audioOnlyPlayer.value.pause(); audioOnlyPlayer.value = null }
    postMsg('STOP_SPEAK')
    isSpeaking.value = false; isPaused.value = false; isPlaying.value = false 
    emit('speaking', false)
    if (props.mode === 'lecture' && props.script && props.script.length > 5) {
      isInitialized.value = true; lastSpokenScript.value = '';
      if (newVal === true && !iframeReady.value) { pendingScript.value = props.script; return; }
      setTimeout(() => {
        postMsg('STOP_SPEAK')
        if (newVal === true && iframeReady.value) postMsg('UPDATE_TTS_CONFIG', { config: ttsConfig.value });
        speakWithGesture(props.script, null, false, resumeTime);
      }, 300);
    }
  }
})

const avatarIframe = ref(null); const isSpeaking = ref(false); const isPaused = ref(false); const lastSpokenScript = ref(''); const audioOnlyPlayer = ref(null); const audioOnlyPausedTime = ref(0); const audioOnlyCurrentText = ref(''); const iframeReady = ref(false); const pendingScript = ref(''); const isPlaying = ref(false); const isInitialized = ref(false); const abortController = ref(null); 
const ttsConfig = ref({ rate: -5, volume: 0, pitch: 2 })
const emotionPresets = { neutral: { rate: -5, pitch: 2, volume: 0, name: '中性讲解' }, emphasis: { rate: -10, pitch: 6, volume: 8, name: '重点强调' }, 启发: { rate: -8, pitch: 4, volume: 3, name: '启发提问' }, excited: { rate: 5, pitch: 8, volume: 10, name: '兴奋总结' }, gentle: { rate: -8, pitch: -2, volume: -3, name: '温柔安抚' }, serious: { rate: -5, pitch: 3, volume: 5, name: '严肃警示' } }
const emotionKeywordMap = { emphasis: ['公式', '结论', '定理', '定律', '记住', '注意', '关键', '重要', '必须', '一定', '易错', '难点', '重点'], 启发: ['大家想想', '为什么', '思考一下', '你们觉得', '如何理解', '怎么解释', '想想看'], excited: ['总结一下', '回顾一下', '课程亮点', '精彩部分', '最重要的', '核心内容', '总而言之'], gentle: ['别担心', '慢慢来', '理解一下', '仔细听', '鼓励', '加油', '没关系'], serious: ['警告', '注意', '误区', '错误', '不能', '禁止', '务必', '千万', '小心'] }

const detectEmotion = (text) => { if (!text) return 'neutral'; for (const [emotion, keywords] of Object.entries(emotionKeywordMap)) { for (const keyword of keywords) { if (text.includes(keyword)) return emotion; } } return 'neutral' }
const applyEmotion = (emotion) => { const preset = emotionPresets[emotion] || emotionPresets.neutral; ttsConfig.value = { rate: preset.rate, pitch: preset.pitch, volume: preset.volume } }

const showGesturePanel = ref(false); let gestureKeepAliveTimer = null; const currentGesture = ref('pointLeft');
const gesturePresets = { wave: { rightHand: 0.5, rightArmA: 8.0, rightArmB: 5.0 }, pointLeft: { leftHand: -0.8, leftArmA: 6.0, leftArmB: 8.0 }, pointRight: { rightHand: -0.8, rightArmA: 6.0, rightArmB: 8.0 }, pointPPT: { leftHand: -0.8, leftArmA: 6.0, leftArmB: 8.0, rightHand: 0.2, rightArmA: 0.5, rightArmB: 0.5 }, welcome: { leftHand: -0.5, rightHand: -0.5, leftArmA: 7.0, rightArmA: 7.0, leftArmB: 4.0, rightArmB: 4.0 }, thinking: { rightHand: 0.3, rightArmA: 5.0, rightArmB: 8.0 }, reset: { leftHand: 0, rightHand: 0, leftArmA: 0, rightArmA: 0, leftArmB: 0, rightArmB: 0 } }

const postMsg = (type, data = {}) => { if (avatarIframe.value && iframeReady.value) { avatarIframe.value.contentWindow.postMessage({ type, ...data }, '*') } }
const forceStopAll = () => { stopAudioOnly(); postMsg('STOP_SPEAK'); isSpeaking.value = false; isPaused.value = true; emit('speaking', false); }
const pauseAudio = () => { if (!props.showAvatar) { if (audioOnlyPlayer.value) { audioOnlyPausedTime.value = audioOnlyPlayer.value.currentTime; audioOnlyPlayer.value.pause(); } isSpeaking.value = false; isPaused.value = true; emit('speaking', false); return; } postMsg('PAUSE_SPEAK', { currentText: props.script }); isSpeaking.value = false; isPaused.value = true; emit('speaking', false); }
const resumeAudio = async () => { isPaused.value = false; if (!props.showAvatar) { if (audioOnlyPausedTime.value > 0 && audioOnlyCurrentText.value) { await speakWithEdgeTTS(audioOnlyCurrentText.value, false, audioOnlyPausedTime.value); } else if (props.script) { await speakWithEdgeTTS(props.script); } return; } postMsg('RESUME_SPEAK', { resumeText: props.script, ttsConfig: { rate: ttsConfig.value.rate, volume: ttsConfig.value.volume, pitch: ttsConfig.value.pitch } }) }
const setGesture = (gestureName) => { const gesture = gesturePresets[gestureName]; if (gesture && iframeReady.value) { postMsg('SET_HAND_GESTURE', { gesture }); currentGesture.value = gestureName; } }
const startGestureKeepAlive = () => { if (gestureKeepAliveTimer) clearInterval(gestureKeepAliveTimer); gestureKeepAliveTimer = setInterval(() => { if (iframeReady.value && currentGesture.value) { const gesture = gesturePresets[currentGesture.value]; if (gesture) { postMsg('SET_HAND_GESTURE', { gesture }); } } }, 2000) }
const stopGestureKeepAlive = () => { if (gestureKeepAliveTimer) { clearInterval(gestureKeepAliveTimer); gestureKeepAliveTimer = null; } }
const updateTtsConfig = (isAdjusting) => { if (isAdjusting) { ttsConfig.value = { rate: -15, volume: 0, pitch: 2 } } else { ttsConfig.value = { rate: 0, volume: 0, pitch: 0 } } }
const globalAudioManager = ref(null); const setGlobalAudioManager = (manager) => { globalAudioManager.value = manager }; 
const stopAudioOnly = () => { if (abortController.value) { abortController.value.abort(); abortController.value = null; } if (audioOnlyPlayer.value) { audioOnlyPlayer.value.pause(); audioOnlyPlayer.value.currentTime = 0; audioOnlyPlayer.value = null; } audioOnlyPausedTime.value = 0; audioOnlyCurrentText.value = ''; isSpeaking.value = false; isPlaying.value = false; emit('speaking', false); }

const speakWithEdgeTTS = async (text, isInterrupt = false, resumeFrom = 0) => {
  if (!text || text.trim().length === 0) return;
  if (!isInterrupt) stopAudioOnly(); stopAudioOnly(); audioOnlyCurrentText.value = text; abortController.value = new AbortController();
  try {
    const response = await axios.post('http://localhost:8880/adh/tts/v0/engine', { engine: 'EdgeTTS', config: { voice: 'zh-CN-XiaoxiaoNeural', rate: ttsConfig.value.rate, volume: ttsConfig.value.volume, pitch: ttsConfig.value.pitch }, data: text }, { timeout: 60000, signal: abortController.value.signal })
    if (response.data && response.data.data) {
      const audioData = response.data.data; const byteCharacters = atob(audioData); const byteNumbers = new Array(byteCharacters.length);
      for (let i = 0; i < byteCharacters.length; i++) { byteNumbers[i] = byteCharacters.charCodeAt(i); }
      const byteArray = new Uint8Array(byteNumbers); const audioBlob = new Blob([byteArray], { type: 'audio/mp3' }); const audioUrl = URL.createObjectURL(audioBlob);
      const audio = new Audio(audioUrl); audioOnlyPlayer.value = audio;
      if (globalAudioManager.value) globalAudioManager.value.play(audio, audioUrl);
      if (resumeFrom > 0) audio.currentTime = resumeFrom;
      audio.onplay = () => { isSpeaking.value = true; emit('speaking', true); }
      audio.onended = () => { isSpeaking.value = false; emit('speaking', false); if (props.mode === 'lecture' && !isPaused.value) emit('autoNextPage'); if (globalAudioManager.value && globalAudioManager.value.currentAudio === audio) globalAudioManager.value.stopAll(); else URL.revokeObjectURL(audioUrl); audioOnlyPlayer.value = null; audioOnlyPausedTime.value = 0; isPlaying.value = false; }
      audio.onerror = (e) => { isSpeaking.value = false; emit('speaking', false); if (globalAudioManager.value && globalAudioManager.value.currentAudio === audio) globalAudioManager.value.stopAll(); else URL.revokeObjectURL(audioUrl); audioOnlyPlayer.value = null; isPlaying.value = false; }
      await audio.play();
    } else { ElMessage.error('语音合成失败'); isPlaying.value = false; }
  } catch (error) { if (error.name === 'CanceledError' || error.name === 'AbortError') return; ElMessage.error('语音合成服务调用失败'); isPlaying.value = false; }
}

const speakWithGesture = async (text, gesture = null, isInterrupt = false, resumeFrom = 0) => {
  if (globalAudioManager.value) globalAudioManager.value.stopAll();
  stopAudioOnly(); postMsg('STOP_SPEAK'); setTimeout(() => postMsg('STOP_SPEAK'), 50);
  const emotion = detectEmotion(text); applyEmotion(emotion);
  if (!props.showAvatar) { await speakWithEdgeTTS(text, isInterrupt, resumeFrom); return; }
  const targetGesture = 'pointLeft'; setGesture(targetGesture);
  const currentTtsConfig = { ...ttsConfig.value };
  isPlaying.value = true;
  setTimeout(() => { isSpeaking.value = true; emit('speaking', true); postMsg('DIRECT_SPEAK', { text, isInterrupt, config: currentTtsConfig }); }, 300);
}

const onIframeLoad = () => { iframeReady.value = true; setGesture('pointLeft'); startGestureKeepAlive(); if (pendingScript.value && props.mode === 'lecture') { speakWithGesture(pendingScript.value); pendingScript.value = ''; } }
const toggleGesturePanel = () => { showGesturePanel.value = !showGesturePanel.value }

watch(() => props.mode, (newMode, oldMode) => {
  if (oldMode === 'lecture' && newMode === 'chat') { pauseAudio(); if (props.showAvatar) { stopGestureKeepAlive(); setGesture('thinking'); if (iframeReady.value) { gestureKeepAliveTimer = setInterval(() => { const gesture = gesturePresets['thinking']; if (gesture) postMsg('SET_HAND_GESTURE', { gesture }); }, 2000) } } } 
  else if (newMode === 'lecture' && oldMode === 'chat') { if (props.showAvatar) { stopGestureKeepAlive(); setGesture('pointLeft'); startGestureKeepAlive(); } if (isPaused.value) resumeAudio(); }
})
watch(() => props.isRhythmAdjusting, (isAdjusting) => { updateTtsConfig(isAdjusting); if (isSpeaking.value && iframeReady.value) { postMsg('UPDATE_TTS_CONFIG', { config: { rate: ttsConfig.value.rate, volume: ttsConfig.value.volume, pitch: ttsConfig.value.pitch } }); } }, { immediate: true })
watch(() => props.speakText, (newText, oldText) => { if (newText && newText.length > 0 && newText !== oldText) { if (props.mode === 'chat') forceStopAll(); } })
watch(() => props.page, (newPage, oldPage) => { if (newPage !== oldPage) lastSpokenScript.value = ''; });
watch(() => props.script, async (newText, oldText) => {
  if (!isInitialized.value) { isInitialized.value = true; if (newText && newText.length > 5) lastSpokenScript.value = newText; return; }
  if (isPlaying.value) return;
  if (props.mode === 'lecture' && !isPaused.value && newText && newText.length > 5) {
    if (newText !== lastSpokenScript.value) {
      lastSpokenScript.value = newText;
      if (!props.showAvatar) stopAudioOnly(); else postMsg('STOP_SPEAK');
      isPlaying.value = true;
      if (!props.showAvatar) await speakWithGesture(newText); else if (!iframeReady.value) pendingScript.value = newText; else await speakWithGesture(newText);
    }
  }
}, { immediate: true })

const handleIframeMessage = (event) => { if (event.data && event.data.type === 'AUDIO_ENDED') { isSpeaking.value = false; isPlaying.value = false; emit('speaking', false); setGesture('pointLeft'); if (props.mode === 'lecture' && !isPaused.value) emit('autoNextPage'); } }
onMounted(() => { window.addEventListener('message', handleIframeMessage); })
onUnmounted(() => { window.removeEventListener('message', handleIframeMessage); stopGestureKeepAlive(); })

defineExpose({ stopAudio: () => { postMsg('STOP_SPEAK'); stopAudioOnly(); if (window.speechSynthesis) window.speechSynthesis.cancel(); isSpeaking.value = false; isPlaying.value = false; isPaused.value = false; audioOnlyPausedTime.value = 0; lastSpokenScript.value = ''; emit('speaking', false); }, setGlobalAudioManager })
</script>

<style scoped>
.digital-avatar-fullscreen { 
  position: relative; width: 100%; height: 100%; 
  background: linear-gradient(135deg, #D2E6FE 0%, #F8FAFC 100%); 
  border-radius: 16px; overflow: hidden; 
  box-shadow: 0 8px 24px rgba(20, 66, 211, 0.1); 
}
.avatar-container { width: 100%; height: 100%; position: relative; }
.avatar-iframe { width: 100%; height: 160%; margin-top: -46px; border: none; }
.overlay-top { position: absolute; top: 0; left: 0; width: 100%; height: 40px; background: transparent; z-index: 10; pointer-events: none; }
.overlay-bottom { position: absolute; bottom: 0; left: 0; width: 100%; height: 120px; background: linear-gradient(to top, rgba(210, 230, 254, 0.9) 0%, rgba(210, 230, 254, 0) 100%); z-index: 10; pointer-events: none; }

.control-panel { 
  position: absolute; bottom: 20px; left: 20px; width: auto; 
  background: rgba(255, 255, 255, 0.85); backdrop-filter: blur(12px); 
  border-radius: 12px; border: 1px solid rgba(48, 122, 227, 0.2); 
  box-shadow: 0 4px 16px rgba(20, 66, 211, 0.15); z-index: 20; transition: all 0.3s ease; padding: 10px 14px; 
}
.control-panel:hover { background: rgba(255, 255, 255, 0.95); transform: translateY(-2px); box-shadow: 0 8px 24px rgba(20, 66, 211, 0.2); }
.panel-header { padding: 0; background: transparent; border-bottom: none; display: none; }
.title { font-weight: 800; font-size: 13px; color: #1442D3; display: flex; align-items: center; gap: 6px; }
.panel-content { padding: 0; display: flex; flex-direction: row; gap: 10px; align-items: center; }

.status-info { display: flex; align-items: center; gap: 8px; font-size: 13px; color: #307AE3; font-weight: 600; padding: 6px 12px; background: rgba(48, 122, 227, 0.1); border-radius: 8px; border: 1px solid rgba(48, 122, 227, 0.2); }
.status-info.ready { color: #1442D3; background: rgba(20, 66, 211, 0.05); border-color: rgba(20, 66, 211, 0.15); }
.status-info.paused { color: #ACB1EC; background: rgba(172, 177, 236, 0.15); border-color: rgba(172, 177, 236, 0.4); }
.pause-icon { font-weight: bold; font-size: 10px; letter-spacing: 1px; color: #1442D3; }
.pulse-dot { width: 8px; height: 8px; background: #307AE3; border-radius: 50%; box-shadow: 0 0 0 rgba(48, 122, 227, 0.4); animation: pulse 1.5s infinite; flex-shrink: 0; }
.static-dot { width: 8px; height: 8px; background: #1442D3; border-radius: 50%; flex-shrink: 0; }
@keyframes pulse { 0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(48, 122, 227, 0.6); } 70% { transform: scale(1); box-shadow: 0 0 0 8px rgba(48, 122, 227, 0); } 100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(48, 122, 227, 0); } }

.brand-btn-outline { border: 1px solid #307AE3 !important; color: #307AE3 !important; background: transparent !important; border-radius: 12px !important; }
.brand-btn-outline:hover { background: #307AE3 !important; color: #FFFFFF !important; }

.gesture-panel {
  position: absolute; bottom: 80px; left: 50%; transform: translateX(-50%); width: 240px; background: rgba(255, 255, 255, 0.95); backdrop-filter: blur(12px); border-radius: 16px; border: 1px solid rgba(48, 122, 227, 0.2); box-shadow: 0 12px 32px rgba(20, 66, 211, 0.2); overflow: hidden; z-index: 20;
}
.gesture-header { padding: 12px 16px; background: linear-gradient(90deg, #D2E6FE 0%, #F8FAFC 100%); border-bottom: 1px solid rgba(48, 122, 227, 0.1); display: flex; justify-content: space-between; align-items: center; color: #1442D3; font-size: 14px; font-weight: 800; }
.close-icon { cursor: pointer; font-size: 18px; color: #307AE3; transition: color 0.3s; }
.close-icon:hover { color: #1442D3; }
.gesture-buttons { padding: 16px; display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; background: #fff; }
.gesture-buttons :deep(.el-button) { margin: 0; padding: 10px; display: flex; align-items: center; justify-content: center; gap: 6px; font-weight: 600; }
.gesture-emoji { font-size: 16px; }

.slide-up-enter-active, .slide-up-leave-active { transition: all 0.3s cubic-bezier(0.2, 0.8, 0.2, 1); }
.slide-up-enter-from, .slide-up-leave-to { opacity: 0; transform: translate(-50%, 15px); }

.audio-only { background: linear-gradient(135deg, #1442D3 0%, #307AE3 100%); display: flex; align-items: center; justify-content: center; min-height: 200px; }
.audio-only-indicator { display: flex; flex-direction: column; align-items: center; justify-content: center; color: white; padding: 20px; }
.audio-icon { font-size: 56px; margin-bottom: 16px; animation: pulse 2s infinite; color: #D2E6FE; }
.audio-text { font-size: 16px; font-weight: 600; opacity: 0.9; letter-spacing: 1px; }
.audio-wave { display: flex; align-items: center; gap: 6px; margin-bottom: 16px; height: 48px; }
.audio-wave span { display: block; width: 6px; background: #D2E6FE; border-radius: 3px; animation: wave 1s ease-in-out infinite; }
.audio-wave span:nth-child(1) { height: 20%; animation-delay: 0s; }
.audio-wave span:nth-child(2) { height: 40%; animation-delay: 0.1s; }
.audio-wave span:nth-child(3) { height: 60%; animation-delay: 0.2s; }
.audio-wave span:nth-child(4) { height: 40%; animation-delay: 0.3s; }
.audio-wave span:nth-child(5) { height: 20%; animation-delay: 0.4s; }
@keyframes wave { 0%, 100% { transform: scaleY(0.5); } 50% { transform: scaleY(1); } }
</style>