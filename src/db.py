import sqlite3

DB_PATH = 'data/planner.db'


def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Habilitar foreign keys
    c.execute("PRAGMA foreign_keys = ON")

    # 1. Tabla de Ingredientes Únicos
    c.execute('''CREATE TABLE IF NOT EXISTS ingredientes
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  categoria TEXT DEFAULT 'Otros',
                  nombre TEXT UNIQUE)''')

    # 2. Tabla de Recetas
    c.execute('''CREATE TABLE IF NOT EXISTS recetas
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  nombre TEXT UNIQUE)''')

    # 3. Tabla Intermedia (Muchos a Muchos)
    c.execute('''CREATE TABLE IF NOT EXISTS receta_ingredientes
                 (receta_id INTEGER, 
                  ingrediente_id INTEGER,
                  FOREIGN KEY(receta_id) REFERENCES recetas(id) ON DELETE CASCADE,
                  FOREIGN KEY(ingrediente_id) REFERENCES ingredientes(id) ON DELETE CASCADE,
                  PRIMARY KEY (receta_id, ingrediente_id))''')

    # 4. Tabla de Planificación (Calendario)
    c.execute('''CREATE TABLE IF NOT EXISTS planificacion
                 (fecha TEXT, 
                  momento TEXT, 
                  receta_id INTEGER,
                  FOREIGN KEY(receta_id) REFERENCES recetas(id) ON DELETE SET NULL,
                  PRIMARY KEY (fecha, momento))''')

    conn.commit()
    conn.close()


def run_query(query, params=(), return_data=False):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("PRAGMA foreign_keys = ON")
    try:
        c.execute(query, params)
        conn.commit()
        if return_data:
            return c.fetchall()
    except Exception as e:
        print(f"Error DB: {e}")
    finally:
        conn.close()


# --- GESTIÓN DE INGREDIENTES ---
def add_ingredient(nombre, categoria="Otros"):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO ingredientes (nombre, categoria) VALUES (?, ?)", (nombre, categoria))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def get_all_ingredients():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Importante: Pedimos ID, nombre y categoria
    c.execute("SELECT id, nombre, categoria FROM ingredientes ORDER BY nombre ASC")
    res = c.fetchall()
    conn.close()
    return res

def get_ingredients_categories():
    """Devuelve un diccionario con el nombre del ingrediente y su categoría"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Intentamos obtener nombre y categoria
    try:
        c.execute("SELECT nombre, categoria FROM ingredientes")
        # Si la categoría es None o vacía, le ponemos "Otros"
        res = {row[0]: (row[1] if row[1] else "Otros") for row in c.fetchall()}
    except sqlite3.OperationalError:
        # Si la columna no existe aún, devolvemos "Otros" para todos
        c.execute("SELECT nombre FROM ingredientes")
        res = {row[0]: "Otros" for row in c.fetchall()}
    conn.close()
    return res

def delete_ingredient(ingrediente_id):
    run_query("DELETE FROM ingredientes WHERE id=?", (ingrediente_id,))

def update_ingredient(ing_id, new_name, new_cat):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute(
            "UPDATE ingredientes SET nombre = ?, categoria = ? WHERE id = ?",
            (new_name, new_cat, ing_id)
        )
        conn.commit()
        return True
    except sqlite3.Error:
        return False
    finally:
        conn.close()

# --- GESTIÓN DE RECETAS ---
def ensure_special_recipe(nombre_especial):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Verificamos si existe
    c.execute("SELECT id FROM recetas WHERE nombre = ?", (nombre_especial,))
    if not c.fetchone():
        # Si no existe, la creamos vacía (sin ingredientes inicialmente)
        c.execute("INSERT INTO recetas (nombre) VALUES (?)", (nombre_especial,))
        conn.commit()
    conn.close()

def create_recipe(nombre_receta, lista_ids_ingredientes):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        # 1. Crear Receta
        c.execute("INSERT INTO recetas (nombre) VALUES (?)", (nombre_receta,))
        receta_id = c.lastrowid

        # 2. Asociar ingredientes
        for ing_id in lista_ids_ingredientes:
            c.execute("INSERT INTO receta_ingredientes (receta_id, ingrediente_id) VALUES (?, ?)",
                      (receta_id, ing_id))
        conn.commit()
        return True
    except Exception as e:
        print(e)
        return False
    finally:
        conn.close()


def delete_recipe(receta_id):
    # Al borrar receta, el ON DELETE CASCADE borrará las relaciones en receta_ingredientes
    run_query("DELETE FROM recetas WHERE id=?", (receta_id,))


def update_recipe(receta_id, nuevo_nombre, lista_ids_ingredientes):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("PRAGMA foreign_keys = ON")
    try:
        # 1. Actualizar el nombre de la receta
        c.execute("UPDATE recetas SET nombre = ? WHERE id = ?", (nuevo_nombre, receta_id))

        # 2. Eliminar ingredientes antiguos de esta receta
        c.execute("DELETE FROM receta_ingredientes WHERE receta_id = ?", (receta_id,))

        # 3. Insertar los nuevos ingredientes seleccionados
        for ing_id in lista_ids_ingredientes:
            c.execute("INSERT INTO receta_ingredientes (receta_id, ingrediente_id) VALUES (?, ?)",
                      (receta_id, ing_id))

        conn.commit()
        return True
    except Exception as e:
        print(f"Error al actualizar: {e}")
        return False
    finally:
        conn.close()

def get_all_recipes():
    return run_query("SELECT id, nombre FROM recetas ORDER BY nombre", return_data=True)


def get_recipe_ingredients(receta_id):
    query = '''
        SELECT i.nombre 
        FROM ingredientes i
        JOIN receta_ingredientes ri ON i.id = ri.ingrediente_id
        WHERE ri.receta_id = ?
    '''
    data = run_query(query, (receta_id,), return_data=True)
    return [row[0] for row in data]


# --- GESTIÓN PLANIFICACIÓN ---
def save_meal_plan(fecha, momento, receta_id):
    run_query("INSERT OR REPLACE INTO planificacion (fecha, momento, receta_id) VALUES (?, ?, ?)",
              (str(fecha), momento, receta_id))


def get_plan_range_details(start_date, end_date):
    # Esta query es más compleja porque hace JOINs para traer nombres
    query = '''
        SELECT p.fecha, p.momento, r.id, r.nombre 
        FROM planificacion p
        JOIN recetas r ON p.receta_id = r.id
        WHERE p.fecha BETWEEN ? AND ?
    '''
    return run_query(query, (str(start_date), str(end_date)), return_data=True)

# --- GESTIÓN DE LA LISTA DE LA COMPRA ---
def init_shopping_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Tabla para guardar el estado (tachado/no tachado) de los ingredientes por semana
    c.execute('''CREATE TABLE IF NOT EXISTS compras_estado
                 (semana_inicio TEXT, 
                  ingrediente_nombre TEXT, 
                  comprado BOOLEAN,                  
                  PRIMARY KEY (semana_inicio, ingrediente_nombre))''')
    conn.commit()
    conn.close()

def get_shopping_status(semana_inicio):
    """Devuelve un diccionario {ingrediente: True/False} para la semana dada"""
    query = "SELECT ingrediente_nombre, comprado FROM compras_estado WHERE semana_inicio = ?"
    data = run_query(query, (str(semana_inicio),), return_data=True)
    return {row[0]: bool(row[1]) for row in data}

def update_shopping_status(semana_inicio, ingrediente, estado):
    """Guarda si un ingrediente está comprado o no"""
    query = '''INSERT OR REPLACE INTO compras_estado 
               (semana_inicio, ingrediente_nombre, comprado) 
               VALUES (?, ?, ?)'''
    run_query(query, (str(semana_inicio), ingrediente, estado))

def clear_shopping_status(semana_inicio):
    """Elimina todos los registros de 'comprado' para una semana concreta"""
    query = "DELETE FROM compras_estado WHERE semana_inicio = ?"
    run_query(query, (str(semana_inicio),))


def reset_historical_data():
    conn = sqlite3.connect(DB_PATH)
    # Importante: Cambiamos el nivel de aislamiento a None para que VACUUM funcione
    conn.isolation_level = None
    c = conn.cursor()
    try:
        # 1. Borramos los datos (Esto sí requiere una transacción manual o auto)
        c.execute("BEGIN")
        c.execute("DELETE FROM planificacion")
        c.execute("DELETE FROM compras_estado")
        c.execute("COMMIT")

        # 2. Ahora ejecutamos VACUUM fuera de la transacción
        c.execute("VACUUM")

        return True
    except Exception as e:
        if conn:
            c.execute("ROLLBACK")
        print(f"Error detallado en DB: {e}")
        return False
    finally:
        conn.close()