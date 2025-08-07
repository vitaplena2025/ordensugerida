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
# Forzar pedido mínimo por SKU si hay demanda
force_min_sku = st.sidebar.checkbox(
    "Forzar pedido mínimo por SKU si hay demanda", value=False
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
    # Lectura robusta del CSV
    try:
        df = pd.read_csv(uploaded_file)
    except Exception:
        uploaded_file.seek(0)
        df = pd.read_csv(uploaded_file, sep=None, engine='python', encoding='latin1')
    # Normalizar y renombrar columnas comunes
    df.columns = df.columns.str.strip()
    df.rename(columns={
        'Dias de Safety Stock': 'Días de Safety Stock',
        'Minimo de Orden por SKU': 'Mínimo de Orden por SKU'
    }, inplace=True)

    st.subheader("📊 Datos de Entrada")
    # Editor de datos para ajustes manuales antes del cálculo
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
        # Demanda bruta con safety stock en días
        df_calc["qty_needed"] = np.maximum(
            df_calc["Venta diaria promedio"] * total_days
            + df_calc["Venta diaria promedio"] * df_calc["Días de Safety Stock"]
            - df_calc["Inventario On Hand"],
            0
        )
        # Funciones de floor y ceil a múltiplos de MOQ_SKU
        def floor_moq(units, moq):
            return 0 if units <= 0 else int((units // moq) * moq)
        def ceil_moq(units, moq):
            return 0 if units <= 0 else int(np.ceil(units / moq) * moq)
        # Calcular floor y ceil
        df_calc["floor"] = df_calc.apply(lambda r: floor_moq(r["qty_needed"], r["Mínimo de Orden por SKU"]), axis=1)
        df_calc["ceil"] = df_calc.apply(lambda r: ceil_moq(r["qty_needed"], r["Mínimo de Orden por SKU"]), axis=1)
        # Subset-sum DP para cumplir MOQ global con mínimo overshoot
        if min_order_global > 0:
            floor_sum = int(df_calc["floor"].sum())
            if floor_sum >= min_order_global:
                df_calc["Orden Sugerida en Bultos"] = df_calc["floor"]
            else:
                diff = min_order_global - floor_sum
                deltas = (df_calc["ceil"] - df_calc["floor"]).astype(int).tolist()
                dp = {0: []}
                for i, d in enumerate(deltas):
                    if d <= 0:
                        continue
                    for s, idxs in list(dp.items()):
                        new_s = s + d
                        if new_s not in dp:
                            dp[new_s] = idxs + [i]
                candidates = [s for s in dp.keys() if s >= diff]
                if candidates:
                    best = min(candidates)
                    pick = dp[best]
                    orders = [int(df_calc.at[i, "ceil"]) if i in pick else int(df_calc.at[i, "floor"]) for i in range(len(df_calc))]
                else:
                    orders = df_calc["ceil"].astype(int).tolist()
                df_calc["Orden Sugerida en Bultos"] = orders
        else:
            df_calc["Orden Sugerida en Bultos"] = df_calc["ceil"].astype(int)
        # Forzar mínimo por SKU si se activa
        if force_min_sku:
            df_calc["Orden Sugerida en Bultos"] = df_calc.apply(
                lambda r: r["ceil"] if (r["qty_needed"] > 0 and r["floor"] == 0) else r["Orden Sugerida en Bultos"],
                axis=1
            )
        # Mostrar resultados en tabla editable para ajuste manual
        st.subheader("✅ Orden Sugerida por SKU (editable)")
        try:
            final_df = st.data_editor(
                df_calc[["SKU", "Orden Sugerida en Bultos"]],
                num_rows="fixed",
                use_container_width=True
            )
        except AttributeError:
            final_df = st.experimental_data_editor(
                df_calc[["SKU", "Orden Sugerida en Bultos"]],
                num_rows="fixed",
                use_container_width=True
            )
        # Botón de descarga CSV de la tabla final
        csv_out = final_df.to_csv(index=False)
        st.download_button(
            label="Descargar Orden Sugerida (CSV)",
            data=csv_out,
            file_name="orden_sugerida.csv",
            mime="text/csv"
        )
else:
    st.info("Por favor, sube un archivo CSV con las columnas requeridas para generar la orden.")
