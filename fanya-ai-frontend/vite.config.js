import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    vueDevTools(),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    },
  },
 server: {
    host: '0.0.0.0',
    proxy: {
      '/api': {
        target: 'http://localhost:8989', // 后端真实地址
        changeOrigin: true,
        // 视觉接口 body 大、模型耗时长，默认超时易导致代理层 5xx
        timeout: 180000,
        proxyTimeout: 180000
        // 移除rewrite规则，保留/api前缀
      }
    }
  }
})
