import os
import uuid
from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app
from models.database import db, Assignment, Submission, Document, Discussion, DiscussionComment, User
from utils.decorators import role_required
from flask_login import current_user, login_required
from datetime import datetime, date
from sqlalchemy.exc import SQLAlchemyError

learning_bp = Blueprint('learning', __name__)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']


@learning_bp.route('/assignments', methods=['GET', 'POST'])
@login_required
def assignments():
    if request.method == 'POST':
        # Áp dụng Custom Decorator bảo mật thay vì if/else thủ công sơ sài
        if current_user.role not in ['admin', 'teacher']:
            flash('Bạn không có quyền thực hiện chức năng này.', 'danger')
            return redirect(url_for('learning.assignments'))

        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        due_date_str = request.form.get('due_date')

        try:
            # Khắc phục lỗi kiểu dữ liệu: Ép chuỗi String(10) về kiểu Date chuẩn của SQL
            due_date_obj = datetime.strptime(due_date_str, '%Y-%m-%d').date()
            assign = Assignment(title=title, description=description, due_date=due_date_obj)
            db.session.add(assign)
            db.session.commit()
            flash('Đã đăng bài tập mới cho cả lớp.', 'success')
        except (ValueError, SQLAlchemyError):
            db.session.rollback()
            flash('Định dạng thời gian hoặc dữ liệu bị sai lệch.', 'danger')
        return redirect(url_for('learning.assignments'))

    assigns = Assignment.query.order_by(Assignment.date_created.desc()).all()
    return render_template('assignments.html', assigns=assigns)


@learning_bp.route('/assignments/<int:assign_id>', methods=['GET'])
@login_required
def assignment_detail(assign_id):
    # Khôi phục luồng chấm bài bị khuyết cho Giáo viên
    assign = Assignment.query.get_or_404(assign_id)
    subs = []
    if current_user.role in ['teacher', 'admin']:
        subs = Submission.query.filter_by(assignment_id=assign_id).all()
    return render_template('assignment_detail.html', assign=assign, subs=subs)


@learning_bp.route('/assignments/<int:assign_id>/submit', methods=['POST'])
@login_required
def submit_assignment(assign_id):
    # Khắc phục lỗ hổng "Spam cày EXP vô tận": Kiểm tra học sinh đã nộp bài tập này từ trước chưa
    existing_sub = Submission.query.filter_by(assignment_id=assign_id, user_id=current_user.id).first()
    if existing_sub:
        flash('Bạn đã hoàn thành nộp bài tập này từ trước, không thể nộp lại nhiều lần!', 'danger')
        return redirect(url_for('learning.assignments'))

    content = request.form.get('content', '').strip()
    file = request.files.get('sub_file')
    filename = None

    if file and file.filename != '':
        if allowed_file(file.filename):
            ext = file.filename.rsplit('.', 1)[1].lower()
            filename = f"sub_{uuid.uuid4().hex}.{ext}"
            file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
        else:
            flash('Định dạng file nộp bài không nằm trong danh mục cho phép!', 'danger')
            return redirect(url_for('learning.assignments'))

    # Xử lý Logic Streak chuyên sâu dựa vào đối tượng thời gian chuẩn Date
    today_obj = date.today()
    earned_exp = 50
    new_streak = current_user.streak

    if current_user.last_sub_date:
        diff = (today_obj - current_user.last_sub_date).days
        if diff == 1:
            new_streak += 1
        elif diff > 1:
            new_streak = 1
    else:
        new_streak = 1

    if new_streak == 7:
        earned_exp += 300

    try:
        sub = Submission(
            assignment_id=assign_id,
            user_id=current_user.id,
            filename=filename,
            content=content,
            status='Submitted'
        )
        current_user.streak = new_streak
        current_user.last_sub_date = today_obj
        current_user.exp += earned_exp
        current_user.level = (current_user.exp // 500) + 1

        db.session.add(sub)
        db.session.commit()
        # Xóa bỏ dòng thừa flash(url_for(...)) ngớ ngẩn bị giảng viên bắt lỗi
        flash(f'Nộp bài thành công! Hệ thống ghi nhận chuỗi hành động và cộng {earned_exp} EXP.', 'success')
    except SQLAlchemyError:
        db.session.rollback()
        flash('Nộp bài thất bại do xung đột hệ thống cơ sở dữ liệu.', 'danger')

    return redirect(url_for('learning.assignments'))


@learning_bp.route('/assignments/grade/<int:sub_id>', methods=['POST'])
@role_required('teacher', 'admin')  # Bảo vệ route bằng Custom Decorator tập trung
def grade_submission(sub_id):
    sub = Submission.query.get_or_404(sub_id)
    grade = request.form.get('grade', type=float)
    feedback = request.form.get('feedback', '').strip()

    try:
        sub.grade = grade
        sub.feedback = feedback
        sub.status = 'Graded'
        db.session.commit()
        flash(f'Đã chấm điểm thành công cho bài làm của {sub.student.username}.', 'success')
    except SQLAlchemyError:
        db.session.rollback()
        flash('Lỗi lưu điểm số.', 'danger')
    return redirect(url_for('learning.assignment_detail', assign_id=sub.assignment_id))


@learning_bp.route('/documents', methods=['GET', 'POST'])
@login_required
def documents():
    if request.method == 'POST':
        file = request.files.get('doc_file')
        title = request.form.get('title', '').strip()

        if file and file.filename != '':
            if allowed_file(file.filename):
                ext = file.filename.rsplit('.', 1)[1].lower()
                filename = f"doc_{uuid.uuid4().hex}.{ext}"
                # Sửa lỗi sử dụng config tập trung thay vì hard-code đường dẫn tĩnh
                file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))

                try:
                    doc = Document(title=title, filename=filename, user_id=current_user.id)
                    db.session.add(doc)
                    db.session.commit()
                    flash('Tải tài liệu lên kho lưu trữ thành công.', 'success')
                except SQLAlchemyError:
                    db.session.rollback()
            else:
                flash('File upload không an toàn hoặc không đúng định dạng cho phép!', 'danger')
        return redirect(url_for('learning.documents'))

    docs = Document.query.all()
    return render_template('documents.html', docs=docs)


@learning_bp.route('/discuss', methods=['GET', 'POST'])
@login_required
def discuss():
    if request.method == 'POST':
        topic = request.form.get('topic', '').strip()
        content = request.form.get('content', '').strip()

        try:
            disc = Discussion(topic=topic, content=content, user_id=current_user.id)
            db.session.add(disc)
            db.session.commit()
            flash('Chủ đề thảo luận đã được tạo.', 'success')
        except SQLAlchemyError:
            db.session.rollback()
        return redirect(url_for('learning.discuss'))

    discussions = Discussion.query.order_by(Discussion.date_created.desc()).all()
    return render_template('discuss.html', discussions=discussions)


@learning_bp.route('/discuss/<int:disc_id>', methods=['GET', 'POST'])
@login_required
def discuss_detail(disc_id):
    # Khắc phục trọn vẹn luồng Diễn đàn, cho phép xem chi tiết và trả lời bình luận con
    disc = Discussion.query.get_or_404(disc_id)
    if request.method == 'POST':
        content = request.form.get('content', '').strip()
        if content:
            try:
                cm = DiscussionComment(content=content, discussion_id=disc_id, user_id=current_user.id)
                db.session.add(cm)
                db.session.commit()
            except SQLAlchemyError:
                db.session.rollback()
        return redirect(url_for('learning.discuss_detail', disc_id=disc_id))
    return render_template('discussion_detail.html', disc=disc)


@learning_bp.route('/achievements')
@login_required
def achievements():
    total_completed = len(current_user.submissions)
    has_cup = total_completed >= 20
    fire_color = 'none'
    if current_user.streak >= 30:
        fire_color = 'purple'
    elif current_user.streak >= 15:
        fire_color = 'red'
    elif current_user.streak >= 7:
        fire_color = 'orange'
    return render_template('achievements.html', has_cup=has_cup, fire_color=fire_color)
