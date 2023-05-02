from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from models import db, User, Ingredient, Recipe
from utils import get_user_ingredients
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import openai
import os
import random

# Set OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///pantrypal.db'
db.init_app(app)

# Initialize login manager
login_manager = LoginManager()
login_manager.init_app(app)

# User loader function for login manager
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes for user authentication (register, login, and logout)
# Route implements the register action for the user concept
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

# Route implements the login action for the user concept
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

# Route implements the log out action for the user concept
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# Route for the homepage
@app.route('/')
def index():
    recipes = Recipe.query.all()
    random.shuffle(recipes)
    return render_template('index.html', recipes=recipes)

# Route for generating a new recipe
# Implements the generate action for the recipe concept
@app.route('/recipe', methods=['POST'])
def generate_recipe():
    ingredient_names = []
    if current_user.is_authenticated:
        ingredient_names = get_user_ingredients(current_user.id)

    # Gets the list of ingredients that will be associated with this new recipe
    ingredients_text = request.form.get('ingredients')
    if ingredients_text == "":
        selected_ingredients = []
        for key, value in request.form.items():
            if key.startswith('pantry-ingredient'):
                selected_ingredients.append(value)
        ingredients_text = ', '.join(selected_ingredients)

    # Gets the dietary restrictions / preferences of the current user, as an argument to the generate function of the recipe concept
    dietary_restrictions = ""
    meal_preferences = ""
    if current_user.is_authenticated:
        if len(current_user.dietary_restrictions) > 0:
            dietary_restrictions = f"The recipe should obey the following dietary restrictions: {current_user.dietary_restrictions}."
        if len(current_user.meal_preferences) > 0:
            meal_preferences = f"The recipe should keep in mind the following preferences: {current_user.meal_preferences}."

    meal_type = request.form.get('meal_type')

    if ingredients_text == "":
        return render_template('recipe.html', recipe="Please input at least one ingredient!", ingredient_names=ingredient_names)
    
    prompt = f"""
    Create a recipe in the following format. The list of ingredients on the second line shouldn't have quantities, but the ingredients in the HTML should have quantities.

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

    The recipe should only use the following ingredients. You don't need to use all the ingredients, but you must only use ingredients from this list: {ingredients_text}. The recipe should be for {meal_type}.
    Only use ingredients from the list provided, do not use any ingredients not from this list!
    {dietary_restrictions}
    {meal_preferences}"""

    # The actual generate action of the recipe concept -- AI backend!
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages = [
            {"role": "system", "content": "You are a world-class chef that creates recipes for users."},
            {"role": "user", "content": prompt}
        ]
    ).choices[0].message.content

    try:
        recipe_title = response.split("\n")[0]
        ingredients = response.split("\n")[1]
        if ingredients == '':
            ingredients = response.split("\n")[2]
        generated_recipe_content = response[response.index("<"):]
    except:
        # If GPT returns something in an invalid format, just display the entire response
        # Have not seen this happen, but theorectically possible
        return render_template('recipe.html', recipe=response, ingredient_names=ingredient_names)

    generated_recipe = Recipe(title=recipe_title, ingredients=ingredients, content=generated_recipe_content)
    db.session.add(generated_recipe)
    db.session.commit()

    return redirect(f'/recipe?recipe_id={generated_recipe.id}')

# Route for displaying a recipe
@app.route('/recipe', methods=['GET'])
def recipe():
    ingredient_names = []
    if current_user.is_authenticated:
        ingredient_names = get_user_ingredients(current_user.id)

    recipe_id = request.args.get('recipe_id', type=int)
    recipe_content = ""
    if recipe_id:
        recipe_content = Recipe.query.filter_by(id=recipe_id).first().content

    return render_template('recipe.html', recipe=recipe_content, ingredient_names=ingredient_names, recipe_id=recipe_id)

# Implements the add action of the ingredient concept, with the current_user as the user argument
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

# Implements the delete action of the ingredient concept, with the current_user as the user argument
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

# Route for updating common ingredients
# An alternative implementation of the add / delete action of the ingredient concept
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

# Route for updating user preferences (dietary restrictions and meal preferences)
# Implements the add / delete actions of the dietary restrictions / preferences concept
@app.route('/update_preferences', methods=['POST'])
@login_required
def update_preferences():
    restrictions = ['vegetarian', 'vegan', 'gluten-free', 'dairy-free', 'nut-free']
    preferences = ['low_carb', 'high_protein', 'low_fat', 'low_sodium']

    user_restrictions = []
    user_preferences = []

    for restriction in restrictions:
        if restriction in request.form:
            user_restrictions.append(restriction)

    for preference in preferences:
        if preference in request.form:
            user_preferences.append(preference)

    current_user.dietary_restrictions = ','.join(user_restrictions)
    current_user.meal_preferences = ','.join(user_preferences)
    db.session.commit()

    flash('Preferences updated successfully')
    return redirect(url_for('pantry'))

# Route for displaying the user's saved recipes
# Displays the recipe concept filtered by a user's saved recipes
@app.route('/saved_recipes')
@login_required
def saved_recipes():
    saved_recipes = current_user.saved_recipes
    return render_template('saved_recipes.html', saved_recipes=saved_recipes)

# Route for saving a recipe
# Implements the save action of the recipe action, with the current user as the user argument
@app.route('/save_recipe/<int:recipe_id>', methods=['POST'])
@login_required
def save_recipe(recipe_id):
    recipe = Recipe.query.get(recipe_id)
    if recipe is None:
        flash('Recipe not found', 'error')
        return redirect(url_for('index'))

    current_user.saved_recipes.append(recipe)
    db.session.commit()

    flash('Recipe saved successfully', 'success')
    return redirect(url_for('recipe', recipe_id=recipe_id))

# Route for unsaving a recipe
@app.route('/unsave_recipe/<int:recipe_id>', methods=['POST'])
@login_required
def unsave_recipe(recipe_id):
    recipe = Recipe.query.get_or_404(recipe_id)
    current_user.saved_recipes.remove(recipe)
    db.session.commit()
    flash(f'Recipe "{recipe.title}" has been removed from your saved recipes', 'success')
    return redirect(url_for('saved_recipes'))

# Route for displaying the user's pantry
@app.route('/pantry')
@login_required
def pantry():
    user_ingredients = get_user_ingredients(current_user.id, False)
    return render_template('pantry.html', ingredients=user_ingredients, ingredient_names=[ingredient.name for ingredient in user_ingredients])

if __name__ == '__main__':
    app.run(debug=True)
