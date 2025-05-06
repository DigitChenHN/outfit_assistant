
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
import json
from app import db
from app.models import Clothing, CATEGORIES, SEASONS, OCCASIONS, DESCRIPTION_EXAMPLES

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
                'occasions': json.dumps(request.form.getlist('occasions'))
            }
            
            # 创建新衣物
            clothing = Clothing(**data)
            db.session.add(clothing)
            db.session.commit()
            
            flash('衣物添加成功！', 'success')
            return redirect(url_for('wardrobe.index'))
            
        except Exception as e:
            db.session.rollback()
            flash('添加失败，请重试。', 'error')
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
            
            db.session.commit()
            flash('衣物更新成功！', 'success')
            return redirect(url_for('wardrobe.index'))
            
        except Exception as e:
            db.session.rollback()
            flash('更新失败，请重试。', 'error')
    
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

def init_app(app):
    app.register_blueprint(wardrobe_bp)