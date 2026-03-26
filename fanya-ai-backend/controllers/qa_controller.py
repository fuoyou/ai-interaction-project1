from flask import Blueprint, request, jsonify, send_from_directory, Response, stream_with_context
from flask_jwt_extended import get_jwt_identity, jwt_required
from models.qa import QASession, QARecord
from models.lesson import Lesson
from models.knowledge import KnowledgeDoc
from models.progress import RhythmAdjustment
from extensions import db
import os
import uuid
import json
import time
import hashlib
import threading
from collections import OrderedDict

from utils import tts_utils
from utils.ai_utils import AIGenerator
from utils.api_utils import verify_signature, api_response
from utils.kb_category import normalize_kb_category_id
from utils.file_utils import extract_text_from_pdf, extract_text_from_ppt
from utils.qwen_vl_utils import qwen_vl_chat
from utils.rag_utils import (
    RAGRetriever,
    build_rag_chunks,
    dumps_rag_chunks,
    loads_rag_chunks,
)

qa_bp = Blueprint('qa', __name__)

RAG_RETRIEVER_CACHE_MAX = 64
RAG_REBUILD_COOLDOWN_SECONDS = 600
QA_SYNC_TTS_FOR_TEXT = os.getenv("QA_SYNC_TTS_FOR_TEXT", "0") == "1"
_RAG_CACHE_LOCK = threading.Lock()
_RAG_RETRIEVER_CACHE = OrderedDict()
_RAG_REBUILD_GUARD = {}
CONFUSED_KEYWORDS = ["不明白", "听不懂", "还是不懂", "再讲一遍", "难点", "困惑", "复杂", "简练点"]


def _make_rag_cache_key(lesson_id, rag_chunks_raw):
    raw = rag_chunks_raw or ""
    digest = hashlib.md5(raw.encode("utf-8")).hexdigest() if raw else "empty"
    return f"{lesson_id}:{digest}"


def _get_cached_retriever(lesson_id, rag_chunks_raw, rag_chunks):
    cache_key = _make_rag_cache_key(lesson_id, rag_chunks_raw)
    with _RAG_CACHE_LOCK:
        retriever = _RAG_RETRIEVER_CACHE.get(cache_key)
        if retriever is not None:
            _RAG_RETRIEVER_CACHE.move_to_end(cache_key)
            return retriever

    retriever = RAGRetriever(rag_chunks)
    with _RAG_CACHE_LOCK:
        _RAG_RETRIEVER_CACHE[cache_key] = retriever
        _RAG_RETRIEVER_CACHE.move_to_end(cache_key)
        while len(_RAG_RETRIEVER_CACHE) > RAG_RETRIEVER_CACHE_MAX:
            _RAG_RETRIEVER_CACHE.popitem(last=False)
    return retriever


def _invalidate_lesson_cache(lesson_id):
    lesson_prefix = f"{lesson_id}:"
    with _RAG_CACHE_LOCK:
        to_delete = [k for k in _RAG_RETRIEVER_CACHE.keys() if k.startswith(lesson_prefix)]
        for key in to_delete:
            _RAG_RETRIEVER_CACHE.pop(key, None)


def _build_rag_context_with_cache(
    lesson_id, question, rag_chunks_raw, rag_chunks, top_k=3, source_name="当前课件"
):
    """返回 (拼接后的课件 RAG 上下文, 溯源列表)。"""
    if not question or not rag_chunks:
        return "", []
    retriever = _get_cached_retriever(lesson_id, rag_chunks_raw, rag_chunks)
    hits = retriever.search(question, top_k=top_k)
    if not hits:
        return "", []
    ctx = "\n\n".join([f"[片段{i + 1}] {c}" for i, c in enumerate(hits)])
    cites = []
    for i, t in enumerate(hits):
        snip = t if len(t) <= 280 else t[:280] + "…"
        cites.append(
            {
                "kind": "courseware",
                "ref": i + 1,
                "sourceName": source_name or "当前课件",
                "snippet": snip,
            }
        )
    return ctx, cites


def _should_attempt_rebuild(lesson_id):
    now_ts = int(time.time())
    with _RAG_CACHE_LOCK:
        last_ts = _RAG_REBUILD_GUARD.get(str(lesson_id), 0)
        if now_ts - last_ts < RAG_REBUILD_COOLDOWN_SECONDS:
            return False
        _RAG_REBUILD_GUARD[str(lesson_id)] = now_ts
        return True


def _resolve_kb_category_id(data, lesson_id):
    """优先使用请求中的 categoryId；否则从课件记录读取 course_id（与教师端/学生端知识库同一分类即同一资料池）。"""
    cid = normalize_kb_category_id(data.get("categoryId") or data.get("courseCategoryId") or "")
    if cid:
        return cid
    if not lesson_id:
        return ""
    lesson = Lesson.query.filter(
        (Lesson.parse_id == str(lesson_id)) | (Lesson.id == lesson_id)
    ).first()
    if lesson and lesson.course_id is not None:
        s = normalize_kb_category_id(lesson.course_id)
        if s:
            return s
    return ""


def _resolve_lesson_context(lesson_id, current_section_id, question_content, allow_rebuild=True):
    context_text = ""
    rag_context_text = ""
    related_knowledge = {}
    lesson_rag_citations = []

    if not lesson_id:
        return context_text, rag_context_text, related_knowledge, lesson_rag_citations

    lesson = Lesson.query.filter((Lesson.parse_id == lesson_id) | (Lesson.id == lesson_id)).first()
    if lesson and lesson.script_content:
        try:
            script_structure = json.loads(lesson.script_content)
            for section in script_structure:
                if (current_section_id and section.get('sectionId') == current_section_id) or str(section.get('page')) == str(current_section_id).replace('sec', ''):
                    context_text = section.get('content', '')
                    related_knowledge = {
                        'knowledgeId': section.get('sectionId'),
                        'knowledgeName': section.get('sectionName'),
                        'relatedSectionId': current_section_id
                    }
                    break
        except Exception:
            pass

    if lesson:
        src_label = lesson.file_name or "当前课件"
        rag_chunks_raw = getattr(lesson, "rag_chunks", None)
        rag_chunks = loads_rag_chunks(rag_chunks_raw)
        if not rag_chunks and allow_rebuild:
            source_file = os.path.join("uploads", lesson.file_url) if lesson.file_url else ""
            if source_file and os.path.exists(source_file):
                if lesson.file_type == "pdf":
                    rebuilt_content = extract_text_from_pdf(source_file)
                elif lesson.file_type in ["ppt", "pptx"]:
                    rebuilt_content = extract_text_from_ppt(source_file)
                else:
                    rebuilt_content = []

                rag_chunks = build_rag_chunks(rebuilt_content or [], chunk_size=500)
                if rag_chunks:
                    lesson.rag_chunks = dumps_rag_chunks(rag_chunks)
                    rag_chunks_raw = lesson.rag_chunks
                    db.session.commit()
                    _invalidate_lesson_cache(lesson.id)

        if rag_chunks:
            rag_context_text, lesson_rag_citations = _build_rag_context_with_cache(
                lesson.id,
                question_content,
                rag_chunks_raw,
                rag_chunks,
                top_k=3,
                source_name=src_label,
            )

        if allow_rebuild and not rag_context_text and _should_attempt_rebuild(lesson.id):
            source_file = os.path.join("uploads", lesson.file_url) if lesson.file_url else ""
            if source_file and os.path.exists(source_file):
                if lesson.file_type == "pdf":
                    rebuilt_content = extract_text_from_pdf(source_file)
                elif lesson.file_type in ["ppt", "pptx"]:
                    rebuilt_content = extract_text_from_ppt(source_file)
                else:
                    rebuilt_content = []
                rebuilt_chunks = build_rag_chunks(rebuilt_content or [], chunk_size=500)
                if rebuilt_chunks:
                    lesson.rag_chunks = dumps_rag_chunks(rebuilt_chunks)
                    rag_chunks_raw = lesson.rag_chunks
                    db.session.commit()
                    _invalidate_lesson_cache(lesson.id)
                    rag_context_text, lesson_rag_citations = _build_rag_context_with_cache(
                        lesson.id,
                        question_content,
                        rag_chunks_raw,
                        rebuilt_chunks,
                        top_k=3,
                        source_name=src_label,
                    )

    return context_text, rag_context_text, related_knowledge, lesson_rag_citations


def _retrieve_course_knowledge_context(category_id, question, top_k=5, per_doc_top=2):
    """
    按课程分类（与课件 courseId/categoryId 一致）检索知识库片段，返回拼接上下文与溯源列表。
    检索策略：每份资料内 BM25 取前 per_doc_top，再按分数全局取 top_k（与 AgenticRAGOCR 的「多片段打分再截断」思路一致，向量库换为现有 BM25）。
    """
    cat_key = normalize_kb_category_id(category_id)
    if not cat_key or not (question or "").strip():
        return "", []

    docs = (
        KnowledgeDoc.query.filter_by(category_id=cat_key)
        .order_by(KnowledgeDoc.create_time.desc())
        .all()
    )
    scored = []
    for doc in docs:
        chunks = loads_rag_chunks(doc.rag_chunks)
        if not chunks:
            continue
        retriever = RAGRetriever(chunks)
        for text, sc in retriever.search_with_scores(question, top_k=per_doc_top):
            if not (text or "").strip():
                continue
            scored.append(
                (
                    sc,
                    text.strip(),
                    {"docId": doc.id, "sourceName": doc.name or "未命名资料", "fileType": doc.file_type or ""},
                )
            )

    scored.sort(key=lambda x: x[0], reverse=True)
    picked = scored[:top_k]
    if not picked:
        return "", []

    context_lines = []
    citations = []
    for i, (_, text, meta) in enumerate(picked):
        ref = i + 1
        title = meta["sourceName"]
        context_lines.append(f"[课程知识库·资料{ref}]《{title}》\n{text}")
        snip = text if len(text) <= 320 else text[:320] + "…"
        citations.append(
            {
                "kind": "knowledge",
                "ref": ref,
                "docId": meta["docId"],
                "sourceName": title,
                "snippet": snip,
                "fileType": meta.get("fileType") or "",
            }
        )

    return "\n\n".join(context_lines), citations


def _format_history(history_qa):
    formatted_history = []
    for qa in history_qa:
        if qa.get('role'):
            formatted_history.append(qa)
        elif qa.get('question'):
            formatted_history.append({'role': 'user', 'content': qa.get('question')})
            formatted_history.append({'role': 'ai', 'content': qa.get('answer')})
    return formatted_history


def _build_final_context(
    is_confused,
    context_text,
    rag_context_text,
    current_section_id=None,
    current_page_content=None,
    kb_context_text=None,
):
    system_prefix = "你是一个耐心、温柔的大学教师。" if is_confused else "你是一个专业、富有激情的大学教师。"
    page_hint = f"\n当前页标识：{current_section_id}" if current_section_id else ""
    page_content_hint = f"\n当前页可见内容（优先依据它回答）：{current_page_content}" if current_page_content else ""
    final_context = (
        f"{system_prefix}"
        f"\n请优先依据“当前页”内容回答；若证据不足请明确说明，不要编造。"
        f"{page_hint}"
        f"{page_content_hint}"
        f"\n课程上下文：{context_text}"
    )
    if rag_context_text:
        final_context += (
            f"\n\n检索到的课件原文片段：\n{rag_context_text}"
            f"\n若回答参考了上述片段，请在相应位置标注编号，如[片段1]、[片段2]。"
        )
    if kb_context_text:
        final_context += (
            f"\n\n以下为该课程「知识库」检索到的补充资料（非当前页正文，回答若用到请用脚注形式标明来源编号，如[资料1]）：\n"
            f"{kb_context_text}"
        )
    return final_context


def _sse_event(event_name, data):
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event_name}\ndata: {payload}\n\n"

# ==================== 2.2.1 问答交互接口（增强版） ====================
@qa_bp.route('/interact', methods=['POST'])
@verify_signature
@jwt_required()
def qa_interact():
    """
    接口功能：接收学生提问，结合课程上下文生成解答。
    核心逻辑：检测理解程度，若不理解则将回复语速调慢 25%，增加温和感。
    """
    req_start = time.perf_counter()
    current_user_id = get_jwt_identity()
    data = request.get_json()
    
    school_id = data.get('schoolId', 'sch10001')
    course_id = data.get('courseId')
    lesson_id = data.get('lessonId') or course_id 
    session_id = data.get('sessionId')
    question_type = data.get('questionType', 'text')
    need_audio = bool(data.get('needAudio', False))
    question_content = data.get('questionContent') or data.get('question')
    current_page_content = (data.get('currentPageContent') or "").strip()
    current_section_id = data.get('currentSectionId')
    history_qa = data.get('historyQa', [])
    use_course_kb = bool(data.get('useCourseKnowledgeBase') or data.get('useKnowledgeBase'))

    if not question_content:
        return api_response(code=400, msg='提问内容不能为空')
    
    if not session_id:
        session_id = f"ses{int(time.time())}{uuid.uuid4().hex[:6]}"
        session = QASession(session_id=session_id, school_id=school_id, user_id=str(current_user_id), course_id=course_id, lesson_id=lesson_id, current_section_id=current_section_id)
        db.session.add(session)
    else:
        session = QASession.query.filter_by(session_id=session_id).first()
        if session: session.current_section_id = current_section_id
    
    context_text, rag_context_text, related_knowledge, courseware_citations = _resolve_lesson_context(
        lesson_id,
        current_section_id,
        question_content
    )

    course_category_id = _resolve_kb_category_id(data, lesson_id)
    kb_context_text, knowledge_citations = "", []
    if use_course_kb and not course_category_id:
        print(
            f"[QA知识库] 已开启 useCourseKnowledgeBase 但未解析到课程分类 ID（"
            f"请传 categoryId 或保证课件 biz_lesson.course_id 与知识库 category_id 一致），lesson_id={lesson_id}"
        )
    if use_course_kb and course_category_id:
        kb_context_text, knowledge_citations = _retrieve_course_knowledge_context(
            course_category_id, question_content
        )
        if not knowledge_citations:
            print(
                f"[QA知识库] 分类 {course_category_id} 下无可用 RAG 片段（无文档或 rag_chunks 为空/未建索引），question={question_content[:80]!r}"
            )

    ai_generator = AIGenerator(provider='zhipu')
    formatted_history = _format_history(history_qa)
    
    try:
        ai_start = time.perf_counter()
        # 1. 判定理解程度（关键词增加逻辑）
        understanding_level = "partial"
        is_confused = any(k in question_content for k in CONFUSED_KEYWORDS)
        
        # 2. 调用 AI，如果是困惑状态，Prompt 要求 AI 表现得更有耐心
        final_context = _build_final_context(
            is_confused,
            context_text,
            rag_context_text,
            current_section_id=current_section_id,
            current_page_content=current_page_content[:1200],
            kb_context_text=kb_context_text or None,
        )

        answer_content = ai_generator.generate_chat_reply(
            question=question_content,
            history=formatted_history,
            context=final_context
        )
        ai_elapsed_ms = int((time.perf_counter() - ai_start) * 1000)
        
        supplement_content = ""
        adjusted_script = ""  # 新增：调整后的讲稿
        if is_confused:
            understanding_level = "none"
            adjust_prompt = f"学生对‘{context_text[:100]}’不理解，请用极简的生活化类比再讲一遍（150字以内）。"
            supplement_content = ai_generator.generate_reply(adjust_prompt)

            # 【创新点四】生成简化版讲稿（通俗易懂版，多举例）
            simplify_prompt = f"""
学生对以下内容理解困难：
{context_text[:500]}

请将上述内容改写为通俗易懂版本，要求：
1. 使用生活化的语言和比喻
2. 增加2-3个具体例子
3. 避免专业术语，或对术语进行解释
4. 保持200-300字
5. 语气要温和、鼓励
"""
            adjusted_script = ai_generator.generate_reply(simplify_prompt)
            print(f"[讲授节奏调整] 学生理解困难，已生成简化版讲稿（{len(adjusted_script)}字）")
        elif any(k in question_content for k in ["懂了", "明白了", "理解了"]):
            understanding_level = "full"

        # 3. 语音生成（优化：文本问答默认不阻塞等待 TTS）
        should_sync_tts = (question_type == 'voice') or need_audio or QA_SYNC_TTS_FOR_TEXT
        if should_sync_tts:
            voice_rate = "-150%" if understanding_level == "none" else "+0%"  # 不懂时慢速
            voice_pitch = "+50Hz" if understanding_level == "none" else "+0Hz" # 不懂时音调微高，显得亲切
            tts_start = time.perf_counter()
            audio_filename = tts_utils.text_to_speech(answer_content, rate=voice_rate, pitch=voice_pitch)
            audio_url = f'/api/v1/qa/audio/{audio_filename}' if audio_filename else ""
            tts_elapsed_ms = int((time.perf_counter() - tts_start) * 1000)
        else:
            audio_url = ""
            tts_elapsed_ms = 0

    except Exception as e:
        print(f"AI Error: {e}")
        answer_content, understanding_level, audio_url, supplement_content, adjusted_script = "系统忙，请稍后再试", "partial", "", "", ""
        ai_elapsed_ms = -1
        tts_elapsed_ms = -1

    answer_id = f"ans{int(time.time())}{uuid.uuid4().hex[:6]}"
    qa_record = QARecord(answer_id=answer_id, session_id=session_id, question_type=question_type, question_content=question_content, answer_content=answer_content, answer_type='text', answer_audio_url=audio_url, related_knowledge_id=related_knowledge.get('knowledgeId'), related_knowledge_name=related_knowledge.get('knowledgeName'), related_section_id=related_knowledge.get('relatedSectionId'), understanding_level=understanding_level, suggestions=json.dumps(["需要我举例吗？", "哪里觉得难？"], ensure_ascii=False))
    db.session.add(qa_record)
    
    # 【创新点四】如果检测到理解困难，保存节奏调整记录
    if understanding_level == 'none' and adjusted_script:
        rhythm_record = RhythmAdjustment(
            user_id=str(current_user_id),
            lesson_id=str(lesson_id),
            current_section_id=current_section_id,
            understanding_level=understanding_level,
            qa_record_id=answer_id,
            adjust_type='simplify',  # 简化讲解
            continue_section_id=current_section_id,  # 继续当前章节
            supplement_content=supplement_content,
            next_sections=json.dumps([current_section_id], ensure_ascii=False)  # 建议继续当前章节
        )
        db.session.add(rhythm_record)
        print(f"[讲授节奏调整] 已保存调整记录到数据库")
    
    db.session.commit()
    total_elapsed_ms = int((time.perf_counter() - req_start) * 1000)
    print(
        f"[QA性能] total={total_elapsed_ms}ms, ai={ai_elapsed_ms}ms, tts={tts_elapsed_ms}ms, "
        f"questionType={question_type}, syncTTS={should_sync_tts if 'should_sync_tts' in locals() else False}"
    )
    
    return api_response(
        data={
            'answerId': answer_id,
            'answerContent': answer_content,
            'audioUrl': audio_url,
            'understandingLevel': understanding_level,
            'supplementContent': supplement_content,
            'adjustedScript': adjusted_script,
            'sessionId': session_id,
            'knowledgeCitations': knowledge_citations,
            'coursewareCitations': courseware_citations,
        }
    )


@qa_bp.route('/interact/stream', methods=['POST'])
@verify_signature
@jwt_required()
def qa_interact_stream():
    """SSE 流式问答：边生成边返回，降低首字等待时间。"""
    req_start = time.perf_counter()
    current_user_id = get_jwt_identity()
    data = request.get_json() or {}

    school_id = data.get('schoolId', 'sch10001')
    course_id = data.get('courseId')
    lesson_id = data.get('lessonId') or course_id
    session_id = data.get('sessionId')
    question_type = data.get('questionType', 'text')
    question_content = data.get('questionContent') or data.get('question')
    current_page_content = (data.get('currentPageContent') or "").strip()
    current_section_id = data.get('currentSectionId')
    history_qa = data.get('historyQa', [])
    use_course_kb = bool(data.get('useCourseKnowledgeBase') or data.get('useKnowledgeBase'))

    if not question_content:
        return api_response(code=400, msg='提问内容不能为空')

    if not session_id:
        session_id = f"ses{int(time.time())}{uuid.uuid4().hex[:6]}"
        session = QASession(
            session_id=session_id,
            school_id=school_id,
            user_id=str(current_user_id),
            course_id=course_id,
            lesson_id=lesson_id,
            current_section_id=current_section_id
        )
        db.session.add(session)
    else:
        session = QASession.query.filter_by(session_id=session_id).first()
        if session:
            session.current_section_id = current_section_id

    answer_id = f"ans{int(time.time())}{uuid.uuid4().hex[:6]}"

    @stream_with_context
    def generate():
        ai_elapsed_ms = -1
        tts_elapsed_ms = 0
        try:
            yield _sse_event("meta", {"sessionId": session_id, "answerId": answer_id})

            # 流式场景优先保证首包与连贯输出，不在请求链路里做重型重建/OCR
            context_text, rag_context_text, related_knowledge, courseware_citations = _resolve_lesson_context(
                lesson_id,
                current_section_id,
                question_content,
                allow_rebuild=False
            )
            course_category_id = _resolve_kb_category_id(data, lesson_id)
            kb_context_text, knowledge_citations = "", []
            if use_course_kb and not course_category_id:
                print(
                    f"[QA知识库-流式] 已开启知识库但未解析到课程分类 ID，lesson_id={lesson_id}"
                )
            if use_course_kb and course_category_id:
                kb_context_text, knowledge_citations = _retrieve_course_knowledge_context(
                    course_category_id, question_content
                )
                if not knowledge_citations:
                    print(
                        f"[QA知识库-流式] 分类 {course_category_id} 检索结果为空（无文档或无 rag_chunks），"
                        f"question={question_content[:80]!r}"
                    )
            formatted_history = _format_history(history_qa)
            ai_generator = AIGenerator(provider='zhipu')
            is_confused = any(k in question_content for k in CONFUSED_KEYWORDS)
            final_context = _build_final_context(
                is_confused,
                context_text,
                rag_context_text,
                current_section_id=current_section_id,
                current_page_content=current_page_content[:1200],
                kb_context_text=kb_context_text or None,
            )

            ai_start = time.perf_counter()
            answer_parts = []
            for delta in ai_generator.stream_chat_reply(
                question=question_content,
                history=formatted_history,
                context=final_context
            ):
                if not delta:
                    continue
                answer_parts.append(delta)
                yield _sse_event("delta", {"text": delta})

            answer_content = "".join(answer_parts).strip()
            if not answer_content:
                answer_content = "系统忙，请稍后再试"
            ai_elapsed_ms = int((time.perf_counter() - ai_start) * 1000)

            understanding_level = "partial"
            supplement_content = ""
            adjusted_script = ""  # 新增：调整后的讲稿
            if is_confused:
                understanding_level = "none"
                adjust_prompt = f"学生对‘{context_text[:100]}’不理解，请用极简的生活化类比再讲一遍（150字以内）。"
                supplement_content = ai_generator.generate_reply(adjust_prompt)
                
                # 【创新点四】生成简化版讲稿
                simplify_prompt = f"""
学生对以下内容理解困难：
{context_text[:500]}

请将上述内容改写为通俗易懂版本，要求：
1. 使用生活化的语言和比喻
2. 增加2-3个具体例子
3. 避免专业术语，或对术语进行解释
4. 保持200-300字
5. 语气要温和、鼓励
"""
                adjusted_script = ai_generator.generate_reply(simplify_prompt)
                print(f"[讲授节奏调整-流式] 已生成简化版讲稿（{len(adjusted_script)}字）")
            elif any(k in question_content for k in ["懂了", "明白了", "理解了", "清楚了", "会了", "掌握了", "明确了"]):
                understanding_level = "full"
            # 部分理解的判断（新增）
            elif any(k in question_content for k in ["有点懂", "大概明白", "基本理解", "还有点", "不太确定", "有点模糊"]):
                understanding_level = "partial"
            # 根据问题类型判断理解程度
            elif "是什么" in question_content or "定义" in question_content or "概念" in question_content:
                understanding_level = "partial"
            elif "为什么" in question_content and len(question_content) > 20:
                understanding_level = "partial"
            elif "怎么做" in question_content or "如何" in question_content or "步骤" in question_content:
                understanding_level = "partial"
            elif "举例" in question_content or "例子" in question_content or "比如" in question_content:
                understanding_level = "partial"
            elif "公式" in question_content or "计算" in question_content:
                if "推导" in question_content or "原理" in question_content:
                    understanding_level = "partial"
                else:
                    understanding_level = "none"
            elif len(question_content) < 10:
                if any(k in question_content for k in ["？", "?", "啥", "什么", "呢"]):
                    understanding_level = "none"
                else:
                    understanding_level = "partial"
            elif len(question_content) > 50:
                understanding_level = "partial"

            audio_url = ""
            qa_record = QARecord(
                answer_id=answer_id,
                session_id=session_id,
                question_type=question_type,
                question_content=question_content,
                answer_content=answer_content,
                answer_type='text',
                answer_audio_url=audio_url,
                related_knowledge_id=related_knowledge.get('knowledgeId'),
                related_knowledge_name=related_knowledge.get('knowledgeName'),
                related_section_id=related_knowledge.get('relatedSectionId'),
                understanding_level=understanding_level,
                suggestions=json.dumps(["需要我举例吗？", "哪里觉得难？"], ensure_ascii=False)
            )
            db.session.add(qa_record)
            
            # 【创新点四】保存节奏调整记录
            if understanding_level == 'none' and adjusted_script:
                rhythm_record = RhythmAdjustment(
                    user_id=str(current_user_id),
                    lesson_id=str(lesson_id),
                    current_section_id=current_section_id,
                    understanding_level=understanding_level,
                    qa_record_id=answer_id,
                    adjust_type='simplify',
                    supplement_content=supplement_content
                )
                db.session.add(rhythm_record)
                print(f"[讲授节奏调整-流式] 已保存调整记录到数据库")
            
            db.session.commit()

            total_elapsed_ms = int((time.perf_counter() - req_start) * 1000)
            print(
                f"[QA流式性能] total={total_elapsed_ms}ms, ai={ai_elapsed_ms}ms, "
                f"tts={tts_elapsed_ms}ms, questionType={question_type}"
            )

            yield _sse_event("done", {
                "answerId": answer_id,
                "answerContent": answer_content,
                "audioUrl": audio_url,
                "understandingLevel": understanding_level,
                "supplementContent": supplement_content,
                "adjustedScript": adjusted_script,
                "sessionId": session_id,
                "knowledgeCitations": knowledge_citations,
                "coursewareCitations": courseware_citations,
            })
        except Exception as e:
            print(f"AI Stream Error: {e}")
            db.session.rollback()
            yield _sse_event("error", {"message": "系统忙，请稍后再试"})

    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive"
        }
    )


@qa_bp.route("/vision", methods=["POST"])
@jwt_required()
def qa_vision_explain():
    """
    课件预览中点击 Paddle 识别的配图区域：截取区域图 + 课程上下文，调用通义千问视觉作答。
    需配置 DASHSCOPE_API_KEY；不参与 enc 签名校验（请求体含大图）。
    """
    try:
        data = request.get_json(silent=True) or {}
        image = data.get("imageBase64") or data.get("image") or ""
        question = (data.get("questionContent") or data.get("question") or "").strip()
        user_ctx = (data.get("contextText") or data.get("currentPageContent") or "").strip()
        lesson_id = data.get("lessonId") or data.get("courseId")
        current_section_id = data.get("currentSectionId")
        page_num = data.get("pageNum")
        file_name = (data.get("fileName") or "").strip()

        if page_num is not None and current_section_id is None:
            try:
                current_section_id = f"sec{int(page_num)}"
            except (TypeError, ValueError):
                current_section_id = data.get("currentSectionId")
        if isinstance(current_section_id, int):
            current_section_id = f"sec{current_section_id}"
        elif (
            current_section_id
            and not str(current_section_id).startswith("sec")
            and str(current_section_id).isdigit()
        ):
            current_section_id = f"sec{int(current_section_id)}"

        if not (image or "").strip():
            return api_response(code=400, msg="缺少配图数据 imageBase64")

        # 防止异常超大 body 拖垮内存（约 12MB base64）
        img_len = len((image or "").strip())
        if img_len > 12_000_000:
            return jsonify(
                {
                    "code": 400,
                    "msg": "配图数据过大，请缩小选区或刷新页面后重试",
                    "data": {},
                    "requestId": f"req{int(time.time())}{uuid.uuid4().hex[:6]}",
                }
            ), 200

        server_ctx = ""
        if lesson_id:
            try:
                ct, _, _, _ = _resolve_lesson_context(
                    lesson_id,
                    current_section_id,
                    question or "插图内容",
                    allow_rebuild=False,
                )
                server_ctx = (ct or "").strip()
            except Exception as e:
                print(f"[QA视觉] 加载课件上下文失败: {e}")

        meta_lines = []
        if file_name:
            meta_lines.append(f"当前课件文件名：{file_name}")
        if page_num is not None:
            meta_lines.append(f"学生点击的页码：第 {page_num} 页")

        parts = []
        if meta_lines:
            parts.append("\n".join(meta_lines))
        if server_ctx:
            parts.append("【本页课程文本/讲稿上下文】\n" + server_ctx[:6000])
        if user_ctx:
            parts.append("【当前页可见文字摘录】\n" + user_ctx[:4000])
        full_context = "\n\n".join(parts)

        default_q = (
            "请结合上述课程上下文，说明这张插图展示了什么、关键信息是什么，"
            "以及它与当前页知识点有什么关系。若图中有公式、图表或示意图请逐项说明。"
        )
        answer, err = qwen_vl_chat(image, question or default_q, full_context)
        if err:
            safe_err = (err or "").replace("\x00", "")
            return (
                jsonify(
                    {
                        "code": 500,
                        "msg": safe_err,
                        "data": {},
                        "requestId": f"req{int(time.time())}{uuid.uuid4().hex[:6]}",
                    }
                ),
                200,
            )

        safe_answer = (answer or "").replace("\x00", "")
        return api_response(
            data={
                "answerContent": safe_answer,
                "visionModel": os.environ.get("QWEN_VL_MODEL", "qwen-vl-plus"),
            }
        )
    except Exception as e:
        print(f"[QA视觉] 未处理异常: {e}")
        import traceback

        traceback.print_exc()
        # 统一 HTTP 200 + 业务 code，避免浏览器报「500 + 红字」且前端仍可读 msg
        return (
            jsonify(
                {
                    "code": 500,
                    "msg": f"视觉接口异常: {str(e)[:800]}",
                    "data": {},
                    "requestId": f"req{int(time.time())}{uuid.uuid4().hex[:6]}",
                }
            ),
            200,
        )


# ==================== 2.2.2 语音提问识别接口 ====================
@qa_bp.route('/voiceToText', methods=['POST'])
@verify_signature
@jwt_required()
def voice_to_text():
    """
    接口功能：将学生语音提问转换为文字
    （实际比赛建议接入 Whisper 或 阿里/百度 API，此处保持结构完整）
    """
    data = request.get_json()
    voice_url = data.get('voiceUrl')
    
    if not voice_url:
        return api_response(code=400, msg='语音文件URL不能为空')
    
    # 模拟识别过程
    return api_response(data={
        'text': '识别到的模拟语音文字内容',
        'confidence': 0.98,
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
    }, msg='语音识别成功')


# ==================== 辅助查询接口 ====================
@qa_bp.route('/history/<session_id>', methods=['GET'])
@jwt_required()
def get_qa_history(session_id):
    """获取指定会话的问答历史"""
    records = QARecord.query.filter_by(session_id=session_id)\
        .order_by(QARecord.create_time.asc()).all()
    
    return api_response(data=[record.to_dict() for record in records])


@qa_bp.route('/audio/<path:filename>', methods=['GET'])
def serve_qa_audio(filename):
    """静态文件服务：提供问答生成的音频下载"""
    return send_from_directory(os.path.join('uploads', 'tts'), filename)