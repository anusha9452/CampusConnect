# CampusConnect – Smart Student Life Assistant
A simple college student portal built as a B.Tech CSE mini-project.

## 1. Features
Student registration/login, Dashboard, Assignments, Class Timetable, Attendance Tracker (75% rule),
Study Planner, College Notices, Campus Events, Student Profile. Responsive (desktop/tablet/mobile).

## 2. Technologies Used
| Layer | Technology | Why |
|---|---|---|
| Backend | Python + **FastAPI** | Fast, simple routing, auto-handles forms |
| Server | **Uvicorn** | ASGI server that runs FastAPI |
| Database | **SQLite** (`sqlite3` module) | File-based, no installation needed |
| Templates | **Jinja2** | Inserts Python data into HTML |
| Frontend | HTML5, CSS3, JavaScript | Pages, styling, sidebar toggle + delete confirmation |
| Auth | Session cookies (`SessionMiddleware`) + PBKDF2-SHA256 salted password hashing | Passwords never stored as plain text |

## 3. Project Structure
```
campusconnect/
├── main.py            # all backend routes + database code
├── requirements.txt   # Python packages
├── templates/         # HTML (Jinja2): base, auth, dashboard, assignments, ...
├── static/css/style.css
├── static/js/main.js
└── campusconnect.db   # created automatically on first run
```

## 4. Run Locally
```bash
python -m venv venv
venv\Scripts\activate          # Windows   (Linux/Mac: source venv/bin/activate)
pip install -r requirements.txt
uvicorn main:app --reload
```
Open http://127.0.0.1:8000 → Register → Login.

## 5. Host Publicly (Free) – Render.com
1. Create a GitHub account → New repository → upload all project files.
2. Sign up at https://render.com with GitHub.
3. **New → Web Service** → select your repository.
4. Settings:
   - Runtime: **Python 3**
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - Instance type: **Free**
5. Add environment variable `SECRET_KEY` = any long random text.
6. Click **Create Web Service**. After 2–3 minutes you get a public URL like `https://campusconnect.onrender.com`.

**Note:** On Render's free plan the SQLite file resets when the app restarts, and the app sleeps after
inactivity (first load is slow). Open it once before your viva.

### Quick alternative for demo day (no deployment): ngrok
Run `uvicorn main:app`, then in another terminal `ngrok http 8000` → share the https link it prints.

## 6. How It Works (for viva)
1. Browser sends a request (e.g. `/assignments`) → FastAPI route in `main.py` runs.
2. Route reads the logged-in user from the **session**, queries **SQLite** using `?` placeholders (prevents SQL injection).
3. Data is passed to a **Jinja2** template, which returns HTML.
4. Forms use **POST**, then the server redirects (POST-Redirect-GET) so refresh doesn't resubmit.
5. Each row stores `user_id`, so a student sees only their own data. Notices/events are shared.

### Database tables
`users`, `assignments`, `timetable`, `attendance`, `planner`, `notices`, `events`

### Likely viva questions
- **Why FastAPI?** Lightweight, quick to learn, clean routes, built-in form handling.
- **Why SQLite?** Zero setup, single file, enough for a mini-project; can be swapped for MySQL/PostgreSQL.
- **How is the password secured?** Salted PBKDF2-SHA256 hash; plain password is never stored.
- **How does login stay active?** Signed session cookie (`SessionMiddleware`, `SECRET_KEY`).
- **What is Jinja2?** Template engine: `{{ value }}`, `{% for %}`, `{% extends %}` for reusable layout (`base.html`).
- **How is attendance % calculated?** `attended / total × 100`; below 75% shows "Shortage".
- **How is the site responsive?** CSS media queries; JS toggles the sidebar on mobile.
- **How do you prevent SQL injection?** Parameterised queries (`?`), never string-joined user input.
- **Future scope:** Admin panel for notices, email reminders, file upload, MySQL.
