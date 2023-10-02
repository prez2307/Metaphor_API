from . import db
from flask_login import UserMixin
from sqlalchemy.sql import func

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True)
    password = db.Column(db.String(150))
    first_name = db.Column(db.String(150))
    reviews = db.relationship('MovieReview', backref='user', lazy=True)

class FavoriteMovie(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    movie_id = db.Column(db.String(50), nullable=False)  
    title = db.Column(db.String(200), nullable=False)  
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

class MovieReview(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    movie_id = db.Column(db.String(50), nullable=False)
    movie_title = db.Column(db.String(200), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=func.now())