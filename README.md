# Northstar Academy School Management System

A small SQLite-backed school management system for a school with day and boarding sectors, boys and girls, differentiated uniforms, and role-aware account access.

## Run locally

Run the Python application server so the browser and API use the same origin:

```bash
python3 server.py
```

Then visit `http://localhost:8080`.

The server creates `school.db` on first start. It contains tables for users, students, and finance transactions. The database file is local and should be backed up in a real deployment.

## Demo accounts

All demo accounts use the password `northstar`:

- `head@northstar.test` or `deputy@northstar.test`: full administration access
- `bursar@northstar.test`: finance-only access
- `teacher@northstar.test`, `cook@northstar.test`, `cleaner@northstar.test`, `askari@northstar.test`, or `electrician@northstar.test`: staff workspace access

All demo accounts use the password `northstar`. Head Teacher and Deputy Head Teacher accounts have admin access. The Bursar can access money-related endpoints only. Production use should add HTTPS, a production session store, password reset, audit logging, CSRF protection, and stronger deployment secrets.

The Head Teacher workspace contains teacher rosters and roles, total student population, day/boarding residential status, student financial flow, academic performance, support staff and roles, alumni academic documents, and class timetables. These records are stored in SQLite and are restricted server-side to the Head Teacher role; the Deputy Head Teacher cannot access this endpoint.
