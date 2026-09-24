#!/usr/bin/env python3
import hashlib
import http.cookies
import json
import os
import secrets
import sqlite3
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).parent
DATABASE = ROOT / "school.db"
SESSIONS = {}
CURRENCY = "UGX"
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


def password_hash(password):
    return hashlib.pbkdf2_hmac("sha256", password.encode(), b"northstar-school", 120_000).hex()


def database():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    with database() as connection:
        connection.executescript("""
            CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT NOT NULL, role TEXT NOT NULL,
              email TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL,
              access TEXT NOT NULL CHECK (access IN ('admin','finance','staff')),
              department TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1);
            CREATE TABLE IF NOT EXISTS students (id TEXT PRIMARY KEY, name TEXT NOT NULL, class_name TEXT NOT NULL,
              gender TEXT NOT NULL, sector TEXT NOT NULL, uniform TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS finance_transactions (id INTEGER PRIMARY KEY, reference TEXT NOT NULL,
              description TEXT NOT NULL, amount INTEGER NOT NULL, status TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS teacher_roster (id INTEGER PRIMARY KEY, name TEXT NOT NULL, assignment TEXT NOT NULL,
              class_name TEXT NOT NULL, subject TEXT NOT NULL, sector TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS support_staff (id INTEGER PRIMARY KEY, name TEXT NOT NULL, role TEXT NOT NULL,
              department TEXT NOT NULL, responsibility TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS student_financial_flow (id INTEGER PRIMARY KEY, student_id TEXT NOT NULL,
              student_name TEXT NOT NULL, term TEXT NOT NULL, expected INTEGER NOT NULL, paid INTEGER NOT NULL, status TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS academic_performance (id INTEGER PRIMARY KEY, class_name TEXT NOT NULL, subject TEXT NOT NULL,
              average INTEGER NOT NULL, pass_rate INTEGER NOT NULL, trend TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS alumni_documents (id INTEGER PRIMARY KEY, alumnus_name TEXT NOT NULL,
              graduation_year INTEGER NOT NULL, document_type TEXT NOT NULL, status TEXT NOT NULL, updated_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS class_timetable (id INTEGER PRIMARY KEY, class_name TEXT NOT NULL, day TEXT NOT NULL,
              period TEXT NOT NULL, subject TEXT NOT NULL, teacher TEXT NOT NULL, room TEXT NOT NULL);
        """)
        if connection.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
            connection.executemany("INSERT INTO users (name,role,email,password_hash,access,department) VALUES (?,?,?,?,?,?)",
                [(n,r,e,password_hash("northstar"),a,d) for n,r,e,a,d in USERS])
        # Start with clean, user-entered tables. Existing demo records are removed too.
        for table in ("students", "finance_transactions", "teacher_roster", "support_staff",
                      "student_financial_flow", "academic_performance", "alumni_documents", "class_timetable"):
            connection.execute(f"DELETE FROM {table}")


def current_user(handler):
    cookies = http.cookies.SimpleCookie(handler.headers.get("Cookie", ""))
    session = cookies.get("session")
    return SESSIONS.get(session.value) if session else None


def respond(handler, payload, status=200, headers=None, content_type="application/json"):
    body = json.dumps(payload).encode() if content_type == "application/json" else payload
    handler.send_response(status)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Content-Length", str(len(body)))
    for key, value in (headers or {}).items(): handler.send_header(key, value)
    handler.end_headers(); handler.wfile.write(body)


class SchoolHandler(SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/api/login": return respond(self, {"error":"Not found"}, 404)
        try:
            length = int(self.headers.get("Content-Length", 0)); credentials = json.loads(self.rfile.read(length))
        except (ValueError, json.JSONDecodeError): return respond(self, {"error":"Invalid request"}, 400)
        with database() as db:
            user = db.execute("SELECT id,name,role,email,access,department FROM users WHERE email=? AND password_hash=? AND active=1",
                              (credentials.get("email", "").lower(), password_hash(credentials.get("password", "")))).fetchone()
        if not user: return respond(self, {"error":"Invalid credentials"}, 401)
        token = secrets.token_urlsafe(32); SESSIONS[token] = dict(user)
        respond(self, dict(user), headers={"Set-Cookie":f"session={token}; HttpOnly; SameSite=Lax; Path=/"})

    def do_GET(self):
        if not self.path.startswith("/api/"): return super().do_GET()
        user = current_user(self)
        if not user: return respond(self, {"error":"Authentication required"}, 401)
        path, query = urlparse(self.path).path, parse_qs(urlparse(self.path).query)
        if path == "/api/config": return respond(self, {"currency": CURRENCY})
        if path == "/api/users":
            if user["access"] != "admin": return respond(self, {"error":"Administration access required"}, 403)
            with database() as db: rows = db.execute("SELECT id,name,role,email,access,department,active FROM users ORDER BY name").fetchall()
            return respond(self, [dict(row) for row in rows])
        if path == "/api/user-report":
            requested = query.get("id", [user["id"]])[0]
            if str(requested) != str(user["id"]) and user["access"] != "admin": return respond(self, {"error":"Administration access required"}, 403)
            with database() as db: row = db.execute("SELECT id,name,role,email,access,department,active FROM users WHERE id=?", (requested,)).fetchone()
            return respond(self, dict(row) if row else {"error":"User not found"}, 404 if not row else 200)
        if path == "/api/students":
            with database() as db: rows = db.execute("SELECT id,name,class_name,gender,sector,uniform FROM students ORDER BY name").fetchall()
            return respond(self, [[row[k] for k in row.keys()] for row in rows])
        if path == "/api/finance":
            if user["access"] not in ("admin", "finance"): return respond(self, {"error":"Finance access required"}, 403)
            with database() as db: rows = db.execute("SELECT reference,description,amount,status FROM finance_transactions ORDER BY id DESC").fetchall()
            return respond(self, {"currency":CURRENCY,"transactions":[dict(row) for row in rows]})
        if path == "/api/headteacher":
            if user["role"] != "Head Teacher": return respond(self, {"error":"Head Teacher access required"}, 403)
            empty = {"population":{"total":0,"day":0,"boarding":0,"boys":0,"girls":0},"roster":[],"support":[],"financial":[],"performance":[],"alumni":[],"timetable":[]}
            return respond(self, empty)
        return respond(self, {"error":"Not found"}, 404)

    def log_message(self, format, *args):
        if not self.path.startswith("/api/"): super().log_message(format, *args)


if __name__ == "__main__":
    initialize_database()
    port = int(os.environ.get("PORT", "8080"))
    server = ThreadingHTTPServer(("127.0.0.1", port), SchoolHandler)
    print(f"Northstar Academy running at http://127.0.0.1:{server.server_port}")
    server.serve_forever()
