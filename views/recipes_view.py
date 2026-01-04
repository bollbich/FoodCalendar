import streamlit as st
from src import db


def show_recipes_page(es_editor):
    st.header("Gestión de Recetas")

    # Aseguramos la receta especial
    db.ensure_special_recipe("Compra")

    # CARGA DE DATOS SIEMPRE FRESCA (Sin caché)
    all_ings = db.get_all_ingredients()
    opciones_ingredientes = {nombre: id_ing for id_ing, nombre, _ in all_ings}
    recetas_existentes = db.get_all_recipes()

    # Selector de modo (sustituye a st.tabs para mayor estabilidad)
    modo = st.radio("Acción", ["➕ Crear Nueva", "✏️ Editar / Ver Recetas"], horizontal=True, key="modo_recetas")

    if modo == "➕ Crear Nueva":
        if not es_editor:
            st.warning("No tienes permisos para crear recetas.")
        else:
            with st.container(border=True):
                nom = st.text_input("Nombre del Plato", key="crear_nom")
                ings = st.multiselect("Ingredientes", options=opciones_ingredientes.keys(), key="crear_ings")

                if st.button("Guardar Nueva Receta"):
                    if nom and ings:
                        ids = [opciones_ingredientes[x] for x in ings]
                        if db.create_recipe(nom, ids):
                            st.toast(f"✅ Receta '{nom}' creada")
                            st.rerun()  # Recarga para que aparezca en la lista de abajo
                        else:
                            st.error("Error al guardar.")
                    else:
                        st.warning("Completa los campos.")

    elif modo == "✏️ Editar / Ver Recetas":
        if not recetas_existentes:
            st.info("No hay recetas.")
        else:
            # Botón rápido para ir a la Compra General
            if st.button("🛒 Ir a Lista de Compra General"):
                for r_id, r_nom in recetas_existentes:
                    if r_nom == "Compra":
                        st.session_state["selector_editar_receta"] = (r_id, r_nom)
                        st.rerun()

            # Selector de receta
            # Al no tener caché, 'recetas_existentes' es la lista REAL de la DB
            receta_selec = st.selectbox(
                "Selecciona una receta",
                options=recetas_existentes,
                format_func=lambda x: x[1],
                key="selector_editar_receta"
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
                                st.toast("Actualizado")
                                st.rerun()

                        if col2.form_submit_button("🗑️ Eliminar", disabled=es_receta_especial):
                            if db.delete_recipe(id_r):
                                # Limpieza total del estado para que el selector no busque la receta muerta
                                if "selector_editar_receta" in st.session_state:
                                    del st.session_state["selector_editar_receta"]
                                st.rerun()