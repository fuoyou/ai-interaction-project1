from extensions import db
from datetime import datetime
import pytz

CNT = pytz.timezone('Asia/Shanghai')

class Platform(db.Model):
    """外部平台信息表"""
    __tablename__ = 'sys_platform'
    
    id = db.Column(db.Integer, primary_key=True)
    platform_id = db.Column(db.String(50), unique=True, nullable=False)
    platform_name = db.Column(db.String(100), nullable=False)
    platform_type = db.Column(db.String(50))  # 平台类型：教务系统、MOOC平台等
    
    api_key = db.Column(db.String(255))  # 对接密钥
    status = db.Column(db.Integer, default=1)  # 1: 启用, 0: 禁用
    
    create_time = db.Column(db.DateTime, default=lambda: datetime.now(CNT))
    update_time = db.Column(db.DateTime, default=lambda: datetime.now(CNT), onupdate=lambda: datetime.now(CNT))
    
    def to_dict(self):
        return {
            'platformId': self.platform_id,
            'platformName': self.platform_name,
            'platformType': self.platform_type,
            'status': self.status,
            'createTime': self.create_time.strftime('%Y-%m-%d %H:%M:%S')
        }


class ExternalCourse(db.Model):
    """外部平台课程映射表"""
    __tablename__ = 'biz_external_course'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # 外部平台信息
    platform_id = db.Column(db.String(50), db.ForeignKey('sys_platform.platform_id'), nullable=False)
    external_course_id = db.Column(db.String(100), nullable=False)  # 外部平台课程ID
    
    # 内部系统映射
    internal_course_id = db.Column(db.String(50), nullable=False)  # 系统内部课程ID
    
    # 课程基本信息
    course_name = db.Column(db.String(255), nullable=False)
    school_id = db.Column(db.String(50))
    school_name = db.Column(db.String(100))
    term = db.Column(db.String(20))
    credit = db.Column(db.Float)
    period = db.Column(db.Integer)
    course_cover = db.Column(db.String(500))
    
    # 教师信息（JSON格式）
    teacher_info = db.Column(db.Text)
    
    # 同步状态
    sync_status = db.Column(db.String(50), default='success')  # success, failed, pending
    sync_time = db.Column(db.DateTime, default=lambda: datetime.now(CNT))
    
    create_time = db.Column(db.DateTime, default=lambda: datetime.now(CNT))
    update_time = db.Column(db.DateTime, default=lambda: datetime.now(CNT), onupdate=lambda: datetime.now(CNT))
    
    __table_args__ = (db.UniqueConstraint('platform_id', 'external_course_id', name='_platform_course_uc'),)
    
    def to_dict(self):
        import json
        teacher_list = []
        try:
            if self.teacher_info:
                teacher_list = json.loads(self.teacher_info)
        except:
            pass
        
        return {
            'platformId': self.platform_id,
            'externalCourseId': self.external_course_id,
            'internalCourseId': self.internal_course_id,
            'courseName': self.course_name,
            'schoolId': self.school_id,
            'schoolName': self.school_name,
            'term': self.term,
            'credit': self.credit,
            'period': self.period,
            'courseCover': self.course_cover,
            'teacherInfo': teacher_list,
            'syncStatus': self.sync_status,
            'syncTime': self.sync_time.strftime('%Y-%m-%d %H:%M:%S')
        }


class ExternalUser(db.Model):
    """外部平台用户映射表"""
    __tablename__ = 'biz_external_user'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # 外部平台信息
    platform_id = db.Column(db.String(50), db.ForeignKey('sys_platform.platform_id'), nullable=False)
    external_user_id = db.Column(db.String(100), nullable=False)  # 外部平台用户ID
    
    # 内部系统映射
    internal_user_id = db.Column(db.String(50), nullable=False)  # 系统内部用户ID
    
    # 用户基本信息
    user_name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # student, teacher
    school_id = db.Column(db.String(50))
    
    # 关联课程（JSON数组）
    related_course_ids = db.Column(db.Text)
    
    # 联系方式（JSON格式）
    contact_info = db.Column(db.Text)
    
    # 认证令牌
    auth_token = db.Column(db.String(500))
    token_expire_time = db.Column(db.DateTime)
    
    # 同步状态
    sync_status = db.Column(db.String(50), default='success')
    sync_time = db.Column(db.DateTime, default=lambda: datetime.now(CNT))
    
    create_time = db.Column(db.DateTime, default=lambda: datetime.now(CNT))
    update_time = db.Column(db.DateTime, default=lambda: datetime.now(CNT), onupdate=lambda: datetime.now(CNT))
    
    __table_args__ = (db.UniqueConstraint('platform_id', 'external_user_id', name='_platform_user_uc'),)
    
    def to_dict(self):
        import json
        course_list = []
        contact = {}
        
        try:
            if self.related_course_ids:
                course_list = json.loads(self.related_course_ids)
        except:
            pass
        
        try:
            if self.contact_info:
                contact = json.loads(self.contact_info)
        except:
            pass
        
        return {
            'platformId': self.platform_id,
            'externalUserId': self.external_user_id,
            'internalUserId': self.internal_user_id,
            'userName': self.user_name,
            'role': self.role,
            'schoolId': self.school_id,
            'relatedCourseIds': course_list,
            'contactInfo': contact,
            'syncStatus': self.sync_status,
            'syncTime': self.sync_time.strftime('%Y-%m-%d %H:%M:%S')
        }
