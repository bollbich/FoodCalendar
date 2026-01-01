import streamlit as st
import pandas as pd
from datetime import date, timedelta
import os

# Importamos nuestros módulos locales
if not os.path.exists('data'):
    os.makedirs('data')
from src import db

# Configuración de página
st.set_page_config(page_title="Planificador Pro", layout="wide", page_icon="🥑")

# Inicializar DB
db.init_db()

# --- BARRA LATERAL ---
st.sidebar.title("Navegación")
opcion = st.sidebar.radio("Ir a:", ["📅 Planificador Semanal", "📖 Mi Recetario", "🛒 Lista de la Compra"])

# --- VISTA 1: RECETARIO (Fundamental para que funcione la lista) ---
if opcion == "📖 Mi Recetario":
    st.header("Gestión de Recetas")
    st.info("💡 Crea recetas aquí para poder seleccionarlas en el calendario y generar la lista de compra automática.")

    col1, col2 = st.columns([1, 2])

    with col1:
        with st.form("nueva_receta"):
            st.subheader("Nueva Receta")
            nombre = st.text_input("Nombre del plato (ej: Lentejas)")
            ingredientes = st.text_area("Ingredientes (separados por coma)",
                                        placeholder="Lentejas, Chorizo, Zanahoria, Cebolla")
            submitted = st.form_submit_button("Guardar Receta")

            if submitted and nombre:
                db.save_recipe(nombre, ingredientes)
                st.success(f"Receta '{nombre}' guardada.")
                st.rerun()

    with col2:
        st.subheader("Recetas Disponibles")
        recetas = db.get_all_recipes()
        if recetas:
            df_recetas = pd.DataFrame(recetas, columns=["Nombre"])
            st.dataframe(df_recetas, use_container_width=True)
        else:
            st.warning("Aún no tienes recetas. ¡Añade algunas!")

# --- VISTA 2: PLANIFICADOR (CALENDARIO) ---
elif opcion == "📅 Planificador Semanal":
    st.header("Planificación de Comidas")

    recetas_disponibles = [""] + db.get_all_recipes()  # Opción vacía al principio
    momentos = ["Desayuno", "Media Mañana", "Comida", "Media Tarde", "Cena"]

    # Selector de fecha (Semana)
    d = st.date_input("Selecciona el inicio de la semana", date.today())
    start_of_week = d - timedelta(days=d.weekday())  # Forzar a lunes

    st.write(f"Viendo semana del: **{start_of_week}** al **{start_of_week + timedelta(days=6)}**")

    # Recuperar datos de la semana
    plan_data = db.get_plan_range(start_of_week, start_of_week + timedelta(days=6))
    # Convertir a diccionario para acceso rápido {(fecha, momento): receta}
    plan_dict = {(fecha, mom): rec for fecha, mom, rec in plan_data}

    # Crear Grid de 7 días
    cols = st.columns(7)
    days = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

    for i, col in enumerate(cols):
        current_date = start_of_week + timedelta(days=i)
        date_str = str(current_date)

        with col:
            st.markdown(f"### {days[i]}")
            st.caption(f"{current_date.strftime('%d/%m')}")

            for momento in momentos:
                key_val = f"{date_str}_{momento}"
                # Valor actual en DB o vacío
                valor_actual = plan_dict.get((date_str, momento), "")

                # Si la receta guardada ya no existe en el recetario, manéjalo con cuidado
                index_val = recetas_disponibles.index(valor_actual) if valor_actual in recetas_disponibles else 0

                seleccion = st.selectbox(
                    momento,
                    recetas_disponibles,
                    index=index_val,
                    key=key_val,
                    label_visibility="collapsed"  # Ocultar etiqueta para ahorrar espacio visual
                )

                # Guardar automáticamente si cambia (Auto-save)
                if seleccion != valor_actual:
                    db.save_meal(current_date, momento, seleccion)
                    # No hacemos rerun aquí para no refrescar toda la pág constantemente,
                    # pero se guarda en DB.

# --- VISTA 3: LISTA DE LA COMPRA AUTOMÁTICA ---
elif opcion == "🛒 Lista de la Compra":
    st.header("Generador de Lista de la Compra")

    col1, col2 = st.columns(2)
    with col1:
        start_d = st.date_input("Desde", date.today())
    with col2:
        end_d = st.date_input("Hasta", date.today() + timedelta(days=7))

    if st.button("Generar Lista"):
        # 1. Obtener platos planificados
        plan_data = db.get_plan_range(start_d, end_d)

        if not plan_data:
            st.warning("No hay comidas planificadas para esas fechas.")
        else:
            lista_ingredientes = []
            st.write(f"Analizando {len(plan_data)} comidas planificadas...")

            # 2. Buscar ingredientes de cada plato
            for _, _, receta in plan_data:
                if receta:
                    ings = db.get_ingredients(receta)
                    # Separar por comas y limpiar espacios
                    lista_ingredientes.extend([i.strip().title() for i in ings.split(',') if i.strip()])

            # 3. Agrupar y contar (opcional, aquí solo listamos únicos o todos)
            from collections import Counter

            conteo = Counter(lista_ingredientes)

            st.subheader("📝 Tu Lista:")

            check_col1, check_col2 = st.columns(2)

            # Mostramos como checkboxes para ir tachando
            for i, (ingrediente, cantidad) in enumerate(conteo.items()):
                # Distribuir en dos columnas
                col = check_col1 if i % 2 == 0 else check_col2
                col.checkbox(f"{ingrediente} (x{cantidad})")

            # Opción de exportar
            df_lista = pd.DataFrame(lista_ingredientes, columns=["Ingrediente"])
            st.download_button("Descargar CSV", df_lista.to_csv(index=False), "compra.csv")