import streamlit as st
from src import db


def show_recipes_page(es_editor):
    check_messages()
    st.header("Gestión de Recetas")

    db.ensure_special_recipe("Compra")

    all_ings = db.get_all_ingredients()
    opciones_ingredientes = {nombre: id_ing for id_ing, nombre, _ in all_ings}
    recetas_existentes = db.get_all_recipes()

    if "receta_refresher" not in st.session_state:
        st.session_state.receta_refresher = 0

    modo = st.radio("Acción", ["➕ Crear Nueva", "✏️ Editar / Ver Recetas"], horizontal=True, key="modo_recetas")

    if modo == "➕ Crear Nueva":
        if not es_editor:
            st.warning("No tienes permisos.")
        else:
            def guardar_callback():
                nom = st.session_state.crear_nom
                ings = st.session_state.crear_ings
                if nom and ings:
                    ids = [opciones_ingredientes[x] for x in ings]
                    if db.create_recipe(nom, ids):
                        add_message(f"✅ Receta '{nom}' creada", tipo="toast")
                        st.session_state.crear_nom = ""
                        st.session_state.crear_ings = []
                    else:
                        st.error("Error al guardar.")
                else:
                    st.warning("Completa los campos.")

            with st.container(border=True):
                st.text_input("Nombre del Plato", key="crear_nom")
                st.multiselect("Ingredientes", options=opciones_ingredientes.keys(), key="crear_ings")
                st.button("Guardar Nueva Receta", type="primary", on_click=guardar_callback)

    elif modo == "✏️ Editar / Ver Recetas":
        if not recetas_existentes:
            st.info("No hay recetas.")
        else:
            if st.button("🛒 Ir a Lista de Compra General"):
                for r_id, r_nom in recetas_existentes:
                    if r_nom == "Compra":
                        key_actual = f"selector_receta_{st.session_state.receta_refresher}"
                        st.session_state[key_actual] = (r_id, r_nom)
                        st.rerun()
            receta_selec = st.selectbox(
                "Selecciona una receta",
                options=recetas_existentes,
                format_func=lambda x: x[1],
                key=f"selector_receta_{st.session_state.receta_refresher}"
            )

            if receta_selec:
                id_r, nombre_r = receta_selec
                es_receta_especial = (nombre_r == "Compra")
                ings_actuales = db.get_recipe_ingredients(id_r)

                with st.form(key=f"form_edicion_{id_r}"):
                    nuevo_nombre = st.text_input("Nombre", value=nombre_r, disabled=es_receta_especial or not es_editor)
                    nuevos_ings = st.multiselect("Ingredientes", options=opciones_ingredientes.keys(),
                                                 default=ings_actuales, disabled=not es_editor)

                    col1, col2 = st.columns(2)
                    if es_editor:
                        if col1.form_submit_button("💾 Guardar"):
                            ids_n = [opciones_ingredientes[x] for x in nuevos_ings]
                            if db.update_recipe(id_r, nuevo_nombre, ids_n):
                                add_message("✅ Receta actualizada", tipo="toast")
                                st.rerun()

                        if col2.form_submit_button("🗑️ Eliminar", disabled=es_receta_especial):
                            if db.delete_recipe(id_r):
                                st.session_state.receta_refresher += 1
                                add_message("🗑️ Receta eliminada", tipo="toast")
                                st.rerun()

def add_message(texto, tipo="info"):
    """Añade un mensaje a la cola para ser mostrado tras el rerun"""
    if "cola_mensajes" not in st.session_state:
        st.session_state.cola_mensajes = []
    st.session_state.cola_mensajes.append({"texto": texto, "tipo": tipo})

def check_messages():
    """Revisa si hay mensajes pendientes, los lanza y vacía la lista"""
    if "cola_mensajes" in st.session_state and st.session_state.cola_mensajes:
        for msg in st.session_state.cola_mensajes:
            if msg["tipo"] == "toast":
                st.toast(msg["texto"])
            elif msg["tipo"] == "success":
                st.success(msg["texto"])
            elif msg["tipo"] == "error":
                st.error(msg["texto"])
        st.session_state.cola_mensajes = []