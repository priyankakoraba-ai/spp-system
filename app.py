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
    """Supports both row['col'] and row indexing for SQLite and PostgreSQL."""
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
        if params:
            self._cur.execute(pg_sql, params)
        else:
            self._cur.execute(pg_sql)
        if is_insert:
            row = self._cur.fetchone()
            self.lastrowid = row['id'] if row else None
        return self
    def fetchone(self):
        row = self._cur.fetchone()
        if row is None:
            return None
        if len(row) == 1 and 'count' in row:
            return row['count']
        return DualRow(row)
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

def assign_sample_students_to_suk_uni(c):
    """Links the 36 sample records to suk_uni (Sharanbasva University) while keeping Head Admin view open."""
    uni_row = c.execute(
        "SELECT id FROM users WHERE LOWER(TRIM(username)) = ? OR LOWER(name) LIKE ? ORDER BY id ASC LIMIT 1",
        ('suk_uni', '%sharanbasva%')
    ).fetchone()
    if uni_row:
        c.execute("UPDATE students SET user_id = ? WHERE user_id = 1 OR user_id IS NULL", (uni_row['id'],))
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
            usn TEXT,
            user_id INTEGER DEFAULT 1
        )''')
        c.execute('ALTER TABLE students ADD COLUMN IF NOT EXISTS user_id INTEGER DEFAULT 1')
        c.commit()
        if os.path.exists(LOCAL_DB):
            sc = sqlite3.connect(LOCAL_DB)
            sc.row_factory = sqlite3.Row
            if c.execute('SELECT COUNT(*) FROM users').fetchone() == 0:
                for u in sc.execute('SELECT name, username, password FROM users').fetchall():
                    c.execute('INSERT INTO users(name, username, password) VALUES(?,?,?) ON CONFLICT DO NOTHING',
                              (u['name'], u['username'], u['password']))
            if c.execute('SELECT COUNT(*) FROM students').fetchone() == 0:
                for s in sc.execute('SELECT * FROM students ORDER BY id ASC').fetchall():
                    s_dict = dict(s)
                    c.execute('''INSERT INTO students(name,roll_no,department,attendance,study_hours,assignment_score,previous_average,prediction,math_marks,physics_marks,cs_marks,subject_marks,usn,user_id)
                                 VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,1)''',
                              (s_dict.get('name'), s_dict.get('roll_no'), s_dict.get('department'),
                               s_dict.get('attendance'), s_dict.get('study_hours'), s_dict.get('assignment_score'),
                               s_dict.get('previous_average'), s_dict.get('prediction'),
                               s_dict.get('math_marks', 0), s_dict.get('physics_marks', 0), s_dict.get('cs_marks', 0),
                               s_dict.get('subject_marks', '{}'), s_dict.get('usn', '')))
            sc.close()
        assign_sample_students_to_suk_uni(c)
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
    if 'user_id' not in cols: c.execute('ALTER TABLE students ADD COLUMN user_id INTEGER DEFAULT 1')
    assign_sample_students_to_suk_uni(c)
    c.execute("UPDATE students SET usn = 'SAMPLE-USN-' || printf('%03d', CAST(TRIM(roll_no) AS INTEGER)) WHERE usn IS NULL OR TRIM(usn) = ''")
    c.commit(); c.close()

def logged_in(): return 'user_id' in session
def guard(): return None if logged_in() else redirect(url_for('login'))

def is_admin():
    """Only 'admin' is the Head of the Project and sees all users and all student records."""
    uname = (session.get('username') or '').strip().lower()
    fname = (session.get('user_name') or '').strip().lower()
    return uname == 'admin' or fname == 'admin'

def owner_clause():
    if is_admin():
        uid_filter = request.args.get('user_id', '').strip()
        if uid_filter.isdigit():
            return 'user_id=?', [int(uid_filter)]
        return '1=1', []
    return 'user_id=?', [session.get('user_id')]


def get_student_for_user(c, sid):
    clause, params = owner_clause()
    return c.execute(f'SELECT * FROM students WHERE id=? AND {clause}', [sid] + params).fetchone()

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
        'open_elective_marks': float(subjects[next(iter(electives))])
    }
    row=np.array([[values[f] for f in features]]) if features else np.array([[a,s,ass,p] + [values[SUBJECT_FEATURES[sub]] for sub in SUBJECT_CATALOG]])
    return str(model.predict(row).item())

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
        raise ValueError('Please enter marks for exactly one Open Elective: Electronics & Communication (EC) or Mechanical (ME).')
    math=cleaned.get('Mathematics', 0); physics=cleaned.get('Physics', 0); cs=cleaned.get('PIC (Programming in C)', 0)
    return name,roll,dept,a,s,ass,p,math,physics,cs,cleaned

def tips(st):
    t=[]
    if st['attendance']<75: t.append('Maintain attendance above 75% by attending classes regularly.')
    if st['study_hours']<3: t.append('Increase study time to at least 3 hours per day.')
    if st['assignment_score']<60: t.append('Complete assignments on time and ask teachers for feedback.')
    if st['previous_average']<60: t.append('Revise basic topics and practise previous question papers.')
    if st['prediction']=='Very Good': return ['Excellent performance! Keep up the strong study routine and continue maintaining your consistency.']
    if st['prediction']=='Good': return ['Good work! Continue your current study routine and keep improving your weaker subjects.']
    if st['prediction']=='Average': return ['Focus on regular practice, attendance and improving subject-wise marks.']
    return t or ['Focus on the fundamentals, increase study time and seek support in difficult subjects.']

def count(c,label):
    clause, params = owner_clause()
    row = c.execute(f'SELECT COUNT(*) FROM students WHERE prediction=? AND {clause}', [label] + params).fetchone()
    return row if isinstance(row, int) else row['count']

def performance_metrics(student):
    try:
        marks = json.loads(student['subject_marks'] or '{}')
    except (TypeError, json.JSONDecodeError):
        marks = {}
    if not isinstance(marks, dict):
        marks = {}
    values = [float(v) for v in marks.values()]
    total = sum(values)
    max_marks = len(values) * 100
    overall_percentage = (total / max_marks * 100) if max_marks else 0
    overall_average = (sum(values) / len(values)) if values else 0
    return {
        'total_marks': total,
        'max_marks': max_marks,
        'overall_percentage': overall_percentage,
        'overall_average': overall_average,
        'subject_count': len(values),
    }

def build_student_rows(rows):
    return [(row, performance_metrics(row)) for row in rows]

@app.route('/')
def home(): return render_template('index.html')

@app.route('/register',methods=['GET','POST'])
def register():
    if request.method=='POST':
        name=request.form['name'].strip(); username=request.form['username'].strip(); password=request.form['password']
        if password!=request.form['confirm_password']: flash('Passwords do not match.','error'); return redirect(url_for('register'))
        if len(password)<6: flash('Password must contain at least 6 characters.','error'); return redirect(url_for('register'))
        c=db()
        try:
            c.execute('INSERT INTO users(name,username,password) VALUES(?,?,?)',(name,username,generate_password_hash(password)))
            assign_sample_students_to_suk_uni(c)
            c.commit()
        except IntegrityErrors: flash('Username already exists.','error'); return redirect(url_for('register'))
        finally: c.close()
        flash('Registration successful. Please login.','success'); return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        registered_name = request.form.get('registered_name', '').strip()
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not username or not registered_name:
            flash('Please enter both your username and registered full name.', 'error')
            return redirect(url_for('forgot_password'))
        if len(new_password) < 6:
            flash('New password must contain at least 6 characters.', 'error')
            return redirect(url_for('forgot_password'))
        if new_password != confirm_password:
            flash('Passwords do not match.', 'error')
            return redirect(url_for('forgot_password'))

        c = db()
        user = c.execute(
            'SELECT * FROM users WHERE username=? AND LOWER(TRIM(name))=LOWER(TRIM(?))',
            (username, registered_name)
        ).fetchone()
        if not user:
            c.close()
            flash('Username and registered full name do not match an account.', 'error')
            return redirect(url_for('forgot_password'))

        c.execute(
            'UPDATE users SET password=? WHERE id=?',
            (generate_password_hash(new_password), user['id'])
        )
        c.commit()
        c.close()
        flash('Password reset successfully. Please login with your new password.', 'success')
        return redirect(url_for('login'))

    return render_template('forgot_password.html')

@app.route('/forgot-username', methods=['GET','POST'])
def forgot_username():
    username = None
    if request.method == 'POST':
        name = request.form['name'].strip()
        c = db()
        users = c.execute('SELECT username FROM users WHERE LOWER(name)=LOWER(?)', (name,)).fetchall()
        c.close()
        if len(users) == 1:
            username = users.pop()['username']
        elif len(users) == 0:
            flash('No registered account was found with that full name.', 'error')
        else:
            flash('More than one account uses this full name. Please contact the administrator to identify the account.', 'error')
    return render_template('forgot_username.html', username=username)

@app.route('/login',methods=['GET','POST'])
def login():
    if request.method=='POST':
        c=db(); u=c.execute('SELECT * FROM users WHERE username=?',(request.form['username'].strip(),)).fetchone(); c.close()
        if u and check_password_hash(u['password'],request.form['password']):
            session['user_id']=u['id']; session['user_name']=u['name']; session['username']=u['username']
            return redirect(url_for('dashboard'))
        flash('Invalid username or password.','error')
    return render_template('login.html')

@app.route('/logout')
def logout(): session.clear(); return redirect(url_for('home'))

@app.route('/dashboard')
def dashboard():
    g=guard()
    if g:return g
    c=db(); clause, params = owner_clause()
    total_row = c.execute(f'SELECT COUNT(*) FROM students WHERE {clause}', params).fetchone()
    total = total_row if isinstance(total_row, int) else total_row['count']
    very_good=count(c,'Very Good'); good=count(c,'Good'); average=count(c,'Average'); poor=count(c,'Poor')
    rows=c.execute(f'SELECT subject_marks, previous_average FROM students WHERE {clause}', params).fetchall()
    recent_scores=[]
    for row in rows:
        try:
            marks=json.loads(row['subject_marks'] or '{}')
        except (TypeError, json.JSONDecodeError):
            marks={}
        if isinstance(marks, dict) and marks:
            try:
                vals=[float(v) for v in marks.values()]
                current=(sum(vals)/(len(vals)*100))*100 if vals else None
            except (TypeError, ValueError):
                current=None
            if current is not None:
                recent_scores.append(current)
                continue
        recent_scores.append(float(row['previous_average'] or 0))
    avg=sum(recent_scores)/len(recent_scores) if recent_scores else 0
    recent=c.execute(f'''SELECT * FROM (SELECT * FROM students WHERE {clause} ORDER BY id DESC LIMIT 5) AS latest_students ORDER BY CAST(TRIM(roll_no) AS INTEGER) ASC, roll_no COLLATE NOCASE ASC, id ASC''', params).fetchall()
    attendance_rows=c.execute(f'SELECT attendance FROM students WHERE {clause}', params).fetchall()
    attendance_values=[]
    for ar in attendance_rows:
        try:
            attendance_values.append(float(ar['attendance'] or 0))
        except (TypeError, ValueError): attendance_values.append(0.0)
    bins=[sum(1 for v in attendance_values if v < 70),sum(1 for v in attendance_values if 70 <= v < 80),sum(1 for v in attendance_values if 80 <= v < 90),sum(1 for v in attendance_values if v >= 90)]
    attendance_total=len(attendance_values) or 1
    attendance_pct=[round(v*100/attendance_total,1) for v in bins]
    viewing_user = None
    uid_filter = request.args.get('user_id', '').strip()
    if is_admin() and uid_filter.isdigit():
        viewing_user = c.execute('SELECT id, name, username FROM users WHERE id=?', (int(uid_filter),)).fetchone()
    all_users = c.execute('''
        SELECT u.id, u.name, u.username, COUNT(s.id) AS student_count
        FROM users u
        LEFT JOIN students s ON s.user_id = u.id
        WHERE LOWER(TRIM(u.username)) != 'admin'
        GROUP BY u.id, u.name, u.username
        ORDER BY u.id ASC
    ''').fetchall() if (is_admin() and not viewing_user) else []

    c.close()
    perf_total=total or 1
    perf_pct=[round(very_good*100/perf_total,1),round(good*100/perf_total,1),round(average*100/perf_total,1),round(poor*100/perf_total,1)]
    return render_template('dashboard.html',total=total,very_good=very_good,good=good,average=average,poor=poor,score=round(avg,1),students=recent,attendance_bins=bins,attendance_pct=attendance_pct,perf_pct=perf_pct,is_admin=is_admin(),all_users=all_users,viewing_user=viewing_user)


@app.route('/add-student',methods=['GET','POST'])
def add_student():
    g=guard()
    if g:return g
    if request.method=='POST':
        try: name,roll,dept,a,s,ass,p,math,physics,cs,subjects=form_data(); result=predict(a,s,ass,p,subjects)
        except FileNotFoundError: flash('Model file missing. Run: python model.py','error'); return render_template('add_student.html',student=None)
        except (ValueError,KeyError) as e:
            flash(str(e) if str(e).startswith('Please enter marks') else 'Please enter valid values.','error'); return render_template('add_student.html',student=None)
        usn=request.form.get('usn','').strip()
        uid=session.get('user_id', 1)
        c=db(); cur=c.execute('''INSERT INTO students(name,roll_no,department,attendance,study_hours,assignment_score,previous_average,prediction,math_marks,physics_marks,cs_marks,subject_marks,usn,user_id) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',(name,roll,dept,a,s,ass,p,result,math,physics,cs,json.dumps(subjects),usn,uid)); sid=cur.lastrowid; c.commit(); c.close(); return redirect(url_for('prediction',sid=sid))
    return render_template('add_student.html',student=None)

@app.route('/edit/<int:sid>',methods=['GET','POST'])
def edit_student(sid):
    g=guard()
    if g:return g
    c=db(); st=get_student_for_user(c, sid)
    if not st:c.close();flash('Student not found.','error');return redirect(url_for('students'))
    if request.method=='POST':
        try: name,roll,dept,a,s,ass,p,math,physics,cs,subjects=form_data(); result=predict(a,s,ass,p,subjects)
        except (ValueError,KeyError) as e: c.close();flash(str(e) if str(e).startswith('Please enter marks') else 'Please enter valid values.','error');return redirect(url_for('edit_student',sid=sid))
        usn=request.form.get('usn','').strip()
        c.execute('''UPDATE students SET name=?,roll_no=?,department=?,attendance=?,study_hours=?,assignment_score=?,previous_average=?,prediction=?,math_marks=?,physics_marks=?,cs_marks=?,subject_marks=?,usn=? WHERE id=?''',(name,roll,dept,a,s,ass,p,result,math,physics,cs,json.dumps(subjects),usn,sid));c.commit();c.close();return redirect(url_for('prediction',sid=sid))
    c.close()

    try:
        existing_marks = json.loads(st['subject_marks'] or '{}')
        if not isinstance(existing_marks, dict):
            existing_marks = {}
    except (TypeError, json.JSONDecodeError):
        existing_marks = {}

    return render_template(
        'add_student.html',
        student=st,
        existing_marks=existing_marks
    )

@app.route('/prediction')
def prediction_home():
    g=guard()
    if g:return g
    rows, q, pf = search_students()
    return render_template('students.html', students=build_student_rows(rows), q=q, pred_filter=pf)

@app.route('/prediction/<int:sid>')
def prediction(sid):
    g=guard()
    if g:return g
    c=db(); st=get_student_for_user(c, sid);c.close()
    if not st: flash('Student not found.','error'); return redirect(url_for('students'))
    return render_template('prediction.html',student=st,tips=tips(st),subject_marks=json.loads(st['subject_marks'] or '{}'),metrics=performance_metrics(st))

@app.route('/student/<int:sid>/report.pdf')
def export_student_pdf(sid):
    g=guard()
    if g:return g
    c=db(); st=get_student_for_user(c, sid); c.close()
    if not st:
        flash('Student not found.','error')
        return redirect(url_for('students'))
    try:
        marks=json.loads(st['subject_marks'] or '{}')
        if not isinstance(marks,dict): marks={}
    except (TypeError,ValueError):
        marks={}
    metrics=performance_metrics(st)
    generated=datetime.now().strftime('%d %B %Y, %I:%M %p')
    buffer=io.BytesIO()
    doc=SimpleDocTemplate(buffer,pagesize=A4,rightMargin=18*mm,leftMargin=18*mm,topMargin=18*mm,bottomMargin=18*mm,title='Student Performance Report')
    styles=getSampleStyleSheet()
    styles.add(ParagraphStyle(name='ReportTitle',parent=styles['Title'],fontName='Helvetica-Bold',fontSize=18,leading=22,textColor=colors.HexColor('#1D4ED8'),alignment=TA_CENTER,spaceAfter=4))
    styles.add(ParagraphStyle(name='ReportSubtitle',parent=styles['Normal'],fontSize=9,leading=12,textColor=colors.HexColor('#64748B'),alignment=TA_CENTER,spaceAfter=12))
    styles.add(ParagraphStyle(name='SectionHeader',parent=styles['Heading2'],fontSize=11,leading=14,textColor=colors.HexColor('#1E3A8A'),spaceBefore=8,spaceAfter=6))
    styles.add(ParagraphStyle(name='ReportNote',parent=styles['Normal'],fontSize=8,leading=11,textColor=colors.HexColor('#64748B')))
    story=[Paragraph('STUDENT PERFORMANCE REPORT',styles['ReportTitle']),Paragraph('Student Performance Prediction System',styles['ReportSubtitle'])]
    info=[['Student Name',st['name'] or '—','USN',st['usn'] or '—'],['Roll Number',st['roll_no'] or '—','Department',st['department'] or '—']]
    t=Table(info,colWidths=[28*mm,62*mm,24*mm,54*mm])
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),colors.HexColor('#EFF6FF')),('TEXTCOLOR',(0,0),(-1,-1),colors.HexColor('#1F2937')),('FONTNAME',(0,0),(-1,-1),'Helvetica'),('FONTNAME',(0,0),(0,-1),'Helvetica-Bold'),('FONTNAME',(2,0),(2,-1),'Helvetica-Bold'),('FONTSIZE',(0,0),(-1,-1),9),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('GRID',(0,0),(-1,-1),0.4,colors.HexColor('#D1D5DB')),('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7)]))
    story += [t,Paragraph('Subject-wise Marks',styles['SectionHeader'])]
    subject_data=[['Subject','Marks Obtained','Percentage']]
    for subject,mark in marks.items():
        try: val=float(mark)
        except (TypeError,ValueError): continue
        if 0 <= val <= 100: subject_data.append([str(subject),f'{val:.2f} / 100',f'{val:.2f}%'])
    if len(subject_data)==1: subject_data.append(['No subject marks recorded','—','—'])
    subject_table=Table(subject_data,colWidths=[100*mm,36*mm,32*mm],repeatRows=1)
    subject_table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#2563EB')),('TEXTCOLOR',(0,0),(-1,0),colors.white),('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),('FONTNAME',(0,1),(-1,-1),'Helvetica'),('FONTSIZE',(0,0),(-1,-1),9),('GRID',(0,0),(-1,-1),0.4,colors.HexColor('#D1D5DB')),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#F8FAFC')]),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6)]))
    story += [subject_table,Paragraph('Performance Summary',styles['SectionHeader'])]
    summary=[['Total Marks',f"{metrics['total_marks']:.0f} / {metrics['max_marks']}"],['Overall Percentage',f"{metrics['overall_percentage']:.2f}%"],['Attendance',f"{float(st['attendance'] or 0):.1f}%"],['Study Hours',f"{float(st['study_hours'] or 0):.2f} hours/day"],['Assignment Score',f"{float(st['assignment_score'] or 0):.2f}%"],['Previous Average',f"{float(st['previous_average'] or 0):.2f}%"]]
    summary_table=Table(summary,colWidths=[54*mm,114*mm])
    summary_table.setStyle(TableStyle([('BACKGROUND',(0,0),(0,-1),colors.HexColor('#EFF6FF')),('FONTNAME',(0,0),(0,-1),'Helvetica-Bold'),('FONTNAME',(1,0),(1,-1),'Helvetica'),('FONTSIZE',(0,0),(-1,-1),9),('GRID',(0,0),(-1,-1),0.4,colors.HexColor('#D1D5DB')),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('LEFTPADDING',(0,0),(-1,-1),6),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6)]))
    story += [summary_table,Paragraph('Prediction Result',styles['SectionHeader'])]
    prediction_cell=Table([[Paragraph(f"<b>{html_escape(str(st['prediction'] or 'Not available').upper())}</b>",styles['Normal'])]],colWidths=[168*mm])
    prediction_cell.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),colors.HexColor('#DBEAFE')),('BOX',(0,0),(-1,-1),0.8,colors.HexColor('#93C5FD')),('ALIGN',(0,0),(-1,-1),'CENTER'),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('TOPPADDING',(0,0),(-1,-1),10),('BOTTOMPADDING',(0,0),(-1,-1),10)]))
    story.append(prediction_cell)
    tip_list=tips(st)
    story += [Paragraph('Suggestions',styles['SectionHeader']),Paragraph('• '+('<br/>• '.join(tip_list)),styles['Normal']),Spacer(1,10),Paragraph(f'Report generated: {generated}',styles['ReportNote']),Spacer(1,4),Paragraph('This report contains a machine-learning-based prediction for academic guidance. It is an estimate and does not guarantee future academic performance.',styles['ReportNote'])]
    doc.build(story)
    buffer.seek(0)
    safe_name=''.join(ch for ch in (st['name'] or 'Student') if ch.isalnum() or ch in (' ','-','_')).strip().replace(' ','_')
    filename=f'{safe_name or "Student"}_Performance_Report.pdf'
    return send_file(buffer,mimetype='application/pdf',as_attachment=True,download_name=filename)

@app.route('/student/<int:sid>')
def student_detail(sid):
    g=guard()
    if g:return g
    c=db(); st=get_student_for_user(c, sid);c.close()
    if not st: flash('Student not found.','error'); return redirect(url_for('students'))

def search_students():
    clause, params = owner_clause()
    uid_filter = request.args.get('user_id', '').strip()
    if is_admin():
        if uid_filter.isdigit():
            clause = 'user_id=?'
            params = [int(uid_filter)]
        elif uid_filter != 'all':
            c_tmp = db()
            uni_row = c_tmp.execute(
                "SELECT id FROM users WHERE LOWER(TRIM(username)) = ? OR LOWER(name) LIKE ? ORDER BY id ASC LIMIT 1",
                ('suk_uni', '%sharanbasva%')
            ).fetchone()
            c_tmp.close()
            if uni_row:
                clause = 'user_id=?'
                params = [uni_row['id']]
    q=request.args.get('q','').strip(); pf=request.args.get('prediction','').strip(); sql=f'SELECT * FROM students WHERE {clause}'
    if q: sql+=' AND (name LIKE ? OR roll_no LIKE ? OR usn LIKE ? OR department LIKE ?)'; params += [f'%{q}%']*4
    if pf in ('Very Good','Good','Average','Poor'): sql+=' AND prediction=?';params.append(pf)
    c=db(); rows=c.execute(sql+' ORDER BY CAST(TRIM(roll_no) AS INTEGER) ASC, roll_no COLLATE NOCASE ASC, id ASC',params).fetchall();c.close();return rows,q,pf
@app.route('/students')
def students():
    g=guard()
    if g:return g
    rows, q, pf = search_students()
    viewing_user = None
    uid_filter = request.args.get('user_id', '').strip()
    if is_admin() and uid_filter.isdigit():
        c = db()
        viewing_user = c.execute('SELECT id, name, username FROM users WHERE id=?', (int(uid_filter),)).fetchone()
        c.close()
    return render_template('students.html', students=build_student_rows(rows), q=q, pred_filter=pf, viewing_user=viewing_user)

@app.route('/export')
def export_csv():
    g=guard()
    if g:return g
    rows,_,_=search_students();out=io.StringIO();w=csv.writer(out)
    headers=['Name','Roll No','USN','Department','PIC','AIA','English','Mathematics','Physics','Open Elective','Attendance','Study Hours','Assignment Score','Previous Average','Prediction']
    w.writerow(headers)
    for r in rows:
        marks=json.loads(r['subject_marks'] or '{}')
        elective=marks.get('Electronics & Communication (EC)', marks.get('Mechanical (ME)', ''))
        w.writerow([r['name'],r['roll_no'],r['usn'] or '',r['department'],marks.get('PIC (Programming in C)',''),marks.get('AIA (Artificial Intelligence & Applications)',''),marks.get('English',''),marks.get('Mathematics',''),marks.get('Physics',''),elective,r['attendance'],r['study_hours'],r['assignment_score'],r['previous_average'],r['prediction']])
    return Response(out.getvalue(),mimetype='text/csv',headers={'Content-Disposition':'attachment; filename=students.csv'})

@app.route('/delete/<int:sid>',methods=['POST'])
def delete(sid):
    g=guard()
    if g:return g
    c=db(); clause, params = owner_clause()
    c.execute(f'DELETE FROM students WHERE id=? AND {clause}', [sid] + params)
    c.commit();c.close();flash('Student deleted.','success');return redirect(url_for('students'))

@app.route('/delete-user/<int:uid>', methods=['POST'])
def delete_user(uid):
    g = guard()
    if g: return g
    if not is_admin():
        flash('Unauthorized access.', 'error')
        return redirect(url_for('dashboard'))
    c = db()
    target = c.execute('SELECT id, username FROM users WHERE id=?', (uid,)).fetchone()
    if not target:
        c.close()
        flash('User not found.', 'error')
        return redirect(url_for('dashboard'))
    if (target['username'] or '').strip().lower() in ('admin', 'suk_uni'):
        c.close()
        flash('Protected system accounts (admin and suk_uni) cannot be deleted.', 'error')
        return redirect(url_for('dashboard'))
    c.execute('DELETE FROM students WHERE user_id=?', (uid,))
    c.execute('DELETE FROM users WHERE id=?', (uid,))
    c.commit()
    c.close()
    flash(f"User '{target['username']}' and their student records have been deleted.", 'success')
    return redirect(url_for('dashboard'))

@app.route('/analytics')
def analytics():
    g=guard()
    if g:return g
    c=db(); clause, params = owner_clause()
    very_good=count(c,'Very Good');good=count(c,'Good');average=count(c,'Average');poor=count(c,'Poor');total=very_good+good+average+poor
    rows=c.execute(f'SELECT subject_marks, attendance FROM students WHERE {clause}', params).fetchall()
    attendance_values=[]
    for r in rows:
        try:
            value=float(r['attendance'] or 0)
            if 0 <= value <= 100: attendance_values.append(value)
        except (TypeError, ValueError):
            continue
    attendance_total=len(attendance_values)
    attendance_counts=[sum(1 for v in attendance_values if v >= 90),sum(1 for v in attendance_values if 75 <= v < 90),sum(1 for v in attendance_values if v < 75)]
    attendance_pct=[round(n*100/attendance_total,1) if attendance_total else 0 for n in attendance_counts]
    avg_attendance=round(sum(attendance_values)/attendance_total,1) if attendance_total else 0
    viewing_user = None
    uid_filter = request.args.get('user_id', '').strip()
    if is_admin() and uid_filter.isdigit():
    viewing_user = c.execute('SELECT id, name, username FROM users WHERE id=?', (int(uid_filter),)).fetchone()

    c.close()
    subject_names=['PIC (Programming in C)','AIA (Artificial Intelligence & Applications)','English','Mathematics','Physics','Electronics & Communication (EC)','Mechanical (ME)']
    sums={name:[] for name in subject_names}
    for r in rows:
        try: marks=json.loads(r['subject_marks'] or '{}')
        except (TypeError, ValueError): marks={}
        for name in subject_names:
            try:
                val=float(marks[name])
                if 0 <= val <= 100: sums[name].append(val)
            except (KeyError, TypeError, ValueError): pass
    subject_avgs=[]
    for name in subject_names[:5]:
        vals=sums[name]; subject_avgs.append(round(sum(vals)/len(vals),1) if vals else 0)
    elective_values=sums['Electronics & Communication (EC)'] + sums['Mechanical (ME)']
    subject_avgs.append(round(sum(elective_values)/len(elective_values),1) if elective_values else 0)
    performance_pct=[round(n*100/total,1) if total else 0 for n in [very_good,good,average,poor]]
    return render_template('analytics.html',very_good=very_good,good=good,average=average,poor=poor,total=total,subject_avgs=subject_avgs,attendance_counts=attendance_counts,attendance_pct=attendance_pct,attendance_total=attendance_total,avg_attendance=avg_attendance,performance_pct=performance_pct,viewing_user=viewing_user)


init()

if __name__=='__main__':
    if not os.path.exists(MODEL): print('Model file missing. Run: python model.py')
    app.run(host='127.0.0.1',port=5000,debug=os.environ.get('FLASK_DEBUG')=='1')