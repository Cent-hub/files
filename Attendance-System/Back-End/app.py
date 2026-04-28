"""
Attendance Management System — Flask Backend
Stack: Python 3.10+, Flask, Flask-CORS, PyMySQL, bcrypt, PyJWT
Run:   pip install flask flask-cors pymysql bcrypt pyjwt
       python app.py
"""

import os
import random
import string
from datetime import datetime, timedelta, timezone

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
    email    = body.get("email", "").strip().lower()
    password = body.get("password", "")

    if not email or not password:
        return jsonify({"error": "Email and password required"}), 400

    conn = get_db()
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cur.fetchone()
    conn.close()

    if not user or not bcrypt.checkpw(password.encode(), user["password"].encode()):
        return jsonify({"error": "Invalid credentials"}), 401

    token = make_token(user["id"], user["role"])
    return jsonify({
        "token": token,
        "user": {
            "id":         user["id"],
            "full_name":  user["full_name"],
            "email":      user["email"],
            "role":       user["role"],
            "student_id": user["student_id"],
            "section":    user["section"],
        }
    })


@app.post("/api/auth/register")
def register():
    body      = request.get_json(force=True)
    full_name  = body.get("full_name", "").strip()
    email      = body.get("email", "").strip().lower()
    password   = body.get("password", "")
    role       = body.get("role", "student")
    student_id = body.get("student_id", "").strip() or None
    section    = body.get("section", "").strip() or None

    if not all([full_name, email, password]):
        return jsonify({"error": "All fields required"}), 400
    if role not in ("student", "teacher"):
        return jsonify({"error": "Invalid role"}), 400

    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO users (full_name, email, password, role, student_id, section) "
                "VALUES (%s,%s,%s,%s,%s,%s)",
                (full_name, email, hashed, role, student_id, section)
            )
        new_id = conn.insert_id()
    except pymysql.IntegrityError:
        conn.close()
        return jsonify({"error": "Email already registered"}), 409
    conn.close()

    token = make_token(new_id, role)
    return jsonify({"token": token, "user": {
        "id": new_id, "full_name": full_name,
        "email": email, "role": role,
        "student_id": student_id, "section": section,
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
            "SELECT u.full_name, u.student_id AS sid, u.section, "
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

        # determine late (simple: after 15 min from start)
        cur.execute("SELECT start_time FROM sessions WHERE id = %s", (session["id"],))
        s = cur.fetchone()
        start_str = str(s["start_time"])
        # start_time comes as timedelta from pymysql
        if isinstance(s["start_time"], timedelta):
            total_sec = int(s["start_time"].total_seconds())
            h, rem = divmod(total_sec, 3600)
            m, _ = divmod(rem, 60)
        else:
            h, m = map(int, start_str.split(":")[:2])

        now     = datetime.now()
        cutoff  = now.replace(hour=h, minute=m, second=0) + timedelta(minutes=15)
        status  = "late" if now > cutoff else "present"

        cur.execute(
            "INSERT INTO attendance (session_id, student_id, status) VALUES (%s,%s,%s)",
            (session["id"], int(request.user["sub"]), status)
        )
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


# ── Run ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=True, port=5000)
