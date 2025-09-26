# app/__init__.py
import os
from pathlib import Path
import shutil
from flask import Flask
from flask_migrate import Migrate
from sqlalchemy.exc import SQLAlchemyError

from app.models import db
from app.auth import bp as auth_bp, init_login_manager
from app.courses import bp as courses_bp
from app.routes import bp as main_bp

def handle_sqlalchemy_error(err):
    msg = ('Возникла ошибка при подключении к базе данных. '
           'Повторите попытку позже.')
    return f'{msg} (Подробнее: {err})', 500

def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    disk_db = Path(app.instance_path) / "project.db"

    repo_db = Path(__file__).resolve().parent.parent / "instance" / "project.db"
    if not disk_db.exists() and repo_db.exists():
        shutil.copy(repo_db, disk_db)

    cfg_path = Path(app.root_path).parent / "config.py"
    if cfg_path.exists():
        app.config.from_pyfile(str(cfg_path))

    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{disk_db}"
    )
    app.config.setdefault("SQLALCHEMY_TRACK_MODIFICATIONS", False)
    app.config.setdefault("SECRET_KEY", os.getenv("SECRET_KEY", "dev-secret"))

    if test_config:
        app.config.update(test_config)

    db.init_app(app)
    Migrate(app, db)
    init_login_manager(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(courses_bp)
    app.register_blueprint(main_bp)
    app.errorhandler(SQLAlchemyError)(handle_sqlalchemy_error)

    return app
