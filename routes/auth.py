import os
from flask import Blueprint, render_template, redirect, url_for, flash, request
from models.database import db, bcrypt, User
from flask_login import login_user, logout_user, current_user, login_required
from sqlalchemy.exc import SQLAlchemyError

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password')
        role = request.form.get('role', 'Student')
        teacher_code = request.form.get('teacher_code', '').strip()

        # ĐOẠN CODE KIỂM TRA ÉP BUỘC ĐUÔI @GMAIL.COM CỦA MÁ NÈ:
        if not email.endswith('@gmail.com'):
            flash('Hệ thống lớp học chỉ chấp nhận tài khoản có đuôi @gmail.com hợp lệ!', 'danger')
            return redirect(url_for('auth.register'))

        # Khắc phục lỗi lọt bộ lọc kiểm tra Email trùng lặp gây sập ứng dụng
        if User.query.filter_by(username=username).first():
            flash('Tên tài khoản này đã tồn tại!', 'danger')
            return redirect(url_for('auth.register'))
        if User.query.filter_by(email=email).first():
            flash('Địa chỉ Email này đã được đăng ký sử dụng!', 'danger')
            return redirect(url_for('auth.register'))

        # Kiểm tra mã xác minh giáo viên an toàn qua file môi trường .env
        if role == 'Teacher':
            if teacher_code != os.environ.get('TEACHER_VERIFICATION_CODE'):
                flash('Mã xác minh giáo viên không đúng! Hệ thống tự động cấp vai trò Học sinh.', 'warning')
                role = 'Student'
        elif role == 'Admin':
            role = 'Student'  # Khóa cứng không cho phép đăng ký trực tiếp quyền admin

        try:
            hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
            # Giáo viên / Học sinh mới cần được Admin phê duyệt ở trang Thành viên lớp để chống acc clone
            is_app = True if role == 'admin' else False
            user = User(username=username, email=email, password=hashed_pw, role=role, is_approved=is_app)
            db.session.add(user)
            db.session.commit()
            flash('Tài khoản đã tạo thành công! Vui lòng chờ Giáo viên hoặc Quản trị viên duyệt hồ sơ.', 'success')
            return redirect(url_for('auth.login'))
        except SQLAlchemyError:
            db.session.rollback()  # Khắc phục lỗi thiếu Transaction & Rollback khiến sập session
            flash('Có lỗi xảy ra trong quá trình ghi dữ liệu. Vui lòng thử lại.', 'danger')

    return render_template('register.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()

        if user and bcrypt.check_password_hash(user.password, password):
            # Tính năng chống Acc Clone: Tài khoản chưa duyệt không cho phép đăng nhập
            if not user.is_approved:
                flash('Tài khoản của bạn đang trong hàng chờ kiểm tra từ Giáo viên để tránh nick ảo.', 'warning')
                return redirect(url_for('auth.login'))
            login_user(user)
            return redirect(url_for('main.dashboard'))
        else:
            flash('Đăng nhập thất bại. Vui lòng kiểm tra lại thông tin.', 'danger')
    return render_template('login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))
