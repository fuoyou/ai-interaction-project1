from extensions import db
from datetime import datetime

import pytz

CNT = pytz.timezone('Asia/Shanghai')

class LearningProgress(db.Model):
    __tablename__ = 'biz_student_progress'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('sys_user.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('biz_course_ware.id'), nullable=False)
    current_page = db.Column(db.Integer, default=1)
    max_page = db.Column(db.Integer, default=1)
    mastery_degree = db.Column(db.Integer, default=0)  # 掌握程度 0-100
    status = db.Column(db.String(20), default='ongoing')  # ongoing, completed
    update_time = db.Column(db.DateTime, default=lambda: datetime.now(CNT), onupdate=lambda: datetime.now(CNT))
    
    __table_args__ = (db.UniqueConstraint('student_id', 'course_id', name='_student_course_uc'),)

class LearningHistory(db.Model):
    __tablename__ = 'biz_rhythm_log'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('sys_user.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('biz_course_ware.id'), nullable=False)
    page_num = db.Column(db.Integer, nullable=False)
    question = db.Column(db.Text, nullable=False)
    ai_reply = db.Column(db.Text, nullable=False)
    audio_file = db.Column(db.String(255))  # 存储服务器生成的 TTS 音频文件名
    action = db.Column(db.String(50))  # EXPLAIN_MORE, ROLLBACK, CONTINUE
    knowledge_point = db.Column(db.String(255))
    target_page = db.Column(db.Integer)
    create_time = db.Column(db.DateTime, default=lambda: datetime.now(CNT))