import sqlite3
import pandas as pd

DB_PATH = 'data/planner.db'


def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Tabla 1: Recetario (Nombre del plato e ingredientes)
    c.execute('''CREATE TABLE IF NOT EXISTS recetas
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  nombre TEXT UNIQUE, 
                  ingredientes TEXT)''')  # Ingredientes separados por coma

    # Tabla 2: Calendario (Día, Momento, ID de Receta)
    c.execute('''CREATE TABLE IF NOT EXISTS planificacion
                 (fecha TEXT, 
                  momento TEXT, 
                  receta_nombre TEXT,
                  PRIMARY KEY (fecha, momento))''')
    conn.commit()
    conn.close()


def run_query(query, params=(), return_data=False):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute(query, params)
        conn.commit()
        if return_data:
            return c.fetchall()
    except Exception as e:
        print(e)
    finally:
        conn.close()


def get_all_recipes():
    data = run_query("SELECT nombre FROM recetas", return_data=True)
    return [row[0] for row in data] if data else []


def get_ingredients(receta_nombre):
    data = run_query("SELECT ingredientes FROM recetas WHERE nombre=?", (receta_nombre,), return_data=True)
    return data[0][0] if data else ""


def save_recipe(nombre, ingredientes):
    run_query("INSERT OR REPLACE INTO recetas (nombre, ingredientes) VALUES (?, ?)", (nombre, ingredientes))


def get_plan_range(start_date, end_date):
    query = "SELECT fecha, momento, receta_nombre FROM planificacion WHERE fecha BETWEEN ? AND ?"
    data = run_query(query, (str(start_date), str(end_date)), return_data=True)
    return data


def save_meal(fecha, momento, receta):
    run_query("INSERT OR REPLACE INTO planificacion (fecha, momento, receta_nombre) VALUES (?, ?, ?)",
              (str(fecha), momento, receta))