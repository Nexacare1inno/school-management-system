#!/usr/bin/env python3
import hashlib
import http.cookies
import json
import os
import secrets
import sqlite3
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).parent
DATABASE = ROOT / "school.db"
SESSIONS = {}

USERS = [
    ("Grace Wanjiku", "Head Teacher", "head@northstar.test", "admin", "Administration"),
    ("Daniel Otieno", "Deputy Head Teacher", "deputy@northstar.test", "admin", "Administration"),
    ("Miriam Kilonzo", "Bursar", "bursar@northstar.test", "finance", "Finance"),
    ("Peter Mwangi", "Teacher", "teacher@northstar.test", "staff", "Academics"),
    ("Asha Njeri", "Cook", "cook@northstar.test", "staff", "Catering"),
    ("Samuel Kariuki", "Cleaner", "cleaner@northstar.test", "staff", "Facilities"),
    ("Moses Kiprotich", "Askari", "askari@northstar.test", "staff", "Security"),
    ("Irene Atieno", "Electrician", "electrician@northstar.test", "staff", "Facilities"),
]

STUDENTS = [
    ("ST-2026-014", "Amara Njeri", "Form 2 Blue", "Girls", "Boarding", "Emerald pinafore"),
    ("ST-2026-021", "Brian Otieno", "Form 3 Gold", "Boys", "Boarding", "Forest green blazer"),
    ("ST-2026-033", "Chloe Wambui", "Form 1 Green", "Girls", "Day", "Emerald pinafore"),
    ("ST-2026-048", "David Kiptoo", "Form 4 Red", "Boys", "Day", "Forest green blazer"),
    ("ST-2026-057", "Esther Achieng", "Form 2 Blue", "Girls", "Boarding", "Emerald pinafore"),
]

TEACHER_ROSTER = [
    ("Peter Mwangi", "Class Teacher", "Form 1 Green", "English", "Day"),
    ("Lydia Chebet", "Mathematics Lead", "Form 2 Blue", "Mathematics", "Boarding"),
    ("John Kamau", "Science Teacher", "Form 3 Gold", "Biology", "Boarding"),
    ("Faith Achieng", "House Parent", "Form 4 Red", "Residence", "Boarding"),
]

SUPPORT_STAFF = [
    ("Asha Njeri", "Cook", "Catering", "Kitchen and meal service"),
    ("Samuel Kariuki", "Cleaner", "Facilities", "Classrooms and offices"),
    ("Moses Kiprotich", "Askari", "Security", "Gate and night patrol"),
    ("Irene Atieno", "Electrician", "Facilities", "Electrical maintenance"),
]

FINANCIAL_FLOW = [
    ("ST-2026-014", "Amara Njeri", "Term 3", 68000, 68000, "Paid"),
    ("ST-2026-021", "Brian Otieno", "Term 3", 92000, 60000, "Part paid"),
    ("ST-2026-033", "Chloe Wambui", "Term 3", 54000, 54000, "Paid"),
    ("ST-2026-048", "David Kiptoo", "Term 3", 54000, 30000, "Part paid"),
]

ACADEMIC_PERFORMANCE = [
    ("Form 1 Green", "English", 72, 88, "Up"),
    ("Form 2 Blue", "Mathematics", 68, 81, "Stable"),
    ("Form 3 Gold", "Biology", 76, 91, "Up"),
    ("Form 4 Red", "Overall average", 79, 94, "Up"),
]

ALUMNI_DOCUMENTS = [
    ("Naomi Wambui", 2024, "KCSE certificate", "Verified", "2026-09-18"),
    ("Kevin Otieno", 2023, "Academic transcript", "Ready for collection", "2026-09-12"),
    ("Mary Chebet", 2022, "Recommendation letter", "Issued", "2026-08-30"),
]

CLASS_TIMETABLE = [
    ("Form 1 Green", "Monday", "08:00", "English", "Peter Mwangi", "Room 4"),
    ("Form 1 Green", "Monday", "10:30", "Mathematics", "Lydia Chebet", "Room 4"),
    ("Form 2 Blue", "Tuesday", "08:00", "Science", "John Kamau", "Lab 1"),
    ("Form 3 Gold", "Wednesday", "13:00", "Biology", "John Kamau", "Lab 1"),
    ("Form 4 Red", "Thursday", "10:30", "English", "Peter Mwangi", "Room 8"),
]


def password_hash(password):
    return hashlib.pbkdf2_hmac("sha256", password.encode(), b"northstar-school", 120_000).hex()


def database():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    with database() as connection:
        connection.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                role TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                access TEXT NOT NULL CHECK (access IN ('admin', 'finance', 'staff')),
                department TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS students (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                class_name TEXT NOT NULL,
                gender TEXT NOT NULL CHECK (gender IN ('Boys', 'Girls')),
                sector TEXT NOT NULL CHECK (sector IN ('Day', 'Boarding')),
                uniform TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS finance_transactions (
                id INTEGER PRIMARY KEY,
                reference TEXT NOT NULL,
                description TEXT NOT NULL,
                amount INTEGER NOT NULL,
                status TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS teacher_roster (
                id INTEGER PRIMARY KEY, name TEXT NOT NULL, assignment TEXT NOT NULL,
                class_name TEXT NOT NULL, subject TEXT NOT NULL, sector TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS support_staff (
                id INTEGER PRIMARY KEY, name TEXT NOT NULL, role TEXT NOT NULL,
                department TEXT NOT NULL, responsibility TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS student_financial_flow (
                id INTEGER PRIMARY KEY, student_id TEXT NOT NULL, student_name TEXT NOT NULL,
                term TEXT NOT NULL, expected INTEGER NOT NULL, paid INTEGER NOT NULL, status TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS academic_performance (
                id INTEGER PRIMARY KEY, class_name TEXT NOT NULL, subject TEXT NOT NULL,
                average INTEGER NOT NULL, pass_rate INTEGER NOT NULL, trend TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS alumni_documents (
                id INTEGER PRIMARY KEY, alumnus_name TEXT NOT NULL, graduation_year INTEGER NOT NULL,
                document_type TEXT NOT NULL, status TEXT NOT NULL, updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS class_timetable (
                id INTEGER PRIMARY KEY, class_name TEXT NOT NULL, day TEXT NOT NULL,
                period TEXT NOT NULL, subject TEXT NOT NULL, teacher TEXT NOT NULL, room TEXT NOT NULL
            );
        """)
        if connection.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
            connection.executemany(
                "INSERT INTO users (name, role, email, password_hash, access, department) VALUES (?, ?, ?, ?, ?, ?)",
                [(name, role, email, password_hash("northstar"), access, department) for name, role, email, access, department in USERS],
            )
        if connection.execute("SELECT COUNT(*) FROM students").fetchone()[0] == 0:
            connection.executemany("INSERT INTO students VALUES (?, ?, ?, ?, ?, ?)", STUDENTS)
        if connection.execute("SELECT COUNT(*) FROM finance_transactions").fetchone()[0] == 0:
            connection.executemany("INSERT INTO finance_transactions VALUES (?, ?, ?, ?, ?)", [
                (1, "#RC-8841", "Boarding fees · Form 3", 48000, "Received"),
                (2, "#RC-8840", "Uniform deposit · Form 1", 12500, "Received"),
                (3, "#INV-219", "Catering supplies", 76400, "Awaiting approval"),
            ])
        if connection.execute("SELECT COUNT(*) FROM teacher_roster").fetchone()[0] == 0:
            connection.executemany("INSERT INTO teacher_roster (name, assignment, class_name, subject, sector) VALUES (?, ?, ?, ?, ?)", TEACHER_ROSTER)
        if connection.execute("SELECT COUNT(*) FROM support_staff").fetchone()[0] == 0:
            connection.executemany("INSERT INTO support_staff (name, role, department, responsibility) VALUES (?, ?, ?, ?)", SUPPORT_STAFF)
        if connection.execute("SELECT COUNT(*) FROM student_financial_flow").fetchone()[0] == 0:
            connection.executemany("INSERT INTO student_financial_flow (student_id, student_name, term, expected, paid, status) VALUES (?, ?, ?, ?, ?, ?)", FINANCIAL_FLOW)
        if connection.execute("SELECT COUNT(*) FROM academic_performance").fetchone()[0] == 0:
            connection.executemany("INSERT INTO academic_performance (class_name, subject, average, pass_rate, trend) VALUES (?, ?, ?, ?, ?)", ACADEMIC_PERFORMANCE)
        if connection.execute("SELECT COUNT(*) FROM alumni_documents").fetchone()[0] == 0:
            connection.executemany("INSERT INTO alumni_documents (alumnus_name, graduation_year, document_type, status, updated_at) VALUES (?, ?, ?, ?, ?)", ALUMNI_DOCUMENTS)
        if connection.execute("SELECT COUNT(*) FROM class_timetable").fetchone()[0] == 0:
            connection.executemany("INSERT INTO class_timetable (class_name, day, period, subject, teacher, room) VALUES (?, ?, ?, ?, ?, ?)", CLASS_TIMETABLE)


def current_user(handler):
    cookies = http.cookies.SimpleCookie(handler.headers.get("Cookie", ""))
    session = cookies.get("session")
    return SESSIONS.get(session.value) if session else None


def respond(handler, payload, status=200, headers=None):
    body = json.dumps(payload).encode()
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    for key, value in (headers or {}).items():
        handler.send_header(key, value)
    handler.end_headers()
    handler.wfile.write(body)


class SchoolHandler(SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/api/login":
            respond(self, {"error": "Not found"}, 404)
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            credentials = json.loads(self.rfile.read(length))
        except (ValueError, json.JSONDecodeError):
            respond(self, {"error": "Invalid request"}, 400)
            return
        with database() as connection:
            user = connection.execute(
                "SELECT id, name, role, email, access, department FROM users WHERE email = ? AND password_hash = ? AND active = 1",
                (credentials.get("email", "").lower(), password_hash(credentials.get("password", ""))),
            ).fetchone()
        if not user:
            respond(self, {"error": "Invalid credentials"}, 401)
            return
        token = secrets.token_urlsafe(32)
        SESSIONS[token] = dict(user)
        respond(self, dict(user), headers={"Set-Cookie": f"session={token}; HttpOnly; SameSite=Lax; Path=/"})

    def do_GET(self):
        if self.path.startswith("/api/"):
            user = current_user(self)
            if not user:
                respond(self, {"error": "Authentication required"}, 401)
                return
            if self.path == "/api/students":
                with database() as connection:
                    rows = connection.execute("SELECT id, name, class_name, gender, sector, uniform FROM students ORDER BY name").fetchall()
                respond(self, [[row[key] for key in row.keys()] for row in rows])
                return
            if self.path == "/api/finance":
                if user["access"] not in ("admin", "finance"):
                    respond(self, {"error": "Finance access required"}, 403)
                    return
                with database() as connection:
                    rows = connection.execute("SELECT reference, description, amount, status FROM finance_transactions ORDER BY id DESC").fetchall()
                respond(self, [dict(row) for row in rows])
                return
            if self.path == "/api/headteacher":
                if user["role"] != "Head Teacher":
                    respond(self, {"error": "Head Teacher access required"}, 403)
                    return
                with database() as connection:
                    population = connection.execute("SELECT COUNT(*) AS total, SUM(sector = 'Day') AS day, SUM(sector = 'Boarding') AS boarding, SUM(gender = 'Boys') AS boys, SUM(gender = 'Girls') AS girls FROM students").fetchone()
                    roster = connection.execute("SELECT name, assignment, class_name, subject, sector FROM teacher_roster ORDER BY class_name").fetchall()
                    support = connection.execute("SELECT name, role, department, responsibility FROM support_staff ORDER BY name").fetchall()
                    financial = connection.execute("SELECT student_id, student_name, term, expected, paid, expected - paid AS balance, status FROM student_financial_flow ORDER BY student_name").fetchall()
                    performance = connection.execute("SELECT class_name, subject, average, pass_rate, trend FROM academic_performance ORDER BY class_name").fetchall()
                    alumni = connection.execute("SELECT alumnus_name, graduation_year, document_type, status, updated_at FROM alumni_documents ORDER BY graduation_year DESC").fetchall()
                    timetable = connection.execute("SELECT class_name, day, period, subject, teacher, room FROM class_timetable ORDER BY class_name, day, period").fetchall()
                respond(self, {"population": dict(population), "roster": [dict(row) for row in roster], "support": [dict(row) for row in support], "financial": [dict(row) for row in financial], "performance": [dict(row) for row in performance], "alumni": [dict(row) for row in alumni], "timetable": [dict(row) for row in timetable]})
                return
            respond(self, {"error": "Not found"}, 404)
            return
        super().do_GET()

    def log_message(self, format, *args):
        if not self.path.startswith("/api/"):
            super().log_message(format, *args)


if __name__ == "__main__":
    initialize_database()
    port = int(os.environ.get("PORT", "8080"))
    server = ThreadingHTTPServer(("127.0.0.1", port), SchoolHandler)
    print(f"Northstar Academy running at http://127.0.0.1:{server.server_port}")
    server.serve_forever()
