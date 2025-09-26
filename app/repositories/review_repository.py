from app.models import Review

class ReviewRepository:
    def __init__(self, db):
        self.db = db

    def add_review(self, text, rating, course_id, user_id):
        review = Review(text=text, rating=rating, course_id=course_id, user_id=user_id)
        self.db.session.add(review)
        self.db.session.commit()
        return review

    def get_reviews_by_course_id(self, course_id):
        return self.db.session.execute(self.db.select(Review).filter_by(course_id=course_id)).scalars().all()