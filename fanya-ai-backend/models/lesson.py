from extensions import db
from datetime import datetime
import pytz
import json
from sqlalchemy import Text
from sqlalchemy.dialects.mysql import LONGTEXT

CNT = pytz.timezone('Asia/Shanghai')

class Lesson(db.Model):
    """智课课件表 - 对应API文档的课件解析与智课生成"""
    __tablename__ = 'biz_lesson'
    
    id = db.Column(db.Integer, primary_key=True)
    parse_id = db.Column(db.String(100), unique=True, nullable=False)  # 解析任务ID
    
    # 基础信息
    school_id = db.Column(db.String(50))
    user_id = db.Column(db.String(50))  # 教师工号
    course_id = db.Column(db.String(50))  # 课程ID
    
    # 文件信息
    file_name = db.Column(db.String(255), nullable=False)
    file_url = db.Column(db.String(500), nullable=False)
    file_type = db.Column(db.String(20))  # ppt, pdf
    file_size = db.Column(db.Integer, default=0)
    page_count = db.Column(db.Integer, default=0)
    
    # 解析结果（含 paddlePages，大课件易超 64KB，MySQL 须 LONGTEXT）
    structure_data = db.Column(Text().with_variant(LONGTEXT, "mysql"))
    rag_chunks = db.Column(Text().with_variant(LONGTEXT, "mysql"))  # JSON: RAG 切片
    
    # 脚本信息
    script_id = db.Column(db.String(100))
    teaching_style = db.Column(db.String(50), default='standard')  # standard, detailed, concise
    speech_speed = db.Column(db.String(50), default='normal')  # slow, normal, fast
    script_content = db.Column(db.Text)  # JSON: 结构化脚本
    
    # 音频信息
    audio_id = db.Column(db.String(100))
    audio_url = db.Column(db.String(500))
    audio_sections = db.Column(db.Text)  # JSON: 分章节音频
    
    # 智能插旗考点 (来自第一份代码)
    checkpoints = db.Column(db.Text)  # JSON: 考点和题目
    
    # 可视化数据 (来自第二份代码)
    mindmap_data = db.Column(db.Text)  # JSON: 思维导图数据
    knowledge_graph_data = db.Column(db.Text)  # JSON: 知识图谱数据
    
    # 状态管理
    task_status = db.Column(db.String(50), default='processing')  # processing, completed, failed
    
    # 时间戳
    create_time = db.Column(db.DateTime, default=lambda: datetime.now(CNT))
    update_time = db.Column(db.DateTime, default=lambda: datetime.now(CNT), onupdate=lambda: datetime.now(CNT))
    
    def to_dict(self, include_detail=True):
        """转换为字典格式"""
        # 状态映射：processing=1, converting_pdf/paddle_parsing/generating_script=1, completed=3, failed=9
        status_map = {
            'processing': 1,
            'converting_pdf': 1,
            'paddle_parsing': 1,
            'generating_script': 1,  # 生成讲稿中也是处理中状态
            'completed': 3,
            'failed': 9,
            'regen_failed': 9,
        }
        
        data = {
            'id': self.id,
            'parseId': self.parse_id,
            'schoolId': self.school_id,
            'userId': self.user_id,
            'courseId': self.course_id,
            'courseName': self.file_name,  # 前端期望的字段
            'fileUrl': self.file_url,  # 前端需要这个字段
            'fileInfo': {
                'fileName': self.file_name,
                'fileSize': self.file_size,
                'pageCount': self.page_count
            },
            'taskStatus': self.task_status,
            'status': status_map.get(self.task_status, 1),  # 前端期望的数字状态
            'createTime': self.create_time.strftime('%Y-%m-%d %H:%M:%S'),
            'updateTime': self.update_time.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        if include_detail:
            # 解析JSON字段
            try:
                if self.structure_data:
                    sp = json.loads(self.structure_data)
                    data['structurePreview'] = sp
                    data['paddlePages'] = sp.get('paddlePages') if isinstance(sp, dict) else []
                    data['parseError'] = sp.get('parseError') if isinstance(sp, dict) else None
                else:
                    data['structurePreview'] = {'chapters': []}
                    data['paddlePages'] = []
                    data['parseError'] = None
            except Exception:
                data['structurePreview'] = {'chapters': []}
                data['paddlePages'] = []
                data['parseError'] = None
            
            # 前端期望的 aiScript 字段
            try:
                if self.script_content:
                    script_data = json.loads(self.script_content)
                    data['scriptStructure'] = script_data
                    data['aiScript'] = script_data  # 前端期望的字段
                    data['scriptId'] = self.script_id
                else:
                    data['aiScript'] = []
            except:
                data['scriptStructure'] = []
                data['aiScript'] = []
            
            # 前端期望的 audioScript 字段
            try:
                if self.audio_sections:
                    audio_data = json.loads(self.audio_sections)
                    data['audioInfo'] = audio_data
                    data['audioScript'] = audio_data.get('sectionAudios', [])  # 前端期望的字段
                    data['audioUrl'] = self.audio_url
                    data['audioId'] = self.audio_id
                else:
                    data['audioScript'] = []
            except:
                data['audioInfo'] = {}
                data['audioScript'] = []
            
            # 智能插旗考点 (整合自第一份代码)
            try:
                if self.checkpoints:
                    data['checkpoints'] = json.loads(self.checkpoints)
                else:
                    data['checkpoints'] = []
            except:
                data['checkpoints'] = []
                
            # 思维导图数据 (整合自第二份代码)
            try:
                if self.mindmap_data:
                    data['mindmapData'] = json.loads(self.mindmap_data)
                else:
                    data['mindmapData'] = None
            except:
                data['mindmapData'] = None
            
            # 知识图谱数据 (整合自第二份代码)
            try:
                if self.knowledge_graph_data:
                    data['knowledgeGraphData'] = json.loads(self.knowledge_graph_data)
                else:
                    data['knowledgeGraphData'] = None
            except:
                data['knowledgeGraphData'] = None
        
        return data


class ScriptSection(db.Model):
    """脚本章节表 - 存储结构化讲授脚本"""
    __tablename__ = 'biz_script_section'
    
    id = db.Column(db.Integer, primary_key=True)
    lesson_id = db.Column(db.Integer, db.ForeignKey('biz_lesson.id'), nullable=False)
    script_id = db.Column(db.String(100), nullable=False)
    
    section_id = db.Column(db.String(100), nullable=False)
    section_name = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    duration = db.Column(db.Integer, default=0)  # 预计讲授时长（秒）
    
    related_chapter_id = db.Column(db.String(100))
    related_page = db.Column(db.String(50))
    key_points = db.Column(db.Text)  # JSON数组
    
    audio_url = db.Column(db.String(500))
    
    sort_order = db.Column(db.Integer, default=0)
    create_time = db.Column(db.DateTime, default=lambda: datetime.now(CNT))
    
    def to_dict(self):
        data = {
            'sectionId': self.section_id,
            'sectionName': self.section_name,
            'content': self.content,
            'duration': self.duration,
            'relatedChapterId': self.related_chapter_id,
            'relatedPage': self.related_page,
            'audioUrl': self.audio_url
        }
        
        try:
            if self.key_points:
                data['keyPoints'] = json.loads(self.key_points)
        except:
            data['keyPoints'] = []
        
        return data