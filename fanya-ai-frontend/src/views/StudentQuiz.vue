<template>
  <div class="student-quiz">
    <header class="quiz-header">
      <div class="header-left">
        <el-button link @click="$router.back()" class="brand-link-btn">
          <el-icon><ArrowLeft /></el-icon> 返回
        </el-button>
        <el-divider direction="vertical" />
        <span class="course-title">{{ courseName }} - 测验</span>
      </div>
      <div class="header-right">
        <el-tag v-if="!quizCompleted" class="brand-tag-success" effect="light" round size="small">
          进度：{{ answeredCount }}/{{ quizzes.length }}
        </el-tag>
        <el-tag v-else type="success" effect="light" round size="small">已完成</el-tag>
      </div>
    </header>

    <main class="quiz-main">
      <div v-if="!quizCompleted" class="quiz-container">
        <div class="quiz-list">
          <div v-loading="loadingQuizzes" class="quiz-content">
            <el-empty v-if="!loadingQuizzes && quizzes.length === 0" description="暂无测验题" />
            <div v-for="(quiz, index) in paginatedQuizzes" :key="quiz.id" class="quiz-item glass-item">
              <div class="quiz-number">
                <span class="number-badge brand-deep-bg">{{ (currentPage - 1) * pageSize + index + 1 }}</span>
                <span class="quiz-type" :class="`type-${quiz.questionType}`">{{ getQuizTypeName(quiz.questionType) }}</span>
              </div>
              <div class="quiz-question">
                <p class="question-text">{{ quiz.questionText }}</p>
                <div v-if="quiz.questionType === 'single_choice'" class="options-container">
                  <el-radio-group v-model="answers[quiz.id]">
                    <el-radio v-for="(opt, idx) in quiz.options" :key="idx" :label="opt" class="brand-radio">{{ opt }}</el-radio>
                  </el-radio-group>
                </div>
                <div v-else-if="quiz.questionType === 'multiple_choice'" class="options-container">
                  <el-checkbox-group v-model="answers[quiz.id]">
                    <el-checkbox v-for="(opt, idx) in quiz.options" :key="idx" :label="opt" class="brand-radio">{{ opt }}</el-checkbox>
                  </el-checkbox-group>
                </div>
                <div v-else-if="quiz.questionType === 'true_false'" class="options-container">
                  <el-radio-group v-model="answers[quiz.id]">
                    <el-radio label="正确" class="brand-radio">✓ 正确</el-radio>
                    <el-radio label="错误" class="brand-radio">✗ 错误</el-radio>
                  </el-radio-group>
                </div>
                <div v-else class="input-container">
                  <el-input v-model="answers[quiz.id]" type="textarea" placeholder="请输入您的答案" :rows="3" class="brand-textarea" />
                </div>
              </div>
            </div>
          </div>
        </div>

        <aside class="quiz-sidebar">
          <div class="sidebar-card glass-card">
            <h3 class="sidebar-title">答题进度</h3>
            <div class="progress-info">
              <div class="progress-item"><span>已答题：</span><span class="value">{{ answeredCount }}</span></div>
              <div class="progress-item"><span>未答题：</span><span class="value">{{ quizzes.length - answeredCount }}</span></div>
              <div class="progress-item"><span>总题数：</span><span class="value">{{ quizzes.length }}</span></div>
            </div>
            <el-progress :percentage="Math.round((answeredCount / quizzes.length) * 100)" :stroke-width="10" />
          </div>
          <div class="sidebar-card glass-card">
            <h3 class="sidebar-title">题型统计</h3>
            <div class="type-stats">
              <div v-for="(count, type) in typeStats" :key="type" class="stat-item">
                <span>{{ getQuizTypeName(type) }}：</span>
                <span class="value">{{ count }}</span>
              </div>
            </div>
          </div>
          <div class="sidebar-actions">
            <el-button type="primary" size="large" class="brand-btn" @click="submitQuiz" :loading="submitting" style="width: 100%;">
              <el-icon class="el-icon--left"><Check /></el-icon> 提交答卷
            </el-button>
          </div>
        </aside>
      </div>

      <div v-else class="quiz-result">
        <div class="result-card glass-card">
          <div class="result-header">
            <el-icon :size="60" color="#307AE3"><SuccessFilled /></el-icon>
            <h2>测验已完成</h2>
          </div>
          <div class="result-stats">
            <div class="stat-box">
              <div class="stat-value brand-primary-text">{{ totalScore }}</div>
              <div class="stat-label">总分</div>
            </div>
            <div class="stat-box">
              <div class="stat-value">{{ correctCount }}</div>
              <div class="stat-label">正确题数</div>
            </div>
            <div class="stat-box">
              <div class="stat-value">{{ Math.round((correctCount / quizzes.length) * 100) }}%</div>
              <div class="stat-label">正确率</div>
            </div>
          </div>
          <div class="result-actions">
            <el-button type="primary" class="brand-btn" @click="showAnswers = true" size="large">
              <el-icon class="el-icon--left"><View /></el-icon> 查看答案和解析
            </el-button>
            <el-button @click="$router.back()" size="large" class="brand-btn-outline">
              <el-icon class="el-icon--left"><ArrowLeft /></el-icon> 返回课程
            </el-button>
          </div>
        </div>
      </div>
    </main>

    <div v-if="!quizCompleted && quizzes.length > 0" class="pagination-container">
      <el-pagination v-model:current-page="currentPage" :page-size="pageSize" :total="quizzes.length" layout="prev, pager, next" />
    </div>

    <!-- 答案详情弹窗 -->
    <el-dialog v-model="showAnswers" title="答案和解析" width="800px" align-center class="fancy-dialog">
      <div v-loading="loadingAnswers" class="answers-container">
        <div v-for="(quiz, index) in quizzes" :key="quiz.id" class="answer-item">
          <div class="answer-header">
            <span class="answer-number">第 {{ index + 1 }} 题</span>
            <span class="answer-type" :class="`type-${quiz.questionType}`">{{ getQuizTypeName(quiz.questionType) }}</span>
            <el-tag v-if="studentAnswers[quiz.id]?.isCorrect" type="success" size="small">正确</el-tag>
            <el-tag v-else type="danger" size="small">错误</el-tag>
          </div>
          <div class="answer-content">
            <p><strong>题目：</strong>{{ quiz.questionText }}</p>
            <p><strong>您的答案：</strong>{{ studentAnswers[quiz.id]?.studentAnswer || '未作答' }}</p>
            <p><strong>正确答案：</strong>{{ quiz.correctAnswer }}</p>
            <p><strong>解析：</strong>{{ quiz.explanation }}</p>
          </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft, Check, View, SuccessFilled } from '@element-plus/icons-vue'
import { listQuizzes, submitAnswer } from '@/api/quiz'
import { getCourseDetail } from '@/api/course'

// 逻辑部分保持原样...
const stopAllAudio = () => { if (window.speechSynthesis) window.speechSynthesis.cancel(); const allAudios = document.querySelectorAll('audio'); allAudios.forEach(a => { a.pause(); a.currentTime = 0; }); const allIframes = document.querySelectorAll('iframe'); allIframes.forEach(i => { try { i.contentWindow.postMessage({ type: 'STOP_SPEAK' }, '*') } catch (e) {} }); };
const route = useRoute(); const router = useRouter(); const lessonId = ref(route.params.id); const courseName = ref(''); const quizzes = ref([]); const loadingQuizzes = ref(false); const submitting = ref(false); const answers = reactive({}); const studentAnswers = reactive({}); const quizCompleted = ref(false); const showAnswers = ref(false); const currentPage = ref(1); const pageSize = 5;
const paginatedQuizzes = computed(() => { const start = (currentPage.value - 1) * pageSize; return quizzes.value.slice(start, start + pageSize); });
const answeredCount = computed(() => Object.values(answers).filter(a => a !== undefined && a !== null && a !== '').length);
const typeStats = computed(() => { const stats = {}; quizzes.value.forEach(q => { stats[q.questionType] = (stats[q.questionType] || 0) + 1; }); return stats; });
const totalScore = computed(() => Object.values(studentAnswers).reduce((sum, a) => sum + (a?.score || 0), 0));
const correctCount = computed(() => Object.values(studentAnswers).filter(a => a?.isCorrect).length);
const getQuizTypeName = (type) => { const names = { 'single_choice': '单选题', 'multiple_choice': '多选题', 'true_false': '判断题', 'calculation': '计算题', 'application': '应用题' }; return names[type] || type; };
const loadQuizzes = async () => { loadingQuizzes.value = true; try { const res = await listQuizzes(lessonId.value); quizzes.value = res.data?.quizzes || []; quizzes.value.forEach(q => { answers[q.id] = undefined; }); } catch (e) { ElMessage.error('加载测验题失败'); } finally { loadingQuizzes.value = false; } };
const loadCourseName = async () => { try { const res = await getCourseDetail(lessonId.value); courseName.value = res.data?.courseName || res.data?.fileName || '测验'; } catch (e) { courseName.value = '测验'; } };
const submitQuiz = async () => { if (answeredCount.value === 0) return ElMessage.warning('请至少答一道题'); submitting.value = true; try { for (const quiz of quizzes.value) { const answer = answers[quiz.id]; if (answer !== undefined && answer !== null && answer !== '') { const res = await submitAnswer({ quizId: quiz.id, lessonId: lessonId.value, studentAnswer: Array.isArray(answer) ? answer.join(',') : answer }); studentAnswers[quiz.id] = { studentAnswer: Array.isArray(answer) ? answer.join(',') : answer, isCorrect: res.data?.isCorrect, score: res.data?.score || 0 }; } } quizCompleted.value = true; ElMessage.success('答卷已提交'); } catch (e) { ElMessage.error('提交失败，请重试'); } finally { submitting.value = false; } };
onMounted(async () => { stopAllAudio(); await loadCourseName(); await loadQuizzes(); });
onUnmounted(() => { stopAllAudio(); });
</script>

<style scoped>
.student-quiz { 
  --brand-deep: #1442D3; --brand-primary: #307AE3; --brand-lavender: #ACB1EC; --brand-light: #D2E6FE;
  min-height: 100vh; background: #F8FAFC; display: flex; flex-direction: column; 
}
.brand-btn { background: linear-gradient(135deg, var(--brand-primary), var(--brand-deep)) !important; border: none !important; box-shadow: 0 4px 12px rgba(48, 122, 227, 0.2) !important; color: #FFF !important; border-radius: 12px !important; }
.brand-btn-outline { border: 1px solid var(--brand-primary) !important; color: var(--brand-primary) !important; background: transparent !important; border-radius: 12px !important; font-weight: 600;}
.brand-btn-success { background: var(--brand-deep) !important; color: #FFF !important; }
.brand-link-btn { color: var(--brand-primary) !important; font-weight: 700; }
.brand-tag-success { background: rgba(48, 122, 227, 0.1); color: var(--brand-primary); border: 1px solid var(--brand-light); }
.brand-deep-bg { background: var(--brand-deep); color: #FFF; }
.brand-primary-text { color: var(--brand-primary); }
.brand-radio { border: 1px solid #D2E6FE !important; border-radius: 12px !important; background: #F8FAFC !important; margin-right: 0 !important; width: 100%; box-sizing: border-box; }
.brand-radio.is-checked { border-color: var(--brand-primary) !important; background: #EFF6FF !important; }
.brand-textarea :deep(.el-textarea__inner) { border-radius: 12px; background: #F8FAFC; border: 1px solid #D2E6FE; }
.brand-input :deep(.el-input__wrapper) { border-radius: 12px; }

.quiz-header { height: 60px; background: #FFFFFF; border-bottom: 1px solid var(--brand-light); display: flex; justify-content: space-between; align-items: center; padding: 0 24px; box-shadow: 0 2px 8px rgba(20, 66, 211, 0.05); flex-shrink: 0; }
.header-left { display: flex; align-items: center; gap: 12px; }
.course-title { font-size: 16px; font-weight: 800; color: var(--brand-deep); }
.quiz-main { flex: 1; padding: 24px; }
.quiz-container { display: flex; gap: 24px; max-width: 1200px; margin: 0 auto; }
.glass-item { background: #FFFFFF; border: 1px solid #D2E6FE; border-radius: 20px; padding: 24px; box-shadow: 0 4px 16px rgba(20, 66, 211, 0.05); }
.quiz-list { flex: 1; display: flex; flex-direction: column; gap: 20px; }
.quiz-item { margin-bottom: 0; }
.number-badge { display: inline-flex; align-items: center; justify-content: center; width: 32px; height: 32px; border-radius: 50%; font-weight: 800; font-size: 14px; }
.quiz-type { font-size: 12px; padding: 4px 12px; border-radius: 8px; font-weight: 700; }
.type-single_choice { background: #D2E6FE; color: var(--brand-primary); }
.type-multiple_choice { background: #ACB1EC; color: var(--brand-deep); }
.type-true_false { background: #D1FAE5; color: #065F46; }
.quiz-question { margin-top: 16px; }
.question-text { font-size: 16px; font-weight: 700; color: var(--text-main); margin-bottom: 20px; }
.quiz-sidebar { width: 300px; display: flex; flex-direction: column; gap: 20px; }
.sidebar-card { background: #FFFFFF; border-radius: 20px; padding: 20px; border: 1px solid var(--brand-light); box-shadow: 0 4px 16px rgba(48, 122, 227, 0.05); }
.sidebar-title { font-size: 15px; font-weight: 800; color: var(--brand-deep); margin: 0 0 16px 0; }
.value { font-weight: 800; color: var(--brand-primary); }
.result-card { background: #FFFFFF; border-radius: 24px; padding: 48px; box-shadow: 0 12px 48px rgba(48, 122, 227, 0.15); text-align: center; max-width: 600px; margin: 40px auto; }
.stat-value { font-size: 32px; font-weight: 900; color: var(--brand-primary); }
.fancy-dialog { border-radius: 24px; overflow: hidden; }
</style>