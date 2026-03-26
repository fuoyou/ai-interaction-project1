"""
AI 文本生成模块
支持多种 AI 服务商的文字生成能力

使用示例：
1. 模拟模式（不需要 API）
2. OpenAI ChatGPT
3. 阿里通义千问
4. 讯飞星火
"""

import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class AIGenerator:
    """AI 文本生成接口"""
    
    def __init__(self, provider: str = "mock"):
        self.provider = provider.lower()
    
    def generate_reply(self, question: str, context: str = None, max_tokens: int = 500) -> str:
        """生成 AI 回复"""
        if self.provider == "openai":
            return self._openai_generate(question, context, max_tokens)
        elif self.provider == "zhipu":
            return self._zhipu_generate(question, context, max_tokens)
        elif self.provider == "aliyun":
            return self._aliyun_generate(question, context, max_tokens)
        elif self.provider == "xfyun":
            return self._xfyun_generate(question, context, max_tokens)
        else:
            return self._mock_generate(question, context)
    
    def generate_chat_reply(self, question: str, history: list = None, context: str = None, max_tokens: int = 800) -> str:
        """【新增】支持多轮对话上下文的 AI 回复"""
        if self.provider == "zhipu":
            return self._zhipu_chat_generate(question, history, context, max_tokens)
        return self._mock_generate(question, context)

    def stream_chat_reply(self, question: str, history: list = None, context: str = None, max_tokens: int = 800):
        """流式生成 AI 回复，逐段 yield 文本"""
        if self.provider == "zhipu":
            yield from self._zhipu_chat_stream(question, history, context, max_tokens)
            return

        # 非流式模型兜底：一次性返回
        full_text = self._mock_generate(question, context)
        if full_text:
            yield full_text

    def _mock_generate(self, question: str, context: Optional[str] = None) -> str:
        """模拟生成（用于测试）- 直接返回讲解内容，不包含提示词"""
        # 从question中提取课件内容（如果有的话）
        if "课件内容：" in question:
            content = question.split("课件内容：")[1].split("要求：")[0].strip()
            # 生成简单的讲解
            return f"同学们好，我们来看这部分内容。{content[:150]}...这是本页的核心知识点，请大家重点理解和掌握。"
        else:
            return f"同学们好，关于这个问题，核心要点是：首先要理解基础概念，其次结合实际案例分析，最后通过练习巩固。"
    
    def _zhipu_generate(self, question: str, context: Optional[str] = None, max_tokens: int = 500) -> str:
        """
        使用智谱 GLM API（推荐）
        
        安装：pip install zhipuai
        配置环境变量：ZHIPU_API_KEY
        
        模型选择：
        - glm-4: 最新最强模型
        - glm-4-flash: 快速版本
        - glm-3.5-turbo: 较轻量版本
        """
        try:
            from zhipuai import ZhipuAI
        except ImportError:
            print("zhipuai library not installed. Install with: pip install zhipuai")
            return self._mock_generate(question, context)
        
        api_key = os.getenv("ZHIPU_API_KEY")
        if not api_key:
            print("ZHIPU_API_KEY not set in environment")
            return self._mock_generate(question, context)
        
        try:
            client = ZhipuAI(api_key=api_key)
            
            system_prompt = "你是一个耐心的教学助手。用简洁易懂的语言回答学生的问题。"
            if context:
                system_prompt += f"\n课程上下文：{context}"
            
            response = client.chat.completions.create(
                model="glm-4-flash",  # 使用快速版本以获得更好的性能
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": question
                    }
                ],
                max_tokens=max_tokens,
                temperature=0.7
            )
            
            return response.choices[0].message.content.strip()
        
        except Exception as e:
            print(f"Zhipu API error: {e}")
            return self._mock_generate(question, context)
    
    def _openai_generate(self, question: str, context: Optional[str] = None, max_tokens: int = 500) -> str:
        """使用 OpenAI API"""
        try:
            import openai
        except ImportError:
            return self._mock_generate(question, context)
        
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return self._mock_generate(question, context)
        
        openai.api_key = api_key
        
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "你是一个耐心的教学助手。用简洁易懂的语言回答学生的问题。"},
                    {"role": "user", "content": question}
                ],
                max_tokens=max_tokens,
                temperature=0.7
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"OpenAI error: {e}")
            return self._mock_generate(question, context)
    
    def _aliyun_generate(self, question: str, context: Optional[str] = None, max_tokens: int = 500) -> str:
        """使用阿里通义千问 API（兼容 OpenAI 模式或 dashscope SDK）"""
        api_key = os.getenv("DASHSCOPE_API_KEY")
        if not api_key:
            return self._mock_generate(question, context)

        base_url = (os.getenv("DASHSCOPE_BASE_URL") or "").strip()
        model = os.getenv("QWEN_MODEL", "qwen-turbo")

        if base_url:
            try:
                from openai import OpenAI
            except ImportError:
                return self._mock_generate(question, context)
            try:
                client = OpenAI(api_key=api_key, base_url=base_url)
                r = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": "你是一个耐心的教学助手。用简洁易懂的语言回答学生的问题。"},
                        {"role": "user", "content": question},
                    ],
                    max_tokens=max_tokens,
                )
                return (r.choices[0].message.content or "").strip()
            except Exception as e:
                print(f"Aliyun (OpenAI-compatible) error: {e}")
                return self._mock_generate(question, context)

        try:
            import dashscope
        except ImportError:
            return self._mock_generate(question, context)

        try:
            dashscope.api_key = api_key
            response = dashscope.Generation.call(
                model=model if model else "qwen-plus",
                messages=[
                    {"role": "system", "content": "你是一个耐心的教学助手。用简洁易懂的语言回答学生的问题。"},
                    {"role": "user", "content": question},
                ],
                max_tokens=max_tokens,
            )
            if response.status_code == 200:
                return response.output.choices[0]["message"]["content"].strip()
            return self._mock_generate(question, context)
        except Exception as e:
            print(f"Aliyun error: {e}")
            return self._mock_generate(question, context)
    
    def _xfyun_generate(self, question: str, context: Optional[str] = None, max_tokens: int = 500) -> str:
        """使用讯飞星火 API（需要自行集成）"""
        return self._mock_generate(question, context)

    def _zhipu_chat_generate(self, question: str, history: list = None, context: str = None, max_tokens: int = 800) -> str:
        """【新增】智谱多轮对话核心逻辑"""
        try:
            from zhipuai import ZhipuAI
        except ImportError:
            return self._mock_generate(question, context)
        
        api_key = os.getenv("ZHIPU_API_KEY")
        if not api_key: return self._mock_generate(question, context)
            
        try:
            client = ZhipuAI(api_key=api_key)
            messages = self._build_chat_messages(question, history, context)
            response = client.chat.completions.create(
                model="glm-4-flash",
                messages=messages,
                max_tokens=max_tokens,
                temperature=0.7
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Zhipu Chat API error: {e}")
            return f"抱歉，系统开小差了，请稍后再试。"

    @staticmethod
    def _build_chat_messages(question: str, history: list = None, context: str = None) -> list:
        messages = []
        system_prompt = "你是一个耐心、专业的AI教学助手。请结合提供的课程上下文和历史对话回答学生问题。如果问题超出课程范畴，请友善引导回课程。"
        if context:
            system_prompt += f"\n\n【当前正在学习的课件知识点如下】：\n{context}"
        messages.append({"role": "system", "content": system_prompt})

        if history:
            for msg in history:
                role = "assistant" if msg.get("role") == "ai" else "user"
                if msg.get("content"):
                    messages.append({"role": role, "content": msg.get("content")})

        messages.append({"role": "user", "content": question})
        return messages

    def _zhipu_chat_stream(self, question: str, history: list = None, context: str = None, max_tokens: int = 800):
        """智谱流式输出，逐段返回 delta content"""
        try:
            from zhipuai import ZhipuAI
        except ImportError:
            fallback = self._mock_generate(question, context)
            if fallback:
                yield fallback
            return

        api_key = os.getenv("ZHIPU_API_KEY")
        if not api_key:
            fallback = self._mock_generate(question, context)
            if fallback:
                yield fallback
            return

        try:
            client = ZhipuAI(api_key=api_key)
            messages = self._build_chat_messages(question, history, context)
            stream = client.chat.completions.create(
                model="glm-4-flash",
                messages=messages,
                max_tokens=max_tokens,
                temperature=0.7,
                stream=True
            )

            for chunk in stream:
                delta_text = ""
                try:
                    # SDK 对象形式
                    delta_text = (
                        chunk.choices[0].delta.content
                        if chunk and chunk.choices and chunk.choices[0].delta
                        else ""
                    )
                except Exception:
                    # dict 兜底
                    try:
                        delta_text = (
                            chunk.get("choices", [{}])[0]
                            .get("delta", {})
                            .get("content", "")
                        )
                    except Exception:
                        delta_text = ""

                if delta_text:
                    yield delta_text
        except Exception as e:
            print(f"Zhipu Stream API error: {e}")
            fallback = self._zhipu_chat_generate(question, history, context, max_tokens)
            if fallback:
                yield fallback

_ai_generator = None


def get_ai_generator():
    """获取 AI 生成器单例"""
    global _ai_generator
    if _ai_generator is None:
        provider = os.getenv("AI_PROVIDER", "mock").lower()
        _ai_generator = AIGenerator(provider=provider)
    return _ai_generator


def generate_answer(question: str, context: str = None) -> str:
    """快捷函数：生成答案"""
    generator = get_ai_generator()
    return generator.generate_reply(question, context)
