from datetime import datetime
import os
from urllib.parse import quote_plus
from dotenv import load_dotenv

load_dotenv()
from functools import wraps
from io import BytesIO

from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from werkzeug.security import generate_password_hash, check_password_hash
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from services.rule_engine import evaluate_risk
from services.recommendation_service import (
    get_recommendation,
    get_recommendation_key,
    get_test_recommendation,
    get_test_recommendation_key,
)

def get_env_value(primary_key, aliases=None, default=None):
    keys = [primary_key] + (aliases or [])
    for key in keys:
        value = os.getenv(key)
        if value not in (None, ""):
            return value
    return default


app = Flask(__name__)
app.config["SECRET_KEY"] = get_env_value("SECRET_KEY", default="change-this-secret-key")

db_user = get_env_value("DB_USER", ["MYSQL_USER"], "root")
db_password = get_env_value("DB_PASSWORD", ["MYSQL_PASSWORD"], "")
db_host = get_env_value("DB_HOST", ["MYSQL_HOST"], "127.0.0.1")
db_name = get_env_value("DB_NAME", ["MYSQL_DB"], "tb_cdss")

app.config["SQLALCHEMY_DATABASE_URI"] = (
    f"mysql+pymysql://{quote_plus(db_user)}:{quote_plus(db_password)}"
    f"@{db_host}/{db_name}"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), nullable=False, default="health_worker")
    can_add_user = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Screening(db.Model):
    __tablename__ = "screenings"

    id = db.Column(db.Integer, primary_key=True)

    patient_name = db.Column(db.String(120), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    gender = db.Column(db.String(20), nullable=False)

    cough = db.Column(db.Boolean, nullable=False)
    cough_duration = db.Column(db.Boolean, nullable=False)
    night_sweats = db.Column(db.Boolean, nullable=False)
    weight_loss = db.Column(db.Boolean, nullable=False)
    coughing_blood = db.Column(db.Boolean, nullable=False)
    fever = db.Column(db.Boolean, nullable=False)
    fatigue = db.Column(db.Boolean, nullable=False)
    chest_pain = db.Column(db.Boolean, nullable=False)

    risk_level = db.Column(db.String(20), nullable=False)
    recommendation = db.Column(db.Text, nullable=False)
    language_selected = db.Column(db.String(20), nullable=False, default="en")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class PermissionRequest(db.Model):
    __tablename__ = "permission_requests"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    permission_type = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="pending")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    reviewed_at = db.Column(db.DateTime, nullable=True)

    user = db.relationship("User", backref="permission_requests")


@app.before_request
def refresh_logged_in_user_session():
    if session.get("user_id"):
        user = User.query.get(session["user_id"])

        if not user:
            session.clear()
            return

        session["user_name"] = user.full_name
        session["user_role"] = user.role
        session["can_add_user"] = user.can_add_user


def login_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)
    return wrapper


def admin_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in first.", "warning")
            return redirect(url_for("login"))

        if session.get("user_role") != "admin":
            flash("Access denied. Admins only.", "danger")
            return redirect(url_for("dashboard"))

        return view_func(*args, **kwargs)
    return wrapper


def add_user_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in first.", "warning")
            return redirect(url_for("login"))

        if session.get("user_role") == "admin" or session.get("can_add_user"):
            return view_func(*args, **kwargs)

        flash("You do not have permission to add users.", "danger")
        return redirect(url_for("dashboard"))
    return wrapper


@app.context_processor
def inject_pending_permission_count():
    count = 0

    if session.get("user_role") == "admin":
        count = PermissionRequest.query.filter_by(status="pending").count()

    return {
        "pending_permission_count": count
    }


def ensure_user_schema():
    inspector = db.inspect(db.engine)
    if not inspector.has_table("users"):
        return

    columns = {column["name"] for column in inspector.get_columns("users")}

    if "full_name" not in columns:
        if "name" in columns:
            db.session.execute(text("ALTER TABLE users ADD COLUMN full_name VARCHAR(120) NOT NULL DEFAULT ''"))
            db.session.execute(text("UPDATE users SET full_name = COALESCE(name, email) WHERE full_name = '' OR full_name IS NULL"))
        else:
            db.session.execute(text("ALTER TABLE users ADD COLUMN full_name VARCHAR(120) NOT NULL DEFAULT ''"))

    if "can_add_user" not in columns:
        db.session.execute(text("ALTER TABLE users ADD COLUMN can_add_user BOOLEAN NOT NULL DEFAULT FALSE"))

    db.session.commit()


with app.app_context():
    db.create_all()
    ensure_user_schema()

    default_user = User.query.filter_by(email="admin@tbcare.com").first()
    if not default_user:
        default_user = User(
            full_name="System Admin",
            email="admin@tbcare.com",
            role="admin",
            can_add_user=True
        )
        default_user.set_password("admin123")
        db.session.add(default_user)
        db.session.commit()


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/screening")
def screening():
    return render_template("screening.html")


@app.route("/submit-screening", methods=["POST"])
def submit_screening():
    patient_name = request.form.get("patient_name", "").strip()
    age = request.form.get("age", "").strip()
    gender = request.form.get("gender", "").strip()

    if not patient_name or not age or not gender:
        flash("Please fill in patient name, age, and gender.", "danger")
        return redirect(url_for("screening"))

    data = {
        "cough": request.form.get("cough") == "Yes",
        "cough_duration": request.form.get("cough_duration") == "Yes",
        "night_sweats": request.form.get("night_sweats") == "Yes",
        "weight_loss": request.form.get("weight_loss") == "Yes",
        "coughing_blood": request.form.get("coughing_blood") == "Yes",
        "fever": request.form.get("fever") == "Yes",
        "fatigue": request.form.get("fatigue") == "Yes",
        "chest_pain": request.form.get("chest_pain") == "Yes",
    }

    language_selected = request.form.get("language_selected", "en")

    risk_level = evaluate_risk(data)
    recommendation = get_recommendation(risk_level)
    recommendation_key = get_recommendation_key(risk_level)
    test_recommendation = get_test_recommendation(risk_level)
    test_recommendation_key = get_test_recommendation_key(risk_level)

    risk_key_map = {
        "Low": "risk.low",
        "Moderate": "risk.moderate",
        "High": "risk.high",
        "Emergency": "risk.emergency",
    }
    risk_key = risk_key_map.get(risk_level, "risk.low")

    screening_record = Screening(
        patient_name=patient_name,
        age=int(age),
        gender=gender,
        cough=data["cough"],
        cough_duration=data["cough_duration"],
        night_sweats=data["night_sweats"],
        weight_loss=data["weight_loss"],
        coughing_blood=data["coughing_blood"],
        fever=data["fever"],
        fatigue=data["fatigue"],
        chest_pain=data["chest_pain"],
        risk_level=risk_level,
        recommendation=recommendation,
        language_selected=language_selected,
    )

    db.session.add(screening_record)
    db.session.commit()

    return render_template(
        "result.html",
        screening_id=screening_record.id,
        risk_level=risk_level,
        recommendation=recommendation,
        test_recommendation=test_recommendation,
        risk_key=risk_key,
        recommendation_key=recommendation_key,
        test_recommendation_key=test_recommendation_key,
    )


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            session.clear()
            session["user_id"] = user.id
            session["user_name"] = user.full_name
            session["user_role"] = user.role
            session["can_add_user"] = user.can_add_user

            flash(f"Welcome, {user.full_name}", "success")
            return redirect(url_for("dashboard"))

        flash("Invalid email or password.", "danger")
        return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    screenings = Screening.query.order_by(Screening.created_at.desc()).all()

    total_screenings = Screening.query.count()
    low = Screening.query.filter_by(risk_level="Low").count()
    moderate = Screening.query.filter_by(risk_level="Moderate").count()
    high = Screening.query.filter_by(risk_level="High").count()
    emergency = Screening.query.filter_by(risk_level="Emergency").count()

    existing_request = PermissionRequest.query.filter_by(
        user_id=session["user_id"],
        permission_type="add_user",
        status="pending"
    ).first()

    latest_request = PermissionRequest.query.filter_by(
        user_id=session["user_id"],
        permission_type="add_user"
    ).order_by(PermissionRequest.created_at.desc()).first()

    pending_permission_count = PermissionRequest.query.filter_by(
        status="pending"
    ).count()

    return render_template(
        "dashboard.html",
        screenings=screenings,
        total_screenings=total_screenings,
        high_risk_cases=high,
        emergency_cases=emergency,
        low=low,
        moderate=moderate,
        high=high,
        emergency=emergency,
        existing_request=existing_request,
        latest_request=latest_request,
        pending_permission_count=pending_permission_count
    )


@app.route("/register", methods=["GET", "POST"])
@add_user_required
def register():
    if request.method == "POST":
        full_name = request.form.get("full_name")
        email = request.form.get("email")
        password = request.form.get("password")

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("User already exists.", "warning")
            return redirect(url_for("register"))

        new_user = User(
            full_name=full_name,
            email=email,
            role="health_worker",
            can_add_user=False
        )
        new_user.set_password(password)

        db.session.add(new_user)
        db.session.commit()

        flash("User created successfully.", "success")
        return redirect(url_for("dashboard"))

    return render_template("register.html")


@app.route("/request-add-user-access", methods=["POST"])
@login_required
def request_add_user_access():
    if session.get("user_role") == "admin" or session.get("can_add_user"):
        flash("You already have permission to add users.", "warning")
        return redirect(url_for("dashboard"))

    existing_request = PermissionRequest.query.filter_by(
        user_id=session["user_id"],
        permission_type="add_user",
        status="pending"
    ).first()

    if existing_request:
        flash("You already have a pending request.", "warning")
        return redirect(url_for("dashboard"))

    new_request = PermissionRequest(
        user_id=session["user_id"],
        permission_type="add_user",
        status="pending"
    )

    db.session.add(new_request)
    db.session.commit()

    flash("Permission request sent successfully.", "success")
    return redirect(url_for("dashboard"))


@app.route("/permission-requests")
@admin_required
def permission_requests():
    requests = PermissionRequest.query.order_by(PermissionRequest.created_at.desc()).all()
    users_with_permission = User.query.filter_by(can_add_user=True).order_by(User.full_name.asc()).all()

    return render_template(
        "permission_requests.html",
        requests=requests,
        users_with_permission=users_with_permission
    )


@app.route("/permission-requests/<int:request_id>/approve", methods=["POST"])
@admin_required
def approve_permission_request(request_id):
    permission_request = PermissionRequest.query.get_or_404(request_id)

    permission_request.status = "approved"
    permission_request.reviewed_at = datetime.utcnow()

    user = User.query.get(permission_request.user_id)
    if user and permission_request.permission_type == "add_user":
        user.can_add_user = True

    db.session.commit()

    flash("Permission approved successfully.", "success")
    return redirect(url_for("permission_requests"))


@app.route("/permission-requests/<int:request_id>/reject", methods=["POST"])
@admin_required
def reject_permission_request(request_id):
    permission_request = PermissionRequest.query.get_or_404(request_id)

    permission_request.status = "rejected"
    permission_request.reviewed_at = datetime.utcnow()

    db.session.commit()

    flash("Permission request rejected.", "warning")
    return redirect(url_for("permission_requests"))


@app.route("/revoke-add-user-permission/<int:user_id>", methods=["POST"])
@admin_required
def revoke_add_user_permission(user_id):
    user = User.query.get_or_404(user_id)

    if user.role == "admin":
        flash("You cannot revoke add-user permission from an admin.", "danger")
        return redirect(url_for("permission_requests"))

    user.can_add_user = False
    db.session.commit()

    flash(f"Add-user permission revoked for {user.full_name}.", "warning")
    return redirect(url_for("permission_requests"))


@app.route("/export-pdf/<int:screening_id>")
def export_pdf(screening_id):
    screening = Screening.query.get_or_404(screening_id)

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    y = height - 50

    pdf.setTitle(f"TB_Screening_Result_{screening.id}")

    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(50, y, "TB CARE ASSIST")
    y -= 25

    pdf.setFont("Helvetica", 12)
    pdf.drawString(50, y, "Rule-Based Multilingual TB Screening Report")
    y -= 35

    pdf.setFont("Helvetica-Bold", 13)
    pdf.drawString(50, y, "Screening Summary")
    y -= 25

    pdf.setFont("Helvetica", 11)
    pdf.drawString(50, y, f"Screening ID: {screening.id}")
    y -= 20
    pdf.drawString(50, y, f"Date: {screening.created_at.strftime('%Y-%m-%d %H:%M')}")
    y -= 20
    pdf.drawString(50, y, f"Language: {screening.language_selected}")
    y -= 20
    pdf.drawString(50, y, f"Patient Name: {screening.patient_name}")
    y -= 20
    pdf.drawString(50, y, f"Age: {screening.age}")
    y -= 20
    pdf.drawString(50, y, f"Gender: {screening.gender}")
    y -= 30

    pdf.setFont("Helvetica-Bold", 13)
    pdf.drawString(50, y, "Symptoms")
    y -= 25

    pdf.setFont("Helvetica", 11)
    symptoms = [
        ("Cough", screening.cough),
        ("Cough more than 2 weeks", screening.cough_duration),
        ("Night sweats", screening.night_sweats),
        ("Weight loss", screening.weight_loss),
        ("Coughing blood", screening.coughing_blood),
        ("Fever", screening.fever),
        ("Fatigue", screening.fatigue),
        ("Chest pain", screening.chest_pain),
    ]

    for label, value in symptoms:
        pdf.drawString(60, y, f"{label}: {'Yes' if value else 'No'}")
        y -= 18

    y -= 10
    pdf.setFont("Helvetica-Bold", 13)
    pdf.drawString(50, y, "Assessment")
    y -= 25

    pdf.setFont("Helvetica", 11)
    pdf.drawString(60, y, f"Risk Level: {screening.risk_level}")
    y -= 20

    test_recommendation = get_test_recommendation(screening.risk_level)

    pdf.drawString(60, y, "Recommended Lab Test(s):")
    y -= 20

    text_tests = pdf.beginText(75, y)
    text_tests.setFont("Helvetica", 11)
    for line in test_recommendation.split(". "):
        cleaned = line.strip()
        if cleaned:
            if not cleaned.endswith("."):
                cleaned += "."
            text_tests.textLine(cleaned)
    pdf.drawText(text_tests)

    y = text_tests.getY() - 20

    text = pdf.beginText(60, y)
    text.setFont("Helvetica", 11)
    text.textLine("Recommendation:")
    for line in screening.recommendation.split(". "):
        cleaned = line.strip()
        if cleaned:
            if not cleaned.endswith("."):
                cleaned += "."
            text.textLine(f"  {cleaned}")
    pdf.drawText(text)

    y = text.getY() - 25

    pdf.setFont("Helvetica-Oblique", 10)
    pdf.drawString(
        50,
        y,
        "Note: This report is for preliminary screening support only and does not replace professional medical diagnosis."
    )

    pdf.showPage()
    pdf.save()

    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"tb_screening_result_{screening.id}.pdf",
        mimetype="application/pdf"
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8081, debug=True)