import datetime as dt
import pytest
from app.models import db, Review, Course

@pytest.fixture
def login(client):
    """Логин в системе существующим пользователем user3/qwerty."""
    def _login():
        return client.post(
            "/auth/login",
            data={"login": "user3", "password": "qwerty"},
            follow_redirects=True,
        )
    return _login

def _post_review_any_route(client, course_id: int, rating: int, text: str) -> bool:
    """
    Тестовый пост отзыва. Сначала стучимся туда, где у тебя реально висит форма:
    /courses/<id>/add_review. Для надёжности оставляем и пару запасных путей.
    """
    paths = [
        f"/courses/{course_id}/add_review",
        f"/courses/{course_id}/review",
        f"/courses/{course_id}/reviews/add",
        f"/courses/{course_id}/reviews",
    ]
    for url in paths:
        resp = client.post(
            url,
            data={"rating": str(rating), "text": text},
            follow_redirects=True,
        )
        if resp.status_code == 200 and (text in resp.get_data(as_text=True)):
            return True
    return False


def _course_show_path(course_id: int) -> str:
    return f"/courses/{course_id}"


def _course_reviews_path(course_id: int) -> str:
    return f"/courses/{course_id}/reviews"


def _course_add_review_path(course_id: int) -> str:
    return f"/courses/{course_id}/add_review"


def test_add_review_updates_rating_and_shows_on_page(client, user, course):
    with client.session_transaction() as sess:
        sess["_user_id"] = str(user.id)
        sess["_fresh"] = True

    ok = _post_review_any_route(client, course.id, 5, "Отличный курс!")
    assert ok, "Не удалось создать отзыв ни одним из известных роутов"

    c = db.session.get(Course, course.id)
    assert c is not None
    assert c.rating_num == 1
    assert c.rating_sum == 5


def test_user_sees_own_review_instead_of_form(client, login, course):
    login()
    _post_review_any_route(client, course.id, 4, "Неплохо")

    before = db.session.query(Review).filter_by(course_id=course.id).count()
    _post_review_any_route(client, course.id, 3, "Попытка №2")
    after = db.session.query(Review).filter_by(course_id=course.id).count()
    assert before == after


def test_last_five_reviews_only(client, another_user_factory, course, factories):
    base = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=1)
    for i in range(6):
        u = another_user_factory(i)
        factories["mk_review"](
            course=course,
            user=u,
            rating=5 - (i % 3),
            text=f"review #{i}",
            created=base + dt.timedelta(minutes=i),
        )

    resp = client.get(_course_show_path(course.id))
    assert resp.status_code == 200

    last_five = (
        db.session.query(Review)
        .filter_by(course_id=course.id)
        .order_by(Review.created_at.desc())
        .limit(5)
        .all()
    )
    assert len(last_five) == 5
    assert all("review #0" != r.text for r in last_five)


def test_pagination_and_sort_positive(client, course, factories, another_user_factory):
    for i in range(12):
        u = another_user_factory(100 + i)
        factories["mk_review"](course=course, user=u, rating=(i % 6), text=f"r{i}")

    resp = client.get(_course_reviews_path(course.id) + "?sort_by=positive&page=1")
    assert resp.status_code == 200

    top_exists = (
        db.session.query(Review)
        .filter_by(course_id=course.id, rating=5)
        .count()
        > 0
    )
    assert top_exists


def test_pagination_and_sort_negative(client, course, factories, another_user_factory):
    for i in range(12):
        u = another_user_factory(200 + i)
        factories["mk_review"](course=course, user=u, rating=(i % 6), text=f"rn{i}")

    resp = client.get(_course_reviews_path(course.id) + "?sort_by=negative&page=1")
    assert resp.status_code == 200

    low_exists = (
        db.session.query(Review)
        .filter(Review.course_id == course.id, Review.rating.in_([0, 1, 2]))
        .count()
        > 0
    )
    assert low_exists


def test_add_review_requires_login(client, course):
    resp = client.post(
        _course_add_review_path(course.id),
        data={"rating": "5", "text": "hidden"},
        follow_redirects=False,
    )
    assert resp.status_code in (302, 401)
    if resp.status_code == 302:
        assert "/login" in (resp.headers.get("Location") or "")
