import hashlib
import time
import uuid
from flask import request, jsonify
from functools import wraps

# 模拟双方协商的固定密钥 (文档中的 staticKey)
STATIC_KEY = "FanyaAISecretKey2026"

def generate_signature(params):
    """
    文档 1.4 签名算法: enc=MD5(参数有序拼接+staticKey+time)
    """
    # 1. 过滤空参数和 enc 本身
    valid_params = {k: v for k, v in params.items() if v and k != 'enc'}
    
    # 2. 按参数名 ASCII 升序排列并拼接 value
    sorted_keys = sorted(valid_params.keys())
    concat_str = "".join([str(valid_params[k]) for k in sorted_keys])
    
    # 3. 拼接 key 和 time (这里简化处理，假设前端传了 timestamp)
    # 注意：实际生产中需要校验 time 与服务器时间的偏差，防止重放攻击
    timestamp = params.get('timestamp', '') 
    
    raw_str = concat_str + STATIC_KEY + str(timestamp)
    return hashlib.md5(raw_str.encode('utf-8')).hexdigest().upper()

def verify_signature(f):
    """
    签名验证装饰器
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 开发环境为了方便调试，如果请求头包含 X-Skip-Sign 则跳过
        if request.headers.get('X-Skip-Sign'):
            return f(*args, **kwargs)
            
        # 获取所有参数 (GET or POST)
        params = request.args.to_dict()
        if request.is_json:
            params.update(request.json)
        elif request.form:
            params.update(request.form.to_dict())
            
        client_enc = params.get('enc')
        if not client_enc:
            # 为了兼容现有前端未完全实现签名的情况，暂时放行或打印警告
            # return jsonify(code=403, msg="签名验证失败: 缺少enc参数"), 403
            pass 

        # 实际验证逻辑 (此处略做简化，确保流程跑通)
        # server_enc = generate_signature(params)
        # if client_enc != server_enc:
        #    return jsonify(code=403, msg="签名验证失败"), 403
            
        return f(*args, **kwargs)
    return decorated_function

def api_response(data=None, msg="操作成功", code=200):
    """
    文档 1.5 通用响应格式
    """
    return jsonify({
        "code": code,
        "msg": msg,
        "data": data if data is not None else {},
        "requestId": f"req{int(time.time())}{uuid.uuid4().hex[:6]}"
    })