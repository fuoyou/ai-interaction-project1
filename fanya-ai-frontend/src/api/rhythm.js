/**
 * 节奏相关API - 兼容旧接口
 * 新接口请使用 progress.js
 */
import {
  diagnoseRhythm as diagnose,
  getStudentProgress as getProgress,
  getLearningHistory as getHistory
} from './progress'

// 导出兼容接口
export const diagnoseRhythm = diagnose
export const getStudentProgress = getProgress
export const getLearningHistory = getHistory