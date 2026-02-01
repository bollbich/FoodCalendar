import streamlit as st
import pandas as pd
from datetime import date, timedelta
import os
from src import db, logic

# Inicializar DB
if not os.path.exists('data'):
    os.makedirs('data')
db.init_db()

st.set_page_config(page_title="Planificador Pro V2", layout="wide", page_icon="🥑")

# --- CONFIGURACIÓN DE ESTADO Y FECHAS ---
if "fecha_global" not in st.session_state:
    st.session_state["fecha_global"] = logic.get_start_of_week(date.today())

def change_date(dias=0, nueva_fecha=None):
    if nueva_fecha is not None:
        base = nueva_fecha
    else:
        base = st.session_state["fecha_global"] + timedelta(days=dias)

    st.session_state["fecha_global"] = logic.get_start_of_week(base)

def get_start_of_week(dt):
    # dt.weekday() devuelve 0 para Lunes, 1 para Martes...
    return dt - timedelta(days=dt.weekday())

# --- BARRA LATERAL ---
# --- SEGURIDAD EN LA BARRA LATERAL ---
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

# ----------------------------------------
# VISTA: GESTIÓN DE INGREDIENTES
# ----------------------------------------
if opcion == "🍅 Ingredientes":
    st.header("Gestión de la Despensa")

    tab1, tab2 = st.tabs(["➕ Añadir Nuevo", "✏️ Editar / Ver Listado"])

    # --- TAB 1: AÑADIR ---
    with tab1:
        # 1. Función para procesar el envío y limpiar el campo
        def procesar_alta_ingrediente():
            # Recuperamos los valores de la memoria temporal (session_state)
            nombre = st.session_state.nuevo_ing_nombre.strip()
            categoria = st.session_state.nueva_cat_sel

            if nombre:
                if db.add_ingredient(nombre, categoria):
                    st.toast(f"✅ {nombre} añadido", icon="🛒")
                    # Limpiamos la variable del input en el estado de la sesión
                    st.session_state.nuevo_ing_nombre = ""
                else:
                    st.error("Ese ingrediente ya existe.")
            else:
                st.warning("Escribe un nombre.")


        col1, col2 = st.columns([1, 1])

        with col1:
            # Vinculamos el input a una clave de sesión (key)
            st.text_input("Nombre del nuevo ingrediente", key="nuevo_ing_nombre")

        with col2:
            st.selectbox("Categoría", [
                "🥦 Frutería", "🥩 Carnicería", "🧀 Charcuteria", "🐟 Pescaderia", "🥛 Frescos", "🥖 Panadería",
                "🥫 Despensa", "🧼 Limpieza", "❄️ Congelados", "Otros"
            ], key="nueva_cat_sel")

        # Al pulsar, llamamos a la función de arriba
        st.button("Añadir a la lista", on_click=procesar_alta_ingrediente)

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

            # Dividimos en dos columnas
            col_list, col_edit = st.columns([1, 1])

            with col_list:
                st.subheader("Ingredientes")
                event = st.dataframe(
                    df_ings,
                    column_order=("Nombre", "Categoría"),
                    use_container_width=True,
                    height=450,  # Altura fija para que no sea infinita
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
                    id_i = int(df_ings.iloc[row_idx]["ID"])
                    nombre_i = df_ings.iloc[row_idx]["Nombre"]
                    cat_i = df_ings.iloc[row_idx]["Categoría"]

                    # Usamos el form con key dinámica para asegurar limpieza de datos
                    with st.form(key=f"form_side_edit_{id_i}"):
                        nuevo_nom = st.text_input("Nombre", value=nombre_i)

                        try:
                            idx_cat = lista_categorias.index(cat_i)
                        except:
                            idx_cat = lista_categorias.index("Otros")

                        nueva_cat = st.selectbox("Categoría", options=lista_categorias, index=idx_cat)

                        c1, c2 = st.columns(2)

                        if c1.form_submit_button("💾 Guardar", use_container_width=True):
                            if nuevo_nom:
                                db.update_ingredient(id_i, nuevo_nom, nueva_cat)
                                st.toast(f"✅ {nuevo_nom} actualizado")
                                st.rerun()

                        if c2.form_submit_button("🗑️ Borrar", use_container_width=True):
                            db.delete_ingredient(id_i)
                            st.warning("Eliminado")
                            st.rerun()

                    st.info("💡 Cambia el nombre o categoría y pulsa Guardar.")
                else:
                    st.info("👈 Selecciona un ingrediente de la lista para editar sus detalles.")

# ----------------------------------------
# VISTA: GESTIÓN DE RECETAS
# ----------------------------------------
elif opcion == "📖 Recetas":
    st.header("Gestión de Recetas")

    # Aseguramos que exista la receta especial "Compra"
    db.ensure_special_recipe("Compra")

    all_ings = db.get_all_ingredients()
    opciones_ingredientes = {nombre: id_ing for id_ing, nombre, _ in all_ings}
    recetas_existentes = db.get_all_recipes()  # [(id, nombre)]

    tab1, tab2 = st.tabs(["➕ Crear Nueva", "✏️ Editar / Ver Recetas"])

    # --- TAB 1: CREAR ---
    with tab1:
        # Definimos la función de guardado para limpiar los campos después
        def guardar_receta_nueva():
            nom = st.session_state.crear_receta_nombre.strip()
            ings = st.session_state.crear_receta_ings

            if nom and ings:
                ids = [opciones_ingredientes[x] for x in ings]
                if db.create_recipe(nom, ids):
                    st.toast(f"✅ Receta '{nom}' creada")
                    # Limpiamos los widgets usando sus keys
                    st.session_state.crear_receta_nombre = ""
                    st.session_state.crear_receta_ings = []
                else:
                    st.error("Error al guardar la receta.")
            else:
                st.warning("Escribe un nombre y elige ingredientes.")


        # Widgets vinculados a session_state
        st.text_input("Nombre del Plato", key="crear_receta_nombre")
        st.multiselect("Ingredientes", options=opciones_ingredientes.keys(), key="crear_receta_ings")

        # Botón con callback para limpiar al terminar
        st.button("Guardar Nueva Receta", on_click=guardar_receta_nueva)

    # --- TAB 2: EDITAR ---
    with tab2:
        if not recetas_existentes:
            st.info("No hay recetas para editar.")
        else:
            # 1. Inicialización limpia: Si no existe en el estado, ponemos la primera
            if "selector_editar_receta" not in st.session_state:
                st.session_state["selector_editar_receta"] = recetas_existentes[0]

            # 2. Botón de acceso rápido (Esto funciona porque está ANTES del selectbox)
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

                # 4. Formulario de edición con KEY DINÁMICA
                with st.form(key=f"form_edit_receta_{id_r}"):
                    nuevo_nombre = st.text_input("Editar nombre", value=nombre_r, disabled=es_receta_especial)
                    nuevos_ings = st.multiselect(
                        "Editar ingredientes",
                        options=opciones_ingredientes.keys(),
                        default=ings_actuales
                    )

                    col_btn1, col_btn2 = st.columns(2)

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

                if es_receta_especial:
                    st.info(
                        "ℹ️ Estás editando la **Compra General**. Los ingredientes aquí guardados aparecerán siempre en tu lista semanal.")
# ----------------------------------------
# VISTA: PLANIFICADOR (CALENDARIO)
# ----------------------------------------
elif opcion == "📅 Planificador":
    st.header("Planificación Semanal")

    # --- NAVEGACIÓN UNIFICADA (Planificador) ---
    col_nav1, col_nav2, col_nav3 = st.columns([1, 2, 1])

    with col_nav1:
        if st.button("⬅️ Semana Anterior", key="btn_prev_plan", use_container_width=True):
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
        if st.button("Semana Siguiente ➡️", key="btn_next_plan", use_container_width=True):
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

# ----------------------------------------
# VISTA: COMPRA
# ----------------------------------------
elif opcion == "🛒 Compra":
    st.header("Lista de la Compra")

    # --- NAVEGACIÓN UNIFICADA (Compra) ---
    c_nav1, c_nav2, c_nav3 = st.columns([1, 2, 1])

    with c_nav1:
        if st.button("⬅️ Anterior", key="btn_prev_compra", use_container_width=True):
            change_date(dias=-7)

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

    # Usamos la misma fecha global
    start_w = logic.get_start_of_week(st.session_state["fecha_global"])
    end_w = start_w + timedelta(days=6)
    st.info(f"📋 Listado del **{start_w.strftime('%d/%m')}** al **{end_w.strftime('%d/%m/%Y')}**")

    # --- 2. LOGICA DE DATOS ---
    datos_plan = db.get_plan_range_details(start_w, end_w)
    lista_bruta = logic.extract_ingredients_from_plan(datos_plan, db)
    conteo_ingredientes = logic.aggregate_ingredients(lista_bruta)

    if not conteo_ingredientes:
        st.warning("📭 No hay comidas planificadas.")
    else:
        estado_compras = db.get_shopping_status(start_w)

        # OBTENER CATEGORÍAS
        # Retorna un diccionario {NombreIngrediente: Categoria}
        categorias_dict = db.get_ingredients_categories()

        # --- 3. BARRA DE PROGRESO ---
        total_items = len(conteo_ingredientes)
        comprados_count = sum(1 for ing in conteo_ingredientes if estado_compras.get(ing, False))
        progreso = comprados_count / total_items if total_items > 0 else 0
        st.progress(progreso, text=f"Progreso: {comprados_count} de {total_items}")

        # --- 4. LISTA DE CHECKBOXES POR CATEGORÍAS ---
        # Agrupamos los ingredientes por su categoría
        agrupados = {}
        for ing, cant in conteo_ingredientes.items():
            cat = categorias_dict.get(ing, "Otros")
            if cat not in agrupados: agrupados[cat] = []
            agrupados[cat].append((ing, cant))

        # Dibujamos un colapsable por cada categoría
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
                prefijo = f"chk_{start_w}"
                for key in list(st.session_state.keys()):
                    if key.startswith(prefijo):
                        del st.session_state[key]
                st.rerun()