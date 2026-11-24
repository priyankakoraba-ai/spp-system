# 🎓 Student Performance Prediction System

A full-stack, machine-learning-powered web application built with **Flask**, **scikit-learn**, and **PostgreSQL / SQLite** that predicts student academic performance (`Very Good`, `Good`, `Average`, `Poor`), generates personalized study recommendations, visualizes class analytics, and exports individual PDF performance reports.

🌐 **Live Demo:** [https://vercel.app](https://vercel.app)

---

## ✨ Key Features

### 🤖 Machine Learning Performance Prediction
- Predicts student academic standing (**Very Good**, **Good**, **Average**, or **Poor**) using a trained **scikit-learn** classification model (`performance_model.pkl`).
- Evaluates **10 academic & behavioral parameters**:
  - **Core Metrics:** Attendance (%), Daily Study Hours, Assignment Score (%), and Previous Semester Average (%).
  - **5 Compulsory Subjects:** Programming in C (`PIC`), Artificial Intelligence & Applications (`AIA`), English, Mathematics, and Physics.
  - **1 Open Elective:** Electronics & Communication (`EC`) **or** Mechanical (`ME`).
- Automatically generates actionable, personalized academic improvement tips based on weak metrics.

### 🔐 Role-Based Multi-User Architecture
- **Head Admin (`admin`):**
  - System-wide visibility across all student records and analytics.
  - Dashboard **Registered Accounts** panel displaying all registered accounts (`University` and `User` roles), student counts, one-click **`View Students`** filtering per user, and protected **`Delete`** controls for regular user accounts.
- **University Account (`suk_uni` — Sharanbasva University):**
  - Preloaded with 36 baseline student records and full CRUD, analytics, and reporting capabilities.
- **Standard Users (Faculty / Evaluators):**
  - Isolated workspace starting with a clean dashboard (`0` students), allowing independent creation, editing, prediction, and reporting without affecting other accounts.
- **Account Recovery:** Built-in **Forgot Password** and **Forgot Username** verification flows.

### 📊 Interactive Analytics, Search & Reporting
- **Dashboard & Analytics:** Real-time KPI cards, performance category distribution charts, attendance bracket breakdowns, and subject-wise average performance comparisons.
- **Search & Filtering:** Instant search by Student Name, Roll Number, USN, or Department, plus filtering by predicted performance tier.
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
| **Frontend** | HTML5, CSS3, Jinja2 Templates, Chart.js |
| **Reporting** | ReportLab (PDF generation), Python `csv` module |
| **Deployment** | Vercel (Serverless Python Runtime) + GitHub CI/CD |

---

## 📁 Project Structure

```text
spp_system/
├── app.py                  # Main Flask application, routes, RBAC, and DB layer
├── model.py                # Machine learning model training script
├── performance_model.pkl   # Serialized scikit-learn prediction model
├── database.db             # Local SQLite database with sample seed data
├── requirements.txt        # Python dependencies for Vercel deployment
├── vercel.json             # Vercel serverless routing configuration
├── static/                 # CSS stylesheets, JS scripts, and assets
└── templates/              # Jinja2 HTML templates (dashboard, students, analytics, auth)
```

---

## 🚀 Local Setup & Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com
   cd spp-system
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
2. Create a free PostgreSQL database on **Neon** and copy the connection string.
3. Add the following **Environment Variables** in Vercel (`Project Settings → Environment Variables`):
   - `DATABASE_URL`: Your Neon PostgreSQL connection string (`postgresql://...`)
   - `SECRET_KEY`: A strong random string for Flask session encryption
4. Deploy—the application automatically initializes the PostgreSQL schema and seeds baseline university records on first boot.
