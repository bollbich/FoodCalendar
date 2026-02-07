import streamlit as st
from datetime import timedelta
from src import db, logic


@st.fragment
def render_shopping_list_fragment(conteo_detallado, start_w, categorias_dict):
    """Maneja el estado en memoria y guarda solo al pulsar el botón"""
    state_key = f"carrito_{start_w}"
    if state_key not in st.session_state:
        st.session_state[state_key] = db.get_shopping_status(start_w)

    # 1. BARRA DE PROGRESO
    total_items = len(conteo_detallado)
    comprados_count = sum(1 for ing in conteo_detallado if st.session_state[state_key].get(ing, False))
    progreso = comprados_count / total_items if total_items > 0 else 0
    st.progress(progreso, text=f"Progreso: {comprados_count} de {total_items}")

    # 2. AGRUPAR POR CATEGORÍAS
    agrupados = {}
    for ing, datos in conteo_detallado.items():
        cat = categorias_dict.get(ing, "Otros")
        if cat not in agrupados: agrupados[cat] = []
        agrupados[cat].append((ing, datos))

    # 3. RENDERIZAR LISTA
    for cat in sorted(agrupados.keys()):
        with st.expander(f"📦 {cat}", expanded=True):
            c1, c2 = st.columns(2)
            for idx, (ingrediente, datos) in enumerate(sorted(agrupados[cat])):
                col = c1 if idx % 2 == 0 else c2

                cantidad = datos["cantidad"]
                # Formateamos los días para que se vean limpios
                dias_str = ", ".join(sorted(list(datos["dias"])))

                # Checkbox con nombre en negrita y días en cursiva debajo
                st.session_state[state_key][ingrediente] = col.checkbox(
                    f"**{ingrediente}** (x{cantidad})  \n  *{dias_str}*",
                    value=st.session_state[state_key].get(ingrediente, False),
                    key=f"chk_{start_w}_{ingrediente}"
                )

    st.write("---")

    # 4. BOTONES DE ACCIÓN
    c_btn1, c_btn2 = st.columns(2)
    with c_btn1:
        if st.button("💾 Guardar Cambios", use_container_width=True, type="primary"):
            for ingrediente, estado in st.session_state[state_key].items():
                db.update_shopping_status(start_w, ingrediente, estado)
            st.toast("✅ ¡Lista actualizada!")

    with c_btn2:
        if st.button("🗑️ Vaciar lista", use_container_width=True):
            db.clear_shopping_status(start_w)
            st.session_state[state_key] = {}
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

    # --- LÓGICA DE EXTRACCIÓN BLINDADA ---
    datos_plan = db.get_plan_range_details(start_w, end_w)

    conteo_detallado = {}
    nombres_dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

    import datetime as dt

    for fecha_raw, momento, receta_id, rec_nombre in datos_plan:
        if receta_id:
            # 1. CONVERSIÓN DE SEGURIDAD: Aseguramos que sea un objeto date
            fecha_obj = fecha_raw
            if isinstance(fecha_raw, str):
                try:
                    fecha_obj = dt.date.fromisoformat(fecha_raw)
                except:
                    fecha_obj = dt.datetime.strptime(fecha_raw, "%Y-%m-%d").date()

            # 2. OBTENER EL DÍA
            try:
                dia_semana = nombres_dias[fecha_obj.weekday()]
            except:
                dia_semana = "S/D"

            # 3. EXTRAER INGREDIENTES
            ingredientes_receta = db.get_recipe_ingredients(receta_id)
            for ing in ingredientes_receta:
                if ing not in conteo_detallado:
                    conteo_detallado[ing] = {"cantidad": 0, "dias": set()}

                conteo_detallado[ing]["cantidad"] += 1
                conteo_detallado[ing]["dias"].add(dia_semana)

    if not conteo_detallado:
        st.warning("📭 No hay ingredientes. Planifica algo primero.")
    else:
        categorias_dict = db.get_ingredients_categories()
        render_shopping_list_fragment(conteo_detallado, start_w, categorias_dict)