Student Performance Prediction System

Subjects
--------
There are exactly 6 subjects for each student:
1. PIC (Programming in C)
2. AIA (Artificial Intelligence & Applications)
3. English
4. Mathematics
5. Physics
6. Open Elective: choose ONE of:
   - Electronics & Communication (EC)
   - Mechanical (ME)

The application enforces five compulsory subjects plus exactly one Open Elective.
EC and Mechanical cannot both be entered for the same student.

Run
---
pip install -r requirements.txt
python model.py


Open http://127.0.0.1:5000
