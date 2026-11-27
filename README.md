# 🎓 Student Performance Prediction System

A full-stack, machine-learning-powered web application built with **Flask**, **scikit-learn**, and **Neon PostgreSQL / SQLite** that predicts student academic performance (`Very Good`, `Good`, `Average`, `Poor`), generates personalized study recommendations, visualizes class analytics, supports multi-role administration, and exports individual PDF performance reports.


🌐 **Live demo App:** [https://spp-system.vercel.app/](https://spp-system.vercel.app/)  
🔐 **User / University Login:** [https://spp-system.vercel.app/login](https://spp-system.vercel.app/login)  
🛡️ **Head Admin Portal:** [https://spp-system.vercel.app/admin/login](https://spp-system.vercel.app/admin/login)


---

## ✨ Key Features

### 🤖 Machine Learning Performance Prediction
- Predicts student academic standing (**Very Good**, **Good**, **Average**, or **Poor**) using a trained **scikit-learn** classification model (`performance_model.pkl`).
- Evaluates **10 academic & behavioral parameters**:
  - **Core Metrics:** Attendance (%), Daily Study Hours, Assignment Score (%), and Previous Semester Average (%).
  - **5 Compulsory Subjects:** Programming in C (`PIC`), Artificial Intelligence & Applications (`AIA`), English, Mathematics, and Physics.
  - **1 Open Elective:** Electronics & Communication (`EC`) **or** Mechanical (`ME`).
- Automatically generates actionable, personalized academic improvement tips based on weak metrics.

### 🔐 Strict Multi-Role Architecture & Dedicated Portals
- **Head Admin (`admin`) — Dedicated `/admin/login` Portal:**
  - Restricted administrator login portal (`🔒 Admin Login`) separated from standard user login.
  - Defaults **Students** and **Predictions** lists cleanly to the primary university dataset (`Sharanbasva University`) while allowing one-click viewing of all combined records (`View All Students →`).
  - **Registered Accounts Panel** on the Admin Dashboard displaying all registered accounts (`University` and `User` roles), student counts per account, and direct per-user inspection controls:
    - **`View Dashboard`:** Opens any user's complete KPI summary, performance charts, and recent students.
    - **`View Students`:** Filters the student prediction table to a specific user's entries with a context banner and quick navigation controls.
    - **`View Analytics`:** Displays subject-wise averages, attendance distributions, and performance insights for a specific user.
    - **`Delete`:** Safely removes regular test/user accounts and their associated student records while protecting system accounts (`admin` and `suk_uni`).
- **University Account (`suk_uni` — Sharanbasva University):**
  - Preloaded with 36 baseline student records and full CRUD, analytics, and reporting capabilities.
- **Standard Users (Faculty / Evaluators):**
  - Isolated workspace starting with a clean dashboard (`0` students), allowing independent student creation, editing, prediction, and reporting without affecting other accounts.
- **Account Recovery:** Built-in **Forgot Password** and **Forgot Username** verification flows.

### 📊 Interactive Analytics, Search & Reporting
- **Dashboard & Analytics:** Real-time KPI cards, performance category distribution donut charts, attendance bracket breakdowns, and subject-wise average comparisons.
- **Context-Preserving Search & Filtering:** Instant search by Student Name, Roll Number, USN, or Department, plus filtering by predicted performance tier (`Very Good`, `Good`, `Average`, `Poor`) while preserving active Admin user filters.
- **Export Capabilities:**
  - **Individual PDF Reports:** Downloadable, formatted A4 Student Performance Reports generated via **ReportLab**.
  - **Bulk CSV Export:** One-click export of filtered student records and subject marks to `students.csv`.

---

## 🛠️ Tech Stack

| Layer | Technologies |
| :--- | :--- |
| **Backend** | Python 3, Flask, Werkzeug Security |
| **Machine Learning** | scikit-learn, NumPy, Joblib |
| **Database** | Neon Serverless PostgreSQL (`psycopg2-binary`) in production; SQLite (`database.db`) for local development |
| **Frontend** | HTML5, CSS3, Jinja2 Templates |
| **Reporting** | ReportLab (PDF generation), Python `csv` module |
| **Deployment** | Vercel (Serverless Python Runtime) + GitHub CI/CD |

---

## 📁 Project Structure

```text
spp_system/
├── app.py                  # Main Flask application, RBAC, Admin portals, and dual DB layer
├── model.py                # Machine learning model training script
├── performance_model.pkl   # Serialized scikit-learn prediction model
├── database.db             # Local SQLite database with sample seed data
├── requirements.txt        # Python dependencies for Vercel deployment
├── vercel.json             # Vercel serverless routing configuration
├── static/                 # CSS stylesheets, JS scripts, and assets
└── templates/              # Jinja2 HTML templates
    ├── base.html           # Shared layout and navigation bar (including Admin Login)
    ├── index.html          # Landing page
    ├── login.html          # Standard User & University login page
    ├── admin_login.html    # Dedicated Head Admin login portal
    ├── register.html       # New user registration page
    ├── dashboard.html      # Role-aware dashboard & Admin Registered Accounts table
    ├── students.html       # Student prediction directory with user context banner
    ├── analytics.html      # Visual performance & subject analytics with user banner
    ├── prediction.html     # Individual student prediction & PDF report view
    └── student_detail.html # Add / Edit student form
```

---

## 🚀 Local Setup & Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com && cd spp-system
   ```

2. **Create and activate a virtual environment (optional but recommended):**
   ```bash
   python -m venv venv
   # Windows:
   venv\Scripts\activate
   # macOS/Linux:
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Train the ML model (if `performance_model.pkl` is not present):**
   ```bash
   python model.py
   ```

5. **Run the application locally:**
   ```bash
   python app.py
   ```
   Open **`http://127.0.0.1:5000`** in your browser.

---

## ☁️ Production Deployment (Vercel + Neon PostgreSQL)

1. Push the repository to GitHub and import it into **Vercel**.
2. Create a PostgreSQL database on **Neon** and copy the connection string.
3. Add the following **Environment Variables** in Vercel (`Project Settings → Environment Variables`):
   - `DATABASE_URL`: Your Neon PostgreSQL connection string (`postgresql://...`)
   - `SECRET_KEY`: A strong random string for Flask session encryption
4. Deploy—the application automatically initializes the PostgreSQL schema and seeds baseline university records on first boot.


---

## 🔒 Data Privacy & Sample Dataset Note

> **Disclaimer:** All preloaded student records, marks, and university profiles (`suk_uni`) included in this application are **synthetic demonstration datasets** created solely for academic evaluation, testing, and visualization purposes. No real student data or personally identifiable information (PII) is stored or used.

---


## 👥 Project Team

| Name | Role & Contributions |
| :--- | :--- |
| **Priyanka Koraba** ([@priyankakoraba-ai](https://github.com)) | **Sole Developer & Architect** — End-to-end development of the Flask backend, ML prediction model, PostgreSQL database, UI, and Vercel deployment |
| **Manasa Pallapur** | **Testing & Academic Review** — Assisted with academic evaluation parameters and basic functional testing |
| **Anushree Gola** | **Presentation & Coordination** — Assisted with interface feedback, presentation slides, and team coordination |

