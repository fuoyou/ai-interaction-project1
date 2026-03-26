"""
智能插旗：考点和题目生成工具
"""
import json
import re
import random


def generate_checkpoints(content_list, script_sections, ai_generator):
    """
    基于课件内容和讲稿，使用AI生成智能考点和题目
    每5页生成一个考点，题型包括选择题、判断题、简答题
    """
    checkpoints = []
    
    if not content_list or len(content_list) == 0:
        return checkpoints
    
    # 每5页设置一个考点
    for i in range(4, len(content_list), 5):  # 从第5页开始，每5页一个
        page_num = i + 1
        page_content = content_list[i] if i < len(content_list) else ""
        page_script = script_sections[i]["content"] if i < len(script_sections) else ""
        
        # 如果页面内容太少，跳过
        if len(page_content.strip()) < 20:
            continue
        
        try:
            # 使用AI生成考点题目
            checkpoint = generate_single_checkpoint(
                page_num, page_content, page_script, ai_generator
            )
            if checkpoint:
                checkpoints.append(checkpoint)
                print(f"  [智能插旗] 第{page_num}页考点已生成")
        except Exception as e:
            print(f"  [智能插旗] 第{page_num}页考点生成失败: {e}")
            continue
    
    return checkpoints


def generate_single_checkpoint(page_num, page_content, page_script, ai_generator):
    """生成单个考点的题目"""
    # 随机选择题型
    question_types = ['choice', 'judge', 'short']
    question_type = random.choice(question_types)
    
    # 构建提示词
    if question_type == 'choice':
        prompt = f"""基于以下课件内容，生成一道选择题来检测学生对核心知识点的理解。

课件原文：
{page_content[:500]}

讲解内容：
{page_script[:300]}

要求：
1. 题目要针对本页的核心知识点
2. 提供4个选项（A、B、C、D）
3. 只有一个正确答案
4. 提供详细的解析说明

请按以下JSON格式输出（只输出JSON，不要其他内容）：
{{
  "question": "题目内容",
  "options": ["选项A：内容", "选项B：内容", "选项C：内容", "选项D：内容"],
  "correctAnswer": "选项A：内容",
  "explanation": "解析说明"
}}"""
    
    elif question_type == 'judge':
        prompt = f"""基于以下课件内容，生成一道判断题来检测学生对核心知识点的理解。

课件原文：
{page_content[:500]}

讲解内容：
{page_script[:300]}

要求：
1. 题目要针对本页的核心知识点
2. 答案为"正确"或"错误"
3. 提供详细的解析说明

请按以下JSON格式输出（只输出JSON，不要其他内容）：
{{
  "question": "判断题内容",
  "correctAnswer": "正确",
  "explanation": "解析说明"
}}"""
    
    else:  # short
        prompt = f"""基于以下课件内容，生成一道简答题来检测学生对核心知识点的理解。

课件原文：
{page_content[:500]}

讲解内容：
{page_script[:300]}

要求：
1. 题目要针对本页的核心知识点
2. 提供关键词作为参考答案
3. 提供详细的解析说明

请按以下JSON格式输出（只输出JSON，不要其他内容）：
{{
  "question": "简答题内容",
  "correctAnswer": "关键词",
  "explanation": "详细解析"
}}"""
    
    try:
        # 调用AI生成
        response = ai_generator.generate_reply(prompt, max_tokens=500)
        
        # 解析JSON响应
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            question_data = json.loads(json_match.group())
            
            # 构建考点对象
            checkpoint = {
                "id": f"checkpoint_{page_num}",
                "pageNum": page_num,
                "type": question_type,
                "question": question_data.get("question", ""),
                "correctAnswer": question_data.get("correctAnswer", ""),
                "explanation": question_data.get("explanation", "")
            }
            
            if question_type == 'choice':
                checkpoint["options"] = question_data.get("options", [])
            
            return checkpoint
        else:
            print(f"  [智能插旗] AI响应格式错误，使用默认题目")
            return generate_fallback_checkpoint(page_num, question_type, page_content)
            
    except Exception as e:
        print(f"  [智能插旗] AI生成失败: {e}，使用默认题目")
        return generate_fallback_checkpoint(page_num, question_type, page_content)


def generate_fallback_checkpoint(page_num, question_type, page_content):
    """生成默认的考点题目（当AI生成失败时使用）"""
    if question_type == 'choice':
        return {
            "id": f"checkpoint_{page_num}",
            "pageNum": page_num,
            "type": "choice",
            "question": f"关于第{page_num}页的内容，以下哪个说法是正确的？",
            "options": [
                "选项A：这是正确答案",
                "选项B：这是错误答案",
                "选项C：这也是错误答案",
                "选项D：这还是错误答案"
            ],
            "correctAnswer": "选项A：这是正确答案",
            "explanation": f"第{page_num}页主要讲解了核心知识点，选项A准确概括了主要内容。"
        }
    elif question_type == 'judge':
        return {
            "id": f"checkpoint_{page_num}",
            "pageNum": page_num,
            "type": "judge",
            "question": f"第{page_num}页提到的核心概念是本章的重点内容。",
            "correctAnswer": "正确",
            "explanation": f"这个说法是正确的。第{page_num}页的内容确实是本章的核心知识点。"
        }
    else:
        return {
            "id": f"checkpoint_{page_num}",
            "pageNum": page_num,
            "type": "short",
            "question": f"请简要概括第{page_num}页的主要内容。",
            "correctAnswer": "核心知识点",
            "explanation": f"第{page_num}页主要讲解了核心知识点，包括基本概念和应用场景。"
        }
