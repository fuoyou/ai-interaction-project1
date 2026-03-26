from extensions import db
from datetime import datetime
import pytz

CNT = pytz.timezone('Asia/Shanghai')


class KnowledgeDoc(db.Model):
    """知识库文档表"""
    __tablename__ = 'biz_knowledge_doc'

    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.String(100), nullable=False, index=True)  # 所属分类ID
    user_id = db.Column(db.String(50), nullable=False, index=True)        # 上传者
    name = db.Column(db.String(255), nullable=False)                       # 资料名称
    description = db.Column(db.String(500), default='')                   # 资料描述
    file_url = db.Column(db.String(500), nullable=False)                  # 文件路径
    file_type = db.Column(db.String(20), default='')                      # pdf/docx/txt
    rag_chunks = db.Column(db.Text)                                        # JSON: RAG切片
    # processing=后台解析中 | ready=已建索引 | empty=无可用文本 | failed=解析失败；NULL=历史数据
    index_status = db.Column(db.String(20), nullable=True)
    create_time = db.Column(db.DateTime, default=lambda: datetime.now(CNT))

    def to_dict(self, current_user_id=None):
        has_rag = bool(self.rag_chunks and self.rag_chunks != '[]')
        st = (self.index_status or '').strip() or None
        if st == 'processing':
            index_status = 'processing'
        elif st == 'failed':
            index_status = 'failed'
        elif st == 'ready':
            index_status = 'ready'
        elif st == 'empty':
            index_status = 'empty'
        else:
            # 历史行无 index_status：按是否已有切片推断
            index_status = 'ready' if has_rag else 'empty'

        d = {
            'id': self.id,
            'categoryId': self.category_id,
            'name': self.name,
            'description': self.description or '',
            'fileType': self.file_type,
            'hasRag': has_rag,
            'indexStatus': index_status,
            'createTime': self.create_time.strftime('%Y-%m-%d %H:%M:%S'),
        }
        if current_user_id is not None:
            d['canDelete'] = str(self.user_id) == str(current_user_id)
        return d
