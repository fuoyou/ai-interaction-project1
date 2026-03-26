import request from '@/utils/request'

// 生成测验题 (支持结合知识库生成)
export const generateQuiz = (lessonId, knowledgeDocIds = []) => {
  return request({
    url: '/v1/quiz/generate',
    method: 'post',
    data: { lessonId, knowledgeDocIds }
  })
}

// 获取测验题列表
export const listQuizzes = (lessonId) => {
  return request({
    url: `/v1/quiz/list/${lessonId}`,
    method: 'get'
  })
}

// 新增题目
export const addQuiz = (data) => {
  return request({
    url: '/v1/quiz/add',
    method: 'post',
    data
  })
}

// 编辑题目
export const updateQuiz = (quizId, data) => {
  return request({
    url: `/v1/quiz/update/${quizId}`,
    method: 'put',
    data
  })
}

// 删除题目
export const deleteQuiz = (quizId) => {
  return request({
    url: `/v1/quiz/delete/${quizId}`,
    method: 'delete'
  })
}

// 提交答案
export const submitAnswer = (data) => {
  return request({
    url: '/v1/quiz/submit-answer',
    method: 'post',
    data
  })
}

// 获取学生答题记录（最近一次测验）
export const getStudentAnswers = (lessonId) => {
  return request({
    url: `/v1/quiz/student-answers/${lessonId}`,
    method: 'get'
  })
}

// 获取学生测验历史列表
export const getQuizAttempts = (lessonId) => {
  return request({
    url: `/v1/quiz/attempts/${lessonId}`,
    method: 'get'
  })
}

// 导出Word
export const exportQuizWord = (lessonId) => {
  return request({
    url: `/v1/quiz/export-word/${lessonId}`,
    method: 'get',
    responseType: 'blob'
  })
}

// 保存智能插旗考点答题记录
export const saveCheckpointAnswer = (data) => {
  return request({
    url: '/v1/quiz/checkpoint-answer',
    method: 'post',
    data
  })
}

// 获取智能插旗考点答题记录
export const getCheckpointAnswers = (lessonId) => {
  return request({
    url: `/v1/quiz/checkpoint-answers/${lessonId}`,
    method: 'get'
  })
}