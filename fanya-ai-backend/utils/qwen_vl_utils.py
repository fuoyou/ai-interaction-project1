"""
通义千问视觉（Qwen-VL）调用：用于课件配图理解与答疑。

与「文本千问」使用同一类密钥：优先读环境变量 DASHSCOPE_API_KEY（与 utils/ai_utils 里
_aliyun_generate 相同）；也可设 QWEN_API_KEY 作为别名。可选 QWEN_VL_MODEL（默认 qwen-vl-plus）。
"""
from __future__ import annotations

import os
from typing import Optional, Tuple

QWEN_VL_MODEL = os.getenv("QWEN_VL_MODEL", "qwen-vl-plus").strip() or "qwen-vl-plus"


def _dashscope_api_key() -> str:
    """与文本通义共用：.env 里配过的 DASHSCOPE_API_KEY 即可，无需单独再配。"""
    for name in ("DASHSCOPE_API_KEY", "QWEN_API_KEY"):
        v = (os.getenv(name) or "").strip()
        if v:
            return v
    return ""


def _normalize_image(image_input: str) -> str:
    s = (image_input or "").strip()
    if not s:
        return ""
    if s.startswith("http://") or s.startswith("https://"):
        return s
    if s.startswith("data:image"):
        return s
    return f"data:image/png;base64,{s}"


def _extract_vl_text(response) -> Tuple[Optional[str], Optional[str]]:
    """从 DashScope 多模态响应中取出文本；失败返回 (None, error)."""
    try:
        code = getattr(response, "status_code", None)
        if code is not None and code != 200:
            msg = getattr(response, "message", None) or getattr(response, "code", None)
            return None, str(msg or response)

        out = getattr(response, "output", None)
        if out is None:
            return None, "模型无输出"

        if isinstance(out, dict):
            if out.get("text"):
                return str(out["text"]).strip(), None
            choices = out.get("choices") or []
            if choices:
                msg = choices[0].get("message") or {}
                content = msg.get("content")
                if isinstance(content, str) and content.strip():
                    return content.strip(), None
                if isinstance(content, list):
                    parts = []
                    for item in content:
                        if isinstance(item, dict):
                            t = item.get("text")
                            if t:
                                parts.append(str(t))
                        elif isinstance(item, str):
                            parts.append(item)
                    if parts:
                        return "\n".join(parts).strip(), None
        else:
            choices = getattr(out, "choices", None) or []
            if choices:
                msg = getattr(choices[0], "message", None) or {}
                if isinstance(msg, dict):
                    content = msg.get("content")
                else:
                    content = getattr(msg, "content", None)
                if isinstance(content, str) and content.strip():
                    return content.strip(), None

        return None, f"无法解析模型输出: {out!r}"
    except Exception as e:
        return None, str(e)


def qwen_vl_chat(
    image_input: str,
    user_question: str,
    context_text: str = "",
    max_chars_context: int = 8000,
) -> Tuple[str, Optional[str]]:
    """
    调用千问视觉模型。返回 (回答文本, 错误信息)；成功时错误为 None。
    """
    api_key = _dashscope_api_key()
    if not api_key:
        return (
            "",
            "未检测到通义 API Key：请在运行后端的同一环境中设置 DASHSCOPE_API_KEY（与文本千问相同），"
            "保存 .env 后重启 Flask；若已填写仍报错，请确认启动目录能加载到该 .env。",
        )

    img = _normalize_image(image_input)
    if not img:
        return "", "图片数据为空"

    try:
        from dashscope import MultiModalConversation
    except ImportError:
        return "", "未安装 dashscope，请执行: pip install dashscope"

    ctx = (context_text or "").strip()
    if len(ctx) > max_chars_context:
        ctx = ctx[:max_chars_context] + "…"

    q = (user_question or "").strip() or (
        "请结合下方课程上下文，说明这张插图的内容、要点，以及它与当前正在学习的知识点有什么关系。"
    )

    text_blob = q
    if ctx:
        text_blob = (
            "【课程与当前页相关上下文】\n"
            + ctx
            + "\n\n【学生问题】\n"
            + q
        )

    messages = [
        {
            "role": "user",
            "content": [
                {"image": img},
                {"text": text_blob},
            ],
        }
    ]

    try:
        response = MultiModalConversation.call(
            model=QWEN_VL_MODEL,
            messages=messages,
            api_key=api_key,
        )
    except Exception as e:
        return "", _friendly_vl_error(f"调用视觉模型异常: {e}")

    answer, err = _extract_vl_text(response)
    if err:
        err = _friendly_vl_error(err)
        return "", err
    return answer or "", None


def _friendly_vl_error(raw: str) -> str:
    """把 DashScope 英文拒识提示转成更易懂的中文。"""
    s = (raw or "").strip()
    if not s:
        return "视觉模型调用失败"
    low = s.lower()
    if "larger than 10" in low or ("height" in low and "width" in low and "10" in s):
        return "配图裁切区域过小（模型要求宽高均大于约 10 像素）。请点击较大的配图区域，或放大页面后重试。"
    if "invalidparameter" in low or "invalid parameter" in low:
        return f"视觉模型参数或图片不符合要求：{s[:400]}"
    return s
