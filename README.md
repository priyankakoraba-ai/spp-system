# Student Performance Prediction System

A full-stack Flask application for predicting student performance, generating improvement recommendations, and presenting role-based dashboards and reports.

**Live demo:** https://spp-system.vercel.app  
**Student / university login:** https://spp-system.vercel.app/login  
**Head admin login:** https://spp-system.vercel.app/admin/login

> This is an educational prototype. Predictions are decision-support information, not a basis for grading, admissions, discipline, or other high-impact decisions about students.

## Features

- Predicts performance as `Very Good`, `Good`, `Average`, or `Poor` with a scikit-learn Random Forest model.
- Accepts attendance, study hours, assignment score, previous average, five compulsory subject marks, and one open elective mark.
- Generates recommendations for weak attendance, study, assignment, subject, or previous-performance metrics.
- Provides dashboards for head admins and university or standard users.
- Searches and filters students by name, roll number, USN, department, and predicted category.
- Displays attendance, performance-category, and subject-wise analytics.
- Exports individual reports as PDF and filtered student lists as CSV.
- Supports account registration, username recovery, and password recovery workflows.

## Technology

| Layer | Technology |
| --- | --- |
| Application | Python, Flask, Jinja2 |
| Machine learning | pandas, scikit-learn, NumPy, Joblib |
| Database | SQLite locally; PostgreSQL through `psycopg2-binary` in production |
| Authentication | Werkzeug password hashing and Flask sessions |
| Frontend | HTML5, CSS3, JavaScript |
| Reports | ReportLab and Python's `csv` module |
| Deployment | Vercel |

## How It Works

```text
Browser
  -> Flask routes and Jinja templates
  -> SQLite or PostgreSQL
  -> Flask input validation
  -> Random Forest model (performance_model.pkl)
  -> Performance category and recommendations
  -> Dashboard, PDF, or CSV
```

The application is initialized by `app.py`. On startup, it creates the required database tables and updates older SQLite schemas when new columns are missing.

## Model

`model.py` trains a `RandomForestClassifier` with 300 trees, a maximum depth of 8, balanced class weights, and a random seed of 42.

The model uses these 10 features:

- `attendance`
- `study_hours`
- `assignment_score`
- `previous_average`
- `pic_marks`
- `aia_marks`
- `english_marks`
- `mathematics_marks`
- `physics_marks`
- `open_elective_marks`

A student must provide all five compulsory subjects:

- Programming in C (PIC)
- Artificial Intelligence & Applications (AIA)
- English
- Mathematics
- Physics

The student must also provide exactly one open elective:

- Electronics & Communication (EC), or
- Mechanical (ME)

Training labels are derived from a weighted overall index:

- The mean of attendance, assignment score, previous average, all subject marks, and the open-elective mark is multiplied by 0.9.
- `study_hours` is clipped to 0–7, scaled to 0–100, and multiplied by 0.1.
- `Very Good`: at least 85
- `Good`: at least 70
- `Average`: at least 50
- `Poor`: below 50

The retraining script reports test accuracy and a classification report for an 80/20 split. It uses `random_state=42` and stratified sampling.

## Project Structure

```text
spp-system/
├── app.py                  # Flask routes, authentication, databases, reports, and RBAC
├── model.py                # Model training and category generation
├── performance_model.pkl   # Serialized trained model and feature list
├── requirements.txt        # Python dependencies
├── static/
│   └── style.css
├── templates/
│   ├── base.html
│   ├── dashboard.html
│   ├── prediction.html
│   ├── students.html
│   └── ...
└── .gitignore
```

`database.db` is created locally when needed and is ignored by Git. `student_data.csv` is training input and is also ignored by Git.

## Local Setup

Python 3.10 or newer is recommended.

1. Clone the repository:

   ```bash
   git clone https://github.com/priyankakoraba-ai/spp-system.git
   cd spp-system
   ```

2. Create and activate a virtual environment:

   ```bash
   python -m venv .venv
   ```

   Windows PowerShell:

   ```powershell
   .venv\Scripts\Activate.ps1
   ```

   macOS/Linux:

   ```bash
   source .venv/bin/activate
   ```

3. Install dependencies:

   ```bash
   python -m pip install -r requirements.txt
   ```

4. Start the application:

   ```bash
   python app.py
   ```

5. Open http://127.0.0.1:5000.

Without `DATABASE_URL`, the application uses `database.db` in the repository. The database schema is created automatically on startup.

For local Flask debug mode:

```bash
FLASK_DEBUG=1 python app.py
```

On Windows PowerShell, set the variable separately:

```powershell
$env:FLASK_DEBUG="1"
python app.py
```

## Retraining the Model

Place a `student_data.csv` file in the repository root. The file must contain:

```text
attendance
study_hours
assignment_score
previous_average
pic_marks
aia_marks
english_marks
mathematics_marks
physics_marks
open_elective_marks
```

Older CSV files may use `ec_marks` and `me_marks`; `model.py` converts those columns into `open_elective_marks`.

Run:

```bash
python model.py
```

This overwrites `performance_model.pkl` and adds a `performance` column to `student_data.csv`. Review the printed accuracy and classification report before deploying a newly trained model.

## Environment Variables

| Variable | Required | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | Production only | PostgreSQL connection string. `postgres://` URLs are normalized to `postgresql://`. |
| `SECRET_KEY` | Recommended | Flask session signing key. |
| `FLASK_DEBUG` | No | Set to `1` to enable Flask debug mode locally. |
| `VERCEL` | Set automatically | Tells the app to use `/tmp/database.db` when no `DATABASE_URL` is configured. |

Use a unique, random `SECRET_KEY` in deployed environments. If no key is configured locally, the app creates `secret.key`; if key creation fails, it falls back to a built-in development key.

Do not set a real database connection or secret in source control. For local environment files, use `.env` or your shell's environment-variable mechanism and keep it excluded by `.gitignore`.

## Vercel and PostgreSQL Deployment

1. Push the repository to GitHub and import it into Vercel.
2. Create a PostgreSQL database in Neon or another PostgreSQL provider.
3. Configure `DATABASE_URL` and `SECRET_KEY` in Vercel.
4. Deploy the application.

At startup, the app creates the PostgreSQL tables. If a local `database.db` is available and the PostgreSQL users or students tables are empty, it imports matching seed data.

For serverless deployments, SQLite in `/tmp` is ephemeral. Use PostgreSQL for persistent data.

## Data Privacy

All preloaded records and university profile data should be treated as demonstration data. The repository does not contain a canonical set of demo login credentials. Do not enter real student information or personally identifiable information into the public demo.

## Testing and Validation

The repository does not currently include an automated test suite. Before contributing a change, at least verify:

- Registration and login for a standard account.
- Head admin login and restricted dashboard access.
- Adding and editing a student with all required fields.
- Predictions for all four categories.
- PDF and CSV exports.
- SQLite startup from a fresh database.
- PostgreSQL startup and schema initialization when `DATABASE_URL` is configured.

Use synthetic data for every test.

## Development Context

This project is an academic software and machine-learning demonstration. AI-generated suggestions and implementation details should be reviewed and validated by the project owner and appropriate academic reviewers.

It is suitable for:

- Student and faculty demonstrations.
- Academic project presentations.
- Learning Flask, role-based access, SQLite/PostgreSQL, and scikit-learn.
- Testing prediction, analytics, reporting, and deployment workflows.

Model performance is dataset-dependent, and category labels derive from the scoring formula used in `model.py`. Reported test metrics should not be presented as evidence of real-world student-outcome accuracy without representative data and independent evaluation.

## Project Team

| Name | Role and Contributions |
| --- | --- |
| **Priyanka Koraba** ([@priyankakoraba-ai](https://github.com/priyankakoraba-ai)) | Developer and project lead: application architecture, Flask backend, machine learning, database, UI, documentation, and deployment. |
| **Manasa Pallapur** | Testing and academic review: academic evaluation parameters and basic functional testing. |
| **Anushree Gola** | Presentation and coordination: interface feedback and presentation materials. |

## License

This project is licensed under the [MIT License](LICENSE).
