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
    "MOQ Global de la Orden", min_value=0, value=0, step=1
)
lead_time = st.sidebar.number_input(
    "Lead time (días)", min_value=0, value=0, step=1
)
coverage_days = st.sidebar.number_input(
    "Días de Cobertura Adicional", min_value=0, value=0, step=1
)

# ----- Carga de Datos -----
st.sidebar.header("Historial de Ventas y Parámetros por SKU")
uploaded_file = st.sidebar.file_uploader(
    "Sube un CSV con columnas: SKU, avg_daily_sales, inventory_current, safety_stock, moq_sku",
    type=["csv"]
)

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    st.subheader("📊 Datos de Entrada")
    # Permite edición en línea (agregar/modificar filas y valores)
    edited_df = st.experimental_data_editor(
        df,
        num_rows="dynamic",
        use_container_width=True
    )

    if st.button("Calcular Orden Sugerida 🧮"):
        df_calc = edited_df.copy()
        # Cálculo de cantidad requerida
        df_calc["qty_needed"] = (
            df_calc["avg_daily_sales"] * (lead_time + coverage_days)
            + df_calc["safety_stock"]
            - df_calc["inventory_current"]
        )
        df_calc["qty_needed"] = df_calc["qty_needed"].clip(lower=0)

        # Función para ajustar por MOQ de SKU
        def apply_moq(x, moq):
            return 0 if x <= 0 else int(np.ceil(x / moq) * moq)

        df_calc["suggested_order"] = df_calc.apply(
            lambda r: apply_moq(r["qty_needed"], r["moq_sku"]), axis=1
        )

        # Ajuste para MOQ Global (si aplica)
        total_order = df_calc["suggested_order"].sum()
        if 0 < total_order < min_order_global:
            factor = min_order_global / total_order
            df_calc["suggested_order"] = (
                df_calc["suggested_order"]
                .apply(lambda x: int(np.ceil(x * factor)))
            )

        # Mostrar resultados finales
        st.subheader("✅ Orden Sugerida por SKU")
        st.dataframe(df_calc[["SKU", "suggested_order"]])
else:
    st.info("Por favor, sube un archivo CSV con las columnas requeridas para generar la orden.")
