from flask import Flask, request, jsonify, render_template, redirect, url_for, flash
import sqlite3, datetime, os

app = Flask(__name__)
app.secret_key = "lifeline-secret"

# ----------------- DATABASE SETUP -----------------
DB_FILE = "lifeline.db"

def init_db():
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
        )""")
        # Profile table (only 1 profile stored)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS profile (
            id INTEGER PRIMARY KEY,
            full_name TEXT, age INTEGER, blood_group TEXT,
            language TEXT, allergies TEXT, conditions TEXT,
            emergency_contact_name TEXT, emergency_contact_phone TEXT
        )""")
        conn.commit()

init_db()

# ----------------- ROUTES -----------------

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/api/ambulances")
def api_ambulances():
    dummy_ambulances = [
        {"id":1,"name":"Ambulance A","lat":28.6139,"lng":77.2090,"status":"available"},
        {"id":2,"name":"Ambulance B","lat":28.6200,"lng":77.2150,"status":"busy"},
        {"id":3,"name":"Ambulance C","lat":28.6250,"lng":77.2000,"status":"available"},
    ]
    return jsonify(dummy_ambulances)

@app.route("/sos", methods=["GET","POST"])
def sos():
    status = "Idle"
    if request.method == "POST":
        notes = request.form.get("notes","")
        lat, lng = 28.61, 77.20  # stubbed user location
        triage = "Critical"      # stubbed triage result
        with sqlite3.connect(DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute("INSERT INTO alerts (created_at,lat,lng,triage_level,notes) VALUES (?,?,?,?,?)",
                        (datetime.datetime.now().isoformat(), lat, lng, triage, notes))
            conn.commit()
        status = "🚑 SOS sent! Nearest ambulance being dispatched."
        flash(status)
        return redirect(url_for("sos"))
    return render_template("sos.html", status=status)

@app.route("/triage", methods=["GET","POST"])
def triage():
    triage = None
    if request.method == "POST":
        symptoms = request.form.get("symptoms","").lower()
        if "bleeding" in symptoms or "unconscious" in symptoms:
            triage = "Critical"
        elif "pain" in symptoms:
            triage = "Urgent"
        else:
            triage = "Non-Urgent"
    return render_template("triage.html", triage=triage)

@app.route("/profile", methods=["GET","POST"])
def profile():
    profile_data = {}
    if request.method == "POST":
        with sqlite3.connect(DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM profile")
            cur.execute("INSERT INTO profile (id,full_name,age,blood_group,language,allergies,conditions,emergency_contact_name,emergency_contact_phone) VALUES (1,?,?,?,?,?,?,?,?)",
                        (request.form.get("full_name"), request.form.get("age"),
                         request.form.get("blood_group"), request.form.get("language"),
                         request.form.get("allergies"), request.form.get("conditions"),
                         request.form.get("emergency_contact_name"), request.form.get("emergency_contact_phone")))
            conn.commit()
        flash("Profile saved.")
        return redirect(url_for("profile"))
    with sqlite3.connect(DB_FILE) as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM profile WHERE id=1")
        row = cur.fetchone()
        if row:
            keys = ["id","full_name","age","blood_group","language","allergies","conditions","emergency_contact_name","emergency_contact_phone"]
            profile_data = dict(zip(keys,row))
    return render_template("profile.html", p=profile_data)

@app.route("/contacts")
def contacts():
    return render_template("contacts.html")

@app.route("/first_aid")
def first_aid():
    return render_template("first_aid.html")

@app.route("/dashboard")
def dashboard():
    with sqlite3.connect(DB_FILE) as conn:
        cur = conn.cursor()
        alerts = cur.execute("SELECT id,created_at,lat,lng,triage_level,notes FROM alerts ORDER BY id DESC").fetchall()
    return render_template("dashboard.html", alerts=alerts)

# ----------------- MAIN -----------------
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
