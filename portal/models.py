from datetime import datetime

from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    password_plaintext = db.Column(db.String(255), nullable=True)
    anchor_name = db.Column(db.String(100), nullable=False)
    is_admin = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    created_entries = db.relationship(
        "ScheduleEntry",
        back_populates="creator",
        lazy="dynamic",
        cascade="all,delete",
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        self.password_plaintext = password

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class ScheduleEntry(db.Model):
    __tablename__ = "schedule_entries"

    id = db.Column(db.Integer, primary_key=True)
    live_date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    live_account = db.Column(db.String(120), nullable=False)
    anchor_name = db.Column(db.String(100), nullable=False)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    creator = db.relationship("User", back_populates="created_entries")
