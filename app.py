import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO

# =====================================
# CONFIGURACION
# =====================================

st.set_page_config(
    page_title="Analizador Cuenta 14",
    layout="wide"
)

st.title("📊 Analizador Inteligente - Cuenta 14")

st.markdown("""
Sistema automático para:

- Entregas a rendir
- Regularizaciones
- Duplicados
- Coincidencias Débito vs Crédito
- Riesgos
- Exportación automática
""")

# =====================================
# FUNCIONES
# =====================================

def cargar_archivo(archivo):

    if archivo.name.endswith(".csv"):

        df = pd.read_csv(archivo)

    else:

        df = pd.read_excel(archivo)

    return df


def limpiar_columnas(df):

    df.columns = (
        df.columns
        .astype(str)
        .str.strip()
    )

    return df


def convertir_numeros(df):

    columnas = [
        "Débito",
        "Crédito",
        "Saldo",
        "T/C"
    ]

    for col in columnas:

        if col in df.columns:

            df[col] = (
                df[col]
                .astype(str)
                .str.replace(",", "", regex=False)
                .str.strip()
            )

            df[col] = pd.to_numeric(
                df[col],
                errors="coerce"
            )

    return df


# =====================================
# REGULARIZACION REAL
# =====================================

def detectar_regularizacion(df):

    df["Estado"] = "Pendiente"

    df["Relacionado"] = ""

    df["Espejo"] = False

    debitos = df[
        df["Débito"] > 0
    ]

    creditos = df[
        df["Crédito"] > 0
    ]

    for i, deb in debitos.iterrows():

        monto_debito = deb["Débito"]

        posibles = creditos[
            creditos["Crédito"] == monto_debito
        ]

        if not posibles.empty:

            for idx, cred in posibles.iterrows():

                # =================================
                # MARCAR DEBITO
                # =================================

                df.at[i, "Estado"] = "Regularizado"

                df.at[i, "Espejo"] = True

                df.at[i, "Relacionado"] = (
                    f"↔ Crédito {cred['Crédito']}"
                )

                # =================================
                # MARCAR CREDITO
                # =================================

                df.at[idx, "Estado"] = "Regularizado"

                df.at[idx, "Espejo"] = True

                df.at[idx, "Relacionado"] = (
                    f"↔ Débito {deb['Débito']}"
                )

    return df


# =====================================
# DUPLICADOS EXACTOS
# =====================================

def detectar_duplicados(df):

    columnas_dup = [
        "Cuenta",
        "Fecha",
        "Débito",
        "Crédito",
        "Concepto"
    ]

    columnas_existentes = [
        c for c in columnas_dup
        if c in df.columns
    ]

    df["Duplicado"] = df.duplicated(
        subset=columnas_existentes,
        keep=False
    )

    return df


# =====================================
# RIESGO
# =====================================

def riesgo(row):

    if row["Duplicado"]:
        return "🔴 Duplicado"

    if row["Espejo"]:
        return "🔵 Regularizado"

    if row["Estado"] == "Pendiente":
        return "🟡 Pendiente"

    return "🟢 Normal"


# =====================================
# COLORES
# =====================================

def colorear_filas(row):

    # REGULARIZADO / ESPEJO
    if row["Espejo"]:
        return ["background-color: #99ccff"] * len(row)

    # DUPLICADO
    if row["Duplicado"]:
        return ["background-color: #ff9999"] * len(row)

    # PENDIENTE
    if row["Estado"] == "Pendiente":
        return ["background-color: #fff3b0"] * len(row)

    return [""] * len(row)


# =====================================
# CARGAR ARCHIVO
# =====================================

archivo = st.file_uploader(
    "📂 Cargar Excel Cuenta 14",
    type=["xlsx", "xls", "csv"]
)

# =====================================
# PROCESO
# =====================================

if archivo:

    df = cargar_archivo(archivo)

    df = limpiar_columnas(df)

    df = convertir_numeros(df)

    # =====================================
    # FECHAS
    # =====================================

    if "Fecha" in df.columns:

        df["Fecha"] = pd.to_datetime(
            df["Fecha"],
            errors="coerce"
        )

    # =====================================
    # ANALISIS
    # =====================================

    df = detectar_regularizacion(df)

    df = detectar_duplicados(df)

    # =====================================
    # RIESGO
    # =====================================

    df["Riesgo"] = df.apply(
        riesgo,
        axis=1
    )

    # =====================================
    # FORMATO NUMEROS
    # =====================================

    columnas_formato = [
        "Débito",
        "Crédito",
        "Saldo",
        "T/C"
    ]

    for col in columnas_formato:

        if col in df.columns:

            df[col] = (
                df[col]
                .astype(float)
                .round(2)
            )

    # =====================================
    # KPIS
    # =====================================

    total_debito = df["Débito"].sum()

    total_credito = df["Crédito"].sum()

    pendientes = df[
        df["Estado"] == "Pendiente"
    ]["Débito"].sum()

    duplicados = df["Duplicado"].sum()

    regularizados = df["Espejo"].sum()

    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric(
        "💸 Débito",
        f"S/ {total_debito:,.2f}"
    )

    col2.metric(
        "💰 Crédito",
        f"S/ {total_credito:,.2f}"
    )

    col3.metric(
        "⚠️ Pendientes",
        f"S/ {pendientes:,.2f}"
    )

    col4.metric(
        "🔴 Duplicados",
        duplicados
    )

    col5.metric(
        "🔵 Regularizados",
        regularizados
    )

    st.divider()

    # =====================================
    # FILTROS
    # =====================================

    st.sidebar.header("🔎 Filtros")

    riesgo_select = st.sidebar.multiselect(
        "Riesgo",
        df["Riesgo"].unique(),
        default=df["Riesgo"].unique()
    )

    df_filtrado = df[
        df["Riesgo"].isin(riesgo_select)
    ]

    # =====================================
    # TABLA PRINCIPAL
    # =====================================

    st.subheader("📄 Análisis Inteligente")

    columnas_mostrar = [

        "Cuenta",
        "Descripción",
        "Débito",
        "Crédito",
        "Saldo",
        "T/C",
        "Fecha",
        "Concepto",
        "Estado",
        "Relacionado",
        "Duplicado",
        "Espejo",
        "Riesgo"
    ]

    columnas_existentes = [
        c for c in columnas_mostrar
        if c in df_filtrado.columns
    ]

    st.dataframe(
        df_filtrado[columnas_existentes]
        .style
        .format({
            "Débito": "{:,.2f}",
            "Crédito": "{:,.2f}",
            "Saldo": "{:,.2f}",
            "T/C": "{:,.3f}"
        })
        .apply(colorear_filas, axis=1),
        use_container_width=True,
        height=700
    )

    # =====================================
    # DASHBOARD
    # =====================================

    st.subheader("📈 Dashboard")

    resumen = (
        df_filtrado
        .groupby("Riesgo")[["Débito", "Crédito"]]
        .sum()
        .reset_index()
    )

    fig = px.bar(
        resumen,
        x="Riesgo",
        y=["Débito", "Crédito"],
        barmode="group",
        title="Análisis de Riesgo"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    # =====================================
    # DUPLICADOS
    # =====================================

    st.subheader("🔴 Posibles Duplicados")

    dup_df = df_filtrado[
        df_filtrado["Duplicado"]
    ]

    if not dup_df.empty:

        st.dataframe(
            dup_df.style.format({
                "Débito": "{:,.2f}",
                "Crédito": "{:,.2f}"
            }),
            use_container_width=True
        )

    else:

        st.success(
            "✅ No se encontraron duplicados"
        )

    # =====================================
    # EXPORTAR
    # =====================================

    output = BytesIO()

    with pd.ExcelWriter(
        output,
        engine="openpyxl"
    ) as writer:

        df_filtrado.to_excel(
            writer,
            index=False,
            sheet_name="Analisis"
        )

        dup_df.to_excel(
            writer,
            index=False,
            sheet_name="Duplicados"
        )

    output.seek(0)

    st.download_button(
        label="⬇️ Descargar análisis",
        data=output,
        file_name="Analisis_Cuenta14.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

else:

    st.info(
        "👆 Carga un Excel para iniciar el análisis"
    )
