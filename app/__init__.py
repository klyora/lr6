import os
from pathlib import Path

from flask import Flask
from flask_migrate import Migrate
from sqlalchemy.exc import SQLAlchemyError

from app.models import db
from app.auth import bp as auth_bp, init_login_manager
from app.courses import bp as courses_bp
from app.routes import bp as main_bp


def handle_sqlalchemy_error(err):
    msg = (
        "Возникла ошибка при подключении к базе данных. "
        "Повторите попытку позже."
    )
    return f"{msg} (Подробнее: {err})", 500


def _apply_default_config(app: Flask) -> None:
    """Заполняем обязательные настройки, если их нет."""

    app.config.setdefault("SECRET_KEY", os.getenv("SECRET_KEY", "dev-secret-change-me"))

    db_uri = os.getenv("DATABASE_URL", app.config.get("SQLALCHEMY_DATABASE_URI"))
    if not db_uri:
        db_uri = "sqlite:///" + os.path.join(app.instance_path, "app.db")

    if db_uri.startswith("postgres://"):
        db_uri = db_uri.replace("postgres://", "postgresql://", 1)

    app.config["SQLALCHEMY_DATABASE_URI"] = db_uri
    app.config.setdefault("SQLALCHEMY_TRACK_MODIFICATIONS", False)
    app.config.setdefault("SQLALCHEMY_ENGINE_OPTIONS", {"pool_pre_ping": True})


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)

    try:
        from app.config import Config as AppConfig 
        app.config.from_object(AppConfig)
    except Exception:
        app.config.from_pyfile("config.py", silent=True)

    if test_config:
        app.config.from_mapping(test_config)

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    _apply_default_config(app)
    
    db.init_app(app)
    Migrate(app, db)
    init_login_manager(app)

    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(courses_bp, url_prefix="/courses")
    app.register_blueprint(main_bp)

    app.errorhandler(SQLAlchemyError)(handle_sqlalchemy_error)

    with app.app_context():
        from . import models 
        db.create_all()

    return app
