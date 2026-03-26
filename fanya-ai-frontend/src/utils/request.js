import axios from 'axios'
import { ElMessage } from 'element-plus'
import md5 from 'js-md5'

const service = axios.create({
  baseURL: '/api', 
  timeout: 300000 
})

// 签名密钥 (与后端一致)
const STATIC_KEY = "FanyaAISecretKey2026"

function generateSignature(params) {
  // 1. 过滤空值
  const validKeys = Object.keys(params).filter(k => params[k] !== null && params[k] !== undefined && params[k] !== '')
  // 2. 排序
  validKeys.sort()
  // 3. 拼接
  let str = ''
  validKeys.forEach(k => str += String(params[k]))
  // 4. 加盐 + 时间戳
  str += STATIC_KEY + (params.timestamp || '')
  return md5(str).toUpperCase()
}

service.interceptors.request.use(
  config => {
    const token = localStorage.getItem('token')
    if (token && token !== 'undefined') {
      config.headers['Authorization'] = token.startsWith('Bearer ') ? token : `Bearer ${token}`
    }

    // --- 添加签名逻辑 ---
    const timestamp = Date.now()
    let signParams = { timestamp }
    
    // GET 请求签名
    if (config.method === 'get') {
        if (!config.params) config.params = {}
        Object.assign(signParams, config.params)
        config.params.timestamp = timestamp
        config.params.enc = generateSignature(signParams)
    } 
    // POST/PUT/DELETE 请求签名
    else if (config.method === 'post' || config.method === 'put' || config.method === 'delete') {
        if (config.data instanceof FormData) {
           // FormData 跳过签名，防止破坏 boundary
           config.headers['X-Skip-Sign'] = '1' 
        } else {
           if (!config.data) config.data = {}
           // 复制 data 用于计算签名
           Object.assign(signParams, config.data)
           // 将 timestamp 和 enc 注入到请求体中
           config.data.timestamp = timestamp
           config.data.enc = generateSignature(signParams)
        }
    }

    return config
  },
  error => Promise.reject(error)
)

service.interceptors.response.use(
  response => {
    // 处理 blob 响应（文件下载）
    if (response.data instanceof Blob) {
      return { data: response.data }
    }
    
    const res = response.data
    // 兼容标准 HTTP 200 但业务 code 非 200 的情况
    // 注意：后端现在返回的 code 是 数字 200
    if (res.code !== 200 && res.code !== '200') {
      ElMessage.error(res.msg || '系统错误')
      return Promise.reject(new Error(res.msg || 'Error'))
    }
    // 【关键修复】
    // 直接返回 res 对象 (包含 code, msg, data)，
    // 因为你的组件里写的是 const res = await ...; const list = res.data;
    return res
  },
  error => {
    console.error('API Error:', error)
    if (error.response?.status === 401) {
        localStorage.removeItem('token')
        localStorage.removeItem('userInfo')
        window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export default service