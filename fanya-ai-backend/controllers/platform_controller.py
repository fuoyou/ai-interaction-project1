from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from models.platform import Platform, ExternalCourse, ExternalUser
from models.user import User
from extensions import db
import uuid
import json
import time
from datetime import datetime, timedelta

from utils.api_utils import verify_signature, api_response

platform_bp = Blueprint('platform', __name__)

# ==================== 3.1 课程信息同步接口 ====================
@platform_bp.route('/syncCourse', methods=['POST'])
@verify_signature
def sync_course():
    """
    接口功能：与外部教育平台同步课程基础信息，支持智课关联课程体系
    接口地址：/api/v1/platform/syncCourse
    请求方法：POST
    """
    data = request.get_json()
    
    platform_id = data.get('platformId')
    course_info = data.get('courseInfo')
    
    if not platform_id or not course_info:
        return api_response(code=400, msg='platformId和courseInfo不能为空')
    
    # 验证平台是否已注册
    platform = Platform.query.filter_by(platform_id=platform_id).first()
    if not platform:
        return api_response(code=404, msg='平台未注册，请先注册平台信息')
    
    if platform.status != 1:
        return api_response(code=403, msg='平台已被禁用')
    
    # 提取课程信息
    external_course_id = course_info.get('courseId')
    course_name = course_info.get('courseName')
    school_id = course_info.get('schoolId')
    school_name = course_info.get('schoolName')
    teacher_info = course_info.get('teacherInfo', [])
    term = course_info.get('term')
    credit = course_info.get('credit')
    period = course_info.get('period')
    course_cover = course_info.get('courseCover')
    
    if not external_course_id or not course_name:
        return api_response(code=400, msg='课程ID和课程名称不能为空')
    
    # 查找或创建课程映射
    external_course = ExternalCourse.query.filter_by(
        platform_id=platform_id,
        external_course_id=external_course_id
    ).first()
    
    if external_course:
        # 更新现有课程
        external_course.course_name = course_name
        external_course.school_id = school_id
        external_course.school_name = school_name
        external_course.term = term
        external_course.credit = credit
        external_course.period = period
        external_course.course_cover = course_cover
        external_course.teacher_info = json.dumps(teacher_info, ensure_ascii=False)
        external_course.sync_status = 'success'
        external_course.sync_time = datetime.now()
        
        internal_course_id = external_course.internal_course_id
    else:
        # 创建新课程映射
        internal_course_id = f"cou{int(time.time())}{uuid.uuid4().hex[:6]}"
        
        external_course = ExternalCourse(
            platform_id=platform_id,
            external_course_id=external_course_id,
            internal_course_id=internal_course_id,
            course_name=course_name,
            school_id=school_id,
            school_name=school_name,
            term=term,
            credit=credit,
            period=period,
            course_cover=course_cover,
            teacher_info=json.dumps(teacher_info, ensure_ascii=False),
            sync_status='success'
        )
        db.session.add(external_course)
    
    db.session.commit()
    
    return api_response(data={
        'internalCourseId': internal_course_id,
        'syncStatus': 'success',
        'syncTime': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }, msg='课程同步成功')


# ==================== 3.2 用户信息同步接口 ====================
@platform_bp.route('/syncUser', methods=['POST'])
@verify_signature
def sync_user():
    """
    接口功能：同步外部平台用户信息（教师/学生），支持权限校验与身份识别
    接口地址：/api/v1/platform/syncUser
    请求方法：POST
    """
    data = request.get_json()
    
    platform_id = data.get('platformId')
    user_info = data.get('userInfo')
    
    if not platform_id or not user_info:
        return api_response(code=400, msg='platformId和userInfo不能为空')
    
    # 验证平台是否已注册
    platform = Platform.query.filter_by(platform_id=platform_id).first()
    if not platform:
        return api_response(code=404, msg='平台未注册，请先注册平台信息')
    
    if platform.status != 1:
        return api_response(code=403, msg='平台已被禁用')
    
    # 提取用户信息
    external_user_id = user_info.get('userId')
    user_name = user_info.get('userName')
    role = user_info.get('role')
    school_id = user_info.get('schoolId')
    related_course_ids = user_info.get('relatedCourseIds', [])
    contact_info = user_info.get('contactInfo', {})
    
    if not external_user_id or not user_name or not role:
        return api_response(code=400, msg='用户ID、用户名和角色不能为空')
    
    if role not in ['student', 'teacher']:
        return api_response(code=400, msg='角色必须是student或teacher')
    
    # 查找或创建用户映射
    external_user = ExternalUser.query.filter_by(
        platform_id=platform_id,
        external_user_id=external_user_id
    ).first()
    
    if external_user:
        # 更新现有用户
        external_user.user_name = user_name
        external_user.role = role
        external_user.school_id = school_id
        external_user.related_course_ids = json.dumps(related_course_ids, ensure_ascii=False)
        external_user.contact_info = json.dumps(contact_info, ensure_ascii=False)
        external_user.sync_status = 'success'
        external_user.sync_time = datetime.now()
        
        internal_user_id = external_user.internal_user_id
        auth_token = external_user.auth_token
    else:
        # 创建新用户映射
        internal_user_id = f"{role[:3]}{int(time.time())}{uuid.uuid4().hex[:6]}"
        
        # 生成认证令牌（简化版，实际应该使用JWT）
        from flask_jwt_extended import create_access_token
        
        # 检查内部系统是否已有该用户
        internal_user = User.query.filter_by(username=external_user_id).first()
        if not internal_user:
            # 创建内部用户
            internal_user = User(
                username=external_user_id,
                password=User.generate_hash(str(uuid.uuid4())),  # 随机密码
                role=role,
                nickname=user_name,
                college=school_id
            )
            db.session.add(internal_user)
            db.session.flush()
            
            internal_user_id = str(internal_user.id)
        else:
            internal_user_id = str(internal_user.id)
        
        # 生成JWT令牌
        auth_token = create_access_token(identity=internal_user_id)
        token_expire_time = datetime.now() + timedelta(days=30)
        
        external_user = ExternalUser(
            platform_id=platform_id,
            external_user_id=external_user_id,
            internal_user_id=internal_user_id,
            user_name=user_name,
            role=role,
            school_id=school_id,
            related_course_ids=json.dumps(related_course_ids, ensure_ascii=False),
            contact_info=json.dumps(contact_info, ensure_ascii=False),
            auth_token=auth_token,
            token_expire_time=token_expire_time,
            sync_status='success'
        )
        db.session.add(external_user)
    
    db.session.commit()
    
    return api_response(data={
        'internalUserId': internal_user_id,
        'syncStatus': 'success',
        'authToken': auth_token
    }, msg='用户同步成功')


# ==================== 平台管理接口（额外提供） ====================
@platform_bp.route('/register', methods=['POST'])
@jwt_required()
def register_platform():
    """
    平台注册接口（管理员使用）
    用于注册新的外部平台
    """
    data = request.get_json()
    
    platform_id = data.get('platformId')
    platform_name = data.get('platformName')
    platform_type = data.get('platformType', '教育平台')
    
    if not platform_id or not platform_name:
        return api_response(code=400, msg='platformId和platformName不能为空')
    
    # 检查平台是否已存在
    existing = Platform.query.filter_by(platform_id=platform_id).first()
    if existing:
        return api_response(code=400, msg='平台ID已存在')
    
    # 生成API密钥
    api_key = uuid.uuid4().hex
    
    platform = Platform(
        platform_id=platform_id,
        platform_name=platform_name,
        platform_type=platform_type,
        api_key=api_key,
        status=1
    )
    db.session.add(platform)
    db.session.commit()
    
    return api_response(data={
        'platformId': platform_id,
        'apiKey': api_key,
        'status': 'active'
    }, msg='平台注册成功')


@platform_bp.route('/list', methods=['GET'])
@jwt_required()
def list_platforms():
    """获取平台列表"""
    platforms = Platform.query.all()
    return api_response(data=[p.to_dict() for p in platforms])


@platform_bp.route('/courses/<platform_id>', methods=['GET'])
@jwt_required()
def list_platform_courses(platform_id):
    """获取平台课程列表"""
    courses = ExternalCourse.query.filter_by(platform_id=platform_id).all()
    return api_response(data=[c.to_dict() for c in courses])


@platform_bp.route('/users/<platform_id>', methods=['GET'])
@jwt_required()
def list_platform_users(platform_id):
    """获取平台用户列表"""
    users = ExternalUser.query.filter_by(platform_id=platform_id).all()
    return api_response(data=[u.to_dict() for u in users])
