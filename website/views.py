from flask import Blueprint, render_template, request, flash, jsonify, url_for, redirect
from flask_login import login_required, current_user
from .models import Note, FavoriteMovie, MovieReview
import urllib.request, json
from urllib.parse import quote
from . import db
import json
import os
from metaphor_python import Metaphor
import openai 

views = Blueprint('views', __name__)

def search_and_summarize(movie_title, critics, reviews):
    metaphor_api = Metaphor(api_key=os.environ.get('METAPHOR_API_KEY'))
    if critics:
        query = 'Here is a review of ' + movie_title + 'by some top movie critics: '
        summary_response = metaphor_api.search(query=query, use_autoprompt=True)
        content = summary_response.get_contents()
        first = content.contents[0]
        second = content.contents[1]

    openai.api_key = os.getenv("OPEN_AI_API_KEY")

    if critics:
        USER_QUESTION = 'TRUE ' + first.extract + second.extract
    else:
        USER_QUESTION = movie_title + 'review' + ' '.join([review.content for review in reviews])

    completion = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": 'You are a helpful assistant that summarizes the contents of what I give you, either a webpage or a string of reviews. It will always have some kind of movie review. Depending on if the input I provide you starts with TRUE or not, you will summarize the critics consensus for the movie, or what the reviews I give you think about the movie. I want you to be specific enough for the user to be able to gauge whether they should watch the movie.'},
            {"role": "user", "content": USER_QUESTION},
        ],
    )

    summary = completion.choices[0].message.content
    return summary


@views.route('/', methods=['GET'])
@login_required
def home():
    user_reviews = current_user.reviews 
    return render_template("home.html", user=current_user, reviews=user_reviews)

@views.route('/movies', methods = ['GET'])
def movies():
    page = request.args.get('page', 1, type=int) 
    url = f"https://api.themoviedb.org/3/discover/movie?api_key={os.environ.get('TMDB_API_KEY')}&page={page}"
    
    response = urllib.request.urlopen(url)
    data = response.read()
    results_dict = json.loads(data)  
    
    movies_with_images = [movie for movie in results_dict["results"] if movie.get('backdrop_path')]

    return render_template("movies.html", movies=movies_with_images, user=current_user, current_page=page, total_pages=results_dict["total_pages"])


@views.route('/search_movies', methods=['GET'])
def search_movies():
    query = request.args.get('query')
    
    if not query:
        return redirect(url_for('movies'))
    
    encoded_query = quote(query)
    url = "https://api.themoviedb.org/3/search/movie?api_key={}&query={}".format(os.environ.get("TMDB_API_KEY"), encoded_query)
    
    response = urllib.request.urlopen(url)
    data = response.read()
    results = json.loads(data)
    total_pages = results.get('total_pages', 1)
    
    return render_template("movies.html", movies=results["results"], user=current_user, current_page=1, total_pages=total_pages)

@views.route('/movies/<int:movie_id>/reviews', methods=['GET', 'POST'])
@login_required
def movie_reviews(movie_id):
    url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={os.environ.get('TMDB_API_KEY')}"
    response = urllib.request.urlopen(url)
    data = response.read()
    movie_details = json.loads(data)
    movie_title = movie_details.get('title', '')


    if request.method == 'POST':
        content = request.form.get('content')
        if content:
            # Including movie_title when creating a new review
            new_review = MovieReview(movie_id=str(movie_id), movie_title=movie_title, user_id=current_user.id, content=content)
            db.session.add(new_review)
            db.session.commit()
            flash('Your review has been posted!', category='success')
    
    # Fetch user-generated reviews
    user_reviews = MovieReview.query.filter_by(movie_id=str(movie_id)).all()
    if not user_reviews:
        audience_summary = 'Sorry, there are no audience reviews for this movie currently'
    else:
        audience_summary = search_and_summarize(movie_title=movie_title, critics=False, reviews=user_reviews)
    
    critics_summary = search_and_summarize(movie_title=movie_title, critics=True, reviews=user_reviews)

    return render_template("reviews.html", movie=movie_details, reviews=user_reviews, user=current_user, critics_summ=critics_summary, audience_summ=audience_summary)

@views.route('/delete-review/<int:review_id>', methods=['POST'])
@login_required
def delete_review(review_id):
    review = MovieReview.query.get(review_id)
    if review and review.user_id == current_user.id:
        db.session.delete(review)
        db.session.commit()
        flash('Review deleted!', category='success')
    else:
        flash('Review not found!', category='error')
    return redirect(request.referrer) 


@views.route('/add_favorite', methods=['POST'])
@login_required
def add_favorite():
    if request.method == 'POST':
        movie_id = request.form.get('movie_id')
        title = request.form.get('title')
        
        if not movie_id or not title:
            flash('Movie ID and Title are required!', category='error')
            return redirect(request.referrer)  
        
        # Check if the movie is already in the favorites
        existing_favorite = FavoriteMovie.query.filter_by(user_id=current_user.id, movie_id=movie_id).first()
        if existing_favorite:
            flash('This movie is already in your favorites!', category='error')
            return redirect(request.referrer)  
        
        # Add to favorites since it doesn’t exist
        new_favorite_movie = FavoriteMovie(movie_id=movie_id, title=title, user_id=current_user.id)
        db.session.add(new_favorite_movie)
        db.session.commit()
        
        flash('Movie added to favorites!', category='success')
        return redirect(url_for('views.home'))  
    
    return redirect(url_for('views.movies'))  


@views.route('/remove_favorite', methods=['POST'])
@login_required
def remove_favorite():
    movie_id = request.form.get('movie_id')
    favorite_movie = FavoriteMovie.query.filter_by(user_id=current_user.id, movie_id=movie_id).first()
    
    if favorite_movie:
        db.session.delete(favorite_movie)
        db.session.commit()
        flash('Movie removed from favorites!', category='success')
    else:
        flash('Movie not found in your favorites!', category='error')
        
    return redirect(url_for('views.favorite_movies')) 

@views.route('/favorites', methods=['GET'])
@login_required
def favorite_movies():
    user_favorites = FavoriteMovie.query.filter_by(user_id=current_user.id).all()
    return render_template('favorite_movies.html', favorites=user_favorites, user=current_user)