import datetime as dt
import os
import uuid

import pytest

from app import create_app
from app.models import db, User, Course, Review, Category, Image



@pytest.fixture(scope="session")
def app():
    app = create_app()
    app.config.update(
        TESTING=True,
        WTF_CSRF_ENABLED=False,
        SQLALCHEMY_DATABASE_URI="sqlite://",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        UPLOAD_FOLDER=os.path.abspath(os.getcwd()),
    )
    with app.app_context():
        db.create_all()
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()



@pytest.fixture(autouse=True)
def _app_ctx(app):
    ctx = app.app_context()
    ctx.push()
    try:
        yield
    finally:
        ctx.pop()


@pytest.fixture()
def client(app):
    return app.test_client()


def _now_utc():
    return dt.datetime.now(dt.timezone.utc)


def _mk_category(name: str = "Программирование"):
    cat = db.session.query(Category).filter_by(name=name).first()
    if cat:
        return cat
    cat = Category(name=name)
    db.session.add(cat)
    db.session.commit()
    return cat


def _mk_image():
    img = Image(
        id=str(uuid.uuid4()),
        file_name="bg.jpg",
        mime_type="image/jpeg",
        md5_hash=uuid.uuid4().hex,
        object_id=None,
        object_type=None,
        created_at=_now_utc(),
    )
    db.session.add(img)
    db.session.commit()
    return img


def _mk_user(
    *,
    login: str | None = None,
    first: str = "Иван",
    last: str = "Привалов",
    password: str = "qwerty",
):
    if login is None:
        login = f"user_{uuid.uuid4().hex[:10]}"

    u = User(first_name=first, last_name=last, login=login, created_at=_now_utc())
    u.set_password(password)
    db.session.add(u)
    db.session.commit()
    return u


def _mk_course(
    *,
    name="PYTHON С НУЛЯ",
    short_desc="Базовый курс по Python",
    full_desc="Полное описание Python курса",
    author: User,
):
    cat = db.session.query(Category).first() or _mk_category()
    img = _mk_image()
    c = Course(
        name=name,
        short_desc=short_desc,
        full_desc=full_desc,
        rating_sum=0,
        rating_num=0,
        category_id=cat.id,
        author_id=author.id,
        background_image_id=img.id,
        created_at=_now_utc(),
    )
    db.session.add(c)
    db.session.commit()
    return c


def _mk_review(
    *,
    course: Course,
    user: User,
    rating: int,
    text: str,
    created: dt.datetime | None = None,
):
    r = Review(
        rating=rating,
        text=text,
        created_at=created or _now_utc(),
        course_id=course.id,
        user_id=user.id,
    )
    db.session.add(r)

    course.rating_sum += rating
    course.rating_num += 1
    db.session.commit()
    return r


@pytest.fixture()
def user():
    return _mk_user()


@pytest.fixture()
def another_user_factory():
    def _factory(i: int):
        return _mk_user(login=f"user_{i}", first="User", last=str(i))
    return _factory


@pytest.fixture()
def course(user):
    return _mk_course(author=user)


@pytest.fixture()
def login(client, user):
    def _login(login: str | None = None, password: str = "qwerty"):
        if login is None:
            login = user.login
        return client.post("/login", data={"login": login, "password": password}, follow_redirects=True)
    return _login


@pytest.fixture()
def factories():
    return {
        "mk_user": _mk_user,
        "mk_course": _mk_course,
        "mk_review": _mk_review,
        "mk_category": _mk_category,
        "mk_image": _mk_image,
    }

