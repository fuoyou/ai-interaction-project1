from extensions import db
from datetime import datetime
import pytz

# 设置时区为中国东8区
CNT = pytz.timezone('Asia/Shanghai')

class Course(db.Model):
    __tablename__ = 'biz_course_ware'
    id = db.Column(db.Integer, primary_key=True)
    course_name = db.Column(db.String(255), nullable=False)
    file_url = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(50))
    ai_script = db.Column(db.Text)
    audio_script = db.Column(db.Text)
    status = db.Column(db.Integer, default=0)  # 0: pending, 1: processing, 3: completed, 9: failed
    create_time = db.Column(db.DateTime, default=lambda: datetime.now(CNT))
    update_time = db.Column(db.DateTime, default=lambda: datetime.now(CNT), onupdate=lambda: datetime.now(CNT))
    create_by = db.Column(db.Integer, db.ForeignKey('sys_user.id'), nullable=False)
    teacher = db.relationship('User', backref=db.backref('courses', lazy=True))


    # 新增：将重复的解析逻辑封装在模型内部，去掉 Controller 里的冗余
    def to_dict(self):
        ai_script = []
        audio_script =[]
        try:
            if self.ai_script:
                ai_script = json.loads(self.ai_script) # 替换 eval
            if self.audio_script:
                audio_script = json.loads(self.audio_script) # 替换 eval
        except Exception as e:
            print(f"解析讲稿数据失败: {e}")
            
        return {
            'id': self.id,
            'courseName': self.course_name,
            'fileUrl': self.file_url if self.file_url else '',
            'status': self.status,
            'aiScript': ai_script,
            'audioScript': audio_script,
            'createBy': self.create_by,
            'createTime': self.create_time.strftime('%Y-%m-%d %H:%M:%S'),
            'updateTime': self.update_time.strftime('%Y-%m-%d %H:%M:%S')
        }