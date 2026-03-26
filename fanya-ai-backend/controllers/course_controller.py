from flask import Blueprint, request, jsonify, send_from_directory, current_app
from flask_jwt_extended import get_jwt_identity, jwt_required
from models.course import Course
from models.user import User
from extensions import db
import os
import uuid
import json
import threading
import time

# 引入工具类
from utils import tts_utils 
from utils.file_utils import extract_text_from_pdf, extract_text_from_ppt
from utils.ai_utils import AIGenerator
# 引入新加的 API 规范工具
from utils.api_utils import verify_signature, api_response

# 修改 Blueprint 名称以符合新规范逻辑，但保持变量名兼容
course_bp = Blueprint('lesson', __name__)

if not os.path.exists('uploads'):
    os.makedirs('uploads')

def _course_to_dict(course, include_scripts=True):
    """
    转字典，同时兼容文档格式和前端现有格式
    """
    # 基础数据
    ai_script, audio_script = [], []
    try:
        # 确保 ai_script 是 Python List 对象，而不是 JSON 字符串
        if course.ai_script:
            try: ai_script = json.loads(course.ai_script)
            except: 
                try: ai_script = eval(course.ai_script)
                except: ai_script = []
        
        if course.audio_script:
            try: audio_script = json.loads(course.audio_script)
            except:
                try: audio_script = eval(course.audio_script)
                except: audio_script = []
    except Exception as e:
        print(f"Data parsing error: {e}")

    data = {
        # --- 兼容现有前端的字段 ---
        'id': course.id,
        'courseName': course.course_name,
        # 只返回文件名，由前端拼接路径
        'fileUrl': course.file_url if course.file_url else '',
        'status': course.status,
        'createTime': course.create_time.strftime('%Y-%m-%d %H:%M:%S'),
        'updateTime': course.update_time.strftime('%Y-%m-%d %H:%M:%S'),
        # 这里必须是 List/Dict 对象，Flask 的 jsonify 会自动把它转成 JSON 数组
        'aiScript': ai_script,
        'audioScript': audio_script,
        
        # --- 符合文档规范的字段映射 ---
        'parseId': str(course.id),
        'fileInfo': {
            'fileName': course.course_name,
            'fileSize': 0, 
            'pageCount': len(ai_script) if ai_script else 0
        },
        'structurePreview': {
            'chapters': [{'chapterName': '自动解析章节', 'subChapters': []}]
        }
    }
    
    if hasattr(course, 'create_by'):
        data['createBy'] = course.create_by
        
    return data

# --- 2.1.1 课件上传与解析接口 (文档: /api/v1/lesson/parse) ---
# 原 /upload 接口改造
@course_bp.route('/parse', methods=['POST'])
@verify_signature
@jwt_required()
def parse_lesson():
    # 兼容文档参数 schoolId, userId (从 token 取), fileUrl (实际支持文件上传)
    current_user_id = get_jwt_identity()
    
    # 即使文档说 fileUrl 是参数，为了功能可用，我们依然优先处理文件上传
    if 'file' not in request.files: 
        return api_response(code=400, msg='请上传文件')
        
    file = request.files['file']
    if file.filename == '': 
        return api_response(code=400, msg='文件名不能为空')
    
    filename = str(uuid.uuid4()) + '.' + file.filename.split('.')[-1]
    file_path = os.path.join('uploads', filename)
    file.save(file_path)
    
    course = Course(
        course_name=file.filename,
        file_url=filename,
        file_type=file.filename.split('.')[-1],
        create_by=current_user_id,
        status=0
    )
    db.session.add(course)
    db.session.commit()
    
    app_obj = current_app._get_current_object()
    threading.Thread(target=process_course_file, args=(app_obj, course.id, file_path)).start()
    
    # 返回文档规定的格式，parseId 对应 courseId
    # 同时返回 id 以兼容前端
    return api_response(data={
        "parseId": course.id,
        "id": course.id, 
        "taskStatus": "processing"
    }, msg="课件上传成功，解析任务已提交")

# --- 2.1.2 智课脚本生成接口 (文档: /api/v1/lesson/generateScript) ---
# 原 update_course_script 改造，这里用于"更新/重新生成"脚本
@course_bp.route('/generateScript', methods=['POST'])
@verify_signature
@jwt_required()
def generate_script():
    # 文档参数: parseId (即 courseId), teachingStyle, etc.
    # 实际逻辑: 接收前端编辑后的脚本进行保存，并触发音频生成
    
    data = request.get_json()
    # 兼容处理：前端可能传 courseId 或 parseId
    course_id = data.get('parseId') or data.get('courseId')
    
    if not course_id:
        return api_response(code=400, msg="缺少 parseId (courseId)")
        
    course = Course.query.get(course_id)
    if not course:
        return api_response(code=404, msg='课程不存在')

    # 如果传了 content/scripts，说明是保存操作
    scripts = data.get('scripts') or data.get('content')
    if scripts:
        course.ai_script = json.dumps(scripts, ensure_ascii=False)
        course.status = 2 # 状态流转
        db.session.commit()
        
        # 触发音频生成
        app_obj = current_app._get_current_object()
        threading.Thread(target=generate_audio_for_course, args=(app_obj, course.id)).start()

    return api_response(data={
        "scriptId": f"script_{course.id}",
        "msg": "脚本已更新并触发语音合成"
    })

# --- 2.1.3 语音合成接口 (文档: /api/v1/lesson/generateAudio) ---
@course_bp.route('/generateAudio', methods=['POST'])
@verify_signature
@jwt_required()
def generate_audio_api():
    data = request.get_json()
    # 这里的 scriptId 格式假设为 script_{courseId}
    script_id = data.get('scriptId', '')
    try:
        course_id = int(script_id.split('_')[1])
    except:
        course_id = data.get('courseId')

    if not course_id:
        return api_response(code=400, msg="无效的 ID")

    # 手动触发生成
    app_obj = current_app._get_current_object()
    threading.Thread(target=generate_audio_for_course, args=(app_obj, course_id)).start()
    
    return api_response(msg="语音合成任务已提交")


# --- 逻辑处理函数 (保持之前修复的逻辑不变) ---
def process_course_file(app_obj, course_id, file_path=None):
    with app_obj.app_context():
        course = Course.query.get(course_id)
        if not course: return
        try:
            course.status = 1
            db.session.commit()
            
            if not file_path:
                file_path = os.path.join(app_obj.config['UPLOAD_FOLDER'], course.file_url)
            
            content_list = []
            if course.file_type == 'pdf':
                content_list = extract_text_from_pdf(file_path)
            elif course.file_type in ['ppt', 'pptx']:
                content_list = extract_text_from_ppt(file_path)
            
            content = '\n\n'.join(content_list).strip() if content_list else ''
            
            slides = []
            if not content:
                slides = [{'page': i + 1, 'content': f'无法解析内容，生成默认讲稿页 {i+1}'} for i in range(5)]
            else:
                ai_generator = AIGenerator(provider='zhipu')
                content_parts = content.split('\n\n')
                total_pages = min(6, len(content_parts))
                
                for i in range(total_pages):
                    part = content_parts[i]
                    prompt = f"请为以下课件内容生成一页讲稿(200字以内)：\n{part}"
                    try:
                        reply = ai_generator.generate_reply(prompt)
                        slides.append({'page': i + 1, 'content': reply})
                    except:
                        slides.append({'page': i + 1, 'content': '内容生成失败'})
            
            course.ai_script = json.dumps(slides, ensure_ascii=False)
            course.status = 2 
            db.session.commit()
            
            generate_audio_for_course(app_obj, course_id)
            
        except Exception as e:
            print(f"Process failed: {e}")
            course.status = 9
            db.session.commit()

def generate_audio_for_course(app_obj, course_id):
    with app_obj.app_context():
        course = Course.query.get(course_id)
        if not course: return
        try:
            print(f"Starting audio gen: {course_id}")
            slides = []
            if course.ai_script:
                try: slides = json.loads(course.ai_script)
                except: 
                    try: slides = eval(course.ai_script)
                    except: slides = []
            
            if not slides:
                course.status = 3
                db.session.commit()
                return

            audio_script = []
            for slide in slides:
                page = slide.get('page')
                content = slide.get('content', '')
                if page and content:
                    fname = f"course_{course_id}_p{page}_{uuid.uuid4().hex[:6]}.mp3"
                    try:
                        # 确保 tts_utils 已正确修复
                        saved_name = tts_utils.text_to_speech(content, fname)
                        audio_script.append({
                            'page': page,
                            'audioUrl': f'/api/v1/lesson/chat/tts/{saved_name}' # 注意这里路径也要改
                        })
                    except Exception as e:
                        print(f"TTS Error: {e}")
            
            course.audio_script = json.dumps(audio_script, ensure_ascii=False)
            course.status = 3
            db.session.commit()
            print("Audio gen done.")
            
        except Exception as e:
            print(f"Audio gen failed: {e}")
            course.status = 3
            db.session.commit()

# --- 辅助接口 (用于前端展示) ---

@course_bp.route('/detail/<int:course_id>', methods=['GET'])
@jwt_required()
def get_course_detail(course_id):
    course = Course.query.get(course_id)
    if not course: return api_response(code=404, msg='不存在')
    return api_response(data=_course_to_dict(course))

@course_bp.route('/teacher/list', methods=['GET'])
@jwt_required()
def get_teacher_courses():
    uid = get_jwt_identity()
    courses = Course.query.filter_by(create_by=uid).order_by(Course.create_time.desc()).all()
    return api_response(data=[_course_to_dict(c) for c in courses])

@course_bp.route('/student/list', methods=['GET'])
@jwt_required()
def get_student_courses():
    courses = Course.query.order_by(Course.create_time.desc()).all()
    return api_response(data=[_course_to_dict(c, False) for c in courses])

# 静态文件服务接口
@course_bp.route('/files/<filename>', methods=['GET'])
def get_file(filename):
    return send_from_directory('uploads', filename)

@course_bp.route('/chat/tts/<path:filename>', methods=['GET'])
def serve_chat_tts(filename):
    return send_from_directory(os.path.join('uploads', 'tts'), filename)

@course_bp.route('/tts/single', methods=['POST'])
@jwt_required()
def generate_single_tts():
    """单页TTS生成接口 - 用于前端点击播放按钮时实时生成"""
    data = request.get_json()
    text = data.get('text', '')
    
    if not text or not text.strip():
        return api_response(code=400, msg='文本内容不能为空')
    
    # 生成唯一文件名
    filename = f"single_{uuid.uuid4().hex[:8]}.mp3"
    
    try:
        saved_name = tts_utils.text_to_speech(text.strip(), filename)
        if saved_name:
            return api_response(data={
                'audioUrl': f'/api/v1/lesson/chat/tts/{saved_name}'
            })
        else:
            return api_response(code=500, msg='语音生成失败')
    except Exception as e:
        print(f"Single TTS error: {e}")
        return api_response(code=500, msg='语音生成失败')
    
# 问答接口 (QA) 适配文档
# 问答接口 (QA) 适配多轮交互和上下文
@course_bp.route('/qa/interact', methods=['POST'])
@verify_signature
@jwt_required()
def chat_with_ai():
    data = request.get_json()
    course_id = data.get('courseId')
    page_num = data.get('pageNum', 1)
    question = data.get('questionContent') or data.get('question')
    history_qa = data.get('historyQa',[]) # 获取前端传来的多轮历史
    
    # 1. 尝试获取当前页的讲稿作为 AI 的知识上下文关联
    context = ""
    if course_id:
        course = Course.query.get(course_id)
        if course and course.ai_script:
            try:
                slides = json.loads(course.ai_script)
                for slide in slides:
                    # 精准匹配当前页的讲稿
                    if str(slide.get('page')) == str(page_num) or str(slide.get('pageNum')) == str(page_num):
                        context = slide.get('content', '')
                        break
            except Exception as e:
                print(f"解析讲稿获取上下文失败: {e}")
                
    # 2. 调用支持多轮记忆的 AI 接口 (真实调用大模型)
    ai_generator = AIGenerator(provider='zhipu') # 确保使用的是 zhipu
    reply = ai_generator.generate_chat_reply(question=question, history=history_qa, context=context)
    
    # 3. 尝试 TTS 语音合成
    audio_url = ""
    try:
        fname = tts_utils.text_to_speech(reply)
        if fname:
            audio_url = f'/api/v1/lesson/chat/tts/{fname}'
    except Exception as e:
        print(f"QA TTS error: {e}")
        
    return api_response(data={
        'answerId': f"ans{uuid.uuid4().hex[:8]}",
        'answerContent': reply,
        'audioUrl': audio_url,
        'answerType': 'text'
    })