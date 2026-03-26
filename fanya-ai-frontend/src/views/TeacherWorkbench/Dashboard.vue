<template>
  <div class="dashboard-container">
    <header class="dashboard-header">
      <h2><el-icon color="#307AE3"><PieChart /></el-icon> 学情洞察看板</h2>
      <el-button type="primary" @click="$emit('back')" class="back-btn">返回创作</el-button>
    </header>

    <div class="chart-grid">
      <div class="chart-card">
        <h3>全班掌握度热力分布</h3>
        <div class="mock-heatmap">
          <!-- 改为主色调的不同透明度 -->
          <div v-for="i in 15" :key="i" class="heat-box" :style="{ opacity: Math.random() * 0.7 + 0.3 }">
            P{{ i }}
          </div>
        </div>
        <p class="chart-desc">注：第 8 页和第 12 页学生停留及提问次数显著偏高</p>
      </div>

      <div class="chart-card">
        <h3>学生提问关键词云</h3>
        <div class="mock-word-cloud">
          <span style="font-size: 24px; color: #1442D3; font-weight: bold;">Transformer</span>
          <span style="font-size: 18px; color: #307AE3">Attention</span>
          <span style="font-size: 20px; color: #ACB1EC">Encoder</span>
          <span style="font-size: 14px; color: #1442D3">QKV</span>
          <span style="font-size: 16px; color: #307AE3">维度对齐</span>
        </div>
      </div>
    </div>

    <div class="ai-suggestion">
      <el-alert title="AI 教学优化建议" type="warning" show-icon :closable="false" class="custom-alert">
        系统监测到 60% 的学生在“编码器结构”章节产生困惑，建议教师针对第 8 页内容重录讲解或增加随堂练习。
      </el-alert>
    </div>
  </div>
</template>

<script setup>
import { PieChart } from '@element-plus/icons-vue'
</script>

<style scoped>
.dashboard-container { padding: 32px; background: transparent; height: 100%; overflow-y: auto; }
.dashboard-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 32px; }
.dashboard-header h2 { font-size: 22px; color: #1442D3; font-weight: bold; display: flex; align-items: center; gap: 10px; }
.back-btn { border-radius: 8px; font-weight: bold; }
.chart-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-bottom: 32px; }
.chart-card { background: rgba(255,255,255,0.85); backdrop-filter: blur(10px); padding: 24px; border-radius: 16px; border: 1px solid #D2E6FE; box-shadow: 0 8px 24px rgba(48, 122, 227, 0.08); transition: transform 0.3s; }
.chart-card:hover { transform: translateY(-4px); box-shadow: 0 12px 32px rgba(48, 122, 227, 0.12); border-color: #ACB1EC; }
.chart-card h3 { font-size: 16px; margin-bottom: 24px; color: #1442D3; font-weight: bold; }
.mock-heatmap { display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; }
.heat-box { background: #307AE3; color: #fff; height: 56px; display: flex; align-items: center; justify-content: center; border-radius: 8px; font-size: 14px; font-weight: bold; }
.mock-word-cloud { height: 180px; display: flex; flex-wrap: wrap; align-items: center; justify-content: center; gap: 16px; }
.chart-desc { font-size: 13px; color: #ACB1EC; margin-top: 20px; font-weight: 500;}

/* 覆盖 Element Plus 警告组件色调 */
:deep(.custom-alert) { background-color: #D2E6FE; color: #1442D3; border-radius: 12px; }
:deep(.custom-alert .el-alert__title) { font-weight: bold; font-size: 14px; }
:deep(.custom-alert .el-alert__icon) { color: #307AE3; }
</style>