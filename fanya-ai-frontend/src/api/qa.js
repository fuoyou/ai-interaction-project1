import request from '@/utils/request'
import md5 from 'js-md5'

// ==================== 2.2 多模态实时问答模块 ====================

/**
 * 2.2.1 问答交互接口
 * 接口地址：POST /api/v1/qa/interact
 */
export function qaInteract(data) {
  return request({
    url: '/v1/qa/interact',
    method: 'post',
    data: {
      schoolId: data.schoolId || 'sch10001',
      courseId: data.courseId || 'default',
      lessonId: data.lessonId || data.courseId, // 兼容参数
      sessionId: data.sessionId || '', // 首次为空，后续传入
      questionType: data.questionType || 'text',
      questionContent: data.questionContent || data.question, // 兼容参数
      currentSectionId: data.currentSectionId || data.pageNum || 'sec001',
      historyQa: data.historyQa || [],
      currentPageContent: data.currentPageContent || '',
      useCourseKnowledgeBase: data.useCourseKnowledgeBase ? true : false,
      categoryId: data.categoryId || ''
    }
  })
}

const STATIC_KEY = 'FanyaAISecretKey2026'

function generateSignature(params) {
  const validKeys = Object.keys(params).filter(
    (k) => params[k] !== null && params[k] !== undefined && params[k] !== '' && k !== 'enc'
  )
  validKeys.sort()
  let str = ''
  validKeys.forEach((k) => {
    str += String(params[k])
  })
  str += STATIC_KEY + String(params.timestamp || '')
  return md5(str).toUpperCase()
}

/**
 * SSE 流式问答接口
 * @param {Object} data
 * @param {Object} handlers { onMeta, onDelta, onDone, onError }
 * @returns {Promise<void>}
 */
export async function qaInteractStream(data, handlers = {}) {
  const timestamp = Date.now()
  const payload = {
    schoolId: data.schoolId || 'sch10001',
    courseId: data.courseId || 'default',
    lessonId: data.lessonId || data.courseId,
    sessionId: data.sessionId || '',
    questionType: data.questionType || 'text',
    questionContent: data.questionContent || data.question,
    currentSectionId: data.currentSectionId || data.pageNum || 'sec001',
    historyQa: data.historyQa || [],
    currentPageContent: data.currentPageContent || '',
    useCourseKnowledgeBase: data.useCourseKnowledgeBase ? true : false,
    categoryId: data.categoryId || '',
    timestamp
  }
  payload.enc = generateSignature(payload)

  const token = localStorage.getItem('token')
  const headers = {
    'Content-Type': 'application/json'
  }
  if (token && token !== 'undefined') {
    headers.Authorization = token.startsWith('Bearer ') ? token : `Bearer ${token}`
  }

  const response = await fetch('/api/v1/qa/interact/stream', {
    method: 'POST',
    headers,
    body: JSON.stringify(payload)
  })

  if (!response.ok || !response.body) {
    throw new Error(`流式接口请求失败: ${response.status}`)
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder('utf-8')
  let buffer = ''

  const parseEvent = (rawBlock) => {
    const lines = rawBlock.split('\n')
    let eventName = 'message'
    let dataText = ''
    for (const line of lines) {
      if (line.startsWith('event:')) {
        eventName = line.slice(6).trim()
      } else if (line.startsWith('data:')) {
        dataText += line.slice(5).trim()
      }
    }
    if (!dataText) return
    let payloadObj = {}
    try {
      payloadObj = JSON.parse(dataText)
    } catch (e) {
      payloadObj = { text: dataText }
    }

    if (eventName === 'meta' && handlers.onMeta) handlers.onMeta(payloadObj)
    if (eventName === 'delta' && handlers.onDelta) handlers.onDelta(payloadObj)
    if (eventName === 'done' && handlers.onDone) handlers.onDone(payloadObj)
    if (eventName === 'error' && handlers.onError) handlers.onError(payloadObj)
  }

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, '\n')

    let splitIndex = buffer.indexOf('\n\n')
    while (splitIndex !== -1) {
      const block = buffer.slice(0, splitIndex)
      buffer = buffer.slice(splitIndex + 2)
      if (block.trim()) parseEvent(block)
      splitIndex = buffer.indexOf('\n\n')
    }
  }
}

/**
 * 2.2.2 语音提问识别接口
 * 接口地址：POST /api/v1/qa/voiceToText
 */
export function voiceToText(voiceUrl, options = {}) {
  return request({
    url: '/v1/qa/voiceToText',
    method: 'post',
    data: {
      voiceUrl: voiceUrl,
      voiceDuration: options.voiceDuration || 0,
      language: options.language || 'zh-CN'
    }
  })
}

/**
 * 获取问答历史
 * 接口地址：GET /api/v1/qa/history/{sessionId}
 */
export function getQAHistory(sessionId) {
  return request({
    url: `/v1/qa/history/${sessionId}`,
    method: 'get'
  })
}

/**
 * 课件配图 + 上下文 → 通义千问视觉（需后端 DASHSCOPE_API_KEY）
 * 不使用 enc 签名（body 含大图）
 */
export async function qaVisionExplain(payload) {
  const token = localStorage.getItem('token')
  const headers = { 'Content-Type': 'application/json' }
  if (token && token !== 'undefined') {
    headers.Authorization = token.startsWith('Bearer ') ? token : `Bearer ${token}`
  }
  const res = await fetch('/api/v1/qa/vision', {
    method: 'POST',
    headers,
    body: JSON.stringify({
      imageBase64: payload.imageBase64,
      questionContent: payload.question || '',
      contextText: payload.contextText || '',
      lessonId: payload.lessonId,
      courseId: payload.courseId,
      pageNum: payload.pageNum,
      currentSectionId: payload.currentSectionId,
      fileName: payload.fileName || ''
    })
  })
  const raw = await res.text().catch(() => '')
  let json = {}
  if (raw) {
    try {
      json = JSON.parse(raw)
    } catch {
      json = {}
    }
  }
  if (json.code === 200 || json.code === '200') {
    return json
  }
  const hint = json.msg || (res.ok ? '' : `HTTP ${res.status}`)
  throw new Error(hint || '视觉问答失败')
}

// ==================== 兼容旧接口 ====================

/**
 * 实时问答（兼容旧接口）
 */
export function chatWithAI(data) {
  return qaInteract({
    lessonId: data.courseId,
    questionContent: data.question,
    currentSectionId: `sec${data.pageNum || 1}`,
    historyQa: data.historyQa || [],
    currentPageContent: data.currentPageContent || '',
    useCourseKnowledgeBase: data.useCourseKnowledgeBase ? true : false,
    categoryId: data.categoryId || ''
  })
}
