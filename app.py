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
        col1, _ = st.columns([1, 1])
        with col1:
            nuevo_ing = st.text_input("Nombre del nuevo ingrediente (ej: Brócoli)").strip()
            if st.button("Añadir a la lista"):
                if nuevo_ing:
                    if db.add_ingredient(nuevo_ing):
                        st.success(f"✅ {nuevo_ing} añadido correctamente")
                        st.rerun()
                    else:
                        st.error("Este ingrediente ya existe en tu lista.")

    # --- TAB 2: EDITAR Y LISTADO ---
    with tab2:
        all_ings = db.get_all_ingredients()  # Retorna [(id, nombre), ...]

        if not all_ings:
            st.info("La despensa está vacía.")
        else:
            col_list, col_edit = st.columns([1, 1])

            with col_list:
                st.subheader("Ingredientes actuales")
                df_ings = pd.DataFrame(all_ings, columns=["ID", "Nombre"])
                st.dataframe(
                    df_ings,
                    column_order=("Nombre",),
                    use_container_width=True,
                    height=400,
                    hide_index=True
                )

            with col_edit:
                st.subheader("Modificar ingrediente")
                ing_selec = st.selectbox(
                    "Selecciona el ingrediente a cambiar",
                    all_ings,
                    format_func=lambda x: x[1],
                    key="select_edit_ing"
                )

                if ing_selec:
                    id_i, nombre_i = ing_selec

                    with st.form("form_edit_ing"):
                        nuevo_nom_ing = st.text_input("Nuevo nombre", value=nombre_i)

                        c1, c2 = st.columns(2)
                        if c1.form_submit_button("💾 Guardar"):
                            if nuevo_nom_ing:
                                if db.update_ingredient(id_i, nuevo_nom_ing):
                                    st.success("Nombre actualizado")
                                    st.rerun()

                        if c2.form_submit_button("🗑️ Borrar"):
                            # El borrado afectará a las recetas (se quita de ellas)
                            db.delete_ingredient(id_i)
                            st.warning("Ingrediente eliminado")
                            st.rerun()

                    st.info(
                        "⚠️ Al cambiar el nombre o borrar, los cambios se reflejan en todas tus recetas automáticamente.")

# ----------------------------------------
# VISTA: GESTIÓN DE RECETAS
# ----------------------------------------
elif opcion == "📖 Recetas":
    st.header("Gestión de Recetas")

    # Aseguramos que exista la receta especial "Compra"
    db.ensure_special_recipe("Compra")

    all_ings = db.get_all_ingredients()
    opciones_ingredientes = {nombre: id_ing for id_ing, nombre in all_ings}
    recetas_existentes = db.get_all_recipes()  # [(id, nombre)]

    tab1, tab2 = st.tabs(["➕ Crear Nueva", "✏️ Editar / Ver Recetas"])

    # --- TAB 1: CREAR ---
    with tab1:
        with st.form("form_crear"):
            nombre_n = st.text_input("Nombre del Plato")
            ings_n = st.multiselect("Ingredientes", options=opciones_ingredientes.keys())
            if st.form_submit_button("Guardar Nueva Receta"):
                if nombre_n and ings_n:
                    ids = [opciones_ingredientes[x] for x in ings_n]
                    db.create_recipe(nombre_n, ids)
                    st.success("¡Receta creada!")
                    st.rerun()

    # --- TAB 2: EDITAR ---
    with tab2:
        # --- TAB 2: EDITAR ---
        with tab2:
            if not recetas_existentes:
                st.info("No hay recetas para editar.")
            else:
                # Botón de acceso rápido
                if st.button("🛒 Editar Lista de Compra General", use_container_width=True):
                    # Buscamos el ID de la receta "Compra" en la lista de existentes
                    for r_id, r_nom in recetas_existentes:
                        if r_nom == "Compra":
                            st.session_state["receta_a_editar"] = (r_id, r_nom)
                            st.rerun()

                # Determinamos qué receta mostrar en el selectbox por defecto
                # Si venimos del botón, usamos el session_state
                indice_defecto = 0
                if "receta_a_editar" in st.session_state:
                    # Buscamos la posición del ID guardado para que el selectbox se mueva ahí
                    ids_solo = [r[0] for r in recetas_existentes]
                    if st.session_state["receta_a_editar"][0] in ids_solo:
                        indice_defecto = ids_solo.index(st.session_state["receta_a_editar"][0])

                receta_selec = st.selectbox(
                    "Selecciona una receta para modificar",
                    recetas_existentes,
                    format_func=lambda x: x[1],
                    index=indice_defecto
                )

            if receta_selec:
                id_r, nombre_r = receta_selec
                es_receta_especial = (nombre_r == "Compra")

                ings_actuales = db.get_recipe_ingredients(id_r)

                with st.form("form_editar"):
                    # Bloqueamos el cambio de nombre si es la receta especial
                    nuevo_nombre = st.text_input(
                        "Editar nombre",
                        value=nombre_r,
                        disabled=es_receta_especial  # <--- Protegido
                    )

                    nuevos_ings = st.multiselect(
                        "Editar ingredientes",
                        options=opciones_ingredientes.keys(),
                        default=ings_actuales
                    )

                    col_btn1, col_btn2 = st.columns(2)

                    if col_btn1.form_submit_button("💾 Guardar Cambios"):
                        ids_n = [opciones_ingredientes[x] for x in nuevos_ings]
                        if db.update_recipe(id_r, nuevo_nombre, ids_n):
                            st.success("Actualizada con éxito")
                            # Limpiamos el acceso rápido al guardar
                            if "receta_a_editar" in st.session_state:
                                del st.session_state["receta_a_editar"]
                            st.rerun()

                    # El botón de eliminar se deshabilita si es la receta "Compra"
                    if col_btn2.form_submit_button("🗑️ Eliminar Receta", disabled=es_receta_especial):
                        db.delete_recipe(id_r)
                        st.warning("Receta eliminada")
                        st.rerun()

                if es_receta_especial:
                    st.caption("ℹ️ Esta es una receta del sistema. No se puede borrar ni renombrar.")

# ----------------------------------------
# VISTA: PLANIFICADOR (CALENDARIO)
# ----------------------------------------
elif opcion == "📅 Planificador":
    st.header("Planificación Semanal")

    # 1. Obtenemos fechas y datos
    d = st.date_input("Semana del:", date.today(), disabled=not es_editor)
    start_of_week = logic.get_start_of_week(d)
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
    # Ajustamos pesos: los días necesitan más espacio que la leyenda
    columnas = st.columns([0.8, 1, 1, 1, 1, 1, 1, 1])



    dias_nombres = ["Momentos", "Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

    # 3. Dibujamos la LEYENDA en la última columna (índice 7)
    with columnas[0]:
        # ESPACIADOR: Este bloque vacío hace que la leyenda baje y se alinee con los selectores
        st.markdown('<div style="height:80px;margin-top:1px;"></div>', unsafe_allow_html=True)

        for momento, emoji in momentos_config.items():
            # Usamos st.info o un markdown personalizado para que tenga la misma altura que un selectbox
            st.markdown(f"""
                    <div style="height:38px; display:flex; align-items:center; background-color:#e1f5fe; border-radius:5px; padding-left:10px; margin-bottom:18px; border: 1px solid #b3e5fc;">
                        <span style="font-size:0.9em;">{emoji} <b>{momento}</b></span>
                    </div>
                """, unsafe_allow_html=True)

    # 4. Dibujamos los 7 días
    for i in range(1, 8):
        current_date = start_of_week + timedelta(days=i)
        date_str = str(current_date)

        with columnas[i]:
            # Encabezado del día
            st.markdown(f"""
                <div style="background-color:#f0f2f6; padding:10px; border-radius:5px; text-align:center; height:70px; margin-bottom:10px; display:flex; flex-direction:column; justify-content:center;">
                    <p style="margin:0; font-weight:bold; line-height:1.2;">{dias_nombres[i]}</p>
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
                    st.rerun()



# ----------------------------------------
# VISTA: COMPRA
# ----------------------------------------
elif opcion == "🛒 Compra":
    st.header("Lista de la Compra")

    # Aseguramos que la tabla de compras exista
    db.init_shopping_db()

    # --- 1. SELECTOR DE FECHAS ---
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        hoy = date.today()
        lunes_esta_semana = logic.get_start_of_week(hoy)
        # Añadimos key única para evitar conflictos
        start_w = st.date_input("Semana del", lunes_esta_semana, key="fecha_compra_input")
        start_w = logic.get_start_of_week(start_w)

    with col_f2:
        end_w = start_w + timedelta(days=6)
        st.info(f"Visualizando hasta el {end_w.strftime('%d/%m/%Y')}")

    st.divider()

    # --- 2. LOGICA DE DATOS ---
    datos_plan = db.get_plan_range_details(start_w, end_w)
    lista_bruta = logic.extract_ingredients_from_plan(datos_plan, db)
    conteo_ingredientes = logic.aggregate_ingredients(lista_bruta)

    if not conteo_ingredientes:
        st.warning("📭 No tienes comidas planificadas para esta semana. ¡Ve al Planificador!")
    else:
        # Recuperamos estado de la BD
        estado_compras = db.get_shopping_status(start_w)

        # --- 3. BARRA DE PROGRESO ---
        total_items = len(conteo_ingredientes)
        # Contamos cuántos True hay en la base de datos para los ingredientes actuales
        comprados_count = sum(1 for ing in conteo_ingredientes if estado_compras.get(ing, False))

        # Evitamos división por cero
        progreso = comprados_count / total_items if total_items > 0 else 0

        st.progress(progreso, text=f"Progreso de compra: {comprados_count} de {total_items} artículos")

        # --- 4. LISTA DE CHECKBOXES ---
        c1, c2 = st.columns(2)
        items_ordenados = sorted(conteo_ingredientes.items())

        for i, (ingrediente, cantidad) in enumerate(items_ordenados):
            col = c1 if i % 2 == 0 else c2

            esta_marcado = estado_compras.get(ingrediente, False)

            # Checkbox con Key única basada en semana e ingrediente
            nuevo_estado = col.checkbox(
                f"{ingrediente} (x{cantidad})",
                value=esta_marcado,
                key=f"chk_{start_w}_{ingrediente}"
            )

            # Guardado inmediato al cambiar
            if nuevo_estado != esta_marcado:
                db.update_shopping_status(start_w, ingrediente, nuevo_estado)
                st.rerun()

        st.divider()

        # --- 5. BOTÓN DE RESET (CON BORRADO DE MEMORIA) ---
        col_reset, _ = st.columns([1, 2])
        with col_reset:
            if st.button("🗑️ Vaciar lista de esta semana", key="btn_reset_compra_final"):
                # 1. Borrar de la base de datos (Persistencia)
                db.clear_shopping_status(start_w)

                # 2. Borrar de la memoria de Streamlit (Interfaz)
                # Buscamos todas las variables que empiecen por el patrón de esta semana
                prefijo = f"chk_{start_w}"
                for key in list(st.session_state.keys()):
                    if key.startswith(prefijo):
                        del st.session_state[key]

                st.success("Lista reiniciada.")
                st.rerun()