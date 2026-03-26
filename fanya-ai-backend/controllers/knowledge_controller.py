from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from models.knowledge import KnowledgeDoc
from extensions import db
from utils.api_utils import api_response
from utils.rag_utils import build_rag_chunks, dumps_rag_chunks, loads_rag_chunks, get_rag_context
from utils.normalize import pages_from_paddle_jsonl_lines, content_list_from_paddle_doc
from utils.paddle_client import run_parse_pipeline
import os
import uuid
import json

knowledge_bp = Blueprint('knowledge', __name__)


# ==================== 1. 上传知识库文档 ====================
@knowledge_bp.route('/upload', methods=['POST'])
@jwt_required()
def upload_knowledge():
    """上传知识库资料并自动构建RAG索引"""
    try:
        current_user_id = get_jwt_identity()
        category_id = request.form.get('categoryId', '')
        name = request.form.get('name', '')
        description = request.form.get('description', '')

        if not category_id:
            return api_response(code=400, msg='categoryId不能为空')
        if not name:
            return api_response(code=400, msg='资料名称不能为空')
        if 'file' not in request.files:
            return api_response(code=400, msg='请上传文件')

        file = request.files['file']
        if file.filename == '':
            return api_response(code=400, msg='文件名不能为空')

        file_ext = file.filename.rsplit('.', 1)[-1].lower()
        if file_ext not in ['pdf', 'doc', 'docx', 'txt']:
            return api_response(code=400, msg='仅支持PDF、DOC、DOCX、TXT格式')

        # 保存文件
        filename = f'knowledge_{uuid.uuid4().hex}.{file_ext}'
        save_dir = os.path.join('uploads', 'knowledge')
        os.makedirs(save_dir, exist_ok=True)
        file_path = os.path.join(save_dir, filename)
        file.save(file_path)

        # 提取文本并构建RAG
        content_list = []
        try:
            if file_ext == 'pdf':
                content_list = []
                if os.environ.get("PADDLE_OCR_TOKEN", "").strip():
                    try:
                        _, lines = run_parse_pipeline(file_path)
                        doc = pages_from_paddle_jsonl_lines(lines)
                        content_list = content_list_from_paddle_doc(doc)
                        if not any((s or "").strip() for s in content_list):
                            content_list = []
                    except Exception as e:
                        print(f'[知识库] Paddle 解析失败: {e}')
                else:
                    print('[知识库] 未配置 PADDLE_OCR_TOKEN，跳过 PDF 索引')
            elif file_ext == 'txt':
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    text = f.read()
                content_list = [text[i:i+500] for i in range(0, len(text), 500)]
            else:
                # docx 简单处理
                try:
                    import docx as python_docx
                    doc = python_docx.Document(file_path)
                    full_text = '\n'.join([p.text for p in doc.paragraphs if p.text.strip()])
                    content_list = [full_text[i:i+500] for i in range(0, len(full_text), 500)]
                except Exception:
                    content_list = []
        except Exception as e:
            print(f'[知识库] 文本提取失败: {e}')

        rag_str = '[]'
        if content_list:
            chunks = build_rag_chunks(content_list, chunk_size=500)
            rag_str = dumps_rag_chunks(chunks)
            print(f'[知识库] 构建RAG完成，共 {len(chunks)} 个片段')

        doc_obj = KnowledgeDoc(
            category_id=category_id,
            user_id=str(current_user_id),
            name=name,
            description=description,
            file_url=os.path.join('knowledge', filename),
            file_type=file_ext,
            rag_chunks=rag_str
        )
        db.session.add(doc_obj)
        db.session.commit()

        return api_response(data=doc_obj.to_dict(), msg='知识库资料上传成功')

    except Exception as e:
        db.session.rollback()
        print(f'[知识库] 上传失败: {e}')
        import traceback; traceback.print_exc()
        return api_response(code=500, msg=f'上传失败: {str(e)}')


# ==================== 2. 获取分类下的知识库列表 ====================
@knowledge_bp.route('/list/<category_id>', methods=['GET'])
@jwt_required()
def list_knowledge(category_id):
    try:
        current_user_id = get_jwt_identity()
        docs = KnowledgeDoc.query.filter_by(
            category_id=category_id,
            user_id=str(current_user_id)
        ).order_by(KnowledgeDoc.create_time.desc()).all()
        return api_response(data=[d.to_dict() for d in docs])
    except Exception as e:
        return api_response(code=500, msg=f'查询失败: {str(e)}')


# ==================== 3. 删除知识库文档 ====================
@knowledge_bp.route('/delete/<int:doc_id>', methods=['DELETE'])
@jwt_required()
def delete_knowledge(doc_id):
    try:
        current_user_id = get_jwt_identity()
        print(f'[知识库删除] 请求: doc_id={doc_id}, user_id={current_user_id}')
        
        doc = KnowledgeDoc.query.get(doc_id)
        
        if not doc:
            print(f'[知识库删除] 文档不存在: {doc_id}')
            return api_response(code=404, msg='文档不存在')
        
        print(f'[知识库删除] 找到文档: id={doc.id}, user_id={doc.user_id}, name={doc.name}')
        
        # 权限检查：确保是文档所有者
        if str(doc.user_id) != str(current_user_id):
            print(f'[知识库删除] 权限检查失败: doc.user_id={doc.user_id}, current_user_id={current_user_id}')
            return api_response(code=403, msg='无权限删除他人文档')
        
        # 删除文件
        try:
            file_path = os.path.join('uploads', doc.file_url)
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f'[知识库删除] 已删除文件: {file_path}')
            else:
                print(f'[知识库删除] 文件不存在: {file_path}')
        except Exception as e:
            print(f'[知识库删除] 删除文件失败: {e}')
        
        # 从数据库删除记录
        try:
            db.session.delete(doc)
            db.session.commit()
            print(f'[知识库删除] 已删除数据库记录: {doc_id}')
            return api_response(msg='知识库资料已成功删除')
        except Exception as e:
            db.session.rollback()
            print(f'[知识库删除] 删除数据库记录失败: {e}')
            import traceback
            traceback.print_exc()
            return api_response(code=500, msg=f'删除失败: {str(e)}')
    
    except Exception as e:
        db.session.rollback()
        print(f'[知识库删除] 异常: {e}')
        import traceback
        traceback.print_exc()
        return api_response(code=500, msg=f'删除失败: {str(e)}')


# ==================== 4. 获取多个知识库文档的合并RAG内容 ====================
@knowledge_bp.route('/rag-context', methods=['POST'])
@jwt_required()
def get_knowledge_rag_context():
    """根据勾选的知识库文档ID和查询词，返回最相关的RAG片段"""
    try:
        data = request.get_json()
        doc_ids = data.get('docIds', [])
        query = data.get('query', '')
        top_k = data.get('topK', 5)

        if not doc_ids:
            return api_response(data={'context': ''}, msg='未选择知识库文档')

        # 合并所有选中文档的RAG chunks
        all_chunks = []
        for doc_id in doc_ids:
            doc = KnowledgeDoc.query.get(doc_id)
            if doc and doc.rag_chunks:
                chunks = loads_rag_chunks(doc.rag_chunks)
                all_chunks.extend(chunks)

        if not all_chunks:
            return api_response(data={'context': ''}, msg='知识库内容为空')

        context = get_rag_context(query or '知识点 考点', all_chunks, top_k=top_k)
        return api_response(data={'context': context, 'chunkCount': len(all_chunks)})

    except Exception as e:
        return api_response(code=500, msg=f'获取失败: {str(e)}')
