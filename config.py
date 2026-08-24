import os
from datetime import timedelta
from dotenv import load_dotenv

# Tải cấu hình bí mật từ file .env
load_dotenv()


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = ('sqlite:///classroom.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Quản lý đường dẫn file upload tập trung, tránh hard-code
    UPLOAD_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'static', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # Giới hạn file tối đa 16MB chống DoS

    # Cấu hình bảo mật cookie cho Flask-Login
    REMEMBER_COOKIE_DURATION = timedelta(days=7)
    REMEMBER_COOKIE_HTTPONLY = True

    # Danh sách định dạng file an toàn (Whitelist) chống tải mã độc RCE
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'docx', 'doc', 'xlsx', 'zip'}
