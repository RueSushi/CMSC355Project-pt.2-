from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()  # ✅ This line MUST exist

class Medication(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    dosage = db.Column(db.String(100), nullable=False)
    frequency = db.Column(db.String(100), nullable=False)
    time_of_day = db.Column(db.String(100), nullable=False)
    patient_id = db.Column(db.String(100), nullable=False)

print("✅ models_file.py loaded")
