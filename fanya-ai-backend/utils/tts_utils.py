import os
import uuid
import asyncio
import time
from typing import Optional

# 确保安装: pip install edge-tts>=6.1.9

# 全局变量缓存检查结果
_edge_tts_available = None


def check_edge_tts():
    global _edge_tts_available
    if _edge_tts_available is None:
        try:
            import edge_tts
            _edge_tts_available = True
        except ImportError:
            _edge_tts_available = False
            print("edge-tts module not found. Install it with: pip install edge-tts")
    return _edge_tts_available


def text_to_speech(text: str, filename: Optional[str] = None, rate: str = "+0%", pitch: str = "+0Hz") -> Optional[str]:
    """
    文本转语音核心函数：支持语速和音调调节，并加入失败重试机制。
    rate: 语速，如 "+10%", "-20%"
    pitch: 音调，如 "+5Hz", "-5Hz"
    """
    # 1. 准备目录
    out_dir = os.path.join('uploads', 'tts')
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    # 2. 准备文件名
    if not filename:
        filename = f"{uuid.uuid4()}.mp3"
    elif filename.endswith('.wav'):
        filename = filename.replace('.wav', '.mp3')

    path = os.path.join(out_dir, filename)

    # 3. 尝试生成语音 (带重试机制)
    success = False
    if check_edge_tts():
        import edge_tts

        # 定义异步任务
        async def _gen():
            # 使用中文女声 zh-CN-XiaoxiaoNeural，应用传入的情绪参数
            communicate = edge_tts.Communicate(
                text, "zh-CN-XiaoxiaoNeural", rate=rate, pitch=pitch)
            await communicate.save(path)

        # 循环重试机制，最多尝试 3 次
        for attempt in range(3):
            try:
                asyncio.run(_gen())
                # 检查文件是否真的生成成功且有内容
                if os.path.exists(path) and os.path.getsize(path) > 0:
                    success = True
                    print(
                        f"TTS Success: {filename} (Attempt: {attempt + 1}, Rate: {rate}, Pitch: {pitch})")
                    break
            except Exception as e:
                print(f"TTS Generation Error (Attempt {attempt + 1}/3): {e}")
                time.sleep(1.5)  # 失败后等待

    # 4. 降级处理：如果失败或者文件是空的，直接返回 None，并清理废文件
    if not success or not os.path.exists(path) or os.path.getsize(path) == 0:
        print(f"TTS ultimately failed for: {filename}. Cleaning up.")
        if os.path.exists(path):
            try:
                os.remove(path)  # 删掉坏文件，防止前端播放器卡死
            except:
                pass
        return None  # 返回 None，告诉调用方这页没音频

    return filename
