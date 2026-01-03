import streamlit as st
from datetime import timedelta
from src import db, logic

def show_shopping_list_page(change_date):
    st.header("Lista de la Compra")
    db.init_shopping_db()

    # --- 1. NAVEGACIÓN UNIFICADA ---
    c_nav1, c_nav2, c_nav3 = st.columns([1, 2, 1])

    with c_nav1:
        if st.button("⬅️ Anterior", key="btn_prev_compra", use_container_width=True):
            change_date(dias=-7)
            st.rerun()

    with c_nav2:
        def update_compra_date():
            change_date(nueva_fecha=st.session_state.selector_fecha_compra_input)

        st.date_input(
            "Semana del",
            value=st.session_state["fecha_global"],
            key="selector_fecha_compra_input",
            on_change=update_compra_date
        )

    with c_nav3:
        if st.button("Siguiente ➡️", key="btn_next_compra", use_container_width=True):
            change_date(dias=7)
            st.rerun()

    # --- 2. LÓGICA DE DATOS ---
    start_w = logic.get_start_of_week(st.session_state["fecha_global"])
    end_w = start_w + timedelta(days=6)
    st.info(f"📋 Listado del **{start_w.strftime('%d/%m')}** al **{end_w.strftime('%d/%m/%Y')}**")

    datos_plan = db.get_plan_range_details(start_w, end_w)
    lista_bruta = logic.extract_ingredients_from_plan(datos_plan, db)
    conteo_ingredientes = logic.aggregate_ingredients(lista_bruta)

    if not conteo_ingredientes:
        st.warning("📭 No hay comidas planificadas para esta semana.")
    else:
        estado_compras = db.get_shopping_status(start_w)
        categorias_dict = db.get_ingredients_categories()

        # --- 3. BARRA DE PROGRESO ---
        total_items = len(conteo_ingredientes)
        comprados_count = sum(1 for ing in conteo_ingredientes if estado_compras.get(ing, False))
        progreso = comprados_count / total_items if total_items > 0 else 0
        st.progress(progreso, text=f"Progreso: {comprados_count} de {total_items}")

        # --- 4. LISTA POR CATEGORÍAS ---
        agrupados = {}
        for ing, cant in conteo_ingredientes.items():
            cat = categorias_dict.get(ing, "Otros")
            if cat not in agrupados: agrupados[cat] = []
            agrupados[cat].append((ing, cant))

        for cat in sorted(agrupados.keys()):
            with st.expander(f"{cat}", expanded=True):
                c1, c2 = st.columns(2)
                for idx, (ingrediente, cantidad) in enumerate(sorted(agrupados[cat])):
                    col = c1 if idx % 2 == 0 else c2
                    esta_marcado = estado_compras.get(ingrediente, False)

                    nuevo_estado = col.checkbox(
                        f"{ingrediente} (x{cantidad})",
                        value=esta_marcado,
                        key=f"chk_{start_w}_{ingrediente}"
                    )

                    if nuevo_estado != esta_marcado:
                        db.update_shopping_status(start_w, ingrediente, nuevo_estado)
                        st.rerun()

        st.divider()

        # --- 5. BOTÓN DE RESET ---
        col_reset, _ = st.columns([1, 2])
        with col_reset:
            if st.button("🗑️ Vaciar lista de esta semana", key="btn_reset_compra_final"):
                db.clear_shopping_status(start_w)
                # Limpiar las claves de los checkboxes del session_state para que se desmarquen visualmente
                prefijo = f"chk_{start_w}"
                for key in list(st.session_state.keys()):
                    if key.startswith(prefijo):
                        del st.session_state[key]
                st.rerun()