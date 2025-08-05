# ordensugerida_app.py
import streamlit as st
import pandas as pd
import numpy as np

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
order_horizon_months = st.sidebar.number_input(
    "Rango de Pedido (meses)", min_value=1, value=3, step=1
)
order_horizon_days = order_horizon_months * 30
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
    try:
        edited_df = st.data_editor(
            df,
            num_rows="dynamic",
            use_container_width=True
        )
    except AttributeError:
        edited_df = st.experimental_data_editor(
            df,
            num_rows="dynamic",
            use_container_width=True
        )

    if st.button("Calcular Orden Sugerida 🧮"):
        df_calc = edited_df.copy()
        # Convertir venta total a promedio diario
        df_calc["Venta diaria promedio"] = (
            df_calc["Venta total periodo"] / duration_sales_period
        )
        # Días totales considerados
        total_days = lead_time + coverage_days + order_horizon_days
        # Cálculo de la demanda base
        df_calc["qty_needed"] = np.maximum(
            df_calc["Venta diaria promedio"] * total_days
            + df_calc["Venta diaria promedio"] * df_calc["Días de Safety Stock"]
            - df_calc["Inventario On Hand"],
            0
        )

        # Función para ajustar por MOQ de SKU
        def apply_moq(units, moq):
            return 0 if units <= 0 else int(np.ceil(units / moq) * moq)

        # Ajuste individual por SKU
        df_calc["Orden Sugerida en Bultos"] = df_calc.apply(
            lambda r: apply_moq(r["qty_needed"], r["Mínimo de Orden por SKU"]), axis=1
        )

        # Ajustar para cumplir MOQ global exacto con mínimo overshoot
        total = df_calc["Orden Sugerida en Bultos"].sum()
        if min_order_global > 0 and total < min_order_global:
            leftover = min_order_global - total
            # Encontrar MOQ más pequeño
            smallest_moq = df_calc["Mínimo de Orden por SKU"].min()
            # Índice de un SKU con ese MOQ
            idx = df_calc[df_calc["Mínimo de Orden por SKU"] == smallest_moq].index[0]
            # Incremento necesario (múltiplo de smallest_moq)
            increments = int(np.ceil(leftover / smallest_moq)) * smallest_moq
            df_calc.at[idx, "Orden Sugerida en Bultos"] += increments

        # Mostrar resultados finales
        st.subheader("✅ Orden Sugerida por SKU")
        st.dataframe(df_calc[["SKU", "Orden Sugerida en Bultos"]])

        # Botón de descarga CSV de salida
        csv_out = df_calc[["SKU", "Orden Sugerida en Bultos"]].to_csv(index=False)
        st.download_button(
            label="Descargar Orden Sugerida (CSV)",
            data=csv_out,
            file_name="orden_sugerida.csv",
            mime="text/csv"
        )
else:
    st.info("Por favor, sube un CSV con las columnas requeridas para generar la orden.")
