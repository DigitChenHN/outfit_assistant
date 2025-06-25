from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, current_app
from flask_login import login_required, current_user
import json
import os
from werkzeug.utils import secure_filename
from app import db
from app.models import Clothing, CATEGORIES, SEASONS, OCCASIONS, DESCRIPTION_EXAMPLES
from app.llm.service import LLMService

wardrobe_bp = Blueprint('wardrobe', __name__, url_prefix='/wardrobe')

@wardrobe_bp.route('/')
@login_required
def index():
    """查看衣橱"""
    # 获取筛选参数
    category = request.args.get('category', '')
    
    # 查询用户的衣物
    query = Clothing.query.filter_by(user_id=current_user.id)
    if category:
        query = query.filter_by(category=category)
    
    clothes = query.order_by(Clothing.created_at.desc()).all()
    
    return render_template('wardrobe/index.html',
                         clothes=clothes,
                         categories=CATEGORIES,
                         current_category=category)

@wardrobe_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    """添加衣物"""
    if request.method == 'POST':
        try:
            # 获取表单数据
            data = {
                'user_id': current_user.id,
                'category': request.form['category'],
                'description': request.form['description'],
                'seasons': json.dumps(request.form.getlist('seasons')),
                'occasions': json.dumps(request.form.getlist('occasions')),
                'image_data': None,
                'image_mimetype': None
            }
            
            # 处理图片上传
            if 'clothing_image' in request.files:
                image_file = request.files['clothing_image']
                if image_file and image_file.filename:
                    # 检查文件类型
                    file_ext = os.path.splitext(image_file.filename)[1][1:].lower()
                    if file_ext in current_app.config['ALLOWED_IMAGE_EXTENSIONS']:
                        # 读取图片数据
                        image_data = image_file.read()
                        if image_data:
                            data['image_data'] = image_data
                            data['image_mimetype'] = image_file.mimetype
                    else:
                        flash('不支持的图片格式。请使用JPG、PNG、GIF或WEBP格式。', 'error')
            
            # 创建新衣物
            clothing = Clothing(**data)
            db.session.add(clothing)
            db.session.commit()
            
            flash('衣物添加成功！', 'success')
            return redirect(url_for('wardrobe.index'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'添加失败，请重试。错误: {str(e)}', 'error')
            return render_template('wardrobe/form.html',
                                categories=CATEGORIES,
                                seasons=SEASONS,
                                occasions=OCCASIONS,
                                description_examples=DESCRIPTION_EXAMPLES)
    
    return render_template('wardrobe/form.html',
                         categories=CATEGORIES,
                         seasons=SEASONS,
                         occasions=OCCASIONS,
                         description_examples=DESCRIPTION_EXAMPLES)

@wardrobe_bp.route('/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    """编辑衣物"""
    clothing = Clothing.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    
    if request.method == 'POST':
        try:
            # 更新数据
            clothing.category = request.form['category']
            clothing.description = request.form['description']
            clothing.seasons = json.dumps(request.form.getlist('seasons'))
            clothing.occasions = json.dumps(request.form.getlist('occasions'))
            
            # 处理图片上传
            if 'clothing_image' in request.files:
                image_file = request.files['clothing_image']
                if image_file and image_file.filename:
                    # 检查文件类型
                    file_ext = os.path.splitext(image_file.filename)[1][1:].lower()
                    if file_ext in current_app.config['ALLOWED_IMAGE_EXTENSIONS']:
                        # 读取图片数据
                        image_data = image_file.read()
                        if image_data:
                            clothing.image_data = image_data
                            clothing.image_mimetype = image_file.mimetype
                    else:
                        flash('不支持的图片格式。请使用JPG、PNG、GIF或WEBP格式。', 'error')
            
            db.session.commit()
            flash('衣物更新成功！', 'success')
            return redirect(url_for('wardrobe.index'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'更新失败，请重试。错误: {str(e)}', 'error')
    
    return render_template('wardrobe/form.html',
                         clothing=clothing,
                         categories=CATEGORIES,
                         seasons=SEASONS,
                         occasions=OCCASIONS,
                         description_examples=DESCRIPTION_EXAMPLES)

@wardrobe_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete(id):
    """删除衣物"""
    clothing = Clothing.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    
    try:
        db.session.delete(clothing)
        db.session.commit()
        return jsonify({'success': True, 'message': '衣物已删除'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': '删除失败，请重试'}), 500

@wardrobe_bp.route('/<int:id>/image')
@login_required
def get_image(id):
    """获取衣物图片"""
    clothing = Clothing.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    
    if not clothing.image_data:
        return "No image available", 404
        
    return clothing.image_data, 200, {
        'Content-Type': clothing.image_mimetype,
        'Cache-Control': 'max-age=31536000'  # 缓存一年
    }

@wardrobe_bp.route('/analyze-image', methods=['POST'])
@login_required
def analyze_image():
    """分析衣物图片"""
    if 'clothing_image' not in request.files:
        return jsonify({'success': False, 'message': '没有收到图片文件'}), 400
        
    image_file = request.files['clothing_image']
    if not image_file or not image_file.filename:
        return jsonify({'success': False, 'message': '请选择有效的图片文件'}), 400
        
    # 检查文件类型    
    file_ext = os.path.splitext(image_file.filename)[1][1:].lower()
    if file_ext not in current_app.config['ALLOWED_IMAGE_EXTENSIONS']:
        return jsonify({'success': False, 'message': '不支持的图片格式。请使用JPG、PNG、GIF或WEBP格式。'}), 400
        
    # 读取图片数据
    image_data = image_file.read()
    if not image_data:
        return jsonify({'success': False, 'message': '无法读取图片数据'}), 400
        
    try:
        # 使用LLM服务分析图片
        llm_service = LLMService()
        
        # 获取指定的配置ID（如果提供）
        config_id = request.form.get('config_id')
        llm_service.set_user_id(current_user.id, config_id)
        
        result = llm_service.analyze_clothing_image(image_data)
        
        if 'error' in result:
            return jsonify({'success': False, 'message': result['error']}), 400
            
        return jsonify({
            'success': True, 
            'data': result
        })
    except Exception as e:
        current_app.logger.error(f"分析图片时出错: {str(e)}")
        return jsonify({'success': False, 'message': f'分析图片时出错: {str(e)}'}), 500