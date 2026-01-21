import streamlit as st
import pandas as pd
import psycopg2
from datetime import date

# ---------------- DB (Supabase Postgres) ----------------
@st.cache_resource
def get_conn():
    # Debes poner DB_URL en Streamlit Secrets
    # Ejemplo en Secrets:
    # DB_URL="postgresql://postgres:TU_PASSWORD@db.xxxx.supabase.co:5432/postgres"
    return psycopg2.connect(st.secrets["DB_URL"])

conn = get_conn()

def init_db():
    with conn.cursor() as c:
        c.execute("""
        CREATE TABLE IF NOT EXISTS productos (
            id SERIAL PRIMARY KEY,
            nombre TEXT UNIQUE NOT NULL,
            costo NUMERIC NOT NULL CHECK (costo >= 0)
        );
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS ventas (
            id SERIAL PRIMARY KEY,
            fecha DATE NOT NULL,
            producto TEXT NOT NULL,
            cantidad INT NOT NULL CHECK (cantidad > 0),
            precio_venta NUMERIC NOT NULL CHECK (precio_venta >= 0)
        );
        """)
        conn.commit()

def borrar_venta(venta_id: int):
    with conn.cursor() as c:
        c.execute("DELETE FROM ventas WHERE id = %s", (venta_id,))
        conn.commit()

def upsert_producto(nombre: str, costo: float):
    nombre = nombre.strip()
    if not nombre:
        raise ValueError("Nombre vacío")
    with conn.cursor() as c:
        c.execute("""
            INSERT INTO productos (nombre, costo)
            VALUES (%s, %s)
            ON CONFLICT (nombre) DO UPDATE SET costo = EXCLUDED.costo
        """, (nombre, costo))
        conn.commit()

def insertar_venta(fecha, producto: str, cantidad: int, precio_venta: float):
    with conn.cursor() as c:
        c.execute("""
            INSERT INTO ventas (fecha, producto, cantidad, precio_venta)
            VALUES (%s, %s, %s, %s)
        """, (fecha, producto, cantidad, precio_venta))
        conn.commit()

init_db()

# ---------------- UI ----------------
st.set_page_config(page_title="Mi Negocio", layout="centered")
st.title("📊 Administrador de Ventas")

menu = st.sidebar.selectbox("Menú", ["Productos", "Registrar venta", "Resumen diario"])

# -------- Productos ----------
if menu == "Productos":
    st.header("📦 Productos")

    nombre = st.text_input("Nombre del producto")
    costo = st.number_input("Costo de producción", min_value=0.0, step=10.0, format="%.2f")

    if st.button("Guardar producto"):
        try:
            upsert_producto(nombre, float(costo))
            st.success("Producto guardado")
        except Exception as e:
            st.error(f"Error: {e}")

    st.subheader("Lista de productos")
    df = pd.read_sql("SELECT id, nombre, costo FROM productos ORDER BY nombre", conn)
    st.dataframe(df, use_container_width=True, hide_index=True)

# -------- Registrar venta ----------
elif menu == "Registrar venta":
    st.header("🧾 Registrar venta")

    productos = pd.read_sql("SELECT nombre FROM productos ORDER BY nombre", conn)

    if productos.empty:
        st.warning("Primero agrega productos")
    else:
        producto = st.selectbox("Producto", productos["nombre"])
        cantidad = st.number_input("Cantidad", min_value=1, step=1, value=1)
        precio = st.number_input("Precio de venta", min_value=0.0, step=10.0, format="%.2f")
        fecha = st.date_input("Fecha", value=date.today())

        if st.button("Registrar venta"):
            try:
                insertar_venta(fecha, producto, int(cantidad), float(precio))
                st.success("Venta registrada")
            except Exception as e:
                st.error(f"Error: {e}")

# -------- Resumen diario ----------
elif menu == "Resumen diario":
    st.header("📈 Resumen diario")

    fecha = st.date_input("Selecciona una fecha", value=date.today())

    query = """
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
    WHERE v.fecha = %s
    ORDER BY v.id DESC
    """
    df = pd.read_sql(query, conn, params=(fecha,))

    if df.empty:
        st.info("No hay ventas ese día")
    else:
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.success(f"💰 Ganancia del día: ${float(df['ganancia'].sum()):,.2f}")

        st.markdown("### 🗑️ Eliminar una venta")
        # Selector más claro: muestra ID + producto + cantidad + precio
        df["_label"] = df.apply(lambda r: f"ID {int(r['venta_id'])} — {r['producto']} — {int(r['cantidad'])} pza — ${float(r['precio_venta']):,.2f}", axis=1)
        opcion = st.selectbox("Selecciona la venta a eliminar", df["_label"].tolist())
        venta_id = int(df.loc[df["_label"] == opcion, "venta_id"].iloc[0])

        if st.button("Eliminar venta seleccionada"):
            borrar_venta(venta_id)
            st.success("Venta eliminada correctamente ✅")
            st.rerun()
