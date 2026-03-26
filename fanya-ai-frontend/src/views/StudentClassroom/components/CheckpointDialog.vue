<template>
  <el-dialog
    v-model="visible"
    title="智能考点检测"
    width="90%"
    :style="{ maxWidth: '500px' }"
    :close-on-click-modal="false"
    :close-on-press-escape="false"
    :show-close="false"
    center
    class="checkpoint-dialog brand-dialog"
  >
    <div class="checkpoint-content">
      <div class="checkpoint-header">
        <el-tag class="flag-tag brand-tag" size="large">
          <el-icon><Flag /></el-icon> 核心考点
        </el-tag>
        <p class="checkpoint-tip">请回答以下问题后继续学习</p>
      </div>

      <div class="question-section glass-box">
        <div class="question-title">{{ checkpoint.question }}</div>
        
        <!-- 选择题 -->
        <el-radio-group v-if="checkpoint.type === 'choice'" v-model="userAnswer" class="answer-options">
          <el-radio 
            v-for="(option, index) in checkpoint.options" 
            :key="index" 
            :label="option"
            :disabled="answered"
            border
            class="brand-radio"
          >
            {{ option }}
          </el-radio>
        </el-radio-group>

        <!-- 判断题 -->
        <el-radio-group v-else-if="checkpoint.type === 'judge'" v-model="userAnswer" class="answer-options">
          <el-radio label="正确" :disabled="answered" border class="brand-radio">✓ 正确</el-radio>
          <el-radio label="错误" :disabled="answered" border class="brand-radio">✗ 错误</el-radio>
        </el-radio-group>

        <!-- 简答题 -->
        <el-input
          v-else
          v-model="userAnswer"
          type="textarea"
          :rows="4"
          placeholder="请输入你的答案..."
          :disabled="answered"
          class="brand-textarea"
        />
      </div>

      <!-- 答案解析 -->
      <transition name="fade">
        <div v-if="answered" class="analysis-section glass-box">
          <el-alert
            :title="isCorrect ? '✓ 回答正确！' : '✗ 回答错误'"
            :type="isCorrect ? 'success' : 'error'"
            :closable="false"
            show-icon
          />
          <div class="analysis-content">
            <div class="analysis-label">正确答案：</div>
            <div class="analysis-text brand-analysis-text">{{ checkpoint.correctAnswer }}</div>
            <div class="analysis-label">解析：</div>
            <div class="analysis-text brand-analysis-text">{{ checkpoint.explanation }}</div>
          </div>
        </div>
      </transition>
    </div>

    <template #footer>
      <div class="dialog-footer">
        <el-button v-if="!answered" class="submit-btn brand-btn" type="primary" @click="submitAnswer" :disabled="!userAnswer" round>
          提交答案
        </el-button>
        <el-button v-else type="success" class="continue-btn brand-btn" @click="continueLearn" round>
          我已理解，继续学习 →
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, watch } from 'vue'
import { Flag } from '@element-plus/icons-vue'
import { saveCheckpointAnswer } from '@/api/quiz'

const props = defineProps({
  modelValue: Boolean,
  checkpoint: {
    type: Object,
    default: () => ({ question: '', type: 'choice', options: [], correctAnswer: '', explanation: '' })
  },
  lessonId: {
    type: [String, Number],
    default: ''
  }
})

const emit = defineEmits(['update:modelValue', 'continue', 'answerSubmitted'])

const visible = ref(false)
const userAnswer = ref('')
const answered = ref(false)
const isCorrect = ref(false)

watch(() => props.modelValue, (val) => {
  visible.value = val
  if (val) { userAnswer.value = ''; answered.value = false; isCorrect.value = false }
})

watch(visible, (val) => emit('update:modelValue', val))

const submitAnswer = async () => {
  if (!userAnswer.value) return
  
  // 判断答案是否正确
  const correct = props.checkpoint.type === 'short' 
    ? userAnswer.value.includes(props.checkpoint.correctAnswer) 
    : userAnswer.value === props.checkpoint.correctAnswer
  
  answered.value = true
  isCorrect.value = correct
  
  // 保存答题记录到后端
  if (props.lessonId && props.checkpoint.id) {
    try {
      await saveCheckpointAnswer({
        lessonId: props.lessonId,
        checkpointId: props.checkpoint.id,
        pageNum: props.checkpoint.pageNum || 0,
        questionText: props.checkpoint.question,
        userAnswer: userAnswer.value,
        correctAnswer: props.checkpoint.correctAnswer,
        isCorrect: correct
      })
      console.log('[Checkpoint] 答题记录已保存')
      emit('answerSubmitted', {
        checkpointId: props.checkpoint.id,
        isCorrect: correct,
        userAnswer: userAnswer.value
      })
    } catch (error) {
      console.error('[Checkpoint] 保存答题记录失败:', error)
    }
  }
}

const continueLearn = () => {
  visible.value = false
  emit('continue')
}
</script>

<style scoped>
/* 弹窗：海洋流体品牌四色深度定制 */
:deep(.brand-dialog .el-dialog) {
  background: #F8FAFC; 
  border-radius: 20px; 
  border: 1px solid #D2E6FE; 
  box-shadow: 0 12px 32px rgba(20, 66, 211, 0.15); 
  overflow: hidden;
}

:deep(.brand-dialog .el-dialog__header) { 
  padding: 24px; 
  background: #FFFFFF; 
  border-bottom: 1px solid #D2E6FE; 
  margin-right: 0;
}

:deep(.brand-dialog .el-dialog__title) { 
  font-size: 18px; 
  font-weight: 800; 
  color: #1442D3; 
}

:deep(.brand-dialog .el-dialog__body) { 
  padding: 24px; 
}

:deep(.brand-dialog .el-dialog__footer) { 
  padding: 16px 24px 24px; 
}

.checkpoint-header { 
  text-align: center; 
  margin-bottom: 24px; 
}

.brand-tag { 
  background: linear-gradient(135deg, #307AE3 0%, #1442D3 100%) !important; 
  border: none !important; 
  color: #FFFFFF !important; 
  font-weight: 700; 
  border-radius: 12px; 
}

.checkpoint-tip { 
  margin-top: 12px; 
  font-size: 14px; 
  color: #64748B; 
  font-weight: 500;
}

.glass-box { 
  background: #FFFFFF; 
  border: 1px solid #D2E6FE; 
  padding: 24px; 
  border-radius: 16px; 
  margin-bottom: 20px; 
  box-shadow: 0 4px 16px rgba(48, 122, 227, 0.05); 
}

.question-title { 
  font-size: 17px; 
  font-weight: 800; 
  color: #1E293B; 
  margin-bottom: 20px; 
  line-height: 1.6;
}

/* 选项美化 */
.brand-radio { 
  border-radius: 12px !important; 
  border: 1px solid #D2E6FE !important; 
  transition: all 0.3s; 
  background: #F8FAFC; 
  width: 100%; 
  box-sizing: border-box;
  margin-right: 0 !important;
  margin-bottom: 12px;
}

.brand-radio:hover:not(.is-disabled) {
  border-color: #307AE3 !important;
  background: #EFF6FF;
}

.brand-radio.is-checked { 
  border-color: #307AE3 !important; 
  background: #EFF6FF !important; 
  box-shadow: 0 0 0 1px #307AE3 inset; 
}

:deep(.brand-radio .el-radio__label) { 
  color: #1E293B !important; 
  font-weight: 600; 
  font-size: 15px;
}

/* 输入框美化 */
.brand-textarea :deep(.el-textarea__inner) { 
  border-radius: 12px; 
  border: 1px solid #D2E6FE; 
  background: #F8FAFC; 
  font-weight: 500; 
  font-size: 15px; 
  padding: 12px;
}

.brand-textarea :deep(.el-textarea__inner:focus) { 
  border-color: #307AE3; 
  box-shadow: 0 0 0 2px rgba(48, 122, 227, 0.1); 
  background: #FFFFFF; 
}

/* 解析区美化 */
.analysis-label { 
  font-weight: 800; 
  color: #1E293B; 
  margin: 16px 0 8px; 
  font-size: 15px;
}

.brand-analysis-text { 
  color: #1442D3; 
  line-height: 1.6; 
  padding: 16px; 
  background: #EFF6FF; 
  border-radius: 12px; 
  margin-top: 5px; 
  border-left: 4px solid #307AE3; 
  font-weight: 600; 
  font-size: 14px;
}

/* 按钮统一 */
.brand-btn { 
  background: linear-gradient(135deg, #307AE3 0%, #1442D3 100%) !important; 
  border: none !important; 
  padding: 12px 32px !important; 
  font-size: 15px !important; 
  font-weight: 700 !important; 
  box-shadow: 0 6px 16px rgba(48, 122, 227, 0.2) !important;
}

.brand-btn:hover { 
  transform: translateY(-2px); 
  box-shadow: 0 8px 24px rgba(20, 66, 211, 0.3) !important;
}

.brand-btn:disabled {
  background: #ACB1EC !important;
  box-shadow: none !important;
  transform: none !important;
}

.fade-enter-active, .fade-leave-active { 
  transition: opacity 0.3s; 
}

.fade-enter-from, .fade-leave-to { 
  opacity: 0; 
}

/* 响应式设计 - 平板 */
@media (max-width: 768px) {
  :deep(.brand-dialog .el-dialog) { 
    width: 95% !important; 
    margin: auto !important; 
  }
  
  .glass-box { 
    padding: 16px; 
    margin-bottom: 16px; 
  }
  
  .question-title { 
    font-size: 16px; 
    margin-bottom: 16px; 
  }
  
  .brand-btn { 
    padding: 10px 24px !important; 
  }
}

/* 响应式设计 - 手机 */
@media (max-width: 480px) {
  :deep(.brand-dialog .el-dialog) {
    width: 98% !important;
  }

  .checkpoint-header { 
    margin-bottom: 16px; 
  }

  .glass-box {
    padding: 14px;
    margin-bottom: 14px;
  }

  .question-title { 
    font-size: 14px; 
    margin-bottom: 10px; 
  }

  .brand-btn {
    padding: 8px 20px !important;
    font-size: 14px !important;
  }

  .checkpoint-tip { 
    font-size: 12px; 
  }

  .brand-analysis-text {
    padding: 10px;
    font-size: 13px;
  }
}
</style>