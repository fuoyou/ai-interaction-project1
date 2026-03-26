"""
响应工具类
符合超星AI互动智课系统API规范
"""
from datetime import datetime
import uuid
from flask import jsonify


def generate_request_id():
    """生成唯一的请求ID"""
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    return f"req{timestamp}{uuid.uuid4().hex[:6]}"


def success_response(data=None, msg='操作成功', request_id=None):
    """
    成功响应
    
    Args:
        data: 业务数据
        msg: 状态描述
        request_id: 请求唯一标识
    
    Returns:
        Flask jsonify response
    """
    if request_id is None:
        request_id = generate_request_id()
    
    return jsonify(
        code=200,
        msg=msg,
        data=data if data is not None else {},
        requestId=request_id
    )


def error_response(code, msg, data=None, request_id=None, http_status=None):
    """
    错误响应
    
    Args:
        code: 错误码（400/401/403/404/408/500/503）
        msg: 错误描述
        data: 额外数据
        request_id: 请求唯一标识
        http_status: HTTP状态码（如果不指定，使用code）
    
    Returns:
        Flask jsonify response with status code
    """
    if request_id is None:
        request_id = generate_request_id()
    
    if http_status is None:
        http_status = code
    
    return jsonify(
        code=code,
        msg=msg,
        data=data if data is not None else {},
        requestId=request_id
    ), http_status
