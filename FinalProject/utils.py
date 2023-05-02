from models import Ingredient

# Function to get user ingredients
def get_user_ingredients(user_id, as_string=True):
    ingredients = Ingredient.query.filter_by(user_id=user_id).order_by(Ingredient.name).all()
    if as_string == False:
        return ingredients
    ingredient_names = [ingredient.name for ingredient in ingredients]
    return ingredient_names