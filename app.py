from flask import Flask, render_template, request, redirect, flash, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Mail, Message
import random
import os

app = Flask(__name__)
app.secret_key = "placex_secret"

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['UPLOAD_FOLDER'] = "static/resumes"

db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


# ---------------- LOGIN LOADER ----------------

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# ---------------- MODELS ----------------

class User(db.Model, UserMixin):

    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)

    password = db.Column(db.String(200))

    role = db.Column(db.String(20))

    # student profile
    fullname = db.Column(db.String(150))
    contact = db.Column(db.String(20))
    location = db.Column(db.String(100))
    linkedin = db.Column(db.String(200))
    github = db.Column(db.String(200))
    portfolio = db.Column(db.String(200))
    resume = db.Column(db.String(200))


class Company(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer)
    name = db.Column(db.String(150))
    email = db.Column(db.String(150))
    location = db.Column(db.String(150))
    description = db.Column(db.Text)
    website = db.Column(db.String(200))


class Job(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    title = db.Column(db.String(100))
    description = db.Column(db.Text)

    company_name = db.Column(db.String(150))

    location = db.Column(db.String(100))
    job_type = db.Column(db.String(50))
    salary = db.Column(db.String(50))

    #  FIXED (link to User table)
    employer_id = db.Column(db.Integer, db.ForeignKey("user.id"))

    #  relationship
    employer = db.relationship("User")


class Application(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    job_id = db.Column(db.Integer, db.ForeignKey("job.id"))
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))

    status = db.Column(db.String(20), default="Pending")

    job = db.relationship("Job")
    user = db.relationship("User")


# ---------------- HOME ----------------

@app.route("/")
def home():

    jobs = Job.query.all()

    return render_template("index.html", jobs=jobs)


# ---------------- AUTH ----------------

@app.route("/register", methods=["GET","POST"])
def register():

    if request.method == "POST":

        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]
        confirm = request.form["confirm_password"]
        role = request.form["role"]

        # Check password match
        if password != confirm:
            flash("Passwords do not match", "error")
            return redirect(url_for("register"))

        # Check existing email
        existing_user = User.query.filter_by(email=email).first()

        if existing_user:
            flash("Email already registered", "error")
            return redirect(url_for("register"))

        # Hash password
        hashed_password = generate_password_hash(password)

        new_user = User(
            username=username,
            email=email,
            password=hashed_password,
            role=role
        )

        db.session.add(new_user)
        db.session.commit()

        flash("Registration successful", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET","POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        user = User.query.filter_by(email=email).first()

        if not user:
            flash("Email not found", "error")
            return redirect(url_for("login"))

        if not check_password_hash(user.password, password):
            flash("Incorrect password", "error")
            return redirect(url_for("login"))

        login_user(user)

        if user.role == "student":
            return redirect("/student_dashboard")
        else:
            return redirect("/employer_dashboard")

    return render_template("login.html")

@app.route("/forgot_password", methods=["GET","POST"])
def forgot_password():

    if request.method == "POST":

        email = request.form["email"]
        new_password = request.form["password"]

        user = User.query.filter_by(email=email).first()

        if not user:
            flash("Email not registered", "error")
            return redirect("/forgot_password")

        user.password = generate_password_hash(new_password)

        db.session.commit()

        flash("Password updated successfully", "success")
        return redirect("/login")

    return render_template("forgot_password.html")


@app.route("/logout")
@login_required
def logout():

    logout_user()

    return redirect("/")


# ---------------- STUDENT ----------------

@app.route("/student_dashboard")
@login_required
def student_dashboard():

    jobs = Job.query.all()

    total_jobs = Job.query.count()

    applied_jobs = Application.query.filter_by(user_id=current_user.id).count()

    accepted = Application.query.filter_by(
        user_id=current_user.id,
        status="Accepted"
    ).count()

    rejected = Application.query.filter_by(
        user_id=current_user.id,
        status="Rejected"
    ).count()

    return render_template(
        "student_dashboard.html",
        jobs=jobs,
        total_jobs=total_jobs,
        applied_jobs=applied_jobs,
        accepted=accepted,
        rejected=rejected
    )


@app.route("/profile", methods=["GET","POST"])
@login_required
def profile():

    if request.method == "POST":

        current_user.fullname = request.form["fullname"]
        current_user.email = request.form["email"]
        current_user.contact = request.form["contact"]
        current_user.location = request.form["location"]
        
        linkedin = request.form["linkedin"].strip()
        if linkedin and not linkedin.startswith(('http://', 'https://')):
            linkedin = 'https://' + linkedin
        current_user.linkedin = linkedin
        
        github = request.form["github"].strip()
        if github and not github.startswith(('http://', 'https://')):
            github = 'https://' + github
        current_user.github = github
        
        portfolio = request.form["portfolio"].strip()
        if portfolio and not portfolio.startswith(('http://', 'https://')):
            portfolio = 'https://' + portfolio
        current_user.portfolio = portfolio

        db.session.commit()

        flash("Profile saved successfully", "success")

    return render_template("profile.html", user=current_user)


@app.route('/upload_resume', methods=['POST'])
@login_required
def upload_resume():

    file = request.files['resume']

    if file.filename == "":
        flash("No file selected", "error")
        return redirect("/profile")

    filename = secure_filename(file.filename)

    path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    file.save(path)

    current_user.resume = filename

    db.session.commit()

    flash("Resume uploaded successfully", "success")

    return redirect("/profile")


@app.route("/available_jobs")
@login_required
def available_jobs():

    jobs = Job.query.all()

    return render_template("available_jobs.html", jobs=jobs)


@app.route("/apply/<int:job_id>")
@login_required
def apply(job_id):

    existing = Application.query.filter_by(
        job_id=job_id,
        user_id=current_user.id
    ).first()

    if existing:
        flash("Already applied", "error")
        return redirect("/available_jobs")

    app_job = Application(
        job_id=job_id,
        user_id=current_user.id
    )

    db.session.add(app_job)
    db.session.commit()

    flash("Application submitted", "success")

    return redirect("/applications")


@app.route("/applications")
@login_required
def applications():

    apps = Application.query.filter_by(user_id=current_user.id).all()

    return render_template("applications.html", apps=apps)


@app.route("/notifications")
@login_required
def notifications():

    return render_template("notifications.html")


# ---------------- EMPLOYER ----------------

@app.route("/employer_dashboard")
@login_required
def employer_dashboard():

    jobs = Job.query.filter_by(employer_id=current_user.id).all()

    total_jobs = Job.query.filter_by(
        employer_id=current_user.id
    ).count()

    total_apps = Application.query.join(Job).filter(
        Job.employer_id == current_user.id
    ).count()

    accepted = Application.query.join(Job).filter(
        Job.employer_id == current_user.id,
        Application.status == "Accepted"
    ).count()

    rejected = Application.query.join(Job).filter(
        Job.employer_id == current_user.id,
        Application.status == "Rejected"
    ).count()

    return render_template(
        "employer_dashboard.html",
        jobs=jobs,
        total_jobs=total_jobs,
        total_apps=total_apps,
        accepted=accepted,
        rejected=rejected
    )


@app.route("/company_profile", methods=["GET","POST"])
@login_required
def company_profile():

    company = Company.query.filter_by(user_id=current_user.id).first()

    if request.method == "POST":

        if not company:
            company = Company(user_id=current_user.id)

        company.name = request.form["name"]
        company.email = request.form["email"]
        company.location = request.form["location"]
        company.description = request.form["description"]
        company.website = request.form["website"]

        db.session.add(company)
        db.session.commit()

        flash("Company profile saved", "success")

    return render_template("company_profile.html", company=company)


@app.route('/post_job', methods=['GET','POST'])
@login_required
def post_job():

    company = Company.query.filter_by(user_id=current_user.id).first()

    if not company:
        flash("Please create company profile first", "error")
        return redirect("/company_profile")

    if request.method == "POST":

        job = Job(
            title=request.form["title"],
            description=request.form["description"],
            company_name=company.name,
            location=request.form["location"],
            job_type=request.form["job_type"],
            salary=request.form["salary"],
            employer_id=current_user.id
        )

        db.session.add(job)
        db.session.commit()

        flash("Job posted successfully", "success")

        return redirect("/manage_jobs")

    return render_template("post_job.html")


@app.route("/manage_jobs")
@login_required
def manage_jobs():

    jobs = Job.query.filter_by(employer_id=current_user.id).all()

    return render_template("manage_jobs.html", jobs=jobs)


@app.route("/delete_job/<int:id>")
@login_required
def delete_job(id):

    job = Job.query.get_or_404(id)

    db.session.delete(job)
    db.session.commit()

    flash("Job deleted", "success")

    return redirect("/manage_jobs")


@app.route("/edit_job/<int:id>", methods=["GET","POST"])
@login_required
def edit_job(id):

    job = Job.query.get_or_404(id)

    if request.method == "POST":

        job.title = request.form["title"]
        job.description = request.form["description"]
        job.location = request.form["location"]
        job.salary = request.form["salary"]
        job.job_type = request.form["job_type"]

        db.session.commit()

        flash("Job updated", "success")

        return redirect("/manage_jobs")

    return render_template("edit_job.html", job=job)


@app.route("/view_applications")
@login_required
def view_applications():

    if current_user.role != "employer":
        return "Unauthorized"

    # get jobs posted by this employer
    jobs = Job.query.filter_by(employer_id=current_user.id).all()

    job_ids = [job.id for job in jobs]

    # get applications only for those jobs
    apps = Application.query.filter(Application.job_id.in_(job_ids)).all()

    return render_template("view_applications.html", apps=apps)


@app.route("/student_profile/<int:id>")
@login_required
def student_profile(id):

    student = User.query.get_or_404(id)

    return render_template("student_profile.html", student=student)


@app.route("/update_application/<int:id>/<status>")
@login_required
def update_application(id,status):

    application = Application.query.get_or_404(id)

    application.status = status

    db.session.commit()

    flash("Application updated", "success")

    return redirect("/view_applications")


# ---------------- RUN ----------------

if __name__ == "__main__":

    with app.app_context():
        db.create_all()

    app.run(host="0.0.0.0", port=10000)        
