# 🥑 Planificador de Comidas Inteligente

Aplicación web construida con Streamlit para gestionar menús semanales, crear recetarios y generar listas de la compra automáticas basadas en tu planificación.

## 🚀 Características

* **Calendario Semanal Interactiva:** Vista de 7 días con selectores rápidos para Desayuno, Comida, Cena, etc.
* **Base de Datos de Recetas:** Guarda tus platos favoritos y sus ingredientes.
* **Lista de Compra Automática:** Al planificar una comida, los ingredientes se añaden automáticamente a tu lista de la compra.
* **Persistencia de Datos:** Utiliza SQLite localmente (fácilmente escalable a bases de datos en la nube).

## 📂 Estructura del Proyecto

```text
.
├── .streamlit/       # Configuración visual
├── data/             # Base de datos SQLite (generada automáticamente)
├── src/              # Código fuente auxiliar
│   ├── db.py         # Gestión de Base de Datos
│   └── logic.py      # Lógica de negocio y cálculos
├── app.py            # Interfaz principal (Streamlit)
├── requirements.txt  # Dependencias
└── README.md         # Documentación