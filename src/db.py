import sqlite3
import psycopg2
import streamlit as st
import os

DB_PATH = 'data/planner.db'

# --- CONFIGURACIÓN Y CONEXIONES ---

def is_local_mode():
    return st.session_state.get("modo_datos", "Local") == "Local"

def get_sqlite_conn():
    if not os.path.exists('data'): os.makedirs('data')
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

@st.cache_resource
def get_supabase_conn():
    try:
        conn_str = st.secrets["db"]["connection_string"]
        return psycopg2.connect(conn_str)
    except Exception as e:
        st.error(f"Error de conexión con Supabase: {e}")
        return None

def sync_to_db(datos_json):
    """
    Esta es la función que tu app.py llama en el botón de sincronizar.
    He adaptado el nombre para que coincida con tu app.py actual.
    """
    return sync_local_to_cloud()

def run_query(query, params=(), return_data=False):
    """Ejecutor simplificado: SIEMPRE LOCAL"""
    query = query.replace('%s', '?').replace('::text', '')
    
    try:
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            c = conn.cursor()
            c.execute(query, params)
            conn.commit()
            if return_data:
                return c.fetchall()
            return None
    except Exception as e:
        print(f"Error SQLite: {e}")
        return [] if return_data else None

# --- INICIALIZACIÓN ---

def init_db():
    conn = get_sqlite_conn()
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS ingredientes (id INTEGER PRIMARY KEY AUTOINCREMENT, categoria TEXT DEFAULT 'Otros', nombre TEXT UNIQUE)")
    c.execute("CREATE TABLE IF NOT EXISTS recetas (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT UNIQUE)")
    c.execute("CREATE TABLE IF NOT EXISTS receta_ingredientes (receta_id INTEGER, ingrediente_id INTEGER, PRIMARY KEY (receta_id, ingrediente_id))")
    c.execute("CREATE TABLE IF NOT EXISTS planificacion (fecha TEXT, momento TEXT, receta_id INTEGER, PRIMARY KEY (fecha, momento))")
    c.execute("CREATE TABLE IF NOT EXISTS compras_estado (semana_inicio TEXT, ingrediente_nombre TEXT, comprado BOOLEAN, PRIMARY KEY (semana_inicio, ingrediente_nombre))")
    conn.commit()
    conn.close()

def init_local_data():
    """Stub para que app.py no falle al arrancar"""
    init_db()

def ensure_special_recipe(nombre):
    """Crea la receta si no existe (Fix para el error de atributo)"""
    res = run_query("SELECT id FROM recetas WHERE nombre = %s", (nombre,), return_data=True)
    if not res:
        run_query("INSERT INTO recetas (nombre) VALUES (%s)", (nombre,))

# --- GESTIÓN DE INGREDIENTES ---

def add_ingredient(nombre, categoria="Otros"):
    query = "INSERT INTO ingredientes (nombre, categoria) VALUES (%s, %s)"
    try:
        run_query(query, (nombre, categoria))
        return True
    except: return False

def get_all_ingredients(): return run_query("SELECT id, nombre, categoria FROM ingredientes ORDER BY nombre ASC", return_data=True) or []

def get_ingredients_categories():
    data = run_query("SELECT nombre, categoria FROM ingredientes", return_data=True)
    return {r[0]: (r[1] or "Otros") for r in data} if data else {}

def delete_ingredient(ing_id):
    run_query("DELETE FROM ingredientes WHERE id=%s", (ing_id,))

def update_ingredient(ing_id, nombre, categoria):
    run_query("UPDATE ingredientes SET nombre=%s, categoria=%s WHERE id=%s", (nombre, categoria, ing_id))

# --- GESTIÓN DE RECETAS ---

def create_recipe(nombre, lista_ids):
    if is_local_mode():
        conn = get_sqlite_conn()
        try:
            c = conn.cursor()
            c.execute("INSERT INTO recetas (nombre) VALUES (?)", (nombre,))
            rid = c.lastrowid
            for iid in lista_ids:
                c.execute("INSERT INTO receta_ingredientes (receta_id, ingrediente_id) VALUES (?, ?)", (rid, iid))
            conn.commit()
            return True
        except: return False
        finally: conn.close()
    else:
        conn = get_supabase_conn()
        try:
            with conn.cursor() as c:
                c.execute("INSERT INTO recetas (nombre) VALUES (%s) RETURNING id", (nombre,))
                rid = c.fetchone()[0]
                for iid in lista_ids:
                    c.execute("INSERT INTO receta_ingredientes (receta_id, ingrediente_id) VALUES (%s, %s)", (rid, iid))
                conn.commit()
            return True
        except: return False

def get_all_recipes(): return run_query("SELECT id, nombre FROM recetas ORDER BY nombre", return_data=True) or []

def get_recipe_ingredients(rid):
    data = run_query("SELECT i.nombre FROM ingredientes i JOIN receta_ingredientes ri ON i.id = ri.ingrediente_id WHERE ri.receta_id = %s", (rid,), return_data=True)
    return [r[0] for r in data]

def delete_recipe(receta_id):
    run_query("DELETE FROM recetas WHERE id=%s", (receta_id,))

def update_recipe(receta_id, nombre, lista_ids):
    run_query("UPDATE recetas SET nombre=%s WHERE id=%s", (nombre, receta_id))
    run_query("DELETE FROM receta_ingredientes WHERE receta_id=%s", (receta_id,))
    for iid in lista_ids:
        run_query("INSERT INTO receta_ingredientes (receta_id, ingrediente_id) VALUES (%s, %s)", (receta_id, iid))

# --- PLANIFICACIÓN ---

def save_meal_plan(f, m, rid):
    # Guardamos el dato
    run_query("INSERT OR REPLACE INTO planificacion (fecha, momento, receta_id) VALUES (%s, %s, %s)", (str(f), m, rid))
    st.cache_data.clear()

def get_plan_range_details(s, e): 
    return run_query("SELECT p.fecha, p.momento, r.id, r.nombre FROM planificacion p JOIN recetas r ON p.receta_id = r.id WHERE p.fecha BETWEEN %s AND %s", (str(s), str(e)), return_data=True) or []

# --- COMPRA ---

def get_shopping_status(s): 
    data = run_query("SELECT ingrediente_nombre, comprado FROM compras_estado WHERE semana_inicio = %s", (str(s),), return_data=True)
    return {r[0]: bool(r[1]) for r in data} if data else {}

def update_shopping_status(s, i, e): run_query("INSERT OR REPLACE INTO compras_estado (semana_inicio, ingrediente_nombre, comprado) VALUES (%s, %s, %s)", (str(s), i, e))

def clear_shopping_status(s): run_query("DELETE FROM compras_estado WHERE semana_inicio = %s", (str(s),))

# --- SINCRONIZACIÓN BIDIRECCIONAL ---

def sync_local_to_cloud():
    """Sube el archivo .db con reintento de conexión y gestión de errores"""
    if not os.path.exists(DB_PATH):
        return False
    conn = None
    try:
        with open(DB_PATH, 'rb') as f:
            blob_data = f.read()
        st.cache_resource.clear() 
        conn = get_supabase_conn()
        if conn is None:
            return False
        with conn.cursor() as c:
            c.execute("SET statement_timeout = '60s'")
            
            c.execute("""
                UPDATE sistema_backup 
                SET archivo_binario = %s, fecha_sincro = NOW() 
                WHERE id = 1
            """, (psycopg2.Binary(blob_data),))
            conn.commit()
        return True

    except (psycopg2.InterfaceError, psycopg2.OperationalError) as e:
        print(f"Reintentando por error de conexión: {e}")
        return False
    except Exception as e:
        st.error(f"Error crítico al subir: {e}")
        return False
    finally:
        if conn:
            conn.close()

def sync_cloud_to_local():
    """Descarga el archivo .db forzando una conexión nueva"""
    conn = None
    try:
        st.cache_resource.clear()

        conn = get_supabase_conn()
        if conn is None:
            return False

        with conn.cursor() as c:
            c.execute("SET statement_timeout = '60s'")
            c.execute("SELECT archivo_binario FROM sistema_backup WHERE id = 1")
            record = c.fetchone()

            if record and record[0]:
                with open(DB_PATH, 'wb') as f:
                    f.write(record[0])
                return True
            return False

    except Exception as e:
        print(f"Error al bajar binario: {e}")
        if "closed" in str(e).lower():
            st.sidebar.warning("La conexión estaba inactiva. Reintentando...")
        return False
    finally:
        if conn:
            conn.close()