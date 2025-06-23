
from flask import Blueprint, render_template
from flask_login import current_user
# routes/__init__.py
from .auth import auth_bp
from .wardrobe import wardrobe_bp
from .weather import weather_bp
from .chat import chat_bp
from .api_keys import bp as api_keys_bp

# 创建主蓝图
main_bp = Blueprint('main', __name__)

__all__ = ['auth_bp', 'wardrobe_bp', 'weather_bp', 'chat_bp', 'api_keys_bp', 'main_bp']

@main_bp.route('/')
def index():
    return render_template('index.html')    