<template>
  <div class="rhythm-panel">
    <!-- 理解度仪表盘 -->
    <div class="understanding-gauge glass-card-primary">
      <div class="gauge-header">
        <span class="gauge-title">📊 学习理解度</span>
        <el-tooltip content="基于AI分析您的提问和回答，评估当前理解程度" placement="top">
          <el-icon class="info-icon"><QuestionFilled /></el-icon>
        </el-tooltip>
      </div>
      
      <div class="gauge-body">
        <el-progress 
          type="dashboard" 
          :percentage="understandingScore" 
          :color="getScoreColor(understandingScore)"
          :width="120"
        >
          <template #default="{ percentage }">
            <span class="percentage-value">{{ percentage }}</span>
            <span class="percentage-label">分</span>
          </template>
        </el-progress>
        
        <div class="score-label">{{ getScoreLabel(understandingScore) }}</div>
      </div>
    </div>

    <!-- AI 诊断报告 -->
    <div v-if="aiDiagnosis" class="ai-diagnosis glass-section">
      <div class="diagnosis-header">
        <el-icon class="diagnosis-icon"><Promotion /></el-icon>
        <span class="diagnosis-title">🤖 AI 诊断报告</span>
      </div>
      <div class="diagnosis-content">
        <p>{{ aiDiagnosis }}</p>
      </div>
    </div>

    <!-- 答题正确率统计 -->
    <div v-if="quizStats" class="quiz-stats glass-section">
      <div class="quiz-stats-header">
        <el-icon><DocumentChecked /></el-icon>
        <span>答题统计</span>
      </div>
      <div class="quiz-stats-body">
        <div class="quiz-accuracy">
          <el-progress 
            type="circle" 
            :percentage="quizStats.accuracy" 
            :color="getScoreColor(quizStats.accuracy)"
            :width="80"
          >
            <template #default="{ percentage }">
              <span class="accuracy-value">{{ percentage }}%</span>
            </template>
          </el-progress>
          <div class="accuracy-label">正确率</div>
        </div>
        <div class="quiz-detail">
          <div class="quiz-detail-item">
            <span class="label">总题数</span>
            <span class="value">{{ quizStats.total }}</span>
          </div>
          <div class="quiz-detail-item">
            <span class="label">正确</span>
            <span class="value correct">{{ quizStats.correct }}</span>
          </div>
          <div class="quiz-detail-item">
            <span class="label">错误</span>
            <span class="value wrong">{{ quizStats.total - quizStats.correct }}</span>
          </div>
        </div>
        <div class="quiz-detail-actions">
          <el-button size="small" class="brand-btn-outline" @click="showAnswerDetails">
            <el-icon><View /></el-icon> 查看详情
          </el-button>
        </div>
      </div>
    </div>

    <!-- 理解统计 -->
    <div class="understanding-stats">
      <div class="stat-item glass-item" v-for="(value, key) in understandingStats" :key="key">
        <div class="stat-icon" :class="`stat-${key}`">
          <span v-if="key === 'full'">✓</span>
          <span v-else-if="key === 'partial'">~</span>
          <span v-else>✗</span>
        </div>
        <div class="stat-info">
          <div class="stat-label">{{ getStatLabel(key) }}</div>
          <div class="stat-value">{{ value }} 次</div>
        </div>
      </div>
    </div>

    <!-- 节奏建议 -->
    <div class="rhythm-suggestions glass-section" v-if="suggestions.length > 0">
      <div class="suggestions-header">💡 智能建议</div>
      <div class="suggestion-list">
        <div 
          v-for="(suggestion, index) in suggestions" 
          :key="index"
          class="suggestion-item glass-item"
          :class="`suggestion-${suggestion.type}`"
        >
          <div class="suggestion-icon">
            <el-icon v-if="suggestion.type === 'slow_down'"><Warning /></el-icon>
            <el-icon v-else-if="suggestion.type === 'speed_up'"><Promotion /></el-icon>
            <el-icon v-else><SuccessFilled /></el-icon>
          </div>
          <div class="suggestion-content">
            <div class="suggestion-message">{{ suggestion.message }}</div>
            <!-- 显示诊断详情 -->
            <div v-if="suggestion.details" class="suggestion-details">
              <p v-for="(detail, i) in suggestion.details" :key="i" class="detail-text">• {{ detail }}</p>
            </div>
            <div class="suggestion-actions" v-if="suggestion.sections && suggestion.sections.length > 0">
              <el-button size="small" type="primary" class="brand-btn" @click="trackReviewStart(suggestion.sections[0])">立即复习</el-button>
              <el-button size="small" type="info" class="brand-btn-outline" @click="evaluateReviewEffect(suggestion.sections[0])">查看效果</el-button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 困惑章节 - 显示需要加强的知识点 -->
    <div class="confused-sections glass-section" v-if="confusedSections.length > 0">
      <div class="section-header">
        <span>🤔 需要加强的知识点</span>
        <el-tag size="small" type="warning" effect="plain">{{ confusedSections.length }}</el-tag>
      </div>
      <div class="section-list">
        <div 
          v-for="(section, index) in confusedSections.slice(0, 5)" 
          :key="index"
          class="section-item confused glass-item"
          @click="handleReviewSection(section)"
        >
          <span class="section-name">{{ section }}</span>
          <el-icon class="section-arrow"><ArrowRight /></el-icon>
        </div>
      </div>
    </div>

    <!-- 已掌握章节 -->
    <div class="mastered-sections glass-section" v-if="masteredSections.length > 0">
      <div class="section-header">
        <span>✅ 已掌握的章节</span>
        <el-tag size="small" type="success" effect="plain">{{ masteredSections.length }}</el-tag>
      </div>
      <div class="section-list">
        <div v-for="section in masteredSections.slice(0, 3)" :key="section" class="section-item mastered glass-item">
          <span class="section-name">{{ section }}</span>
          <el-icon class="section-check"><Check /></el-icon>
        </div>
      </div>
    </div>

    <!-- 刷新按钮 -->
    <div class="panel-footer">
      <el-button size="small" :loading="loading" @click="refreshDiagnosis" style="width: 100%;" class="refresh-btn brand-btn-outline">
        <el-icon><Refresh /></el-icon> 重新评估节奏
      </el-button>
    </div>
  </div>

  <!-- 复习效果评估对话框 -->
  <el-dialog v-model="showReviewResult" title="复习效果评估" width="400px" center custom-class="fancy-dialog">
    <div v-if="reviewResult" class="review-result-content">
      <div class="result-header">
        <h3>{{ reviewResult.section }}</h3>
      </div>
      <div class="result-body">
        <div class="level-comparison">
          <div class="level-item">
            <span class="label">复习前</span>
            <div class="level-badge" :class="`level-${reviewResult.previousLevel}`">
              {{ getLevelLabel(reviewResult.previousLevel) }}
            </div>
          </div>
          <div class="arrow">→</div>
          <div class="level-item">
            <span class="label">复习后</span>
            <div class="level-badge" :class="`level-${reviewResult.recentLevel}`">
              {{ getLevelLabel(reviewResult.recentLevel) }}
            </div>
          </div>
        </div>
        <div class="improvement-section">
          <div class="improvement-badge" :class="`improvement-${reviewResult.improvement}`">
            <el-icon v-if="reviewResult.improvement === 'significant'"><SuccessFilled /></el-icon>
            <el-icon v-else-if="reviewResult.improvement === 'moderate'"><Warning /></el-icon>
            <el-icon v-else><InfoFilled /></el-icon>
            <span>{{ getImprovementLabel(reviewResult.improvement) }}</span>
          </div>
        </div>
        <div class="stats-info">
          <p>本章节共提问 <strong>{{ reviewResult.totalQuestions }}</strong> 次</p>
          <p>{{ reviewResult.message }}</p>
        </div>
      </div>
    </div>
    <template #footer>
      <el-button @click="showReviewResult = false" round>关闭</el-button>
      <el-button type="primary" class="brand-btn" @click="showReviewResult = false" round>继续学习</el-button>
    </template>
  </el-dialog>
  
  <!-- 答题详情弹窗 -->
  <el-dialog
    v-model="showAnswerDetailDialog"
    title="答题详情"
    width="700px"
    top="5vh"
    :close-on-click-modal="false"
    class="answer-detail-dialog fancy-dialog"
  >
    <div v-loading="answerDetailLoading" class="answer-detail-content">
      <div class="filter-buttons">
        <el-radio-group v-model="answerDetailType" @change="filterAnswerDetails">
          <el-radio-button label="all">全部</el-radio-button>
          <el-radio-button label="correct">正确</el-radio-button>
          <el-radio-button label="wrong">错误</el-radio-button>
        </el-radio-group>
      </div>
      
      <div class="answer-list">
        <div v-if="answerDetailList.length === 0" class="empty-text">暂无答题记录</div>
        <div v-for="(item, index) in answerDetailList" :key="index" class="answer-item" :class="{ 'correct': item.isCorrect, 'wrong': !item.isCorrect }">
          <div class="answer-header">
            <el-tag size="small" :type="item.type === 'checkpoint' ? 'success' : 'primary'">{{ item.typeLabel }}</el-tag>
            <span v-if="item.pageNum" class="page-num">第{{ item.pageNum }}页</span>
            <span class="answer-time">{{ item.submitTime }}</span>
            <el-tag size="small" :type="item.isCorrect ? 'success' : 'danger'" effect="dark">{{ item.isCorrect ? '✓ 正确' : '✗ 错误' }}</el-tag>
          </div>
          <div class="answer-content">
            <p class="question-text"><strong>题目：</strong>{{ item.question }}</p>
            <p class="answer-text" :class="{ 'correct-text': item.isCorrect, 'wrong-text': !item.isCorrect }">
              <strong>你的答案：</strong>{{ item.userAnswer || '未作答' }}
            </p>
            <p class="correct-answer-text"><strong>正确答案：</strong>{{ item.correctAnswer }}</p>
          </div>
        </div>
      </div>
    </div>
    <template #footer><el-button @click="showAnswerDetailDialog = false" round>关闭</el-button></template>
  </el-dialog>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { QuestionFilled, Warning, Promotion, SuccessFilled, ArrowRight, Check, Refresh, InfoFilled, DocumentChecked, View } from '@element-plus/icons-vue'
import { diagnoseRhythm } from '@/api/progress'

const props = defineProps({ lessonId: { type: [String, Number], required: true } })
const emit = defineEmits(['reviewSection'])
const loading = ref(false)
const understandingScore = ref(50)
const understandingStats = ref({ full: 0, partial: 0, none: 0 })
const suggestions = ref([])
const confusedSections = ref([])
const masteredSections = ref([])
const aiDiagnosis = ref('')
const quizStats = ref(null) 

const getScoreColor = (score) => (score >= 80 ? '#1442D3' : score >= 60 ? '#307AE3' : '#F56C6C')
const getScoreLabel = (score) => (score >= 80 ? '掌握良好' : score >= 60 ? '基本理解' : score >= 40 ? '需要加强' : '理解困难')
const getStatLabel = (key) => ({ full: '完全理解', partial: '部分理解', none: '未理解' }[key] || key)
const getLevelLabel = (level) => { const labels = { 'full': '完全理解', 'partial': '部分理解', 'none': '完全不了解' }; return labels[level] || level }
const getImprovementLabel = (improvement) => { const labels = { 'significant': '显著提升 🎉', 'moderate': '有所提升 👍', 'no_change': '继续加油 💪' }; return labels[improvement] || improvement }
const handleReviewSection = (section) => emit('reviewSection', section)
const trackReviewStart = (section) => { emit('reviewSection', section) }

const reviewResult = ref(null)
const showReviewResult = ref(false)
const showAnswerDetailDialog = ref(false)
const answerDetailLoading = ref(false)
const answerDetailList = ref([])
const answerDetailType = ref('all') 

const fetchAnswerDetails = async (type = 'all') => {
  if (!props.lessonId) return
  answerDetailLoading.value = true; answerDetailType.value = type;
  try {
    const checkpointRes = await fetch(`/api/v1/quiz/checkpoint-answers/${props.lessonId}`, { headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` } })
    const checkpointData = await checkpointRes.json()
    const quizRes = await fetch(`/api/v1/quiz/student-answers/${props.lessonId}`, { headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` } })
    const quizData = await quizRes.json()
    let allAnswers = []
    if (checkpointData.data?.answers) { checkpointData.data.answers.forEach(ans => { allAnswers.push({ type: 'checkpoint', typeLabel: '每5页测验', pageNum: ans.pageNum, question: ans.questionText, userAnswer: ans.userAnswer, correctAnswer: ans.correctAnswer, isCorrect: ans.isCorrect, submitTime: ans.submitTime }) }) }
    const answersDetail = quizData.data?.answersDetail || {}
    Object.values(answersDetail).forEach(ans => { allAnswers.push({ type: 'quiz', typeLabel: '老师测验', question: ans.question || ans.questionText, userAnswer: ans.userAnswer || ans.studentAnswer, correctAnswer: ans.correctAnswer, isCorrect: ans.isCorrect, submitTime: ans.submitTime || quizData.data?.submitTime }) })
    allAnswers.sort((a, b) => new Date(b.submitTime) - new Date(a.submitTime))
    if (type === 'correct') answerDetailList.value = allAnswers.filter(a => a.isCorrect); else if (type === 'wrong') answerDetailList.value = allAnswers.filter(a => !a.isCorrect); else answerDetailList.value = allAnswers;
    showAnswerDetailDialog.value = true
  } catch (error) { ElMessage.error('获取答题详情失败'); } finally { answerDetailLoading.value = false; }
}
const showAnswerDetails = () => { fetchAnswerDetails('all') }
const filterAnswerDetails = (type) => { fetchAnswerDetails(type) }
const evaluateReviewEffect = async (section) => {
  try {
    const res = await fetch(`/api/v1/progress/evaluateReview/${props.lessonId}/${encodeURIComponent(section)}`, { method: 'GET', headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` } })
    const data = await res.json()
    if (data.data) { reviewResult.value = data.data; showReviewResult.value = true; ElMessage.success(data.data.message) }
  } catch (error) { ElMessage.error('评估复习效果失败'); }
}
const loadDiagnosis = async (forceRefresh = false) => {
  if (!props.lessonId) return
  loading.value = true
  try {
    const res = await diagnoseRhythm(props.lessonId, forceRefresh)
    const data = res.data || res
    understandingScore.value = data.understandingScore || 50; understandingStats.value = data.understandingStats || { full: 0, partial: 0, none: 0 }; quizStats.value = data.quizStats || null; suggestions.value = (data.suggestions || []).map(s => ({ ...s, message: s.message || '根据您的答题情况，建议调整学习节奏' })); confusedSections.value = data.confusedSections || []; masteredSections.value = data.masteredSections || []; aiDiagnosis.value = data.aiDiagnosis || '';
    if (forceRefresh) ElMessage.success('诊断完成');
  } catch (error) { ElMessage.error('加载诊断信息失败'); } finally { loading.value = false; }
}

const refreshDiagnosis = async () => { if (!props.lessonId) return ElMessage.warning('请先选择课件'); await loadDiagnosis(true) }
onMounted(() => { if (props.lessonId) { loadDiagnosis(false) } })
defineExpose({ refreshDiagnosis })
</script>

<style scoped>
/* 品牌四色统一 */
.rhythm-panel {
  --primary-blue: #307AE3;
  --dark-blue: #1442D3;
  --light-blue: #D2E6FE;
  --lavender: #ACB1EC;
  --bg-color: #F8FAFC;
  --text-main: #1E293B;
  --text-sub: #64748B;
  --border-color: rgba(48, 122, 227, 0.15);
  
  --shadow-sm: 0 4px 12px rgba(48, 122, 227, 0.05);
  --shadow-md: 0 8px 24px rgba(48, 122, 227, 0.1);
  --shadow-lg: 0 12px 32px rgba(20, 66, 211, 0.15);
  
  background: transparent; padding: 20px; display: flex; flex-direction: column; gap: 20px; 
}

/* 按钮通用类 */
.brand-btn { background: linear-gradient(135deg, var(--primary-blue), var(--dark-blue)) !important; border: none !important; box-shadow: var(--shadow-sm) !important; color: #fff !important; border-radius: 12px !important; }
.brand-btn:hover { transform: translateY(-2px); box-shadow: var(--shadow-md) !important; }
.brand-btn-outline { border: 1px solid var(--primary-blue) !important; color: var(--primary-blue) !important; background: transparent !important; border-radius: 12px !important; }
.brand-btn-outline:hover { background: var(--primary-blue) !important; color: #fff !important; }

/* 核心卡片 */
.glass-card-primary { background: #FFFFFF; border: 1px solid var(--border-color); box-shadow: var(--shadow-md); border-radius: 20px; padding: 24px; color: var(--text-main); transition: all 0.3s ease; }
.glass-card-primary:hover { box-shadow: var(--shadow-lg); transform: translateY(-2px); border-color: var(--light-blue); }

.gauge-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.gauge-title { font-size: 16px; font-weight: 800; color: var(--dark-blue); }
.info-icon { color: var(--text-sub); cursor: pointer; transition: all 0.2s ease; }
.info-icon:hover { color: var(--primary-blue); transform: scale(1.1); }
.gauge-body { display: flex; flex-direction: column; align-items: center; gap: 12px; }

:deep(.el-progress__text) { color: var(--dark-blue) !important; }
.percentage-value { font-size: 32px; font-weight: 800; color: var(--dark-blue); }
.percentage-label { font-size: 14px; color: var(--text-sub); font-weight: 500;}
.score-label { font-size: 15px; font-weight: 700; color: var(--primary-blue); }

.understanding-stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }

.glass-section { background: var(--bg-color); border: 1px solid var(--border-color); border-radius: 20px; padding: 20px; transition: all 0.3s ease; }
.glass-section:hover { box-shadow: var(--shadow-sm); border-color: var(--light-blue); }

.glass-item { background: #FFFFFF; border: 1px solid var(--border-color); border-radius: 16px; padding: 16px; transition: all 0.3s ease; display: flex; flex-direction: column; cursor: pointer; }
.glass-item:hover { background: #FFFFFF; box-shadow: var(--shadow-md); transform: translateY(-2px); border-color: var(--primary-blue); }

.stat-icon { width: 40px; height: 40px; border-radius: 12px; display: flex; align-items: center; justify-content: center; font-size: 18px; font-weight: 800; margin-bottom: 10px; }
.stat-icon.stat-full { background: var(--light-blue); color: var(--primary-blue); }
.stat-icon.stat-partial { background: var(--lavender); color: var(--dark-blue); }
.stat-icon.stat-none { background: rgba(245, 108, 108, 0.1); color: #F56C6C; }

.stat-label { font-size: 13px; color: var(--text-sub); margin-bottom: 4px; font-weight: 600;}
.stat-value { font-size: 18px; font-weight: 800; color: var(--text-main); }

.suggestions-header { font-size: 15px; font-weight: 800; color: var(--dark-blue); margin-bottom: 16px;}
.suggestion-item { display: flex; gap: 12px; border-left: 4px solid var(--primary-blue); flex-direction: column; padding-left: 16px; }
.suggestion-icon { font-size: 22px; color: var(--primary-blue); align-self: flex-start; }
.suggestion-content { flex: 1; }
.suggestion-message { font-weight: 700; color: var(--dark-blue); margin-bottom: 8px; font-size: 14px; line-height: 1.5; }
.suggestion-details { background: var(--bg-color); border-radius: 12px; padding: 12px; margin-bottom: 12px; border: 1px solid var(--light-blue);}
.detail-text { font-size: 13px; color: var(--text-sub); margin: 4px 0; line-height: 1.5; font-weight: 500;}
.suggestion-actions { display: flex; gap: 10px; margin-top: 10px; }

.section-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; font-weight: 800; color: var(--dark-blue); }
.section-list { display: flex; flex-direction: column; gap: 12px; }
.section-item { flex-direction: row; justify-content: space-between; align-items: center; padding: 14px 16px; }
.section-name { font-size: 14px; color: var(--text-main); font-weight: 600; flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; padding-right: 12px; }
.confused .section-arrow { color: var(--primary-blue); font-size: 18px; transition: transform 0.2s; }
.confused:hover .section-arrow { transform: translateX(4px); }
.mastered .section-check { color: var(--primary-blue); font-size: 20px; font-weight: bold; }

.diagnosis-header { display: flex; align-items: center; gap: 10px; margin-bottom: 16px; font-weight: 800; color: var(--dark-blue); }
.diagnosis-icon { font-size: 20px; color: var(--primary-blue); }
.diagnosis-content { font-size: 14px; color: var(--text-main); line-height: 1.6; background: #FFFFFF; padding: 20px; border-radius: 16px; border: 1px solid var(--light-blue); font-weight: 500;}

.quiz-stats { background: var(--bg-color); }
.quiz-stats-header { display: flex; align-items: center; gap: 10px; margin-bottom: 16px; font-weight: 800; color: var(--dark-blue); }
.quiz-stats-body { display: flex; align-items: center; background: #FFFFFF; padding: 20px; border-radius: 16px; border: 1px solid var(--light-blue); }
.quiz-accuracy { display: flex; flex-direction: column; align-items: center; margin-right: 24px; }
.accuracy-value { font-size: 20px; font-weight: 900; color: var(--dark-blue); }
.accuracy-label { font-size: 12px; color: var(--text-sub); margin-top: 6px; font-weight: 600;}
.quiz-detail { flex: 1; display: flex; flex-direction: column; gap: 10px; }
.quiz-detail-item { display: flex; justify-content: space-between; align-items: center; font-size: 14px; }
.quiz-detail-item .label { color: var(--text-sub); font-weight: 500;}
.quiz-detail-item .value { font-weight: 800; color: var(--text-main); }
.quiz-detail-item .correct { color: var(--primary-blue); }
.quiz-detail-item .wrong { color: #F56C6C; }
.quiz-detail-actions { margin-left: 20px; }

.panel-footer { margin-top: 10px; }

:deep(.fancy-dialog) { border-radius: 24px; overflow: hidden; }
:deep(.fancy-dialog .el-dialog__header) { padding: 24px; background: var(--bg-color); border-bottom: 1px solid var(--light-blue); }
:deep(.fancy-dialog .el-dialog__title) { font-size: 18px; font-weight: 800; color: var(--dark-blue); }
:deep(.fancy-dialog .el-dialog__body) { padding: 24px; }
:deep(.fancy-dialog .el-dialog__footer) { padding: 16px 24px 24px; }

.review-result-content { padding: 0; }
.result-header { text-align: center; margin-bottom: 24px; }
.result-header h3 { color: var(--dark-blue); font-size: 20px; margin: 0; font-weight: 800;}
.level-comparison { display: flex; justify-content: center; align-items: center; gap: 24px; margin-bottom: 24px; background: var(--bg-color); padding: 20px; border-radius: 16px; border: 1px solid var(--light-blue);}
.level-item { display: flex; flex-direction: column; align-items: center; gap: 10px; }
.level-item .label { font-size: 13px; color: var(--text-sub); font-weight: 600;}
.level-badge { padding: 8px 16px; border-radius: 20px; font-size: 14px; font-weight: 700; }
.level-full { background: var(--light-blue); color: var(--primary-blue); }
.level-partial { background: var(--lavender); color: var(--dark-blue); }
.level-none { background: #FFF0F0; color: #F56C6C; }
.arrow { color: var(--primary-blue); font-size: 24px; font-weight: bold;}
.improvement-section { display: flex; justify-content: center; margin-bottom: 24px; }
.improvement-badge { display: flex; align-items: center; gap: 10px; padding: 10px 20px; border-radius: 24px; font-size: 15px; font-weight: 800; }
.improvement-significant { background: linear-gradient(135deg, var(--primary-blue), var(--dark-blue)); color: white; }
.improvement-moderate { background: var(--lavender); color: var(--dark-blue); }
.improvement-no_change { background: var(--bg-color); color: var(--text-main); }
.stats-info { text-align: center; color: var(--text-sub); font-size: 14px; line-height: 1.6; font-weight: 500;}

.answer-detail-content { min-height: 300px; max-height: 60vh; overflow-y: auto; padding-right: 10px; }
.filter-buttons { margin-bottom: 20px; display: flex; justify-content: center; }
:deep(.filter-buttons .el-radio-button__inner) { font-weight: 600; }
:deep(.filter-buttons .el-radio-button__original-radio:checked + .el-radio-button__inner) { background-color: var(--primary-blue); border-color: var(--primary-blue); box-shadow: -1px 0 0 0 var(--primary-blue); }

.answer-list { display: flex; flex-direction: column; gap: 16px; }
.empty-text { text-align: center; color: var(--text-sub); padding: 40px 0; font-weight: 600;}
.answer-item { border: 1px solid var(--border-color); border-radius: 16px; padding: 20px; background: #FFFFFF; transition: all 0.3s; }
.answer-item:hover { box-shadow: var(--shadow-md); transform: translateY(-2px); }
.answer-item.correct { border-left: 4px solid var(--primary-blue); }
.answer-item.wrong { border-left: 4px solid #F56C6C; background: #FFF9F9; }
.answer-header { display: flex; align-items: center; gap: 12px; margin-bottom: 16px; padding-bottom: 12px; border-bottom: 1px solid var(--light-blue); }
.page-num { font-size: 13px; color: var(--primary-blue); background: var(--light-blue); padding: 4px 10px; border-radius: 12px; font-weight: 600;}
.answer-time { font-size: 13px; color: var(--text-sub); flex: 1; font-weight: 500;}
.answer-content { display: flex; flex-direction: column; gap: 12px; font-size: 14px; }
.question-text { color: var(--text-main); line-height: 1.6; margin: 0; font-weight: 600;}
.answer-text { margin: 0; padding: 12px 16px; border-radius: 12px; background: var(--bg-color); font-weight: 500;}
.correct-text { color: var(--primary-blue); }
.wrong-text { color: #F56C6C; text-decoration: line-through; }
.correct-answer-text { margin: 0; color: var(--primary-blue); font-weight: 700; }
</style>