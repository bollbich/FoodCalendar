import streamlit as st
import os
from datetime import date
from src import db, logic
from views import ingredients_view, recipes_view, planner_view, shopping_view

# 1. Inicialización y Configuración
st.set_page_config(page_title="Planificador Pro V2", layout="wide", page_icon="🥑")

# Inicializamos la base de datos local (SQLite)
db.init_db()

# --- AUTO-SINCRONIZACIÓN AL INICIO DE SESIÓN ---
if "sincronizado" not in st.session_state:
    with st.status("🔄 Sincronizando con la nube...", expanded=False) as status:
        st.write("Conectando a Supabase...")
        if db.sync_cloud_to_local():
            st.write("✅ Archivo .db descargado con éxito.")
            st.cache_data.clear()
            status.update(label="Sincronización completada", state="complete", expanded=False)
        else:
            st.write("⚠️ No se encontró backup o error de conexión.")
            status.update(label="Usando base de datos local", state="error", expanded=False)

    st.session_state["sincronizado"] = True

# Sincronizamos el estado del modo de datos (Local por defecto)
if "modo_datos" not in st.session_state:
    st.session_state["modo_datos"] = "Local"

# 2. Gestión de Fechas (Semana actual)
if "fecha_global" not in st.session_state:
    st.session_state["fecha_global"] = logic.get_start_of_week(date.today())

def change_date(dias=0, nueva_fecha=None):
    from datetime import timedelta
    base = nueva_fecha if nueva_fecha else st.session_state["fecha_global"] + timedelta(days=dias)
    st.session_state["fecha_global"] = logic.get_start_of_week(base)

# 3. Sidebar: Acceso y Navegación
st.sidebar.title("🥑 Menú Principal")
st.sidebar.divider()

# --- SEGURIDAD: ACCESO EDITOR ---
st.sidebar.subheader("🔐 Acceso Editor")
clave_maestra = st.secrets.get("CLAVE_EDITOR")
password_usuario = st.sidebar.text_input("Código de edición", type="password", key="pwd_input")
es_editor = (password_usuario == clave_maestra)

if es_editor:
    st.sidebar.success("Modo Edición Activo")
else:
    st.sidebar.warning("Modo Lectura")

# --- NAVEGACIÓN ---
if es_editor:
    opcion = st.sidebar.radio(
        "Ir a:",
        ["📅 Planificador", "📖 Recetas", "🍅 Ingredientes", "🛒 Compra"]
    )
else:
    opcion = "📅 Planificador"
    st.sidebar.info("Navegación restringida a solo lectura.")

# --- 4. BLOQUE DE SINCRONIZACIÓN BINARIA (CON SEGURO) ---
if es_editor:
    st.sidebar.divider()
    st.sidebar.write("☁️ **Sincronización Nube**")

    # Check de confirmación para evitar accidentes
    confirmar_bajar = st.sidebar.checkbox("Confirmar sobreescribir local",
                                          help="Marca esto para poder bajar los datos de la nube y borrar los actuales.")

    col_down, col_up = st.sidebar.columns(2)

    # BOTÓN PARA IMPORTAR (Bajar el archivo de la nube al PC)
    # Solo se activa el botón si el checkbox está marcado
    if col_down.button("📥 BAJAR", disabled=not confirmar_bajar, type="secondary"):
        with st.spinner("Bajando..."):
            if db.sync_cloud_to_local():
                st.cache_data.clear()
                st.toast("✅ Datos recuperados correctamente")
                st.rerun()
            else:
                st.sidebar.error("Sin backup")
    # BOTÓN PARA EXPORTAR (Subir tu archivo del PC a la nube)
    if col_up.button("📤 SUBIR", type="primary"):
        with st.spinner("Subiendo..."):
            if db.sync_local_to_cloud():
                st.toast("☁️ Copia guardada en la nube")
                st.cache_data.clear()
            else:
                st.sidebar.error("Error al subir")

# 5. Enrutador de Vistas (Router)
if opcion == "📅 Planificador":
    planner_view.show_planner_page(es_editor, change_date)

elif opcion == "📖 Recetas":
    recipes_view.show_recipes_page(es_editor)

elif opcion == "🍅 Ingredientes":
    ingredients_view.show_ingredients_page(es_editor)

elif opcion == "🛒 Compra":
    shopping_view.show_shopping_list_page(change_date)
