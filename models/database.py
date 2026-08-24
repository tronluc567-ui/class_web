from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin
from datetime import datetime

db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Bảng phụ liên kết Nhiều - Nhiều (M:N) đúng kỹ thuật ORM
likes = db.Table('likes',
                 db.Column('user_id', db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), primary_key=True),
                 db.Column('post_id', db.Integer, db.ForeignKey('post.id', ondelete='CASCADE'), primary_key=True)
                 )

hearts = db.Table('hearts',
                  db.Column('user_id', db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), primary_key=True),
                  db.Column('post_id', db.Integer, db.ForeignKey('post.id', ondelete='CASCADE'), primary_key=True)
                  )


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)  # Đã bổ sung Unique Constraint
    password = db.Column(db.String(255), nullable=False)  # Nâng lên 255 dự phòng mở rộng thuật toán băm
    role = db.Column(db.String(20), default='student')  # student, teacher, admin
    is_approved = db.Column(db.Boolean, default=False)

    # Hệ thống Gamification
    exp = db.Column(db.Integer, default=0)
    level = db.Column(db.Integer, default=1)
    streak = db.Column(db.Integer, default=0)
    last_sub_date = db.Column(db.Date, nullable=True)  # Sửa thành kiểu Date chuẩn

    # Cấu hình giao diện
    dark_mode = db.Column(db.Boolean, default=False)
    mute_notif = db.Column(db.Boolean, default=False)

    # Thiết lập Cascade Delete tránh lỗi mồ côi dữ liệu khi xóa tài khoản
    posts = db.relationship('Post', backref='author', lazy=True, cascade="all, delete-orphan")
    submissions = db.relationship('Submission', backref='student', lazy=True, cascade="all, delete-orphan")
    comments = db.relationship('Comment', backref='author', lazy=True, cascade="all, delete-orphan")
    disc_comments = db.relationship('DiscussionComment', backref='author', lazy=True, cascade="all, delete-orphan")


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    image_file = db.Column(db.String(100), nullable=True)
    content = db.Column(db.Text, nullable=False)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)

    liked_by = db.relationship('User', secondary=likes, backref=db.backref('liked_posts', lazy='dynamic'))
    hearted_by = db.relationship('User', secondary=hearts, backref=db.backref('hearted_posts', lazy='dynamic'))
    comments = db.relationship('Comment', backref='post', lazy=True, cascade="all, delete-orphan")


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)


class Assignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    due_date = db.Column(db.Date, nullable=False)  # Sửa thành kiểu Date chuẩn để tính toán thời gian
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    submissions = db.relationship('Submission', backref='assignment', lazy=True, cascade="all, delete-orphan")


class Submission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    assignment_id = db.Column(db.Integer, db.ForeignKey('assignment.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)

    # Sửa lỗi nghiệp vụ nộp bài: Cho phép đính kèm file hoặc link nội dung bài làm
    filename = db.Column(db.String(200), nullable=True)
    content = db.Column(db.Text, nullable=True)

    # Sửa lỗi nghiệp vụ chấm điểm
    status = db.Column(db.String(20), default='Submitted')  # Submitted, Graded
    grade = db.Column(db.Float, nullable=True)
    feedback = db.Column(db.Text, nullable=True)

    date_submitted = db.Column(db.DateTime, default=datetime.utcnow)

    # Sửa lỗi bảo mật: Thêm Unique Constraint để 1 học sinh chỉ được nộp 1 bản ghi duy nhất cho 1 bài tập
    __table_args__ = (db.UniqueConstraint('assignment_id', 'user_id', name='uq_user_assignment'),)


class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    filename = db.Column(db.String(200), nullable=False)

    # Khắc phục lỗi vi phạm toàn vẹn tham chiếu RDBMS của Giảng viên
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    uploader = db.relationship('User', backref='uploaded_documents')

    date_uploaded = db.Column(db.DateTime, default=datetime.utcnow)


class CalendarEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    event_date = db.Column(db.Date, nullable=False)  # Sửa thành kiểu Date chuẩn
    type = db.Column(db.String(50), default='exam')  # exam, activity


class Discussion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    topic = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)

    # Khắc phục lỗi vi phạm toàn vẹn tham chiếu RDBMS
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    creator = db.relationship('User', backref='discussions')

    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    comments = db.relationship('DiscussionComment', backref='discussion', lazy=True, cascade="all, delete-orphan")


# Sửa lỗi nghiệp vụ "Cụt ngọn": Cho phép mọi người thảo luận con bên trong Topic diễn đàn
class DiscussionComment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    discussion_id = db.Column(db.Integer, db.ForeignKey('discussion.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
