from datetime import timedelta
from collections import Counter


def get_start_of_week(date_obj):
    """
    Dada una fecha, devuelve el lunes de esa semana.
    """
    return date_obj - timedelta(days=date_obj.weekday())


def extract_ingredients_from_plan(plan_data, db_module):
    """
    Recibe los datos crudos del plan (fecha, momento, receta)
    y devuelve una lista limpia de ingredientes.
    """
    lista_final = []

    if not plan_data:
        return []

    # Iteramos sobre cada comida planificada
    for _, _, receta_nombre in plan_data:
        if receta_nombre:
            # Obtenemos la cadena de ingredientes de la DB
            ings_str = db_module.get_ingredients(receta_nombre)

            # Limpieza de datos:
            # 1. Separar por comas
            # 2. Quitar espacios en blanco al inicio/final
            # 3. Poner en formato Título (ej: "tomate" -> "Tomate")
            if ings_str:
                items = [i.strip().title() for i in ings_str.split(',') if i.strip()]
                lista_final.extend(items)

    return lista_final


def aggregate_ingredients(ingredient_list):
    """
    Recibe una lista de ingredientes ['Huevo', 'Huevo', 'Patata']
    Devuelve un diccionario contado {'Huevo': 2, 'Patata': 1}
    """
    return Counter(ingredient_list)