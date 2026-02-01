import psycopg2
import json
import streamlit as st
from datetime import datetime

# --- UTILIDADES DE MODO ---
def get_mode():
    """Devuelve 'JSON' o 'QUERY'"""
    return st.session_state.get("modo_operacion", "JSON")

def is_json_mode():
    return get_mode() == "JSON"

# --- INICIALIZACIÓN DEL MASTER JSON ---
def init_local_data():
    """Carga los datos. Si no hay JSON en la nube, succiona las tablas SQL."""
    if "master_json" not in st.session_state:
        remote_data = load_from_db()

        if remote_data and len(remote_data.get("ingredientes", [])) > 0:
            st.session_state.master_json = remote_data
        else:
            st.warning("⚠️ No se encontró backup JSON. Importando datos desde SQL...")

            ing = run_query("SELECT id, nombre, categoria FROM ingredientes", return_data=True) or []
            rec = run_query("SELECT id, nombre FROM recetas", return_data=True) or []
            ri = run_query("SELECT receta_id, ingrediente_id FROM receta_ingredientes", return_data=True) or []
            # Convertimos fechas a string para el JSON
            plan = run_query("SELECT fecha::text, momento, receta_id FROM planificacion", return_data=True) or []
            comp = run_query("SELECT semana_inicio::text, ingrediente_nombre, comprado FROM compras_estado",
                             return_data=True) or []

            st.session_state.master_json = {
                "ingredientes": [list(x) for x in ing],
                "recetas": [list(x) for x in rec],
                "receta_ingredientes": [list(x) for x in ri],
                "planificacion": [list(x) for x in plan],
                "compras_estado": [list(x) for x in comp]
            }
            st.success("✅ Importación completada. Recuerda Sincronizar al terminar.")

# --- CONEXIÓN Y CONSULTAS BASE ---
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
            if return_data: return c.fetchall()
    except Exception as e:
        conn.rollback()
        print(f"Error DB Query: {e}")
        return None

# --- SINCRONIZACIÓN MACRO ---
def sync_to_db(master_json):
    """Sincronización bruta: sube TODO el estado actual"""
    query = """
        INSERT INTO app_sync (key, content, updated_at) 
        VALUES ('master_data', %s, CURRENT_TIMESTAMP)
        ON CONFLICT (key) DO UPDATE SET content = EXCLUDED.content, updated_at = CURRENT_TIMESTAMP
    """
    # Convertimos fechas a string para que el JSON no explote
    data_to_save = json.loads(json.dumps(master_json, default=str))
    return run_query(query, (json.dumps(data_to_save),))

def load_from_db():
    data = run_query("SELECT content FROM app_sync WHERE key = 'master_data'", return_data=True)
    return data[0][0] if data else None

def init_db():
    """Inicializa las tablas."""
    conn = get_connection()
    if conn:
        with conn.cursor() as c:
            c.execute('''CREATE TABLE IF NOT EXISTS app_sync (
            key TEXT PRIMARY KEY,
            content JSONB,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''')
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
    if is_json_mode():
        data = st.session_state.master_json["ingredientes"]
        if any(i[1].lower() == nombre.lower() for i in data): return False
        new_id = max([i[0] for i in data], default=0) + 1
        data.append([new_id, nombre, categoria])
        return True
    else:
        query = "INSERT INTO ingredientes (nombre, categoria) VALUES (%s, %s)"
        return run_query(query, (nombre, categoria)) is not None

@st.cache_data
def get_all_ingredients():
    if is_json_mode():
        return sorted(st.session_state.master_json["ingredientes"], key=lambda x: x[1])
    return run_query("SELECT id, nombre, categoria FROM ingredientes ORDER BY nombre ASC", return_data=True) or []

def delete_ingredient(ingrediente_id):
    if is_json_mode():
        st.session_state.master_json["ingredientes"] = [i for i in st.session_state.master_json["ingredientes"] if i[0] != ingrediente_id]
        st.session_state.master_json["receta_ingredientes"] = [ri for ri in st.session_state.master_json["receta_ingredientes"] if ri[1] != ingrediente_id]
    else:
        run_query("DELETE FROM ingredientes WHERE id=%s", (ingrediente_id,))
        get_all_ingredients.clear()

@st.cache_data
def get_ingredients_categories():
    if is_json_mode():
        return {i[1]: i[2] for i in st.session_state.master_json["ingredientes"]}
    data = run_query("SELECT nombre, categoria FROM ingredientes", return_data=True)
    return {row[0]: (row[1] or "Otros") for row in data} if data else {}

def update_ingredient(ing_id, new_name, new_cat):
    if is_json_mode():
        for i in st.session_state.master_json["ingredientes"]:
            if i[0] == ing_id:
                i[1], i[2] = new_name, new_cat
                return True
        return False
    else:
        query = "UPDATE ingredientes SET nombre = %s, categoria = %s WHERE id = %s"
        res = run_query(query, (new_name, new_cat, ing_id))
        get_all_ingredients.clear()
        return res is not None

# --- GESTIÓN PLANIFICACIÓN ---
def save_meal_plan(fecha, momento, receta_id):
    fecha_s = str(fecha)
    if is_json_mode():
        plan = st.session_state.master_json["planificacion"]
        # Filtramos para quitar el registro viejo (simular el ON CONFLICT)
        new_plan = [p for p in plan if not (p[0] == fecha_s and p[1] == momento)]
        new_plan.append([fecha_s, momento, receta_id])
        st.session_state.master_json["planificacion"] = new_plan
        return True
    else:
        query = """
            INSERT INTO planificacion (fecha, momento, receta_id) 
            VALUES (%s, %s, %s)
            ON CONFLICT (fecha, momento) DO UPDATE SET receta_id = EXCLUDED.receta_id
        """
        run_query(query, (fecha_s, momento, receta_id))
        get_plan_range_details.clear()
        return True


@st.cache_data
def get_plan_range_details(start_date, end_date):
    start_s = str(start_date)
    end_s = str(end_date)

    if is_json_mode():
        plan = st.session_state.master_json.get("planificacion", [])
        # Creamos el diccionario de nombres asegurando que el ID sea int para comparar
        recetas_dict = {int(r[0]): r[1] for r in st.session_state.master_json.get("recetas", [])}

        resultado = []
        for p in plan:
            if start_s <= p[0] <= end_s:
                # --- EL ARREGLO ESTÁ AQUÍ ---
                # Si p[2] existe, lo hacemos int. Si es None, usamos None.
                id_receta = int(p[2]) if p[2] is not None else None
                nombre_receta = recetas_dict.get(id_receta, "") if id_receta else ""

                resultado.append([p[0], p[1], id_receta, nombre_receta])
        return resultado
    else:
        # Modo SQL (ya lo tenías bien, pero asegúrate de usar LEFT JOIN)
        query = """
            SELECT p.fecha::text, p.momento, p.receta_id, r.nombre 
            FROM planificacion p
            LEFT JOIN recetas r ON p.receta_id = r.id
            WHERE p.fecha >= %s AND p.fecha <= %s
        """
        return run_query(query, (start_s, end_s), return_data=True) or []

# --- GESTIÓN DE RECETAS ---
def ensure_special_recipe(nombre_especial):
    """Asegura que exista una receta (como 'Comida fuera') tanto en JSON como en SQL"""
    if is_json_mode():
        # Lógica para JSON
        recetas = st.session_state.master_json["recetas"]
        # Comprobamos si ya existe el nombre
        if not any(r[1] == nombre_especial for r in recetas):
            new_id = max([r[0] for r in recetas], default=0) + 1
            recetas.append([new_id, nombre_especial])
            return True
    else:
        # Lógica para SQL (tu código original optimizado)
        conn = get_connection()
        if not conn: return False
        try:
            with conn.cursor() as c:
                c.execute("SELECT id FROM recetas WHERE nombre = %s", (nombre_especial,))
                if not c.fetchone():
                    c.execute("INSERT INTO recetas (nombre) VALUES (%s)", (nombre_especial,))
                    conn.commit()
            return True
        except Exception as e:
            if conn: conn.rollback()
            print(f"Error en ensure_special_recipe: {e}")
            return False

def create_recipe(nombre_receta, lista_ids_ingredientes):
    if is_json_mode():
        recetas = st.session_state.master_json["recetas"]
        new_id = max([r[0] for r in recetas], default=0) + 1
        recetas.append([new_id, nombre_receta])
        for ing_id in lista_ids_ingredientes:
            st.session_state.master_json["receta_ingredientes"].append([new_id, ing_id])
        return True
    else:
        conn = get_connection()
        try:
            with conn.cursor() as c:
                c.execute("INSERT INTO recetas (nombre) VALUES (%s) RETURNING id", (nombre_receta,))
                receta_id = c.fetchone()[0]

                if lista_ids_ingredientes:
                    valores = [(receta_id, ing_id) for ing_id in lista_ids_ingredientes]
                    c.executemany("INSERT INTO receta_ingredientes (receta_id, ingrediente_id) VALUES (%s, %s)",
                                  valores)
                conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            print(f"Error creando receta: {e}")
            return False
        pass

@st.cache_data
def get_all_recipes():
    if is_json_mode():
        return sorted(st.session_state.master_json["recetas"], key=lambda x: x[1])
    return run_query("SELECT id, nombre FROM recetas ORDER BY nombre", return_data=True) or []

def delete_recipe(receta_id):
    if is_json_mode():
        st.session_state.master_json["recetas"] = [r for r in st.session_state.master_json["recetas"] if r[0] != receta_id]
        st.session_state.master_json["receta_ingredientes"] = [ri for ri in st.session_state.master_json["receta_ingredientes"] if ri[0] != receta_id]
    else:
        run_query("DELETE FROM recetas WHERE id=%s", (receta_id,))

def update_recipe(receta_id, nuevo_nombre, lista_ids_ingredientes):
    if is_json_mode():
        for r in st.session_state.master_json["recetas"]:
            if r[0] == receta_id: r[1] = nuevo_nombre
        st.session_state.master_json["receta_ingredientes"] = [ri for ri in st.session_state.master_json["receta_ingredientes"] if ri[0] != receta_id]
        for ing_id in lista_ids_ingredientes:
            st.session_state.master_json["receta_ingredientes"].append([receta_id, ing_id])
        return True
    else:
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

def get_recipe_ingredients(receta_id):
    if is_json_mode():
        ing_ids = [ri[1] for ri in st.session_state.master_json["receta_ingredientes"] if ri[0] == receta_id]
        return [i[1] for i in st.session_state.master_json["ingredientes"] if i[0] in ing_ids]
    query = "SELECT i.nombre FROM ingredientes i JOIN receta_ingredientes ri ON i.id = ri.ingrediente_id WHERE ri.receta_id = %s"
    data = run_query(query, (receta_id,), return_data=True)
    return [row[0] for row in data] if data else []


# --- GESTIÓN COMPRAS ---
def get_shopping_status(semana_inicio):
    semana_s = str(semana_inicio)
    if is_json_mode():
        compras = st.session_state.master_json.get("compras_estado", [])
        return {c[1]: c[2] for c in compras if c[0] == semana_s}
    query = "SELECT ingrediente_nombre, comprado FROM compras_estado WHERE semana_inicio = %s"
    data = run_query(query, (semana_s,), return_data=True)
    return {row[0]: bool(row[1]) for row in data} if data else {}


def update_shopping_status(semana_inicio, ingrediente, estado):
    semana_s = str(semana_inicio)
    if is_json_mode():
        compras = st.session_state.master_json["compras_estado"]
        st.session_state.master_json["compras_estado"] = [c for c in compras if not (c[0] == semana_s and c[1] == ingrediente)]
        st.session_state.master_json["compras_estado"].append([semana_s, ingrediente, estado])
    else:
        query = "INSERT INTO compras_estado (semana_inicio, ingrediente_nombre, comprado) VALUES (%s,%s,%s) ON CONFLICT (semana_inicio, ingrediente_nombre) DO UPDATE SET comprado = EXCLUDED.comprado"
        run_query(query, (semana_s, ingrediente, estado))

def clear_shopping_status(semana_inicio):
    if is_json_mode():
        semana_s = str(semana_inicio)
        st.session_state.master_json["compras_estado"] = [c for c in st.session_state.master_json["compras_estado"] if c[0] != semana_s]
    else:
        run_query("DELETE FROM compras_estado WHERE semana_inicio = %s", (str(semana_inicio),))


def reset_historical_data():
    if is_json_mode():
        st.session_state.master_json["planificacion"] = []
        st.session_state.master_json["compras_estado"] = []
        return True
    run_query("TRUNCATE TABLE planificacion")
    run_query("TRUNCATE TABLE compras_estado")
    return True