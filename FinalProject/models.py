from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

db = SQLAlchemy()

# Define the many-to-many relationship between users and saved recipes
saved_recipes = db.Table('saved_recipes',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('recipe_id', db.Integer, db.ForeignKey('recipe.id'), primary_key=True)
)

# USER CONCEPT
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)
    dietary_restrictions = db.Column(db.String(255), nullable=True, default="")
    meal_preferences = db.Column(db.String(255), nullable=True, default="")
    saved_recipes = db.relationship('Recipe', secondary=saved_recipes, lazy='subquery', backref=db.backref('users', lazy=True))

# INGREDIENT CONCEPT
class Ingredient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    required = db.Column(db.Boolean, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# RECIPE CONCEPT
class Recipe(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(256), nullable=False)
    content = db.Column(db.String(10000), nullable=False)
    ingredients = db.Column(db.String(1000), nullable=False)