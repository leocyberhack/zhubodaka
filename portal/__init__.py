import os
from pathlib import Path

from flask import Flask
from sqlalchemy import inspect, text

from .extensions import db


def create_app():
    base_dir = Path(__file__).resolve().parent.parent
    storage_dir = base_dir / "storage"
    storage_dir.mkdir(parents=True, exist_ok=True)

    default_db_path = storage_dir / "anchor_schedule.db"
    database_url = os.getenv("DATABASE_URL", f"sqlite:///{default_db_path.as_posix()}")

    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "replace-this-before-deploy")
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)

    from .models import ScheduleEntry, User  # noqa: F401
    from .routes import portal_bp

    app.register_blueprint(portal_bp)

    with app.app_context():
        db.create_all()
        ensure_schema_updates()

    return app


def ensure_schema_updates():
    inspector = inspect(db.engine)
    tables = set(inspector.get_table_names())
    if "users" not in tables:
        return

    user_columns = {column["name"] for column in inspector.get_columns("users")}
    if "password_plaintext" not in user_columns:
        with db.engine.begin() as connection:
            connection.execute(text("ALTER TABLE users ADD COLUMN password_plaintext VARCHAR(255)"))
