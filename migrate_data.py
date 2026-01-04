import sqlite3


def generate_supabase_sql():
    sl_conn = sqlite3.connect('data/planner.db')
    sl_cur = sl_conn.cursor()

    with open('migration_data.sql', 'w', encoding='utf-8') as f:
        # 1. Limpiar tablas (Opcional, por si quieres empezar de cero)
        f.write("-- Limpieza de datos previos\n")
        f.write("TRUNCATE ingredientes, recetas, receta_ingredientes, planificacion CASCADE;\n\n")

        # 2. Migrar INGREDIENTES
        f.write("-- Insertar Ingredientes\n")
        sl_cur.execute("SELECT nombre, categoria FROM ingredientes")
        for nombre, cat in sl_cur.fetchall():
            f.write(
                f"INSERT INTO ingredientes (nombre, categoria) VALUES ('{nombre}', '{cat}') ON CONFLICT (nombre) DO NOTHING;\n")

        # 3. Migrar RECETAS
        f.write("\n-- Insertar Recetas\n")
        sl_cur.execute("SELECT id, nombre FROM recetas")
        for old_id, nombre in sl_cur.fetchall():
            f.write(f"INSERT INTO recetas (nombre) VALUES ('{nombre}') ON CONFLICT (nombre) DO NOTHING;\n")

        # 4. Migrar RELACIÓN (basada en nombres para evitar líos de IDs)
        f.write("\n-- Insertar Relaciones Receta-Ingrediente\n")
        sl_cur.execute("""
            SELECT r.nombre, i.nombre 
            FROM receta_ingredientes ri
            JOIN recetas r ON ri.receta_id = r.id
            JOIN ingredientes i ON ri.ingrediente_id = i.id
        """)
        for rec_nom, ing_nom in sl_cur.fetchall():
            f.write(f"INSERT INTO receta_ingredientes (receta_id, ingrediente_id) "
                    f"SELECT r.id, i.id FROM recetas r, ingredientes i "
                    f"WHERE r.nombre = '{rec_nom}' AND i.nombre = '{ing_nom}' "
                    f"ON CONFLICT DO NOTHING;\n")

        # 5. Migrar PLANIFICACIÓN
        f.write("\n-- Insertar Planificación\n")
        sl_cur.execute("""
            SELECT p.fecha, p.momento, r.nombre 
            FROM planificacion p
            JOIN recetas r ON p.receta_id = r.id
        """)
        for fecha, momento, rec_nom in sl_cur.fetchall():
            f.write(f"INSERT INTO planificacion (fecha, momento, receta_id) "
                    f"SELECT '{fecha}', '{momento}', id FROM recetas WHERE nombre = '{rec_nom}' "
                    f"ON CONFLICT (fecha, momento) DO NOTHING;\n")

    print("✅ Archivo 'migration_data.sql' generado con éxito.")
    sl_conn.close()


if __name__ == "__main__":
    generate_supabase_sql()