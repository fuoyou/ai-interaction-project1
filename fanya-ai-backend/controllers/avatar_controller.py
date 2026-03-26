import os
import uuid
import asyncio
import requests
import base64
import tempfile
import traceback
from flask import Blueprint, request
from flask_jwt_extended import jwt_required
from utils.response_utils import success_response, error_response, generate_request_id

avatar_bp = Blueprint('avatar', __name__)

# ==================== 配置区 ====================
# 必须与你 SSH 隧道 -L 后面的第一个数字一致
AUTO_DL_URL = "http://127.0.0.1:6009/render" 

VIDEO_SAVE_DIR = os.path.join('static', 'digital_humans')
os.makedirs(VIDEO_SAVE_DIR, exist_ok=True)

# 确保这张图片在主服务器的该路径下存在
TEACHER_IMAGE_PATH = os.path.abspath(os.path.join('static', 'images', 'teacher.png'))

# ==================== 核心辅助 ====================

async def text_to_speech(text, output_path):
    try:
        import edge_tts
        voice = "zh-CN-XiaoxiaoNeural"
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(output_path)
        return True
    except Exception as e:
        print(f"TTS Error: {e}")
        return False

def sync_text_to_speech(text, output_path):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(text_to_speech(text, output_path))

# ==================== 主路由接口 ====================

@avatar_bp.route('/talk', methods=['POST'])
@jwt_required()
def create_talk():
    """
    数字人语音合成接口
    符合超星AI互动智课系统API规范
    接口地址：/api/v1/avatar/talk
    """
    request_id = generate_request_id()
    data = request.get_json()
    script = data.get('script')
    
    # 参数验证
    if not os.path.exists(TEACHER_IMAGE_PATH):
        return error_response(
            code=404,
            msg='主服务器缺少老师照片 static/images/teacher.png',
            request_id=request_id
        )
    
    if not script:
        return error_response(
            code=400,
            msg='script 不能为空',
            request_id=request_id
        )

    task_id = str(uuid.uuid4())
    temp_wav_path = os.path.abspath(os.path.join(tempfile.gettempdir(), f"{task_id}.wav"))

    try:
        # 1. 生成语音 (WAV 格式最稳)
        print(f"[{task_id}] 1. 正在合成语音...")
        if not sync_text_to_speech(script, temp_wav_path):
            return error_response(
                code=500,
                msg='语音合成失败',
                request_id=request_id
            )

        # 2. 将素材转为 Base64
        print(f"[{task_id}] 2. 正在编码 Base64 素材...")
        with open(TEACHER_IMAGE_PATH, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode()
        with open(temp_wav_path, "rb") as f:
            wav_b64 = base64.b64encode(f.read()).decode()

        # 3. 发送给 AutoDL 渲染工厂
        print(f"[{task_id}] 3. 正在提交 4090 渲染任务，请耐心等待 30-60s...")
        # 超时时间设为 300 秒，保证 4090 渲染完
        resp = requests.post(AUTO_DL_URL, json={
            "img_base64": img_b64,
            "wav_base64": wav_b64
        }, timeout=300)

        if resp.status_code != 200:
            print(f"渲染工厂返回错误: {resp.text}")
            return error_response(
                code=500,
                msg='4090 渲染失败，请检查 AutoDL 日志',
                request_id=request_id
            )

        # 4. 接收视频流并保存
        print(f"[{task_id}] 4. 渲染成功！正在保存视频...")
        final_video_name = f"{task_id}.mp4"
        final_save_path = os.path.join(VIDEO_SAVE_DIR, final_video_name)
        
        with open(final_save_path, 'wb') as f:
            f.write(resp.content)

        # 5. 清理本地临时文件
        if os.path.exists(temp_wav_path):
            os.remove(temp_wav_path)
            
        print(f"[{task_id}] 任务圆满完成！")

        # 符合超星API规范的响应格式
        return success_response(
            data={
                "audioId": task_id,
                "result_url": f"/static/digital_humans/{final_video_name}",
                "videoUrl": f"/static/digital_humans/{final_video_name}"
            },
            request_id=request_id
        )

    except requests.Timeout:
        return error_response(
            code=408,
            msg='请求超时',
            request_id=request_id
        )
    except Exception as e:
        traceback.print_exc()
        return error_response(
            code=500,
            msg=f'系统异常: {str(e)}',
            request_id=request_id
        )
