/**
 * API统一导出文件
 * 符合超星AI互动智课服务系统开放API设计规范
 */

// 用户相关
export * from './user'

// 智课生成模块（2.1）
export * from './lesson'

// 问答交互模块（2.2）
export * from './qa'

// 学习进度模块（2.3）
export * from './progress'

// 测验模块
export * from './quiz'

// 数字人模块
export * from './avatar'

// 兼容旧接口（向后兼容）
export * from './course'
export * from './rhythm'
