import psycopg2
import streamlit as st

# --- CONEXIÓN A LA BASE DE DATOS (SUPABASE) ---
@st.cache_resource
def get_connection():
    """
    Mantiene una única conexión abierta.
    Para uso personal, esto consume solo 1 conexión del pool de Supabase.
    """
    try:
        conn_str = st.secrets["db"]["connection_string"]
        conn = psycopg2.connect(conn_str)
        return conn
    except Exception as e:
        st.error(f"Error conectando a la base de datos: {e}")
        return None


def run_query(query, params=(), return_data=False):
    """Ejecuta una query gestionando el cursor automáticamente."""
    conn = get_connection()
    if not conn: return None

    if conn.closed:
        st.cache_resource.clear()
        conn = get_connection()

    try:
        with conn.cursor() as c:
            c.execute(query, params)
            conn.commit()
            if return_data:
                return c.fetchall()
    except Exception as e:
        conn.rollback()
        if isinstance(e, psycopg2.InterfaceError):
            st.cache_resource.clear()
        print(f"Error DB Query: {e}")
        return None


def init_db():
    """Inicializa las tablas."""
    conn = get_connection()
    if conn:
        with conn.cursor() as c:
            c.execute('''CREATE TABLE IF NOT EXISTS ingredientes (
                id SERIAL PRIMARY KEY,
                categoria TEXT DEFAULT 'Otros',
                nombre TEXT UNIQUE NOT NULL
            )''')
            c.execute('''CREATE TABLE IF NOT EXISTS recetas (
                id SERIAL PRIMARY KEY,
                nombre TEXT UNIQUE NOT NULL
            )''')
            c.execute('''CREATE TABLE IF NOT EXISTS receta_ingredientes (
                receta_id INTEGER,
                ingrediente_id INTEGER,
                FOREIGN KEY(receta_id) REFERENCES recetas(id) ON DELETE CASCADE,
                FOREIGN KEY(ingrediente_id) REFERENCES ingredientes(id) ON DELETE CASCADE,
                PRIMARY KEY (receta_id, ingrediente_id)
            )''')
            c.execute('''CREATE TABLE IF NOT EXISTS planificacion (
                fecha DATE, 
                momento TEXT, 
                receta_id INTEGER,
                FOREIGN KEY(receta_id) REFERENCES recetas(id) ON DELETE SET NULL,
                PRIMARY KEY (fecha, momento)
            )''')
            c.execute('''CREATE TABLE IF NOT EXISTS compras_estado (
                semana_inicio DATE, 
                ingrediente_nombre TEXT, 
                comprado BOOLEAN DEFAULT FALSE,                  
                PRIMARY KEY (semana_inicio, ingrediente_nombre)
            )''')
            conn.commit()


# --- GESTIÓN DE INGREDIENTES ---
def add_ingredient(nombre, categoria="Otros"):
    query = "INSERT INTO ingredientes (nombre, categoria) VALUES (%s, %s)"
    try:
        run_query(query, (nombre, categoria))
        get_all_ingredients.clear()
        return True
    except Exception:
        return False


@st.cache_data
def get_all_ingredients():
    return run_query("SELECT id, nombre, categoria FROM ingredientes ORDER BY nombre ASC", return_data=True) or []


@st.cache_data
def get_ingredients_categories():
    data = run_query("SELECT nombre, categoria FROM ingredientes", return_data=True)
    if data:
        return {row[0]: (row[1] if row[1] else "Otros") for row in data}
    return {}


def delete_ingredient(ingrediente_id):
    run_query("DELETE FROM ingredientes WHERE id=%s", (ingrediente_id,))
    get_all_ingredients.clear()
    get_ingredients_categories.clear()


def update_ingredient(ing_id, new_name, new_cat):
    query = "UPDATE ingredientes SET nombre = %s, categoria = %s WHERE id = %s"
    try:
        run_query(query, (new_name, new_cat, ing_id))
        get_all_ingredients.clear()
        get_ingredients_categories.clear()
        return True
    except Exception as e:
        print(f"Error al actualizar ingrediente: {e}")
        return False


# --- GESTIÓN DE RECETAS ---
def ensure_special_recipe(nombre_especial):
    conn = get_connection()
    try:
        with conn.cursor() as c:
            c.execute("SELECT id FROM recetas WHERE nombre = %s", (nombre_especial,))
            if not c.fetchone():
                c.execute("INSERT INTO recetas (nombre) VALUES (%s)", (nombre_especial,))
                conn.commit()
    except Exception:
        conn.rollback()


def create_recipe(nombre_receta, lista_ids_ingredientes):
    conn = get_connection()
    try:
        with conn.cursor() as c:
            c.execute("INSERT INTO recetas (nombre) VALUES (%s) RETURNING id", (nombre_receta,))
            receta_id = c.fetchone()[0]

            if lista_ids_ingredientes:
                valores = [(receta_id, ing_id) for ing_id in lista_ids_ingredientes]
                c.executemany("INSERT INTO receta_ingredientes (receta_id, ingrediente_id) VALUES (%s, %s)", valores)
            conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"Error creando receta: {e}")
        return False


def delete_recipe(receta_id):
    run_query("DELETE FROM recetas WHERE id=%s", (receta_id,))

def update_recipe(receta_id, nuevo_nombre, lista_ids_ingredientes):
    conn = get_connection()
    try:
        with conn.cursor() as c:
            c.execute("UPDATE recetas SET nombre = %s WHERE id = %s", (nuevo_nombre, receta_id))
            c.execute("DELETE FROM receta_ingredientes WHERE receta_id = %s", (receta_id,))

            if lista_ids_ingredientes:
                valores = [(receta_id, ing_id) for ing_id in lista_ids_ingredientes]
                c.executemany("INSERT INTO receta_ingredientes (receta_id, ingrediente_id) VALUES (%s, %s)", valores)
            conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"Error al actualizar: {e}")
        return False


def get_all_recipes():
    """Obtiene recetas. Cacheado indefinidamente hasta que se modifique una receta."""
    return run_query("SELECT id, nombre FROM recetas ORDER BY nombre", return_data=True) or []


def get_recipe_ingredients(receta_id):
    query = '''
        SELECT i.nombre 
        FROM ingredientes i
        JOIN receta_ingredientes ri ON i.id = ri.ingrediente_id
        WHERE ri.receta_id = %s
    '''
    data = run_query(query, (receta_id,), return_data=True)
    return [row[0] for row in data] if data else []


# --- GESTIÓN PLANIFICACIÓN ---
def save_meal_plan(fecha, momento, receta_id):
    fecha_str = str(fecha).strip()
    query = '''
        INSERT INTO planificacion (fecha, momento, receta_id) 
        VALUES (%s, %s, %s)
        ON CONFLICT (fecha, momento) 
        DO UPDATE SET receta_id = EXCLUDED.receta_id
    '''
    run_query(query, (fecha_str, momento, receta_id))
    # Limpiamos caché del planificador para que se refleje el cambio
    get_plan_range_details.clear()


@st.cache_data
def get_plan_range_details(start_date, end_date):
    query = '''
        SELECT p.fecha::text, p.momento, r.id, r.nombre 
        FROM planificacion p
        JOIN recetas r ON p.receta_id = r.id
        WHERE p.fecha >= %s AND p.fecha <= %s
    '''
    return run_query(query, (str(start_date), str(end_date)), return_data=True) or []


# --- GESTIÓN DE LA LISTA DE LA COMPRA ---
def init_shopping_db():
    pass


def get_shopping_status(semana_inicio):
    """Trae todos los estados de una semana en una sola consulta"""
    query = "SELECT ingrediente_nombre, comprado FROM compras_estado WHERE semana_inicio = %s"
    data = run_query(query, (str(semana_inicio),), return_data=True)
    return {row[0]: bool(row[1]) for row in data} if data else {}


def update_shopping_status(semana_inicio, ingrediente, estado):
    query = '''
        INSERT INTO compras_estado (semana_inicio, ingrediente_nombre, comprado) 
        VALUES (%s, %s, %s)
        ON CONFLICT (semana_inicio, ingrediente_nombre) 
        DO UPDATE SET comprado = EXCLUDED.comprado
    '''
    run_query(query, (str(semana_inicio), ingrediente, estado))


def clear_shopping_status(semana_inicio):
    query = "DELETE FROM compras_estado WHERE semana_inicio = %s"
    run_query(query, (str(semana_inicio),))


def reset_historical_data():
    try:
        run_query("TRUNCATE TABLE planificacion")
        run_query("TRUNCATE TABLE compras_estado")
        get_plan_range_details.clear()
        return True
    except Exception:
        return False