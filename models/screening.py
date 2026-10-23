from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Screening(db.Model):
    __tablename__ = 'screenings'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=True)
    patient_type = db.Column(db.String(20), default='self')

    cough = db.Column(db.Boolean, nullable=False)
    cough_duration = db.Column(db.Boolean, nullable=False)
    night_sweats = db.Column(db.Boolean, nullable=False)
    weight_loss = db.Column(db.Boolean, nullable=False)
    coughing_blood = db.Column(db.Boolean, nullable=False)
    fever = db.Column(db.Boolean, nullable=False)
    fatigue = db.Column(db.Boolean, nullable=False)
    chest_pain = db.Column(db.Boolean, nullable=False)

    risk_level = db.Column(db.String(20), nullable=False)
    recommendation = db.Column(db.Text, nullable=False)
    language_selected = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
