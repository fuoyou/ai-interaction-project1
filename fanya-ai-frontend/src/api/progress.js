import request from '@/utils/request'

// ==================== 2.3 学习进度智能适配模块 ====================

/**
 * 2.3.1 学习进度追踪接口
 * 接口地址：POST /api/v1/progress/track
 */
export function trackProgress(data) {
  return request({
    url: '/v1/progress/track',
    method: 'post',
    data: {
      schoolId: data.schoolId || 'sch10001',
      courseId: data.courseId || 'default',
      lessonId: data.lessonId || data.courseId,
      currentSectionId: data.currentSectionId || `sec${data.pageNum || 1}`,
      progressPercent: data.progressPercent || 0,
      lastOperateTime: data.lastOperateTime || new Date().toISOString().slice(0, 19).replace('T', ' '),
      qaRecordId: data.qaRecordId || ''
    }
  })
}

/**
 * 2.3.2 学习节奏调整接口
 * 接口地址：POST /api/v1/progress/adjust
 */
export function adjustRhythm(data) {
  return request({
    url: '/v1/progress/adjust',
    method: 'post',
    data: {
      lessonId: data.lessonId || data.courseId,
      currentSectionId: data.currentSectionId || `sec${data.pageNum || 1}`,
      understandingLevel: data.understandingLevel || 'partial',
      qaRecordId: data.qaRecordId || ''
    }
  })
}

/**
 * 获取学习进度详情
 * 接口地址：GET /api/v1/progress/detail/{lessonId}
 */
export function getProgressDetail(lessonId) {
  return request({
    url: `/v1/progress/detail/${lessonId}`,
    method: 'get'
  })
}

/**
 * 获取节奏调整历史
 * 接口地址：GET /api/v1/progress/adjustments/{lessonId}
 */
export function getAdjustments(lessonId) {
  return request({
    url: `/v1/progress/adjustments/${lessonId}`,
    method: 'get'
  })
}

// ==================== 兼容旧接口 ====================

/**
 * 获取学生进度（兼容旧接口）
 */
export function getStudentProgress(courseId) {
  return getProgressDetail(courseId)
}

/**
 * 获取学习历史（真实的问答历史记录）
 */
export function getLearningHistory(courseId) {
  return request({
    url: `/rhythm/history/${courseId}`,
    method: 'get'
  })
}

/**
 * 智能诊断学习节奏
 * 接口地址：GET /api/v1/progress/diagnose/{lessonId}
 * @param {string|number} lessonId - 课件ID
 * @param {boolean} forceRefresh - 是否强制刷新（不走缓存）
 */
export function diagnoseRhythm(lessonId, forceRefresh = false) {
  return request({
    url: `/v1/progress/diagnose/${lessonId}`,
    method: 'get',
    params: {
      forceRefresh: forceRefresh ? 1 : 0
    }
  })
}
