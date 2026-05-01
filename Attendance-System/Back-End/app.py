"""
Attendance Management System — Flask Backend
Stack: Python 3.10+, Flask, Flask-CORS, PyMySQL, bcrypt, PyJWT
Run:   pip install flask flask-cors pymysql bcrypt pyjwt
       python app.py
"""

import os
import random
import string
from datetime import datetime, timedelta, timezone, time
from urllib.parse import urlparse, unquote_plus

import bcrypt
import jwt
import pymysql
import pymysql.cursors
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
# Allow any origin in development to avoid fetch failures from local files or different localhost ports.
CORS(
    app,
    resources={r"/api/*": {"origins": "*"}},
    allow_headers=["Content-Type", "Authorization"],
    methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"]
)

# ── Config ──────────────────────────────────────────────────────────────────
SECRET_KEY = os.environ.get("SECRET_KEY")
if not SECRET_KEY:
    print("⚠️  WARNING: SECRET_KEY not set! Using default development key.")
    print("   Set via: export SECRET_KEY='your-secret-key'")
    SECRET_KEY = "change-me-in-production-xyz987"
TOKEN_EXP_HOURS = 8

def parse_database_url(url: str) -> dict:
    parsed = urlparse(url)
    return {
        "host": parsed.hostname,
        "port": parsed.port or 3306,
        "user": unquote_plus(parsed.username) if parsed.username else "",
        "password": unquote_plus(parsed.password) if parsed.password else "",
        "db": parsed.path.lstrip("/") if parsed.path else "",
        "charset": "utf8mb4",
        "cursorclass": pymysql.cursors.DictCursor,
        "autocommit": True,
    }

DB_CONFIG = {
    "host":     os.environ.get("DB_HOST",     "localhost"),
    "port":     int(os.environ.get("DB_PORT", 3306)),
    "user":     os.environ.get("DB_USER",     "root"),
    "password": os.environ.get("DB_PASSWORD", ""),
    "db":       os.environ.get("DB_NAME",     "attendance_db"),
    "charset":  "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor,
    "autocommit": True,
}

database_url = os.environ.get("DATABASE_URL") or os.environ.get("JAWSDB_URL") or os.environ.get("JAWSDB_MARIA_URL")
if database_url:
    DB_CONFIG = parse_database_url(database_url)


# ── Helpers ──────────────────────────────────────────────────────────────────
def get_db():
    return pymysql.connect(**DB_CONFIG)


def make_token(user_id: int, role: str) -> str:
    now = datetime.now(timezone.utc)
    exp = now + timedelta(hours=TOKEN_EXP_HOURS)
    payload = {
        "sub":  str(user_id),  # Convert to string!
        "role": role,
        "iat":  int(now.timestamp()),
        "exp":  int(exp.timestamp()),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


def decode_token(token: str) -> dict:
    return jwt.decode(token, SECRET_KEY, algorithms=["HS256"])


def auth_required(roles=None):
    """Decorator — validates Bearer JWT and optionally checks role."""
    from functools import wraps

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            auth = request.headers.get("Authorization", "").strip()
            if not auth.startswith("Bearer "):
                return jsonify({"error": "Unauthorized"}), 401
            try:
                token = auth.split()[1].strip()
                payload = decode_token(token)
            except jwt.ExpiredSignatureError:
                return jsonify({"error": "Token expired"}), 401
            except jwt.InvalidTokenError as e:
                return jsonify({"error": f"Invalid token: {str(e)}"}), 401
            if roles and payload["role"] not in roles:
                return jsonify({"error": "Forbidden"}), 403
            request.user = payload
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def gen_code(length=6) -> str:
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=length))


# ── Auth Routes ──────────────────────────────────────────────────────────────
@app.post("/api/auth/login")
def login():
    body = request.get_json(force=True)
    identifier = body.get("email", "").strip()
    password = body.get("password", "")

    if not identifier or not password:
        return jsonify({"error": "Identifier and password required"}), 400

    conn = get_db()
    with conn.cursor() as cur:
        if '@' in identifier:
            cur.execute("SELECT * FROM users WHERE email = %s", (identifier.lower(),))
        else:
            cur.execute("SELECT * FROM users WHERE student_id = %s", (identifier,))
        user = cur.fetchone()
    conn.close()

    if not user or not bcrypt.checkpw(password.encode(), user["password"].encode()):
        return jsonify({"error": "Invalid credentials"}), 401

    token = make_token(user["id"], user["role"])
    return jsonify({
        "token": token,
        "user": {
            "id":             user["id"],
            "full_name":      user["full_name"],
            "email":          user["email"],
            "role":           user["role"],
            "student_id":     user["student_id"],
            "section":        user["section"],
            "student_type":   user["student_type"],
            "gender":         user.get("gender"),
            "department":     user.get("department"),
            "profile_picture":user.get("profile_picture"),
        }
    })


@app.post("/api/auth/register")
def register():
    body      = request.get_json(force=True)
    full_name  = body.get("full_name", "").strip()
    identifier = body.get("email", "").strip()  # for students, this is student_id
    password   = body.get("password", "")
    role       = body.get("role", "student")
    student_id = body.get("student_id", "").strip() or None
    section    = body.get("section", "").strip() or None
    student_type = body.get("student_type", "regular")

    if not all([full_name, identifier, password]):
        return jsonify({"error": "All fields required"}), 400
    if role not in ("student", "teacher"):
        return jsonify({"error": "Invalid role"}), 400

    if role == "student":
        email = None
        student_id = identifier
    else:
        email = identifier.lower()
        student_id = student_id

    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO users (full_name, email, password, role, student_id, section, student_type) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s)",
                (full_name, email, hashed, role, student_id, section, student_type)
            )
        new_id = conn.insert_id()
    except pymysql.IntegrityError:
        conn.close()
        return jsonify({"error": "Identifier already registered"}), 409
    conn.close()

    token = make_token(new_id, role)
    return jsonify({"token": token, "user": {
        "id": new_id, "full_name": full_name,
        "email": email, "role": role,
        "student_id": student_id, "section": section, "student_type": student_type,
        "gender": None, "department": None, "profile_picture": None,
    }}), 201


# ── Session Routes (Teacher) ─────────────────────────────────────────────────
@app.post("/api/sessions")
@auth_required(roles=["teacher"])
def create_session():
    body    = request.get_json(force=True)
    subject = body.get("subject", "").strip()
    section = body.get("section", "").strip()
    date    = body.get("session_date")
    start   = body.get("start_time")
    end     = body.get("end_time")
    max_students = body.get("max_students")
    if max_students is not None:
        try:
            max_students = int(max_students)
            if max_students <= 0:
                max_students = None
        except:
            max_students = None

    if not all([subject, section, date, start, end]):
        return jsonify({"error": "All fields required"}), 400

    code = gen_code()
    conn = get_db()
    try:
        with conn.cursor() as cur:
            # ensure unique code
            for _ in range(10):
                cur.execute("SELECT id FROM sessions WHERE code = %s", (code,))
                if not cur.fetchone():
                    break
                code = gen_code()

            cur.execute(
                "INSERT INTO sessions (teacher_id, subject, section, session_date, "
                "start_time, end_time, code, max_students) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                (int(request.user["sub"]), subject, section, date, start, end, code, max_students)
            )
            session_id = conn.insert_id()
    except pymysql.err.OperationalError as e:
        if "Unknown column 'max_students'" in str(e):
            with conn.cursor() as cur:
                # ensure unique code
                for _ in range(10):
                    cur.execute("SELECT id FROM sessions WHERE code = %s", (code,))
                    if not cur.fetchone():
                        break
                    code = gen_code()

                cur.execute(
                    "INSERT INTO sessions (teacher_id, subject, section, session_date, "
                    "start_time, end_time, code) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                    (int(request.user["sub"]), subject, section, date, start, end, code)
                )
                session_id = conn.insert_id()
        else:
            conn.close()
            raise
    conn.close()
    return jsonify({"id": session_id, "code": code}), 201


@app.get("/api/sessions")
@auth_required(roles=["teacher"])
def list_sessions():
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, subject, section, session_date, start_time, end_time, "
                "code, max_students, is_open, created_at FROM sessions "
                "WHERE teacher_id = %s ORDER BY session_date DESC, start_time DESC",
                (int(request.user["sub"]),)
            )
            rows = cur.fetchall()
    except pymysql.err.OperationalError as e:
        # Fallback if max_students column doesn't exist
        if "Unknown column 'max_students'" in str(e):
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, subject, section, session_date, start_time, end_time, "
                    "code, is_open, created_at FROM sessions "
                    "WHERE teacher_id = %s ORDER BY session_date DESC, start_time DESC",
                    (int(request.user["sub"]),)
                )
                rows = cur.fetchall()
                # Add max_students as None for compatibility
                for r in rows:
                    r["max_students"] = None
        else:
            conn.close()
            raise
    conn.close()
    # stringify dates / times
    for r in rows:
        r["session_date"] = str(r["session_date"])
        r["start_time"]   = str(r["start_time"])
        r["end_time"]     = str(r["end_time"])
        r["created_at"]   = str(r["created_at"])
    return jsonify(rows)


@app.get("/api/sessions/<int:sid>")
@auth_required(roles=["teacher"])
def get_session(sid):
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, teacher_id, subject, section, session_date, start_time, end_time, "
            "code, max_students, is_open, created_at FROM sessions WHERE id = %s", (sid,)
        )
        row = cur.fetchone()
        if not row:
            conn.close()
            return jsonify({"error": "Not found"}), 404
        if row["teacher_id"] != int(request.user["sub"]):
            conn.close()
            return jsonify({"error": "Forbidden"}), 403
    conn.close()
    # stringify dates / times
    row["session_date"] = str(row["session_date"])
    row["start_time"]   = str(row["start_time"])
    row["end_time"]     = str(row["end_time"])
    row["created_at"]   = str(row["created_at"])
    return jsonify(row)


@app.patch("/api/sessions/<int:sid>/toggle")
@auth_required(roles=["teacher"])
def toggle_session(sid):
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT is_open, teacher_id FROM sessions WHERE id = %s", (sid,)
        )
        row = cur.fetchone()
        if not row:
            conn.close()
            return jsonify({"error": "Not found"}), 404
        if row["teacher_id"] != int(request.user["sub"]):
            conn.close()
            return jsonify({"error": "Forbidden"}), 403
        new_state = 0 if row["is_open"] else 1
        cur.execute("UPDATE sessions SET is_open = %s WHERE id = %s", (new_state, sid))
    conn.close()
    return jsonify({"is_open": bool(new_state)})


@app.delete("/api/sessions/<int:sid>")
@auth_required(roles=["teacher"])
def delete_session(sid):
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT teacher_id FROM sessions WHERE id = %s", (sid,)
        )
        row = cur.fetchone()
        if not row:
            conn.close()
            return jsonify({"error": "Not found"}), 404
        if row["teacher_id"] != int(request.user["sub"]):
            conn.close()
            return jsonify({"error": "Forbidden"}), 403
        cur.execute("DELETE FROM sessions WHERE id = %s", (sid,))
    conn.close()
    return jsonify({"message": "Session deleted"}), 200


@app.patch("/api/sessions/<int:sid>/max")
@auth_required(roles=["teacher"])
def update_session(sid):
    data = request.get_json()
    updates = {}
    if "max_students" in data:
        max_students = data["max_students"]
        if max_students is not None and (not isinstance(max_students, int) or max_students < 1):
            return jsonify({"error": "Invalid max_students"}), 400
        updates["max_students"] = max_students
    if "start_time" in data:
        start_time = data["start_time"]
        if not start_time:
            return jsonify({"error": "Invalid start_time"}), 400
        updates["start_time"] = start_time
    if "end_time" in data:
        end_time = data["end_time"]
        if not end_time:
            return jsonify({"error": "Invalid end_time"}), 400
        updates["end_time"] = end_time
    if not updates:
        return jsonify({"error": "No fields to update"}), 400
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT teacher_id FROM sessions WHERE id = %s", (sid,)
        )
        row = cur.fetchone()
        if not row:
            conn.close()
            return jsonify({"error": "Not found"}), 404
        if row["teacher_id"] != int(request.user["sub"]):
            conn.close()
            return jsonify({"error": "Forbidden"}), 403
        set_clause = ", ".join(f"{k} = %s" for k in updates.keys())
        values = list(updates.values()) + [sid]
        cur.execute(f"UPDATE sessions SET {set_clause} WHERE id = %s", values)
    conn.close()
    return jsonify(updates)


@app.get("/api/sessions/<int:sid>/attendance")
@auth_required(roles=["teacher"])
def session_attendance(sid):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT s.id, s.subject, s.section, s.session_date, s.start_time, "
                "s.end_time, s.code, s.max_students, s.is_open FROM sessions s WHERE s.id = %s AND s.teacher_id = %s",
                (sid, int(request.user["sub"]))
            )
            session = cur.fetchone()
    except pymysql.err.OperationalError as e:
        if "Unknown column 'max_students'" in str(e):
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT s.id, s.subject, s.section, s.session_date, s.start_time, "
                    "s.end_time, s.code, s.is_open FROM sessions s WHERE s.id = %s AND s.teacher_id = %s",
                    (sid, int(request.user["sub"]))
                )
                session = cur.fetchone()
                if session:
                    session["max_students"] = None
        else:
            conn.close()
            raise
    
    if not session:
        conn.close()
        return jsonify({"error": "Not found"}), 404

    with conn.cursor() as cur:
        cur.execute(
            "SELECT u.id AS uid, u.full_name, u.student_id AS sid, u.section, u.student_type, u.gender, u.department, u.profile_picture, "
            "a.confirmed_at, a.status "
            "FROM attendance a "
            "JOIN users u ON u.id = a.student_id "
            "WHERE a.session_id = %s "
            "ORDER BY a.confirmed_at",
            (sid,)
        )
        records = cur.fetchall()
    conn.close()

    session["session_date"] = str(session["session_date"])
    session["start_time"]   = str(session["start_time"])
    session["end_time"]     = str(session["end_time"])
    for r in records:
        r["confirmed_at"] = str(r["confirmed_at"])
    return jsonify({"session": session, "records": records})


@app.get("/api/users/<int:uid>")
@auth_required(roles=["teacher"])
def get_user_profile(uid):
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, full_name, student_id, section, student_type, gender, department, profile_picture "
            "FROM users WHERE id = %s AND role = 'student'",
            (uid,)
        )
        user = cur.fetchone()
    conn.close()
    if not user:
        return jsonify({"error": "Student not found"}), 404
    return jsonify({"user": user})


@app.patch("/api/users/profile")
@auth_required(roles=["student"])
def update_my_profile():
    body = request.get_json(force=True)
    print("DEBUG: Received body:", body)
    updates = {}
    if "full_name" in body:
        updates["full_name"] = body["full_name"].strip()
    if "student_id" in body:
        updates["student_id"] = body["student_id"].strip()
    if "section" in body:
        updates["section"] = body["section"].strip() or None
    if "student_type" in body:
        updates["student_type"] = body["student_type"].strip() or None
    if "gender" in body:
        updates["gender"] = body["gender"].strip() or None
    if "department" in body:
        updates["department"] = body["department"].strip() or None
    if "profile_picture" in body:
        updates["profile_picture"] = body["profile_picture"]

    if not updates:
        return jsonify({"error": "No profile fields to update"}), 400

    conn = get_db()
    try:
        with conn.cursor() as cur:
            if "student_id" in updates:
                cur.execute("SELECT id FROM users WHERE student_id = %s AND id != %s", (updates["student_id"], int(request.user["sub"])))
                if cur.fetchone():
                    return jsonify({"error": "Student ID already in use"}), 409
            set_clause = ", ".join(f"{k} = %s" for k in updates.keys())
            values = list(updates.values()) + [int(request.user["sub"])]
            cur.execute(f"UPDATE users SET {set_clause} WHERE id = %s", values)
            cur.execute(
                "SELECT id, full_name, student_id, section, student_type, gender, department, profile_picture "
                "FROM users WHERE id = %s",
                (int(request.user["sub"]),)
            )
            updated_user = cur.fetchone()
    except pymysql.IntegrityError:
        conn.close()
        return jsonify({"error": "Failed to update profile"}), 500
    conn.close()
    if not updated_user:
        return jsonify({"error": "Could not reload profile"}), 500
    return jsonify({"message": "Profile updated", "user": updated_user})


# ── Attendance Routes (Student) ──────────────────────────────────────────────
@app.post("/api/attendance/confirm")
@auth_required(roles=["student"])
def confirm_attendance():
    body = request.get_json(force=True)
    code = body.get("code", "").strip().upper()
    if not code:
        return jsonify({"error": "Code required"}), 400

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, is_open, subject, section, max_students FROM sessions WHERE code = %s", (code,)
            )
            session = cur.fetchone()
    except pymysql.err.OperationalError as e:
        if "Unknown column 'max_students'" in str(e):
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, is_open, subject, section FROM sessions WHERE code = %s", (code,)
                )
                session = cur.fetchone()
                if session:
                    session["max_students"] = None
        else:
            conn.close()
            raise
    
    if not session:
        conn.close()
        return jsonify({"error": "Invalid session code"}), 404
    if not session["is_open"]:
        conn.close()
        return jsonify({"error": "Session is closed"}), 409

    with conn.cursor() as cur:
        # check max_students limit
        if session["max_students"] is not None:
            cur.execute("SELECT COUNT(*) as count FROM attendance WHERE session_id = %s", (session["id"],))
            count = cur.fetchone()["count"]
            if count >= session["max_students"]:
                conn.close()
                return jsonify({"error": "Session is full"}), 409

        # check duplicate
        cur.execute(
            "SELECT id FROM attendance WHERE session_id = %s AND student_id = %s",
            (session["id"], int(request.user["sub"]))
        )
        if cur.fetchone():
            conn.close()
            return jsonify({"error": "Already confirmed for this session"}), 409

        # determine status based on designated hours and grace period
        cur.execute("SELECT session_date, start_time, end_time FROM sessions WHERE id = %s", (session["id"],))
        s = cur.fetchone()
        
        # Combine session_date with start_time and end_time
        session_date = s["session_date"]
        start_time = s["start_time"]
        end_time = s["end_time"]
        
        # Parse time objects to extract hour and minute
        # PyMySQL returns TIME columns as datetime.time objects
        if hasattr(start_time, 'hour'):
            start_h = start_time.hour
            start_m = start_time.minute
        elif isinstance(start_time, timedelta):
            start_total_sec = int(start_time.total_seconds())
            start_h, start_rem = divmod(start_total_sec, 3600)
            start_m, _ = divmod(start_rem, 60)
        else:
            start_h, start_m = map(int, str(start_time).split(":")[:2])
        
        if hasattr(end_time, 'hour'):
            end_h = end_time.hour
            end_m = end_time.minute
        elif isinstance(end_time, timedelta):
            end_total_sec = int(end_time.total_seconds())
            end_h, end_rem = divmod(end_total_sec, 3600)
            end_m, _ = divmod(end_rem, 60)
        else:
            end_h, end_m = map(int, str(end_time).split(":")[:2])
        
        # Create datetime objects for comparison
        end_datetime = datetime.combine(session_date, time(end_h, end_m))
        late_cutoff = end_datetime + timedelta(minutes=30)
        
        now = datetime.now()
        
        if now <= end_datetime:
            status = "present"
        elif now <= late_cutoff:
            status = "late"
        else:
            status = "absent"

        try:
            cur.execute(
                "INSERT INTO attendance (session_id, student_id, status) VALUES (%s,%s,%s)",
                (session["id"], int(request.user["sub"]), status)
            )
        except pymysql.err.OperationalError as e:
            if "Data truncated" in str(e) and status == "absent":
                # Update the ENUM to include 'absent'
                cur.execute("ALTER TABLE attendance MODIFY COLUMN status ENUM('present','late','absent') NOT NULL DEFAULT 'present'")
                # Retry the insert
                cur.execute(
                    "INSERT INTO attendance (session_id, student_id, status) VALUES (%s,%s,%s)",
                    (session["id"], int(request.user["sub"]), status)
                )
            else:
                raise
    conn.close()
    return jsonify({
        "message": "Attendance confirmed!",
        "status":  status,
        "subject": session["subject"],
    }), 201


@app.get("/api/attendance/my")
@auth_required(roles=["student"])
def my_attendance():
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT s.subject, s.section, s.session_date, s.start_time, "
            "a.confirmed_at, a.status "
            "FROM attendance a "
            "JOIN sessions s ON s.id = a.session_id "
            "WHERE a.student_id = %s "
            "ORDER BY s.session_date DESC",
            (int(request.user["sub"]),)
        )
        rows = cur.fetchall()
    conn.close()
    for r in rows:
        r["session_date"]  = str(r["session_date"])
        r["start_time"]    = str(r["start_time"])
        r["confirmed_at"]  = str(r["confirmed_at"])
    return jsonify(rows)


# ── Health ───────────────────────────────────────────────────────────────────
@app.get("/api/health")
def health():
    return jsonify({"status": "ok", "time": str(datetime.now())})


# ── Startup Schema Check ──────────────────────────────────────────────────────
def ensure_schema():
    """Ensure database schema supports all required columns and values."""
    try:
        conn = get_db()
        with conn.cursor() as cur:
            # Ensure attendance status ENUM includes 'absent'
            cur.execute("ALTER TABLE attendance MODIFY COLUMN status ENUM('present','late','absent') NOT NULL DEFAULT 'present'")
        conn.close()
        print("✓ Database schema verified and updated if needed")
    except Exception as e:
        print(f"⚠️  Warning: Could not verify schema: {e}")


# ── Run ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    ensure_schema()
    app.run(debug=True, port=5000)
