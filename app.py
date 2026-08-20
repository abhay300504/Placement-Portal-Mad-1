import os
from flask import Flask
from werkzeug.security import generate_password_hash

from backend.models import db, Admin
from backend.routes import register_routes

app = Flask(__name__)

app.config['SECRET_KEY']                  = 'placement_portal_secret_2024'
app.config['SQLALCHEMY_DATABASE_URI']     = 'sqlite:///placement_portal.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER']               = os.path.join('static', 'uploads', 'resumes')
app.config['MAX_CONTENT_LENGTH']          = 5 * 1024 * 1024  # 5 MB max file upload

db.init_app(app)

register_routes(app)

with app.app_context():
    db.create_all()

    if not Admin.query.first():
        admin = Admin(
            username      = 'admin',
            email         = 'admin@placement.com',
            password_hash = generate_password_hash('admin123')
        )
        db.session.add(admin)
        db.session.commit()
        print("=" * 50)
        print("  Default admin created!")
        print("  Email   : admin@placement.com")
        print("  Password: admin123")
        print("=" * 50)

        # main

if __name__ == '__main__':
    app.run(debug=True)