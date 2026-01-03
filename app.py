import streamlit as st
import os
from datetime import date
from src import db, logic
from views import ingredients_view, recipes_view, planner_view, shopping_view

# 1. Inicialización y Configuración
if not os.path.exists('data'): os.makedirs('data')
db.init_db()
st.set_page_config(page_title="Planificador Pro V2", layout="wide", page_icon="🥑")

# 2. Gestión de Fechas
if "fecha_global" not in st.session_state:
    st.session_state["fecha_global"] = logic.get_start_of_week(date.today())

def change_date(dias=0, nueva_fecha=None):
    from datetime import timedelta
    base = nueva_fecha if nueva_fecha else st.session_state["fecha_global"] + timedelta(days=dias)
    st.session_state["fecha_global"] = logic.get_start_of_week(base)
    st.rerun()

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
st.sidebar.subheader("Seguridad")
st.sidebar.divider()
# --- MANTENIMIENTO (Solo visible para editores) ---
if es_editor:
    with st.sidebar.expander("⚙️ Mantenimiento Avanzado"):
        # Botón de Descarga
        try:
            with open("data/planner.db", "rb") as f:
                st.download_button(
                    label="📥 Copia de Seguridad (.db)",
                    data=f,
                    file_name=f"backup_planner_{date.today()}.db",
                    mime="application/x-sqlite3"
                )
        except FileNotFoundError:
            st.error("Archivo DB no encontrado")

        st.divider()
        st.warning("Zona de Peligro")
        confirmar = st.checkbox("Confirmar limpieza total")
        if st.button("🗑️ Borrar Historial", disabled=not confirmar, key="btn_reset_sidebar"):
            if db.reset_historical_data():
                st.success("Historial borrado")
                st.rerun()

# 4. Enrutador (Router)
if opcion == "📅 Planificador":
    planner_view.show_planner_page(es_editor, change_date)

elif opcion == "📖 Recetas":
    recipes_view.show_recipes_page(es_editor)

elif opcion == "🍅 Ingredientes":
    ingredients_view.show_ingredients_page(es_editor)

elif opcion == "🛒 Compra":
    shopping_view.show_shopping_list_page(change_date)