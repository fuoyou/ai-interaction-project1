<template>
  <div class="quiz-management">
    <header class="quiz-header">
      <h2><el-icon><DocumentCopy /></el-icon> 测验题管理</h2>
      <div class="header-actions">
        <el-button type="primary" @click="generateQuiz" :loading="generating">
          <el-icon class="el-icon--left"><Plus /></el-icon>
          生成测验题
        </el-button>
        <el-button @click="addQuizManually" class="plain-action-btn">
          <el-icon class="el-icon--left"><Edit /></el-icon>
          手动新增题目
        </el-button>
        <el-button @click="exportWord" :disabled="quizzes.length === 0" class="plain-action-btn">
          <el-icon class="el-icon--left"><Download /></el-icon>
          导出Word
        </el-button>
      </div>
    </header>

    <div v-loading="loadingQuizzes" class="quiz-content glass-panel">
      <el-empty v-if="quizzes.length === 0" description="暂无测验题，点击上方按钮生成或新增" />
      
      <div v-else class="quiz-list">
        <div v-for="(quiz, index) in quizzes" :key="quiz.id" class="quiz-card">
          <div class="quiz-card-header">
            <div class="quiz-info">
              <span class="quiz-number">第 {{ index + 1 }} 题</span>
              <span class="quiz-type" :class="`type-${quiz.questionType}`">{{ getQuizTypeName(quiz.questionType) }}</span>
              <span v-if="quiz.source === 'ai'" class="source-tag ai-tag">AI生成</span>
              <span v-else class="source-tag manual-tag">手动添加</span>
            </div>
            <div class="quiz-actions">
              <el-button link type="primary" size="small" @click="editQuiz(quiz)">编辑</el-button>
              <el-button link type="danger" size="small" @click="deleteQuiz(quiz.id)">删除</el-button>
            </div>
          </div>

          <div class="quiz-card-content">
            <p class="question-text"><strong>题目：</strong>{{ quiz.questionText }}</p>
            <div v-if="quiz.options && quiz.options.length > 0" class="options-section">
              <p><strong>选项：</strong></p>
              <ul>
                <li v-for="(opt, idx) in quiz.options" :key="idx">{{ opt }}</li>
              </ul>
            </div>
            <p class="answer-text">
              <strong>答案：</strong>
              <span v-if="['calculation','application'].includes(quiz.questionType)" class="answer-long">{{ quiz.correctAnswer }}</span>
              <span v-else>{{ quiz.correctAnswer }}</span>
            </p>
            <p class="explanation-text"><strong>解析：</strong>{{ quiz.explanation }}</p>
          </div>
        </div>
      </div>
    </div>

    <!-- 新增/编辑题目对话框 -->
    <el-dialog v-model="showQuizDialog" :title="editingQuiz ? '编辑题目' : '新增题目'" width="600px" align-center class="glass-dialog">
      <el-form :model="quizForm" label-width="100px">
        <el-form-item label="题型" required>
          <el-select v-model="quizForm.questionType" placeholder="请选择题型" class="glass-input">
            <el-option label="单选题" value="single_choice" />
            <el-option label="多选题" value="multiple_choice" />
            <el-option label="判断题" value="true_false" />
            <el-option label="计算题" value="calculation" />
            <el-option label="应用题" value="application" />
          </el-select>
        </el-form-item>
        <el-form-item label="题目内容" required>
          <el-input v-model="quizForm.questionText" type="textarea" :rows="3" placeholder="请输入题目内容" class="glass-input" />
        </el-form-item>
        <el-form-item v-if="['single_choice', 'multiple_choice', 'true_false'].includes(quizForm.questionType)" label="选项">
          <div class="options-input">
            <div v-for="(opt, idx) in quizForm.options" :key="idx" class="option-item">
              <el-input v-model="quizForm.options[idx]" :placeholder="`选项 ${String.fromCharCode(65 + idx)}`" class="glass-input"/>
              <el-button link type="danger" @click="quizForm.options.splice(idx, 1)">删除</el-button>
            </div>
            <el-button link type="primary" @click="quizForm.options.push('')">添加选项</el-button>
          </div>
        </el-form-item>
        <el-form-item label="正确答案" required>
          <el-input v-model="quizForm.correctAnswer" placeholder="请输入正确答案" class="glass-input" />
        </el-form-item>
        <el-form-item label="解析" required>
          <el-input v-model="quizForm.explanation" type="textarea" :rows="3" placeholder="请输入答案解析" class="glass-input" />
        </el-form-item>
        <el-form-item label="难度">
          <el-select v-model="quizForm.difficulty" placeholder="请选择难度" class="glass-input">
            <el-option label="简单" value="easy" />
            <el-option label="中等" value="medium" />
            <el-option label="困难" value="hard" />
          </el-select>
        </el-form-item>
        <el-form-item label="分值">
          <el-input-number v-model="quizForm.points" :min="1" :max="100" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showQuizDialog = false" class="glass-btn">取消</el-button>
        <el-button type="primary" @click="saveQuiz" class="glass-btn-primary">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { DocumentCopy, Plus, Edit, Download } from '@element-plus/icons-vue'
import { generateQuiz as generateQuizAPI, listQuizzes, addQuiz, updateQuiz, deleteQuiz as deleteQuizAPI, exportQuizWord } from '@/api/quiz'

const props = defineProps({ lessonId: { type: Number, required: true }, knowledgeDocIds: { type: Array, default: () => [] } })

const quizzes = ref([])
const loadingQuizzes = ref(false)
const generating = ref(false)
const showQuizDialog = ref(false)
const editingQuiz = ref(null)

const quizForm = reactive({ questionType: 'single_choice', questionText: '', options: ['', '', '', ''], correctAnswer: '', explanation: '', difficulty: 'medium', points: 5 })

const getQuizTypeName = (type) => { const names = { 'single_choice': '单选题', 'multiple_choice': '多选题', 'true_false': '判断题', 'calculation': '计算题', 'application': '应用题' }; return names[type] || type }

const loadQuizzes = async () => {
  loadingQuizzes.value = true
  try { const res = await listQuizzes(props.lessonId); quizzes.value = res.data?.quizzes || [] } 
  catch (e) { ElMessage.error('加载测验题失败') } finally { loadingQuizzes.value = false }
}

const generateQuiz = async () => {
  generating.value = true
  try { const res = await generateQuizAPI(props.lessonId, props.knowledgeDocIds); quizzes.value = res.data?.quizzes || []; ElMessage.success('测验题生成成功') } 
  catch (e) { ElMessage.error('生成失败，请重试') } finally { generating.value = false }
}

const addQuizManually = () => { editingQuiz.value = null; quizForm.questionType = 'single_choice'; quizForm.questionText = ''; quizForm.options = ['', '', '', '']; quizForm.correctAnswer = ''; quizForm.explanation = ''; quizForm.difficulty = 'medium'; quizForm.points = 5; showQuizDialog.value = true }

const editQuiz = (quiz) => { editingQuiz.value = quiz; quizForm.questionType = quiz.questionType; quizForm.questionText = quiz.questionText; quizForm.options = quiz.options || []; quizForm.correctAnswer = quiz.correctAnswer; quizForm.explanation = quiz.explanation; quizForm.difficulty = quiz.difficulty; quizForm.points = quiz.points; showQuizDialog.value = true }

const saveQuiz = async () => {
  if (!quizForm.questionText.trim()) return ElMessage.warning('请输入题目内容')
  if (!quizForm.correctAnswer.trim()) return ElMessage.warning('请输入正确答案')
  try {
    if (editingQuiz.value) {
      await updateQuiz(editingQuiz.value.id, { questionType: quizForm.questionType, questionText: quizForm.questionText, options: quizForm.options.filter(o => o.trim()), correctAnswer: quizForm.correctAnswer, explanation: quizForm.explanation, difficulty: quizForm.difficulty, points: quizForm.points })
      ElMessage.success('题目更新成功')
    } else {
      await addQuiz({ lessonId: props.lessonId, questionType: quizForm.questionType, questionText: quizForm.questionText, options: quizForm.options.filter(o => o.trim()), correctAnswer: quizForm.correctAnswer, explanation: quizForm.explanation, difficulty: quizForm.difficulty, points: quizForm.points })
      ElMessage.success('题目添加成功')
    }
    showQuizDialog.value = false; await loadQuizzes()
  } catch (e) { ElMessage.error('保存失败，请重试') }
}

const deleteQuiz = (quizId) => {
  ElMessageBox.confirm('确定要删除此题目吗？', '提示', { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' }).then(async () => {
    try { await deleteQuizAPI(quizId); ElMessage.success('题目已删除'); await loadQuizzes() } catch (e) { ElMessage.error('删除失败') }
  }).catch(() => {})
}

const exportWord = async () => {
  try {
    const res = await exportQuizWord(props.lessonId); const url = window.URL.createObjectURL(res.data)
    const link = document.createElement('a'); link.href = url; link.setAttribute('download', `测验题.docx`)
    document.body.appendChild(link); link.click(); document.body.removeChild(link); window.URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
  } catch (e) { ElMessage.error('导出失败，请重试') }
}

onMounted(() => { loadQuizzes() })
</script>

<style scoped>
.quiz-management { padding: 0; background: transparent; height: 100%; overflow-y: auto; }
.quiz-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; flex-wrap: wrap; gap: 12px; }
.quiz-header h2 { margin: 0; display: flex; align-items: center; gap: 10px; color: #1442D3; font-size: 20px; font-weight: bold; }
.header-actions { display: flex; gap: 10px; flex-wrap: wrap; }
.plain-action-btn { border-color: #D2E6FE; color: #1442D3; font-weight: bold; }
.plain-action-btn:hover { background: #D2E6FE; color: #307AE3; border-color: #307AE3; }

.glass-panel { background: rgba(255, 255, 255, 0.7); backdrop-filter: blur(10px); border-radius: 12px; padding: 20px; border: 1px solid #D2E6FE; }
.quiz-list { display: flex; flex-direction: column; gap: 16px; }
.quiz-card { background: #FFFFFF; border: 1px solid #D2E6FE; border-radius: 12px; padding: 20px; box-shadow: 0 4px 12px rgba(48, 122, 227, 0.05); transition: all 0.3s; }
.quiz-card:hover { transform: translateY(-2px); box-shadow: 0 8px 24px rgba(48, 122, 227, 0.1); border-color: #307AE3; }

.quiz-card-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 16px; padding-bottom: 16px; border-bottom: 1px dashed #D2E6FE; gap: 8px; }
.quiz-info { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; flex: 1; }
.quiz-number { font-weight: bold; color: #1442D3; white-space: nowrap; font-size: 15px;}
.quiz-type { font-size: 12px; padding: 4px 12px; border-radius: 6px; font-weight: bold; white-space: nowrap; }

/* 完美匹配四色的标签分类 */
.type-single_choice { background: #D2E6FE; color: #307AE3; }
.type-multiple_choice { background: rgba(172, 177, 236, 0.3); color: #1442D3; }
.type-true_false { background: rgba(48, 122, 227, 0.15); color: #307AE3; }
.type-calculation { background: rgba(20, 66, 211, 0.1); color: #1442D3; }
.type-application { background: rgba(172, 177, 236, 0.4); color: #1442D3; }

.source-tag { font-size: 11px; padding: 3px 10px; border-radius: 4px; white-space: nowrap; font-weight: bold;}
.ai-tag { background: #D2E6FE; color: #307AE3; border: 1px solid #307AE3; }
.manual-tag { background: #FFFFFF; color: #ACB1EC; border: 1px solid #ACB1EC; }
.quiz-actions { display: flex; gap: 10px; flex-shrink: 0; }

.quiz-card-content { display: flex; flex-direction: column; gap: 10px; }
.quiz-card-content p { margin: 0; font-size: 14px; line-height: 1.7; word-break: break-word; color: #333; }
.question-text { color: #1442D3; }
.options-section { margin: 8px 0; background: rgba(210, 230, 254, 0.2); padding: 12px; border-radius: 8px; }
.options-section ul { margin: 8px 0 0 20px; padding: 0; }
.options-section li { margin: 6px 0; color: #307AE3; font-weight: 500;}
.answer-text { color: #307AE3; font-weight: bold; margin-top: 10px;}
.answer-long { display: block; margin-top: 6px; white-space: pre-wrap; line-height: 1.7; font-weight: 500; color: #1442D3; word-break: break-word; }
.explanation-text { color: #1442D3; background: #D2E6FE; padding: 12px 16px; border-radius: 8px; word-break: break-word; margin-top: 8px; font-size: 13px !important;}

.options-input { display: flex; flex-direction: column; gap: 10px; }
.option-item { display: flex; gap: 10px; align-items: center; }

/* 弹窗及输入框高级样式 */
:deep(.glass-dialog .el-dialog) { background: rgba(255,255,255,0.95); backdrop-filter: blur(10px); border-radius: 16px; border: 1px solid #D2E6FE; box-shadow: 0 16px 40px rgba(48, 122, 227, 0.15); }
:deep(.glass-input .el-input__wrapper), :deep(.glass-input .el-textarea__inner) { background: rgba(210, 230, 254, 0.3) !important; border-radius: 8px !important; box-shadow: 0 0 0 1px #D2E6FE inset !important; transition: all 0.3s; }
:deep(.glass-input .el-input__wrapper.is-focus), :deep(.glass-input .el-textarea__inner:focus) { box-shadow: 0 0 0 2px #307AE3 inset !important; background: #FFFFFF !important; }

.glass-btn { background: #FFFFFF !important; border: 1px solid #D2E6FE !important; color: #1442D3 !important; border-radius: 10px; font-weight: bold; transition: all 0.3s; }
.glass-btn:hover { background: #D2E6FE !important; color: #307AE3 !important; border-color: #307AE3 !important; }
.glass-btn-primary { background: linear-gradient(135deg, #307AE3 0%, #1442D3 100%) !important; border: none !important; border-radius: 10px; font-weight: bold; transition: all 0.3s; }
.glass-btn-primary:hover { transform: translateY(-2px); box-shadow: 0 8px 24px rgba(48, 122, 227, 0.3) !important; }

@media (max-width: 768px) {
  .quiz-management { padding: 12px; }
  .quiz-header { 
    flex-direction: column; 
    align-items: stretch; 
    gap: 16px;
    margin-bottom: 16px;
  }
  .quiz-header h2 { 
    font-size: 18px;
    margin-bottom: 8px;
  }
  .header-actions { 
    width: 100%; 
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
  }
  .header-actions .el-button { 
    width: 100%;
    font-size: 13px;
    padding: 8px 12px !important;
    height: auto;
    white-space: normal;
    word-break: break-word;
  }
  .header-actions .el-icon { font-size: 16px; }
  
  .glass-panel { padding: 16px 12px; border-radius: 12px; }
  .quiz-list { gap: 12px; }
  
  .quiz-card { 
    padding: 16px 12px;
    border-radius: 10px;
  }
  .quiz-card-header { 
    flex-direction: column; 
    gap: 12px;
    padding-bottom: 12px;
    margin-bottom: 12px;
  }
  .quiz-info { 
    flex-wrap: wrap;
    gap: 8px;
  }
  .quiz-number { 
    font-size: 14px;
    white-space: nowrap;
  }
  .quiz-type { 
    font-size: 11px;
    padding: 3px 8px;
  }
  .source-tag { 
    font-size: 10px;
    padding: 2px 8px;
  }
  .quiz-actions { 
    align-self: flex-start;
    width: 100%;
    display: flex;
    gap: 8px;
  }
  .quiz-actions .el-button { 
    font-size: 12px;
    padding: 4px 8px !important;
    flex: 1;
  }
  
  .quiz-card-content { gap: 8px; }
  .quiz-card-content p { 
    font-size: 13px;
    line-height: 1.6;
    margin: 0;
  }
  .question-text { font-size: 13px; }
  .options-section { 
    margin: 6px 0;
    padding: 10px;
    font-size: 12px;
  }
  .options-section ul { margin: 6px 0 0 16px; }
  .options-section li { 
    margin: 4px 0;
    font-size: 12px;
  }
  .answer-text { 
    font-size: 12px;
    margin-top: 8px;
  }
  .answer-long { 
    font-size: 12px;
    margin-top: 4px;
  }
  .explanation-text { 
    font-size: 12px;
    padding: 10px 12px;
    margin-top: 6px;
  }
  
  :deep(.glass-dialog .el-dialog) { 
    width: 95% !important;
    border-radius: 12px;
  }
  :deep(.glass-dialog .el-dialog__body) { padding: 16px; }
  :deep(.glass-dialog .el-form-item) { margin-bottom: 16px; }
  :deep(.glass-dialog .el-form-item__label) { 
    font-size: 13px;
    width: 70px !important;
  }
  
  .options-input { gap: 8px; }
  .option-item { 
    gap: 8px;
    flex-wrap: wrap;
  }
  .option-item .el-input { flex: 1; min-width: 150px; }
  .option-item .el-button { font-size: 12px; }
}
</style>