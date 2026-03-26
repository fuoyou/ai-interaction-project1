from extensions import db
from datetime import datetime
import pytz
import json

CNT = pytz.timezone('Asia/Shanghai')

class QASession(db.Model):
    """问答会话表 - 支持多轮交互"""
    __tablename__ = 'biz_qa_session'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(100), unique=True, nullable=False)
    
    school_id = db.Column(db.String(50))
    user_id = db.Column(db.String(50), nullable=False)  # 学生学号
    course_id = db.Column(db.String(50))
    lesson_id = db.Column(db.String(100))
    
    current_section_id = db.Column(db.String(100))
    
    create_time = db.Column(db.DateTime, default=lambda: datetime.now(CNT))
    update_time = db.Column(db.DateTime, default=lambda: datetime.now(CNT), onupdate=lambda: datetime.now(CNT))
    
    def to_dict(self):
        return {
            'sessionId': self.session_id,
            'userId': self.user_id,
            'courseId': self.course_id,
            'lessonId': self.lesson_id,
            'currentSectionId': self.current_section_id
        }


class QARecord(db.Model):
    """问答记录表"""
    __tablename__ = 'biz_qa_record'
    
    id = db.Column(db.Integer, primary_key=True)
    answer_id = db.Column(db.String(100), unique=True, nullable=False)
    session_id = db.Column(db.String(100), db.ForeignKey('biz_qa_session.session_id'), nullable=False)
    
    question_type = db.Column(db.String(20))  # text, voice
    question_content = db.Column(db.Text, nullable=False)
    question_voice_url = db.Column(db.String(500))
    
    answer_content = db.Column(db.Text, nullable=False)
    answer_type = db.Column(db.String(20), default='text')  # text, mixed
    answer_audio_url = db.Column(db.String(500))
    
    # 关联知识点
    related_knowledge_id = db.Column(db.String(100))
    related_knowledge_name = db.Column(db.String(255))
    related_section_id = db.Column(db.String(100))
    
    # 理解程度评估
    understanding_level = db.Column(db.String(50))  # none, partial, full
    
    suggestions = db.Column(db.Text)  # JSON数组：追问建议
    
    create_time = db.Column(db.DateTime, default=lambda: datetime.now(CNT))
    
    def to_dict(self):
        data = {
            'answerId': self.answer_id,
            'questionType': self.question_type,
            'questionContent': self.question_content,
            'answerContent': self.answer_content,
            'answerType': self.answer_type,
            'understandingLevel': self.understanding_level,
            'createTime': self.create_time.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        if self.answer_audio_url:
            data['audioUrl'] = self.answer_audio_url
        
        if self.related_knowledge_id:
            data['relatedKnowledge'] = {
                'knowledgeId': self.related_knowledge_id,
                'knowledgeName': self.related_knowledge_name,
                'relatedSectionId': self.related_section_id
            }
        
        try:
            if self.suggestions:
                data['suggestions'] = json.loads(self.suggestions)
        except:
            data['suggestions'] = []
        
        return data
