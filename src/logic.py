from datetime import timedelta
from collections import Counter


def get_start_of_week(date_obj):
    return date_obj - timedelta(days=date_obj.weekday())


def extract_ingredients_from_plan(plan_data, db_module):
    """
    plan_data ahora viene como [(fecha, momento, receta_id, receta_nombre)...]
    """
    lista_final = []

    if not plan_data:
        return []

    for _, _, receta_id, _ in plan_data:
        if receta_id:
            # Obtenemos la lista de nombres de ingredientes directamente
            ingredientes = db_module.get_recipe_ingredients(receta_id)
            lista_final.extend(ingredientes)

    return lista_final


def aggregate_ingredients(ingredient_list):
    return Counter(ingredient_list)