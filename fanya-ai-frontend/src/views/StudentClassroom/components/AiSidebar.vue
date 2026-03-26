<template>
  <div class="ai-sidebar" :style="{ width: width + 'px' }">
    <!-- 顶部标签栏 -->
    <div class="sidebar-tabs">
      <div class="tab-item" :class="{ active: activeTab === 'lecture' }" @click="handleLectureTabClick">
        <el-icon><Headset /></el-icon> 伴随讲解
      </div>
      <div class="tab-item" :class="{ active: activeTab === 'chat' }" @click="handleChatTabClick">
        <el-icon><ChatDotRound /></el-icon> 互动答疑
      </div>
      <div class="tab-item" :class="{ active: activeTab === 'mindmap' }" @click="handleMindmapTabClick">
        <el-icon><Share /></el-icon> 思维导图
      </div>
      <div class="tab-item" :class="{ active: activeTab === 'knowledge' }" @click="handleKnowledgeTabClick">
        <el-icon><Connection /></el-icon> 知识图谱
      </div>
      <div class="tab-item" :class="{ active: activeTab === 'quiz' }" @click="handleQuizTabClick">
        <el-icon><DocumentChecked /></el-icon> 测验题
      </div>
    </div>
    
    <!-- 伴随讲解和互动答疑标签页 -->
    <template v-if="activeTab === 'lecture' || activeTab === 'chat'">
      <!-- 测验中禁用提示 -->
      <div v-if="quizStarted && !quizSubmitted" class="quiz-blocking-overlay">
        <div class="quiz-blocking-content">
          <el-icon size="48" class="brand-primary-text"><DocumentChecked /></el-icon>
          <p>正在进行测验，无法使用此功能</p>
          <el-button type="primary" class="brand-btn" @click="activeTab = 'quiz'">返回测验</el-button>
        </div>
      </div>
      <template v-else>
        <ChatArea 
          :mode="mode" 
          :script="script" 
          :audioUrl="audioUrl"
          :history="history" 
          :isChatLoading="isChatLoading" 
          @speakContent="(content) => $emit('speakContent', content)"
          @resolve="(idx) => $emit('resolve', idx)"
          @jumpToPage="(page) => $emit('jumpToPage', page)"
          @chatTextSelected="(data) => $emit('chatTextSelected', data)"
        />
        <InputBox 
          v-model="inputVal" 
          :mode="mode" 
          :placeholder="placeholder"
          @send="onSend"
          @replay="$emit('replay')"
          @switchToChat="activeTab = 'chat'; handleTabChange('chat')"
          @resolve="(idx) => $emit('resolve', idx)" 
        />
      </template>
    </template>
    
    <!-- 思维导图标签页 -->
    <div v-else-if="activeTab === 'mindmap'" class="mindmap-container">
      <!-- 测验中禁用提示 -->
      <div v-if="quizStarted && !quizSubmitted" class="quiz-blocking-overlay">
        <div class="quiz-blocking-content">
          <el-icon size="48" class="brand-primary-text"><DocumentChecked /></el-icon>
          <p>正在进行测验，无法使用此功能</p>
          <el-button type="primary" class="brand-btn" @click="activeTab = 'quiz'">返回测验</el-button>
        </div>
      </div>
      <div v-else class="mindmap-content">
        <div v-if="!mindmapData" class="mindmap-placeholder">
          <el-icon class="mindmap-icon brand-primary-text" size="48"><Share /></el-icon>
          <h3>思维导图</h3>
          <p>基于当前课件内容生成的结构化思维导图</p>
          <el-button type="primary" size="small" class="brand-btn" @click="generateMindmap" :loading="isGeneratingMindmap">生成思维导图</el-button>
        </div>
        <div v-else class="mindmap-visualization">
          <div class="mindmap-loading brand-primary-text" v-if="isGeneratingMindmap">
            <el-icon class="is-loading"><Loading /></el-icon>
            <span>正在生成思维导图...</span>
          </div>
          <div v-else class="mindmap-canvas">
            <svg class="mindmap-svg" :viewBox="computedMindmapViewBox" preserveAspectRatio="xMidYMid meet" @wheel="handleSvgWheel">
              <g class="mindmap-lines">
                <path v-for="(branch, index) in mindmapData.branches" 
                      :key="'line-'+index"
                      :d="getBranchLinePath(branch)"
                      :stroke="branch.color"
                      stroke-width="3"
                      fill="none"
                      class="mindmap-line"
                />
                <path v-for="(line, index) in subLines" 
                      :key="'subline-'+index"
                      :d="line.path"
                      :stroke="line.color"
                      stroke-width="1.5"
                      fill="none"
                      class="mindmap-line"
                />
              </g>
              <g v-if="mindmapData.center" class="mindmap-center">
                <rect 
                  :x="mindmapData.center.x - mindmapData.center.width / 2" 
                  :y="mindmapData.center.y - mindmapData.center.height / 2"
                  :width="mindmapData.center.width"
                  :height="mindmapData.center.height"
                  rx="16" ry="16" 
                  fill="#1442D3" 
                  class="mindmap-center-node" />
                <text 
                  :x="mindmapData.center.x" 
                  :y="mindmapData.center.y" 
                  text-anchor="middle" 
                  dominant-baseline="middle"
                >{{ mindmapData.center.label }}</text>
              </g>
              <g v-for="(branch, index) in mindmapData.branches" :key="'branch-'+index" class="mindmap-branch">
                <rect 
                  :x="branch.x - branch.width / 2" 
                  :y="branch.y - branch.height / 2"
                  :width="branch.width"
                  :height="branch.height"
                  rx="20" ry="20"
                  :fill="branch.color" 
                  class="mindmap-branch-node"/>
                <text 
                  :x="branch.x" 
                  :y="branch.y" 
                  text-anchor="middle"
                  dominant-baseline="middle" 
                  :fill="getTextColor(branch.color)"
                >{{ branch.label }}</text>
                <g v-for="(sub, subIndex) in branch.children" :key="'sub-'+index+'-'+subIndex" class="mindmap-sub">
                  <text 
                    :x="sub.x" 
                    :y="sub.y" 
                    text-anchor="start"
                    dominant-baseline="middle"
                  >{{ sub.label }}</text>
                </g>
              </g>
            </svg>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 知识图谱标签页 -->
    <div v-else-if="activeTab === 'knowledge'" class="knowledge-graph-container">
      <!-- 测验中禁用提示 -->
      <div v-if="quizStarted && !quizSubmitted" class="quiz-blocking-overlay">
        <div class="quiz-blocking-content">
          <el-icon size="48" class="brand-primary-text"><DocumentChecked /></el-icon>
          <p>正在进行测验，无法使用此功能</p>
          <el-button type="primary" class="brand-btn" @click="activeTab = 'quiz'">返回测验</el-button>
        </div>
      </div>
      <div v-else class="knowledge-graph-content">
        <div v-if="!knowledgeGraphData" class="knowledge-graph-placeholder">
          <el-icon class="knowledge-graph-icon brand-primary-text" size="48"><Connection /></el-icon>
          <h3>知识图谱</h3>
          <p>基于当前课件内容生成的关联知识网络</p>
          <el-button type="primary" size="small" class="brand-btn" @click="generateKnowledgeGraph" :loading="isGeneratingGraph">生成知识图谱</el-button>
        </div>
        <div v-else class="knowledge-graph-visualization">
          <div class="knowledge-graph-loading brand-primary-text" v-if="isGeneratingGraph">
            <el-icon class="is-loading"><Loading /></el-icon>
            <span>正在生成知识图谱...</span>
          </div>
          <div v-else class="knowledge-graph-canvas">
            <svg class="knowledge-graph-svg" :viewBox="computedGraphViewBox" preserveAspectRatio="xMidYMid meet" @wheel="handleSvgWheel">
              
              <!-- 连线 -->
              <g class="knowledge-graph-edges">
                <g v-for="(edge, index) in knowledgeGraphData.edges" :key="'edge-'+index">
                  <line 
                    :x1="edge.x1" :y1="edge.y1" 
                    :x2="edge.x2" :y2="edge.y2" 
                    stroke="#D2E6FE" stroke-width="2.5" 
                    class="knowledge-graph-line"
                  />
                  <!-- 连线标签 -->
                  <g v-if="edge.label" :transform="`translate(${edge.mx}, ${edge.my}) rotate(${edge.angle})`">
                    <text text-anchor="middle" dominant-baseline="central" font-size="13" fill="none" stroke="#ffffff" stroke-width="4" stroke-linejoin="round">{{ edge.label }}</text>
                    <text text-anchor="middle" dominant-baseline="central" font-size="13" fill="#307AE3" class="edge-text">{{ edge.label }}</text>
                  </g>
                </g>
              </g>

              <!-- 节点 -->
              <g class="knowledge-graph-nodes">
                <g v-for="node in knowledgeGraphData.nodes" :key="'node-'+node.id" class="knowledge-graph-node">
                  <circle :cx="node.x" :cy="node.y" :r="node.size" :fill="node.color" />
                  <text :x="node.x" :y="node.y" text-anchor="middle" dominant-baseline="central" :fill="node.textColor" font-size="15" font-weight="600">
                    <tspan v-for="(line, i) in node.lines" :key="i" :x="node.x" :dy="i === 0 ? (node.lines.length === 1 ? 0 : -10) : 20">
                      {{ line }}
                    </tspan>
                  </text>
                </g>
              </g>

            </svg>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 测验题标签页 -->
    <div v-else-if="activeTab === 'quiz'" class="quiz-container">
      <div class="quiz-content">
        <!-- 未开始状态 -->
        <div v-if="!quizStarted" class="quiz-placeholder">
          <el-icon class="quiz-icon brand-primary-text" size="48"><DocumentChecked /></el-icon>
          <h3>课程测验</h3>
          <p>基于当前课件内容生成的测试题，检验学习成果</p>
          
          <!-- 显示最近一次测验记录 -->
          <div v-if="lastAttempt" class="last-attempt-info">
            <el-divider />
            <p class="attempt-title">上次测验结果</p>
            <div class="attempt-stats">
              <span class="attempt-score" :class="{ 'pass': lastAttempt.totalScore >= 60 }">
                {{ lastAttempt.totalScore }}分
              </span>
              <span class="attempt-detail">
                {{ lastAttempt.correctCount }}对 / {{ lastAttempt.wrongCount }}错
              </span>
              <span class="attempt-time">{{ lastAttempt.submitTime }}</span>
            </div>
            <div class="attempt-actions">
              <el-button type="primary" size="small" class="brand-btn" @click="viewLastAttempt">查看详情</el-button>
              <el-button size="small" @click="showAttemptHistory">历史记录</el-button>
            </div>
            <el-divider />
          </div>
          
          <el-button 
            type="primary" 
            size="small" 
            class="brand-btn"
            @click="startQuiz" 
            :loading="isLoadingQuiz"
            :disabled="!courseId"
          >
            {{ lastAttempt ? '重新测验' : '开始测验' }}
          </el-button>
          <p v-if="!courseId" class="quiz-hint">请先选择课件</p>
        </div>
        
        <!-- 做题状态 -->
        <div v-else-if="!quizSubmitted" class="quiz-questions">
          <div class="quiz-header">
            <span class="quiz-progress">题目 {{ currentQuestionIndex + 1 }} / {{ quizList.length }}</span>
            <span class="quiz-type-tag" :class="`type-${currentQuestion.questionType}`">{{ getQuestionTypeLabel(currentQuestion.questionType) }}</span>
          </div>
          
          <div class="question-card">
            <h4 class="question-title">{{ currentQuestion.questionText }}</h4>
            
            <!-- 多选题 -->
            <el-checkbox-group v-if="currentQuestion.questionType === 'multiple_choice'" v-model="userAnswers[currentQuestionIndex]">
              <el-checkbox v-for="(option, idx) in currentQuestion.options" :key="idx" :label="String.fromCharCode(65 + idx)">
                {{ String.fromCharCode(65 + idx) }}. {{ option.replace(/^[A-D]\.\s*/, '') }}
              </el-checkbox>
            </el-checkbox-group>
            
            <!-- 判断题 -->
            <el-radio-group v-else-if="currentQuestion.questionType === 'true_false'" v-model="userAnswers[currentQuestionIndex]">
              <el-radio label="正确">正确</el-radio>
              <el-radio label="错误">错误</el-radio>
            </el-radio-group>
            
            <!-- 有选项的题目（单选题、应用题等） -->
            <el-radio-group v-else-if="currentQuestion.options && currentQuestion.options.length > 0" v-model="userAnswers[currentQuestionIndex]">
              <el-radio v-for="(option, idx) in currentQuestion.options" :key="idx" :label="String.fromCharCode(65 + idx)">
                {{ String.fromCharCode(65 + idx) }}. {{ option.replace(/^[A-D]\.\s*/, '') }}
              </el-radio>
            </el-radio-group>
            
            <!-- 无选项的简答题（计算题、应用题等） -->
            <el-input
              v-else
              v-model="userAnswers[currentQuestionIndex]"
              type="textarea"
              :rows="4"
              placeholder="请输入您的答案..."
            />
          </div>
          
          <div class="quiz-actions">
            <el-button 
              @click="prevQuestion" 
              :disabled="currentQuestionIndex === 0"
            >
              上一题
            </el-button>
            <el-button 
              v-if="currentQuestionIndex < quizList.length - 1"
              type="primary" 
              class="brand-btn"
              @click="nextQuestion"
            >
              下一题
            </el-button>
            <el-button 
              v-else
              type="success" 
              class="brand-btn-success"
              @click="submitQuiz"
              :loading="isSubmitting"
            >
              提交答案
            </el-button>
          </div>
        </div>
        
        <!-- 结果状态 -->
        <div v-else class="quiz-result">
          <div class="result-header">
            <el-icon class="result-icon" size="64" :color="quizResult.score >= 60 ? '#1442D3' : '#F56C6C'">
              <CircleCheck v-if="quizResult.score >= 60" />
              <CircleClose v-else />
            </el-icon>
            <h3>{{ quizResult.score >= 60 ? '测验通过！' : '继续加油！' }}</h3>
            <p class="score-text">得分: <span class="score">{{ quizResult.score }}</span> 分</p>
          </div>
          
          <div class="result-details">
            <div class="result-summary">
              <p>总题数: {{ quizResult.totalQuestions || quizResult.correctCount + quizResult.wrongCount }} 题</p>
              <p>答对: {{ quizResult.correctCount }} 题</p>
              <p>答错: {{ quizResult.wrongCount }} 题</p>
            </div>
            
            <el-divider />
            
            <div class="ai-review" v-if="quizResult.aiReview">
              <h4>AI 批改点评</h4>
              <p class="review-content">{{ quizResult.aiReview }}</p>
            </div>
            
            <!-- 标签页切换：全部题 / 错题 -->
            <el-tabs v-model="resultActiveTab" class="result-tabs">
              <el-tab-pane label="全部题" name="all">
                <div class="complete-answers" v-if="quizResult.allAnswers && quizResult.allAnswers.length > 0">
                  <div v-for="(item, idx) in quizResult.allAnswers" :key="idx" 
                       class="answer-item" :class="{ 'correct': item.isCorrect, 'wrong': !item.isCorrect }">
                    <div class="answer-header">
                      <span class="answer-number">第 {{ idx + 1 }} 题</span>
                      <el-tag size="small" :type="item.isCorrect ? 'success' : 'danger'">
                        {{ item.isCorrect ? '✓ 正确' : '✗ 错误' }}
                      </el-tag>
                      <span class="answer-type">{{ getQuestionTypeLabel(item.questionType) }}</span>
                    </div>
                    <p class="answer-question"><strong>题目：</strong>{{ item.question }}</p>
                    <p class="answer-user"><strong>您的答案：</strong><span :class="{ 'wrong-text': !item.isCorrect }">{{ formatAnswer(item.userAnswer) || '未作答' }}</span></p>
                    <p class="answer-correct"><strong>正确答案：</strong>{{ formatAnswer(item.correctAnswer) }}</p>
                    <p v-if="!item.isCorrect && item.explanation" class="answer-explain"><strong>解析：</strong>{{ item.explanation }}</p>
                  </div>
                </div>
              </el-tab-pane>
              
              <el-tab-pane label="错题" name="wrong">
                <div class="complete-answers" v-if="quizResult.allAnswers && quizResult.allAnswers.length > 0">
                  <div v-for="(item, idx) in quizResult.allAnswers.filter(a => !a.isCorrect)" :key="idx" 
                       class="answer-item wrong">
                    <div class="answer-header">
                      <span class="answer-number">第 {{ item.index + 1 }} 题</span>
                      <el-tag size="small" type="danger">✗ 错误</el-tag>
                      <span class="answer-type">{{ getQuestionTypeLabel(item.questionType) }}</span>
                    </div>
                    <p class="answer-question"><strong>题目：</strong>{{ item.question }}</p>
                    <p class="answer-user"><strong>您的答案：</strong><span class="wrong-text">{{ formatAnswer(item.userAnswer) || '未作答' }}</span></p>
                    <p class="answer-correct"><strong>正确答案：</strong>{{ formatAnswer(item.correctAnswer) }}</p>
                    <p v-if="item.explanation" class="answer-explain"><strong>解析：</strong>{{ item.explanation }}</p>
                  </div>
                  <div v-if="quizResult.allAnswers.filter(a => !a.isCorrect).length === 0" class="no-wrong-answers">
                    <el-empty description="恭喜！本次测验没有错题" />
                  </div>
                </div>
              </el-tab-pane>
            </el-tabs>
          </div>
          
          <div class="result-actions">
            <el-button class="btn-back-quiz" @click="restartQuiz">返回测验</el-button>
            <el-button class="brand-btn btn-back-learn" @click="backToLearning">返回学习</el-button>
          </div>
        </div>
      </div>
      
      <!-- 历史记录弹窗 -->
      <el-dialog v-model="showHistoryDialog" title="测验历史记录" width="550px" :fullscreen="showAttemptDetail" class="history-dialog">
        <!-- 历史列表 -->
        <div v-if="!showAttemptDetail">
          <div v-if="attemptHistory.length === 0" class="history-empty">
            <el-empty description="暂无历史记录" />
          </div>
          <div v-else class="history-list">
            <div v-for="(attempt, idx) in attemptHistory" :key="attempt.attemptId" class="history-item">
              <div class="history-info">
                <span class="history-index">第 {{ attemptHistory.length - idx }} 次</span>
                <span class="history-score" :class="{ 'pass': attempt.totalScore >= 60 }">
                  {{ attempt.totalScore }}分
                </span>
                <span class="history-detail">
                  {{ attempt.correctCount }}对 / {{ attempt.wrongCount }}错
                </span>
                <span class="history-time">{{ attempt.submitTime }}</span>
              </div>
              <el-button type="primary" size="small" @click="viewAttemptDetailFn(attempt)">查看详情</el-button>
            </div>
          </div>
        </div>
        
        <!-- 某次测验的完整答题详情 -->
        <div v-else class="attempt-detail">
          <div class="detail-header">
            <el-button link @click="showAttemptDetail = false">← 返回列表</el-button>
            <h3>第 {{ selectedAttemptIndex }} 次测验详情</h3>
            <span class="detail-score" :class="{ 'pass': selectedAttempt.totalScore >= 60 }">
              {{ selectedAttempt.totalScore }}分
            </span>
          </div>
          
          <div class="detail-summary">
            <span>总题数: {{ selectedAttempt.totalQuestions }} 题</span>
            <span>答对: {{ selectedAttempt.correctCount }} 题</span>
            <span>答错: {{ selectedAttempt.wrongCount }} 题</span>
            <span>提交时间: {{ selectedAttempt.submitTime }}</span>
          </div>
          
          <el-divider />
          
          <!-- 标签页切换：全部题 / 错题 -->
          <el-tabs v-model="detailActiveTab" class="detail-tabs">
            <el-tab-pane label="全部题" name="all">
              <div class="detail-answers" v-if="selectedAttempt.answersDetail && selectedAttempt.answersDetail.allAnswers">
                <div v-for="(item, idx) in selectedAttempt.answersDetail.allAnswers" :key="idx" 
                     class="detail-answer-item" :class="{ 'correct': item.isCorrect, 'wrong': !item.isCorrect }">
                  <div class="detail-answer-header">
                    <span class="detail-answer-number">第 {{ idx + 1 }} 题</span>
                    <el-tag size="small" :type="item.isCorrect ? 'success' : 'danger'">
                      {{ item.isCorrect ? '✓ 正确' : '✗ 错误' }}
                    </el-tag>
                    <span class="detail-answer-type">{{ getQuestionTypeLabel(item.questionType) }}</span>
                  </div>
                  <p class="detail-answer-question"><strong>题目：</strong>{{ item.question }}</p>
                  <p class="detail-answer-user">
                    <strong>您的答案：</strong>
                    <span :class="{ 'wrong-text': !item.isCorrect }">{{ formatAnswer(item.userAnswer) || '未作答' }}</span>
                  </p>
                  <p class="detail-answer-correct"><strong>正确答案：</strong>{{ formatAnswer(item.correctAnswer) }}</p>
                  <p v-if="item.explanation" class="detail-answer-explain"><strong>解析：</strong>{{ item.explanation }}</p>
                </div>
              </div>
            </el-tab-pane>
            
            <el-tab-pane label="错题" name="wrong">
              <div class="detail-answers" v-if="selectedAttempt.answersDetail && selectedAttempt.answersDetail.allAnswers">
                <div v-for="(item, idx) in selectedAttempt.answersDetail.allAnswers.filter(a => !a.isCorrect)" :key="idx" 
                     class="detail-answer-item wrong">
                  <div class="detail-answer-header">
                    <span class="detail-answer-number">第 {{ item.index + 1 }} 题</span>
                    <el-tag size="small" type="danger">✗ 错误</el-tag>
                    <span class="detail-answer-type">{{ getQuestionTypeLabel(item.questionType) }}</span>
                  </div>
                  <p class="detail-answer-question"><strong>题目：</strong>{{ item.question }}</p>
                  <p class="detail-answer-user">
                    <strong>您的答案：</strong>
                    <span class="wrong-text">{{ formatAnswer(item.userAnswer) || '未作答' }}</span>
                  </p>
                  <p class="detail-answer-correct"><strong>正确答案：</strong>{{ formatAnswer(item.correctAnswer) }}</p>
                  <p v-if="item.explanation" class="detail-answer-explain"><strong>解析：</strong>{{ item.explanation }}</p>
                </div>
                <div v-if="selectedAttempt.answersDetail.allAnswers.filter(a => !a.isCorrect).length === 0" class="no-wrong-answers">
                  <el-empty description="恭喜！本次测验没有错题" />
                </div>
              </div>
            </el-tab-pane>
          </el-tabs>
        </div>
      </el-dialog>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { Headset, ChatDotRound, Share, Connection, Loading, DocumentChecked, CircleCheck, CircleClose } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import ChatArea from './ChatArea.vue'
import InputBox from './InputBox.vue'
import { getMindmap, getKnowledgeGraph } from '@/api/lesson'
import { listQuizzes, submitAnswer, getStudentAnswers, getQuizAttempts } from '@/api/quiz'

const props = defineProps({
  width: { type: Number, default: 350 },
  mode: { type: String, default: 'lecture' },
  script: { type: String, default: '' },
  audioUrl: { type: String, default: '' },
  history: { type: Array, default: () => [] },
  placeholder: { type: String, default: '输入您的问题...' },
  isChatLoading: { type: Boolean, default: false },
  courseId: { type: [String, Number], default: '' }
})

// 判断字体颜色（用于导图/图谱）
const getTextColor = (bgColor) => {
  if (['#D2E6FE', '#ACB1EC'].includes(bgColor)) return '#1442D3'
  return '#FFFFFF'
}

const emit = defineEmits(['update:mode', 'replay', 'sendMessage', 'resolve', 'speakContent', 'jumpToPage', 'chatTextSelected', 'pauseAudio', 'resumeAudio'])
const inputVal = ref('')
const activeTab = ref('lecture')

const mindmapData = ref(null)
const isGeneratingMindmap = ref(false)
const knowledgeGraphData = ref(null)
const isGeneratingGraph = ref(false)

const handleTabChange = (tab) => {
  if (tab === 'lecture' || tab === 'chat') {
    emit('update:mode', tab)
  }
}

watch(() => activeTab.value, (newTab) => {
  handleTabChange(newTab)
})

watch(() => props.mode, (newMode) => {
  if (newMode && activeTab.value !== newMode) {
    activeTab.value = newMode;
  }
});

const handleLectureTabClick = () => {
  if (quizStarted.value && !quizSubmitted.value) {
    ElMessage.warning('正在进行测验，无法切换到伴随讲解')
    return
  }
  activeTab.value = 'lecture'
}

const handleChatTabClick = () => {
  if (quizStarted.value && !quizSubmitted.value) {
    ElMessage.warning('正在进行测验，无法切换到互动答疑')
    return
  }
  activeTab.value = 'chat'
}

const handleMindmapTabClick = () => {
  if (quizStarted.value && !quizSubmitted.value) {
    ElMessage.warning('正在进行测验，无法切换到思维导图')
    return
  }
  activeTab.value = 'mindmap'
}

const handleKnowledgeTabClick = () => {
  if (quizStarted.value && !quizSubmitted.value) {
    ElMessage.warning('正在进行测验，无法切换到知识图谱')
    return
  }
  activeTab.value = 'knowledge'
}

const handleQuizTabClick = () => {
  emit('pauseAudio')
  activeTab.value = 'quiz'
}

// --- Mind Map Logic ---
const convertMindmapData = (backendData) => {
  if (!backendData || !backendData.root) return null;
  const root = backendData.root;
  // 替换为提供的四种品牌色
  const colors = ['#307AE3', '#ACB1EC', '#1442D3', '#D2E6FE'];
  const calcWidth = (text) => Math.max(140, (text.length * 16) + 40);

  const numBranches = root.children ? root.children.length : 0;
  const ySpacing = 120;
  const totalHeight = ySpacing * (numBranches - 1);
  const startY = (600 - totalHeight) / 2;

  const branches = root.children ? root.children.map((child, index) => {
    const label = child.text || child.label || '分支';
    const branchWidth = calcWidth(label); 
    const branchX = 450;
    const branchY = startY + index * ySpacing;
    
    const children = child.children ? child.children.map((sub, subIndex) => {
        const numChildren = child.children.length;
        const childYOffset = (subIndex - (numChildren - 1) / 2) * 25;
        return {
            x: branchX + (branchWidth / 2) + 60, 
            y: branchY + childYOffset,
            label: sub.text || sub.label || '子项'
        };
    }) : [];
    
    return {
      x: branchX, y: branchY, width: branchWidth, height: 45,
      label: label, color: colors[index % colors.length], children: children
    };
  }) : [];
  
  return {
    center: {
      label: root.text || root.label || '课件主题',
      x: 160, y: 300, width: Math.min(260, (root.text?.length || 8) * 16 + 40), height: 60
    },
    branches: branches
  };
};

const getBranchLinePath = (branch) => {
    if (!mindmapData.value || !mindmapData.value.center) return '';
    const center = mindmapData.value.center;
    const startX = center.x + (center.width / 2);
    const startY = center.y;
    const endX = branch.x - (branch.width / 2);
    const endY = branch.y;
    const c1x = startX + (endX - startX) * 0.5;
    const c1y = startY;
    const c2x = startX + (endX - startX) * 0.5;
    const c2y = endY;
    return `M ${startX} ${startY} C ${c1x} ${c1y}, ${c2x} ${c2y}, ${endX} ${endY}`;
};

const subLines = computed(() => {
    if (!mindmapData.value) return [];
    const lines = [];
    mindmapData.value.branches.forEach(branch => {
        if (branch.children) {
            const startX = branch.x + branch.width / 2;
            const startY = branch.y;
            branch.children.forEach(child => {
                const endX = child.x - 5;
                const endY = child.y;
                const c1x = startX + 40;
                const c1y = startY;
                const c2x = endX - 40;
                const c2y = endY;
                lines.push({
                    path: `M ${startX} ${startY} C ${c1x} ${c1y}, ${c2x} ${c2y}, ${endX} ${endY}`,
                    color: branch.color
                });
            });
        }
    });
    return lines;
});

const computedMindmapViewBox = computed(() => {
    if (!mindmapData.value) return '0 0 1000 600';
    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    const center = mindmapData.value.center;
    minX = Math.min(minX, center.x - center.width / 2);
    maxX = Math.max(maxX, center.x + center.width / 2);
    minY = Math.min(minY, center.y - center.height / 2);
    maxY = Math.max(maxY, center.y + center.height / 2);
    
    mindmapData.value.branches.forEach(branch => {
        minX = Math.min(minX, branch.x - branch.width / 2);
        maxX = Math.max(maxX, branch.x + branch.width / 2);
        minY = Math.min(minY, branch.y - branch.height / 2);
        maxY = Math.max(maxY, branch.y + branch.height / 2);
        if (branch.children) {
            branch.children.forEach(sub => {
                const textWidth = (sub.label || '').length * 16; 
                maxX = Math.max(maxX, sub.x + textWidth);
                minY = Math.min(minY, sub.y - 15);
                maxY = Math.max(maxY, sub.y + 15);
            });
        }
    });
    const padding = 80;
    let w = maxX - minX + padding * 2;
    let h = maxY - minY + padding * 2;
    w = Math.max(w, 800);
    h = Math.max(h, 500);
    const cx = (minX + maxX) / 2;
    const cy = (minY + maxY) / 2;
    return `${cx - w/2} ${cy - h/2} ${w} ${h}`;
});


// --- Knowledge Graph Logic ---
const convertKnowledgeGraphData = (backendData) => {
  if (!backendData || !backendData.nodes || backendData.nodes.length === 0) return null;
  const rawNodes = backendData.nodes;
  const rawEdges = backendData.edges || [];

  // 替换为提供的四种品牌色
  const colors = ['#307AE3', '#ACB1EC', '#1442D3', '#D2E6FE'];
  const nodesMap = {};
  
  const degreeMap = {};
  rawNodes.forEach(n => degreeMap[n.id] = 0);
  rawEdges.forEach(e => {
      if(degreeMap[e.source] !== undefined) degreeMap[e.source]++;
      if(degreeMap[e.target] !== undefined) degreeMap[e.target]++;
  });

  let rootId = rawNodes[0].id;
  let maxDegree = -1;
  for (const id in degreeMap) {
      if (degreeMap[id] > maxDegree) { maxDegree = degreeMap[id]; rootId = id; }
  }

  rawNodes.forEach(n => { nodesMap[n.id] = { ...n, level: 99, children: [] }; });
  nodesMap[rootId].level = 0;
  const queue = [rootId];
  while (queue.length > 0) {
      const currentId = queue.shift();
      const currentLevel = nodesMap[currentId].level;
      rawEdges.forEach(e => {
          let neighborId = null;
          if (e.source === currentId) neighborId = e.target;
          else if (e.target === currentId) neighborId = e.source;

          if (neighborId && nodesMap[neighborId] && nodesMap[neighborId].level > currentLevel + 1) {
              nodesMap[neighborId].level = currentLevel + 1;
              nodesMap[neighborId].parentId = currentId;
              nodesMap[currentId].children.push(neighborId);
              queue.push(neighborId);
          }
      });
  }

  const formatTextLines = (text) => {
      if (!text) return [];
      if (text.length <= 4) return [text];
      const mid = Math.ceil(text.length / 2);
      return [text.slice(0, mid), text.slice(mid)];
  };

  const nodes = [];
  rawNodes.forEach(rawNode => {
      const node = nodesMap[rawNode.id];
      node.x = 400 + (Math.random() - 0.5) * 400;
      node.y = 300 + (Math.random() - 0.5) * 400;
      node.vx = 0;
      node.vy = 0;
      
      if (node.level === 0) {
          node.size = 85; 
          node.color = '#1442D3'; 
      } else if (node.level === 1) {
          node.size = 65;
          const siblings = rawNodes.filter(n => nodesMap[n.id].level === 1);
          const index = siblings.findIndex(n => n.id === node.id);
          node.assignedColor = colors[index % colors.length];
          node.color = node.assignedColor;
      } else {
          node.size = 50;
          const parent = nodesMap[node.parentId] || nodesMap[rootId];
          node.color = parent.assignedColor || '#307AE3';
      }
      
      node.textColor = getTextColor(node.color);
      node.lines = formatTextLines(node.name || node.label || '未命名');
      nodes.push(node);
  });

  const iterations = 150; 
  const k = 220; 
  const centerGravity = 0.02; 
  
  for (let i = 0; i < iterations; i++) {
      const temp = 1 - i / iterations; 
      for (let j = 0; j < nodes.length; j++) {
          for (let m = j + 1; m < nodes.length; m++) {
              let u = nodes[j];
              let v = nodes[m];
              let dx = u.x - v.x;
              let dy = u.y - v.y;
              let dist = Math.sqrt(dx * dx + dy * dy);
              if (dist === 0) dist = 0.1; 
              
              let minAllowedDist = u.size + v.size + 40; 
              if (dist < minAllowedDist * 2.5) {
                  let f = (k * k) / dist; 
                  if (dist < minAllowedDist) f *= 8; 
                  
                  let fx = (dx / dist) * f;
                  let fy = (dy / dist) * f;
                  u.vx += fx; u.vy += fy;
                  v.vx -= fx; v.vy -= fy;
              }
          }
      }

      rawEdges.forEach(e => {
          let u = nodesMap[e.source];
          let v = nodesMap[e.target];
          if(u && v) {
              let dx = v.x - u.x;
              let dy = v.y - u.y;
              let dist = Math.sqrt(dx * dx + dy * dy);
              if (dist === 0) dist = 0.1;
              let f = (dist * dist) / (k * 1.5);
              let fx = (dx / dist) * f;
              let fy = (dy / dist) * f;
              u.vx += fx; u.vy += fy;
              v.vx -= fx; v.vy -= fy;
          }
      });

      nodes.forEach(u => {
          u.vx += (400 - u.x) * centerGravity;
          u.vy += (300 - u.y) * centerGravity;
          let speed = Math.sqrt(u.vx * u.vx + u.vy * u.vy);
          let maxMove = 40 * temp;
          if (speed > maxMove) {
              u.vx = (u.vx / speed) * maxMove;
              u.vy = (u.vy / speed) * maxMove;
          }
          u.x += u.vx;
          u.y += u.vy;
          u.vx = 0; u.vy = 0;
      });
  }

  const processedEdges = rawEdges.map(e => {
      const sourceNode = nodesMap[e.source];
      const targetNode = nodesMap[e.target];
      if(!sourceNode || !targetNode) return null;
      const x1 = sourceNode.x, y1 = sourceNode.y;
      const x2 = targetNode.x, y2 = targetNode.y;
      const mx = (x1 + x2) / 2;
      const my = (y1 + y2) / 2;
      let angle = Math.atan2(y2 - y1, x2 - x1) * 180 / Math.PI;
      if (angle > 90 || angle < -90) angle += 180;
      return {
          id: `${e.source}-${e.target}`,
          x1, y1, x2, y2, mx, my, angle,
          label: e.label || e.relation || e.name || ''
      };
  }).filter(e => e !== null);

  return { nodes, edges: processedEdges };
}

const computedGraphViewBox = computed(() => {
    if (!knowledgeGraphData.value || !knowledgeGraphData.value.nodes.length) {
        return '0 0 800 600';
    }
    const nodes = knowledgeGraphData.value.nodes;
    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    nodes.forEach(n => {
        if (n.x - n.size < minX) minX = n.x - n.size;
        if (n.x + n.size > maxX) maxX = n.x + n.size;
        if (n.y - n.size < minY) minY = n.y - n.size;
        if (n.y + n.size > maxY) maxY = n.y + n.size;
    });
    if (minX === Infinity) return '0 0 800 600';
    const padding = 120;
    let w = maxX - minX + padding * 2;
    let h = maxY - minY + padding * 2;
    w = Math.max(w, 800);
    h = Math.max(h, 600);
    const cx = (minX + maxX) / 2;
    const cy = (minY + maxY) / 2;
    return `${cx - w/2} ${cy - h/2} ${w} ${h}`;
});

const generateMindmap = async () => {
  if (!props.courseId) return ElMessage.warning('请先选择课程');
  isGeneratingMindmap.value = true;
  try {
    const res = await getMindmap(props.courseId); 
    if (res.data) { mindmapData.value = convertMindmapData(res.data); ElMessage.success('思维导图生成成功'); } 
    else ElMessage.warning('暂无思维导图数据');
  } catch (e) { ElMessage.error('生成思维导图失败'); } 
  finally { isGeneratingMindmap.value = false; }
}

const generateKnowledgeGraph = async () => {
  if (!props.courseId) return ElMessage.warning('请先选择课程');
  isGeneratingGraph.value = true;
  try {
    const res = await getKnowledgeGraph(props.courseId)
    if (res.data && res.data.nodes && res.data.nodes.length > 0) { knowledgeGraphData.value = convertKnowledgeGraphData(res.data); ElMessage.success('知识图谱生成成功'); } 
    else ElMessage.warning('暂无知识图谱数据');
  } catch (e) { ElMessage.error('生成知识图谱失败'); } 
  finally { isGeneratingGraph.value = false; }
}

const onSend = () => {
  if (inputVal.value.trim()) { emit('sendMessage', inputVal.value); inputVal.value = ''; }
}

let svgScale = 1
const handleSvgWheel = (e) => {
  if (e.ctrlKey || e.metaKey) {
    e.preventDefault()
    const svg = e.target.closest('svg')
    if (svg) {
      svgScale += e.deltaY > 0 ? -0.1 : 0.1
      svgScale = Math.max(0.2, Math.min(svgScale, 4))
      svg.style.transform = `scale(${svgScale})`
      svg.style.transformOrigin = 'center'
    }
  }
}

const resetGraphData = () => { mindmapData.value = null; knowledgeGraphData.value = null; svgScale = 1; }

// --- Quiz Logic ---
const quizStarted = ref(false)
const quizSubmitted = ref(false)
const isLoadingQuiz = ref(false)
const isSubmitting = ref(false)
const quizList = ref([])
const currentQuestionIndex = ref(0)
const userAnswers = ref([])
const quizResult = ref(null)
const lastAttempt = ref(null)
const attemptHistory = ref([])
const showHistoryDialog = ref(false)
const showAttemptDetail = ref(false)
const selectedAttempt = ref(null)
const selectedAttemptIndex = ref(0)
const detailActiveTab = ref('all')
const resultActiveTab = ref('all')

const currentQuestion = computed(() => quizList.value[currentQuestionIndex.value] || null)

const getQuestionTypeLabel = (type) => {
  const labels = { 'single_choice': '单选题', 'multiple_choice': '多选题', 'true_false': '判断题', 'calculation': '计算题', 'application': '应用题' }
  return labels[type] || '未知题型'
}
const formatAnswer = (answer) => Array.isArray(answer) ? answer.join(', ') : (answer || '未作答')

const loadLastAttempt = async () => {
  if (!props.courseId) return;
  try {
    const res = await getStudentAnswers(props.courseId)
    if (res.data && res.data.totalCount > 0) lastAttempt.value = res.data;
    else lastAttempt.value = null;
  } catch (e) { lastAttempt.value = null; }
}

const viewLastAttempt = () => {
  if (!lastAttempt.value) return;
  const history = lastAttempt.value;
  const answersDetail = history.answersDetail || {};
  quizResult.value = {
    score: history.totalScore || 0,
    correctCount: history.correctCount || 0,
    wrongCount: history.wrongCount || 0,
    totalQuestions: history.totalCount || 0,
    aiReview: answersDetail.aiReview || '',
    allAnswers: answersDetail.allAnswers || []
  };
  quizStarted.value = true; quizSubmitted.value = true; currentQuestionIndex.value = 0;
}

const showAttemptHistory = async () => {
  if (!props.courseId) return;
  try {
    const res = await getQuizAttempts(props.courseId)
    if (res.data && res.data.attempts) attemptHistory.value = res.data.attempts;
    else attemptHistory.value = [];
    showHistoryDialog.value = true;
  } catch (e) { ElMessage.error('加载历史记录失败'); }
}

const viewAttemptDetailFn = (attempt) => {
  selectedAttempt.value = attempt
  const idx = attemptHistory.value.findIndex(a => a.attemptId === attempt.attemptId)
  selectedAttemptIndex.value = attemptHistory.value.length - idx
  showAttemptDetail.value = true
}

const startQuiz = async () => {
  if (!props.courseId) return ElMessage.warning('请先选择课件');
  isLoadingQuiz.value = true;
  try {
    const quizRes = await listQuizzes(props.courseId)
    const quizzes = quizRes.data?.quizzes || quizRes.data || []
    if (quizzes.length > 0) {
      quizList.value = quizzes
      userAnswers.value = quizList.value.map(q => q.questionType === 'multiple_choice' ? [] : '')
      quizStarted.value = true; quizSubmitted.value = false; quizResult.value = null; currentQuestionIndex.value = 0;
      ElMessage.success(`加载了 ${quizzes.length} 道测验题`)
    } else { ElMessage.warning('暂无测验题'); }
  } catch (e) { ElMessage.error('加载测验题失败'); } 
  finally { isLoadingQuiz.value = false; }
}

const nextQuestion = () => { if (currentQuestionIndex.value < quizList.value.length - 1) currentQuestionIndex.value++; }
const prevQuestion = () => { if (currentQuestionIndex.value > 0) currentQuestionIndex.value--; }

const submitQuiz = async () => {
  const unanswered = userAnswers.value.findIndex((ans) => Array.isArray(ans) ? ans.length === 0 : !ans || ans.trim() === '');
  if (unanswered !== -1) { ElMessage.warning(`第 ${unanswered + 1} 题尚未作答`); currentQuestionIndex.value = unanswered; return; }
  
  isSubmitting.value = true;
  try {
    const answers = quizList.value.map((quiz, index) => ({ quizId: quiz.id, answer: userAnswers.value[index] }))
    const res = await submitAnswer({ lessonId: props.courseId, answers: answers })
    if (res.data) { quizResult.value = res.data; quizSubmitted.value = true; ElMessage.success('提交成功！'); }
  } catch (e) { ElMessage.error('提交答案失败'); } 
  finally { isSubmitting.value = false; }
}

const restartQuiz = () => { quizStarted.value = false; quizSubmitted.value = false; quizList.value = []; userAnswers.value = []; quizResult.value = null; currentQuestionIndex.value = 0; }
const backToLearning = () => { activeTab.value = 'lecture'; emit('resumeAudio'); }
const resetQuizData = () => { restartQuiz(); }

watch(() => props.courseId, (newCourseId) => { if (newCourseId) loadLastAttempt(); }, { immediate: true })
defineExpose({ resetGraphData, resetQuizData })
</script>

<style scoped>
/* 统一风格变量 - 严格遵循四种品牌色 */
.ai-sidebar {
  --primary-blue: #307AE3;
  --dark-blue: #1442D3;
  --lavender: #ACB1EC;
  --light-blue: #D2E6FE;
  --bg-color: #F8FAFC;
  --text-main: #1E293B;
  --text-sub: #64748B;
  --success-green: #307AE3; /* 成功色也向主题蓝靠拢 */
  --danger-red: #F56C6C;
  
  min-width: 300px;
  max-width: 800px;
  background: #FFFFFF;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  overflow: hidden;
  border-left: 1px solid var(--light-blue);
  box-shadow: -4px 0 16px rgba(48, 122, 227, 0.05);
  margin: 0;
}

/* 品牌通用工具类 */
.brand-btn {
  background: linear-gradient(135deg, var(--primary-blue), var(--dark-blue)) !important;
  border: none !important;
  box-shadow: 0 4px 12px rgba(48, 122, 227, 0.2) !important;
  border-radius: 12px !important;
}
.brand-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(20, 66, 211, 0.3) !important;
}
.brand-btn-success {
  background: var(--dark-blue) !important;
  border: none !important;
  border-radius: 12px !important;
}
.brand-primary-text { color: var(--primary-blue) !important; }

/* 顶部标签栏 */
.sidebar-tabs {
  display: flex;
  background: #FFFFFF;
  border-bottom: 1px solid var(--light-blue);
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
  scrollbar-width: none;
}
.sidebar-tabs::-webkit-scrollbar { display: none; }

.tab-item {
  flex: 1; text-align: center; padding: 14px 12px; cursor: pointer; 
  font-size: 14px; color: var(--text-sub); 
  display: flex; align-items: center; justify-content: center; gap: 6px;
  transition: all 0.3s ease; position: relative; font-weight: 600; white-space: nowrap; 
}
.tab-item:hover { background: var(--bg-color); color: var(--primary-blue); }
.tab-item.active { color: var(--dark-blue); background: var(--light-blue); }
.tab-item.active::after {
  content: ''; position: absolute; bottom: 0; left: 0; width: 100%; height: 3px;
  background: var(--dark-blue);
}

/* 思维导图/知识图谱容器 */
.mindmap-container, .knowledge-graph-container {
  flex: 1; overflow: auto; padding: 20px; background: var(--bg-color); 
  display: flex; align-items: center; justify-content: center; width: 100%;
}
.mindmap-content, .knowledge-graph-content {
  height: 100%; width: 100%; display: flex; flex-direction: column; align-items: center; justify-content: center;
}
.mindmap-placeholder, .knowledge-graph-placeholder {
  display: flex; flex-direction: column; align-items: center; justify-content: center; 
  height: 100%; text-align: center; color: var(--text-sub); width: 100%;
}
.mindmap-placeholder h3, .knowledge-graph-placeholder h3 { 
  margin: 16px 0 8px; font-size: 18px; color: var(--dark-blue); font-weight: 800; 
}
.mindmap-placeholder p, .knowledge-graph-placeholder p { margin-bottom: 20px; color: var(--text-sub); }

.mindmap-visualization, .knowledge-graph-visualization { 
  height: 100%; width: 100%; display: flex; flex-direction: column; 
}
.mindmap-loading, .knowledge-graph-loading { 
  display: flex; align-items: center; justify-content: center; gap: 10px; height: 100%; font-weight: 600; 
}

/* 画布容器 */
.mindmap-canvas, .knowledge-graph-canvas {
  flex: 1; display: flex; align-items: center; justify-content: center; 
  background: #FFFFFF; border-radius: 20px; 
  box-shadow: 0 8px 24px rgba(20, 66, 211, 0.06); overflow: auto; position: relative;
  border: 1px solid var(--light-blue);
}
.mindmap-svg, .knowledge-graph-svg {
  width: 100%; height: 100%; max-width: none; max-height: none; cursor: grab; transition: transform 0.2s ease;
}

/* --- 思维导图样式 --- */
.mindmap-svg text { font-family: 'PingFang SC', sans-serif; pointer-events: none; }
.mindmap-center-node { filter: drop-shadow(0 4px 8px rgba(20, 66, 211, 0.2)); transition: all 0.3s ease; }
.mindmap-center-node:hover { filter: drop-shadow(0 8px 16px rgba(20, 66, 211, 0.3)); transform: scale(1.02); }
.mindmap-center text { font-size: 20px; font-weight: 800; fill: #FFFFFF; }
.mindmap-branch-node { filter: drop-shadow(0 2px 6px rgba(48, 122, 227, 0.15)); transition: all 0.3s ease; }
.mindmap-branch:hover .mindmap-branch-node { transform: scale(1.05); filter: drop-shadow(0 6px 12px rgba(48, 122, 227, 0.25)); }
.mindmap-branch text { font-size: 15px; font-weight: 700; }
.mindmap-sub text { font-size: 14px; fill: var(--text-sub); transition: all 0.3s ease; font-weight: 500; }
.mindmap-branch:hover .mindmap-sub text { fill: var(--dark-blue); font-weight: 600; }
.mindmap-line { stroke-linecap: round; opacity: 0.9; transition: all 0.3s ease; }
.mindmap-branch:hover ~ .mindmap-lines .mindmap-line { opacity: 0.2; }
.mindmap-branch:hover .mindmap-line { opacity: 1; stroke-width: 4px; }

/* --- 知识图谱样式 --- */
.knowledge-graph-svg text { font-family: 'PingFang SC', sans-serif; pointer-events: none; }
.knowledge-graph-node { transition: all 0.3s ease; cursor: pointer; }
.knowledge-graph-node:hover circle { filter: drop-shadow(0 6px 16px rgba(48, 122, 227, 0.3)); transform: scale(1.08); transform-origin: center; }
.edge-text { font-family: 'PingFang SC', sans-serif; letter-spacing: 1px; font-weight: 600;}

/* 测验中禁用提示 */
.quiz-blocking-overlay {
  flex: 1; display: flex; align-items: center; justify-content: center;
  background: var(--bg-color); padding: 40px 20px; border-radius: 20px; margin: 20px;
}
.quiz-blocking-content { text-align: center; color: var(--text-sub); }
.quiz-blocking-content .el-icon { margin-bottom: 16px; }
.quiz-blocking-content p { margin: 0 0 20px 0; font-size: 15px; font-weight: 600; }

/* 测验题样式 */
.quiz-container { display: flex; flex: 1; overflow: auto; flex-direction: column; background: var(--bg-color); }
.quiz-content { padding: 20px; flex: 1; overflow-y: auto; }
.quiz-placeholder { text-align: center; padding: 40px 20px; background: #FFFFFF; border-radius: 24px; box-shadow: 0 4px 16px rgba(20, 66, 211, 0.05); }
.quiz-placeholder h3 { margin: 16px 0 8px; color: var(--dark-blue); font-size: 20px; font-weight: 800; }
.quiz-placeholder p { color: var(--text-sub); font-size: 14px; margin-bottom: 24px; }
.quiz-hint { color: var(--danger-red); font-size: 12px; margin-top: 10px; }

/* 最近一次测验记录 */
.last-attempt-info { margin: 24px 0; width: 100%; }
.attempt-title { font-size: 16px; color: var(--text-main); margin-bottom: 12px; font-weight: 700; }
.attempt-stats { display: flex; align-items: center; justify-content: center; gap: 20px; margin-bottom: 16px; padding: 16px; background: var(--light-blue); border-radius: 16px; }
.attempt-score { font-size: 28px; font-weight: 800; color: var(--danger-red); }
.attempt-score.pass { color: var(--dark-blue); }
.attempt-detail { font-size: 15px; color: var(--primary-blue); font-weight: 600; }
.attempt-time { font-size: 13px; color: var(--text-sub); }
.attempt-actions { display: flex; justify-content: center; gap: 12px; }

/* 测验做题界面 */
.quiz-questions { padding: 10px; }
.quiz-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; padding-bottom: 12px; border-bottom: 1px solid var(--light-blue); }
.quiz-progress { font-size: 16px; color: var(--dark-blue); font-weight: 800; }
.quiz-type-tag { font-size: 13px; padding: 6px 16px; border-radius: 20px; font-weight: 600; background: var(--light-blue); color: var(--primary-blue); }

.question-card { background: #FFFFFF; border-radius: 20px; padding: 24px; margin-bottom: 24px; box-shadow: 0 4px 16px rgba(20, 66, 211, 0.05); border: 1px solid var(--light-blue); }
.question-title { font-size: 17px; color: var(--text-main); margin-bottom: 24px; line-height: 1.6; font-weight: 700; }
.question-card :deep(.el-radio-group), .question-card :deep(.el-checkbox-group) { display: flex; flex-direction: column; gap: 14px; width: 100%; }
.question-card :deep(.el-radio), .question-card :deep(.el-checkbox) { margin-right: 0; padding: 14px 20px; background: #F8FAFC; border-radius: 12px; border: 1px solid var(--light-blue); transition: all 0.3s; width: 100%; box-sizing: border-box; }
.question-card :deep(.el-radio:hover), .question-card :deep(.el-checkbox:hover) { border-color: var(--primary-blue); background: var(--light-blue); }
.question-card :deep(.el-radio.is-checked), .question-card :deep(.el-checkbox.is-checked) { border-color: var(--dark-blue); background: var(--light-blue); }
.question-card :deep(.el-radio__label), .question-card :deep(.el-checkbox__label) { padding-left: 10px; font-size: 15px; font-weight: 600; color: var(--text-main); }
.quiz-actions { display: flex; justify-content: space-between; margin-top: 24px; }

/* 测验结果页 */
.quiz-result { padding: 10px; }
.result-header { text-align: center; padding: 32px 20px; background: #FFFFFF; border-radius: 24px; margin-bottom: 24px; box-shadow: 0 4px 16px rgba(20, 66, 211, 0.05); }
.result-icon { margin-bottom: 16px; }
.result-header h3 { font-size: 24px; color: var(--dark-blue); margin-bottom: 10px; font-weight: 800; }
.score-text { font-size: 16px; color: var(--text-sub); font-weight: 600; }
.score { font-size: 40px; font-weight: 900; color: var(--primary-blue); }

.result-details { background: #FFFFFF; border-radius: 24px; padding: 24px; margin-bottom: 24px; box-shadow: 0 4px 16px rgba(20, 66, 211, 0.05); border: 1px solid var(--light-blue); }
.result-summary { display: flex; justify-content: space-around; text-align: center; margin-bottom: 20px; padding: 16px; background: var(--bg-color); border-radius: 16px; }
.result-summary p { margin: 0; color: var(--primary-blue); font-size: 15px; font-weight: 700; }

.ai-review { margin: 24px 0; }
.ai-review h4 { color: var(--dark-blue); margin-bottom: 12px; font-size: 16px; font-weight: 800; }
.review-content { color: var(--text-main); line-height: 1.8; background: var(--bg-color); padding: 20px; border-radius: 16px; border-left: 4px solid var(--primary-blue); font-weight: 500; }

.answer-item, .detail-answer-item { background: var(--bg-color); border-radius: 16px; padding: 20px; margin-bottom: 16px; border-left: 4px solid var(--lavender); transition: all 0.3s ease; }
.answer-item:hover, .detail-answer-item:hover { box-shadow: 0 4px 12px rgba(48, 122, 227, 0.1); transform: translateX(4px); }
.answer-item.correct, .detail-answer-item.correct { border-left-color: var(--primary-blue); background: var(--light-blue); }
.answer-item.wrong, .detail-answer-item.wrong { border-left-color: var(--danger-red); background: #FFF0F0; }
.answer-header, .detail-answer-header { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }
.answer-number, .detail-answer-number { font-weight: 800; color: var(--dark-blue); font-size: 15px; }
.answer-question, .detail-answer-question { color: var(--text-main); margin-bottom: 12px; line-height: 1.6; font-weight: 600; }
.answer-user, .detail-answer-user, .answer-correct, .detail-answer-correct, .answer-explain, .detail-answer-explain { font-size: 14px; margin: 8px 0; font-weight: 500; }
.wrong-text { color: var(--danger-red); text-decoration: line-through; }
.answer-correct, .detail-answer-correct { color: var(--primary-blue); font-weight: 700; }
.answer-explain, .detail-answer-explain { color: var(--text-sub); background: #FFFFFF; padding: 14px; border-radius: 12px; margin-top: 12px; border: 1px solid var(--light-blue); }
.no-wrong-answers { padding: 40px 0; text-align: center; }
.result-actions { display: flex; justify-content: center; gap: 16px; margin-top: 20px; }

/* 响应式适配 */
@media (max-width: 1024px) {
  .ai-sidebar { border-left: none; border-top: 1px solid var(--light-blue); flex-direction: row; }
  .sidebar-tabs { flex-direction: column; min-width: 100px; }
  .tab-item { padding: 16px 0; font-size: 13px; }
  .tab-item.active::after { width: 4px; height: 100%; left: 0; bottom: auto; }
}
@media (max-width: 768px) {
  .ai-sidebar { border-left: none; border-top: 1px solid var(--light-blue); flex-direction: column; height: auto; max-height: none; }
  .sidebar-tabs { flex-direction: row; flex: none; overflow-x: auto; height: 56px; }
  .mindmap-container, .knowledge-graph-container { display: flex; flex: 1; overflow: auto; }
  .tab-item { padding: 12px 8px; font-size: 13px; gap: 4px; flex: 1; }
  .tab-item.active::after { width: 100%; height: 3px; left: 0; bottom: 0; }
}
</style>