<template>
  <div class="interactive-classroom">
    <!-- 顶部返回栏 -->
    <div class="top-bar">
      <div class="top-left">
        <button class="back-btn" @click="goBack">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M19 12H5M12 5l-7 7 7 7"/>
          </svg>
          <span class="back-text">返回</span>
        </button>
        <span class="top-title">互动课堂</span>
      </div>
      <span class="top-badge">Powered by 问潮知海</span>
    </div>

    <!-- iframe 嵌入 OpenMAIC -->
    <div class="iframe-wrapper">
      <div v-if="loading" class="loading-mask">
        <div class="spinner"></div>
        <p>正在加载互动课堂...</p>
      </div>
      <iframe
        ref="iframeRef"
        :src="openmaicUrl"
        frameborder="0"
        allow="microphone; camera; clipboard-write"
        allowfullscreen
        class="openmaic-iframe"
        @load="onIframeLoad"
      ></iframe>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const loading = ref(true)

// OpenMAIC 运行在 3001 端口，动态获取主机地址
const openmaicUrl = computed(() => {
  const host = window.location.hostname
  return `http://${host}:3001`
})

const onIframeLoad = () => {
  loading.value = false
}

const goBack = () => {
  router.push('/student')
}
</script>

<style scoped>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

.interactive-classroom {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 9999;
  display: flex;
  flex-direction: column;
  background: #0f1117;
  overflow: hidden;
}

/* ==================== 顶部栏样式修改 ==================== */
.top-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 48px;
  padding: 0 16px;
  /* 使用提供的配色方案，从左到右渐变 */
  background: linear-gradient(90deg, #267DF6 0%, #C6DCFC 100%);
  border-bottom: none;
  flex-shrink: 0;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.top-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.back-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  padding: 6px 12px;
  background: rgba(255, 255, 255, 0.15);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 6px;
  color: #ffffff;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
  -webkit-tap-highlight-color: transparent;
  /* 添加文字阴影以提高可读性 */
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
}

.back-btn:hover {
  background: rgba(255, 255, 255, 0.25);
  border-color: rgba(255, 255, 255, 0.3);
}

.back-btn svg {
  flex-shrink: 0;
  filter: drop-shadow(0 1px 1px rgba(0, 0, 0, 0.2));
}

.top-title {
  font-size: 15px;
  font-weight: 600;
  color: #ffffff;
  letter-spacing: 0.5px;
  /* 添加文字阴影以提高可读性 */
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
}

.top-badge {
  font-size: 12px;
  font-weight: 700;
  color: #ffffff;
  opacity: 1;
  letter-spacing: 0.25px;
  background: rgba(0, 0, 0, 0.2);
  padding: 3px 8px;
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.35);
  text-shadow: 0 1px 4px rgba(0, 0, 0, 0.35);
}
/* ==================== 顶部栏样式修改结束 ==================== */


/* iframe 容器 */
.iframe-wrapper {
  flex: 1;
  position: relative;
  width: 100%;
  height: 100%;
  overflow: hidden;
  -webkit-overflow-scrolling: touch; 
}

.openmaic-iframe {
  width: 100%;
  height: 100%;
  border: none;
  display: block;
}

/* 加载遮罩 */
.loading-mask {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  background: #0f1117;
  z-index: 10;
}

.loading-mask p {
  color: #5a6480;
  font-size: 14px;
  letter-spacing: 0.5px;
}

.spinner {
  width: 32px;
  height: 32px;
  border: 2px solid rgba(255, 255, 255, 0.06);
  border-top-color: #267DF6;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* 移动端响应式适配 */
@media screen and (max-width: 600px) {
  .top-bar {
    padding: 0 12px;
    height: 44px;
  }
  
  .back-text {
    display: none;
  }
  
  .back-btn {
    padding: 6px 8px;
  }

  .top-title {
    font-size: 14px;
  }

  .top-badge {
    display: none;
  }
}
</style>