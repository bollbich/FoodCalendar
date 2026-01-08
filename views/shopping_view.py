import streamlit as st
from datetime import timedelta
from src import db, logic


@st.fragment
def render_shopping_list_fragment(conteo_ingredientes, start_w, categorias_dict):
    """Maneja el estado en memoria y guarda solo al pulsar el botón"""

    # 1. CARGA INICIAL: Solo si no hemos cargado esta semana aún
    state_key = f"carrito_{start_w}"
    if state_key not in st.session_state:
        # Traemos de la DB los estados actuales para rellenar el estado inicial
        st.session_state[state_key] = db.get_shopping_status(start_w)

    # 2. BARRA DE PROGRESO (basada en el estado de sesión actual)
    total_items = len(conteo_ingredientes)
    comprados_count = sum(1 for ing in conteo_ingredientes if st.session_state[state_key].get(ing, False))
    progreso = comprados_count / total_items if total_items > 0 else 0
    st.progress(progreso, text=f"Progreso: {comprados_count} de {total_items}")

    # 3. AGRUPAR POR CATEGORÍAS
    agrupados = {}
    for ing, cant in conteo_ingredientes.items():
        cat = categorias_dict.get(ing, "Otros")
        if cat not in agrupados: agrupados[cat] = []
        agrupados[cat].append((ing, cant))

    # 4. RENDERIZAR LISTA (Modificando solo memoria)
    for cat in sorted(agrupados.keys()):
        with st.expander(f"📦 {cat}", expanded=True):
            c1, c2 = st.columns(2)
            for idx, (ingrediente, cantidad) in enumerate(sorted(agrupados[cat])):
                col = c1 if idx % 2 == 0 else c2

                st.session_state[state_key][ingrediente] = col.checkbox(
                    f"{ingrediente} (x{cantidad})",
                    value=st.session_state[state_key].get(ingrediente, False),
                    key=f"chk_{start_w}_{ingrediente}"
                )

    st.write("---")

    # 5. BOTÓN DE GUARDAR (Acción única)
    c_btn1, c_btn2 = st.columns(2)

    with c_btn1:
        if st.button("💾 Guardar Cambios", use_container_width=True, type="primary"):
            # Aquí hacemos el guardado masivo
            for ingrediente, estado in st.session_state[state_key].items():
                db.update_shopping_status(start_w, ingrediente, estado)
            st.success("¡Guardado!")

    with c_btn2:
        if st.button("🗑️ Vaciar lista", use_container_width=True):
            db.clear_shopping_status(start_w)
            # Limpiamos el estado en memoria
            st.session_state[state_key] = {}
            # Limpiamos los widgets
            for key in list(st.session_state.keys()):
                if key.startswith(f"chk_{start_w}"):
                    del st.session_state[key]
            st.rerun(scope="fragment")


def show_shopping_list_page(change_date):
    st.header("Lista de la Compra")

    # --- NAVEGACIÓN ---
    c_nav1, c_nav2, c_nav3 = st.columns([1, 2, 1])
    with c_nav1:
        if st.button("⬅️ Anterior", key="btn_prev_compra", use_container_width=True):
            change_date(dias=-7)
            st.rerun()
    with c_nav2:
        def update_compra_date():
            change_date(nueva_fecha=st.session_state.selector_fecha_compra_input)

        st.date_input("Semana del", value=st.session_state["fecha_global"],
                      key="selector_fecha_compra_input", on_change=update_compra_date)
    with c_nav3:
        if st.button("Siguiente ➡️", key="btn_next_compra", use_container_width=True):
            change_date(dias=7)
            st.rerun()

    start_w = logic.get_start_of_week(st.session_state["fecha_global"])
    end_w = start_w + timedelta(days=6)
    st.info(f"📋 Listado del **{start_w.strftime('%d/%m')}** al **{end_w.strftime('%d/%m/%Y')}**")

    datos_plan = db.get_plan_range_details(start_w, end_w)
    lista_bruta = logic.extract_ingredients_from_plan(datos_plan, db)
    conteo_ingredientes = logic.aggregate_ingredients(lista_bruta)

    if not conteo_ingredientes:
        st.warning("📭 No hay comidas planificadas para esta semana.")
    else:
        categorias_dict = db.get_ingredients_categories()
        render_shopping_list_fragment(conteo_ingredientes, start_w, categorias_dict)