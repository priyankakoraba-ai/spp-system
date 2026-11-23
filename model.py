"""Train the student performance model.

The model uses five compulsory subjects plus ONE Open Elective. The Open
Elective can be Electronics & Communication (EC) OR Mechanical (ME); it is
stored as a single feature called open_elective_marks.
"""
import pandas as pd
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report

FEATURES = [
    'attendance', 'study_hours', 'assignment_score', 'previous_average',
    'pic_marks', 'aia_marks', 'english_marks', 'mathematics_marks',
    'physics_marks', 'open_elective_marks'
]

data = pd.read_csv('student_data.csv')

# Older training CSVs contain separate EC and ME columns. Treat them as
# alternatives for the one Open Elective feature. If both are present in a
# training row, their mean represents the elective score for that row.
if 'open_elective_marks' not in data.columns:
    ec = pd.to_numeric(data.get('ec_marks', 0), errors='coerce').fillna(0)
    me = pd.to_numeric(data.get('me_marks', 0), errors='coerce').fillna(0)
    data['open_elective_marks'] = (ec + me) / 2

X = data[FEATURES].copy()

study_scaled = X['study_hours'].clip(0, 7) / 7 * 100
score_columns = [
    'attendance', 'assignment_score', 'previous_average',
    'pic_marks', 'aia_marks', 'english_marks', 'mathematics_marks',
    'physics_marks', 'open_elective_marks'
]
overall_index = X[score_columns].mean(axis=1) * 0.9 + study_scaled * 0.1

def category(score):
    if score >= 85:
        return 'Very Good'
    if score >= 70:
        return 'Good'
    if score >= 50:
        return 'Average'
    return 'Poor'

y = overall_index.apply(category)
data['performance'] = y
# Keep the training CSV transparent and portable while retaining old EC/ME
# columns if they already exist.
data.to_csv('student_data.csv', index=False)

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.20, random_state=42, stratify=y
)
model = RandomForestClassifier(
    n_estimators=300, max_depth=8, random_state=42, class_weight='balanced'
)
model.fit(X_train, y_train)
pred = model.predict(X_test)
print(f'Model accuracy on test split: {accuracy_score(y_test, pred) * 100:.2f}%')
print(classification_report(y_test, pred, zero_division=0))
joblib.dump({'model': model, 'features': FEATURES}, 'performance_model.pkl')
print('Saved performance_model.pkl with Open Elective (EC or ME) support.')
