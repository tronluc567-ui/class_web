from flask import Blueprint, render_template, redirect, url_for, request, flash
from models.database import db, CalendarEvent, User
from utils.decorators import role_required
from flask_login import login_required, current_user
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/calendar', methods=['GET', 'POST'])
@login_required
def calendar():
    if request.method == 'POST':
        # Bảo mật tầng Route chống bypass
        if current_user.role not in ['admin', 'teacher']:
            flash('Bạn không có quyền thêm lịch.', 'danger')
            return redirect(url_for('admin.calendar'))

        title = request.form.get('title', '').strip()
        event_date_str = request.form.get('event_date')
        type_ev = request.form.get('type')

        try:
            date_obj = datetime.strptime(event_date_str, '%Y-%m-%d').date()
            event = CalendarEvent(title=title, event_date=date_obj, type=type_ev)
            db.session.add(event)
            db.session.commit()
            flash('Đã cập nhật sự kiện lịch mới cho lớp học.', 'success')
        except (ValueError, SQLAlchemyError):
            db.session.rollback()
            flash('Lỗi định dạng dữ liệu ngày tháng.', 'danger')
        return redirect(url_for('admin.calendar'))

    events = CalendarEvent.query.order_by(CalendarEvent.event_date.asc()).all()
    return render_template('calendar.html', events=events)


@admin_bp.route('/approve_user/<int:user_id>')
@role_required('admin', 'teacher')  # Áp dụng Custom Decorator bảo mật tuyệt đối
def approve_user(user_id):
    user = User.query.get_or_404(user_id)
    try:
        user.is_approved = True
        db.session.commit()
        flash(f'Đã phê duyệt tài khoản {user.username} vào lớp học.', 'success')
    except SQLAlchemyError:
        db.session.rollback()
    return redirect(url_for('main.members'))


@admin_bp.route('/reject_user/<int:user_id>')
@role_required('admin', 'teacher')
def reject_user(user_id):
    user = User.query.get_or_404(user_id)
    try:
        db.session.delete(user)
        db.session.commit()
        flash(f'Đã xóa bỏ tài khoản ảo {user.username}.', 'info')
    except SQLAlchemyError:
        db.session.rollback()
    return redirect(url_for('main.members'))
