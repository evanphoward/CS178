from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import openai
import os
import random

openai.api_key = os.getenv("OPENAI_API_KEY")

app = Flask(__name__)

app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)

    def __repr__(self):
        return f'<User {self.username}>'

class Ingredient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    required = db.Column(db.Boolean, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Recipe(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(256), nullable=False)
    content = db.Column(db.String(10000), nullable=False)
    ingredients = db.Column(db.String(1000), nullable=False)

def get_user_ingredients(user_id, as_string=True):
    ingredients = Ingredient.query.filter_by(user_id=user_id).order_by(Ingredient.name).all()
    if as_string == False:
        return ingredients
    ingredient_names = [ingredient.name for ingredient in ingredients]
    return ingredient_names

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm-password')

        if password != confirm_password:
            flash('Passwords do not match.')
            return redirect(url_for('register'))

        user = User.query.filter_by(username=username).first()
        if user:
            flash('Username already exists.')
            return redirect(url_for('register'))

        new_user = User(username=username, password=generate_password_hash(password, method='sha256'))
        db.session.add(new_user)
        db.session.commit()

        flash('Registration successful. Please log in.')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('pantry'))

        flash('Invalid username or password. Please try again.')
        return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/pantry')
@login_required
def pantry():
    user_ingredients = get_user_ingredients(current_user.id, False)
    return render_template('pantry.html', ingredients=user_ingredients, ingredient_names=[ingredient.name for ingredient in user_ingredients])

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/')
def index():
    recipes = Recipe.query.all()
    random.shuffle(recipes)
    return render_template('index.html', recipes=recipes)

@app.route('/recipe', methods=['POST', 'GET'])
def recipe():
    if request.method == 'POST':
        ingredients_text = ""
        if request.form.get('ingredients'):
            ingredients_text = request.form.get('ingredients')
        elif current_user.is_authenticated:
            user_ingredients = get_user_ingredients(current_user.id)
            ingredients_text = ', '.join(user_ingredients)

        if ingredients_text == "":
            return render_template('recipe.html', recipe="Please input at least one ingredient!")
        
        prompt = f"""
        Create a recipe that uses only the following ingredients. You don't need to use all the ingredients, but you must only use ingredients from this list. 
        Write in the following format. The list of ingredients on the second line shouldn't have quantities, but the ingredients in the HTML should have quantities.

        ```
        [TITLE]
        [INGREDIENT 1], [INGREDIENT 2], [INGREDIENT 3]
        <div class="generated-recipe">
        <h1 class="recipe-title"> [TITLE] </h1>
        <h2 class="ingredients-header"> Ingredients: </h2>
        <ul class="ingredients-list">
        <li class="ingredients-item"> [INGREDIENT 1] </li>
        <li class="ingredients-item"> [INGREDIENT 2] </li>
        </ul>
        <h2 class="instructions-header">  Instructions: </h2>
        <ol class="instructions-list">
        <li class="instruction-item"> [STEP 1] </li>
        <li class="instruction-item"> [STEP 2] </li>
        </ol>
        </div>
        ```

        Here are the ingredients:  {ingredients_text}"""

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages = [
                {"role": "system", "content": "You are a world-class chef that creates recipes for users."},
                {"role": "user", "content": prompt}
            ]
        ).choices[0].message.content

        recipe_title = response.split("\n")[0]
        ingredients = response.split("\n")[1]
        if ingredients == '':
            ingredients = response.split("\n")[2]
        generated_recipe_content = response[response.index("<"):]

        generated_recipe = Recipe(title=recipe_title, ingredients=ingredients, content=generated_recipe_content)
        db.session.add(generated_recipe)
        db.session.commit()

        return render_template('recipe.html', recipe=generated_recipe_content)

    recipe_id = request.args.get('recipe_id', type=int)
    recipe_content = ""
    if recipe_id:
        recipe_content = Recipe.query.filter_by(id=recipe_id).first().content
    return render_template('recipe.html', recipe=recipe_content)

@app.route('/add_ingredient', methods=['POST'])
@login_required
def add_ingredient():
    ingredient = request.form['ingredient']
    
    # Create and store the Ingredient object
    new_ingredient = Ingredient(name=ingredient, required=False, user_id=current_user.id)
    db.session.add(new_ingredient)
    db.session.commit()

    flash('Ingredient added successfully')
    return redirect(url_for('pantry'))

@app.route('/update_common_ingredients', methods=['POST'])
@login_required
def update_common_ingredients():
    data = request.get_json()
    ingredient_name = data.get('ingredient')
    add = data.get('add')

    ingredient = Ingredient.query.filter_by(name=ingredient_name, user_id=current_user.id).first()

    if add:
        if not ingredient:
            new_ingredient = Ingredient(name=ingredient_name, required=False, user_id=current_user.id)
            db.session.add(new_ingredient)
            db.session.commit()
            return redirect(url_for('pantry'))
    else:
        if ingredient:
            db.session.delete(ingredient)
            db.session.commit()
            return redirect(url_for('pantry'))

    return redirect(url_for('pantry'))

@app.route('/delete_ingredient/<int:ingredient_id>', methods=['POST'])
@login_required
def delete_ingredient(ingredient_id):
    ingredient = Ingredient.query.get_or_404(ingredient_id)
    
    if ingredient.user_id != current_user.id:
        abort(403)
    
    db.session.delete(ingredient)
    db.session.commit()
    flash('Ingredient deleted successfully', 'success')
    return redirect(url_for('pantry'))

@app.route('/update_preferences', methods=['POST'])
@login_required
def update_preferences():
    # Add code to store the user's dietary restrictions and preferences
    flash('Preferences updated successfully')
    return redirect(url_for('pantry'))

if __name__ == '__main__':
    app.run(debug=True)
