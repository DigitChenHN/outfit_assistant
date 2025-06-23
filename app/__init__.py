
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from config import Config

# 初始化扩展
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'  # 设置登录视图的端点
login_manager.login_message = '请先登录以访问此页面'  # 自定义消息

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    @app.after_request
    def add_header(response):
        # 禁用缓存确保每次加载最新脚本
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response

    # 初始化扩展
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    # 初始化蓝图
    from .routes import auth_bp, main_bp, wardrobe_bp, weather_bp, chat_bp, api_keys_bp
    # 注册主路由模块
    app.register_blueprint(main_bp)
    
    # 注册其他路由模块
    app.register_blueprint(auth_bp)
    app.register_blueprint(wardrobe_bp)
    app.register_blueprint(weather_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(api_keys_bp)

    with app.app_context():
        db.create_all()

    return app