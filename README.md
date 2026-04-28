# AttendEase — Attendance Management System
## Stack: Python (Flask) + MySQL + HTML/CSS/JS

---

## 📦 Requirements

### Python packages
```
flask
flask-cors
pymysql
bcrypt
pyjwt
```

Install all at once:
```bash
pip install flask flask-cors pymysql bcrypt pyjwt
```

---

## 🗄️ Database Setup

1. Start your MySQL server
2. Open MySQL client and run the schema file:
```bash
mysql -u root -p < database.sql
```
This creates the `attendance_db` database with all tables and demo seed data.

---

## ⚙️ Configuration

Edit the top of `app.py` to match your environment:

```python
DB_CONFIG = {
    "host":     "localhost",
    "port":     3306,
    "user":     "root",
    "password": "YOUR_MYSQL_PASSWORD",
    "db":       "attendance_db",
    ...
}
```

Or use environment variables:
```bash
export DB_HOST=localhost
export DB_USER=root
export DB_PASSWORD=yourpassword
export DB_NAME=attendance_db
export SECRET_KEY=your-secret-jwt-key
```

---

## 🚀 Running the App

### 1. Start the backend
```bash
python app.py
```
Flask runs on **http://localhost:5000**

### 2. Open the frontend
Open `index.html` directly in your browser — no server needed for the frontend.

> ⚠️ Make sure Flask is running before you open the HTML file.

---

## 👤 Demo Accounts

| Role    | Email                 | Password    |
|---------|-----------------------|-------------|
| Teacher | teacher@school.edu    | password123 |
| Student | juan@student.edu      | password123 |
| Student | ana@student.edu       | password123 |
| Student | carlo@student.edu     | password123 |

---

## 🔄 How It Works

### Teacher Flow
1. Login → **Sessions** tab
2. Click **New Session** → fill subject, section, date, time → click Create
3. A **6-character code** (e.g. `ATT7X2`) is shown — share it with students
4. Click **View** on any session to see who's present in real-time
5. Click **Close** to stop accepting attendance for that session

### Student Flow
1. Login → **Confirm** tab
2. Enter the 6-character code given by the teacher
3. System marks you **Present** (or **Late** if more than 15 min past start)
4. View your full attendance history in **My History** tab

---

## 📁 File Structure

```
attendance_system/
├── app.py          ← Flask backend (all API routes)
├── database.sql    ← MySQL schema + seed data
├── index.html      ← Complete frontend (single file)
├── requirements.txt
└── README.md
```

---

## 🔌 API Endpoints

| Method | Endpoint                        | Auth     | Description                  |
|--------|---------------------------------|----------|------------------------------|
| POST   | /api/auth/login                 | None     | Login                        |
| POST   | /api/auth/register              | None     | Register new user            |
| GET    | /api/sessions                   | Teacher  | List teacher's sessions      |
| POST   | /api/sessions                   | Teacher  | Create new session           |
| PATCH  | /api/sessions/:id/toggle        | Teacher  | Open/close session           |
| GET    | /api/sessions/:id/attendance    | Teacher  | View who attended            |
| POST   | /api/attendance/confirm         | Student  | Confirm attendance via code  |
| GET    | /api/attendance/my              | Student  | View own attendance history  |
| GET    | /api/health                     | None     | Health check                 |
