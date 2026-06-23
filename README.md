# FixMyArea

FixMyArea is a local Civic Issue Tracker built with Flask, SQLite, Bootstrap 5, Chart.js, and vanilla JavaScript.

## Features

- Citizen registration, login, logout, complaint filing, image upload, editing before assignment, tracking timeline, and notifications.
- Admin login, analytics dashboard, filtering, searching, pagination, status updates, priority assignment, remarks, user management, spam deletion, CSV export, and statistics.
- Responsive Bootstrap 5 UI with sidebar navigation, top navbar, data tables, charts, image preview, notification badge, and dark mode.
- SQLite database with automatic initialization and seed data.

## Run Locally

```bash
cd C:\Users\gupta\OneDrive\Desktop
Rename-Item FixMyArea FixMyArea_old
git clone https://github.com/shine-fly07/FixMyArea.git
cd FixMyArea
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000).

## Sample Admin Credentials

- Email: `admin@fixmyarea.local`
- Password: `Admin@123`

## Database

The app creates `database/fixmyarea.db` automatically on first run. To recreate the schema manually, run:

```bash
sqlite3 database/fixmyarea.db < database/schema.sql
```

Uploaded complaint images are stored in `uploads/`.
