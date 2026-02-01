from datetime import timedelta
from collections import Counter


def get_start_of_week(date_obj):
    return date_obj - timedelta(days=date_obj.weekday())

def extract_ingredients_from_plan(datos_plan, db):
    lista_ingredientes = []
    for p in datos_plan:
        receta_id = p[2] # El ID que acabamos de limpiar arriba
        if receta_id:
            ingredientes = db.get_recipe_ingredients(receta_id)
            lista_ingredientes.extend(ingredientes)
    return lista_ingredientes

def aggregate_ingredients(ingredient_list):
    return Counter(ingredient_list)