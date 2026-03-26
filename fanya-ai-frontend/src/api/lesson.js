import request from '@/utils/request'

// ==================== 2.1 智课智能生成模块 ====================

/**
 * 2.1.1 课件上传与解析接口
 * 接口地址：POST /api/v1/lesson/parse
 */
export function uploadCourse(file, schoolId = 'sch10001', courseId = 'default') {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('schoolId', schoolId)
  formData.append('courseId', courseId)
  
  return request({
    url: '/v1/lesson/parse',
    method: 'post',
    data: formData
  })
}

/**
 * 上传课件到指定分类
 * courseId 作为分类标识传给后端
 */
export function uploadCourseToCategory(file, categoryId, schoolId = 'sch10001') {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('schoolId', schoolId)
  formData.append('courseId', categoryId)
  
  return request({
    url: '/v1/lesson/parse',
    method: 'post',
    data: formData
  })
}

/**
 * 2.1.2 智课脚本生成接口
 * 接口地址：POST /api/v1/lesson/generateScript
 */
export function generateScript(parseId, options = {}) {
  return request({
    url: '/v1/lesson/generateScript',
    method: 'post',
    data: {
      parseId: parseId,
      teachingStyle: options.teachingStyle || 'standard',
      speechSpeed: options.speechSpeed || 'normal',
      customOpening: options.customOpening || '',
      scripts: options.scripts // 如果传了scripts，表示保存编辑后的脚本
    }
  })
}

/**
 * 2.1.3 语音合成接口
 * 接口地址：POST /api/v1/lesson/generateAudio
 */
export function generateAudio(scriptId, options = {}) {
  return request({
    url: '/v1/lesson/generateAudio',
    method: 'post',
    data: {
      scriptId: scriptId,
      voiceType: options.voiceType || 'female_standard',
      audioFormat: options.audioFormat || 'mp3',
      sectionIds: options.sectionIds || []
    }
  })
}

/**
 * 获取课件详情
 * 接口地址：GET /api/v1/lesson/detail/{parseId}
 */
export function getCourseDetail(parseId) {
  return request({
    url: `/v1/lesson/detail/${parseId}`,
    method: 'get'
  })
}

/**
 * 获取教师课程列表
 * 接口地址：GET /api/v1/lesson/list
 */
export function listMyCourses() {
  return request({
    url: '/v1/lesson/list',
    method: 'get'
  })
}

/**
 * 获取学生课程列表（兼容旧接口）
 */
export function listMyStudentCourses() {
  return request({
    url: '/v1/lesson/list',
    method: 'get'
  })
}

/**
 * 获取老师上传的课件列表 (供学生查看)
 * 接口地址：GET /api/v1/lesson/teacher/list
 */
export function listTeacherCourses() {
  return request({
    url: '/v1/lesson/teacher/list',
    method: 'get'
  })
}

// ==================== 兼容旧接口 ====================

/**
 * 更新课程脚本（兼容旧接口，实际调用generateScript）
 */
export function updateCourseScript(courseId, scripts) {
  console.log('保存脚本:', courseId, scripts)
  return request({
    url: '/v1/lesson/generateScript',
    method: 'post',
    data: {
      parseId: courseId,
      scripts: scripts
    }
  })
}

/**
 * AI单页润色（映射到问答接口）
 */
export function polishPage(id, data) {
  const baseQuestion = data.question || `请帮我优化这段讲稿内容：\n${data.content}`
  return request({
    url: '/v1/qa/interact',
    method: 'post',
    data: {
      lessonId: id,
      questionType: 'text',
      questionContent: baseQuestion + '\n\n【重要】直接输出优化后的讲稿正文，不要输出任何前缀说明、标题、markdown格式符号（**、#等），不要输出"当然"、"以下是"、"好的"等开场白，只输出老师讲给学生的正文内容。',
      currentSectionId: data.pageNum.toString(),
      currentPageContent: data.content
    }
  })
}

/**
 * 单页TTS生成接口 - 实时生成语音
 */
export function generateSingleTTS(text) {
  return request({
    url: '/v1/lesson/tts/single',
    method: 'post',
    data: { text }
  })
}

/**
 * 获取课件思维导图
 * 接口地址：GET /api/v1/lesson/mindmap/{parseId}
 */
export function getMindmap(parseId) {
  return request({
    url: `/v1/lesson/mindmap/${parseId}`,
    method: 'get'
  })
}

/**
 * 获取课件知识图谱
 * 接口地址：GET /api/v1/lesson/knowledge-graph/{parseId}
 */
export function getKnowledgeGraph(parseId) {
  return request({
    url: `/v1/lesson/knowledge-graph/${parseId}`,
    method: 'get'
  })
}

/**
 * 生成课件测验题目
 * 接口地址：POST /api/v1/lesson/generate-quiz
 */
export function generateQuiz(courseId, options = {}) {
  return request({
    url: '/v1/lesson/generate-quiz',
    method: 'post',
    data: {
      courseId,
      questionCount: options.questionCount || 10,
      types: options.types || ['multiple_choice', 'fill_blank', 'true_false', 'short_answer']
    }
  })
}

// ==================== 分类模块 ====================

/**
 * 创建分类
 */
export function createCategory(name, description = '') {
  return request({
    url: '/v1/category/create',
    method: 'post',
    data: { name, description }
  })
}

/**
 * 获取分类列表
 */
export function listCategories() {
  return request({
    url: '/v1/category/list',
    method: 'get'
  })
}

/**
 * 获取所有分类（包括老师创建的）- 供学生端使用
 */
export function listAllCategories() {
  return request({
    url: '/v1/category/listAll',
    method: 'get'
  })
}

/**
 * 更新分类
 */
export function updateCategory(categoryId, name, description = '') {
  return request({
    url: `/v1/category/update/${categoryId}`,
    method: 'put',
    data: { name, description }
  })
}

/**
 * 删除分类
 */
export function deleteCategory(categoryId) {
  return request({
    url: `/v1/category/delete/${categoryId}`,
    method: 'delete'
  })
}

// ==================== 知识库模块 ====================

/**
 * 上传知识库资料
 */
export function uploadKnowledgeDoc(file, categoryId, name, description = '') {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('categoryId', categoryId)
  formData.append('name', name)
  formData.append('description', description)
  return request({
    url: '/v1/knowledge/upload',
    method: 'post',
    data: formData
  })
}

/**
 * 获取分类下的知识库列表
 */
export function listKnowledgeDocs(categoryId) {
  return request({
    url: `/v1/knowledge/list/${categoryId}`,
    method: 'get'
  })
}

/**
 * 删除知识库文档
 */
export function deleteKnowledgeDoc(docId) {
  return request({
    url: `/v1/knowledge/delete/${docId}`,
    method: 'delete'
  })
}

/**
 * 删除课件
 */
export function deleteCourseware(coursewareId) {
  return request({
    url: '/v1/lesson/delete',
    method: 'delete',
    data: { id: coursewareId }
  })
}

/**
 * 结合知识库重新生成讲稿（发起异步任务）
 */
export function regenerateScriptWithKnowledge(lessonId, knowledgeDocIds) {
  return request({
    url: '/v1/lesson/regenerateScriptWithKnowledge',
    method: 'post',
    data: { lessonId, knowledgeDocIds }
  })
}

/**
 * 轮询讲稿重新生成状态
 */
export function getRegenerateStatus(lessonId) {
  return request({
    url: `/v1/lesson/regenerateStatus/${lessonId}`,
    method: 'get'
  })
}