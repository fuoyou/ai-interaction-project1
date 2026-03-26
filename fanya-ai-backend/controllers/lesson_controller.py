from flask import Blueprint, request, jsonify, send_from_directory, current_app
from flask_jwt_extended import get_jwt_identity, jwt_required
from models.lesson import Lesson, ScriptSection
from models.user import User
from extensions import db
import os
import uuid
import json
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed

from utils import tts_utils 
from utils.file_utils import ppt_to_pdf
from utils.normalize import pages_from_paddle_jsonl_lines, content_list_from_paddle_doc
from utils.paddle_client import run_parse_pipeline
from utils.ai_utils import AIGenerator, get_ai_generator
from utils.api_utils import verify_signature, api_response
from utils.kb_category import normalize_kb_category_id
from utils.rag_utils import build_rag_chunks, dumps_rag_chunks, loads_rag_chunks

lesson_bp = Blueprint('lesson', __name__)

# 与进程「当前工作目录」无关：uploads / 解析日志固定在后端项目根下的 uploads
_BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_UPLOADS_DIR = os.path.join(_BACKEND_ROOT, "uploads")
_PARSE_ERROR_LOG = os.path.join(_UPLOADS_DIR, "parse_errors.log")

if not os.path.exists(_UPLOADS_DIR):
    os.makedirs(_UPLOADS_DIR, exist_ok=True)


def _quiz_context_text_from_lesson(lesson) -> str:
    """测验生成用上下文：讲稿 → RAG 切片 → Paddle 版面文本（不再从文件做 Python 抽字）。"""
    script_content = json.loads(lesson.script_content) if lesson.script_content else []
    script_text = " ".join(
        [
            (s.get("content") or s.get("script") or "").strip()
            for s in script_content
            if isinstance(s, dict)
        ]
    )
    if script_text.strip():
        return script_text
    if lesson.rag_chunks:
        try:
            chunks = loads_rag_chunks(lesson.rag_chunks)
            return " ".join(chunks)
        except Exception:
            pass
    if lesson.structure_data:
        try:
            sp = json.loads(lesson.structure_data)
            parts = []
            for p in sp.get("paddlePages") or []:
                md = p.get("markdown")
                if isinstance(md, str) and md.strip():
                    parts.append(md.strip())
                    continue
                for b in p.get("blocks") or []:
                    t = (b.get("text") or "").strip()
                    if t:
                        parts.append(t)
            return " ".join(parts)
        except Exception:
            pass
    return ""


def _append_parse_error_log(
    message: str,
    *,
    traceback_text: str | None = None,
    lesson: Lesson | None = None,
    lesson_id: int | None = None,
) -> None:
    """追加写入 <后端根>/uploads/parse_errors.log（绝对路径，不受启动目录影响）。"""
    try:
        if lesson is not None:
            lid = lesson.id
            pid = lesson.parse_id or ""
            fname = lesson.file_name or ""
            furl = lesson.file_url or ""
        else:
            lid = lesson_id
            pid = fname = furl = ""
        os.makedirs(_UPLOADS_DIR, exist_ok=True)
        rec = {
            "time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "lessonId": lid,
            "parseId": pid,
            "fileName": fname,
            "fileUrl": furl,
            "message": message,
        }
        with open(_PARSE_ERROR_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            if traceback_text:
                f.write(traceback_text.rstrip() + "\n")
            f.write("---\n")
            f.flush()
    except Exception as log_e:
        print(
            f"[parse_errors.log] 写入失败: {log_e} | 请检查路径是否存在、是否可写: {_PARSE_ERROR_LOG}",
            flush=True,
        )


def _lesson_fail_parse(
    lesson: Lesson, message: str, traceback_text: str | None = None
) -> None:
    """标记课件解析失败，并写入 structure_data.parseError 供前端展示。"""
    try:
        prev = json.loads(lesson.structure_data) if lesson.structure_data else {}
        if not isinstance(prev, dict):
            prev = {}
    except Exception:
        prev = {}
    prev["parseError"] = message
    prev.setdefault("paddlePages", [])
    prev.setdefault("chapters", [])
    lesson.structure_data = json.dumps(prev, ensure_ascii=False)
    lesson.task_status = "failed"
    lesson.page_count = 0
    try:
        db.session.commit()
    except Exception as ce:
        print(f"[课件解析失败] 提交 structure_data 失败: {ce}")
        _append_parse_error_log(
            f"{message} | 且写入数据库失败: {ce}",
            traceback_text=traceback.format_exc(),
            lesson=lesson,
        )
        raise
    print(f"[课件解析失败] {lesson.parse_id}: {message}")
    _append_parse_error_log(message, traceback_text=traceback_text, lesson=lesson)


# ==================== 2.1.1 课件上传与解析接口 ====================
@lesson_bp.route('/parse', methods=['POST'])
@jwt_required()
def parse_lesson():
    try:
        current_user_id = get_jwt_identity()
        school_id = request.form.get('schoolId', 'sch10001')
        course_id = normalize_kb_category_id(request.form.get('courseId', 'default')) or 'default'
        
        if 'file' not in request.files:
            return api_response(code=400, msg='请上传课件文件')
        
        file = request.files['file']
        if file.filename == '':
            return api_response(code=400, msg='文件名不能为空')
        
        file_ext = file.filename.rsplit('.', 1)[-1].lower()
        if file_ext not in ['pdf', 'ppt', 'pptx']:
            return api_response(code=400, msg='仅支持PDF、PPT、PPTX格式')

        if not os.environ.get("PADDLE_OCR_TOKEN", "").strip():
            return api_response(
                code=400,
                msg='服务端未配置 PaddleOCR（PADDLE_OCR_TOKEN），无法解析课件，请联系管理员',
            )
        
        # 保存原始文件
        filename = str(uuid.uuid4()) + '.' + file_ext
        file_path = os.path.join(_UPLOADS_DIR, filename)
        file.save(file_path)
        
        # 上传接口只做快速落盘，避免同步 PPT 转换导致“正在上传”卡很久
        file_size = os.path.getsize(file_path)
        parse_id = f"parse{int(time.time())}{uuid.uuid4().hex[:6]}"
        
        lesson = Lesson(
            parse_id=parse_id,
            school_id=school_id,
            user_id=str(current_user_id),
            course_id=course_id,
            file_name=file.filename,
            file_url=filename,
            file_type=file_ext,
            file_size=file_size,
            task_status='processing'
        )
        db.session.add(lesson)
        db.session.commit()
        
        app_obj = current_app._get_current_object()
        threading.Thread(target=process_lesson_parse, args=(app_obj, lesson.id, file_path)).start()
        
        return api_response(data={
            "id": lesson.id,
            "parseId": parse_id,
            "fileInfo": {
                "fileName": file.filename,
                "fileSize": file_size,
                "pageCount": 0
            },
            "taskStatus": "processing"
        }, msg="课件上传成功，解析任务已提交")
        
    except Exception as e:
        return api_response(code=500, msg=f"上传失败: {str(e)}")


def process_lesson_parse(app_obj, lesson_id, file_path):
    """【核心亮点】：异步流式解析、上下文连续生成、情绪化语音合成、多维AI图谱分析"""
    with app_obj.app_context():
        try:
            lesson = Lesson.query.get(lesson_id)
        except Exception as qe:
            _append_parse_error_log(
                f"查询课件记录失败: {qe}",
                traceback_text=traceback.format_exc(),
                lesson_id=lesson_id,
            )
            return
        if not lesson:
            _append_parse_error_log(
                "解析线程启动时未找到对应课件记录（lesson_id 无效或已删除）",
                lesson_id=lesson_id,
            )
            return

        try:
            if not os.environ.get("PADDLE_OCR_TOKEN", "").strip():
                _lesson_fail_parse(lesson, "未配置 PADDLE_OCR_TOKEN，无法进行 PaddleOCR-VL 解析")
                return

            # 0. PPT/PPTX → PDF（仅 WPS COM / PowerPoint COM，见 file_utils.ppt_to_pdf）
            if lesson.file_type in ['ppt', 'pptx']:
                lesson.task_status = 'converting_pdf'
                db.session.commit()
                try:
                    print(f"[PPT] convert start: {file_path}")
                    pdf_path = ppt_to_pdf(file_path)
                    if not pdf_path or not os.path.exists(pdf_path):
                        _lesson_fail_parse(
                            lesson,
                            "PPT/PPTX 转 PDF 失败，请在本机安装 WPS 演示或 Microsoft PowerPoint，并确保 COM 可用",
                        )
                        return
                    lesson.file_url = os.path.basename(pdf_path)
                    lesson.file_type = 'pdf'
                    lesson.file_size = os.path.getsize(pdf_path)
                    db.session.commit()
                    file_path = pdf_path
                    print(f"[PPT] convert success: {pdf_path}")
                except Exception as e:
                    print(f"[PPT] convert exception: {e}")
                    _lesson_fail_parse(lesson, f"PPT/PPTX 转 PDF 异常: {e}")
                    return

            # 1. 仅使用 PaddleOCR-VL 解析 PDF（不再使用 Python 抽取 PDF/PPT 文字）
            content_list = []
            paddle_pages = []
            if lesson.file_type != 'pdf':
                _lesson_fail_parse(lesson, "内部错误：课件应已转换为 PDF")
                return

            lesson.task_status = 'paddle_parsing'
            db.session.commit()
            try:
                print(f"[Paddle] 开始解析 PDF: {file_path}")
                _, lines = run_parse_pipeline(file_path)
                paddle_doc = pages_from_paddle_jsonl_lines(lines)
                paddle_pages = paddle_doc.get("pages") or []
                content_list = content_list_from_paddle_doc(paddle_doc)
                print(
                    f"[Paddle] 解析完成，共 {len(content_list)} 页，"
                    f"{sum(len(p.get('blocks') or []) for p in paddle_pages)} 个分块"
                )
            except Exception as e:
                import traceback
                traceback.print_exc()
                _lesson_fail_parse(lesson, f"PaddleOCR-VL 解析失败: {e}")
                return

            if not content_list or not any((s or "").strip() for s in content_list):
                _lesson_fail_parse(lesson, "PaddleOCR-VL 未识别到有效页面内容")
                return

            lesson.page_count = len(content_list)
            # 2. RAG 索引改为并行构建，避免阻塞讲稿主链路
            rag_future = None
            rag_pool = None
            if content_list:
                rag_pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix='rag')
                rag_future = rag_pool.submit(build_rag_chunks, content_list, 500)
            
            # 3. 构建初步知识点结构
            chapters = []
            if content_list:
                for i, content in enumerate(content_list[:10]):
                    if content.strip():
                        chapters.append({
                            "chapterId": f"chap{i+1:03d}",
                            "chapterName": f"第{i+1}章节预览",
                            "subChapters": [{
                                "subChapterId": f"sub{i+1:03d}",
                                "subChapterName": content[:30] + "...",
                                "isKeyPoint": True,
                                "pageRange": str(i+1)
                            }]
                        })
            lesson.structure_data = json.dumps(
                {"chapters": chapters, "paddlePages": paddle_pages},
                ensure_ascii=False,
            )
            
            # 标记为讲稿生成中（paddlePages 大时原 TEXT 64KB 不够会导致 1406，已迁移 LONGTEXT）
            lesson.task_status = 'generating_script'
            try:
                db.session.commit()
            except Exception as c_err:
                db.session.rollback()
                err_s = str(c_err)
                lesson = Lesson.query.get(lesson_id)
                if not lesson:
                    _append_parse_error_log(
                        f"提交 structure_data 失败且回滚后无法重载 lesson: {err_s}",
                        traceback_text=traceback.format_exc(),
                        lesson_id=lesson_id,
                    )
                    return
                if "Data too long" in err_s or "1406" in err_s:
                    _lesson_fail_parse(
                        lesson,
                        "课件版面数据超过数据库字段长度（structure_data）。请重启后端完成库迁移（structure_data→LONGTEXT）后重新上传。",
                        traceback_text=traceback.format_exc(),
                    )
                    return
                raise
            
            script_sections = []
            section_audios = []
            ai_generator = get_ai_generator()

            def _build_page_prompt(i, page_content):
                # 关键约束：讲稿内容必须优先基于“当前页”，避免跨页臆测，保证教学相关度
                if i == 0:
                    return f"""你是一位富有激情的大学教师。请为课件第1页生成充满活力的开场白讲解。
                    【当前页原文】：{page_content[:1000]}
                    要求：
                    - 以“同学们好，今天我们开始学习...”自然开场。
                    - 只可基于当前页原文进行讲解，不得引入未出现的信息。
                    - 语气亲切、充满期待，180字以内。
                    - 只输出讲解稿。"""
                return f"""你是一位正在连续授课的专业大学教师。请自然衔接上一页内容并讲解当前页。
                    【当前页原文】："{page_content[:1000]}"
                    要求：
                    - **严禁**再次使用“同学们好”或“大家好”等任何形式的开场白。
                    - 允许先用一句过渡语（例如“接下来我们看这一页”），但知识点解释必须全部来自当前页原文。
                    - 若当前页信息不足，请明确说明“本页主要给出提示/标题”，不要补充未出现知识。
                    - 语气口语化，180字以内。
                    - 只输出讲解稿。"""

            def _gen_page_script(task):
                i, page_text = task
                page_content = page_text.strip() if page_text else ""
                if not page_content:
                    # 该页为纯图片/图表页，无可提取文本，给出提示性占位讲稿
                    return i, f"请大家看第{i+1}页的图示内容。这一页主要通过图表或图片来呈现知识点，请结合上下文仔细观察。"
                try:
                    prompt = _build_page_prompt(i, page_content)
                    lecture_content = ai_generator.generate_reply(prompt, max_tokens=220)
                    return i, lecture_content
                except Exception:
                    return i, f"我们来看第{i+1}页的内容。{page_content[:100]}..."

            # 4. 讲稿并行生成（3线程）
            scripts_by_page = {}
            with ThreadPoolExecutor(max_workers=3, thread_name_prefix='script') as pool:
                futures = {
                    pool.submit(_gen_page_script, (i, page_text)): i
                    for i, page_text in enumerate(content_list)
                }
                for future in as_completed(futures):
                    i = futures[future]
                    try:
                        page_idx, lecture_content = future.result()
                    except Exception as e:
                        page_idx = i
                        lecture_content = f"第{page_idx+1}页讲稿生成失败，请稍后重试。"
                        print(f"讲稿并行任务异常: {e}")

                    scripts_by_page[page_idx] = lecture_content
                    partial_sections = [
                        {"page": idx + 1, "content": scripts_by_page[idx]}
                        for idx in sorted(scripts_by_page.keys())
                    ]
                    lesson.script_content = json.dumps(partial_sections, ensure_ascii=False)
                    if not lesson.script_id:
                        lesson.script_id = f"script{int(time.time())}{uuid.uuid4().hex[:6]}"
                    lesson.task_status = 'generating_script'
                    try:
                        db.session.commit()
                    except Exception as commit_err:
                        print(f"数据库提交失败，正在回滚: {commit_err}")
                        db.session.rollback()
                    print(f"  [讲稿并行] 已完成 {len(scripts_by_page)}/{len(content_list)} 页")

            script_sections = [
                {"page": i + 1, "content": scripts_by_page.get(i, "")}
                for i in range(len(content_list))
            ]
            lesson.script_content = json.dumps(script_sections, ensure_ascii=False)
            
            # --- 整合块 1: 生成思维导图和知识图谱 ---
            try:
                print("[AI] 开始生成思维导图和知识图谱...")
                mindmap_data = generate_mindmap(ai_generator, content_list, script_sections)
                knowledge_graph_data = generate_knowledge_graph(ai_generator, content_list, script_sections)
                lesson.mindmap_data = json.dumps(mindmap_data, ensure_ascii=False)
                lesson.knowledge_graph_data = json.dumps(knowledge_graph_data, ensure_ascii=False)
                print("[AI] 思维导图和知识图谱生成完成")
            except Exception as e:
                print(f"[AI] 生成思维导图/知识图谱失败: {e}")
                import traceback
                traceback.print_exc()

            # --- 整合块 2: 【智能插旗】生成考点和题目 ---
            try:
                from utils.checkpoint_utils import generate_checkpoints
                checkpoints = generate_checkpoints(content_list, script_sections, ai_generator)
                lesson.checkpoints = json.dumps(checkpoints, ensure_ascii=False)
                print(f"  [智能插旗] 已生成 {len(checkpoints)} 个考点")
            except Exception as checkpoint_error:
                print(f"  [智能插旗] 考点生成失败: {checkpoint_error}")
                import traceback
                traceback.print_exc()
                lesson.checkpoints = json.dumps([], ensure_ascii=False)

            # 讲稿主链路完成后再同步写入 RAG，确保不拖慢讲稿可用时间
            if rag_future:
                try:
                    rag_chunks = rag_future.result(timeout=20)
                    lesson.rag_chunks = dumps_rag_chunks(rag_chunks or [])
                except Exception as e:
                    print(f"RAG 并行构建失败（不影响讲稿主流程）: {e}")
                finally:
                    rag_pool.shutdown(wait=False)
            
            try:
                db.session.commit()
            except Exception as commit_err:
                print(f"数据库提交失败，正在回滚: {commit_err}")
                db.session.rollback()

            def _gen_page_audio(task):
                i, lecture_content = task
                v_rate = "+8%" if i == 0 else "+0%"
                v_pitch = "+5Hz" if i == 0 else "+0Hz"
                audio_filename = f"lesson_{lesson.id}_p{i+1}_{uuid.uuid4().hex[:6]}.mp3"
                try:
                    saved_filename = tts_utils.text_to_speech(
                        lecture_content,
                        audio_filename,
                        rate=v_rate,
                        pitch=v_pitch
                    )
                    if saved_filename:
                        return i, f'/api/v1/lesson/audio/{saved_filename}'
                    print(f"第 {i+1} 页音频生成失败，将由前端浏览器TTS接管")
                    return i, ""
                except Exception as e:
                    print(f"音频并行任务异常: {e}")
                    return i, ""

            # 5. 音频并行生成（4线程）
            audio_map = {}
            with ThreadPoolExecutor(max_workers=4, thread_name_prefix='tts') as pool:
                futures = {
                    pool.submit(_gen_page_audio, (i, section["content"])): i
                    for i, section in enumerate(script_sections)
                }
                for future in as_completed(futures):
                    i = futures[future]
                    try:
                        page_idx, audio_url = future.result()
                    except Exception:
                        page_idx, audio_url = i, ""

                    audio_map[page_idx] = audio_url
                    ready_audios = [
                        {"page": idx + 1, "audioUrl": audio_map[idx], "duration": 30}
                        for idx in sorted(audio_map.keys())
                        if audio_map[idx]
                    ]
                    audio_info = {
                        "totalDuration": len(ready_audios) * 30,
                        "fileSize": 0,
                        "format": "mp3",
                        "bitRate": 128000,
                        "sectionAudios": ready_audios
                    }
                    lesson.audio_sections = json.dumps(audio_info, ensure_ascii=False)
                    if 0 in audio_map and audio_map[0]:
                        lesson.audio_url = audio_map[0]
                    lesson.task_status = 'generating_script'
                    try:
                        db.session.commit()
                    except Exception as commit_err:
                        print(f"数据库提交失败，正在回滚: {commit_err}")
                        db.session.rollback()
                    print(f"  [音频并行] 已完成 {len(audio_map)}/{len(script_sections)} 页")

            final_audios = [
                {"page": idx + 1, "audioUrl": audio_map[idx], "duration": 30}
                for idx in sorted(audio_map.keys())
                if audio_map[idx]
            ]
            lesson.audio_sections = json.dumps({
                "totalDuration": len(final_audios) * 30,
                "fileSize": 0,
                "format": "mp3",
                "bitRate": 128000,
                "sectionAudios": final_audios
            }, ensure_ascii=False)
            lesson.task_status = 'completed'
            try:
                db.session.commit()
            except Exception as commit_err:
                print(f"最终提交失败，正在回滚: {commit_err}")
                db.session.rollback()
            print(f"课件解析及并行生成全部完成: {lesson.parse_id}")

            # 解析完成后异步生成缩略图，不阻塞主流程
            _final_file_path = file_path
            def _async_thumbnail(fp):
                try:
                    from utils.file_utils import get_or_create_thumbnail
                    get_or_create_thumbnail(fp, generate=True)
                except Exception as thumb_err:
                    print(f"[Thumbnail] 异步生成失败: {thumb_err}")
            threading.Thread(
                target=_async_thumbnail,
                args=(_final_file_path,),
                daemon=True,
                name="thumbnail-gen"
            ).start()
            
        except Exception as e:
            tb = traceback.format_exc()
            print(f"任务执行失败: {e}")
            traceback.print_exc()
            try:
                db.session.rollback()
                lesson = Lesson.query.get(lesson_id)
                if lesson:
                    # 与「显式 _lesson_fail_parse」区分：此处为未预料异常，仍写入 parseError 便于前端与排查
                    _lesson_fail_parse(
                        lesson,
                        f"任务处理异常: {str(e)[:1800]}",
                        traceback_text=tb,
                    )
            except Exception as persist_err:
                print(f"写入 parseError 失败: {persist_err}")
                traceback.print_exc()
                les = Lesson.query.get(lesson_id)
                _append_parse_error_log(
                    f"_lesson_fail_parse 未生效: {persist_err} | 原异常: {str(e)[:500]}",
                    traceback_text=traceback.format_exc(),
                    lesson=les,
                    lesson_id=lesson_id if les is None else None,
                )
                try:
                    db.session.rollback()
                    lesson = Lesson.query.get(lesson_id)
                    if lesson:
                        lesson.task_status = "failed"
                        db.session.commit()
                except Exception:
                    db.session.rollback()


# ==================== 2.1.2 智课脚本生成接口 ====================
@lesson_bp.route('/generateScript', methods=['POST'])
@verify_signature
@jwt_required()
def generate_script():
    data = request.get_json()
    parse_id = data.get('parseId')
    scripts = data.get('scripts') 
    
    # 同时支持数字ID和字符串parseId查询
    lesson = None
    if parse_id:
        # 先尝试按parse_id查询
        lesson = Lesson.query.filter_by(parse_id=parse_id).first()
        # 如果没找到且parse_id是数字，尝试按id查询
        if not lesson and str(parse_id).isdigit():
            lesson = Lesson.query.get(int(parse_id))
    
    if not lesson:
        return api_response(code=404, msg='课件不存在')
    
    if scripts:
        lesson.script_content = json.dumps(scripts, ensure_ascii=False)
        db.session.commit()
        return api_response(data={"scriptId": lesson.script_id}, msg="脚本保存成功")

    return api_response(data={
        "scriptId": lesson.script_id,
        "scriptStructure": json.loads(lesson.script_content) if lesson.script_content else []
    })


# ==================== 结合知识库重新生成讲稿（异步任务）====================
@lesson_bp.route('/regenerateScriptWithKnowledge', methods=['POST'])
@jwt_required()
def regenerate_script_with_knowledge():
    """发起异步任务：结合知识库重新生成所有页讲稿，保存到数据库"""
    try:
        current_user_id = get_jwt_identity()
        data = request.get_json()
        lesson_id = data.get('lessonId')
        knowledge_doc_ids = data.get('knowledgeDocIds', [])

        if not lesson_id:
            return api_response(code=400, msg='lessonId不能为空')

        lesson = Lesson.query.get(int(lesson_id)) if str(lesson_id).isdigit() else Lesson.query.filter_by(parse_id=lesson_id).first()
        if not lesson:
            return api_response(code=404, msg='课件不存在')
        if str(lesson.user_id) != str(current_user_id):
            return api_response(code=403, msg='无权限')

        # 标记为重新生成中
        lesson.task_status = 'regenerating_script'
        db.session.commit()

        app_obj = current_app._get_current_object()
        threading.Thread(
            target=_do_regenerate_script,
            args=(app_obj, lesson.id, knowledge_doc_ids),
            daemon=True
        ).start()

        return api_response(data={'lessonId': lesson.id, 'taskStatus': 'regenerating_script'}, msg='讲稿重新生成任务已提交')
    except Exception as e:
        db.session.rollback()
        return api_response(code=500, msg=f'提交任务失败: {str(e)}')


def _do_regenerate_script(app_obj, lesson_id, knowledge_doc_ids):
    """后台线程：结合知识库逐页重新生成讲稿并实时保存到数据库"""
    from utils.rag_utils import loads_rag_chunks, get_rag_context
    from models.knowledge import KnowledgeDoc

    with app_obj.app_context():
        lesson = Lesson.query.get(lesson_id)
        if not lesson:
            return
        try:
            # 加载知识库RAG上下文
            knowledge_context = ''
            if knowledge_doc_ids:
                all_chunks = []
                for doc_id in knowledge_doc_ids:
                    doc = KnowledgeDoc.query.get(int(doc_id))
                    if doc and doc.rag_chunks:
                        chunks = loads_rag_chunks(doc.rag_chunks)
                        all_chunks.extend(chunks)
                if all_chunks:
                    knowledge_context = get_rag_context(all_chunks, '', top_k=20)

            # 读取现有讲稿
            existing_scripts = []
            if lesson.script_content:
                try:
                    existing_scripts = json.loads(lesson.script_content)
                except Exception:
                    existing_scripts = []

            if not existing_scripts:
                lesson.task_status = 'regen_failed'
                db.session.commit()
                return

            ai_gen = get_ai_generator()
            new_scripts = [item.copy() for item in existing_scripts]  # 深拷贝
            total_pages = len(new_scripts)

            def regen_page(idx, item):
                page = item.get('page', 0)
                original = item.get('content', '')
                if not original.strip():
                    return idx, item
                # 前后页上下文（用原始讲稿保证一致性）
                prev_content = new_scripts[idx - 1].get('content', '')[-120:] if idx > 0 else ''
                next_content = new_scripts[idx + 1].get('content', '')[:120] if idx < len(new_scripts) - 1 else ''
                context_hint = ''
                if prev_content:
                    context_hint += f'【上一页结尾】{prev_content}\n'
                if next_content:
                    context_hint += f'【下一页开头】{next_content}\n'
                if knowledge_context:
                    prompt = (
                        f"请结合以下知识库资料，对第{page}页讲稿进行优化和扩充，要求逻辑清晰、内容丰富、适合教学讲解，"
                        f"并确保与前后页自然衔接、逻辑连贯，直接输出讲稿正文，不要输出任何前缀或解释。\n\n"
                        f"知识库资料（参考）：\n{knowledge_context}\n\n"
                        + (f"前后页参考：\n{context_hint}\n" if context_hint else "")
                        + f"原始讲稿：\n{original}"
                    )
                else:
                    prompt = (
                        f"请对以下第{page}页讲稿进行优化和扩充，要求逻辑清晰、内容丰富、适合教学讲解，"
                        f"并确保与前后页自然衔接、逻辑连贯，直接输出讲稿正文，不要输出任何前缀或解释。\n\n"
                        + (f"前后页参考：\n{context_hint}\n" if context_hint else "")
                        + f"原始讲稿：\n{original}"
                    )
                try:
                    result = ai_gen.generate_reply(prompt)
                    content = result.strip() if result else original
                    # 清理 AI 前缀提示语和 markdown 格式
                    import re
                    content = re.sub(r'^#{1,6}\s+.+\n?', '', content, flags=re.MULTILINE)
                    content = re.sub(r'\*\*(.+?)\*\*', r'\1', content)
                    content = re.sub(r'\*(.+?)\*', r'\1', content)
                    content = re.sub(r'^(当然[，,]?|好的[，,]?|以下是[^\n]*[：:]|根据[^\n]*[：:]|下面是[^\n]*[：:]|如下[：:]|优化后的讲稿[：:])[\s\S]*?\n\n?', '', content, flags=re.IGNORECASE)
                    content = re.sub(r'^\*\*.+\*\*\n?', '', content, flags=re.MULTILINE)
                    return idx, {'page': page, 'content': content.strip()}
                except Exception as e:
                    print(f'[重新生成讲稿] 第{page}页失败: {e}')
                    return idx, item

            # 逐页生成并实时保存
            completed = 0
            with ThreadPoolExecutor(max_workers=4, thread_name_prefix='regen') as pool:
                futures = {pool.submit(regen_page, idx, item): idx for idx, item in enumerate(new_scripts)}
                for future in as_completed(futures):
                    try:
                        idx, result = future.result()
                        new_scripts[idx] = result
                        completed += 1
                        # 每完成一页就保存一次
                        lesson.script_content = json.dumps(new_scripts, ensure_ascii=False)
                        lesson.task_status = f'regenerating_script:{completed}/{total_pages}'
                        db.session.commit()
                        print(f'[重新生成讲稿] 课件{lesson_id}进度: {completed}/{total_pages}')
                    except Exception as e:
                        print(f'[重新生成讲稿] 处理失败: {e}')

            # 最终标记为完成
            lesson.script_content = json.dumps(new_scripts, ensure_ascii=False)
            lesson.task_status = 'regen_completed'
            db.session.commit()
            print(f'[重新生成讲稿] 课件{lesson_id}全部完成，共{total_pages}页')

        except Exception as e:
            print(f'[重新生成讲稿] 课件{lesson_id}失败: {e}')
            import traceback
            traceback.print_exc()
            try:
                db.session.rollback()
                lesson.task_status = 'regen_failed'
                db.session.commit()
            except Exception:
                pass


@lesson_bp.route('/regenerateStatus/<int:lesson_id>', methods=['GET'])
@jwt_required()
def get_regenerate_status(lesson_id):
    """轮询：获取讲稿重新生成状态及最新内容"""
    try:
        lesson = Lesson.query.get(lesson_id)
        if not lesson:
            return api_response(code=404, msg='课件不存在')
        script = []
        if lesson.script_content:
            try:
                script = json.loads(lesson.script_content)
            except Exception:
                script = []
        return api_response(data={
            'lessonId': lesson_id,
            'taskStatus': lesson.task_status,
            'script': script
        })
    except Exception as e:
        return api_response(code=500, msg=f'查询失败: {str(e)}')


# ==================== 2.1.3 语音合成接口 ====================
@lesson_bp.route('/generateAudio', methods=['POST'])
@verify_signature
@jwt_required()
def generate_audio():
    return api_response(msg="语音任务已在解析时同步处理完成")


# ==================== 辅助查询接口 ====================
@lesson_bp.route('/detail/<parse_id>', methods=['GET'])
@jwt_required()
def get_lesson_detail(parse_id):
    lesson = Lesson.query.filter_by(parse_id=parse_id).first()
    if not lesson and parse_id.isdigit():
        lesson = Lesson.query.get(int(parse_id))
    
    if not lesson:
        return api_response(code=404, msg='课件不存在')
    
    # 返回完整详情，包括考点与思维导图等
    return api_response(data=lesson.to_dict(include_detail=True))


@lesson_bp.route('/list', methods=['GET'])
@jwt_required()
def get_lesson_list():
    """获取当前用户的课件列表（只读已有缩略图缓存，不阻塞生成）"""
    from utils.file_utils import get_or_create_thumbnail

    current_user_id = get_jwt_identity()
    lessons = Lesson.query.filter_by(user_id=str(current_user_id))\
        .order_by(Lesson.create_time.desc()).all()

    result = []
    for lesson in lessons:
        lesson_dict = lesson.to_dict(include_detail=False)
        if lesson.file_url:
            file_path = os.path.join(_UPLOADS_DIR, lesson.file_url)
            # generate=False：仅读缓存，缩略图不存在时不触发生成，接口立即返回
            thumbnail = get_or_create_thumbnail(file_path, generate=False)
            if thumbnail:
                lesson_dict['thumbnailUrl'] = thumbnail
        result.append(lesson_dict)

    return api_response(data=result)


@lesson_bp.route('/teacher/list', methods=['GET'])
@jwt_required()
def get_teacher_lesson_list():
    """获取所有老师上传的课件列表（供学生查看，只读缩略图缓存）"""
    from models.user import User
    from utils.file_utils import get_or_create_thumbnail

    teacher_users = User.query.filter_by(role='teacher').all()
    teacher_user_ids = [str(user.id) for user in teacher_users]

    if not teacher_user_ids:
        return api_response(data=[])

    lessons = Lesson.query.filter(Lesson.user_id.in_(teacher_user_ids))\
        .order_by(Lesson.create_time.desc()).all()

    result = []
    for lesson in lessons:
        lesson_dict = lesson.to_dict(include_detail=False)

        teacher_id = int(lesson.user_id) if lesson.user_id.isdigit() else None
        if teacher_id:
            teacher = User.query.get(teacher_id)
            if teacher:
                lesson_dict['teacherName'] = teacher.nickname or teacher.username

        if lesson.file_url:
            file_path = os.path.join(_UPLOADS_DIR, lesson.file_url)
            # generate=False：只读缓存，不触发耗时的 WPS/PDF 生成
            thumbnail = get_or_create_thumbnail(file_path, generate=False)
            if thumbnail:
                lesson_dict['thumbnailUrl'] = thumbnail

        result.append(lesson_dict)

    return api_response(data=result)


# ==================== 静态文件服务 (增强防崩逻辑) ====================
@lesson_bp.route('/files/<path:filepath>', methods=['GET'])
def get_file(filepath):
    """支持子目录的文件访问，如 thumbnails/xxx.jpg"""
    file_path = os.path.join(_UPLOADS_DIR, filepath)
    if not os.path.exists(file_path):
        return api_response(code=404, msg="课件文件未找到")
    # 获取文件所在目录和文件名
    directory = os.path.dirname(file_path)
    filename = os.path.basename(file_path)
    if directory:
        return send_from_directory(directory, filename)
    return send_from_directory(_UPLOADS_DIR, filepath)


@lesson_bp.route('/audio/<path:filename>', methods=['GET'])
def serve_audio(filename):
    audio_dir = os.path.join(_UPLOADS_DIR, 'tts')
    target_file = os.path.join(audio_dir, filename)
    
    # 【核心兜底】：如果前端请求的音频文件不存在（可能是生成失败后被删除了），返回系统默认提示音
    # 避免前端抛出 404/500 错误
    if not os.path.exists(target_file):
        fallback_file = os.path.join(audio_dir, 'system_loading.mp3')
        if os.path.exists(fallback_file):
            return send_from_directory(audio_dir, 'system_loading.mp3')
        else:
            return api_response(code=404, msg="音频文件缺失")
            
    return send_from_directory(audio_dir, filename)

# ==================== 删除课件接口 ====================
@lesson_bp.route('/delete', methods=['DELETE'])
@jwt_required()
def delete_lesson():
    """删除课件"""
    try:
        current_user_id = get_jwt_identity()
        
        # 处理 DELETE 请求的 JSON 数据
        data = request.get_json() or {}
        lesson_id = data.get('id')
        
        print(f'[课件删除] 请求数据: {data}')
        print(f'[课件删除] 当前用户: {current_user_id}')
        
        if not lesson_id:
            return api_response(code=400, msg='课件ID不能为空')
        
        # 查询课件
        lesson = None
        if str(lesson_id).isdigit():
            lesson = Lesson.query.get(int(lesson_id))
        if not lesson:
            lesson = Lesson.query.filter_by(parse_id=str(lesson_id)).first()
        
        if not lesson:
            print(f'[课件删除] 课件不存在: {lesson_id}')
            return api_response(code=404, msg='课件不存在')
        
        print(f'[课件删除] 找到课件: id={lesson.id}, user_id={lesson.user_id}')
        
        # 权限检查
        if str(lesson.user_id) != str(current_user_id):
            print(f'[课件删除] 权限检查失败: lesson.user_id={lesson.user_id}, current_user_id={current_user_id}')
            return api_response(code=403, msg='无权限删除他人课件')
        
        # 先删除所有关联的记录（处理外键约束）
        try:
            # 删除关联的 ScriptSection 记录
            deleted_count = ScriptSection.query.filter_by(lesson_id=lesson.id).delete()
            print(f'[课件删除] 已删除 {deleted_count} 条关联脚本记录')
            
            # 删除关联的 Quiz 记录
            from models.quiz import Quiz, QuizAnswer, QuizAttempt
            quiz_count = Quiz.query.filter_by(lesson_id=lesson.id).delete()
            print(f'[课件删除] 已删除 {quiz_count} 条关联测验记录')
            
            # 删除关联的 QuizAnswer 记录
            answer_count = QuizAnswer.query.filter_by(lesson_id=lesson.id).delete()
            print(f'[课件删除] 已删除 {answer_count} 条关联答题记录')
            
            # 删除关联的 QuizAttempt 记录
            attempt_count = QuizAttempt.query.filter_by(lesson_id=lesson.id).delete()
            print(f'[课件删除] 已删除 {attempt_count} 条关联测验尝试记录')
            
            db.session.commit()
        except Exception as e:
            print(f'[课件删除] 删除关联记录失败: {e}')
            db.session.rollback()
        
        # 删除关联的文件
        if lesson.file_url:
            file_path = os.path.join(_UPLOADS_DIR, lesson.file_url)
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    print(f'[课件删除] 已删除课件文件: {file_path}')
                except Exception as e:
                    print(f'[课件删除] 删除课件文件失败: {e}')
        
        # 删除关联的音频文件
        if lesson.audio_sections:
            try:
                audio_info = json.loads(lesson.audio_sections)
                for audio in audio_info.get('sectionAudios', []):
                    audio_url = audio.get('audioUrl', '')
                    if audio_url:
                        filename = audio_url.split('/')[-1]
                        audio_path = os.path.join(_UPLOADS_DIR, 'tts', filename)
                        if os.path.exists(audio_path):
                            try:
                                os.remove(audio_path)
                                print(f'[课件删除] 已删除音频文件: {audio_path}')
                            except Exception as e:
                                print(f'[课件删除] 删除音频文件失败: {e}')
            except Exception as e:
                print(f'[课件删除] 处理音频文件失败: {e}')
        
        # 从数据库删除课件
        try:
            db.session.delete(lesson)
            db.session.commit()
            print(f'[课件删除] 已删除课件记录: {lesson.id}')
            return api_response(msg='课件已成功删除')
        except Exception as e:
            db.session.rollback()
            print(f'[课件删除] 删除课件记录失败: {e}')
            import traceback
            traceback.print_exc()
            return api_response(code=500, msg=f'删除失败: {str(e)}')
    
    except Exception as e:
        db.session.rollback()
        print(f'[课件删除] 异常: {e}')
        import traceback
        traceback.print_exc()
        return api_response(code=500, msg=f'删除失败: {str(e)}')


@lesson_bp.route('/tts/single', methods=['POST'])
@jwt_required()
def generate_single_tts():
    """单页TTS生成接口 - 用于前端点击播放按钮时实时生成"""
    data = request.get_json()
    text = data.get('text', '')
    
    if not text or not text.strip():
        return api_response(code=400, msg='文本内容不能为空')
    
    # 生成唯一文件名
    filename = f"single_{uuid.uuid4().hex[:8]}.mp3"
    
    try:
        saved_name = tts_utils.text_to_speech(text.strip(), filename)
        if saved_name:
            return api_response(data={
                'audioUrl': f'/api/v1/lesson/audio/{saved_name}'
            })
        else:
            return api_response(code=500, msg='语音生成失败')
    except Exception as e:
        print(f"Single TTS error: {e}")
        return api_response(code=500, msg='语音生成失败')


# ==================== 思维导图和知识图谱接口 ====================
@lesson_bp.route('/mindmap/<parse_id>', methods=['GET'])
@jwt_required()
def get_mindmap(parse_id):
    """获取课件思维导图数据"""
    lesson = Lesson.query.filter_by(parse_id=parse_id).first()
    if not lesson and parse_id.isdigit():
        lesson = Lesson.query.get(int(parse_id))
    
    if not lesson:
        return api_response(code=404, msg='课件不存在')
    
    try:
        if lesson.mindmap_data:
            mindmap = json.loads(lesson.mindmap_data)
        else:
            # 如果没有预生成，实时生成
            ai_generator = get_ai_generator()
            content_list = []
            if lesson.script_content:
                script_data = json.loads(lesson.script_content)
                content_list = [s.get('content', '') for s in script_data]
            mindmap = generate_mindmap(ai_generator, content_list, script_data if lesson.script_content else [])
            lesson.mindmap_data = json.dumps(mindmap, ensure_ascii=False)
            db.session.commit()
        
        return api_response(data=mindmap)
    except Exception as e:
        print(f"获取思维导图失败: {e}")
        return api_response(code=500, msg='获取思维导图失败')


@lesson_bp.route('/knowledge-graph/<parse_id>', methods=['GET'])
@jwt_required()
def get_knowledge_graph(parse_id):
    """获取课件知识图谱数据"""
    lesson = Lesson.query.filter_by(parse_id=parse_id).first()
    if not lesson and parse_id.isdigit():
        lesson = Lesson.query.get(int(parse_id))
    
    if not lesson:
        return api_response(code=404, msg='课件不存在')
    
    try:
        if lesson.knowledge_graph_data:
            graph_data = json.loads(lesson.knowledge_graph_data)
        else:
            # 如果没有预生成，实时生成
            ai_generator = get_ai_generator()
            content_list = []
            script_data = []
            if lesson.script_content:
                script_data = json.loads(lesson.script_content)
                content_list = [s.get('content', '') for s in script_data]
            graph_data = generate_knowledge_graph(ai_generator, content_list, script_data)
            lesson.knowledge_graph_data = json.dumps(graph_data, ensure_ascii=False)
            db.session.commit()
        
        return api_response(data=graph_data)
    except Exception as e:
        print(f"获取知识图谱失败: {e}")
        return api_response(code=500, msg='获取知识图谱失败')


# ==================== 思维导图和知识图谱生成辅助函数 ====================
def generate_mindmap(ai_generator, content_list, script_sections):
    """
    基于课件内容生成思维导图数据
    返回树形结构数据，适配前端思维导图组件
    """
    # 合并所有内容用于分析
    all_content = "\n".join([c[:500] for c in content_list if c.strip()])
    all_scripts = "\n".join([s.get('content', '')[:300] for s in script_sections if s.get('content')])
    
    prompt = f"""你是一位专业的教育内容分析师。请根据以下课件内容，生成一个结构化的思维导图。

课件内容摘要：
{all_content[:2000]}

讲稿内容摘要：
{all_scripts[:1500]}

请生成思维导图数据，要求：
1. 中心主题是课件的核心主题
2. 包含3-6个主要分支（一级节点），每个分支代表一个重要知识点或章节
3. 每个主要分支下包含2-4个子分支（二级节点），细化具体内容
4. 如果内容允许，可以有三级节点

请严格按照以下JSON格式输出（不要包含任何其他文字）：
{{
    "root": {{
        "id": "root",
        "text": "中心主题",
        "children": [
            {{
                "id": "1",
                "text": "主要分支1",
                "children": [
                    {{"id": "1-1", "text": "子分支1-1"}},
                    {{"id": "1-2", "text": "子分支1-2"}}
                ]
            }}
        ]
    }}
}}"""
    
    try:
        response = ai_generator.generate_reply(prompt, max_tokens=2000)
        # 提取JSON部分
        json_str = extract_json_from_response(response)
        mindmap_data = json.loads(json_str)
        
        # 确保基本结构存在
        if 'root' not in mindmap_data:
            mindmap_data = {'root': mindmap_data}
        
        return mindmap_data
    except Exception as e:
        print(f"生成思维导图失败: {e}")
        # 返回默认结构
        return generate_default_mindmap(content_list)


def generate_knowledge_graph(ai_generator, content_list, script_sections):
    """
    基于课件内容生成知识图谱数据
    返回节点和边的关系图数据
    """
    # 合并所有内容用于分析
    all_content = "\n".join([c[:500] for c in content_list if c.strip()])
    all_scripts = "\n".join([s.get('content', '')[:300] for s in script_sections if s.get('content')])
    
    prompt = f"""你是一位专业的知识图谱构建专家。请根据以下课件内容，生成一个知识图谱。

课件内容摘要：
{all_content[:2000]}

讲稿内容摘要：
{all_scripts[:1500]}

请生成知识图谱数据，要求：
1. 提取课件中的核心概念作为节点（nodes），每个节点包含：id、name（概念名称）、type（类型：concept/keyword/principle/example）
2. 识别概念之间的关系作为边（edges），每条边包含：source（源节点id）、target（目标节点id）、relation（关系类型，如：包含、属于、导致、应用于等）
3. 节点数量控制在8-15个
4. 边数量控制在10-20条

请严格按照以下JSON格式输出（不要包含任何其他文字）：
{{
    "nodes": [
        {{"id": "n1", "name": "概念1", "type": "concept"}},
        {{"id": "n2", "name": "概念2", "type": "keyword"}},
        {{"id": "n3", "name": "原理1", "type": "principle"}}
    ],
    "edges": [
        {{"source": "n1", "target": "n2", "relation": "包含"}},
        {{"source": "n2", "target": "n3", "relation": "应用于"}}
    ]
}}"""
    
    try:
        response = ai_generator.generate_reply(prompt, max_tokens=2000)
        # 提取JSON部分
        json_str = extract_json_from_response(response)
        graph_data = json.loads(json_str)
        
        # 确保基本结构存在
        if 'nodes' not in graph_data:
            graph_data = {'nodes': [], 'edges': []}
        
        return graph_data
    except Exception as e:
        print(f"生成知识图谱失败: {e}")
        # 返回默认结构
        return generate_default_knowledge_graph(content_list)


def extract_json_from_response(response):
    """从AI响应中提取JSON字符串"""
    response = response.strip()
    
    # 尝试直接解析
    try:
        json.loads(response)
        return response
    except:
        pass
    
    # 查找JSON代码块
    if '```json' in response:
        start = response.find('```json') + 7
        end = response.find('```', start)
        if end > start:
            return response[start:end].strip()
    elif '```' in response:
        start = response.find('```') + 3
        end = response.find('```', start)
        if end > start:
            return response[start:end].strip()
    
    # 查找花括号包裹的内容
    start = response.find('{')
    end = response.rfind('}')
    if start >= 0 and end > start:
        return response[start:end+1]
    
    # 查找方括号包裹的内容
    start = response.find('[')
    end = response.rfind(']')
    if start >= 0 and end > start:
        return response[start:end+1]
    
    return response


def generate_default_mindmap(content_list):
    """生成默认的思维导图结构"""
    root_text = "课件内容"
    if content_list and content_list[0]:
        root_text = content_list[0][:20] + "..."
    
    children = []
    for i, content in enumerate(content_list[:6]):
        if content.strip():
            children.append({
                "id": str(i+1),
                "text": content[:30] + "..." if len(content) > 30 else content,
                "children": []
            })
    
    return {
        "root": {
            "id": "root",
            "text": root_text,
            "children": children if children else [{"id": "1", "text": "主要内容", "children": []}]
        }
    }


def generate_default_knowledge_graph(content_list):
    """生成默认的知识图谱结构"""
    nodes = []
    edges = []
    
    for i, content in enumerate(content_list[:8]):
        if content.strip():
            node_id = f"n{i+1}"
            nodes.append({
                "id": node_id,
                "name": content[:20] + "..." if len(content) > 20 else content,
                "type": "concept"
            })
            # 添加顺序连接边
            if i > 0:
                edges.append({
                    "source": f"n{i}",
                    "target": node_id,
                    "relation": "接下来"
                })
    
    if not nodes:
        nodes = [{"id": "n1", "name": "课件内容", "type": "concept"}]
    
    return {"nodes": nodes, "edges": edges}


# ==================== 2.1.4 测验生成接口 ====================
@lesson_bp.route('/generate-quiz', methods=['POST'])
@jwt_required()
def generate_quiz():
    """生成课件测验题目"""
    try:
        data = request.get_json()
        course_id = data.get('courseId')
        question_count = data.get('questionCount', 10)
        question_types = data.get('types', ['multiple_choice', 'fill_blank', 'true_false', 'short_answer'])
        
        print(f"[生成测验] 收到请求: courseId={course_id}, questionCount={question_count}")
        
        if not course_id:
            return api_response(code=400, msg='courseId 不能为空')
        
        # 查询课件信息
        lesson = Lesson.query.filter_by(id=int(course_id) if str(course_id).isdigit() else None).first() or \
                 Lesson.query.filter_by(parse_id=course_id).first()
        
        if not lesson:
            print(f"[生成测验] 课件不存在: {course_id}")
            return api_response(code=404, msg='课件不存在')
        
        print(f"[生成测验] 找到课件: {lesson.file_name}")
        
        script_text = _quiz_context_text_from_lesson(lesson)
        print(f"[生成测验] 上下文长度: {len(script_text)}")
        
        if not script_text.strip():
            # 如果没有内容，返回模板题目
            print(f"[生成测验] 内容为空，返回模板题目")
            questions = generate_template_questions(question_count, question_types)
            return api_response(data={'questions': questions}, msg='题目生成成功')
        
        # 调用 AI 生成题目
        print(f"[生成测验] 调用 AI 生成题目...")
        ai_gen = get_ai_generator()
        prompt = f"""请根据以下课件内容生成{question_count}道测验题目，包含以下题型：
- 选择题 (multiple_choice)
- 填空题 (fill_blank)
- 判断题 (true_false)
- 问答题 (short_answer)

课件内容：
{script_text[:2000]}

请返回 JSON 格式的题目列表，每道题包含：
- type: 题型 (multiple_choice/fill_blank/true_false/short_answer)
- content: 题目内容
- options: 选项列表（仅选择题需要）
- answer: 标准答案
- explanation: 答案解析

返回格式：
{{"questions": [
  {{"type": "multiple_choice", "content": "...", "options": ["A", "B", "C", "D"], "answer": "A", "explanation": "..."}},
  ...
]}}
"""
        
        response = ai_gen.generate_reply(prompt, max_tokens=2000)
        print(f"[生成测验] AI 响应长度: {len(response)}")
        
        # 解析 AI 返回的 JSON
        try:
            json_str = extract_json_from_response(response)
            quiz_data = json.loads(json_str)
            questions = quiz_data.get('questions', [])
            print(f"[生成测验] 成功解析 {len(questions)} 道题目")
        except Exception as parse_err:
            print(f"[生成测验] JSON 解析失败: {parse_err}")
            questions = []
        
        if not questions:
            print(f"[生成测验] AI 生成失败，返回模板题目")
            questions = generate_template_questions(question_count, question_types)
        
        return api_response(data={'questions': questions}, msg='题目生成成功')
    
    except Exception as e:
        print(f"[生成测验] 异常: {e}")
        import traceback
        traceback.print_exc()
        return api_response(code=500, msg=f'生成题目失败: {str(e)}')


def generate_template_questions(count, types):
    """生成模板题目（当 AI 生成失败时使用）"""
    questions = []
    type_list = types or ['multiple_choice', 'fill_blank', 'true_false', 'short_answer']
    
    for i in range(count):
        q_type = type_list[i % len(type_list)]
        
        if q_type == 'multiple_choice':
            questions.append({
                'type': 'multiple_choice',
                'content': f'这是第{i+1}道选择题，请选择正确答案',
                'options': ['选项A', '选项B', '选项C', '选项D'],
                'answer': '选项A',
                'explanation': '这是答案解析'
            })
        elif q_type == 'fill_blank':
            questions.append({
                'type': 'fill_blank',
                'content': f'这是第{i+1}道填空题，请填写答案：_______',
                'options': [],
                'answer': '答案',
                'explanation': '这是答案解析'
            })
        elif q_type == 'true_false':
            questions.append({
                'type': 'true_false',
                'content': f'这是第{i+1}道判断题，判断以下说法是否正确',
                'options': ['正确', '错误'],
                'answer': '正确',
                'explanation': '这是答案解析'
            })
        else:  # short_answer
            questions.append({
                'type': 'short_answer',
                'content': f'这是第{i+1}道问答题，请简述你的理解',
                'options': [],
                'answer': '参考答案',
                'explanation': '这是答案解析'
            })
    
    return questions