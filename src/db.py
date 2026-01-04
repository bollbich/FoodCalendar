import psycopg2
import streamlit as st
import os


# --- CONEXIÓN A LA BASE DE DATOS (SUPABASE) ---
def get_connection():
    try:
        # Intentamos obtener la cadena de los secretos
        conn_str = st.secrets["db"]["connection_string"]
        return psycopg2.connect(conn_str, connect_timeout=5) # Timeout de 5 seg
    except KeyError:
        st.error("❌ No se encontró 'connection_string' en secrets.toml. Revisa los corchetes [db].")
    except psycopg2.OperationalError as e:
        st.error(f"❌ Error de red: No se puede alcanzar Supabase. Detalles: {e}")
    except Exception as e:
        st.error(f"❌ Error inesperado: {e}")
    return None


def init_db():
    """Inicializa las tablas en PostgreSQL si no existen."""
    conn = get_connection()
    if not conn: return

    try:
        c = conn.cursor()

        # 1. Tabla de Ingredientes (SERIAL sustituye a AUTOINCREMENT)
        c.execute('''CREATE TABLE IF NOT EXISTS ingredientes (
            id SERIAL PRIMARY KEY,
            categoria TEXT DEFAULT 'Otros',
            nombre TEXT UNIQUE NOT NULL
        )''')

        # 2. Tabla de Recetas
        c.execute('''CREATE TABLE IF NOT EXISTS recetas (
            id SERIAL PRIMARY KEY,
            nombre TEXT UNIQUE NOT NULL
        )''')

        # 3. Tabla Intermedia
        c.execute('''CREATE TABLE IF NOT EXISTS receta_ingredientes (
            receta_id INTEGER,
            ingrediente_id INTEGER,
            FOREIGN KEY(receta_id) REFERENCES recetas(id) ON DELETE CASCADE,
            FOREIGN KEY(ingrediente_id) REFERENCES ingredientes(id) ON DELETE CASCADE,
            PRIMARY KEY (receta_id, ingrediente_id)
        )''')

        # 4. Tabla de Planificación
        # Nota: Usamos DATE para la fecha, aunque TEXT también funcionaría, DATE es mejor en Postgres
        c.execute('''CREATE TABLE IF NOT EXISTS planificacion (
            fecha DATE, 
            momento TEXT, 
            receta_id INTEGER,
            FOREIGN KEY(receta_id) REFERENCES recetas(id) ON DELETE SET NULL,
            PRIMARY KEY (fecha, momento)
        )''')

        # 5. Tabla de Compras (Inicialización integrada aquí)
        c.execute('''CREATE TABLE IF NOT EXISTS compras_estado (
            semana_inicio DATE, 
            ingrediente_nombre TEXT, 
            comprado BOOLEAN DEFAULT FALSE,                  
            PRIMARY KEY (semana_inicio, ingrediente_nombre)
        )''')

        conn.commit()
    except Exception as e:
        conn.rollback()
        st.error(f"Error inicializando DB: {e}")
    finally:
        conn.close()


def run_query(query, params=(), return_data=False):
    """Ejecuta una query genérica."""
    conn = get_connection()
    if not conn: return None

    try:
        c = conn.cursor()
        c.execute(query, params)
        conn.commit()
        if return_data:
            return c.fetchall()
    except Exception as e:
        conn.rollback()
        print(f"Error DB Query: {e}")  # Útil para debug en logs
        return None
    finally:
        conn.close()


# --- GESTIÓN DE INGREDIENTES ---
def add_ingredient(nombre, categoria="Otros"):
    conn = get_connection()
    try:
        c = conn.cursor()
        # Usamos %s en lugar de ?
        c.execute("INSERT INTO ingredientes (nombre, categoria) VALUES (%s, %s)", (nombre, categoria))
        conn.commit()
        return True
    except psycopg2.IntegrityError:
        conn.rollback()  # Importante hacer rollback si falla
        return False
    except Exception:
        conn.rollback()
        return False
    finally:
        conn.close()


def get_all_ingredients():
    # El orden se mantiene igual
    return run_query("SELECT id, nombre, categoria FROM ingredientes ORDER BY nombre ASC", return_data=True) or []


def get_ingredients_categories():
    """Devuelve un diccionario con el nombre del ingrediente y su categoría"""
    # Simplificado: En Postgres init_db asegura que las columnas existan,
    # así que no necesitamos el try/except complejo de SQLite
    data = run_query("SELECT nombre, categoria FROM ingredientes", return_data=True)
    if data:
        return {row[0]: (row[1] if row[1] else "Otros") for row in data}
    return {}


def delete_ingredient(ingrediente_id):
    run_query("DELETE FROM ingredientes WHERE id=%s", (ingrediente_id,))


def update_ingredient(ing_id, new_name, new_cat):
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute(
            "UPDATE ingredientes SET nombre = %s, categoria = %s WHERE id = %s",
            (new_name, new_cat, ing_id)
        )
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        return False
    finally:
        conn.close()


# --- GESTIÓN DE RECETAS ---
def ensure_special_recipe(nombre_especial):
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute("SELECT id FROM recetas WHERE nombre = %s", (nombre_especial,))
        if not c.fetchone():
            c.execute("INSERT INTO recetas (nombre) VALUES (%s)", (nombre_especial,))
            conn.commit()
    except Exception:
        conn.rollback()
    finally:
        conn.close()


def create_recipe(nombre_receta, lista_ids_ingredientes):
    conn = get_connection()
    try:
        c = conn.cursor()
        # 1. Crear Receta y obtener ID (Diferente a SQLite)
        # En Postgres usamos "RETURNING id" para obtener el ID generado
        c.execute("INSERT INTO recetas (nombre) VALUES (%s) RETURNING id", (nombre_receta,))
        receta_id = c.fetchone()[0]

        # 2. Asociar ingredientes
        if lista_ids_ingredientes:
            # Opción optimizada: executemany
            valores = [(receta_id, ing_id) for ing_id in lista_ids_ingredientes]
            c.executemany("INSERT INTO receta_ingredientes (receta_id, ingrediente_id) VALUES (%s, %s)", valores)

        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"Error creando receta: {e}")
        return False
    finally:
        conn.close()


def delete_recipe(receta_id):
    run_query("DELETE FROM recetas WHERE id=%s", (receta_id,))


def update_recipe(receta_id, nuevo_nombre, lista_ids_ingredientes):
    conn = get_connection()
    try:
        c = conn.cursor()
        # 1. Actualizar nombre
        c.execute("UPDATE recetas SET nombre = %s WHERE id = %s", (nuevo_nombre, receta_id))

        # 2. Eliminar ingredientes antiguos
        c.execute("DELETE FROM receta_ingredientes WHERE receta_id = %s", (receta_id,))

        # 3. Insertar nuevos (usando executemany para eficiencia)
        if lista_ids_ingredientes:
            valores = [(receta_id, ing_id) for ing_id in lista_ids_ingredientes]
            c.executemany("INSERT INTO receta_ingredientes (receta_id, ingrediente_id) VALUES (%s, %s)", valores)

        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"Error al actualizar: {e}")
        return False
    finally:
        conn.close()


def get_all_recipes():
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
    # Forzamos que la fecha sea un string limpio YYYY-MM-DD
    fecha_str = str(fecha).strip()
    query = '''
        INSERT INTO planificacion (fecha, momento, receta_id) 
        VALUES (%s, %s, %s)
        ON CONFLICT (fecha, momento) 
        DO UPDATE SET receta_id = EXCLUDED.receta_id
    '''
    run_query(query, (fecha_str, momento, receta_id))

def get_plan_range_details(start_date, end_date):
    # Forzamos el formato de fecha para evitar errores de zona horaria o strings mal formados
    query = '''
        SELECT p.fecha::text, p.momento, r.id, r.nombre 
        FROM planificacion p
        JOIN recetas r ON p.receta_id = r.id
        WHERE p.fecha >= %s AND p.fecha <= %s
    '''
    # Usamos >= y <= en lugar de BETWEEN para mayor claridad en Postgres con fechas
    data = run_query(query, (str(start_date), str(end_date)), return_data=True)
    return data if data else []


# --- GESTIÓN DE LA LISTA DE LA COMPRA ---

def init_shopping_db():
    # Esta función ahora es redundante porque init_db ya crea todas las tablas,
    # pero la mantenemos por compatibilidad con tu código existente.
    pass


def get_shopping_status(semana_inicio):
    query = "SELECT ingrediente_nombre, comprado FROM compras_estado WHERE semana_inicio = %s"
    data = run_query(query, (str(semana_inicio),), return_data=True)
    if data:
        return {row[0]: bool(row[1]) for row in data}
    return {}


def update_shopping_status(semana_inicio, ingrediente, estado):
    # Upsert para Postgres
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
    conn = get_connection()
    try:
        c = conn.cursor()
        # En Postgres, TRUNCATE es más rápido y limpia mejor que DELETE
        c.execute("TRUNCATE TABLE planificacion")
        c.execute("TRUNCATE TABLE compras_estado")
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"Error reseteando datos: {e}")
        return False
    finally:
        conn.close()