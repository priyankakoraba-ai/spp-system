# 🎓 Student Performance Prediction System

A full-stack Flask application that uses machine learning to predict student performance, generate improvement recommendations, and present role-based dashboards and reports.

**Live demo:** [https://spp-system.vercel.app](https://spp-system.vercel.app)

**User / university login:** [https://spp-system.vercel.app/login](https://spp-system.vercel.app/login)

**Head admin login:** [https://spp-system.vercel.app/admin/login](https://spp-system.vercel.app/admin/login)

## Features

- Predicts performance as `Very Good`, `Good`, `Average`, or `Poor` with a scikit-learn Random Forest model.
- Accepts attendance, study hours, assignment score, previous average, five compulsory subject marks, and one open-elective mark.
- Generates personalized recommendations for weak academic and behavioral metrics.
- Provides separate dashboards and workspaces for head admins, university accounts, and standard users.
- Filters and searches students by name, roll number, USN, department, and performance category.
- Displays attendance, performance-category, and subject-wise analytics.
- Exports individual student reports as PDF and filtered student data as CSV.
- Includes username and password recovery flows.

## Tech Stack

| Layer | Technologies |
| :--- | :--- |
| Backend | Python, Flask, Werkzeug |
| Machine learning | pandas, scikit-learn, NumPy, Joblib |
| Database | SQLite for local development; Neon PostgreSQL for production |
| Frontend | HTML5, CSS3, Jinja2 |
| Reports | ReportLab and Python's `csv` module |
| Deployment | Vercel |

## Project Structure

```text
spp-system/
├── app.py                  # Main Flask application, RBAC, Admin portals, and dual DB layer
├── model.py                # Machine learning model training script
├── performance_model.pkl   # Serialized scikit-learn prediction model
├── database.db             # Local SQLite database with sample seed data
├── requirements.txt        # Python dependencies for Vercel deployment
├── static/                 # CSS stylesheets, JS scripts, and assets
│   ├── style.css
│   └── images/
└── templates/              # Jinja2 HTML templates
    ├── base.html
    ├── index.html
    ├── login.html
    ├── admin_login.html
    ├── register.html
    ├── forgot_password.html
    ├── forgot_username.html
    ├── dashboard.html
    ├── students.html
    ├── analytics.html
    ├── prediction.html
    ├── student_detail.html
    └── add_student.html
```

## Local Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/priyankakoraba-ai/spp-system.git
   cd spp-system
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python -m venv venv
   ```
   Activate it with `venv\Scripts\activate` on Windows or `source venv/bin/activate` on macOS/Linux.

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application:**
   ```bash
   python app.py
   ```
   Open [http://127.0.0.1:5000](http://127.0.0.1:5000).

The repository includes `performance_model.pkl`, so model training is optional. To retrain it, place a `student_data.csv` file in the repository root with the feature columns required by `model.py`, then run:

```bash
python model.py
```

Set `FLASK_DEBUG=1` to enable local Flask debug mode.

## Vercel and Neon Deployment

1. Push the repository to GitHub and import it into Vercel.
2. Create a PostgreSQL database in Neon.
3. Configure these environment variables in Vercel:
   - `DATABASE_URL` — the Neon PostgreSQL connection string
   - `SECRET_KEY` — a strong random value used to sign Flask sessions
4. Deploy the application. It initializes the PostgreSQL schema and imports the local seed data on first startup when no users or students exist.

## Data Privacy

All preloaded student records and university profile data are synthetic demonstration datasets for academic evaluation and testing. Do not enter real student or personally identifiable information into the demo.

## Development and Use Context

This project was developed as an academic software and machine-learning demonstration. AI tools may be useful for assistance during coding, documentation, testing, and debugging, but the final implementation and results must be reviewed and validated by the project owner and appropriate academic reviewers.

The project is suitable for:

- student and faculty demonstrations;
- academic project presentations and projector-based demos;
- learning about Flask, role-based access, SQLite/PostgreSQL, and scikit-learn;
- testing basic prediction, analytics, reporting, and deployment workflows.

It is a prototype or educational system, not a production academic decision system. Predictions should not be used as the only basis for grading, admissions, discipline, or decisions about a student's future.

## Project Team

| Name | Role & Contributions |
| :--- | :--- |
| **Priyanka Koraba** ([@priyankakoraba-ai](https://github.com/priyankakoraba-ai)) | **Developer & Project Lead** — Application architecture, Flask backend, ML integration, database, UI, documentation, and deployment |
| **Manasa Pallapur** | **Testing & Academic Review** — Assisted with academic evaluation parameters and basic functional testing |
| **Anushree Gola** | **Presentation & Coordination** — Assisted with interface feedback, presentation slides, and team coordination |

## License

This project is licensed under the [MIT License](LICENSE).

