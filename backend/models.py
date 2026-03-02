from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()



# ADMIN
class Admin(db.Model):
    __tablename__ = 'admin'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Admin {self.username}>'

# COMPANY
# approval_status: 'pending' | 'approved' | 'rejected' | 'blacklisted'
class Company(db.Model):
    __tablename__ = 'company'
    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    hr_contact = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    website = db.Column(db.String(200))
    description = db.Column(db.Text)
    approval_status = db.Column(db.String(20), default='pending')
    registered_at = db.Column(db.DateTime, default=datetime.utcnow)

    drives = db.relationship('PlacementDrive', backref='company', lazy=True,
                             cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Company {self.company_name}>'

# STUDENT
# is_active: False = blacklisted/deactivated by admin
class Student(db.Model):
    __tablename__ = 'student'
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    phone = db.Column(db.String(20))
    branch = db.Column(db.String(100))
    year = db.Column(db.String(20))
    cgpa = db.Column(db.Float)
    skills = db.Column(db.Text)
    resume_path = db.Column(db.String(300))
    is_active = db.Column(db.Boolean, default=True)
    registered_at = db.Column(db.DateTime, default=datetime.utcnow)

    applications = db.relationship('Application', backref='student', lazy=True,
                                   cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Student {self.full_name}>'

# PLACEMENT DRIVE
# status: 'pending' | 'approved' | 'closed' | 'rejected'
class PlacementDrive(db.Model):
    __tablename__ = 'placement_drive'
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    job_title = db.Column(db.String(150), nullable=False)
    job_description = db.Column(db.Text, nullable=False)
    eligibility_criteria = db.Column(db.Text)
    location = db.Column(db.String(100))
    salary_package = db.Column(db.String(100))
    application_deadline = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    applications = db.relationship('Application', backref='drive', lazy=True,
                                   cascade='all, delete-orphan')

    def __repr__(self):
        return f'<PlacementDrive {self.job_title}>'

# APPLICATION
# status: 'applied' | 'shortlisted' | 'selected' | 'rejected'
class Application(db.Model):
    __tablename__ = 'application'

    id               = db.Column(db.Integer, primary_key=True)
    student_id       = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    drive_id         = db.Column(db.Integer, db.ForeignKey('placement_drive.id'), nullable=False)
    application_date = db.Column(db.DateTime, default=datetime.utcnow)
    status           = db.Column(db.String(20), default='applied')

    # This ensures (student_id + drive_id) is always unique in the DB
    __table_args__ = (
        db.UniqueConstraint('student_id', 'drive_id', name='unique_application'),
    )

    def __repr__(self):
        return f'<Application Student:{self.student_id} Drive:{self.drive_id}>'