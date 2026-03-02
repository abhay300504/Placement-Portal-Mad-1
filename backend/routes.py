import os
from datetime import datetime, date
from functools import wraps
from flask import (render_template, request, redirect, url_for, flash, session, current_app)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

from backend.models import db, Admin, Company, Student, PlacementDrive, Application

# HELPER FUNCTIONS & LOGIN DECORATOR

def login_required(role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Please log in to continue.', 'warning')
                return redirect(url_for('auth_login', role=role))
            if session.get('role') != role:
                flash('You do not have permission to view that page.', 'danger')
                return redirect(url_for('home'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() == 'pdf'


# AUTH ROUTES  (login, register, logout, home)

def register_routes(app):
    # HOME PAGE
    @app.route('/')
    def home():
        """If already logged in, go straight to dashboard. Otherwise show home."""
        if 'user_id' in session:
            role = session.get('role')
            if role == 'admin':   return redirect(url_for('admin_dashboard'))
            if role == 'company': return redirect(url_for('company_dashboard'))
            if role == 'student': return redirect(url_for('student_dashboard'))
        return render_template('auth/home.html')


    # SHARED LOGIN  (/login?role=admin|company|student)
    @app.route('/login', methods=['GET', 'POST'])
    def auth_login():
        
        role = request.args.get('role') or request.form.get('role', 'student')

        if request.method == 'POST':
            email    = request.form.get('email', '').strip().lower()
            password = request.form.get('password', '')

            # Admin login
            if role == 'admin':
                admin = Admin.query.filter_by(email=email).first()
                if not admin or not check_password_hash(admin.password_hash, password):
                    flash('Invalid admin credentials.', 'danger')
                else:
                    session['user_id'] = admin.id
                    session['role']    = 'admin'
                    session['name']    = admin.username
                    flash('Welcome, Admin!', 'success')
                    return redirect(url_for('admin_dashboard'))

            # Company login
            elif role == 'company':
                company = Company.query.filter_by(email=email).first()
                if not company:
                    flash('No account found with this email.', 'danger')
                elif not check_password_hash(company.password_hash, password):
                    flash('Incorrect password.', 'danger')
                elif company.approval_status == 'pending':
                    flash('Your registration is pending admin approval.', 'warning')
                elif company.approval_status == 'rejected':
                    flash('Your registration was rejected. Contact admin.', 'danger')
                elif company.approval_status == 'blacklisted':
                    flash('Your account has been blacklisted.', 'danger')
                else:
                    session['user_id'] = company.id
                    session['role']    = 'company'
                    session['name']    = company.company_name
                    flash(f'Welcome, {company.company_name}!', 'success')
                    return redirect(url_for('company_dashboard'))

            # Student login
            else:
                student = Student.query.filter_by(email=email).first()
                if not student:
                    flash('No account found with this email.', 'danger')
                elif not check_password_hash(student.password_hash, password):
                    flash('Incorrect password.', 'danger')
                elif not student.is_active:
                    flash('Your account has been deactivated. Contact admin.', 'danger')
                else:
                    session['user_id'] = student.id
                    session['role']    = 'student'
                    session['name']    = student.full_name
                    flash(f'Welcome, {student.full_name}!', 'success')
                    return redirect(url_for('student_dashboard'))

        return render_template('auth/login.html', role=role)


    # SHARED REGISTER  (/register?role=company|student)
    @app.route('/register', methods=['GET', 'POST'])
    def auth_register():
        
        role = request.args.get('role') or request.form.get('role', 'student')

        if request.method == 'POST':
            email    = request.form.get('email', '').strip().lower()
            password = request.form.get('password', '')
            confirm  = request.form.get('confirm_password', '')
            phone    = request.form.get('phone', '').strip()

            # Common validation check 
            if not email or not password:
                flash('Email and password are required.', 'danger')
                return render_template('auth/register.html', role=role)
            if password != confirm:
                flash('Passwords do not match.', 'danger')
                return render_template('auth/register.html', role=role)
            if len(password) < 6:
                flash('Password must be at least 6 characters.', 'danger')
                return render_template('auth/register.html', role=role)

            # Student registration
            if role == 'student':
                full_name = request.form.get('full_name', '').strip()
                branch    = request.form.get('branch', '').strip()
                year      = request.form.get('year', '').strip()

                if not full_name:
                    flash('Full name is required.', 'danger')
                    return render_template('auth/register.html', role=role)
                if Student.query.filter_by(email=email).first():
                    flash('An account with this email already exists.', 'danger')
                    return render_template('auth/register.html', role=role)

                student = Student(
                    full_name     = full_name,
                    email         = email,
                    password_hash = generate_password_hash(password),
                    phone         = phone,
                    branch        = branch,
                    year          = year
                )
                db.session.add(student)
                db.session.commit()
                flash('Registration successful! Please log in.', 'success')
                return redirect(url_for('auth_login', role='student'))

            # Company registration
            elif role == 'company':
                company_name = request.form.get('company_name', '').strip()
                hr_contact   = request.form.get('hr_contact', '').strip()
                website      = request.form.get('website', '').strip()
                description  = request.form.get('description', '').strip()

                if not company_name:
                    flash('Company name is required.', 'danger')
                    return render_template('auth/register.html', role=role)
                if Company.query.filter_by(email=email).first():
                    flash('An account with this email already exists.', 'danger')
                    return render_template('auth/register.html', role=role)

                company = Company(
                    company_name    = company_name,
                    email           = email,
                    password_hash   = generate_password_hash(password),
                    hr_contact      = hr_contact,
                    phone           = phone,
                    website         = website,
                    description     = description,
                    approval_status = 'pending'
                )
                db.session.add(company)
                db.session.commit()
                flash('Registration submitted! Awaiting admin approval.', 'success')
                return redirect(url_for('auth_login', role='company'))

        return render_template('auth/register.html', role=role)


    # (all roles)
    @app.route('/logout')
    def logout():
        session.clear()
        flash('You have been logged out.', 'info')
        return redirect(url_for('home'))


    # ADMIN ROUTES

    @app.route('/admin/dashboard')
    @login_required('admin')
    def admin_dashboard():
        stats = {
            'total_students'    : Student.query.count(),
            'total_companies'   : Company.query.count(),
            'total_drives'      : PlacementDrive.query.count(),
            'total_applications': Application.query.count(),
            'pending_companies' : Company.query.filter_by(approval_status='pending').count(),
            'pending_drives'    : PlacementDrive.query.filter_by(status='pending').count(),
        }
        recent_companies = Company.query.order_by(Company.registered_at.desc()).limit(5).all()
        recent_drives    = PlacementDrive.query.order_by(PlacementDrive.created_at.desc()).limit(5).all()
        return render_template('admin/dashboard.html',
                               stats=stats,
                               recent_companies=recent_companies,
                               recent_drives=recent_drives)


    # Admin: Company Management
    @app.route('/admin/companies')
    @login_required('admin')
    def admin_companies():
        search        = request.args.get('search', '').strip()
        query         = Company.query
        if search:
            query = query.filter(Company.company_name.ilike(f'%{search}%'))
        all_companies = query.order_by(Company.registered_at.desc()).all()
        return render_template('admin/companies.html',
                               companies=all_companies, search=search)


    @app.route('/admin/companies/<int:company_id>')
    @login_required('admin')
    def admin_company_detail(company_id):
        company = Company.query.get_or_404(company_id)
        drives  = PlacementDrive.query.filter_by(company_id=company_id).all()
        return render_template('admin/company_detail.html',
                               company=company, drives=drives)


    @app.route('/admin/companies/<int:company_id>/approve')
    @login_required('admin')
    def admin_approve_company(company_id):
        company = Company.query.get_or_404(company_id)
        company.approval_status = 'approved'
        db.session.commit()
        flash(f'"{company.company_name}" approved.', 'success')
        return redirect(url_for('admin_companies'))


    @app.route('/admin/companies/<int:company_id>/reject')
    @login_required('admin')
    def admin_reject_company(company_id):
        company = Company.query.get_or_404(company_id)
        company.approval_status = 'rejected'
        db.session.commit()
        flash(f'"{company.company_name}" rejected.', 'warning')
        return redirect(url_for('admin_companies'))


    @app.route('/admin/companies/<int:company_id>/blacklist')
    @login_required('admin')
    def admin_blacklist_company(company_id):
        company = Company.query.get_or_404(company_id)
        company.approval_status = 'blacklisted'
        db.session.commit()
        flash(f'"{company.company_name}" blacklisted.', 'danger')
        return redirect(url_for('admin_companies'))


    @app.route('/admin/companies/<int:company_id>/delete')
    @login_required('admin')
    def admin_delete_company(company_id):
        company = Company.query.get_or_404(company_id)
        db.session.delete(company)
        db.session.commit()
        flash('Company deleted.', 'success')
        return redirect(url_for('admin_companies'))


    # Admin: Student Management
    @app.route('/admin/students')
    @login_required('admin')
    def admin_students():
        search = request.args.get('search', '').strip()
        query  = Student.query
        if search:
            query = query.filter(
                db.or_(
                    Student.full_name.ilike(f'%{search}%'),
                    Student.email.ilike(f'%{search}%'),
                    Student.phone.ilike(f'%{search}%')
                )
            )
        all_students = query.order_by(Student.registered_at.desc()).all()
        return render_template('admin/students.html',
                               students=all_students, search=search)


    @app.route('/admin/students/<int:student_id>')
    @login_required('admin')
    def admin_student_detail(student_id):
        student      = Student.query.get_or_404(student_id)
        applications = Application.query.filter_by(student_id=student_id).all()
        return render_template('admin/student_detail.html',
                               student=student, applications=applications)


    @app.route('/admin/students/<int:student_id>/edit', methods=['GET', 'POST'])
    @login_required('admin')
    def admin_edit_student(student_id):
        student = Student.query.get_or_404(student_id)
        if request.method == 'POST':
            student.full_name = request.form.get('full_name', '').strip()
            student.email = request.form.get('email', '').strip()
            student.phone = request.form.get('phone', '').strip()
            student.branch = request.form.get('branch', '').strip()
            student.year = request.form.get('year', '').strip()
            cgpa_str = request.form.get('cgpa', '')
            if cgpa_str:
                try:
                    student.cgpa = float(cgpa_str)
                except ValueError:
                    flash('CGPA must be a valid number.', 'danger')
                    return render_template('admin/edit_student.html', student=student)
            db.session.commit()
            flash('Student updated.', 'success')
            return redirect(url_for('admin_student_detail', student_id=student_id))
        return render_template('admin/edit_student.html', student=student)


    @app.route('/admin/students/<int:student_id>/toggle')
    @login_required('admin')
    def admin_toggle_student(student_id):
        student           = Student.query.get_or_404(student_id)
        student.is_active = not student.is_active
        db.session.commit()
        status = 'activated' if student.is_active else 'deactivated'
        flash(f'Student "{student.full_name}" {status}.', 'info')
        return redirect(url_for('admin_students'))


    @app.route('/admin/students/<int:student_id>/delete')
    @login_required('admin')
    def admin_delete_student(student_id):
        student = Student.query.get_or_404(student_id)
        db.session.delete(student)
        db.session.commit()
        flash('Student deleted.', 'success')
        return redirect(url_for('admin_students'))


    # Admin: Placement Drive Management
    @app.route('/admin/drives')
    @login_required('admin')
    def admin_drives():
        status_filter = request.args.get('status', '')
        query         = PlacementDrive.query
        if status_filter:
            query = query.filter_by(status=status_filter)
        all_drives = query.order_by(PlacementDrive.created_at.desc()).all()
        return render_template('admin/drives.html',
                               drives=all_drives, status_filter=status_filter)


    @app.route('/admin/drives/<int:drive_id>')
    @login_required('admin')
    def admin_drive_detail(drive_id):
        drive        = PlacementDrive.query.get_or_404(drive_id)
        applications = Application.query.filter_by(drive_id=drive_id).all()
        return render_template('admin/drive_detail.html',
                               drive=drive, applications=applications)


    @app.route('/admin/drives/<int:drive_id>/approve')
    @login_required('admin')
    def admin_approve_drive(drive_id):
        drive        = PlacementDrive.query.get_or_404(drive_id)
        drive.status = 'approved'
        db.session.commit()
        flash(f'Drive "{drive.job_title}" approved.', 'success')
        return redirect(url_for('admin_drives'))


    @app.route('/admin/drives/<int:drive_id>/reject')
    @login_required('admin')
    def admin_reject_drive(drive_id):
        drive        = PlacementDrive.query.get_or_404(drive_id)
        drive.status = 'rejected'
        db.session.commit()
        flash(f'Drive "{drive.job_title}" rejected.', 'warning')
        return redirect(url_for('admin_drives'))


    # Admin: All Applications
    @app.route('/admin/applications')
    @login_required('admin')
    def admin_applications():
        all_apps = Application.query.order_by(Application.application_date.desc()).all()
        return render_template('admin/applications.html', applications=all_apps)


    # Admin: Search
    @app.route('/admin/search')
    @login_required('admin')
    def admin_search():
        query     = request.args.get('q', '').strip()
        students  = []
        companies = []
        if query:
            students = Student.query.filter(
                db.or_(
                    Student.full_name.ilike(f'%{query}%'),
                    Student.email.ilike(f'%{query}%'),
                    Student.phone.ilike(f'%{query}%')
                )
            ).all()
            companies = Company.query.filter(
                db.or_(
                    Company.company_name.ilike(f'%{query}%'),
                    Company.email.ilike(f'%{query}%')
                )
            ).all()
        return render_template('admin/search.html',
                               query=query, students=students, companies=companies)


    # COMPANY ROUTES

    @app.route('/company/dashboard')
    @login_required('company')
    def company_dashboard():
        company    = Company.query.get(session['user_id'])
        drives     = PlacementDrive.query.filter_by(company_id=company.id).all()
        drive_data = []
        for drive in drives:
            count = Application.query.filter_by(drive_id=drive.id).count()
            drive_data.append({'drive': drive, 'applicant_count': count})
        return render_template('company/dashboard.html',
                               company=company, drive_data=drive_data)


    @app.route('/company/profile/edit', methods=['GET', 'POST'])
    @login_required('company')
    def company_edit_profile():
        company = Company.query.get(session['user_id'])
        if request.method == 'POST':
            company.company_name = request.form.get('company_name', '').strip()
            company.hr_contact   = request.form.get('hr_contact', '').strip()
            company.phone        = request.form.get('phone', '').strip()
            company.website      = request.form.get('website', '').strip()
            company.description  = request.form.get('description', '').strip()
            db.session.commit()
            session['name'] = company.company_name
            flash('Profile updated!', 'success')
            return redirect(url_for('company_dashboard'))
        return render_template('company/edit_profile.html', company=company)


    @app.route('/company/drives')
    @login_required('company')
    def company_drives():
        company    = Company.query.get(session['user_id'])
        all_drives = (PlacementDrive.query
                      .filter_by(company_id=company.id)
                      .order_by(PlacementDrive.created_at.desc()).all())
        return render_template('company/drives.html',
                               drives=all_drives, company=company)


    @app.route('/company/drives/create', methods=['GET', 'POST'])
    @login_required('company')
    def company_create_drive():
        company = Company.query.get(session['user_id'])
        if company.approval_status != 'approved':
            flash('Only approved companies can create drives.', 'danger')
            return redirect(url_for('company_dashboard'))

        if request.method == 'POST':
            job_title    = request.form.get('job_title', '').strip()
            job_desc     = request.form.get('job_description', '').strip()
            eligibility  = request.form.get('eligibility_criteria', '').strip()
            location     = request.form.get('location', '').strip()
            salary       = request.form.get('salary_package', '').strip()
            deadline_str = request.form.get('application_deadline', '')

            if not all([job_title, job_desc, deadline_str]):
                flash('Job title, description and deadline are required.', 'danger')
                return render_template('company/create_drive.html')
            try:
                deadline = datetime.strptime(deadline_str, '%Y-%m-%d').date()
            except ValueError:
                flash('Invalid date format.', 'danger')
                return render_template('company/create_drive.html')
            if deadline < date.today():
                flash('Deadline cannot be in the past.', 'danger')
                return render_template('company/create_drive.html')

            drive = PlacementDrive(
                company_id           = company.id,
                job_title            = job_title,
                job_description      = job_desc,
                eligibility_criteria = eligibility,
                location             = location,
                salary_package       = salary,
                application_deadline = deadline,
                status               = 'pending'
            )
            db.session.add(drive)
            db.session.commit()
            flash(f'Drive "{job_title}" submitted for admin approval.', 'success')
            return redirect(url_for('company_drives'))

        return render_template('company/create_drive.html')


    @app.route('/company/drives/<int:drive_id>/edit', methods=['GET', 'POST'])
    @login_required('company')
    def company_edit_drive(drive_id):
        company = Company.query.get(session['user_id'])
        drive   = PlacementDrive.query.get_or_404(drive_id)
        if drive.company_id != company.id:
            flash('Access denied.', 'danger')
            return redirect(url_for('company_drives'))

        if request.method == 'POST':
            drive.job_title            = request.form.get('job_title', '').strip()
            drive.job_description      = request.form.get('job_description', '').strip()
            drive.eligibility_criteria = request.form.get('eligibility_criteria', '').strip()
            drive.location             = request.form.get('location', '').strip()
            drive.salary_package       = request.form.get('salary_package', '').strip()
            deadline_str               = request.form.get('application_deadline', '')
            if deadline_str:
                try:
                    drive.application_deadline = datetime.strptime(deadline_str, '%Y-%m-%d').date()
                except ValueError:
                    flash('Invalid date.', 'danger')
                    return render_template('company/edit_drive.html', drive=drive)
            drive.status = 'pending'   # re-approve after edit
            db.session.commit()
            flash('Drive updated and re-submitted for approval.', 'success')
            return redirect(url_for('company_drives'))

        return render_template('company/edit_drive.html', drive=drive)


    @app.route('/company/drives/<int:drive_id>/delete')
    @login_required('company')
    def company_delete_drive(drive_id):
        company = Company.query.get(session['user_id'])
        drive   = PlacementDrive.query.get_or_404(drive_id)
        if drive.company_id != company.id:
            flash('Access denied.', 'danger')
            return redirect(url_for('company_drives'))
        db.session.delete(drive)
        db.session.commit()
        flash('Drive deleted.', 'success')
        return redirect(url_for('company_drives'))


    @app.route('/company/drives/<int:drive_id>/close')
    @login_required('company')
    def company_close_drive(drive_id):
        company = Company.query.get(session['user_id'])
        drive   = PlacementDrive.query.get_or_404(drive_id)
        if drive.company_id != company.id:
            flash('Access denied.', 'danger')
            return redirect(url_for('company_drives'))
        drive.status = 'closed'
        db.session.commit()
        flash(f'Drive "{drive.job_title}" closed.', 'info')
        return redirect(url_for('company_drives'))


    @app.route('/company/drives/<int:drive_id>/applications')
    @login_required('company')
    def company_drive_applications(drive_id):
        company       = Company.query.get(session['user_id'])
        drive         = PlacementDrive.query.get_or_404(drive_id)
        if drive.company_id != company.id:
            flash('Access denied.', 'danger')
            return redirect(url_for('company_drives'))
        status_filter = request.args.get('status', '')
        query         = Application.query.filter_by(drive_id=drive_id)
        if status_filter:
            query = query.filter_by(status=status_filter)
        applications  = query.all()
        return render_template('company/drive_applications.html',
                               drive=drive, applications=applications,
                               status_filter=status_filter)


    @app.route('/company/applications/<int:app_id>/update', methods=['POST'])
    @login_required('company')
    def company_update_application(app_id):
        application = Application.query.get_or_404(app_id)
        company     = Company.query.get(session['user_id'])
        drive       = PlacementDrive.query.get(application.drive_id)
        if not drive or drive.company_id != company.id:
            flash('Access denied.', 'danger')
            return redirect(url_for('company_drives'))
        new_status = request.form.get('status', '')
        if new_status in ['applied', 'shortlisted', 'selected', 'rejected']:
            application.status = new_status
            db.session.commit()
            flash(f'Status updated to "{new_status}".', 'success')
        else:
            flash('Invalid status.', 'danger')
        return redirect(url_for('company_drive_applications', drive_id=application.drive_id))


    # STUDENT ROUTES

    @app.route('/student/dashboard')
    @login_required('student')
    def student_dashboard():
        student         = Student.query.get(session['user_id'])
        approved_drives = (PlacementDrive.query
                           .filter_by(status='approved')
                           .order_by(PlacementDrive.created_at.desc())
                           .limit(5).all())
        my_applications = (Application.query
                           .filter_by(student_id=student.id)
                           .order_by(Application.application_date.desc())
                           .all())
        return render_template('student/dashboard.html',
                               student=student,
                               approved_drives=approved_drives,
                               my_applications=my_applications)


    @app.route('/student/profile/edit', methods=['GET', 'POST'])
    @login_required('student')
    def student_edit_profile():
        student = Student.query.get(session['user_id'])
        if request.method == 'POST':
            student.full_name = request.form.get('full_name', '').strip()
            student.phone     = request.form.get('phone', '').strip()
            student.branch    = request.form.get('branch', '').strip()
            student.year      = request.form.get('year', '').strip()
            student.skills    = request.form.get('skills', '').strip()
            cgpa_str          = request.form.get('cgpa', '')
            if cgpa_str:
                try:
                    cgpa = float(cgpa_str)
                    if 0 <= cgpa <= 10:
                        student.cgpa = cgpa
                    else:
                        flash('CGPA must be between 0 and 10.', 'danger')
                        return render_template('student/edit_profile.html', student=student)
                except ValueError:
                    flash('CGPA must be a number.', 'danger')
                    return render_template('student/edit_profile.html', student=student)

            # Resume upload
            file = request.files.get('resume')
            if file and file.filename:
                if not allowed_file(file.filename):
                    flash('Only PDF resumes are allowed.', 'danger')
                    return render_template('student/edit_profile.html', student=student)
                filename      = secure_filename(f"resume_{student.id}_{file.filename}")
                upload_folder = os.path.join('static', 'uploads', 'resumes')
                os.makedirs(upload_folder, exist_ok=True)
                file.save(os.path.join(upload_folder, filename))
                student.resume_path = os.path.join(upload_folder, filename)

            db.session.commit()
            session['name'] = student.full_name
            flash('Profile updated!', 'success')
            return redirect(url_for('student_dashboard'))

        return render_template('student/edit_profile.html', student=student)


    @app.route('/student/drives')
    @login_required('student')
    def student_drives():
        search = request.args.get('search', '').strip()
        query  = PlacementDrive.query.filter_by(status='approved')
        if search:
            query = (query.join(Company).filter(
                db.or_(
                    PlacementDrive.job_title.ilike(f'%{search}%'),
                    Company.company_name.ilike(f'%{search}%')
                )
            ))
        approved_drives   = query.order_by(PlacementDrive.application_deadline.asc()).all()
        student           = Student.query.get(session['user_id'])
        applied_drive_ids = {
            a.drive_id for a in Application.query.filter_by(student_id=student.id).all()
        }
        return render_template('student/drives.html',
                               drives=approved_drives,
                               applied_drive_ids=applied_drive_ids,
                               search=search)


    @app.route('/student/drives/<int:drive_id>')
    @login_required('student')
    def student_drive_detail(drive_id):
        drive = PlacementDrive.query.get_or_404(drive_id)
        if drive.status != 'approved':
            flash('This drive is not available.', 'warning')
            return redirect(url_for('student_drives'))
        student      = Student.query.get(session['user_id'])
        existing_app = Application.query.filter_by(
            student_id=student.id, drive_id=drive_id).first()
        return render_template('student/drive_detail.html',
                               drive=drive, existing_app=existing_app)


    @app.route('/student/drives/<int:drive_id>/apply', methods=['POST'])
    @login_required('student')
    def student_apply(drive_id):
        student = Student.query.get(session['user_id'])
        drive   = PlacementDrive.query.get_or_404(drive_id)

        if drive.status != 'approved':
            flash('This drive is not open for applications.', 'warning')
            return redirect(url_for('student_drives'))
        if drive.application_deadline < date.today():
            flash('The application deadline has passed.', 'warning')
            return redirect(url_for('student_drive_detail', drive_id=drive_id))

        existing = Application.query.filter_by(
            student_id=student.id, drive_id=drive_id).first()
        if existing:
            flash('You have already applied to this drive.', 'warning')
            return redirect(url_for('student_drive_detail', drive_id=drive_id))

        application = Application(
            student_id = student.id,
            drive_id   = drive_id,
            status     = 'applied'
        )
        db.session.add(application)
        db.session.commit()
        flash(f'Successfully applied to "{drive.job_title}"!', 'success')
        return redirect(url_for('student_applications'))


    @app.route('/student/applications')
    @login_required('student')
    def student_applications():
        student  = Student.query.get(session['user_id'])
        all_apps = (Application.query
                    .filter_by(student_id=student.id)
                    .order_by(Application.application_date.desc())
                    .all())
        return render_template('student/applications.html',
                               applications=all_apps, student=student)
