from flask import Flask, abort, render_template, request, redirect, jsonify, flash, send_file, url_for
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

from models import db, User, Resume

from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image,
    Table, TableStyle, ListFlowable, ListItem, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch

from dotenv import load_dotenv
from PIL import Image as PILImage
from io import BytesIO
from math import isfinite
import os
import secrets
import uuid
from xml.sax.saxutils import escape

from ai.chatbot import reply

# --------------------------------------------------
# APP SETUP
# --------------------------------------------------

load_dotenv()

app = Flask(__name__)

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "data.db")
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
REPORT_FOLDER = os.path.join(BASE_DIR, "reports")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(REPORT_FOLDER, exist_ok=True)

secret_key = os.environ.get("SECRET_KEY")
if os.environ.get("APP_ENV", "development").lower() == "production" and not secret_key:
    raise RuntimeError("SECRET_KEY must be configured when APP_ENV=production")

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["SECRET_KEY"] = secret_key or secrets.token_hex(32)
database_url = os.environ.get("DATABASE_URL") or "sqlite:///" + DB_PATH

if database_url.startswith("postgres://"):
    database_url = database_url.replace(
        "postgres://", "postgresql+psycopg://", 1
    )
elif database_url.startswith("postgresql://"):
    database_url = database_url.replace(
        "postgresql://", "postgresql+psycopg://", 1
    )

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("APP_ENV", "").lower() == "production"

db.init_app(app)

with app.app_context():
    db.create_all()

# --------------------------------------------------
# LOGIN MANAGER
# --------------------------------------------------

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# --------------------------------------------------
# AUTH
# --------------------------------------------------

@app.route("/", methods=["GET","POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect("/dashboard")
        flash("Invalid Email or Password")
    return render_template("login.html")


@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if not name or not email or not password:
            flash("Name, email, and password are required")
            return redirect("/register")
        if User.query.filter_by(email=email).first():
            flash("Email already exists")
            return redirect("/register")
        user = User(
            name=name,
            email=email,
            password=generate_password_hash(password)
        )
        db.session.add(user)
        db.session.commit()
        flash("Registration Successful!")
        return redirect("/")
    return render_template("register.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect("/")


@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html")

# --------------------------------------------------
# CAREER
# --------------------------------------------------

@app.route("/career", methods=["GET","POST"])
@login_required
def career():

    if request.method == "POST":

        stream = request.form.get("stream")
        try:
            marks = float(request.form.get("marks", ""))
        except ValueError:
            return render_template("career.html", error="Enter a valid mark between 0 and 100"), 400

        if stream not in {"science", "commerce", "arts"} or not isfinite(marks) or not 0 <= marks <= 100:
            return render_template("career.html", error="Choose a valid stream and enter marks between 0 and 100"), 400

        if stream == "science":
            if marks >= 85:
                data = {
                    "result":"Medical (MBBS)",
                    "fees":"₹1L - ₹10L",
                    "duration":"5.5 Years",
                    "subjects":["Biology"],
                    "careers":["Doctor"],
                    "higher":["MD","MS"]
                }
            elif marks >= 70:
                data = {
                    "result":"Engineering (B.Tech)",
                    "fees":"₹80k - ₹2.5L",
                    "duration":"4 Years",
                    "subjects":["Physics","Chemistry","Maths"],
                    "careers":["Software Engineer"],
                    "higher":["M.Tech","MS","PhD"]
                }
            else:
                data = {
                    "result":"B.Sc Science",
                    "fees":"₹30k - ₹80k",
                    "duration":"3 Years",
                    "subjects":["Physics","Chemistry"],
                    "careers":["Teacher"],
                    "higher":["M.Sc","B.Ed"]
                }

        elif stream == "commerce":
            if marks >= 80:
                data = {
                    "result":"Chartered Accountant",
                    "fees":"₹50k - ₹1L",
                    "duration":"4 Years",
                    "subjects":["Accounting"],
                    "careers":["CA"],
                    "higher":["CFA"]
                }
            elif marks >= 65:
                data = {
                    "result":"B.Com",
                    "fees":"₹40k - ₹1L",
                    "duration":"3 Years",
                    "subjects":["Accounts"],
                    "careers":["Accountant"],
                    "higher":["MBA"]
                }
            else:
                data = {
                    "result":"BBA",
                    "fees":"₹50k - ₹1.5L",
                    "duration":"3 Years",
                    "subjects":["Management"],
                    "careers":["HR"],
                    "higher":["MBA"]
                }

        elif stream == "arts":
            if marks >= 75:
                data = {
                    "result":"Journalism",
                    "fees":"₹60k - ₹2L",
                    "duration":"3 Years",
                    "subjects":["Media"],
                    "careers":["Journalist"],
                    "higher":["MA"]
                }
            elif marks >= 60:
                data = {
                    "result":"BA Psychology",
                    "fees":"₹40k - ₹1.2L",
                    "duration":"3 Years",
                    "subjects":["Psychology"],
                    "careers":["Counselor"],
                    "higher":["MA"]
                }
            else:
                data = {
                    "result":"BA General",
                    "fees":"₹30k - ₹80k",
                    "duration":"3 Years",
                    "subjects":["History"],
                    "careers":["Teacher"],
                    "higher":["MA"]
                }

        return render_template("career.html",
                               result=data["result"],
                               details=data)

    return render_template("career.html")


# --------------------------------------------------
# LAUNCHPAD: SKILL-TO-OPPORTUNITY STUDIO
# --------------------------------------------------

@app.route("/launchpad", methods=["GET", "POST"])
@login_required
def launchpad():
    plan = None
    if request.method == "POST":
        skills = request.form.get("skills", "").strip()[:500]
        interests = request.form.get("interests", "").strip()[:300]
        goal = request.form.get("goal", "").strip()[:300]
        if not skills or not interests or not goal:
            flash("Please complete all three fields to build your LaunchPad plan.")
        else:
            skill_list = [item.strip() for item in skills.replace("\n", ",").split(",") if item.strip()]
            focus = interests.lower()
            if any(word in focus for word in ("ai", "machine learning", "data")):
                track = "Build an intelligent solution"
                project = "Create a small, explainable AI assistant that solves one real student or community problem."
                proof = ["Define one real problem and identify who experiences it",
                         "Prepare a small, clearly documented dataset",
                         "Build a working prototype and test it with 3 sample cases",
                         "Publish a README with screenshots, limitations and next steps"]
            elif any(word in focus for word in ("web", "design", "frontend", "backend", "app")):
                track = "Build a useful digital product"
                project = "Design and build a responsive micro-tool that removes one everyday friction point."
                proof = ["Interview 2 potential users about the problem",
                         "Sketch the main user journey and 3 core screens",
                         "Build a responsive working prototype",
                         "Publish a demo, screenshots and a short case study"]
            elif any(word in focus for word in ("business", "entrepreneur", "marketing", "finance")):
                track = "Validate a practical business idea"
                project = "Create a lean launch experiment for a student-focused product or service."
                proof = ["Describe the target user and their unmet need",
                         "Compare 3 existing alternatives",
                         "Create a one-page offer and simple cost model",
                         "Collect feedback from 5 people and summarize what changed"]
            else:
                track = "Turn your interest into visible proof"
                project = "Create a compact portfolio project that demonstrates your interest through a real outcome."
                proof = ["Choose one specific problem related to your interest",
                         "Research 3 examples and note what can be improved",
                         "Create a small working or presentable solution",
                         "Document the result, your contribution and lessons learned"]
            plan = {
                "track": track, "project": project, "skills": skill_list[:12],
                "proof": proof, "goal": goal,
                "next_step": "Start with the first proof task today. Keep the scope small enough to finish."
            }
    return render_template("launchpad.html", plan=plan)


# --------------------------------------------------
# CAREER LAB: LOCAL-FIRST SMART CAREER TOOLS
# --------------------------------------------------

@app.route("/career-lab", methods=["GET", "POST"])
@login_required
def career_lab():
    result = None
    action = request.form.get("action", "ats") if request.method == "POST" else None

    if request.method == "POST":
        if action == "ats":
            resume_text = request.form.get("resume_text", "").strip()[:12000]
            target_role = request.form.get("target_role", "").strip()[:100]
            if len(resume_text) < 40:
                flash("Paste at least a few lines of your resume to analyse it.")
            else:
                role_terms = {
                    "software developer": ["python", "java", "javascript", "sql", "git", "api", "testing", "projects"],
                    "data analyst": ["excel", "sql", "python", "power bi", "tableau", "statistics", "dashboard", "projects"],
                    "web developer": ["html", "css", "javascript", "react", "api", "git", "responsive", "projects"],
                    "general internship": ["communication", "teamwork", "projects", "problem solving", "education", "skills"]
                }
                role_key = target_role.lower()
                terms = role_terms.get(role_key, role_terms["general internship"])
                text_lower = resume_text.lower()
                found = [term for term in terms if term in text_lower]
                missing = [term for term in terms if term not in text_lower]
                score = min(100, round((len(found) / len(terms)) * 75 + min(25, len(resume_text.split()) / 20)))
                suggestions = []
                if "projects" not in text_lower:
                    suggestions.append("Add 1–2 projects with your role, tools used and measurable outcome.")
                if not any(word in text_lower for word in ("built", "developed", "created", "implemented")):
                    suggestions.append("Use action verbs such as built, developed, implemented and improved.")
                if not any(word in text_lower for word in ("%", "users", "minutes", "records", "accuracy")):
                    suggestions.append("Add honest numbers or outcomes where you can support them.")
                if not any(word in text_lower for word in ("github", "linkedin", "portfolio")):
                    suggestions.append("Include a clickable GitHub, LinkedIn or portfolio link.")
                if not suggestions:
                    suggestions.append("Good structure signals found. Tailor the wording to the exact job description.")
                result = {"kind": "ats", "score": score, "found": found, "missing": missing,
                          "suggestions": suggestions, "role": target_role or "General internship",
                          "note": "This is a local keyword and structure check, not a guarantee of an employer's ATS score."}

        elif action == "interview":
            role = request.form.get("interview_role", "Software Developer").strip()[:100]
            bank = {
                "software": ["Explain a project you built and the problem it solves.", "How would you debug an API that suddenly returns a 500 error?", "What is the difference between a list and a tuple in Python?", "How do you use Git when working with a team?"],
                "data": ["How would you handle missing values in a dataset?", "Explain a project where you used data to answer a question.", "What is the difference between INNER JOIN and LEFT JOIN?", "How would you explain a chart to a non-technical stakeholder?"],
                "general": ["Tell me about yourself and the kind of role you are seeking.", "Describe a challenge you faced and how you handled it.", "What is one skill you are actively improving?", "Why should a team choose you for this opportunity?"]
            }
            key = "data" if any(x in role.lower() for x in ("data", "analyst")) else ("software" if any(x in role.lower() for x in ("software", "developer", "engineer", "web")) else "general")
            result = {"kind": "interview", "role": role, "questions": bank[key],
                      "tip": "Answer using STAR: Situation, Task, Action and Result. Keep each answer specific and honest."}

    return render_template("career_lab.html", result=result)

# --------------------------------------------------
# CHATBOT
# --------------------------------------------------

@app.route("/chatbot")
@login_required
def chatbot():
    return render_template("chatbot.html")

@app.route("/chat", methods=["POST"])
@login_required
def chat():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "A JSON object is required"}), 400

    message = payload.get("msg")
    if not isinstance(message, str) or not message.strip() or len(message) > 1000:
        return jsonify({"error": "Message must contain 1 to 1000 characters"}), 400

    return jsonify({"reply": reply(message)})
# --------------------------------------------------
# ✅ RESUME BUILDER (MODERN TWO COLUMN PDF)
# --------------------------------------------------

@app.route("/resume", methods=["GET", "POST"])
@login_required
def resume():

    if request.method == "POST":

        # ---------------- PHOTO ----------------
        photo_path = None
        photo = request.files.get("photo")

        if photo and photo.filename:
            safe_name = secure_filename(photo.filename)
            extension = os.path.splitext(safe_name)[1].lower()
            if extension not in {".jpg", ".jpeg", ".png"}:
                abort(400, description="Profile photo must be a JPEG or PNG image")

            photo_data = photo.stream.read(5 * 1024 * 1024 + 1)
            if len(photo_data) > 5 * 1024 * 1024:
                abort(413, description="Profile photo must be 5 MB or smaller")
            try:
                uploaded_image = PILImage.open(BytesIO(photo_data))
                if uploaded_image.width * uploaded_image.height > 25_000_000:
                    abort(400, description="The uploaded profile photo dimensions are too large")
                uploaded_image.verify()
            except (OSError, ValueError, PILImage.DecompressionBombError):
                abort(400, description="The uploaded profile photo is not a valid image")

            filename = f"{uuid.uuid4().hex}{extension}"
            photo_path = os.path.join(UPLOAD_FOLDER, filename)
            with open(photo_path, "wb") as uploaded_photo:
                uploaded_photo.write(photo_data)

        # ---------------- FORM DATA ----------------
        name = request.form.get("name", "")
        email = request.form.get("email", "")
        phone = request.form.get("phone", "")
        address = request.form.get("address", "")
        links = request.form.get("links", "")

        summary = request.form.get("summary", "")
        skills = request.form.get("skills", "")
        education = request.form.get("education", "")
        experience = request.form.get("experience", "")
        projects = request.form.get("projects", "")
        certifications = request.form.get("certifications", "")
        achievements = request.form.get("achievements", "")
        languages = request.form.get("languages", "")
        hobbies = request.form.get("hobbies", "")

        # ---------------- SAVE DB ----------------
        r = Resume(
            user_id=current_user.id,
            name=name,
            email=email,
            skills=skills,
            education=education,
            projects=projects
        )
        db.session.add(r)
        db.session.commit()

        # ---------------- PDF PATH ----------------
        pdf_path = os.path.join(REPORT_FOLDER, f"resume_{r.id}.pdf")

        doc = SimpleDocTemplate(
            pdf_path,
            pagesize=A4,
            rightMargin=25,
            leftMargin=25,
            topMargin=25,
            bottomMargin=25
        )

        elements = []
        styles = getSampleStyleSheet()

        # ---------------- STYLES ----------------
        resume_heading = ParagraphStyle(
            "resume_heading",
            parent=styles["Heading1"],
            alignment=1,
            fontSize=24,
            textColor=colors.HexColor("#0f766e"),
            spaceAfter=10
        )

        name_style = ParagraphStyle(
            "name",
            fontSize=20,
            textColor=colors.white,
            spaceAfter=10
        )

        contact_style = ParagraphStyle(
            "contact",
            fontSize=9,
            textColor=colors.whitesmoke,
            spaceAfter=4
        )

        left_title = ParagraphStyle(
            "left_title",
            fontSize=11,
            textColor=colors.white,
            backColor=colors.HexColor("#0f766e"),
            leftIndent=6,
            spaceBefore=12,
            spaceAfter=6
        )

        left_text = ParagraphStyle(
            "left_text",
            fontSize=9,
            textColor=colors.white,
            spaceAfter=4
        )

        right_title = ParagraphStyle(
            "right_title",
            fontSize=13,
            textColor=colors.HexColor("#0f766e"),
            spaceBefore=12,
            spaceAfter=6
        )

        body = ParagraphStyle(
            "body",
            fontSize=10.5,
            spaceAfter=6
        )

        def resume_paragraph(value, style):
            return Paragraph(escape(value).replace("\n", "<br/>"), style)

        # ---------------- TOP HEADING ----------------
        elements.append(Paragraph("RESUME", resume_heading))
        elements.append(Spacer(1, 8))
        elements.append(HRFlowable(width="100%", thickness=1,
                                   color=colors.HexColor("#0f766e")))
        elements.append(Spacer(1, 12))

        # ---------------- LEFT COLUMN ----------------
        left = []

        if photo_path:
            left.append(Image(photo_path, 1.5 * inch, 1.5 * inch))
            left.append(Spacer(1, 12))

        left.append(resume_paragraph(name.upper(), name_style))

        if email:
            left.append(resume_paragraph(email, contact_style))
        if phone:
            left.append(resume_paragraph(phone, contact_style))
        if address:
            left.append(resume_paragraph(address, contact_style))
        if links:
            left.append(resume_paragraph(links, contact_style))

        # SUMMARY
        if summary:
            left.append(Paragraph("SUMMARY", left_title))
            left.append(resume_paragraph(summary, left_text))

        # LANGUAGES
        if languages:
            left.append(Paragraph("LANGUAGES", left_title))
            for l in languages.split(","):
                if l.strip():
                    left.append(resume_paragraph("• " + l.strip(), left_text))

        # HOBBIES
        if hobbies:
            left.append(Paragraph("HOBBIES", left_title))
            for h in hobbies.split(","):
                if h.strip():
                    left.append(resume_paragraph("• " + h.strip(), left_text))

        # ---------------- RIGHT COLUMN ----------------
        right = []

        if education:
            right.append(Paragraph("EDUCATION", right_title))
            right.append(resume_paragraph(education, body))

        if skills:
            right.append(Paragraph("SKILLS", right_title))
            right.append(ListFlowable(
                [ListItem(resume_paragraph(s.strip(), body))
                 for s in skills.split(",") if s.strip()],
                bulletType="bullet"
            ))

        if experience:
            right.append(Paragraph("EXPERIENCE", right_title))
            right.append(resume_paragraph(experience, body))

        if projects:
            right.append(Paragraph("PROJECTS", right_title))
            right.append(resume_paragraph(projects, body))

        if certifications:
            right.append(Paragraph("CERTIFICATIONS", right_title))
            right.append(resume_paragraph(certifications, body))

        if achievements:
            right.append(Paragraph("ACHIEVEMENTS", right_title))
            right.append(resume_paragraph(achievements, body))

        # ---------------- TWO COLUMN TABLE ----------------
        table = Table([[left, right]], colWidths=[200, 330])

        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#0f766e")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 18),
            ("RIGHTPADDING", (0, 0), (-1, -1), 18),
            ("TOPPADDING", (0, 0), (-1, -1), 18),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 18),
        ]))

        elements.append(table)

        # ---------------- BUILD PDF ----------------
        doc.build(elements)

        # Redirect to a dedicated GET endpoint so Android WebView can hand
        # a normal attachment URL to its native DownloadManager.
        return redirect(url_for("download_resume", resume_id=r.id), code=303)

    return render_template("resume.html")


@app.route("/resume/download/<int:resume_id>", methods=["GET"])
@login_required
def download_resume(resume_id):
    resume_record = Resume.query.filter_by(
        id=resume_id,
        user_id=current_user.id
    ).first_or_404()

    pdf_path = os.path.join(REPORT_FOLDER, f"resume_{resume_record.id}.pdf")
    if not os.path.isfile(pdf_path):
        abort(404, description="Resume PDF not found. Please generate it again.")

    response = send_file(
        pdf_path,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"SmartyHub_Resume_{resume_record.id}.pdf",
        max_age=0,
        conditional=False
    )
    # Explicit download headers help Android WebView's native download manager.
    response.headers["Cache-Control"] = "private, no-store, max-age=0"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response
# --------------------------------------------------
# TIMETABLE
# --------------------------------------------------

@app.route("/timetable")
@login_required
def timetable():
    return render_template("timetable.html")

# --------------------------------------------------
# ADMIN
# --------------------------------------------------

@app.route("/admin")
@login_required
def admin():
    if current_user.role != "admin":
        return "Access Denied"
    return render_template("admin.html", users=User.query.all())

# --------------------------------------------------
# RUN
# --------------------------------------------------

if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG", "").lower() == "true")