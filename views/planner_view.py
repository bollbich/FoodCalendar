import streamlit as st
from datetime import timedelta
from src import db, logic

def change_date(dias=0, nueva_fecha=None):
    if nueva_fecha is not None:
        base = nueva_fecha
    else:
        base = st.session_state["fecha_global"] + timedelta(days=dias)

    st.session_state["fecha_global"] = logic.get_start_of_week(base)

def get_start_of_week(dt):
    return dt - timedelta(days=dt.weekday())

def show_planner_page(es_editor, change_date):
    st.header("Planificación Semanal")

    # --- NAVEGACIÓN UNIFICADA (Planificador) ---
    col_nav1, col_nav2, col_nav3 = st.columns([1, 2, 1])

    with col_nav1:
        if st.button("⬅️ Semana Anterior", key="btn_prev_plan", use_container_width=True, disabled=not es_editor):
            change_date(dias=-7)

    with col_nav2:
        def update_plan_date():
            change_date(nueva_fecha=st.session_state.selector_fecha_plan_input)

        st.date_input(
            "Seleccionar fecha:",
            value=st.session_state["fecha_global"],
            key="selector_fecha_plan_input",
            on_change=update_plan_date,  # Usamos la función local
            disabled=not es_editor
        )

    with col_nav3:
        if st.button("Semana Siguiente ➡️", key="btn_next_plan", use_container_width=True, disabled=not es_editor):
            change_date(dias=7)

    # Usamos la fecha global para calcular la semana
    start_of_week = logic.get_start_of_week(st.session_state["fecha_global"])

    st.info(
        f"📅 Semana del **{start_of_week.strftime('%d/%m/%Y')}** al **{(start_of_week + timedelta(days=6)).strftime('%d/%m/%Y')}**")

    # 1. Obtenemos fechas y datos
    plan_data = db.get_plan_range_details(start_of_week, start_of_week + timedelta(days=6))
    plan_dict = {(fecha, mom): rec_nombre for fecha, mom, _, rec_nombre in plan_data}

    momentos_config = {
        "Desayuno": "☕",
        "Media Mañana": "🍏",
        "Comida": "🍲",
        "Media Tarde": "🥪",
        "Cena": "🥗",
        "Compra General": "🛒"
    }

    raw_recipes = db.get_all_recipes()
    opciones_recetas = {nombre: id_rec for id_rec, nombre in raw_recipes}
    lista_nombres_recetas = [""] + list(opciones_recetas.keys())

    # 2. Definimos las columnas: 7 para los días y 1 para la leyenda
    columnas = st.columns([0.8, 1, 1, 1, 1, 1, 1, 1])

    dias_nombres = ["Momentos", "Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

    # 3. Dibujamos la LEYENDA (Momentos)
    with columnas[0]:
        st.markdown('<div style="height:80px;margin-top:1px;"></div>', unsafe_allow_html=True)
        for momento, emoji in momentos_config.items():
            st.markdown(f"""
                        <div style="height:38px; display:flex; align-items:center; background-color:#e1f5fe; border-radius:5px; padding-left:10px; margin-bottom:18px; border: 1px solid #b3e5fc;">
                            <span style="font-size:0.9em;">{emoji} <b>{momento}</b></span>
                        </div>
                    """, unsafe_allow_html=True)

    # 4. Dibujamos los 7 días
    for i in range(7):
        current_date = start_of_week + timedelta(days=i)
        date_str = str(current_date)

        with columnas[i + 1]:
            # Encabezado del día (usamos i+1 para sacar el nombre del día Lunes, Martes...)
            st.markdown(f"""
                    <div style="background-color:#f0f2f6; padding:10px; border-radius:5px; text-align:center; height:70px; margin-bottom:10px; display:flex; flex-direction:column; justify-content:center;">
                        <p style="margin:0; font-weight:bold; line-height:1.2;">{dias_nombres[i + 1]}</p>
                        <p style="margin:0; font-size:0.8em;">{current_date.strftime('%d/%m')}</p>
                    </div>
                """, unsafe_allow_html=True)

            # Selectores de comida
            for momento in momentos_config.keys():
                val_actual = plan_dict.get((date_str, momento), "")
                idx = lista_nombres_recetas.index(val_actual) if val_actual in lista_nombres_recetas else 0

                seleccion = st.selectbox(
                    f"{momento}_{date_str}",
                    lista_nombres_recetas,
                    index=idx,
                    key=f"plan_{date_str}_{momento}",
                    label_visibility="collapsed",
                    disabled=not es_editor
                )

                if seleccion != val_actual:
                    db.save_meal_plan(current_date, momento, opciones_recetas.get(seleccion))