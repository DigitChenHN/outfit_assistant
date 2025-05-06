from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.urls import url_parse
from app import db
from app.models.user import User

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        # 表单验证
        if not all([username, email, password, confirm_password]):
            flash('请填写所有必填字段', 'error')
            return render_template('register.html')
        
        if password != confirm_password:
            flash('两次输入的密码不匹配', 'error')
            return render_template('register.html')

        # 检查用户名和邮箱是否已存在
        if User.query.filter_by(username=username).first():
            flash('用户名已存在', 'error')
            return render_template('register.html')
        
        if User.query.filter_by(email=email).first():
            flash('邮箱已被注册', 'error')
            return render_template('register.html')

        # 创建新用户
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        flash('注册成功！请登录', 'success')
        return redirect(url_for('auth.login'))

    return render_template('register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = request.form.get('remember', False)

        if not all([username, password]):
            flash('请填写所有必填字段', 'error')
            return render_template('login.html')

        user = User.query.filter_by(username=username).first()
        
        if user is None or not user.check_password(password):
            flash('用户名或密码错误', 'error')
            return render_template('login.html')

        # 登录用户
        login_user(user, remember=remember)
        
        # 处理next参数，确保安全重定向
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('main.index')
        
        flash('登录成功！', 'success')
        return redirect(next_page)

    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('您已成功登出', 'success')
    return redirect(url_for('auth.login'))

