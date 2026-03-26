from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from extensions import db
from sqlalchemy import text
from utils.api_utils import api_response
from datetime import datetime
import pytz
import uuid

category_bp = Blueprint('category', __name__)
CNT = pytz.timezone('Asia/Shanghai')


@category_bp.route('/create', methods=['POST'])
@jwt_required()
def create_category():
    """创建分类"""
    try:
        current_user_id = get_jwt_identity()
        data = request.get_json()
        name = data.get('name', '').strip()
        description = data.get('description', '').strip()

        if not name:
            return api_response(code=400, msg='分类名称不能为空')

        now = datetime.now(CNT)
        print(f'[分类] 创建: user_id={current_user_id}, name={name}')

        sql = text("""
            INSERT INTO biz_category (user_id, name, description, create_time, update_time)
            VALUES (:user_id, :name, :description, :create_time, :update_time)
        """)
        result = db.session.execute(sql, {
            'user_id': int(current_user_id),
            'name': name,
            'description': description,
            'create_time': now,
            'update_time': now
        })
        db.session.commit()
        
        # 获取刚插入的自增ID
        category_id = result.lastrowid
        print(f'[分类] 创建成功: id={category_id}')

        return api_response(code=200, msg='分类创建成功', data={
            'id': category_id,
            'name': name,
            'description': description
        })
    except Exception as e:
        db.session.rollback()
        print(f'[分类] 创建失败: {e}')
        return api_response(code=500, msg=f'创建分类失败: {str(e)}')


@category_bp.route('/list', methods=['GET'])
@jwt_required()
def list_categories():
    """获取当前用户的所有分类"""
    try:
        current_user_id = get_jwt_identity()
        print(f'[分类] 获取列表: user_id={current_user_id}')
        sql = text("""
            SELECT id, name, description, create_time
            FROM biz_category
            WHERE user_id = :user_id
            ORDER BY create_time DESC
        """)
        result = db.session.execute(sql, {'user_id': int(current_user_id)}).fetchall()
        categories = [
            {
                'id': row[0],
                'name': row[1],
                'description': row[2] or '',
                'create_time': row[3].isoformat() if row[3] else None
            }
            for row in result
        ]
        return api_response(code=200, msg='获取成功', data=categories)
    except Exception as e:
        print(f'[分类] 列表查询失败: {e}')
        return api_response(code=500, msg=f'获取分类列表失败: {str(e)}')


@category_bp.route('/listAll', methods=['GET'])
@jwt_required()
def list_all_categories():
    """获取所有分类（包括老师创建的）- 供学生端使用"""
    try:
        current_user_id = get_jwt_identity()
        print(f'[分类] 获取所有列表: user_id={current_user_id}')
        sql = text("""
            SELECT id, name, description, create_time, user_id
            FROM biz_category
            ORDER BY create_time DESC
        """)
        result = db.session.execute(sql).fetchall()
        categories = [
            {
                'id': row[0],
                'name': row[1],
                'description': row[2] or '',
                'create_time': row[3].isoformat() if row[3] else None,
                'user_id': row[4]
            }
            for row in result
        ]
        return api_response(code=200, msg='获取成功', data=categories)
    except Exception as e:
        print(f'[分类] 列表查询失败: {e}')
        return api_response(code=500, msg=f'获取分类列表失败: {str(e)}')


@category_bp.route('/update/<category_id>', methods=['PUT'])
@jwt_required()
def update_category(category_id):
    """更新分类"""
    try:
        current_user_id = get_jwt_identity()
        data = request.get_json()
        name = data.get('name', '').strip()
        description = data.get('description', '').strip()

        if not name:
            return api_response(code=400, msg='分类名称不能为空')

        sql = text("""
            UPDATE biz_category
            SET name = :name, description = :description, update_time = :update_time
            WHERE id = :id AND user_id = :user_id
        """)
        db.session.execute(sql, {
            'id': category_id,
            'user_id': int(current_user_id),
            'name': name,
            'description': description,
            'update_time': datetime.now(CNT)
        })
        db.session.commit()
        return api_response(code=200, msg='分类更新成功')
    except Exception as e:
        db.session.rollback()
        print(f'[分类] 更新失败: {e}')
        return api_response(code=500, msg=f'更新分类失败: {str(e)}')


@category_bp.route('/delete/<category_id>', methods=['DELETE'])
@jwt_required()
def delete_category(category_id):
    """删除分类"""
    try:
        current_user_id = get_jwt_identity()
        # 先删除该分类下的知识库文档
        db.session.execute(text(
            "DELETE FROM biz_knowledge_doc WHERE category_id = :cat_id"
        ), {'cat_id': category_id})
        # 再删除分类
        db.session.execute(text(
            "DELETE FROM biz_category WHERE id = :id AND user_id = :user_id"
        ), {'id': category_id, 'user_id': int(current_user_id)})
        db.session.commit()
        return api_response(code=200, msg='分类删除成功')
    except Exception as e:
        db.session.rollback()
        print(f'[分类] 删除失败: {e}')
        return api_response(code=500, msg=f'删除分类失败: {str(e)}')
