import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO

st.set_page_config(page_title="Analizador Cuenta 14", layout="wide")

st.title("📊 Analizador Cuenta 14")

# =========================
# FUNCIONES
# =========================

def cargar_archivo(archivo):
    if archivo.name.endswith('.csv'):
        return pd.read_csv(archivo)
    return pd.read_excel(archivo)

def limpiar_columnas(df):
    df.columns = df.columns.astype(str).str.strip()
    return df

def convertir_numeros(df):
    columnas = ['Débito', 'Crédito', 'Saldo']

    for col in columnas:
        if col in df.columns:
            df[col] = (
                df[col]
                .astype(str)
                .str.replace(',', '', regex=False)
                .str.strip()
            )
            df[col] = pd.to_numeric(df[col], errors='coerce')

    return df

def obtener_estado(row):
    debito = row.get('Débito', 0)
    credito = row.get('Crédito', 0)

    if debito > 0 and credito == 0:
        return 'Pendiente'
    elif credito > 0:
        return 'Regularizado'
    else:
        return 'Sin Movimiento'

# =========================
# CARGA
# =========================

archivo = st.file_uploader(
    "Cargar archivo Excel",
    type=['xlsx', 'xls', 'csv']
)

if archivo:

    df = cargar_archivo(archivo)
    df = limpiar_columnas(df)
    df = convertir_numeros(df)

    if 'Fecha' in df.columns:
        df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce')

    # =========================
    # ESTADO
    # =========================

    df['Estado'] = df.apply(obtener_estado, axis=1)

    # =========================
    # FILTROS
    # =========================

    st.sidebar.header("Filtros")

    cuentas = st.sidebar.multiselect(
        "Cuenta",
        df['Cuenta'].dropna().unique(),
        default=df['Cuenta'].dropna().unique()
    )

    estados = st.sidebar.multiselect(
        "Estado",
        df['Estado'].unique(),
        default=df['Estado'].unique()
    )

    df_filtrado = df[
        (df['Cuenta'].isin(cuentas)) &
        (df['Estado'].isin(estados))
    ]

    # =========================
    # KPIS
    # =========================

    total_debito = df_filtrado['Débito'].sum()
    total_credito = df_filtrado['Crédito'].sum()
    saldo = df_filtrado['Saldo'].max()

    pendientes = df_filtrado[
        df_filtrado['Estado'] == 'Pendiente'
    ]['Débito'].sum()

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Débito", f"S/ {total_debito:,.2f}")
    col2.metric("Crédito", f"S/ {total_credito:,.2f}")
    col3.metric("Saldo", f"S/ {saldo:,.2f}")
    col4.metric("Pendiente", f"S/ {pendientes:,.2f}")

    # =========================
    # TABLA
    # =========================

    st.subheader("Detalle")

    st.dataframe(
        df_filtrado,
        use_container_width=True,
        height=500
    )

    # =========================
    # GRAFICOS
    # =========================

    st.subheader("Dashboard")

    resumen = (
        df_filtrado
        .groupby('Estado')[['Débito', 'Crédito']]
        .sum()
        .reset_index()
    )

    fig = px.bar(
        resumen,
        x='Estado',
        y=['Débito', 'Crédito'],
        barmode='group'
    )

    st.plotly_chart(fig, use_container_width=True)

    # =========================
    # PENDIENTES
    # =========================

    st.subheader("Pendientes de Regularizar")

    pendientes_df = df_filtrado[
        df_filtrado['Estado'] == 'Pendiente'
    ]

    st.dataframe(
        pendientes_df,
        use_container_width=True
    )

    # =========================
    # EXPORTAR
    # =========================

    output = BytesIO()

    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_filtrado.to_excel(writer, index=False)

    output.seek(0)

    st.download_button(
        label="Descargar Excel",
        data=output,
        file_name="Analisis_Cuenta14.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

else:
    st.info("Carga un archivo Excel para iniciar")
