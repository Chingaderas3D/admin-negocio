import streamlit as st
import sqlite3
from datetime import date
import pandas as pd

conn = sqlite3.connect("negocio.db", check_same_thread=False)
c = conn.cursor()
def borrar_venta(venta_id):
    c.execute("DELETE FROM ventas WHERE id = ?", (venta_id,))
    conn.commit()


c.execute("""
CREATE TABLE IF NOT EXISTS productos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT UNIQUE,
    costo REAL
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS ventas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha TEXT,
    producto TEXT,
    cantidad INTEGER,
    precio_venta REAL
)
""")

conn.commit()

st.set_page_config(page_title="Mi Negocio", layout="centered")
st.title("📊 Administrador de Ventas")

menu = st.sidebar.selectbox(
    "Menú",
    ["Productos", "Registrar venta", "Resumen diario"]
)

if menu == "Productos":
    st.header("📦 Productos")

    nombre = st.text_input("Nombre del producto")
    costo = st.number_input("Costo de producción", min_value=0.0, step=10.0)

    if st.button("Guardar producto"):
        c.execute(
            "INSERT OR REPLACE INTO productos (nombre, costo) VALUES (?, ?)",
            (nombre, costo)
        )
        conn.commit()
        st.success("Producto guardado")

    st.subheader("Lista de productos")
    df = pd.read_sql("SELECT * FROM productos", conn)
    st.dataframe(df)

elif menu == "Registrar venta":
    st.header("🧾 Registrar venta")

    productos = pd.read_sql("SELECT nombre FROM productos", conn)

    if productos.empty:
        st.warning("Primero agrega productos")
    else:
        producto = st.selectbox("Producto", productos["nombre"])
        cantidad = st.number_input("Cantidad", min_value=1, step=1)
        precio = st.number_input("Precio de venta", min_value=0.0, step=10.0)
        fecha = st.date_input("Fecha", value=date.today())

        if st.button("Registrar venta"):
            c.execute(
                "INSERT INTO ventas (fecha, producto, cantidad, precio_venta) VALUES (?, ?, ?, ?)",
                (fecha.isoformat(), producto, cantidad, precio)
            )
            conn.commit()
            st.success("Venta registrada")

elif menu == "Resumen diario":
    st.header("📈 Resumen diario")

    fecha = st.date_input("Selecciona una fecha", value=date.today())

       query = f"""
    SELECT v.id AS venta_id,
           v.producto,
           v.cantidad,
           v.precio_venta,
           p.costo,
           (v.cantidad * v.precio_venta) AS ingreso,
           (v.cantidad * p.costo) AS costo_total,
           (v.cantidad * v.precio_venta) - (v.cantidad * p.costo) AS ganancia
    FROM ventas v
    JOIN productos p ON v.producto = p.nombre
    WHERE v.fecha = '{fecha.isoformat()}'
    """


    df = pd.read_sql(query, conn)

   if df.empty:
    st.info("No hay ventas ese día")
else:
    st.dataframe(df, use_container_width=True)

    st.success(f"💰 Ganancia del día: ${df['ganancia'].sum():,.2f}")

    st.markdown("### 🗑️ Eliminar una venta")
    venta_ids = df["venta_id"].tolist()
    venta_seleccionada = st.selectbox(
        "Selecciona la venta a eliminar",
        venta_ids
    )

    if st.button("Eliminar venta seleccionada"):
        borrar_venta(int(venta_seleccionada))
        st.success("Venta eliminada correctamente")
        st.rerun()

