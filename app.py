import os
from flask import Flask
from config import Config
from models.database import db, bcrypt, login_manager


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Khởi tạo các thư viện mở rộng hệ thống
    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)

    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Vui lòng đăng nhập để truy cập hệ thống lớp học.'
    login_manager.login_message_category = 'warning'

    # Tự động tạo thư mục upload an toàn nếu chưa tồn tại
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])

    # Đăng ký các Blueprint điều hướng luồng nghiệp vụ
    from routes.auth import auth_bp
    from routes.main import main_bp
    from routes.learning import learning_bp
    from routes.admin import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(learning_bp)
    app.register_blueprint(admin_bp)

    # Khởi tạo cơ sở dữ liệu và tài khoản quản trị viên hệ thống
    with app.app_context():
        db.create_all()

        # Thiết lập tài khoản Admin mặc định an toàn
        from models.database import User
        admin_user = User.query.filter_by(role='admin').first()
        if not admin_user:
            hashed_pw = bcrypt.generate_password_hash('admin12345').decode('utf-8')
            default_admin = User(
                username='Quản Trị Viên',
                email='tronluc567@gmail.com',
                password=hashed_pw,
                role='Admin',
                is_approved=True
            )
            db.session.add(default_admin)
            db.session.commit()
    return app


if __name__ == '__main__':
    app = create_app()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
