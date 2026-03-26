from extensions import db
from datetime import datetime
import pytz
import json

CNT = pytz.timezone('Asia/Shanghai')

class Quiz(db.Model):
    """测验题库表"""
    __tablename__ = 'biz_quiz'
    
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.String(100), unique=True, nullable=False)
    lesson_id = db.Column(db.Integer, db.ForeignKey('biz_lesson.id'), nullable=False)
    
    # 题目信息
    question_type = db.Column(db.String(20), nullable=False)  # single_choice, multiple_choice, true_false, calculation, application
    question_text = db.Column(db.Text, nullable=False)
    options = db.Column(db.Text)  # JSON: 选项列表（单选、多选用）
    correct_answer = db.Column(db.Text, nullable=False)  # 正确答案
    explanation = db.Column(db.Text)  # 解析
    
    # 元数据
    difficulty = db.Column(db.String(20), default='medium')  # easy, medium, hard
    points = db.Column(db.Integer, default=5)  # 分值
    sort_order = db.Column(db.Integer, default=0)
    
    # 来源标记
    source = db.Column(db.String(20), default='ai')  # ai=AI生成, manual=老师手动添加
    
    # 时间戳
    create_time = db.Column(db.DateTime, default=lambda: datetime.now(CNT))
    update_time = db.Column(db.DateTime, default=lambda: datetime.now(CNT), onupdate=lambda: datetime.now(CNT))
    
    def to_dict(self):
        data = {
            'id': self.id,
            'quizId': self.quiz_id,
            'lessonId': self.lesson_id,
            'questionType': self.question_type,
            'questionText': self.question_text,
            'correctAnswer': self.correct_answer,
            'explanation': self.explanation,
            'difficulty': self.difficulty,
            'points': self.points,
            'sortOrder': self.sort_order,
            'source': self.source,
            'createTime': self.create_time.strftime('%Y-%m-%d %H:%M:%S'),
            'updateTime': self.update_time.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # 解析选项
        try:
            if self.options:
                data['options'] = json.loads(self.options)
            else:
                data['options'] = []
        except:
            data['options'] = []
        
        return data


class QuizAnswer(db.Model):
    """学生答题记录表（单题粒度）"""
    __tablename__ = 'biz_quiz_answer'
    
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.String(100), nullable=False)
    lesson_id = db.Column(db.Integer, nullable=False)
    user_id = db.Column(db.String(50), nullable=False)  # 学生ID
    
    # 答题信息
    student_answer = db.Column(db.Text)  # 学生答案
    is_correct = db.Column(db.Boolean, default=False)  # 是否正确
    score = db.Column(db.Integer, default=0)  # 得分
    
    # 时间戳
    submit_time = db.Column(db.DateTime, default=lambda: datetime.now(CNT))
    
    def to_dict(self):
        return {
            'id': self.id,
            'quizId': self.quiz_id,
            'lessonId': self.lesson_id,
            'userId': self.user_id,
            'studentAnswer': self.student_answer,
            'isCorrect': self.is_correct,
            'score': self.score,
            'submitTime': self.submit_time.strftime('%Y-%m-%d %H:%M:%S')
        }


class QuizAttempt(db.Model):
    """学生测验尝试记录表（每次提交答卷生成一条综合记录）"""
    __tablename__ = 'biz_quiz_attempt'
    
    id = db.Column(db.Integer, primary_key=True)
    attempt_id = db.Column(db.String(100), unique=True, nullable=False)  # 尝试ID
    lesson_id = db.Column(db.Integer, nullable=False)
    user_id = db.Column(db.String(50), nullable=False)
    
    # 答题结果统计
    total_score = db.Column(db.Integer, default=0)  # 总得分（百分制）
    correct_count = db.Column(db.Integer, default=0)  # 答对题数
    wrong_count = db.Column(db.Integer, default=0)  # 答错题数
    total_questions = db.Column(db.Integer, default=0)  # 总题数
    
    # 详细答案（JSON格式）
    answers_detail = db.Column(db.Text)  # 存储所有题目的答题详情
    
    # 时间戳
    submit_time = db.Column(db.DateTime, default=lambda: datetime.now(CNT))
    
    def to_dict(self):
        return {
            'id': self.id,
            'attemptId': self.attempt_id,
            'lessonId': self.lesson_id,
            'userId': self.user_id,
            'totalScore': self.total_score,
            'correctCount': self.correct_count,
            'wrongCount': self.wrong_count,
            'totalQuestions': self.total_questions,
            'answersDetail': json.loads(self.answers_detail) if self.answers_detail else [],
            'submitTime': self.submit_time.strftime('%Y-%m-%d %H:%M:%S')
        }