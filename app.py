import streamlit as st
import os
from datetime import date
from src import db, logic
from views import ingredients_view, recipes_view, planner_view, shopping_view

# 1. Inicialización y Configuración
if not os.path.exists('data'): os.makedirs('data')
st.set_page_config(page_title="Planificador Pro V2", layout="wide", page_icon="🥑")
db.init_db()

if "modo_operacion" not in st.session_state:
    st.session_state["modo_operacion"] = "JSON"

db.init_local_data()


# 2. Gestión de Fechas
if "fecha_global" not in st.session_state:
    st.session_state["fecha_global"] = logic.get_start_of_week(date.today())

def change_date(dias=0, nueva_fecha=None):
    from datetime import timedelta
    base = nueva_fecha if nueva_fecha else st.session_state["fecha_global"] + timedelta(days=dias)
    st.session_state["fecha_global"] = logic.get_start_of_week(base)

# 3. Sidebar y Seguridad
st.sidebar.divider()
st.sidebar.subheader("🔐 Acceso Editor")

# Intentamos leer la clave desde Secrets, si no, usamos una por defecto para local
clave_maestra = st.secrets.get("CLAVE_EDITOR")
password_usuario = st.sidebar.text_input("Código de edición", type="password", key="pwd_input")

es_editor = (clave_maestra is not None) and (password_usuario == clave_maestra)

if es_editor:
    st.sidebar.success("Modo Edición Activo")
else:
    st.sidebar.warning("Modo Lectura")

st.sidebar.title("Navegación")
if es_editor:
    opcion = st.sidebar.radio(
        "Ir a:",
        ["📅 Planificador", "📖 Recetas", "🍅 Ingredientes", "🛒 Compra"]
    )
else:
    st.sidebar.warning("🔒 Modo Lectura")
    # Forzamos la opción de Planificador y deshabilitamos el cambio
    opcion = st.sidebar.radio(
        "Ir a:",
        ["📅 Planificador"],
        disabled=True
    )

st.sidebar.divider()
st.sidebar.subheader("🚀 Optimización")

# Selector de Modo (Simplificado)
modo_actual = st.sidebar.radio(
    "Fuente de datos:",
    ["Local (Rápido ⚡)", "Nube (Directo ☁️)"],
    index=0 if st.session_state["modo_operacion"] == "JSON" else 1
)

# Cambiamos el modo y LIMPIAMOS CACHÉ para evitar ver datos viejos
nuevo_modo = "JSON" if "Local" in modo_actual else "QUERY"
if nuevo_modo != st.session_state["modo_operacion"]:
    st.session_state["modo_operacion"] = nuevo_modo
    st.cache_data.clear() # Limpia get_all_ingredients y demás
    st.rerun()

# Botón de Sincronización (Solo en modo JSON)
if st.session_state["modo_operacion"] == "JSON" and es_editor:
    if st.sidebar.button("💾 SUBIR CAMBIOS A LA NUBE", type="primary", use_container_width=True):
        with st.spinner("Sincronizando..."):
            if db.sync_to_db(st.session_state.master_json):
                st.sidebar.success("¡Datos guardados!")
            else:
                st.sidebar.error("Error al sincronizar.")

st.sidebar.divider()

# 4. Enrutador (Router)
if opcion == "📅 Planificador":
    planner_view.show_planner_page(es_editor, change_date)

elif opcion == "📖 Recetas":
    recipes_view.show_recipes_page(es_editor)

elif opcion == "🍅 Ingredientes":
    ingredients_view.show_ingredients_page(es_editor)

elif opcion == "🛒 Compra":
    shopping_view.show_shopping_list_page(change_date)

with st.sidebar.expander("DEBUG: Estado de Datos"):
    st.write(f"Modo actual: {st.session_state.get('modo_operacion')}")
    if "master_json" in st.session_state:
        st.write(f"Ingredientes: {len(st.session_state.master_json.get('ingredientes', []))}")
        st.write(f"Recetas: {len(st.session_state.master_json.get('recetas', []))}")
        st.write(f"Planes guardados: {len(st.session_state.master_json.get('planificacion', []))}")
    else:
        st.error("master_json NO INICIALIZADO")

    if "master_json" in st.session_state and len(st.session_state.master_json["planificacion"]) > 0:
        st.write("Muestra del primer plan guardado:", st.session_state.master_json["planificacion"][0])