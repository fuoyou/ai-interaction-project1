from extensions import db
from datetime import datetime
import pytz
import json

CNT = pytz.timezone('Asia/Shanghai')

class LearningProgress(db.Model):
    """学习进度表"""
    __tablename__ = 'biz_learning_progress'
    
    id = db.Column(db.Integer, primary_key=True)
    track_id = db.Column(db.String(100), unique=True, nullable=False)
    
    school_id = db.Column(db.String(50))
    user_id = db.Column(db.String(50), nullable=False)  # 学生学号
    course_id = db.Column(db.String(50))
    lesson_id = db.Column(db.String(100))
    
    current_section_id = db.Column(db.String(100))
    progress_percent = db.Column(db.Float, default=0.0)  # 当前章节进度 0-100
    total_progress = db.Column(db.Float, default=0.0)  # 智课总进度 0-100
    
    last_operate_time = db.Column(db.DateTime)
    last_qa_record_id = db.Column(db.String(100))
    
    next_section_suggest = db.Column(db.String(100))  # 建议后续学习章节
    
    create_time = db.Column(db.DateTime, default=lambda: datetime.now(CNT))
    update_time = db.Column(db.DateTime, default=lambda: datetime.now(CNT), onupdate=lambda: datetime.now(CNT))
    
    __table_args__ = (db.UniqueConstraint('user_id', 'lesson_id', name='_user_lesson_uc'),)
    
    def to_dict(self):
        return {
            'trackId': self.track_id,
            'userId': self.user_id,
            'courseId': self.course_id,
            'lessonId': self.lesson_id,
            'currentSectionId': self.current_section_id,
            'progressPercent': self.progress_percent,
            'totalProgress': self.total_progress,
            'nextSectionSuggest': self.next_section_suggest,
            'lastOperateTime': self.last_operate_time.strftime('%Y-%m-%d %H:%M:%S') if self.last_operate_time else None,
            'updateTime': self.update_time.strftime('%Y-%m-%d %H:%M:%S')
        }


class CheckpointAnswer(db.Model):
    """智能插旗考点答题记录表 - 记录每5页测验题的答题情况"""
    __tablename__ = 'biz_checkpoint_answer'
    
    id = db.Column(db.Integer, primary_key=True)
    
    user_id = db.Column(db.String(50), nullable=False)  # 学生ID
    lesson_id = db.Column(db.String(100), nullable=False)  # 课件ID
    checkpoint_id = db.Column(db.String(100), nullable=False)  # 考点ID
    page_num = db.Column(db.Integer, nullable=False)  # 页码
    
    # 答题信息
    question_text = db.Column(db.Text)  # 题目内容
    user_answer = db.Column(db.Text)  # 学生答案
    correct_answer = db.Column(db.Text)  # 正确答案
    is_correct = db.Column(db.Boolean, default=False)  # 是否正确
    
    # 时间戳
    submit_time = db.Column(db.DateTime, default=lambda: datetime.now(CNT))
    
    __table_args__ = (db.UniqueConstraint('user_id', 'lesson_id', 'checkpoint_id', name='_user_lesson_checkpoint_uc'),)
    
    def to_dict(self):
        return {
            'id': self.id,
            'userId': self.user_id,
            'lessonId': self.lesson_id,
            'checkpointId': self.checkpoint_id,
            'pageNum': self.page_num,
            'questionText': self.question_text,
            'userAnswer': self.user_answer,
            'correctAnswer': self.correct_answer,
            'isCorrect': self.is_correct,
            'submitTime': self.submit_time.strftime('%Y-%m-%d %H:%M:%S')
        }


class RhythmAdjustment(db.Model):
    """学习节奏调整记录表"""
    __tablename__ = 'biz_rhythm_adjustment'
    
    id = db.Column(db.Integer, primary_key=True)
    
    user_id = db.Column(db.String(50), nullable=False)
    lesson_id = db.Column(db.String(100), nullable=False)
    current_section_id = db.Column(db.String(100))
    
    understanding_level = db.Column(db.String(50))  # none, partial, full
    qa_record_id = db.Column(db.String(100))
    
    # 调整方案
    adjust_type = db.Column(db.String(50))  # supplement, accelerate, normal
    continue_section_id = db.Column(db.String(100))
    supplement_content = db.Column(db.Text)  # JSON: 补充讲解内容
    next_sections = db.Column(db.Text)  # JSON: 后续章节调整建议
    
    create_time = db.Column(db.DateTime, default=lambda: datetime.now(CNT))
    
    def to_dict(self):
        data = {
            'userId': self.user_id,
            'lessonId': self.lesson_id,
            'currentSectionId': self.current_section_id,
            'understandingLevel': self.understanding_level,
            'adjustType': self.adjust_type,
            'continueSectionId': self.continue_section_id,
            'createTime': self.create_time.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        try:
            if self.supplement_content:
                data['supplementContent'] = json.loads(self.supplement_content)
        except:
            data['supplementContent'] = {}
        
        try:
            if self.next_sections:
                data['nextSections'] = json.loads(self.next_sections)
        except:
            data['nextSections'] = []
        
        return data


class LearningDiagnosis(db.Model):
    """学习诊断记录表 - 保存AI诊断结果"""
    __tablename__ = 'biz_learning_diagnosis'
    
    id = db.Column(db.Integer, primary_key=True)
    diagnosis_id = db.Column(db.String(100), unique=True, nullable=False)
    
    user_id = db.Column(db.String(50), nullable=False)
    lesson_id = db.Column(db.String(100), nullable=False)
    
    # 诊断核心数据
    understanding_score = db.Column(db.Float, default=0.0)  # 理解度分数 0-100
    understanding_stats = db.Column(db.Text)  # JSON: {full: n, partial: n, none: n}
    
    # 答题统计
    quiz_stats = db.Column(db.Text)  # JSON: {total: n, correct: n, accuracy: n}
    
    # 诊断详情
    confused_sections = db.Column(db.Text)  # JSON: 困惑章节列表
    mastered_sections = db.Column(db.Text)  # JSON: 掌握章节列表
    suggestions = db.Column(db.Text)  # JSON: 学习建议列表
    weak_points = db.Column(db.Text)  # JSON: 薄弱知识点
    
    # AI诊断报告文本
    ai_diagnosis = db.Column(db.Text)
    
    # 问题类型统计
    question_types = db.Column(db.Text)  # JSON: {concept: n, reason: n, ...}
    
    # 学习路径建议
    learning_path = db.Column(db.Text)  # JSON: {priority, recommendation}
    
    create_time = db.Column(db.DateTime, default=lambda: datetime.now(CNT))
    update_time = db.Column(db.DateTime, default=lambda: datetime.now(CNT), onupdate=lambda: datetime.now(CNT))
    
    __table_args__ = (db.UniqueConstraint('user_id', 'lesson_id', name='_user_lesson_diagnosis_uc'),)
    
    def to_dict(self):
        data = {
            'diagnosisId': self.diagnosis_id,
            'userId': self.user_id,
            'lessonId': self.lesson_id,
            'understandingScore': self.understanding_score,
            'aiDiagnosis': self.ai_diagnosis,
            'createTime': self.create_time.strftime('%Y-%m-%d %H:%M:%S'),
            'updateTime': self.update_time.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # 解析JSON字段
        json_fields = ['understanding_stats', 'quiz_stats', 'confused_sections', 
                       'mastered_sections', 'suggestions', 'weak_points', 
                       'question_types', 'learning_path']
        
        for field in json_fields:
            value = getattr(self, field)
            if value:
                try:
                    data[field] = json.loads(value)
                except:
                    data[field] = value
            else:
                data[field] = {} if field in ['understanding_stats', 'quiz_stats', 'question_types', 'learning_path'] else []
        
        return data
