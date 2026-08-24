import os
import uuid
from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app, jsonify
from models.database import db, User, Post, Comment
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename
from sqlalchemy.exc import SQLAlchemyError

main_bp = Blueprint('main', __name__)


# Hàm kiểm tra đuôi file upload an toàn (Whitelist Filter) ngăn chặn RCE độc hại
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']


@main_bp.route('/')
@main_bp.route('/dashboard')
@login_required
def dashboard():
    total_assignments = 10
    completed = len(current_user.submissions)
    progress_pct = int((completed / total_assignments) * 100) if total_assignments > 0 else 0
    return render_template('dashboard.html', progress_pct=progress_pct, completed=completed, total=total_assignments)


@main_bp.route('/feed', methods=['GET', 'POST'])
@login_required
def feed():
    if request.method == 'POST':
        content = request.form.get('content', '').strip()
        # Chặn tấn công DoS / Tràn RAM hệ thống bằng cách giới hạn ký tự bài đăng
        if len(content) > 5000:
            flash('Nội dung bài viết quá dài (Tối đa 5000 ký tự).', 'danger')
            return redirect(url_for('main.feed'))

        file = request.files.get('image')
        filename = None

        if file and file.filename != '':
            if allowed_file(file.filename):
                # Khắc phục lỗ hổng ghi đè file: Đổi tên file ngẫu nhiên bằng chuỗi UUID4 an toàn
                ext = file.filename.rsplit('.', 1)[1].lower()
                filename = f"{uuid.uuid4().hex}.{ext}"
                file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
            else:
                flash('Định dạng tệp tin ảnh tải lên không hợp lệ!', 'danger')
                return redirect(url_for('main.feed'))

        try:
            post = Post(content=content, image_file=filename, author=current_user)
            db.session.add(post)
            db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            flash('Có lỗi xảy ra khi đăng bài viết.', 'danger')
        return redirect(url_for('main.feed'))

    # Khắc phục hiệu năng (Pagination): Phân trang bài đăng tránh treo RAM hệ thống
    page = request.args.get('page', 1, type=int)
    posts_pagination = Post.query.order_by(Post.date_posted.desc()).paginate(page=page, per_page=5, error_out=False)
    return render_template('feed.html', posts_pagination=posts_pagination)


# Chuyển đổi nút Like/Thả tim sang cơ chế AJAX/Fetch API trả về JSON chuẩn công nghệ
@main_bp.route('/post/<int:post_id>/like')
@login_required
def like_post(post_id):
    post = Post.query.get_or_404(post_id)  # Sửa lỗi gõ nhầm get_or_400
    if current_user in post.liked_by:
        post.liked_by.remove(current_user)
        status = 'unliked'
    else:
        post.liked_by.append(current_user)
        status = 'liked'
    db.session.commit()
    return jsonify({'status': status, 'like_count': len(post.liked_by)})


@main_bp.route('/post/<int:post_id>/heart')
@login_required
def heart_post(post_id):
    post = Post.query.get_or_404(post_id)  # Sửa lỗi gõ nhầm get_or_400
    if current_user in post.hearted_by:
        post.hearted_by.remove(current_user)
        status = 'unhearted'
    else:
        post.hearted_by.append(current_user)
        status = 'hearted'
    db.session.commit()
    return jsonify({'status': status, 'heart_count': len(post.hearted_by)})


@main_bp.route('/post/<int:post_id>/comment', methods=['POST'])
@login_required
def add_comment(post_id):
    content = request.form.get('content', '').strip()
    if content and len(content) <= 1000:
        try:
            comment = Comment(content=content, post_id=post_id, author=current_user)
            db.session.add(comment)
            db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
    return redirect(url_for('main.feed'))


@main_bp.route('/members')
@login_required
def members():
    users = User.query.order_by(User.level.desc()).all()
    return render_template('members.html', users=users)


@main_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        if 'delete_acc' in request.form:
            # Tăng cường bảo mật: Kiểm tra mật khẩu xác nhận trước khi xóa vĩnh viễn tài khoản
            confirm_pw = request.form.get('confirm_password')
            if bcrypt.check_password_hash(current_user.password, confirm_pw):
                try:
                    db.session.delete(current_user)
                    db.session.commit()
                    flash('Tài khoản của bạn đã được xóa khỏi hệ thống.', 'info')
                    return redirect(url_for('auth.register'))
                except SQLAlchemyError:
                    db.session.rollback()
                    flash('Xóa tài khoản không thành công do ràng buộc hệ thống.', 'danger')
            else:
                flash('Mật khẩu xác nhận không chính xác! Hành động xóa tài khoản bị chặn.', 'danger')
                return redirect(url_for('main.profile'))

        new_username = request.form.get('username', '').strip()
        # Khắc phục lỗi của Giảng viên: Chặn lỗi trùng lặp Username khi người dùng sửa Profile
        if new_username != current_user.username:
            if User.query.filter_by(username=new_username).first():
                flash('Tên người dùng này đã có người khác chọn sử dụng!', 'danger')
                return redirect(url_for('main.profile'))

        try:
            current_user.username = new_username
            db.session.commit()
            flash('Cập nhật hồ sơ cá nhân thành công!', 'success')
        except SQLAlchemyError:
            db.session.rollback()
    return render_template('profile.html')


@main_bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        current_user.dark_mode = True if request.form.get('dark_mode') else False
        current_user.mute_notif = True if request.form.get('mute_notif') else False
        db.session.commit()
        flash('Đã lưu cấu hình thiết lập hệ thống.', 'success')
    return render_template('settings.html')
