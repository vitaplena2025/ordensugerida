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
        edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True)
    except AttributeError:
        edited_df = st.experimental_data_editor(df, num_rows="dynamic", use_container_width=True)

    if st.button("Calcular Orden Sugerida 🧮"):
        df_calc = edited_df.copy()
        # Calcular venta diaria promedio
        df_calc["Venta diaria promedio"] = df_calc["Venta total periodo"] / duration_sales_period
        # Días totales considerados
        total_days = lead_time + coverage_days + order_horizon_days
        # Demanda bruta
        df_calc["qty_needed"] = np.maximum(
            df_calc["Venta diaria promedio"] * total_days
            + df_calc["Venta diaria promedio"] * df_calc["Días de Safety Stock"]
            - df_calc["Inventario On Hand"],
            0
        )
        # Función de redondeo a múltiplos de MOQ_SKU (ceil)
        def apply_moq(units, moq):
            return 0 if units <= 0 else int(np.ceil(units / moq) * moq)
        # Cálculo de floor y ceil por SKU
        df_calc["floor"] = df_calc.apply(
            lambda r: int((r["qty_needed"] // r["Mínimo de Orden por SKU"]) * r["Mínimo de Orden por SKU"]),
            axis=1
        )
        df_calc["ceil"] = df_calc.apply(
            lambda r: apply_moq(r["qty_needed"], r["Mínimo de Orden por SKU"]),
            axis=1
        )
        # Ajuste para cumplir MOQ global con overshoot mínimo (subset-sum)
        if min_order_global > 0:
            floor_sum = int(df_calc["floor"].sum())
            if floor_sum >= min_order_global:
                df_calc["Orden Sugerida en Bultos"] = df_calc["floor"]
            else:
                diff = min_order_global - floor_sum
                deltas = (df_calc["ceil"] - df_calc["floor"]).astype(int).tolist()
                # Programación dinámica subset-sum
                dp = {0: []}
                for i, d in enumerate(deltas):
                    if d <= 0:
                        continue
                    new_dp = dp.copy()
                    for s, idxs in dp.items():
                        new_s = s + d
                        if new_s not in new_dp:
                            new_dp[new_s] = idxs + [i]
                    dp = new_dp
                # Encontrar suma mínima >= diff
                candidates = [s for s in dp.keys() if s >= diff]
                if candidates:
                    best = min(candidates)
                    pick = dp[best]
                    orders = []
                    for idx in range(len(df_calc)):
                        if idx in pick:
                            orders.append(int(df_calc.at[idx, "ceil"]))
                        else:
                            orders.append(int(df_calc.at[idx, "floor"]))
                else:
                    # No hay combinación, usar ceil para todos
                    orders = df_calc["ceil"].astype(int).tolist()
                df_calc["Orden Sugerida en Bultos"] = orders
        else:
            df_calc["Orden Sugerida en Bultos"] = df_calc["ceil"]
        # Mostrar resultados finales
        st.subheader("✅ Orden Sugerida por SKU")
        st.dataframe(df_calc[["SKU", "Orden Sugerida en Bultos"]])
        # Descarga CSV de salida
        csv_out = df_calc[["SKU", "Orden Sugerida en Bultos"]].to_csv(index=False)
        st.download_button(
            label="Descargar Orden Sugerida (CSV)",
            data=csv_out,
            file_name="orden_sugerida.csv",
            mime="text/csv"
        )
else:
    st.info("Por favor, sube un CSV con las columnas requeridas para generar la orden.")
