from flask import Flask, request, jsonify, render_template, redirect, url_for, flash
import sqlite3, datetime, os
from openai import OpenAI
from dotenv import load_dotenv

# ----------------- LOAD ENV -----------------
load_dotenv()  # loads .env file into environment

# ----------------- APP SETUP -----------------
app = Flask(__name__)
app.secret_key = "lifeline-secret"

# OpenAI setup using API key from .env
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Database file
DB_FILE = "lifeline.db"


# ----------------- DATABASE -----------------
def init_db():
    """Initialize database with required tables."""
    with sqlite3.connect(DB_FILE) as conn:
        cur = conn.cursor()
        # Alerts table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT,
            lat REAL,
            lng REAL,
            triage_level TEXT,
            notes TEXT
        )
        """)
        # Profile table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS profile (
            id INTEGER PRIMARY KEY,
            full_name TEXT,
            age INTEGER,
            blood_group TEXT,
            language TEXT,
            allergies TEXT,
            conditions TEXT,
            emergency_contact_name TEXT,
            emergency_contact_phone TEXT
        )
        """)
        conn.commit()

init_db()


# ----------------- AI TRIAGE -----------------
def ai_triage(symptoms: str) -> str:
    """
    Try AI triage first (OpenAI).
    If it fails, fallback to rule-based logic.
    """
    prompt = f"""
    You are an AI triage assistant. Classify the following patient symptoms:
    - Critical: life-threatening, needs immediate care.
    - Urgent: serious but not immediately life-threatening.
    - Non-Urgent: mild condition, can wait.

    Symptoms: {symptoms}

    Answer with only one word: Critical, Urgent, or Non-Urgent.
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=10
        )
        return response.choices[0].message.content.strip()
    except Exception:
        # ---- fallback logic ----
        text = symptoms.lower()
        if "bleeding" in text or "unconscious" in text or "heart" in text:
            return "Critical (fallback)"
        elif "pain" in text or "fever" in text:
            return "Urgent (fallback)"
        return "Non-Urgent (fallback)"


# ----------------- ROUTES -----------------
@app.route("/")
def home():
    """Home page"""
    return render_template("home.html")


@app.route("/api/ambulances")
def api_ambulances():
    """Dummy ambulance data (replace with Nokia API later)."""
    dummy_ambulances = [
        {"id": 1, "name": "Ambulance A", "lat": 28.6139, "lng": 77.2090, "status": "available"},
        {"id": 2, "name": "Ambulance B", "lat": 28.6200, "lng": 77.2150, "status": "busy"},
        {"id": 3, "name": "Ambulance C", "lat": 28.6250, "lng": 77.2000, "status": "available"},
    ]
    return jsonify(dummy_ambulances)


@app.route("/sos", methods=["GET", "POST"])
def sos():
    """SOS button to raise an emergency alert."""
    status = "Idle"
    if request.method == "POST":
        notes = request.form.get("notes", "")
        lat, lng = 28.61, 77.20  # stubbed location
        triage = "Critical"      # stubbed triage

        with sqlite3.connect(DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO alerts (created_at, lat, lng, triage_level, notes)
                VALUES (?, ?, ?, ?, ?)
            """, (datetime.datetime.now().isoformat(), lat, lng, triage, notes))
            conn.commit()

        status = "🚑 SOS sent! Nearest ambulance being dispatched."
        flash(status)
        return redirect(url_for("sos"))

    # auto-refresh every 10 sec
    return render_template("sos.html", status=status, refresh=True)


@app.route("/triage", methods=["GET", "POST"])
def triage():
    """AI symptom triage page."""
    triage_result, symptoms_text, notes = None, "", ""
    if request.method == "POST":
        symptoms_text = request.form.get("symptoms", "")
        notes = request.form.get("notes", "")
        if symptoms_text:
            triage_result = ai_triage(symptoms_text)

    return render_template("triage.html",
                           triage=triage_result,
                           symptoms=symptoms_text,
                           notes=notes)


@app.route("/profile", methods=["GET", "POST"])
def profile():
    profile_data = {}
    if request.method == "POST":
        with sqlite3.connect(DB_FILE) as conn:
            cur = conn.cursor()
            # overwrite existing profile
            cur.execute("DELETE FROM profile")
            cur.execute("""
                INSERT INTO profile (
                    id, full_name, age, blood_group, language, allergies, conditions,
                    emergency_contact_name, emergency_contact_phone
                ) VALUES (1,?,?,?,?,?,?,?,?)
            """, (
                request.form.get("full_name"),
                request.form.get("age"),
                request.form.get("blood_group"),
                request.form.get("language"),
                request.form.get("allergies"),
                request.form.get("conditions"),
                request.form.get("emergency_contact_name"),
                request.form.get("emergency_contact_phone")
            ))
            conn.commit()
        flash("Profile saved.")
        return redirect(url_for("profile"))

    # fetch saved profile safely with dict mapping
    with sqlite3.connect(DB_FILE) as conn:
        conn.row_factory = sqlite3.Row  # allows column-name access
        cur = conn.cursor()
        cur.execute("SELECT * FROM profile WHERE id=1")
        row = cur.fetchone()
        if row:
            profile_data = dict(row)

    return render_template("profile.html", p=profile_data)



@app.route("/contacts")
def contacts():
    profile_data = {}
    with sqlite3.connect(DB_FILE) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM profile WHERE id=1")
        row = cur.fetchone()
        if row:
            profile_data = dict(row)
    return render_template("contacts.html", p=profile_data)


@app.route("/first_aid")
def first_aid():
    """Offline first-aid tips page."""
    return render_template("first_aid.html")


@app.route("/dashboard")
def dashboard():
    """Admin dashboard showing alerts + ambulance status."""
    with sqlite3.connect(DB_FILE) as conn:
        cur = conn.cursor()
        alerts = cur.execute("""
            SELECT id, created_at, lat, lng, triage_level, notes
            FROM alerts ORDER BY id DESC
        """).fetchall()

    ambulances = [
        {"id": 1, "name": "Ambulance A", "lat": 28.6139, "lng": 77.2090, "status": "available"},
        {"id": 2, "name": "Ambulance B", "lat": 28.6200, "lng": 77.2150, "status": "busy"},
        {"id": 3, "name": "Ambulance C", "lat": 28.6250, "lng": 77.2000, "status": "available"},
    ]

    # auto-refresh every 15 sec
    return render_template("dashboard.html", alerts=alerts, ambulances=ambulances, refresh=True)


# ----------------- MAIN -----------------
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
