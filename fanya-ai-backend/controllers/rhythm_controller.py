from flask import Blueprint, request, jsonify, send_from_directory
from flask_jwt_extended import get_jwt_identity, jwt_required
from models.rhythm import LearningHistory, LearningProgress
from models.qa import QARecord, QASession
from models.user import User
from extensions import db
import os

# import tts and ai utils
from utils import tts_utils, ai_utils

rhythm_bp = Blueprint('rhythm', __name__)

@rhythm_bp.route('/diagnose', methods=['POST'])
@jwt_required()
def diagnose_rhythm():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    if user.role != 'student':
        return jsonify(code='403', msg='只有学生可以诊断学习节奏'), 403
    
    data = request.get_json()
    course_id = data.get('courseId')
    page_num = data.get('pageNum')
    question = data.get('question')
    
    # Step 1: 使用 AI 模型生成文字回复
    try:
        ai_reply = ai_utils.generate_answer(question)
    except Exception as e:
        print(f'AI generation error: {e}')
        ai_reply = f'抱歉，未能获取答案。您的问题是："{question}"'
    
    diagnosis = {
        'rhythm': '正常',
        'suggestion': '继续保持当前学习节奏',
        'aiReply': ai_reply
    }

    # Step 2: 为文字回复生成 TTS 语音文件
    audio_filename = None
    try:
        audio_filename = tts_utils.text_to_speech(ai_reply)
        diagnosis['audioUrl'] = f'/api/rhythm/tts/{audio_filename}'
    except Exception as e:
        print(f'TTS error: {e}')
        # TTS 失败不影响返回文字内容

    # Step 3: 记录学习历史
    try:
        history = LearningHistory(
            student_id=current_user_id,
            course_id=course_id,
            page_num=page_num,
            question=question,
            ai_reply=ai_reply,
            audio_file=audio_filename,
            action=None  # 简化处理，实际应该有诊断逻辑
        )
        db.session.add(history)
        db.session.commit()
    except Exception as e:
        print(f'history save error: {e}')

    return jsonify(code='200', data=diagnosis)

@rhythm_bp.route('/progress/<int:course_id>', methods=['GET'])
@jwt_required()
def get_student_progress(course_id):
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    if user.role != 'student':
        return jsonify(code='403', msg='只有学生可以查看学习进度'), 403
    
    progress = LearningProgress.query.filter_by(
        student_id=current_user_id,
        course_id=course_id
    ).first()
    
    if not progress:
        return jsonify(code='200', data={'progress': 0, 'lastPage': 1})
    
    return jsonify(code='200', data={
        'progress': progress.mastery_degree,
        'lastPage': progress.current_page
    })

@rhythm_bp.route('/tts/<path:filename>', methods=['GET'])
def serve_tts(filename):
    # serve previously generated tts wav files from uploads/tts
    return send_from_directory(os.path.join('uploads','tts'), filename)

@rhythm_bp.route('/history/<int:course_id>', methods=['GET'])
@jwt_required()
def get_learning_history(course_id):
    try:
        current_user_id = get_jwt_identity()
        
        # 查询该用户在该课件的所有会话
        sessions = QASession.query.filter_by(
            user_id=str(current_user_id),
            lesson_id=str(course_id)
        ).all()
        
        if not sessions:
            print(f'[学习历史] 用户 {current_user_id} 在课件 {course_id} 没有会话记录')
            return jsonify(code='200', data=[])
        
        session_ids = [s.session_id for s in sessions]
        print(f'[学习历史] 找到 {len(session_ids)} 个会话: {session_ids}')
        
        # 查询这些会话的所有问答记录
        qa_records = QARecord.query.filter(
            QARecord.session_id.in_(session_ids)
        ).order_by(QARecord.create_time.desc()).all()
        
        print(f'[学习历史] 找到 {len(qa_records)} 条问答记录')
        
        history_list = []
        for record in qa_records:
            history_list.append({
                'pageNum': record.related_section_id or '未知',
                'question': record.question_content,
                'aiReply': record.answer_content,
                'audioUrl': record.answer_audio_url or '',
                'action': record.understanding_level or 'unknown',
                'createTime': record.create_time.strftime('%Y-%m-%d %H:%M:%S') if record.create_time else ''
            })
        
        return jsonify(code='200', data=history_list)
    except Exception as e:
        print(f'[学习历史] 查询失败: {e}')
        import traceback
        traceback.print_exc()
        return jsonify(code='500', msg=f'查询失败: {str(e)}'), 500