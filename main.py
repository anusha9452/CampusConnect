"""CampusConnect - Smart Student Life Assistant
Backend: FastAPI + SQLite | Frontend: Jinja2 templates + HTML/CSS/JS
"""
import os
import sqlite3
import hashlib
import secrets
from datetime import date

from fastapi import FastAPI, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

BASE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE, "campusconnect.db")
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

app = FastAPI(title="CampusConnect")
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SECRET_KEY", "change-this-secret-key"))
app.mount("/static", StaticFiles(directory=os.path.join(BASE, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE, "templates"))


# ---------------------------------------------------------------- database
def query(sql, args=(), one=False):
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    rows = con.execute(sql, args).fetchall()
    con.close()
    return (rows[0] if rows else None) if one else rows


def execute(sql, args=()):
    con = sqlite3.connect(DB_PATH)
    cur = con.execute(sql, args)
    con.commit()
    last = cur.lastrowid
    con.close()
    return last


def init_db():
    con = sqlite3.connect(DB_PATH)
    con.executescript("""
    CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, email TEXT UNIQUE,
        password TEXT, branch TEXT, year TEXT, phone TEXT DEFAULT '');
    CREATE TABLE IF NOT EXISTS assignments(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
        title TEXT, subject TEXT, due_date TEXT, status TEXT DEFAULT 'Pending');
    CREATE TABLE IF NOT EXISTS timetable(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
        day TEXT, start_time TEXT, subject TEXT, room TEXT, faculty TEXT);
    CREATE TABLE IF NOT EXISTS attendance(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
        subject TEXT, attended INTEGER DEFAULT 0, total INTEGER DEFAULT 0);
    CREATE TABLE IF NOT EXISTS planner(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
        day TEXT, topic TEXT, hours REAL);
    CREATE TABLE IF NOT EXISTS notices(id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, body TEXT,
        posted_on TEXT, category TEXT);
    CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, event_date TEXT,
        venue TEXT, description TEXT);
    """)
    if con.execute("SELECT COUNT(*) FROM notices").fetchone()[0] == 0:
        con.executemany("INSERT INTO notices(title,body,posted_on,category) VALUES(?,?,?,?)", [
            ("Mid-Semester Examination Schedule", "Mid-semester exams will begin from the first week of next month.", "2026-11-18", "Examination"),
            ("Library Timing Change", "Library will remain open till 8 PM on weekdays.", "2026-11-15", "General"),
            ("Fee Payment Reminder", "Last date for semester fee payment is 30 November.", "2026-11-12", "Accounts"),
            ("Lab Record Submission", "All lab records must be submitted to respective faculty.", "2026-11-10", "Academic"),
        ])
        con.executemany("INSERT INTO events(title,event_date,venue,description) VALUES(?,?,?,?)", [
            ("Technical Fest - TechNova", "2026-12-05", "Main Auditorium", "Coding contest, quiz and project exhibition."),
            ("Placement Awareness Seminar", "2026-12-10", "Seminar Hall", "Guidance on resume building and interviews."),
            ("Annual Sports Day", "2026-12-18", "College Ground", "Inter-department sports competitions."),
            ("Cultural Evening", "2026-12-22", "Open Air Theatre", "Music, dance and drama performances."),
        ])
    con.commit()
    con.close()


init_db()


# ---------------------------------------------------------------- helpers
def hash_password(password, salt=None):
    salt = salt or secrets.token_hex(8)
    h = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000).hex()
    return f"{salt}${h}"


def check_password(password, stored):
    salt = stored.split("$")[0]
    return hash_password(password, salt) == stored


def current_user(request):
    uid = request.session.get("uid")
    return query("SELECT * FROM users WHERE id=?", (uid,), one=True) if uid else None


def render(request, template, active, **ctx):
    """Render a protected page; redirect to login if not logged in."""
    user = current_user(request)
    if not user:
        return RedirectResponse("/login", 303)
    ctx.update(user=user, active=active, title=active)
    return templates.TemplateResponse(request, template, ctx)


def auth_page(request, mode, error=None):
    return templates.TemplateResponse(request, "auth.html", {"mode": mode, "error": error})


# ---------------------------------------------------------------- authentication
@app.get("/register")
def register_page(request: Request):
    return auth_page(request, "register")


@app.post("/register")
def register(request: Request, name: str = Form(...), email: str = Form(...), password: str = Form(...),
             branch: str = Form("Computer Science"), year: str = Form("2nd Year")):
    email = email.strip().lower()
    if len(password) < 6:
        return auth_page(request, "register", "Password must be at least 6 characters.")
    if query("SELECT id FROM users WHERE email=?", (email,), one=True):
        return auth_page(request, "register", "This email is already registered.")
    uid = execute("INSERT INTO users(name,email,password,branch,year) VALUES(?,?,?,?,?)",
                  (name.strip(), email, hash_password(password), branch, year))
    request.session["uid"] = uid
    return RedirectResponse("/", 303)


@app.get("/login")
def login_page(request: Request):
    return auth_page(request, "login")


@app.post("/login")
def login(request: Request, email: str = Form(...), password: str = Form(...)):
    u = query("SELECT * FROM users WHERE email=?", (email.strip().lower(),), one=True)
    if not u or not check_password(password, u["password"]):
        return auth_page(request, "login", "Invalid email or password.")
    request.session["uid"] = u["id"]
    return RedirectResponse("/", 303)


@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", 303)


# ---------------------------------------------------------------- dashboard
@app.get("/")
def dashboard(request: Request):
    user = current_user(request)
    if not user:
        return RedirectResponse("/login", 303)
    uid, today = user["id"], date.today()
    pending = query("SELECT COUNT(*) c FROM assignments WHERE user_id=? AND status='Pending'", (uid,), True)["c"]
    att = query("SELECT SUM(attended) a, SUM(total) t FROM attendance WHERE user_id=?", (uid,), True)
    percent = round(att["a"] * 100 / att["t"]) if att["t"] else 0
    todays = query("SELECT * FROM timetable WHERE user_id=? AND day=? ORDER BY start_time", (uid, today.strftime("%A")))
    events = query("SELECT * FROM events WHERE event_date>=? ORDER BY event_date", (today.isoformat(),))
    notices = query("SELECT * FROM notices ORDER BY posted_on DESC LIMIT 4")
    deadlines = query("SELECT * FROM assignments WHERE user_id=? AND status='Pending' ORDER BY due_date LIMIT 5", (uid,))
    plan = sorted(query("SELECT * FROM planner WHERE user_id=?", (uid,)), key=lambda r: DAYS.index(r["day"]))
    return render(request, "dashboard.html", "Dashboard", pending=pending, percent=percent, todays=todays,
                  events=events, notices=notices, deadlines=deadlines, plan=plan, today=today.isoformat())


# ---------------------------------------------------------------- assignments
@app.get("/assignments")
def assignments(request: Request):
    user = current_user(request)
    rows = query("SELECT * FROM assignments WHERE user_id=? ORDER BY status DESC, due_date", (user["id"],)) if user else []
    return render(request, "assignments.html", "My Assignments", rows=rows, today=date.today().isoformat())


@app.post("/assignments/add")
def add_assignment(request: Request, title: str = Form(...), subject: str = Form(...), due_date: str = Form(...)):
    u = current_user(request)
    if u:
        execute("INSERT INTO assignments(user_id,title,subject,due_date) VALUES(?,?,?,?)", (u["id"], title, subject, due_date))
    return RedirectResponse("/assignments", 303)


@app.post("/assignments/{aid}/toggle")
def toggle_assignment(request: Request, aid: int):
    u = current_user(request)
    if u:
        execute("UPDATE assignments SET status=CASE status WHEN 'Pending' THEN 'Completed' ELSE 'Pending' END "
                "WHERE id=? AND user_id=?", (aid, u["id"]))
    return RedirectResponse("/assignments", 303)


# ---------------------------------------------------------------- timetable
@app.get("/timetable")
def timetable(request: Request):
    user = current_user(request)
    rows = []
    if user:
        rows = sorted(query("SELECT * FROM timetable WHERE user_id=?", (user["id"],)),
                      key=lambda r: (DAYS.index(r["day"]), r["start_time"]))
    return render(request, "timetable.html", "Class Timetable", rows=rows, days=DAYS)


@app.post("/timetable/add")
def add_class(request: Request, day: str = Form(...), start_time: str = Form(...), subject: str = Form(...),
              room: str = Form(""), faculty: str = Form("")):
    u = current_user(request)
    if u and day in DAYS:
        execute("INSERT INTO timetable(user_id,day,start_time,subject,room,faculty) VALUES(?,?,?,?,?,?)",
                (u["id"], day, start_time, subject, room, faculty))
    return RedirectResponse("/timetable", 303)


# ---------------------------------------------------------------- attendance
@app.get("/attendance")
def attendance(request: Request):
    user = current_user(request)
    rows = query("SELECT * FROM attendance WHERE user_id=?", (user["id"],)) if user else []
    return render(request, "attendance.html", "Attendance Tracker", rows=rows)


@app.post("/attendance/add")
def add_subject(request: Request, subject: str = Form(...)):
    u = current_user(request)
    if u:
        execute("INSERT INTO attendance(user_id,subject) VALUES(?,?)", (u["id"], subject))
    return RedirectResponse("/attendance", 303)


@app.post("/attendance/{aid}/{action}")
def mark_attendance(request: Request, aid: int, action: str):
    u = current_user(request)
    if u and action in ("present", "absent"):
        execute("UPDATE attendance SET total=total+1, attended=attended+? WHERE id=? AND user_id=?",
                (1 if action == "present" else 0, aid, u["id"]))
    return RedirectResponse("/attendance", 303)


# ---------------------------------------------------------------- study planner
@app.get("/planner")
def planner(request: Request):
    user = current_user(request)
    rows = []
    if user:
        rows = sorted(query("SELECT * FROM planner WHERE user_id=?", (user["id"],)), key=lambda r: DAYS.index(r["day"]))
    return render(request, "planner.html", "Study Planner", rows=rows, days=DAYS)


@app.post("/planner/add")
def add_plan(request: Request, day: str = Form(...), topic: str = Form(...), hours: float = Form(1)):
    u = current_user(request)
    if u and day in DAYS:
        execute("INSERT INTO planner(user_id,day,topic,hours) VALUES(?,?,?,?)", (u["id"], day, topic, hours))
    return RedirectResponse("/planner", 303)


# ---------------------------------------------------------------- notices & events
@app.get("/notices")
def notices(request: Request):
    return render(request, "notices.html", "College Notices", rows=query("SELECT * FROM notices ORDER BY posted_on DESC"))


@app.get("/events")
def events(request: Request):
    return render(request, "events.html", "Campus Events", rows=query("SELECT * FROM events ORDER BY event_date"),
                  today=date.today().isoformat())


# ---------------------------------------------------------------- profile
@app.get("/profile")
def profile(request: Request):
    return render(request, "profile.html", "Student Profile")


@app.post("/profile")
def update_profile(request: Request, name: str = Form(...), branch: str = Form(...), year: str = Form(...),
                   phone: str = Form("")):
    u = current_user(request)
    if u:
        execute("UPDATE users SET name=?, branch=?, year=?, phone=? WHERE id=?", (name, branch, year, phone, u["id"]))
    return RedirectResponse("/profile", 303)


# ---------------------------------------------------------------- generic delete (whitelisted tables)
@app.post("/delete/{table}/{rid}")
def delete_row(request: Request, table: str, rid: int):
    u = current_user(request)
    if u and table in ("assignments", "timetable", "attendance", "planner"):
        execute(f"DELETE FROM {table} WHERE id=? AND user_id=?", (rid, u["id"]))
    return RedirectResponse("/" + ("planner" if table == "planner" else table), 303)
