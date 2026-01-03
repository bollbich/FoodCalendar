import streamlit as st
from src import db

def show_recipes_page(es_editor):
    st.header("Gestión de Recetas")

    # Aseguramos que exista la receta especial "Compra"
    db.ensure_special_recipe("Compra")

    all_ings = db.get_all_ingredients()
    # Diccionario para mapear nombres a IDs
    opciones_ingredientes = {nombre: id_ing for id_ing, nombre, _ in all_ings}
    recetas_existentes = db.get_all_recipes()

    tab1, tab2 = st.tabs(["➕ Crear Nueva", "✏️ Editar / Ver Recetas"])

    # --- TAB 1: CREAR ---
    with tab1:
        if not es_editor:
            st.warning("No tienes permisos para crear recetas.")
        else:
            def save_new_recipe():
                nom = st.session_state.crear_receta_nombre.strip()
                ings = st.session_state.crear_receta_ings

                if nom and ings:
                    ids = [opciones_ingredientes[x] for x in ings]
                    if db.create_recipe(nom, ids):
                        st.toast(f"✅ Receta '{nom}' creada")
                        st.session_state.crear_receta_nombre = ""
                        st.session_state.crear_receta_ings = []
                    else:
                        st.error("Error al guardar la receta.")
                else:
                    st.warning("Escribe un nombre y elige ingredientes.")

            st.text_input("Nombre del Plato", key="crear_receta_nombre")
            st.multiselect("Ingredientes", options=opciones_ingredientes.keys(), key="crear_receta_ings")
            st.button("Guardar Nueva Receta", on_click=save_new_recipe)

    # --- TAB 2: EDITAR ---
    with tab2:
        if not recetas_existentes:
            st.info("No hay recetas para editar.")
        else:
            # 1. Inicialización limpia del estado
            if "selector_editar_receta" not in st.session_state:
                st.session_state["selector_editar_receta"] = recetas_existentes[0]

            # 2. Botón de acceso rápido
            if st.button("🛒 Editar Lista de Compra General", use_container_width=True):
                for r_id, r_nom in recetas_existentes:
                    if r_nom == "Compra":
                        st.session_state["selector_editar_receta"] = (r_id, r_nom)
                        st.rerun()

            # 3. El Selector
            receta_selec = st.selectbox(
                "Selecciona una receta para modificar",
                recetas_existentes,
                format_func=lambda x: x[1],
                key="selector_editar_receta"
            )

            if receta_selec:
                id_r, nombre_r = receta_selec
                es_receta_especial = (nombre_r == "Compra")
                ings_actuales = db.get_recipe_ingredients(id_r)

                # 4. Formulario de edición
                with st.form(key=f"form_edit_receta_{id_r}"):
                    nuevo_nombre = st.text_input("Editar nombre", value=nombre_r, disabled=es_receta_especial or not es_editor)
                    nuevos_ings = st.multiselect(
                        "Editar ingredientes",
                        options=opciones_ingredientes.keys(),
                        default=ings_actuales,
                        disabled=not es_editor
                    )

                    col_btn1, col_btn2 = st.columns(2)

                    if es_editor:
                        if col_btn1.form_submit_button("💾 Guardar Cambios", use_container_width=True):
                            ids_n = [opciones_ingredientes[x] for x in nuevos_ings]
                            if db.update_recipe(id_r, nuevo_nombre, ids_n):
                                st.success(f"✅ '{nuevo_nombre}' actualizada")
                                st.rerun()

                        if col_btn2.form_submit_button("🗑️ Eliminar Receta", use_container_width=True,
                                                       disabled=es_receta_especial):
                            db.delete_recipe(id_r)
                            st.session_state["selector_editar_receta"] = recetas_existentes[0]
                            st.rerun()
                    else:
                        st.info("Modo lectura: No se pueden realizar cambios.")

                if es_receta_especial:
                    st.info("ℹ️ Estás editando la **Compra General**. Los ingredientes aquí guardados aparecerán siempre en tu lista semanal.")