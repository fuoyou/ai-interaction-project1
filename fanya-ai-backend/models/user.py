from extensions import db
from passlib.hash import pbkdf2_sha256 as sha256

class User(db.Model):
    __tablename__ = 'sys_user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # teacher/student
    nickname = db.Column(db.String(50))
    avatar = db.Column(db.String(255))
    college = db.Column(db.String(100))
    major = db.Column(db.String(100))
    status = db.Column(db.Integer, default=1)  # 1: 正常, 0: 禁用
    
    @staticmethod
    def generate_hash(password):
        return sha256.hash(password)
    
    @staticmethod
    def verify_hash(password, hash):
        try:
            return sha256.verify(password, hash)
        except ValueError:
            # 如果哈希值无效，返回False
            return False