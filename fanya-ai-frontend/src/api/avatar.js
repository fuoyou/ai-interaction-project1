import request from '@/utils/request'

/**
 * 数字人语音合成接口
 * 符合超星AI互动智课系统API规范
 * 
 * @param {Object} data - 请求参数
 * @param {String} data.script - 讲授脚本内容（必填）
 * @returns {Promise} 返回格式：
 * {
 *   code: 200,           // 状态码（数字类型）
 *   msg: '操作成功',     // 状态描述
 *   data: {
 *     audioId: 'xxx',    // 音频任务ID
 *     result_url: '/static/digital_humans/xxx.mp4',  // 视频相对路径
 *     videoUrl: '/static/digital_humans/xxx.mp4'     // 视频URL
 *   },
 *   requestId: 'req20240520001'  // 请求唯一标识
 * }
 */
export function createAvatarTalk(data) {
  return request({
    url: '/avatar/talk',
    method: 'post',
    data,
  })
}