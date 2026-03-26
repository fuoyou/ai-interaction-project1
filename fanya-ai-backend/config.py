import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'mysql+pymysql://root:123456@localhost:3306/ai_course_db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # 降低「Packet sequence number wrong」：避免复用已断开的连接；解析线程与 HTTP 轮询并发时更稳
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 280,
    }
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'dev-jwt-secret-key'
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER') or 'uploads'
    MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100MB
    D_ID_API_KEY = 'eDM3NTY0Nzk2QGdtYWlsLmNvbQ:Q8_TOJDnnbq6fB6hcWi22'
    D_ID_BASE_URL = 'https://api.d-id.com'
    
    # SadTalker 本地服务器配置
    SADTALKER_BASE_URL = os.environ.get('SADTALKER_BASE_URL') or 'http://localhost:6007'