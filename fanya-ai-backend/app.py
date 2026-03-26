from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.exceptions import HTTPException
from config import Config
from extensions import db, jwt
from routes import register_routes
import os
import traceback
from sqlalchemy import text
from utils.file_utils import start_converter_warmup
from utils import tts_utils

app = Flask(__name__)
app.config.from_object(Config)

# 初始化扩展
CORS(app)
db.init_app(app)
jwt.init_app(app)

# 注册路由
register_routes(app)

# ==================== 错误处理器 ====================
# 404/405 等 HTTP 异常必须先于 Exception 注册，否则会被下面「兜底」成 500，
# 前端只看到「服务器错误: 404 Not Found...」，无法区分是路由不存在还是真 500。
@app.errorhandler(HTTPException)
def handle_http_exception(e):
    desc = (e.description or str(e) or "").strip()
    return jsonify({
        "code": e.code,
        "msg": desc or f"HTTP {e.code}",
        "data": {"path": request.path, "method": request.method}
    }), e.code

# 保留了第一份代码中详细的带分隔符的日志输出，方便在控制台调试排错
@app.errorhandler(500)
def internal_error(error):
    print("=" * 60)
    print("500 错误详情:")
    print("=" * 60)
    traceback.print_exc()
    print("=" * 60)
    return jsonify({
        "code": 500,
        "msg": f"服务器内部错误: {str(error)}",
        "data": {}
    }), 500

@app.errorhandler(Exception)
def handle_exception(e):
    if isinstance(e, HTTPException):
        return handle_http_exception(e)
    print("=" * 60)
    print("未捕获的异常:")
    print("=" * 60)
    traceback.print_exc()
    print("=" * 60)
    return jsonify({
        "code": 500,
        "msg": f"服务器错误: {str(e)}",
        "data": {}
    }), 500

# ==================== 数据库初始化与迁移 ====================
with app.app_context():
    # 创建所有表（如果不存在）
    db.create_all()
    print("数据库表创建完成")
    
    # 采用第二份代码的列表遍历方式，更优雅且包含了所有的字段更新和字符集更新
    migrations = [
        ("ALTER TABLE biz_lesson ADD COLUMN rag_chunks TEXT", "添加 rag_chunks"),
        ("ALTER TABLE biz_lesson MODIFY COLUMN rag_chunks LONGTEXT", "升级 rag_chunks 为 LONGTEXT"),
        ("ALTER TABLE biz_lesson MODIFY COLUMN structure_data LONGTEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci", "升级 structure_data 为 LONGTEXT（避免 paddlePages 过大导致提交失败）"),
        ("ALTER TABLE biz_lesson ADD COLUMN mindmap_data TEXT", "添加 mindmap_data"),
        ("ALTER TABLE biz_lesson ADD COLUMN knowledge_graph_data TEXT", "添加 knowledge_graph_data"),
        ("ALTER TABLE biz_lesson ADD COLUMN checkpoints TEXT", "添加 checkpoints"),
        ("ALTER TABLE biz_lesson MODIFY COLUMN script_content LONGTEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci", "升级 script_content 为 utf8mb4"),
        ("ALTER TABLE biz_lesson MODIFY COLUMN mindmap_data TEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci", "升级 mindmap_data 为 utf8mb4"),
        ("ALTER TABLE biz_lesson MODIFY COLUMN knowledge_graph_data TEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci", "升级 knowledge_graph_data 为 utf8mb4"),
        # 测验表字符集更新
        ("ALTER TABLE biz_quiz MODIFY COLUMN question_text TEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci", "升级 biz_quiz.question_text 为 utf8mb4"),
        ("ALTER TABLE biz_quiz MODIFY COLUMN options TEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci", "升级 biz_quiz.options 为 utf8mb4"),
        ("ALTER TABLE biz_quiz MODIFY COLUMN correct_answer TEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci", "升级 biz_quiz.correct_answer 为 utf8mb4"),
        ("ALTER TABLE biz_quiz MODIFY COLUMN explanation TEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci", "升级 biz_quiz.explanation 为 utf8mb4"),
        # 知识库表
        ("CREATE TABLE IF NOT EXISTS biz_category (id INT AUTO_INCREMENT PRIMARY KEY, user_id VARCHAR(50) NOT NULL, name VARCHAR(255) NOT NULL, description VARCHAR(500) DEFAULT '', create_time DATETIME, update_time DATETIME) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci", "创建分类表"),
        ("ALTER TABLE biz_category MODIFY id INT AUTO_INCREMENT", "修改 biz_category id 为 AUTO_INCREMENT"),
        ("ALTER TABLE biz_category ADD COLUMN update_time DATETIME NULL", "biz_category 添加 update_time"),
        ("UPDATE biz_category SET update_time = create_time WHERE update_time IS NULL AND create_time IS NOT NULL", "biz_category 回填 update_time"),
        ("CREATE TABLE IF NOT EXISTS biz_knowledge_doc (id INT AUTO_INCREMENT PRIMARY KEY, category_id INT NOT NULL, user_id VARCHAR(50) NOT NULL, name VARCHAR(255) NOT NULL, description VARCHAR(500) DEFAULT '', file_url VARCHAR(500) NOT NULL, file_type VARCHAR(20) DEFAULT '', rag_chunks LONGTEXT, create_time DATETIME) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci", "创建知识库文档表"),
        ("ALTER TABLE biz_knowledge_doc ADD COLUMN IF NOT EXISTS file_type VARCHAR(20) DEFAULT ''", "知识库表补充file_type列"),
        ("ALTER TABLE biz_knowledge_doc ADD COLUMN IF NOT EXISTS description VARCHAR(500) DEFAULT ''", "知识库表补充description列"),
        ("ALTER TABLE biz_knowledge_doc MODIFY COLUMN id INT NOT NULL AUTO_INCREMENT", "知识库表修复id自增"),
        ("ALTER TABLE biz_knowledge_doc DROP FOREIGN KEY biz_knowledge_doc_ibfk_1", "删除知识库外键约束"),
        ("ALTER TABLE biz_knowledge_doc CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci", "知识库表转换utf8mb4字符集"),
        ("ALTER TABLE biz_knowledge_doc ADD COLUMN index_status VARCHAR(20) NULL", "知识库解析状态 index_status"),
        # 智能插旗考点答题记录表
        ("""CREATE TABLE IF NOT EXISTS biz_checkpoint_answer (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id VARCHAR(50) NOT NULL,
            lesson_id VARCHAR(100) NOT NULL,
            checkpoint_id VARCHAR(100) NOT NULL,
            page_num INT NOT NULL,
            question_text TEXT,
            user_answer TEXT,
            correct_answer TEXT,
            is_correct BOOLEAN DEFAULT FALSE,
            submit_time DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY _user_lesson_checkpoint_uc (user_id, lesson_id, checkpoint_id)
        ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci""", "创建智能插旗考点答题记录表"),
    ]
    
    for sql, desc in migrations:
        try:
            db.session.execute(text(sql))
            db.session.commit()
            print(f"数据库迁移成功: {desc}")
        except Exception as e:
            db.session.rollback()
            # 不打印长堆栈，只打印跳过提示，因为字段已存在时报错是正常现象
            print(f"数据库迁移跳过 (可能已存在或暂不可用): {desc}")
    
    # 智能插旗考点答题记录表 - 检查并添加缺失的列（兼容MySQL 5.7）
    try:
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        if 'biz_checkpoint_answer' in inspector.get_table_names():
            columns = [col['name'] for col in inspector.get_columns('biz_checkpoint_answer')]
            
            # 需要添加的列
            columns_to_add = [
                ('question_text', 'TEXT'),
                ('user_answer', 'TEXT'),
                ('correct_answer', 'TEXT'),
                ('is_correct', 'BOOLEAN DEFAULT FALSE')
            ]
            
            for col_name, col_type in columns_to_add:
                if col_name not in columns:
                    try:
                        db.session.execute(text(f"ALTER TABLE biz_checkpoint_answer ADD COLUMN {col_name} {col_type}"))
                        db.session.commit()
                        print(f"数据库迁移成功: 添加列 {col_name}")
                    except Exception as e:
                        db.session.rollback()
                        print(f"数据库迁移跳过: 添加列 {col_name} - {e}")
    except Exception as e:
        print(f"检查biz_checkpoint_answer表结构失败: {e}")
            
    print("数据库表结构初始化完成")

# ==================== 服务启动配置 ====================
if __name__ == '__main__':
    # 1. 确保必要目录存在 (修复了第一份代码中目录创建在 app.run 之后的 dead code 问题)
    folders = [
        'uploads', 
        'uploads/tts', 
        'static/images', 
        'static/digital_humans'
    ]
    for folder in folders:
        if not os.path.exists(folder):
            os.makedirs(folder)

    # 2. 后台预热 Docling，避免首次 OCR 阻塞
    start_converter_warmup()

    # 3. 预生成系统占位提示音，确保声音统一
    loading_file = 'uploads/tts/system_loading.mp3'
    if not os.path.exists(loading_file):
        print("正在生成系统统一提示音...")
        try:
            # 使用与讲稿相同的工具生成声音
            tts_utils.text_to_speech("同学你好，AI 正在为你准备本页的深度解析，请稍等片刻。", "system_loading.mp3")
            print("系统统一提示音生成成功")
        except Exception as e:
            print(f"提示音生成失败: {e}")

    # 4. 启动服务
    print("服务启动中，监听端口 8989...")
    # 禁用自动重载，避免多线程导致的资源加载冲突
    app.run(debug=True, host='0.0.0.0', port=8989, use_reloader=False)