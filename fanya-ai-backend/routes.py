from controllers.user_controller import user_bp
from controllers.lesson_controller import lesson_bp
from controllers.qa_controller import qa_bp
from controllers.progress_controller import progress_bp
from controllers.platform_controller import platform_bp
from controllers.avatar_controller import avatar_bp
from controllers.rhythm_controller import rhythm_bp
from controllers.quiz_controller import quiz_bp
from controllers.knowledge_controller import knowledge_bp
from controllers.category_controller import category_bp

def register_routes(app):
    """
    注册所有路由
    按照API文档规范配置路由前缀
    """
    
    # 用户模块 - 保持原有路径
    app.register_blueprint(user_bp, url_prefix='/api/user')
    
    # 智课生成模块 - 符合文档规范 /api/v1/lesson
    app.register_blueprint(lesson_bp, url_prefix='/api/v1/lesson')
    
    # 问答交互模块 - 符合文档规范 /api/v1/qa
    app.register_blueprint(qa_bp, url_prefix='/api/v1/qa')
    
    # 学习进度模块 - 符合文档规范 /api/v1/progress
    app.register_blueprint(progress_bp, url_prefix='/api/v1/progress')
    
    # 学习节奏模块 - 兼容旧接口
    app.register_blueprint(rhythm_bp, url_prefix='/api/rhythm')
    
    # 平台对接模块 - 符合文档规范 /api/v1/platform
    app.register_blueprint(platform_bp, url_prefix='/api/v1/platform')
    
    # 数字人模块 - 保持原有路径
    app.register_blueprint(avatar_bp, url_prefix='/api/avatar')
    
    # 测验模块 - 符合文档规范 /api/v1/quiz
    app.register_blueprint(quiz_bp, url_prefix='/api/v1/quiz')

    # 知识库模块
    app.register_blueprint(knowledge_bp, url_prefix='/api/v1/knowledge')
    
    # 分类模块
    app.register_blueprint(category_bp, url_prefix='/api/v1/category')
