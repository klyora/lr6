from flask import Blueprint, render_template, request, flash, redirect, url_for, abort
from flask_login import login_required, current_user
from sqlalchemy.exc import IntegrityError
from sqlalchemy import desc, asc
from app.models import db, Review
from app.repositories import CourseRepository, UserRepository, CategoryRepository, ImageRepository, ReviewRepository

user_repository = UserRepository(db)
course_repository = CourseRepository(db)
category_repository = CategoryRepository(db)
image_repository = ImageRepository(db)
review_repository = ReviewRepository(db)

bp = Blueprint('courses', __name__, url_prefix='/courses')

COURSE_PARAMS = [
    'author_id', 'name', 'category_id', 'short_desc', 'full_desc'
]

REVIEW_PER_PAGE = 5  # Количество отзывов на одной странице

def params():
    return { p: request.form.get(p) or None for p in COURSE_PARAMS }

def search_params():
    return {
        'name': request.args.get('name'),
        'category_ids': [x for x in request.args.getlist('category_ids') if x],
    }

@bp.route('/')
def index():
    pagination = course_repository.get_pagination_info(**search_params())
    courses = course_repository.get_all_courses(pagination=pagination)
    categories = category_repository.get_all_categories()
    return render_template('courses/index.html',
                           courses=courses,
                           categories=categories,
                           pagination=pagination,
                           search_params=search_params())

@bp.route('/new')
@login_required
def new():
    course = course_repository.new_course()
    categories = category_repository.get_all_categories()
    users = user_repository.get_all_users()
    return render_template('courses/new.html',
                           categories=categories,
                           users=users,
                           course=course)

@bp.route('/create', methods=['POST'])
@login_required
def create():
    f = request.files.get('background_img')
    img = None
    course = None

    try:
        if f and f.filename:
            img = image_repository.add_image(f)

        image_id = img.id if img else None
        course = course_repository.add_course(**params(), background_image_id=image_id)
    except IntegrityError as err:
        flash(f'Возникла ошибка при записи данных в БД. Проверьте корректность введённых данных. ({err})', 'danger')
        categories = category_repository.get_all_categories()
        users = user_repository.get_all_users()
        return render_template('courses/new.html',
                            categories=categories,
                            users=users,
                            course=course)

    flash(f'Курс {course.name} был успешно добавлен!', 'success')

    return redirect(url_for('courses.index'))

@bp.route('/<int:course_id>', methods=['GET', 'POST'])
def show(course_id):
    course = course_repository.get_course_by_id(course_id)
    if course is None:
        abort(404)

    # Получаем последние 5 отзывов
    reviews = db.session.execute(db.select(Review).filter_by(course_id=course_id).order_by(desc(Review.created_at)).limit(5)).scalars().all()

    # Проверяем, оставил ли текущий пользователь отзыв для этого курса
    user_review = None
    if current_user.is_authenticated:
        user_review = db.session.execute(db.select(Review).filter_by(course_id=course_id, user_id=current_user.id)).scalar()

    return render_template('courses/show.html', course=course, reviews=reviews, user_review=user_review)

@bp.route('/<int:course_id>/reviews', methods=['GET', 'POST'])
def reviews(course_id):
    course = course_repository.get_course_by_id(course_id)
    if course is None:
        abort(404)

    sort_by = request.args.get('sort_by', 'newest')
    page = request.args.get('page', 1, type=int)

    # Определяем порядок сортировки
    if sort_by == 'positive':
        order = desc(Review.rating)
    elif sort_by == 'negative':
        order = asc(Review.rating)
    else:
        order = desc(Review.created_at)  # newest

    # Получаем отзывы с пагинацией и сортировкой
    pagination = db.paginate(db.select(Review).filter_by(course_id=course_id).order_by(order), page=page, per_page=REVIEW_PER_PAGE)

    # Проверяем, оставил ли текущий пользователь отзыв для этого курса
    user_review = None
    if current_user.is_authenticated:
        user_review = db.session.execute(db.select(Review).filter_by(course_id=course_id, user_id=current_user.id)).scalar()

    return render_template('courses/reviews.html', course=course, pagination=pagination, sort_by=sort_by, user_review=user_review)

@bp.route('/<int:course_id>/add_review', methods=['POST'])
@login_required
def add_review(course_id):
    course = course_repository.get_course_by_id(course_id)
    if course is None:
        abort(404)

    rating = request.form.get('rating', type=int)
    text = request.form.get('text')

    if not text:
        flash('Пожалуйста, напишите текст отзыва.', 'danger')
        return redirect(request.referrer)

    # Проверяем, оставил ли пользователь уже отзыв
    existing_review = db.session.execute(db.select(Review).filter_by(course_id=course_id, user_id=current_user.id)).scalar()
    if existing_review:
        flash('Вы уже оставили отзыв для этого курса.', 'warning')
        return redirect(request.referrer)

    # Создаем и добавляем отзыв
    review = Review(course_id=course_id, user_id=current_user.id, rating=rating, text=text)
    db.session.add(review)

    # Обновляем рейтинг курса
    course.rating_sum += rating
    course.rating_num += 1

    try:
        db.session.commit()
        flash('Спасибо за ваш отзыв!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Произошла ошибка при сохранении отзыва: {e}', 'danger')

    return redirect(request.referrer)