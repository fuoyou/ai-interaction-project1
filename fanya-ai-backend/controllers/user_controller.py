from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required
from models.user import User
from extensions import db

user_bp = Blueprint('user', __name__)

@user_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    role = data.get('role')
    
    user = User.query.filter_by(username=username, role=role).first()
    if not user:
        return jsonify(code='401', msg='账号或密码错误'), 401
    

    if not User.verify_hash(password, user.password):
        return jsonify(code='401', msg='账号或密码错误'), 401

    
    access_token = create_access_token(identity=user.id)
    return jsonify(code='200', data={
        'token': access_token,
        'role': user.role,
        'nickname': user.nickname,
        'username': user.username,
        'avatar': user.avatar
    })

@user_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    role = data.get('role')
    nickname = data.get('nickname')
    college = data.get('college')
    major = data.get('major')
    
    existing_user = User.query.filter_by(username=username).first()
    if existing_user:
        return jsonify(code='400', msg='账号已存在'), 400
    
    new_user = User(
        username=username,
        password=User.generate_hash(password),
        role=role,
        nickname=nickname,
        college=college,
        major=major
    )
    db.session.add(new_user)
    db.session.commit()
    
    return jsonify(code='200', msg='注册成功')

@user_bp.route('/update', methods=['PUT'])
@jwt_required()
def update_user():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    if not user:
        return jsonify(code='404', msg='用户不存在'), 404
    
    data = request.get_json()
    user.nickname = data.get('nickname', user.nickname)
    user.avatar = data.get('avatar', user.avatar)
    
    db.session.commit()
    return jsonify(code='200', msg='更新成功')