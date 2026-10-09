import os
import json
import sqlite3
from datetime import datetime
from functools import wraps

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    jsonify,
    flash,
)

from dotenv import load_dotenv
from authlib.integrations.flask_client import OAuth
from google import genai


# =========================================================
# CONFIGURATION
# =========================================================

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "careernova.db")

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static"),
)

app.secret_key = os.getenv("FLASK_SECRET_KEY")

if not app.secret_key:
    app.secret_key = os.urandom(32).hex()
    print("WARNING: Set FLASK_SECRET_KEY in .env for stable sessions.")

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "").strip()
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "").strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

oauth = OAuth(app)

if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET:
    oauth.register(
        name="google",
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        server_metadata_url=(
            "https://accounts.google.com/.well-known/openid-configuration"
        ),
        client_kwargs={
            "scope": "openid email profile",
        },
    )


# =========================================================
# DATABASE
# =========================================================

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_columns(conn, table_name):
    rows = conn.execute(
        f"PRAGMA table_info({table_name})"
    ).fetchall()

    return {row["name"] for row in rows}


def ensure_column(conn, table_name, column_name, column_type):
    columns = get_columns(conn, table_name)

    if column_name not in columns:
        conn.execute(
            f"ALTER TABLE {table_name} "
            f"ADD COLUMN {column_name} {column_type}"
        )


def init_database():
    conn = get_db()

    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            google_id TEXT UNIQUE,
            name TEXT,
            email TEXT,
            profile_photo TEXT,
            created_at TEXT
        );

        CREATE TABLE IF NOT EXISTS profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE,
            full_name TEXT,
            date_of_birth TEXT,
            location TEXT,
            college TEXT,
            degree TEXT,
            department TEXT,
            current_year TEXT,
            cgpa TEXT,
            technical_skills TEXT,
            professional_skills TEXT,
            creative_skills TEXT,
            interests TEXT,
            career_interest TEXT,
            work_preferences TEXT,
            projects TEXT,
            experience TEXT,
            certifications TEXT,
            achievements TEXT,
            data_json TEXT DEFAULT '{}',
            updated_at TEXT
        );

        CREATE TABLE IF NOT EXISTS activity_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            activity_type TEXT,
            title TEXT,
            query TEXT,
            result_json TEXT,
            created_at TEXT
        );

        CREATE TABLE IF NOT EXISTS career_analysis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            analysis_json TEXT,
            created_at TEXT
        );

        CREATE TABLE IF NOT EXISTS interview_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            career TEXT,
            questions_json TEXT,
            answers_json TEXT,
            feedback_json TEXT,
            created_at TEXT
        );

        CREATE TABLE IF NOT EXISTS assessment_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            answers_json TEXT,
            created_at TEXT
        );

        CREATE TABLE IF NOT EXISTS saved_roadmaps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            roadmap_json TEXT,
            created_at TEXT
        );
    """)

    # Support databases created by an earlier app.py version.
    ensure_column(conn, "users", "google_id", "TEXT")
    ensure_column(conn, "users", "name", "TEXT")
    ensure_column(conn, "users", "email", "TEXT")
    ensure_column(conn, "users", "profile_photo", "TEXT")
    ensure_column(conn, "users", "created_at", "TEXT")

    ensure_column(conn, "profiles", "data_json", "TEXT DEFAULT '{}'")
    ensure_column(conn, "profiles", "updated_at", "TEXT")

    for table in (
        "activity_history",
        "career_analysis",
        "interview_sessions",
        "assessment_results",
        "saved_roadmaps",
    ):
        ensure_column(conn, table, "user_id", "INTEGER")

    conn.commit()
    conn.close()


init_database()


# =========================================================
# USER HELPERS
# =========================================================

def current_user_id():
    return session.get("user_id")


def get_or_create_demo_user():
    conn = get_db()

    row = conn.execute(
        "SELECT id FROM users WHERE email = ?",
        ("demo@careernova.local",),
    ).fetchone()

    if row:
        user_id = row["id"]
    else:
        cursor = conn.execute("""
            INSERT INTO users (
                name, email, created_at
            )
            VALUES (?, ?, ?)
        """, (
            "CareerNova Demo User",
            "demo@careernova.local",
            datetime.now().isoformat(),
        ))

        user_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return user_id


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user_id():
            return redirect(url_for("login"))

        return view(*args, **kwargs)

    return wrapped


def get_profile(user_id=None):
    user_id = user_id or current_user_id()

    if not user_id:
        return {}

    conn = get_db()

    row = conn.execute(
        "SELECT * FROM profiles WHERE user_id = ?",
        (user_id,),
    ).fetchone()

    conn.close()

    if not row:
        return {}

    profile = {}

    try:
        profile.update(json.loads(row["data_json"] or "{}"))
    except (ValueError, TypeError):
        pass

    for key in row.keys():
        if key not in ("id", "user_id", "data_json", "updated_at"):
            value = row[key]

            if value is not None and value != "":
                profile[key] = value

    return profile


def save_history(activity_type, title, result, query=""):
    user_id = current_user_id()

    if not user_id:
        return

    conn = get_db()

    conn.execute("""
        INSERT INTO activity_history (
            user_id, activity_type, title,
            query, result_json, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        activity_type,
        title,
        query,
        json.dumps(result, ensure_ascii=False),
        datetime.now().isoformat(),
    ))

    conn.commit()
    conn.close()


def get_latest_analysis():
    user_id = current_user_id()

    if not user_id:
        return {}

    conn = get_db()

    row = conn.execute("""
        SELECT analysis_json
        FROM career_analysis
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT 1
    """, (user_id,)).fetchone()

    conn.close()

    if not row:
        return {}

    try:
        return json.loads(row["analysis_json"])
    except (ValueError, TypeError):
        return {}


# =========================================================
# GEMINI AI HELPERS
# =========================================================

def gemini_json(prompt):
    """
    Calls Gemini from the server.
    The API key is never sent to the browser.
    """

    if not GEMINI_API_KEY:
        return None

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt + """

Return only valid JSON.
Do not use Markdown code fences.
Do not add explanations outside the JSON object.
""",
        )

        text = (response.text or "").strip()

        if text.startswith("```"):
            lines = text.splitlines()

            if lines and lines[0].startswith("```"):
                lines = lines[1:]

            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]

            text = "\n".join(lines)

        return json.loads(text)

    except Exception as exc:
        app.logger.error("Gemini request failed: %s", exc)
        return None


def build_fallback_analysis(profile):
    """
    A transparent fallback for development.
    This is not a real AI assessment.
    """

    interest_text = " ".join([
        str(profile.get("interests", "")),
        str(profile.get("career_interest", "")),
        str(profile.get("career_areas", "")),
        str(profile.get("department", "")),
    ]).lower()

    careers = [
        {
            "title": "Software Developer",
            "fit_percentage": 70,
            "reason": "Explore programming, application development and problem solving.",
            "skills": ["Programming", "Problem solving", "Version control"],
            "pathway": "Build programming fundamentals and small projects.",
        },
        {
            "title": "Data Analyst",
            "fit_percentage": 68,
            "reason": "Explore working with data, spreadsheets and analytical questions.",
            "skills": ["Excel", "SQL", "Data interpretation"],
            "pathway": "Practise data analysis with beginner-friendly datasets.",
        },
        {
            "title": "Digital Marketing Specialist",
            "fit_percentage": 65,
            "reason": "Explore communication, content, research and digital platforms.",
            "skills": ["Communication", "Content planning", "Analytics"],
            "pathway": "Create a small content campaign and review its performance.",
        },
        {
            "title": "Business Analyst",
            "fit_percentage": 64,
            "reason": "Explore business problems, research and structured communication.",
            "skills": ["Research", "Documentation", "Analytical thinking"],
            "pathway": "Practise writing problem statements and process documents.",
        },
        {
            "title": "Graphic Designer",
            "fit_percentage": 62,
            "reason": "Explore visual communication and creative problem solving.",
            "skills": ["Visual design", "Typography", "Design tools"],
            "pathway": "Create a small portfolio of original designs.",
        },
        {
            "title": "Banking and Finance Associate",
            "fit_percentage": 60,
            "reason": "Explore financial services, accuracy and numerical reasoning.",
            "skills": ["Numerical reasoning", "Excel", "Financial literacy"],
            "pathway": "Study financial basics and practise relevant aptitude questions.",
        },
        {
            "title": "Government Exam Candidate",
            "fit_percentage": 60,
            "reason": "Explore public-sector opportunities and their eligibility requirements.",
            "skills": ["General knowledge", "Reasoning", "Language skills"],
            "pathway": "Identify a suitable examination and check its official eligibility criteria.",
        },
        {
            "title": "Teacher or Education Professional",
            "fit_percentage": 58,
            "reason": "Explore teaching, learning support and educational communication.",
            "skills": ["Communication", "Subject knowledge", "Planning"],
            "pathway": "Research the qualifications required for your chosen teaching role.",
        },
        {
            "title": "Legal Research Assistant",
            "fit_percentage": 58,
            "reason": "Explore legal research, reading and structured writing.",
            "skills": ["Research", "Writing", "Critical thinking"],
            "pathway": "Learn about legal careers and their education requirements.",
        },
        {
            "title": "Human Resources Associate",
            "fit_percentage": 57,
            "reason": "Explore people-focused work, communication and administration.",
            "skills": ["Communication", "Organisation", "Documentation"],
            "pathway": "Learn basic HR processes and workplace communication.",
        },
    ]

    if "design" in interest_text or "creative" in interest_text:
        careers.sort(
            key=lambda item: item["title"] != "Graphic Designer"
        )

    elif "law" in interest_text or "legal" in interest_text:
        careers.sort(
            key=lambda item: item["title"] != "Legal Research Assistant"
        )

    elif "bank" in interest_text or "finance" in interest_text:
        careers.sort(
            key=lambda item: item["title"] != "Banking and Finance Associate"
        )

    elif "government" in interest_text:
        careers.sort(
            key=lambda item: item["title"] != "Government Exam Candidate"
        )

    return {
        "profile_summary": (
            "This is a preliminary development-mode career overview. "
            "Add a Gemini API key and complete the assessment for "
            "personalised AI analysis."
        ),
        "readiness_score": 0,
        "readiness_dimensions": {
            "education": 0,
            "skills": 0,
            "projects": 0,
            "assessment": 0,
            "interview": 0,
            "roadmap": 0,
        },
        "strengths": [
            "Your profile has been collected.",
            "You can explore multiple career pathways.",
        ],
        "skill_gaps": [
            {
                "skill": "Career-specific practical experience",
                "priority": "High",
                "reason": "Practical work helps you demonstrate your abilities.",
                "action": "Complete a small project related to a career you want to explore.",
            }
        ],
        "careers": careers,
        "next_step": "Complete your assessment and add your current skills and projects.",
        "is_fallback": True,
    }


def analyse_profile(profile, assessment_answers):
    prompt = f"""
You are CareerNova AI, a career guidance assistant.

Analyse the following student's information:
{json.dumps(profile, ensure_ascii=False)}

Assessment answers:
{json.dumps(assessment_answers, ensure_ascii=False)}

Consider careers across all relevant fields, including:
technology, finance, banking, law, government, education,
design, creative work, marketing, media, HR, administration,
business, science, research, healthcare-related careers,
hospitality, travel, journalism, entrepreneurship,
agriculture, environmental work and emerging careers.

Do not recommend only technology careers.
Do not invent qualifications, exam eligibility or employment guarantees.
Mention when a qualification or licensing requirement needs verification.
Treat fit percentages as estimates, not probabilities of employment.
Do not assume the student already knows a skill unless their profile says so.
Give practical beginner-friendly next steps.

Return a JSON object with:
{{
  "profile_summary": "short personalised summary",
  "readiness_score": 0,
  "readiness_dimensions": {{
    "education": 0,
    "skills": 0,
    "projects": 0,
    "assessment": 0,
    "interview": 0,
    "roadmap": 0
  }},
  "strengths": ["..."],
  "skill_gaps": [
    {{
      "skill": "...",
      "priority": "High",
      "reason": "...",
      "action": "..."
    }}
  ],
  "careers": [
    {{
      "title": "...",
      "fit_percentage": 70,
      "reason": "...",
      "skills": ["..."],
      "pathway": "..."
    }}
  ],
  "next_step": "..."
}}

Return 5 to 8 career options.
Scores must be integers from 0 to 100.
"""

    result = gemini_json(prompt)

    if not isinstance(result, dict) or not isinstance(
        result.get("careers"), list
    ):
        result = build_fallback_analysis(profile)

    result.setdefault("is_fallback", False)

    result["careers"] = result.get("careers", [])[:8]

    return result


# =========================================================
# BASIC PAGES
# =========================================================

@app.route("/")
def welcome():
    if current_user_id():
        return redirect(url_for("dashboard"))

    return render_template("welcome.html")


@app.route("/login")
def login():
    return render_template("login.html")


@app.route("/google-login")
def google_login():
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        flash(
            "Google Login is not configured yet. Use Demo Login while developing.",
            "warning",
        )
        return redirect(url_for("login"))

    redirect_uri = url_for(
        "google_callback",
        _external=True,
    )

    return oauth.google.authorize_redirect(redirect_uri)


@app.route("/google-callback")
def google_callback():
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        return redirect(url_for("login"))

    try:
        token = oauth.google.authorize_access_token()

        user_info = token.get("userinfo")

        if not user_info:
            user_info = oauth.google.userinfo()

        google_id = user_info.get("sub")
        email = user_info.get("email")
        name = user_info.get("name", "CareerNova User")
        picture = user_info.get("picture", "")

        if not google_id or not email:
            flash("Google account details could not be retrieved.", "error")
            return redirect(url_for("login"))

        conn = get_db()

        user = conn.execute(
            "SELECT id FROM users WHERE google_id = ?",
            (google_id,),
        ).fetchone()

        if user:
            user_id = user["id"]

            conn.execute("""
                UPDATE users
                SET name = ?, email = ?, profile_photo = ?
                WHERE id = ?
            """, (name, email, picture, user_id))

        else:
            cursor = conn.execute("""
                INSERT INTO users (
                    google_id, name, email,
                    profile_photo, created_at
                )
                VALUES (?, ?, ?, ?, ?)
            """, (
                google_id,
                name,
                email,
                picture,
                datetime.now().isoformat(),
            ))

            user_id = cursor.lastrowid

        conn.commit()
        conn.close()

        session.clear()
        session["user_id"] = user_id
        session["user_name"] = name
        session["user_email"] = email
        session["profile_photo"] = picture

        return redirect(url_for("dashboard"))

    except Exception:
        app.logger.exception("Google OAuth failed")
        flash("Google Login failed. Please check OAuth configuration.", "error")
        return redirect(url_for("login"))


@app.route("/demo-login")
def demo_login():
    user_id = get_or_create_demo_user()

    session.clear()
    session["user_id"] = user_id
    session["user_name"] = "CareerNova Demo User"
    session["user_email"] = "demo@careernova.local"

    return redirect(url_for("dashboard"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("welcome"))


# =========================================================
# PROFILE PAGES
# =========================================================

@app.route("/personal")
@login_required
def personal():
    return render_template("personal.html")


@app.route("/education")
@login_required
def education():
    return render_template("education.html")


@app.route("/skills")
@login_required
def skills():
    return render_template("skills.html")


@app.route("/interests")
@login_required
def interests():
    return render_template("interests.html")


@app.route("/projects")
@login_required
def projects():
    return render_template("projects.html")


@app.route("/assessment")
@login_required
def assessment():
    return render_template("assessment.html")


# =========================================================
# PROFILE API
# =========================================================

@app.route("/api/profile", methods=["GET"])
def profile_api():
    if not current_user_id():
        return jsonify({"error": "Please log in first."}), 401

    return jsonify(get_profile())


@app.route("/api/profile/save", methods=["POST"])
def save_profile():
    user_id = current_user_id()

    if not user_id:
        user_id = get_or_create_demo_user()
        session["user_id"] = user_id
        session["user_name"] = "CareerNova Demo User"

    data = request.get_json(silent=True) or {}

    if not isinstance(data, dict):
        return jsonify({"error": "Invalid profile data."}), 400

    conn = get_db()

    existing = conn.execute(
        "SELECT * FROM profiles WHERE user_id = ?",
        (user_id,),
    ).fetchone()

    merged = {}

    if existing:
        try:
            merged.update(json.loads(existing["data_json"] or "{}"))
        except (ValueError, TypeError):
            pass

        for key in existing.keys():
            if key not in ("id", "user_id", "data_json", "updated_at"):
                if existing[key] is not None:
                    merged[key] = existing[key]

    # Merge partial form updates instead of clearing earlier fields.
    merged.update(data)

    now = datetime.now().isoformat()

    columns = get_columns(conn, "profiles")

    values = {
        key: value
        for key, value in merged.items()
        if key in columns
        and key not in ("id", "user_id", "data_json", "updated_at")
        and isinstance(value, (str, int, float))
    }

    values["data_json"] = json.dumps(
        merged,
        ensure_ascii=False,
    )

    values["updated_at"] = now

    if existing:
        assignments = ", ".join(
            f'"{key}" = ?' for key in values
        )

        conn.execute(
            f"UPDATE profiles SET {assignments} WHERE user_id = ?",
            list(values.values()) + [user_id],
        )

    else:
        values["user_id"] = user_id

        names = ", ".join(f'"{key}"' for key in values)
        placeholders = ", ".join("?" for _ in values)

        conn.execute(
            f"INSERT INTO profiles ({names}) VALUES ({placeholders})",
            list(values.values()),
        )

    conn.commit()
    conn.close()

    save_history(
        "profile",
        "Profile updated",
        {"fields_updated": list(data.keys())},
    )

    return jsonify({
        "success": True,
        "message": "Profile saved successfully.",
    })


# =========================================================
# CAREER ANALYSIS
# =========================================================

@app.route("/analysis")
@login_required
def analysis():
    return render_template("analysis.html")


@app.route("/api/assessment/save", methods=["POST"])
def save_assessment():
    user_id = current_user_id()

    if not user_id:
        return jsonify({"error": "Please log in first."}), 401

    data = request.get_json(silent=True) or {}
    answers = data.get("answers", data)

    if not isinstance(answers, (dict, list)):
        return jsonify({"error": "Invalid assessment answers."}), 400

    conn = get_db()

    conn.execute("""
        INSERT INTO assessment_results (
            user_id, answers_json, created_at
        )
        VALUES (?, ?, ?)
    """, (
        user_id,
        json.dumps(answers, ensure_ascii=False),
        datetime.now().isoformat(),
    ))

    conn.commit()
    conn.close()

    session["assessment_answers"] = answers

    save_history(
        "assessment",
        "Career strength assessment completed",
        {"answers": answers},
    )

    return jsonify({"success": True})


@app.route("/api/analyze-career", methods=["POST"])
@login_required
def analyze_career():
    data = request.get_json(silent=True) or {}

    answers = data.get(
        "answers",
        session.get("assessment_answers", {}),
    )

    profile = get_profile()

    analysis_result = analyse_profile(profile, answers)

    conn = get_db()

    conn.execute("""
        INSERT INTO career_analysis (
            user_id, analysis_json, created_at
        )
        VALUES (?, ?, ?)
    """, (
        current_user_id(),
        json.dumps(analysis_result, ensure_ascii=False),
        datetime.now().isoformat(),
    ))

    conn.commit()
    conn.close()

    session["latest_analysis"] = analysis_result

    save_history(
        "career_analysis",
        "Career analysis completed",
        analysis_result,
    )

    return jsonify(analysis_result)


# =========================================================
# CAREER MATCHES
# =========================================================

@app.route("/matches")
@login_required
def matches():
    return render_template("matches.html")


# =========================================================
# SKILL GAP
# =========================================================

@app.route("/skill-gap")
@login_required
def skill_gap():
    return render_template("skill_gap.html")


@app.route("/api/skill-gap", methods=["GET", "POST"])
@login_required
def skill_gap_api():
    profile = get_profile()
    analysis_result = get_latest_analysis()

    data = request.get_json(silent=True) or {}

    selected_career = (
        data.get("career")
        or request.args.get("career")
        or session.get("selected_career")
        or ""
    )

    if not selected_career:
        careers = analysis_result.get("careers", [])

        if careers:
            selected_career = careers[0].get("title", "")

    prompt = f"""
Create a practical career-specific skill gap analysis.

Profile:
{json.dumps(profile, ensure_ascii=False)}

Career analysis:
{json.dumps(analysis_result, ensure_ascii=False)}

Selected career:
{selected_career}

Return JSON with:
{{
 "career": "...",
 "readiness_percentage": 0,
 "readiness": "...",
 "strengths": ["..."],
 "gaps": [
   {{
     "skill": "...",
     "priority": "High",
     "current_level": "...",
     "target_level": "...",
     "reason": "...",
     "action": "..."
   }}
 ],
 "top_priority": "...",
 "top_priority_reason": "..."
}}

Use 0-100 for the readiness estimate.
Be honest about missing information.
"""

    result = gemini_json(prompt)

    if not isinstance(result, dict):
        result = {
            "career": selected_career or "Career exploration",
            "readiness_percentage": 0,
            "readiness": "Preliminary estimate unavailable",
            "strengths": [],
            "gaps": [
                {
                    "skill": "Career-specific practical experience",
                    "priority": "High",
                    "current_level": "Not assessed",
                    "target_level": "Beginner project completed",
                    "reason": "Practical experience has not been fully assessed.",
                    "action": "Build a small project or portfolio item.",
                }
            ],
            "top_priority": "Build practical experience",
            "top_priority_reason": "A project can help demonstrate your skills.",
            "is_fallback": True,
        }

    save_history(
        "skill_gap",
        "Skill gap analysis",
        result,
        selected_career,
    )

    return jsonify(result)


# =========================================================
# ROADMAP
# =========================================================

@app.route("/roadmap")
@login_required
def roadmap():
    return render_template("roadmap.html")


@app.route("/api/roadmap", methods=["GET", "POST"])
@login_required
def roadmap_api():
    profile = get_profile()
    analysis_result = get_latest_analysis()

    data = request.get_json(silent=True) or {}

    career = (
        data.get("career")
        or request.args.get("career")
        or session.get("selected_career")
        or ""
    )

    duration = data.get("duration", 30)

    try:
        duration = int(duration)
    except (TypeError, ValueError):
        duration = 30

    if duration not in (30, 60, 90):
        duration = 30

    prompt = f"""
Create a realistic, beginner-friendly career roadmap.

Profile:
{json.dumps(profile, ensure_ascii=False)}

Analysis:
{json.dumps(analysis_result, ensure_ascii=False)}

Selected career: {career}
Duration: {duration} days

Do not repeat skills the profile clearly demonstrates.
Do not promise employment.
Prioritise affordable, practical learning activities.

Return JSON:
{{
 "career": "...",
 "duration": {duration},
 "focus": "...",
 "readiness": "...",
 "principle": "...",
 "phases": [
   {{
     "title": "...",
     "days": "...",
     "goal": "...",
     "tasks": ["...", "..."],
     "deliverable": "..."
   }}
 ]
}}
"""

    result = gemini_json(prompt)

    if not isinstance(result, dict):
        result = {
            "career": career or "Career exploration",
            "duration": duration,
            "focus": "Build career fundamentals",
            "readiness": "Not fully assessed",
            "principle": "Learn, practise, create, review.",
            "phases": [
                {
                    "title": "Learn the basics",
                    "days": f"Days 1-{max(1, duration // 3)}",
                    "goal": "Understand the foundations.",
                    "tasks": [
                        "Identify the essential skills for this career.",
                        "Choose a beginner-friendly learning resource.",
                    ],
                    "deliverable": "A list of skills and learning goals.",
                },
                {
                    "title": "Practise",
                    "days": f"Days {duration // 3 + 1}-{2 * duration // 3}",
                    "goal": "Apply what you learn.",
                    "tasks": [
                        "Practise relevant tasks regularly.",
                        "Record your progress and questions.",
                    ],
                    "deliverable": "Practice work and progress notes.",
                },
                {
                    "title": "Create and review",
                    "days": f"Days {2 * duration // 3 + 1}-{duration}",
                    "goal": "Demonstrate your learning.",
                    "tasks": [
                        "Create one beginner-level project or work sample.",
                        "Review your progress and identify the next skill.",
                    ],
                    "deliverable": "A project or portfolio sample.",
                },
            ],
            "is_fallback": True,
        }

    conn = get_db()

    conn.execute("""
        INSERT INTO saved_roadmaps (
            user_id, roadmap_json, created_at
        )
        VALUES (?, ?, ?)
    """, (
        current_user_id(),
        json.dumps(result, ensure_ascii=False),
        datetime.now().isoformat(),
    ))

    conn.commit()
    conn.close()

    save_history(
        "roadmap",
        f"{duration}-day career roadmap",
        result,
        career,
    )

    return jsonify(result)


# =========================================================
# MOCK INTERVIEW
# =========================================================

@app.route("/interview")
@login_required
def interview():
    return render_template("interview.html")


@app.route("/api/interview/question", methods=["GET", "POST"])
@login_required
def interview_question():
    data = request.get_json(silent=True) or {}

    career = (
        data.get("career")
        or session.get("selected_career")
        or "career exploration"
    )

    try:
        question_index = int(data.get("question_index", 0))
    except (ValueError, TypeError):
        question_index = 0

    prompt = f"""
Generate one interview question for a beginner exploring:
{career}

Question number: {question_index + 1}

Adapt to the student's profile:
{json.dumps(get_profile(), ensure_ascii=False)}

Use a suitable mix of career knowledge, problem solving,
communication, and practical situations.
Avoid asking for sensitive personal information.
Do not evaluate appearance, face, accent or video.
Return JSON:
{{
 "question": "...",
 "category": "...",
 "purpose": "..."
}}
"""

    result = gemini_json(prompt)

    if not isinstance(result, dict) or not result.get("question"):
        fallback_questions = [
            "Tell us about your interest in this career and why you want to explore it.",
            "What skills do you think are important in this field?",
            "Describe a problem you worked on and how you approached it.",
            "How would you learn a skill that is new to you?",
            "What would you do if you were given a task you did not understand?",
        ]

        result = {
            "question": fallback_questions[
                question_index % len(fallback_questions)
            ],
            "category": "General",
            "purpose": "Explore your reasoning and communication.",
            "is_fallback": True,
        }

    session["selected_career"] = career

    return jsonify(result)


@app.route("/api/interview/evaluate", methods=["POST"])
@login_required
def evaluate_interview():
    data = request.get_json(silent=True) or {}

    career = (
        data.get("career")
        or session.get("selected_career")
        or "career exploration"
    )

    question = str(data.get("question", "")).strip()
    answer = str(data.get("answer", "")).strip()

    if not answer:
        return jsonify({"error": "Please enter an answer first."}), 400

    prompt = f"""
Evaluate this mock interview answer fairly and constructively.

Career: {career}
Question: {question}
Answer: {answer}

Evaluate text content only:
- relevance
- clarity of reasoning
- communication
- career knowledge, where applicable

Do not evaluate face, appearance, accent, age, gender or background.
Do not assume that a short answer means low ability.
Give specific and actionable feedback.
This is practice feedback, not a hiring decision.

Return JSON:
{{
 "overall_score": 0,
 "communication_score": 0,
 "relevance_score": 0,
 "problem_solving_score": 0,
 "career_knowledge_score": 0,
 "strengths": ["..."],
 "improvements": ["..."],
 "feedback": "...",
 "sample_improved_answer": "..."
}}

Scores must be integers from 0 to 100.
"""

    result = gemini_json(prompt)

    if not isinstance(result, dict):
        result = {
            "overall_score": 0,
            "communication_score": 0,
            "relevance_score": 0,
            "problem_solving_score": 0,
            "career_knowledge_score": 0,
            "strengths": [],
            "improvements": [
                "Try giving a specific example.",
                "Explain your reasoning step by step.",
            ],
            "feedback": (
                "AI feedback is unavailable right now. "
                "Check the Gemini configuration and try again."
            ),
            "sample_improved_answer": "",
            "is_fallback": True,
        }

    save_history(
        "interview_answer",
        "Mock interview answer evaluated",
        result,
        career,
    )

    return jsonify(result)


# =========================================================
# FEEDBACK AND REPORT
# =========================================================

@app.route("/feedback")
@login_required
def feedback():
    return render_template("feedback.html")


@app.route("/report")
@login_required
def report():
    return render_template("report.html")


@app.route("/api/report", methods=["GET"])
@login_required
def report_api():
    analysis_result = get_latest_analysis()

    conn = get_db()

    interview_row = conn.execute("""
        SELECT feedback_json
        FROM interview_sessions
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT 1
    """, (current_user_id(),)).fetchone()

    conn.close()

    interview_feedback = {}

    if interview_row and interview_row["feedback_json"]:
        try:
            interview_feedback = json.loads(
                interview_row["feedback_json"]
            )
        except (ValueError, TypeError):
            pass

    return jsonify({
        "profile": get_profile(),
        "analysis": analysis_result,
        "interview_feedback": interview_feedback,
    })


# =========================================================
# DASHBOARD AND HISTORY
# =========================================================

@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html")


@app.route("/api/history", methods=["GET"])
@login_required
def history_api():
    conn = get_db()

    rows = conn.execute("""
        SELECT id, activity_type, title, query,
               result_json, created_at
        FROM activity_history
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT 50
    """, (current_user_id(),)).fetchall()

    conn.close()

    history = []

    for row in rows:
        try:
            result = json.loads(row["result_json"] or "{}")
        except (ValueError, TypeError):
            result = {}

        history.append({
            "id": row["id"],
            "activity_type": row["activity_type"],
            "title": row["title"],
            "query": row["query"],
            "result": result,
            "created_at": row["created_at"],
        })

    return jsonify({"history": history})


@app.route("/api/health")
def health():
    return jsonify({
        "status": "ok",
        "app": "CareerNova AI",
        "gemini_configured": bool(GEMINI_API_KEY),
        "google_login_configured": bool(
            GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET
        ),
    })


# =========================================================
# ERROR HANDLERS
# =========================================================

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "error": "Page not found.",
        "message": "Check the URL and try again.",
    }), 404


@app.errorhandler(500)
def server_error(error):
    app.logger.exception("Internal server error")

    return jsonify({
        "error": "An internal server error occurred.",
        "message": "Check the terminal for the technical details.",
    }), 500


# =========================================================
# RUN APP
# =========================================================

if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True,
    )