import os
import shutil
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


def _ensure_db_exists(app):
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    runtime_db = os.path.join(app.instance_path, "project.db")
    app.config.setdefault("SQLALCHEMY_DATABASE_URI", f"sqlite:///{runtime_db}")
    app.config.setdefault("SQLALCHEMY_TRACK_MODIFICATIONS", False)

    repo_db = os.path.abspath(os.path.join(app.root_path, "..", "instance", "project.db"))

    if not os.path.exists(runtime_db) and os.path.exists(repo_db):
        shutil.copy2(repo_db, runtime_db)

    if not os.path.exists(runtime_db):
        with app.app_context():
            from . import models 
            db.create_all()


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)

    try:
        app.config.from_pyfile("config.py")
    except FileNotFoundError:
        pass

    if test_config:
        app.config.from_mapping(test_config)

    _ensure_db_exists(app)

    db.init_app(app)
    Migrate(app, db)

    init_login_manager(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(courses_bp)
    app.register_blueprint(main_bp)

    app.errorhandler(SQLAlchemyError)(handle_sqlalchemy_error)

    return app
