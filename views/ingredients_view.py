import streamlit as st
import pandas as pd
from src import db


def show_ingredients_page(es_editor):
    st.header("Gestión de la Despensa")

    tab1, tab2 = st.tabs(["➕ Añadir Nuevo", "✏️ Editar / Ver Listado"])

    # --- TAB 1: AÑADIR ---
    with tab1:
        if not es_editor:
            st.warning("🔒 Modo lectura: No puedes añadir ingredientes.")
        else:
            def save_new_ingredient():
                nombre = st.session_state.nuevo_ing_nombre.strip()
                categoria = st.session_state.nueva_cat_sel

                if nombre:
                    if db.add_ingredient(nombre, categoria):
                        st.toast(f"✅ {nombre} añadido", icon="🛒")
                        st.session_state.nuevo_ing_nombre = ""
                    else:
                        st.error("Ese ingrediente ya existe.")
                else:
                    st.warning("Escribe un nombre.")

            col1, col2 = st.columns([1, 1])
            with col1:
                st.text_input("Nombre del nuevo ingrediente", key="nuevo_ing_nombre")
            with col2:
                st.selectbox("Categoría", [
                    "🥦 Frutería", "🥩 Carnicería", "🧀 Charcuteria", "🐟 Pescaderia", "🥛 Frescos", "🥖 Panadería",
                    "🥫 Despensa", "🧼 Limpieza", "❄️ Congelados", "Otros"
                ], key="nueva_cat_sel")

            st.button("Añadir a la lista", on_click=save_new_ingredient, use_container_width=True)

    # --- TAB 2: EDITAR Y LISTADO ---
    with tab2:
        all_ings = db.get_all_ingredients()

        if not all_ings:
            st.info("La despensa está vacía.")
        else:
            lista_categorias = [
                "🥦 Frutería", "🥩 Carnicería", "🧀 Charcuteria", "🐟 Pescaderia", "🥛 Frescos", "🥖 Panadería",
                "🥫 Despensa", "🧼 Limpieza", "❄️ Congelados", "Otros"
            ]

            df_ings = pd.DataFrame(all_ings, columns=["ID", "Nombre", "Categoría"])

            col_list, col_edit = st.columns([1, 1])

            with col_list:
                st.subheader("Ingredientes")
                event = st.dataframe(
                    df_ings,
                    column_order=("Nombre", "Categoría"),
                    use_container_width=True,
                    height=450,
                    hide_index=True,
                    on_select="rerun",
                    selection_mode="single-row",
                    key="tabla_ings_lateral"
                )

            with col_edit:
                st.subheader("Editar Selección")
                indices = event.selection.rows

                if indices:
                    row_idx = indices[0]

                    if row_idx < len(df_ings):
                        id_i = int(df_ings.iloc[row_idx]["ID"])
                        nombre_i = df_ings.iloc[row_idx]["Nombre"]
                        cat_i = df_ings.iloc[row_idx]["Categoría"]

                        with st.form(key=f"form_edit_ing_{id_i}"):
                            nuevo_nom = st.text_input("Nombre", value=nombre_i, disabled=not es_editor)

                            try:
                                idx_cat = lista_categorias.index(cat_i)
                            except:
                                idx_cat = lista_categorias.index("Otros")

                            nueva_cat = st.selectbox("Categoría", options=lista_categorias, index=idx_cat,
                                                     disabled=not es_editor)

                            if es_editor:
                                c1, c2 = st.columns(2)
                                if c1.form_submit_button("💾 Guardar", use_container_width=True):
                                    if nuevo_nom:
                                        db.update_ingredient(id_i, nuevo_nom, nueva_cat)
                                        st.toast(f"✅ {nuevo_nom} actualizado")
                                        st.rerun()

                                if c2.form_submit_button("🗑️ Borrar", use_container_width=True):
                                    db.delete_ingredient(id_i)
                                    st.warning("Eliminado correctamente")
                                    st.cache_data.clear()
                                    st.rerun()
                            else:
                                st.info("Modo lectura: No se permiten cambios.")
                    else:
                        st.info("Actualizando información...")
                        st.rerun()
                else:
                    st.info("👈 Selecciona un ingrediente en la tabla para editarlo.")