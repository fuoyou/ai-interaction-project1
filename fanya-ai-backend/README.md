# 超星AI互动智课服务系统 - 后端API

基于泛雅平台的AI互动智课生成与实时问答系统，符合开放API设计规范。

## 项目结构

```
fanya-ai-backend/
├── app.py                  # 主应用入口
├── config.py              # 配置文件
├── extensions.py          # 扩展初始化
├── routes.py              # 路由注册
├── recreate_db.py         # 数据库重建脚本
├── requirements.txt       # 依赖包
├── .env                   # 环境变量
├── models/                # 数据模型
│   ├── user.py           # 用户模型
│   ├── lesson.py         # 智课课件模型
│   ├── qa.py             # 问答模型
│   └── progress.py       # 学习进度模型
├── controllers/           # 控制器
│   ├── user_controller.py      # 用户接口
│   ├── lesson_controller.py    # 智课生成接口
│   ├── qa_controller.py        # 问答交互接口
│   ├── progress_controller.py  # 进度追踪接口
│   └── avatar_controller.py    # 数字人接口
└── utils/                 # 工具类
    ├── ai_utils.py       # AI生成工具
    ├── tts_utils.py      # 语音合成工具
    ├── file_utils.py     # 文件处理工具
    ├── api_utils.py      # API工具（签名验证等）
    └── response_utils.py # 响应格式工具
```

## 核心功能

### 1. 智课智能生成模块
- **课件上传与解析** (`POST /api/v1/lesson/parse`)
  - 支持PDF、PPT格式
  - 自动提取知识点结构
  - 异步处理，返回任务ID

- **智课脚本生成** (`POST /api/v1/lesson/generateScript`)
  - 基于AI生成结构化讲授脚本
  - 支持多种教学风格（标准/详细/简洁）
  - 可自定义开场白

- **语音合成** (`POST /api/v1/lesson/generateAudio`)
  - 将脚本转换为语音
  - 支持分章节音频
  - 使用Edge TTS技术

### 2. 多模态实时问答模块
- **问答交互** (`POST /api/v1/qa/interact`)
  - 支持文字/语音提问
  - 结合课程上下文生成精准解答
  - 支持多轮对话记忆
  - 自动评估理解程度

- **语音识别** (`POST /api/v1/qa/voiceToText`)
  - 语音转文字

### 3. 学习进度智能适配模块
- **进度追踪** (`POST /api/v1/progress/track`)
  - 记录学习进度
  - 智能推荐下一章节

- **节奏调整** (`POST /api/v1/progress/adjust`)
  - 基于理解程度调整讲授节奏
  - 支持补充讲解/加速/正常三种模式

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env`，配置以下参数：

```env
# 数据库配置
DATABASE_URL=mysql+pymysql://root:password@localhost:3306/ai_course_db

# JWT密钥
SECRET_KEY=your-secret-key
JWT_SECRET_KEY=your-jwt-secret-key

# AI服务配置
AI_PROVIDER=zhipu
ZHIPU_API_KEY=your-zhipu-api-key

# 上传目录
UPLOAD_FOLDER=uploads
```

### 3. 初始化数据库

```bash
python recreate_db.py
```

这将创建所有必要的数据库表，并生成测试账号：
- 教师账号: `teacher` / `123456`
- 学生账号: `student` / `123456`

### 4. 启动服务

```bash
python app.py
```

服务将在 `http://0.0.0.0:8989` 启动

## API文档

### 通用规范

#### 请求格式
- 协议：HTTP/HTTPS
- 数据格式：JSON (UTF-8)
- 认证方式：JWT Token

#### 响应格式
```json
{
  "code": 200,
  "msg": "操作成功",
  "data": {},
  "requestId": "req20240520001"
}
```

#### 状态码
- `200`: 成功
- `400`: 参数错误
- `401`: 未授权
- `403`: 签名验证失败
- `404`: 资源不存在
- `500`: 服务器错误

### 核心接口示例

#### 1. 用户登录
```bash
POST /api/user/login
Content-Type: application/json

{
  "username": "teacher",
  "password": "123456",
  "role": "teacher"
}
```

#### 2. 课件上传与解析
```bash
POST /api/v1/lesson/parse
Authorization: Bearer <token>
Content-Type: multipart/form-data

file: <课件文件>
schoolId: sch10001
courseId: cou30001
```

#### 3. 生成智课脚本
```bash
POST /api/v1/lesson/generateScript
Authorization: Bearer <token>
Content-Type: application/json

{
  "parseId": "parse20240520001",
  "teachingStyle": "standard",
  "speechSpeed": "normal",
  "customOpening": "同学们好，今天我们学习..."
}
```

#### 4. 问答交互
```bash
POST /api/v1/qa/interact
Authorization: Bearer <token>
Content-Type: application/json

{
  "schoolId": "sch10001",
  "courseId": "cou30001",
  "lessonId": "parse20240520001",
  "sessionId": "ses20240520001",
  "questionType": "text",
  "questionContent": "什么是平面假设？",
  "currentSectionId": "sec002",
  "historyQa": []
}
```

## 技术栈

- **Web框架**: Flask 2.3.0
- **数据库**: MySQL + SQLAlchemy
- **认证**: Flask-JWT-Extended
- **AI服务**: 智谱AI (GLM-4-Flash)
- **语音合成**: Edge TTS
- **文件处理**: PyPDF2, python-pptx

## 开发说明

### 签名验证
为了开发方便，可以在请求头中添加 `X-Skip-Sign` 跳过签名验证：

```bash
curl -H "X-Skip-Sign: true" -H "Authorization: Bearer <token>" ...
```

### 数据库迁移
如果修改了模型，重新运行：
```bash
python recreate_db.py
```

### 日志查看
应用日志会输出到控制台，包括：
- 课件解析进度
- AI生成状态
- TTS合成结果
- 错误信息

## 注意事项

1. **AI服务配置**: 需要配置有效的智谱AI API Key
2. **数据库**: 确保MySQL服务已启动
3. **文件上传**: 默认最大100MB，可在config.py中调整
4. **异步任务**: 课件解析、脚本生成、音频合成均为异步处理
5. **跨域**: 已配置CORS，支持前端跨域访问

## 许可证

MIT License
