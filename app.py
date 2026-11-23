"""Student Performance Prediction System - Flask + PostgreSQL/SQLite + scikit-learn."""
import csv, io, json, os, re, secrets, shutil, sqlite3
from datetime import datetime
from html import escape as html_escape
import joblib, numpy as np
from flask import Flask, Response, flash, redirect, render_template, request, session, url_for, send_file
from werkzeug.security import check_password_hash, generate_password_hash
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

try:
    import psycopg2
    import psycopg2.extras
    IntegrityErrors = (sqlite3.IntegrityError, psycopg2.IntegrityError)
except ImportError:
    psycopg2 = None
    IntegrityErrors = (sqlite3.IntegrityError,)

BASE = os.path.dirname(os.path.abspath(__file__))
LOCAL_DB = os.path.join(BASE, 'database.db')
DATABASE_URL = os.environ.get("DATABASE_URL")

if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

if not DATABASE_URL:
    if os.environ.get("VERCEL"):
        DB = '/tmp/database.db'
        if os.path.exists(LOCAL_DB) and not os.path.exists(DB):
            shutil.copy2(LOCAL_DB, DB)
    else:
        DB = LOCAL_DB

MODEL = os.path.join(BASE, 'performance_model.pkl')
KEY_FILE = os.path.join(BASE, 'secret.key')
app = Flask(__name__)

def load_secret_key():
    if os.environ.get("SECRET_KEY"):
        return os.environ.get("SECRET_KEY")
    try:
        if not os.path.exists(KEY_FILE):
            with open(KEY_FILE, "w") as f:
                f.write(secrets.token_hex(32))
        with open(KEY_FILE, "r") as f:
            return f.read().strip()
    except OSError:
        return "spp-system-vercel-secret-key-2026"

app.secret_key = load_secret_key()

class DualRow(dict):
    """Supports both row['col'] and row[0] indexing for SQLite and PostgreSQL."""
    def __init__(self, mapping):
        super().__init__(mapping)
        self._vals = list(mapping.values())
    def __getitem__(self, key):
        if isinstance(key, int):
            return self._vals[key]
        return super().__getitem__(key)

class PgCursorWrapper:
    def __init__(self, cur):
        self._cur = cur
        self.lastrowid = None
    def execute(self, sql, params=()):
        pg_sql = sql.replace('?', '%s')
        pg_sql = pg_sql.replace('COLLATE NOCASE', '')
        pg_sql = re.sub(r'CAST\(TRIM\(roll_no\) AS INTEGER\)', "NULLIF(regexp_replace(roll_no, '[^0-9]', '', 'g'), '')::INTEGER", pg_sql)
        is_insert = pg_sql.strip().upper().startswith('INSERT INTO')
        if is_insert and 'RETURNING' not in pg_sql.upper():
            pg_sql = pg_sql.rstrip().rstrip(';') + ' RETURNING id'
        self._cur.execute(pg_sql, params)
        if is_insert:
            row = self._cur.fetchone()
            self.lastrowid = row['id'] if row else None
        return self
    def fetchone(self):
        row = self._cur.fetchone()
        return DualRow(row) if row is not None else None
    def fetchall(self):
        return [DualRow(r) for r in self._cur.fetchall()]

class PgConnWrapper:
    def __init__(self, conn):
        self._conn = conn
    def execute(self, sql, params=()):
        cur = PgCursorWrapper(self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor))
        return cur.execute(sql, params)
    def commit(self):
        self._conn.commit()
    def close(self):
        self._conn.close()

def db():
    if DATABASE_URL and psycopg2:
        conn = psycopg2.connect(DATABASE_URL)
        return PgConnWrapper(conn)
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c

def init():
    c = db()
    if DATABASE_URL and psycopg2:
        c.execute('''CREATE TABLE IF NOT EXISTS users(
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS students(
            id SERIAL PRIMARY KEY,
            name TEXT,
            roll_no TEXT,
            department TEXT,
            attendance REAL,
            study_hours REAL,
            assignment_score REAL,
            previous_average REAL,
            prediction TEXT,
            math_marks REAL DEFAULT 0,
            physics_marks REAL DEFAULT 0,
            cs_marks REAL DEFAULT 0,
            subject_marks TEXT DEFAULT '{}',
            usn TEXT
        )''')
        c.commit()
        if os.path.exists(LOCAL_DB):
            sc = sqlite3.connect(LOCAL_DB)
            sc.row_factory = sqlite3.Row
            if c.execute('SELECT COUNT(*) FROM users').fetchone()[0] == 0:
                for u in sc.execute('SELECT name, username, password FROM users').fetchall():
                    c.execute('INSERT INTO users(name, username, password) VALUES(?,?,?) ON CONFLICT DO NOTHING',
                              (u['name'], u['username'], u['password']))
            if c.execute('SELECT COUNT(*) FROM students').fetchone()[0] == 0:
                for s in sc.execute('SELECT * FROM students ORDER BY id ASC').fetchall():
                    s_dict = dict(s)
                    c.execute('''INSERT INTO students(name,roll_no,department,attendance,study_hours,assignment_score,previous_average,prediction,math_marks,physics_marks,cs_marks,subject_marks,usn)
                                 VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                              (s_dict.get('name'), s_dict.get('roll_no'), s_dict.get('department'),
                               s_dict.get('attendance'), s_dict.get('study_hours'), s_dict.get('assignment_score'),
                               s_dict.get('previous_average'), s_dict.get('prediction'),
                               s_dict.get('math_marks', 0), s_dict.get('physics_marks', 0), s_dict.get('cs_marks', 0),
                               s_dict.get('subject_marks', '{}'), s_dict.get('usn', '')))
            sc.close()
            c.commit()
        c.close()
        return

    c.execute('''CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL,username TEXT UNIQUE NOT NULL,password TEXT NOT NULL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS students(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT,roll_no TEXT,department TEXT,attendance REAL,study_hours REAL,assignment_score REAL,previous_average REAL,prediction TEXT)''')
    cols = {r['name'] for r in c.execute('PRAGMA table_info(students)').fetchall()}
    for col in ('math_marks','physics_marks','cs_marks'):
        if col not in cols: c.execute(f'ALTER TABLE students ADD COLUMN {col} REAL DEFAULT 0')
    if 'subject_marks' not in cols: c.execute("ALTER TABLE students ADD COLUMN subject_marks TEXT DEFAULT '{}'")
    if 'usn' not in cols: c.execute('ALTER TABLE students ADD COLUMN usn TEXT')
    c.execute("UPDATE students SET usn = 'SAMPLE-USN-' || printf('%03d', CAST(TRIM(roll_no) AS INTEGER)) WHERE usn IS NULL OR TRIM(usn) = ''")
    c.commit(); c.close()

def logged_in(): return 'user_id' in session
def guard(): return None if logged_in() else redirect(url_for('login'))

SUBJECT_CATALOG = [
    'PIC (Programming in C)',
    'AIA (Artificial Intelligence & Applications)',
    'English',
    'Mathematics',
    'Physics',
]
OPEN_ELECTIVES = [
    'Electronics & Communication (EC)',
    'Mechanical (ME)',
]
ALL_SUBJECTS = SUBJECT_CATALOG + OPEN_ELECTIVES

SUBJECT_FEATURES = {
    'PIC (Programming in C)': 'pic_marks',
    'AIA (Artificial Intelligence & Applications)': 'aia_marks',
    'English': 'english_marks',
    'Mathematics': 'mathematics_marks',
    'Physics': 'physics_marks',
    'Electronics & Communication (EC)': 'open_elective_marks',
    'Mechanical (ME)': 'open_elective_marks',
}

def predict(a,s,ass,p,subjects):
    bundle=joblib.load(MODEL)
    model=bundle['model'] if isinstance(bundle,dict) else bundle
    features=bundle.get('features', []) if isinstance(bundle,dict) else []
    missing=[sub for sub in SUBJECT_CATALOG if sub not in subjects]
    electives=[sub for sub in OPEN_ELECTIVES if sub in subjects]
    if missing:
        raise ValueError('Please enter marks for all 5 compulsory subjects before prediction.')
    if len(electives) != 1:
        raise ValueError('Please enter marks for exactly one Open Elective: Electronics & Communication (EC) or Mechanical (ME).')
    values={
        'attendance':a, 'study_hours':s, 'assignment_score':ass, 'previous_average':p,
        **{SUBJECT_FEATURES[sub]: float(subjects[sub]) for sub in SUBJECT_CATALOG},
        'open_elective_marks': float(subjects[electives[0]])
    }
    row=np.array([[values[f] for f in features]]) if features else np.array([[a,s,ass,p] + [values[SUBJECT_FEATURES[sub]] for sub in SUBJECT_CATALOG]])
    return str(model.predict(row)[0])

def form_data():
    name=request.form['name'].strip(); roll=request.form['roll_no'].strip(); dept=request.form['department'].strip()
    a=float(request.form['attendance']); s=float(request.form['study_hours']); ass=float(request.form['assignment_score']); p=float(request.form['previous_average'])
    subject_json=request.form.get('subject_marks','{}')
    subjects=json.loads(subject_json) if subject_json else {}
    if not isinstance(subjects,dict): raise ValueError
    cleaned={}
    for subject, mark in subjects.items():
        subject=str(subject)
        if subject not in ALL_SUBJECTS: continue
        mark=float(mark)
        if not (0<=mark<=100): raise ValueError
        cleaned[subject]=mark
    missing=[sub for sub in SUBJECT_CATALOG if sub not in cleaned]
    electives=[sub for sub in OPEN_ELECTIVES if sub in cleaned]
    if missing:
        raise ValueError('Please enter marks for all 5 compulsory subjects before prediction.')
    if len(electives) != 1: