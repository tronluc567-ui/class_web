from functools import wraps
from flask import flash, redirect, url_for
from flask_login import current_user

# Thay thế toàn bộ code kiểm tra if/else rải rác bằng Custom Decorator tập trung bảo mật cao
def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Vui lòng đăng nhập hệ thống.', 'danger')
                return redirect(url_for('auth.login'))
            if current_user.role not in roles:
                flash('Bạn không có quyền truy cập chức năng này!', 'danger')
                return redirect(url_for('main.dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator
