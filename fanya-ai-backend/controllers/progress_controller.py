from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity, jwt_required
from models.progress import LearningProgress, RhythmAdjustment, LearningDiagnosis
from models.qa import QARecord, QASession
from models.lesson import Lesson
from models.quiz import QuizAnswer, QuizAttempt
from extensions import db
import uuid
import json
import time
from datetime import datetime

from utils.api_utils import verify_signature, api_response

progress_bp = Blueprint('progress', __name__)

# ==================== 2.3.1 学习进度追踪接口 ====================


@progress_bp.route('/track', methods=['POST'])
@verify_signature
@jwt_required()
def track_progress():
    current_user_id = get_jwt_identity()
    data = request.get_json()

    school_id = data.get('schoolId', 'sch10001')
    course_id = data.get('courseId')
    lesson_id = data.get('lessonId')
    current_section_id = data.get('currentSectionId')

    # 【修复空值报错】：强制转换为 float，如果前端传 null 或解析失败，默认给 0.0
    try:
        progress_percent = float(data.get('progressPercent') or 0.0)
    except (TypeError, ValueError):
        progress_percent = 0.0

    last_operate_time = data.get('lastOperateTime')
    qa_record_id = data.get('qaRecordId')

    if not lesson_id:
        return api_response(code=400, msg='lessonId不能为空')

    progress = LearningProgress.query.filter_by(
        user_id=str(current_user_id),
        lesson_id=lesson_id
    ).first()

    if not progress:
        track_id = f"track{int(time.time())}{uuid.uuid4().hex[:6]}"
        progress = LearningProgress(
            track_id=track_id,
            school_id=school_id,
            user_id=str(current_user_id),
            course_id=course_id,
            lesson_id=lesson_id
        )
        db.session.add(progress)

    progress.current_section_id = current_section_id
    progress.progress_percent = progress_percent
    progress.total_progress = progress_percent

    # 这里保留你旧代码可能有的判断逻辑，使用转换后的 progress_percent 就不会报错了
    if progress_percent >= 80:
        try:
            current_num = int(current_section_id.replace('sec', ''))
            progress.next_section_suggest = f"sec{current_num + 1:03d}"
        except:
            progress.next_section_suggest = current_section_id
    else:
        progress.next_section_suggest = current_section_id

    if last_operate_time:
        try:
            progress.last_operate_time = datetime.strptime(
                last_operate_time, '%Y-%m-%d %H:%M:%S')
        except:
            progress.last_operate_time = datetime.now()
    else:
        progress.last_operate_time = datetime.now()

    if qa_record_id:
        progress.last_qa_record_id = qa_record_id

    db.session.commit()

    return api_response(data={
        'trackId': progress.track_id,
        'totalProgress': progress.total_progress,
        'currentSectionId': progress.current_section_id
    }, msg="进度追踪成功")


# ==================== 2.3.2 学习节奏调整接口 ====================
@progress_bp.route('/adjust', methods=['POST'])
@verify_signature
@jwt_required()
def adjust_rhythm():
    """
    接口功能：基于学生理解程度与学习进度，调整后续讲授节奏
    (此逻辑主体已融合到 qa_controller 的 NLP 实时分析中，此接口保留记录用途)
    """
    current_user_id = get_jwt_identity()
    data = request.get_json()

    lesson_id = data.get('lessonId')
    current_section_id = data.get('currentSectionId')
    understanding_level = data.get('understandingLevel', 'partial')
    qa_record_id = data.get('qaRecordId')

    if not lesson_id or not current_section_id:
        return api_response(code=400, msg='lessonId和currentSectionId不能为空')

    adjust_type = 'normal'
    if understanding_level == 'none':
        adjust_type = 'supplement'
    elif understanding_level == 'full':
        adjust_type = 'accelerate'

    # 保存调整记录以供数据大屏（Dashboard）分析使用
    adjustment = RhythmAdjustment(
        user_id=str(current_user_id),
        lesson_id=lesson_id,
        current_section_id=current_section_id,
        understanding_level=understanding_level,
        qa_record_id=qa_record_id,
        adjust_type=adjust_type,
        continue_section_id=current_section_id
    )
    db.session.add(adjustment)
    db.session.commit()

    return api_response(data={
        'adjustPlan': {
            'continueSectionId': current_section_id,
            'adjustType': adjust_type
        }
    })


# ==================== 辅助查询接口（前端进入课堂时拉取） ====================
@progress_bp.route('/detail/<lesson_id>', methods=['GET'])
@jwt_required()
def get_progress_detail(lesson_id):
    """获取该生在该课件的学习进度详情（用于断点续传初始化）"""
    current_user_id = get_jwt_identity()

    progress = LearningProgress.query.filter_by(
        user_id=str(current_user_id),
        lesson_id=lesson_id
    ).first()

    if not progress:
        return api_response(data={
            'totalProgress': 0.0,
            'currentSectionId': None,
            'nextSectionSuggest': None
        })

    return api_response(data=progress.to_dict())


@progress_bp.route('/adjustments/<lesson_id>', methods=['GET'])
@jwt_required()
def get_adjustments(lesson_id):
    """获取该生在该课程的历史节奏调整记录"""
    current_user_id = get_jwt_identity()

    adjustments = RhythmAdjustment.query.filter_by(
        user_id=str(current_user_id),
        lesson_id=lesson_id
    ).order_by(RhythmAdjustment.create_time.desc()).all()

    return api_response(data=[adj.to_dict() for adj in adjustments])


# ==================== 2.3.2.5 复习追踪接口 ====================
@progress_bp.route('/trackReview', methods=['POST'])
@verify_signature
@jwt_required()
def track_review():
    """
    追踪学生的复习情况
    记录复习开始、复习中的提问、复习结束等信息
    """
    current_user_id = get_jwt_identity()
    data = request.get_json()
    
    lesson_id = data.get('lessonId')
    section_name = data.get('section')
    review_type = data.get('type')  # review_start, review_end, review_question
    
    if not lesson_id or not section_name:
        return api_response(code=400, msg='lessonId和section不能为空')
    
    # 记录复习信息到数据库（可以创建新表或使用现有表）
    # 这里简单地返回成功，实际应该保存到数据库
    
    return api_response(data={
        'reviewId': f"rev{int(time.time())}{uuid.uuid4().hex[:6]}",
        'section': section_name,
        'type': review_type,
        'timestamp': datetime.now().isoformat()
    }, msg='复习追踪记录成功')


# ==================== 2.3.2.6 复习效果评估接口 ====================
@progress_bp.route('/evaluateReview/<lesson_id>/<section_name>', methods=['GET'])
@jwt_required()
def evaluate_review(lesson_id, section_name):
    """
    评估学生在特定章节的复习效果
    对比复习前后的理解程度
    """
    current_user_id = get_jwt_identity()
    
    # 获取该用户在该课程的所有会话
    sessions = QASession.query.filter_by(
        user_id=str(current_user_id),
        lesson_id=lesson_id
    ).all()
    
    session_ids = [s.session_id for s in sessions]
    
    if not session_ids:
        return api_response(data={
            'section': section_name,
            'reviewStatus': 'no_data',
            'message': '暂无该章节的问答记录'
        })
    
    # 获取该章节的问答记录（多种匹配方式）
    qa_records = QARecord.query.filter(
        QARecord.session_id.in_(session_ids)
    ).order_by(QARecord.create_time.desc()).all()
    
    # 过滤出与该章节相关的记录
    # 1. 先尝试通过 related_knowledge_name 匹配
    filtered_records = [qa for qa in qa_records if qa.related_knowledge_name and section_name in qa.related_knowledge_name]
    
    # 2. 如果没有找到，尝试通过 related_section_id 匹配
    if not filtered_records:
        filtered_records = [qa for qa in qa_records if qa.related_section_id and section_name in qa.related_section_id]
    
    # 3. 如果还是没有找到，返回最近的问答记录（可能是用户刚提问的）
    if not filtered_records:
        # 获取最近的问答记录
        filtered_records = qa_records[:10]
    
    if not filtered_records:
        return api_response(data={
            'section': section_name,
            'reviewStatus': 'no_data',
            'message': '暂无该章节的问答记录'
        })
    
    # 分析理解程度变化
    understanding_levels = [qa.understanding_level for qa in filtered_records]
    
    # 计算最近的理解程度（复习后）
    recent_level = understanding_levels[0] if understanding_levels else 'partial'
    
    # 计算之前的理解程度（复习前）
    previous_level = understanding_levels[-1] if len(understanding_levels) > 1 else understanding_levels[0]
    
    # 判断复习效果
    improvement = 'no_change'
    if previous_level == 'none' and recent_level in ['partial', 'full']:
        improvement = 'significant'  # 显著提升
    elif previous_level == 'partial' and recent_level == 'full':
        improvement = 'significant'  # 显著提升
    elif previous_level == 'none' and recent_level == 'partial':
        improvement = 'moderate'  # 中等提升
    elif previous_level == recent_level:
        improvement = 'no_change'  # 无变化
    
    return api_response(data={
        'section': section_name,
        'previousLevel': previous_level,
        'recentLevel': recent_level,
        'improvement': improvement,
        'totalQuestions': len(filtered_records),
        'message': {
            'significant': '复习效果显著，理解程度明显提升！',
            'moderate': '复习有效果，理解程度有所提升',
            'no_change': '理解程度未变化，建议继续复习或提问'
        }.get(improvement, '复习中...')
    })


# ==================== 2.3.3 智能节奏诊断接口 ====================
@progress_bp.route('/diagnose/<lesson_id>', methods=['GET'])
@jwt_required()
def diagnose_rhythm(lesson_id):
    """
    智能诊断学习节奏，分析学生理解程度和学习状态
    返回：当前理解水平、建议调整方案、需要补充的知识点
    """
    current_user_id = get_jwt_identity()
    
    # 检查是否强制刷新
    force_refresh = request.args.get('forceRefresh', '0') == '1'
    if force_refresh:
        print(f"[诊断] 强制刷新模式，跳过缓存: user={current_user_id}, lesson={lesson_id}")
    
    # 动态导入模型（避免重启服务）
    from models.progress import LearningDiagnosis
    from models.quiz import QuizAttempt
    
    # 首先尝试从数据库获取已保存的诊断结果（如果不是强制刷新）
    if not force_refresh:
        try:
            # 检查表是否存在
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            if 'biz_learning_diagnosis' not in inspector.get_table_names():
                print("[诊断] 诊断表不存在，跳过缓存读取")
                raise Exception("诊断表不存在")
            
            saved_diagnosis = LearningDiagnosis.query.filter_by(
                user_id=str(current_user_id),
                lesson_id=lesson_id
            ).first()
            
            if saved_diagnosis:
                # 检查诊断结果是否过期（超过1小时重新生成）
                from datetime import timedelta
                if datetime.now() - saved_diagnosis.update_time < timedelta(hours=1):
                    print(f"[诊断] 使用缓存的诊断结果: user={current_user_id}, lesson={lesson_id}")
                    data = saved_diagnosis.to_dict()
                    # 转换字段名以匹配前端期望
                    return api_response(data={
                        'understandingScore': data.get('understanding_score', 50),
                        'understandingStats': data.get('understanding_stats', {'full': 0, 'partial': 0, 'none': 0}),
                        'quizStats': data.get('quiz_stats'),
                        'confusedSections': data.get('confused_sections', []),
                        'masteredSections': data.get('mastered_sections', []),
                        'suggestions': data.get('suggestions', []),
                        'questionTypes': data.get('question_types', {}),
                        'weakPoints': data.get('weak_points', []),
                        'learningPath': data.get('learning_path', {}),
                        'aiDiagnosis': data.get('ai_diagnosis', '')
                    })
        except Exception as e:
            print(f"[诊断] 读取缓存诊断结果失败: {e}")
    
    # 获取该用户在该课程的所有会话
    sessions = QASession.query.filter_by(
        user_id=str(current_user_id),
        lesson_id=lesson_id
    ).all()
    
    session_ids = [s.session_id for s in sessions]
    
    # 获取最近的问答记录（增加到20条以获取更多数据）
    recent_qa = QARecord.query.filter(
        QARecord.session_id.in_(session_ids)
    ).order_by(QARecord.create_time.desc()).limit(20).all()
    
    # 获取节奏调整记录
    adjustments = RhythmAdjustment.query.filter_by(
        user_id=str(current_user_id),
        lesson_id=lesson_id
    ).order_by(RhythmAdjustment.create_time.desc()).limit(5).all()
    
    # 分析理解程度
    understanding_stats = {
        'none': 0,
        'partial': 0,
        'full': 0
    }
    
    # 获取课程的章节信息
    lesson = Lesson.query.filter((Lesson.parse_id == lesson_id) | (Lesson.id == lesson_id)).first()
    chapters_map = {}  # 页码到章节名称的映射
    
    if lesson and lesson.structure_data:
        try:
            structure = json.loads(lesson.structure_data)
            chapters = structure.get('chapters', [])
            for chapter in chapters:
                # 假设章节结构中有 pages 或 page_range 字段
                if isinstance(chapter, dict):
                    chapter_name = chapter.get('name') or chapter.get('title') or ''
                    pages = chapter.get('pages') or chapter.get('page_range') or []
                    if isinstance(pages, list):
                        for page in pages:
                            chapters_map[str(page)] = chapter_name
                    elif isinstance(pages, str):
                        # 处理 "1-5" 这样的范围
                        if '-' in pages:
                            start, end = pages.split('-')
                            for p in range(int(start), int(end) + 1):
                                chapters_map[str(p)] = chapter_name
                        else:
                            chapters_map[pages] = chapter_name
                    # 同时记录章节ID到名称的映射
                    chapter_id = chapter.get('id') or chapter.get('chapter_id')
                    if chapter_id:
                        chapters_map[str(chapter_id)] = chapter_name
        except Exception as e:
            print(f"[诊断] 解析章节信息失败: {e}")
    
    # 如果structure_data中没有章节信息，尝试从文件名或课程名提取
    if not chapters_map and lesson:
        # 使用课程名作为默认章节名
        default_chapter = lesson.file_name or lesson.course_name or '课程内容'
        chapters_map['default'] = default_chapter
    
    confused_sections = []  # 困惑的章节
    mastered_sections = []  # 掌握的章节
    question_types = {}  # 问题类型统计
    weak_points = []  # 薄弱知识点
    section_name_map = {}  # 章节ID到名称的映射
    
    for qa in recent_qa:
        level = qa.understanding_level or 'partial'
        understanding_stats[level] = understanding_stats.get(level, 0) + 1
        
        # 分析问题内容，提取关键词
        question = qa.question_content or ''
        answer = qa.answer_content or ''
        
        # 获取章节名称 - 使用多种方式尝试获取有意义的知识点名称
        section_id = qa.related_section_id
        section_name = None
        
        # 1. 优先使用 related_knowledge_name（最准确的知识点名称）
        if qa.related_knowledge_name:
            section_name = qa.related_knowledge_name
        
        # 2. 从 chapters_map 中查找（根据页码或章节ID）
        if not section_name and section_id:
            # 尝试从 section_id 中提取页码（假设格式为 "sec15" 或 "15"）
            page_num = section_id.replace('sec', '')
            section_name = chapters_map.get(page_num)
            # 如果没有找到，尝试直接使用section_id查找
            if not section_name:
                section_name = chapters_map.get(section_id)
        
        # 3. 尝试从问题内容中提取知识点关键词
        if not section_name and question:
            # 提取问题中的关键概念（如"欧姆定律"、"基尔霍夫定律"等）
            import re
            # 匹配常见的技术术语（如"XX定律"、"XX定理"、"XX效应"等）
            patterns = [
                r'([\u4e00-\u9fa5]{2,8}(?:定律|定理|效应|原理|公式|方法|理论))',
                r'([\u4e00-\u9fa5]{2,6}(?:电流|电压|电阻|功率|电路|电势))',
            ]
            for pattern in patterns:
                match = re.search(pattern, question)
                if match:
                    section_name = match.group(1)
                    break
        
        # 4. 如果还是没有找到，使用section_id或默认名称
        if not section_name:
            if section_id:
                # 尝试美化section_id显示
                section_name = section_id.replace('sec', '第') + '节' if 'sec' in section_id else section_id
            else:
                section_name = '未分类知识点'
        
        if section_id:
            section_name_map[section_id] = section_name
        
        # 统计问题类型
        if '是什么' in question or '定义' in question or '概念' in question:
            question_types['concept'] = question_types.get('concept', 0) + 1
        elif '为什么' in question or '原因' in question or '为何' in question:
            question_types['reason'] = question_types.get('reason', 0) + 1
        elif '怎么' in question or '如何' in question or '方法' in question or '步骤' in question:
            question_types['method'] = question_types.get('method', 0) + 1
        elif '公式' in question or '计算' in question or '数值' in question or '求' in question:
            question_types['formula'] = question_types.get('formula', 0) + 1
        elif '应用' in question or '例子' in question or '实例' in question:
            question_types['application'] = question_types.get('application', 0) + 1
        
        # 根据理解程度和答题情况分析
        if level == 'none':
            # 完全不理解的情况
            if section_id not in confused_sections:
                confused_sections.append(section_id)
            
            # 分析不解难度
            reason = '理解困难'
            if '公式' in question:
                reason = '公式理解困难'
            elif '概念' in question or '定义' in question:
                reason = '基础概念不清'
            elif '应用' in question:
                reason = '知识应用困难'
            
            # 优先使用related_knowledge_name作为知识点名称
            knowledge_point = qa.related_knowledge_name
            answer = qa.answer_content or ''
            print(f"[DEBUG] QA记录: related_knowledge_name={knowledge_point}, question={question[:30]}...")
            
            if not knowledge_point:
                # 1. 尝试从AI回答中提取知识点（AI回答通常会提到知识点名称）
                import re
                # 匹配AI回答中的知识点介绍模式
                answer_patterns = [
                    # 匹配"XXX是..."、"XXX指的是..."等定义模式
                    r'^([\u4e00-\u9fa5]{2,10})(?:是|指的是|表示|定义为)',
                    # 匹配"我们来学习XXX"、"关于XXX"等引导模式
                    r'(?:学习|了解|掌握|理解|介绍|讲解)([\u4e00-\u9fa5]{2,10})(?:的内容|的概念|的原理|的知识)',
                ]
                for pattern in answer_patterns:
                    match = re.search(pattern, answer[:200])  # 只看回答前200字
                    if match:
                        knowledge_point = match.group(1)
                        print(f"[DEBUG] 从AI回答中提取知识点: {knowledge_point}")
                        break
            
            if not knowledge_point:
                # 2. 尝试从问题中提取关键概念
                question_patterns = [
                    # 匹配"第X章 XXX"格式
                    r'第\d+章\s+([\u4e00-\u9fa5]{2,8})',
                    # 匹配"什么是XXX"、"XXX是什么"、"解释XXX"等模式
                    r'(?:什么是|什么叫|解释|说明|介绍|简述)\s*([\u4e00-\u9fa5]{2,10})',
                    r'([\u4e00-\u9fa5]{2,10})(?:是什么|的定义|的概念|的原理)',
                    r'(?:如何|怎么)\s*(?:计算|求解|应用|理解)\s*([\u4e00-\u9fa5]{2,10})',
                    # 匹配技术术语
                    r'([\u4e00-\u9fa5]{2,8}(?:定律|定理|效应|原理|公式|方法|理论))',
                ]
                for pattern in question_patterns:
                    match = re.search(pattern, question)
                    if match:
                        knowledge_point = match.group(1)
                        print(f"[DEBUG] 从问题中提取知识点: {knowledge_point}")
                        break
            
            if not knowledge_point:
                # 3. 使用章节名称（从课件结构中获取）
                if section_id and section_id in section_name_map:
                    knowledge_point = section_name_map[section_id]
                    # 如果章节名称是课件文件名，简化显示
                    if '.pptx' in str(knowledge_point) or '.ppt' in str(knowledge_point):
                        page_match = re.search(r'(\d+)', str(section_id))
                        if page_match:
                            knowledge_point = f"第{page_match.group(1)}页内容"
                        else:
                            knowledge_point = "课件内容"
                    print(f"[DEBUG] 使用章节名称: {knowledge_point}")
                else:
                    # 4. 最后使用页码
                    page_match = re.search(r'(\d+)', str(section_id)) if section_id else None
                    if page_match:
                        knowledge_point = f"第{page_match.group(1)}页内容"
                    else:
                        knowledge_point = '相关知识点'
                    print(f"[DEBUG] 使用默认知识点: {knowledge_point}")
            
            weak_points.append({
                'section': knowledge_point,
                'sectionId': section_id,
                'question': question[:50] + '...' if len(question) > 50 else question,
                'type': reason,
                'level': 'none'
            })
        elif level == 'partial':
            # 部分理解的情况
            if section_id not in confused_sections and section_id not in mastered_sections:
                confused_sections.append(section_id)
            
            # 优先使用related_knowledge_name作为知识点名称
            knowledge_point = qa.related_knowledge_name
            
            if not knowledge_point:
                # 1. 尝试从AI回答中提取知识点
                import re
                answer_patterns = [
                    r'^([\u4e00-\u9fa5]{2,10})(?:是|指的是|表示|定义为)',
                    r'(?:学习|了解|掌握|理解|介绍|讲解)([\u4e00-\u9fa5]{2,10})(?:的内容|的概念|的原理|的知识)',
                ]
                for pattern in answer_patterns:
                    match = re.search(pattern, answer[:200])
                    if match:
                        knowledge_point = match.group(1)
                        break
            
            if not knowledge_point:
                # 2. 尝试从问题中提取关键概念
                question_patterns = [
                    r'第\d+章\s+([\u4e00-\u9fa5]{2,8})',
                    r'(?:什么是|什么叫|解释|说明|介绍|简述)\s*([\u4e00-\u9fa5]{2,10})',
                    r'([\u4e00-\u9fa5]{2,10})(?:是什么|的定义|的概念|的原理)',
                    r'(?:如何|怎么)\s*(?:计算|求解|应用|理解)\s*([\u4e00-\u9fa5]{2,10})',
                    r'([\u4e00-\u9fa5]{2,8}(?:定律|定理|效应|原理|公式|方法|理论))',
                ]
                for pattern in question_patterns:
                    match = re.search(pattern, question)
                    if match:
                        knowledge_point = match.group(1)
                        break
            
            if not knowledge_point:
                # 3. 使用章节名称
                if section_id and section_id in section_name_map:
                    knowledge_point = section_name_map[section_id]
                    if '.pptx' in str(knowledge_point) or '.ppt' in str(knowledge_point):
                        page_match = re.search(r'(\d+)', str(section_id))
                        if page_match:
                            knowledge_point = f"第{page_match.group(1)}页内容"
                        else:
                            knowledge_point = "课件内容"
                else:
                    # 4. 最后使用页码
                    page_match = re.search(r'(\d+)', str(section_id)) if section_id else None
                    if page_match:
                        knowledge_point = f"第{page_match.group(1)}页内容"
                    else:
                        knowledge_point = '相关知识点'
            
            weak_points.append({
                'section': knowledge_point,
                'sectionId': section_id,
                'question': question[:50] + '...' if len(question) > 50 else question,
                'type': '部分理解',
                'level': 'partial'
            })
        elif level == 'full':
            # 完全理解的情况
            if section_id not in mastered_sections:
                mastered_sections.append(section_id)
    
    # 获取学生在该课程的所有测验尝试记录（包括多次答题）
    quiz_attempts = QuizAttempt.query.filter_by(
        user_id=str(current_user_id),
        lesson_id=lesson_id
    ).order_by(QuizAttempt.submit_time.desc()).all()
    
    # 计算所有测验尝试的累计统计
    total_quizzes = 0
    total_correct = 0
    attempt_count = len(quiz_attempts)
    
    if quiz_attempts:
        # 累加所有尝试的题目数和正确数
        for attempt in quiz_attempts:
            total_quizzes += attempt.total_questions
            total_correct += attempt.correct_count
        
        # 计算整体正确率
        quiz_accuracy = (total_correct / total_quizzes * 100) if total_quizzes > 0 else None
        
        # 获取最近一次测验的详情
        latest_attempt = quiz_attempts[0]
        print(f"[DEBUG] 测验尝试次数: {attempt_count}")
        print(f"[DEBUG] 累计答题: 总题数={total_quizzes}, 正确数={total_correct}, 正确率={quiz_accuracy}")
        print(f"[DEBUG] 最近一次测验: 得分={latest_attempt.total_score}, 正确={latest_attempt.correct_count}/{latest_attempt.total_questions}")
    else:
        # 如果没有测验尝试记录，尝试从QuizAnswer获取（兼容旧数据）
        quiz_answers = QuizAnswer.query.filter_by(
            user_id=str(current_user_id),
            lesson_id=lesson_id
        ).all()
        total_quizzes = len(quiz_answers)
        total_correct = sum(1 for a in quiz_answers if a.is_correct)
        quiz_accuracy = (total_correct / total_quizzes * 100) if total_quizzes > 0 else None
        print(f"[DEBUG] 从QuizAnswer获取: 总题数={total_quizzes}, 正确数={total_correct}, 正确率={quiz_accuracy}")
    
    # 获取智能插旗考点（每5页测验题）的答题记录
    try:
        from models.progress import CheckpointAnswer
        print(f"[DEBUG] 正在查询Checkpoint答题记录: user={current_user_id}, lesson={lesson_id}")
        # 尝试用字符串和整数两种形式查询lesson_id
        checkpoint_answers = CheckpointAnswer.query.filter(
            CheckpointAnswer.user_id == str(current_user_id),
            (CheckpointAnswer.lesson_id == str(lesson_id)) | (CheckpointAnswer.lesson_id == lesson_id)
        ).all()
        print(f"[DEBUG] 查询到Checkpoint答题记录数量: {len(checkpoint_answers)}")
        # 打印每条记录详情用于调试
        for ans in checkpoint_answers:
            print(f"[DEBUG] Checkpoint记录: lesson_id={ans.lesson_id}, checkpoint_id={ans.checkpoint_id}, is_correct={ans.is_correct}")
        
        if checkpoint_answers:
            checkpoint_total = len(checkpoint_answers)
            checkpoint_correct = sum(1 for a in checkpoint_answers if a.is_correct)
            checkpoint_accuracy = (checkpoint_correct / checkpoint_total * 100) if checkpoint_total > 0 else 0
            
            print(f"[DEBUG] 智能插旗答题: 总题数={checkpoint_total}, 正确数={checkpoint_correct}, 正确率={checkpoint_accuracy}")
            
            # 将Checkpoint答题数据合并到总测验统计中
            if total_quizzes > 0:
                # 合并统计
                total_quizzes += checkpoint_total
                total_correct += checkpoint_correct
                quiz_accuracy = (total_correct / total_quizzes * 100)
            else:
                # 如果没有普通测验记录，使用Checkpoint数据
                total_quizzes = checkpoint_total
                total_correct = checkpoint_correct
                quiz_accuracy = checkpoint_accuracy
            
            # 根据Checkpoint答题情况更新理解度统计
            # 如果Checkpoint答对率高，增加"完全理解"计数
            if checkpoint_accuracy >= 80:
                understanding_stats['full'] = understanding_stats.get('full', 0) + 1
            elif checkpoint_accuracy >= 50:
                understanding_stats['partial'] = understanding_stats.get('partial', 0) + 1
            else:
                understanding_stats['none'] = understanding_stats.get('none', 0) + 1
                
            print(f"[DEBUG] 合并Checkpoint后: 总题数={total_quizzes}, 正确数={total_correct}, 正确率={quiz_accuracy}")
    except Exception as e:
        print(f"[DEBUG] 获取Checkpoint答题记录失败: {e}")
    
    # 计算整体理解度（0-100）- 结合问答理解和答题正确率
    total_qa = sum(understanding_stats.values())
    if total_qa > 0:
        qa_score = (
            understanding_stats['full'] * 100 + 
            understanding_stats['partial'] * 50 + 
            understanding_stats['none'] * 0
        ) / total_qa
    else:
        qa_score = 50.0
    
    # 如果有答题记录，将正确率与问答理解度加权计算
    if quiz_accuracy is not None:
        # 答题正确率权重60%，问答理解度权重40%
        understanding_score = quiz_accuracy * 0.6 + qa_score * 0.4
        print(f"[DEBUG] 综合理解度: 答题正确率({quiz_accuracy})*0.6 + 问答理解度({qa_score})*0.4 = {understanding_score}")
    else:
        understanding_score = qa_score
    
    # 用于后续使用的变量统一
    correct_quizzes = total_correct
    
    # 生成详细建议
    suggestions = []
    
    # 根据理解程度生成建议
    if understanding_score < 40:
        details = []
        if understanding_stats['none'] > 0:
            details.append(f"您在 {understanding_stats['none']} 个问题上表现出完全不理解")
        if understanding_stats['partial'] > 0:
            details.append(f"还有 {understanding_stats['partial']} 个问题部分理解")
        
        # 根据问题类型给出具体建议
        if question_types.get('concept', 0) > 0:
            details.append("基础概念理解不足，建议从定义和原理开始")
        if question_types.get('formula', 0) > 0:
            details.append("公式推导和应用需要加强，建议多做例题")
        if question_types.get('method', 0) > 0:
            details.append("解题方法不清楚，建议学习标准解题步骤")
        
        if not details:
            details = ['建议重新学习困惑章节，加强基础理解']
        
        suggestions.append({
            'type': 'slow_down',
            'message': '检测到理解困难，建议放慢节奏，增加互动',
            'details': details,
            'action': 'review',
            'sections': [section_name_map.get(s, s) for s in confused_sections[:3]]
        })
    elif understanding_score > 80:
        details = []
        if understanding_stats['full'] > 0:
            details.append(f"您已完全理解 {understanding_stats['full']} 个知识点")
        details.append("掌握程度良好，可以尝试更深入的问题")
        details.append("建议挑战难度更高的应用题")
        
        suggestions.append({
            'type': 'speed_up',
            'message': '掌握良好，可以适当加快进度',
            'details': details,
            'action': 'continue',
            'sections': []
        })
    else:
        details = []
        if understanding_stats['partial'] > 0:
            details.append(f"有 {understanding_stats['partial']} 个知识点部分理解，需要深入学习")
        if understanding_stats['full'] > 0:
            details.append(f"已掌握 {understanding_stats['full']} 个知识点")
        if confused_sections:
            details.append(f"需要重点关注：{', '.join(confused_sections[:2])}")
        
        if not details:
            details = ['保持当前学习节奏，遇到困难及时提问']
        
        suggestions.append({
            'type': 'maintain',
            'message': '当前节奏适中，继续保持',
            'details': details,
            'action': 'continue',
            'sections': [section_name_map.get(s, s) for s in confused_sections[:2]]
        })
    
    # 根据薄弱点生成复习建议
    if weak_points:
        review_details = []
        learning_guide = []
        
        # 按理解程度分类
        none_points = [wp for wp in weak_points if wp.get('level') == 'none']
        partial_points = [wp for wp in weak_points if wp.get('level') == 'partial']
        
        # 优先级排序：完全不理解 > 部分理解
        priority_points = none_points + partial_points
        
        if none_points:
            review_details.append(f"🔴 完全不理解knowledge点（{len(none_points)}个）- 【最高优先级】：")
            for wp in none_points[:3]:
                review_details.append(f"  • {wp['section']}: {wp['question']}")
                # 添加学习建议
                if '公式' in wp['question']:
                    learning_guide.append(f"【{wp['section']}】建议：先理解公式的含义，再学习推导过程，最后做练习题")
                elif '概念' in wp['question'] or '定义' in wp['question']:
                    learning_guide.append(f"【{wp['section']}】建议：通过生活化例子理解概念，制作思维导图，对比相似概念")
                elif '应用' in wp['question']:
                    learning_guide.append(f"【{wp['section']}】建议：先掌握基础理论，再看实际应用案例，最后自己尝试应用")
                else:
                    learning_guide.append(f"【{wp['section']}】建议：重新学习该章节的基础内容，可以看视频讲解或请教老师")
        
        if partial_points:
            review_details.append(f"🟡 部分理解knowledge点（{len(partial_points)}个）- 【中等优先级】：")
            for wp in partial_points[:3]:
                review_details.append(f"  • {wp['section']}: {wp['question']}")
                # 添加学习建议
                if '公式' in wp['question']:
                    learning_guide.append(f"【{wp['section']}】建议：深入理解公式的推导过程，做相关练习题巩固")
                elif '方法' in wp['question'] or '步骤' in wp['question']:
                    learning_guide.append(f"【{wp['section']}】建议：学习标准解题步骤，做类似题目进行练习")
                else:
                    learning_guide.append(f"【{wp['section']}】建议：通过做练习题来巩固理解，遇到问题及时提问")
        
        # 组合详情和学习指南
        all_details = review_details + [""] + ["📚 学习指南："] + learning_guide
        
        suggestions.append({
            'type': 'review',
            'message': f'发现 {len(confused_sections)} 个薄弱章节需要复习',
            'details': all_details if all_details else [f'建议复习：{", ".join([section_name_map.get(s, s) for s in confused_sections[:3]])}'],
            'action': 'review',
            'sections': [section_name_map.get(s, s) for s in confused_sections[:3]],
            'priority': 'high' if none_points else 'medium'
        })
    
    # 根据问题类型给出针对性建议
    if question_types.get('concept', 0) > 2:
        concept_details = [
            f'您提出了 {question_types["concept"]} 个概念性问题',
            '建议：系统梳理基础概念，建立知识框架',
            '方法：制作概念思维导图，理解各概念间的关系'
        ]
        suggestions.append({
            'type': 'concept_weak',
            'message': '概念理解需要加强',
            'details': concept_details,
            'action': 'review',
            'sections': [section_name_map.get(s, s) for s in confused_sections[:2]]
        })
    
    if question_types.get('formula', 0) > 2:
        formula_details = [
            f'您在公式相关问题上提问了 {question_types["formula"]} 次',
            '建议：多做例题，理解公式推导过程',
            '方法：从简单例题开始，逐步提高难度'
        ]
        suggestions.append({
            'type': 'formula_weak',
            'message': '公式应用需要练习',
            'details': formula_details,
            'action': 'practice',
            'sections': []
        })
    
    if question_types.get('method', 0) > 2:
        method_details = [
            f'您在解题方法上提问了 {question_types["method"]} 次',
            '建议：学习标准解题步骤和技巧',
            '方法：观看解题视频，跟随步骤练习'
        ]
        suggestions.append({
            'type': 'method_weak',
            'message': '解题方法需要学习',
            'details': method_details,
            'action': 'practice',
            'sections': []
        })
    
    if question_types.get('application', 0) > 2:
        app_details = [
            f'您在知识应用上提问了 {question_types["application"]} 次',
            '建议：通过实际案例理解知识应用',
            '方法：做应用题，分析实际问题中的知识点'
        ]
        suggestions.append({
            'type': 'application_weak',
            'message': '知识应用能力需要提升',
            'details': app_details,
            'action': 'practice',
            'sections': []
        })
    
    # 调用 AI 进行深度诊断分析
    ai_diagnosis = None
    try:
        from utils.ai_utils import AIGenerator
        ai_gen = AIGenerator(provider='zhipu')
        
        # 构建详细的答题记录信息
        # 1. 老师测验详细记录
        quiz_details = []
        if quiz_attempts:
            for attempt in quiz_attempts[:3]:  # 最近3次测验
                quiz_details.append(f"- 测验时间：{attempt.submit_time.strftime('%Y-%m-%d %H:%M')}, 得分：{attempt.total_score}分, 正确：{attempt.correct_count}/{attempt.total_questions}题")
        
        # 2. 每5页测验（Checkpoint）详细记录
        checkpoint_details = []
        if checkpoint_answers:
            for ans in checkpoint_answers[:10]:  # 最近10条记录
                status = "✓" if ans.is_correct else "✗"
                checkpoint_details.append(f"- 第{ans.page_num}页：{status} {ans.question_text[:30]}... (你的答案：{ans.user_answer[:20]}, 正确答案：{ans.correct_answer[:20]})")
        
        # 3. 问答答疑详细记录
        qa_details = []
        if qa_records:
            for qa in qa_records[:10]:  # 最近10条问答
                level_text = {"none": "不理解", "partial": "部分理解", "full": "完全理解"}.get(qa.understanding_level, "未知")
                qa_details.append(f"- [{level_text}] 问题：{qa.question_text[:40]}...")
        
        # 4. 薄弱知识点详细分析
        weak_details = []
        if weak_points:
            for wp in weak_points[:5]:
                level_text = {"none": "🔴 完全不理解", "partial": "🟡 部分理解"}.get(wp.get('level'), "")
                weak_details.append(f"- {level_text} 【{wp.get('section', '未知章节')}】{wp.get('question', '')[:50]}...")
        
        diagnosis_prompt = f"""请基于以下学生的详细学习数据，生成一份个性化的学习诊断报告。

【学生基本信息】
学习理解程度：{round(understanding_score, 1)}分
- 完全理解：{understanding_stats['full']}个知识点
- 部分理解：{understanding_stats['partial']}个知识点
- 完全不理解：{understanding_stats['none']}个知识点

【老师测验情况】
{chr(10).join(quiz_details) if quiz_details else "暂无测验记录"}
累计答题：{total_quizzes}题，正确：{correct_quizzes}题，正确率：{round(quiz_accuracy, 1) if quiz_accuracy else 0}%

【每5页测验情况（Checkpoint）】
{chr(10).join(checkpoint_details) if checkpoint_details else "暂无Checkpoint答题记录"}
共{len(checkpoint_answers) if checkpoint_answers else 0}题

【课堂问答答疑记录】
{chr(10).join(qa_details) if qa_details else "暂无问答记录"}

【薄弱知识点分析】
{chr(10).join(weak_details) if weak_details else "暂无薄弱点记录"}

困惑章节：{', '.join(confused_sections[:5]) if confused_sections else '无'}
掌握章节：{', '.join(mastered_sections[:5]) if mastered_sections else '无'}

请生成一份详细的个性化诊断报告（400字左右），要求：
1. **主要困难分析**：基于学生的具体答题情况和问答记录，分析该学生真正存在的问题（不要泛泛而谈）
2. **具体薄弱点**：指出哪些具体知识点需要加强，引用学生的实际答题错误
3. **针对性建议**：根据学生的错误类型给出具体的学习建议（如概念不清建议重读定义，应用题错建议多做案例等）
4. **鼓励话语**：基于学生的进步空间给出个性化鼓励

报告要具体到学生的实际情况，避免使用"大部分知识点"、"明显问题"等笼统表述。"""
        
        ai_diagnosis = ai_gen.generate_reply(diagnosis_prompt)
        print(f"[AI诊断] 生成诊断分析成功，长度：{len(ai_diagnosis) if ai_diagnosis else 0}字")
    except Exception as e:
        print(f"[AI诊断] 调用失败: {e}")
        import traceback
        traceback.print_exc()
        ai_diagnosis = None
    
    # 构建返回数据，包含答题正确率
    # 改进confusedSections：使用weak_points中的知识点名称
    confused_sections_enhanced = []
    for s in confused_sections:
        # 查找该section_id对应的weak_points
        section_weak_points = [wp for wp in weak_points if wp.get('sectionId') == s]
        if section_weak_points:
            # 使用知识点名称（section字段）
            knowledge_name = section_weak_points[0].get('section', '')
            if knowledge_name:
                # 如果知识点名称太长，截取前40个字符
                if len(knowledge_name) > 40:
                    knowledge_name = knowledge_name[:40] + '...'
                section_name = knowledge_name
            else:
                section_name = "未命名知识点"
        else:
            # 如果没有weak_points，使用section_name_map中的名称
            section_name = section_name_map.get(s, s)
            # 如果名称包含课件文件名，尝试简化
            if '.pptx' in str(section_name) or '.ppt' in str(section_name):
                # 提取页码部分
                import re
                page_match = re.search(r'(\d+)', str(s))
                if page_match:
                    section_name = f"第{page_match.group(1)}页内容"
                else:
                    section_name = "课件内容"
        
        confused_sections_enhanced.append(section_name)
    
    response_data = {
        'understandingScore': round(understanding_score, 1),
        'understandingStats': understanding_stats,
        'confusedSections': confused_sections_enhanced,
        'masteredSections': [section_name_map.get(s, s) for s in mastered_sections],
        'suggestions': suggestions,
        'questionTypes': question_types,
        'weakPoints': weak_points[:5],
        'recentAdjustments': [adj.to_dict() for adj in adjustments],
        'learningPath': {
            'priority': 'high' if understanding_score < 40 else 'medium' if understanding_score < 70 else 'low',
            'recommendation': '立即开始复习薄弱章节' if understanding_score < 40 else '继续学习，定期复习薄弱章节' if understanding_score < 70 else '保持当前进度，挑战更难的题目'
        },
        'aiDiagnosis': ai_diagnosis
    }
    
    # 如果有答题记录，添加到返回数据中
    if quiz_accuracy is not None:
        response_data['quizStats'] = {
            'total': total_quizzes,
            'correct': correct_quizzes,
            'accuracy': round(quiz_accuracy, 1)
        }
    
    # 保存诊断结果到数据库
    try:
        # 动态导入模型
        from models.progress import LearningDiagnosis
        from sqlalchemy import inspect
        
        # 检查表是否存在
        inspector = inspect(db.engine)
        if 'biz_learning_diagnosis' not in inspector.get_table_names():
            print("[诊断] 诊断表不存在，跳过保存")
            raise Exception("诊断表不存在")
        
        # 查找是否已有诊断记录
        existing_diagnosis = LearningDiagnosis.query.filter_by(
            user_id=str(current_user_id),
            lesson_id=lesson_id
        ).first()
        
        diagnosis_data = {
            'understanding_score': round(understanding_score, 1),
            'understanding_stats': json.dumps(understanding_stats),
            'quiz_stats': json.dumps(response_data.get('quizStats', {})),
            'confused_sections': json.dumps([section_name_map.get(s, s) for s in confused_sections]),
            'mastered_sections': json.dumps([section_name_map.get(s, s) for s in mastered_sections]),
            'suggestions': json.dumps(suggestions),
            'weak_points': json.dumps(weak_points[:5]),
            'ai_diagnosis': ai_diagnosis,
            'question_types': json.dumps(question_types),
            'learning_path': json.dumps(response_data['learningPath'])
        }
        
        if existing_diagnosis:
            # 更新现有记录
            for key, value in diagnosis_data.items():
                setattr(existing_diagnosis, key, value)
            existing_diagnosis.update_time = datetime.now()
            print(f"[诊断] 更新现有诊断记录: user={current_user_id}, lesson={lesson_id}")
        else:
            # 创建新记录
            diagnosis_id = f"diag{int(time.time())}{uuid.uuid4().hex[:6]}"
            new_diagnosis = LearningDiagnosis(
                diagnosis_id=diagnosis_id,
                user_id=str(current_user_id),
                lesson_id=lesson_id,
                **diagnosis_data
            )
            db.session.add(new_diagnosis)
            print(f"[诊断] 创建新诊断记录: diagnosis_id={diagnosis_id}")
        
        db.session.commit()
        print(f"[诊断] 诊断结果已保存到数据库")
    except Exception as e:
        print(f"[诊断] 保存诊断结果失败: {e}")
        db.session.rollback()
    
    return api_response(data=response_data)