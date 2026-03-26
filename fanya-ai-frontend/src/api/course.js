/**
 * 课程相关API - 兼容旧接口
 * 新接口请使用 lesson.js, qa.js, progress.js
 */
import { 
  uploadCourse as uploadLesson,
  getCourseDetail as getLessonDetail,
  listMyCourses as listLessons,
  listTeacherCourses as listTeacherLessons,
  updateCourseScript as updateScript,
  polishPage as polish,
  generateSingleTTS as singleTTS
} from './lesson'

import { chatWithAI as chat } from './qa'

// 导出兼容接口
export const uploadCourse = uploadLesson
export const getCourseDetail = getLessonDetail
export const listMyCourses = listLessons
export const listMyStudentCourses = listLessons
export const listTeacherCourses = listTeacherLessons
export const updateCourseScript = updateScript
export const polishPage = polish
export const chatWithAI = chat
export const generateSingleTTS = singleTTS
