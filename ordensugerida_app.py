# ordensugerida_app.py
import streamlit as st
import pandas as pd
import numpy as np
import io

# Configuración de la página
st.set_page_config(page_title="Orden Sugerida de Compra", layout="wide")
st.title("🛒 Generador de Orden Sugerida")

# ----- Parámetros Globales -----
st.sidebar.header("Parámetros Globales de la Orden")
min_order_global = st.sidebar.number_input(
    "MOQ Global de la Orden (bultos)", min_value=0, value=0, step=1
)
lead_time = st.sidebar.number_input(
    "Lead time (días)", min_value=0, value=0, step=1
)
coverage_days = st.sidebar.number_input(
    "Días de Cobertura Adicional", min_value=0, value=0, step=1
)
# Rango de Pedido define el número de meses para considerar la demanda total
order_horizon_months = st.sidebar.number_input(
    "Rango de Pedido (meses)", min_value=1, value=3, step=1
)
order_horizon_days = order_horizon_months * 30
# Duración del periodo de ventas para calcular promedio diario
duration_sales_period = st.sidebar.number_input(
    "Duración del período de ventas (días)", min_value=1, value=30, step=1
)

# ----- Template CSV -----
st.sidebar.header("Template CSV de Ejemplo")
template_df = pd.DataFrame(
    columns=[
        "SKU",
        "Venta total periodo",
        "Inventario On Hand",
        "Días de Safety Stock",
        "Mínimo de Orden por SKU",
    ]
)
csv_template = template_df.to_csv(index=False)
st.sidebar.download_button(
    label="Descargar template CSV",
    data=csv_template,
    file_name="template_orden_sugerida.csv",
    mime="text/csv"
)

# ----- Carga de Datos -----
st.sidebar.header("Historial de Ventas y Parámetros por SKU")
uploaded_file = st.sidebar.file_uploader(
    "Sube un CSV con columnas: SKU, Venta total periodo, Inventario On Hand, Días de Safety Stock, Mínimo de Orden por SKU",
    type=["csv"]
)

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    st.subheader("📊 Datos de Entrada")
    # Editor de datos para Streamlit >= 1.23
    try:
        edited_df = st.data_editor(
            df,
            num_rows="dynamic",
            use_container_width=True
        )
    except AttributeError:
        # Compatibilidad con versiones anteriores
        edited_df = st.experimental_data_editor(
            df,
            num_rows="dynamic",
            use_container_width=True
        )

    if st.button("Calcular Orden Sugerida 🧮"):
        df_calc = edited_df.copy()
        # Calcular venta diaria promedio a partir de venta total del periodo
        df_calc["Venta diaria promedio"] = (
            df_calc["Venta total periodo"] / duration_sales_period
        )
        # Cálculo de cantidad requerida usando promedio diario, safety stock en días y rango de pedido
        total_days = lead_time + coverage_days + order_horizon_days
        df_calc["qty_needed"] = (
            df_calc["Venta diaria promedio"] * total_days
            + df_calc["Venta diaria promedio"] * df_calc["Días de Safety Stock"]
            - df_calc["Inventario On Hand"]
        )
        df_calc["qty_needed"] = df_calc["qty_needed"].clip(lower=0)

        # Función para ajustar por MOQ de SKU
        def apply_moq(x, moq):
            return 0 if x <= 0 else int(np.ceil(x / moq) * moq)

        df_calc["suggested_order"] = df_calc.apply(
            lambda r: apply_moq(r["qty_needed"], r["Mínimo de Orden por SKU"]), axis=1
        )

        # Renombrar para salida
        df_out = df_calc[["SKU", "suggested_order"]].rename(
            columns={"suggested_order": "Orden Sugerida en Bultos"}
        )

        # Ajuste para MOQ Global (si aplica)
        total_order = df_out["Orden Sugerida en Bultos"].sum()
        if 0 < total_order < min_order_global:
            factor = min_order_global / total_order
            df_out["Orden Sugerida en Bultos"] = df_out["Orden Sugerida en Bultos"].apply(
                lambda x: int(np.ceil(x * factor))
            )

        # Mostrar resultados finales
        st.subheader("✅ Orden Sugerida por SKU")
        st.dataframe(df_out)

        # Botón para descargar Excel
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            df_out.to_excel(writer, index=False, sheet_name="Orden Sugerida")
            writer.save()
        buffer.seek(0)
        st.download_button(
            label="Descargar Orden Sugerida (Excel)",
            data=buffer,
            file_name="orden_sugerida.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
else:
    st.info("Por favor, sube un archivo CSV con las columnas requeridas para generar la orden.")
