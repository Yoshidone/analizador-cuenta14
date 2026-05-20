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

- Regularizaciones
- Duplicados
- Pendientes
- Riesgos
- Relación Manual
- Exportación automática
""")

# =====================================
# SESSION STATE
# =====================================

if "df_master" not in st.session_state:
    st.session_state.df_master = None

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

    df["Espejo"] = False

    creditos_usados = []

    debitos = df[
        df["Débito"] > 0
    ]

    creditos = df[
        df["Crédito"] > 0
    ]

    for i, deb in debitos.iterrows():

        monto_debito = deb["Débito"]

        texto_debito = str(
            deb.get("Concepto", "")
        ).upper()

        palabras_debito = texto_debito.split()

        palabras_clave = [
            p for p in palabras_debito
            if len(p) > 3
        ]

        posibles = creditos[

            (
                creditos["Crédito"] == monto_debito
            )

            &

            (
                creditos["Concepto"]
                .astype(str)
                .str.upper()
                .apply(

                    lambda x:

                    any(
                        palabra in x
                        for palabra in palabras_clave
                    )

                )
            )

            &

            (
                ~creditos.index.isin(
                    creditos_usados
                )
            )

        ]

        if not posibles.empty:

            cred = posibles.iloc[0]

            idx = cred.name

            df.at[i, "Estado"] = "Regularizado"

            df.at[i, "Espejo"] = True

            df.at[idx, "Estado"] = "Regularizado"

            df.at[idx, "Espejo"] = True

            creditos_usados.append(idx)

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

    if row["Espejo"]:
        return ["background-color: #99ccff"] * len(row)

    if row["Duplicado"]:
        return ["background-color: #ff9999"] * len(row)

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

    # =====================================
    # CARGA SOLO UNA VEZ
    # =====================================

    if st.session_state.df_master is None:

        df = cargar_archivo(archivo)

        df = limpiar_columnas(df)

        df = convertir_numeros(df)

        if "Fecha" in df.columns:

            df["Fecha"] = pd.to_datetime(
                df["Fecha"],
                errors="coerce"
            )

        df = detectar_regularizacion(df)

        df = detectar_duplicados(df)

        df["Riesgo"] = df.apply(
            riesgo,
            axis=1
        )

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

        df["Grupo"] = ""

        contador = 1

        debitos = df[
            df["Débito"] > 0
        ]

        creditos = df[
            df["Crédito"] > 0
        ]

        creditos_usados = []

        for i, deb in debitos.iterrows():

            monto = deb["Débito"]

            texto_debito = str(
                deb.get("Concepto", "")
            ).upper()

            palabras_debito = texto_debito.split()

            palabras_clave = [
                p for p in palabras_debito
                if len(p) > 3
            ]

            posibles = creditos[

                (
                    creditos["Crédito"] == monto
                )

                &

                (
                    creditos["Concepto"]
                    .astype(str)
                    .str.upper()
                    .apply(

                        lambda x:

                        any(
                            palabra in x
                            for palabra in palabras_clave
                        )

                    )
                )

                &

                (
                    ~creditos.index.isin(
                        creditos_usados
                    )
                )

            ]

            if not posibles.empty:

                cred = posibles.iloc[0]

                idx = cred.name

                grupo = f"GRUPO {contador}"

                df.at[i, "Grupo"] = grupo

                df.at[idx, "Grupo"] = grupo

                creditos_usados.append(idx)

                contador += 1

        st.session_state.df_master = df

    # =====================================
    # USAR SESSION
    # =====================================

    df = st.session_state.df_master

    # =====================================
    # ORDEN FINAL
    # =====================================

    df = df.sort_values(
        by=["Grupo", "Fecha"],
        ascending=True
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
        "🟡 Pendientes",
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
        "Duplicado",
        "Espejo",
        "Grupo",
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
    # PENDIENTES
    # =====================================

    st.subheader("🟡 Movimientos Pendientes")

    pendientes_df = df_filtrado[
        df_filtrado["Estado"] == "Pendiente"
    ]

    if not pendientes_df.empty:

        st.dataframe(
            pendientes_df.style.format({
                "Débito": "{:,.2f}",
                "Crédito": "{:,.2f}",
                "Saldo": "{:,.2f}",
                "T/C": "{:,.3f}"
            }),
            use_container_width=True
        )

    else:

        st.success(
            "✅ No existen movimientos pendientes"
        )

    # =====================================
    # RELACION MANUAL
    # =====================================

    st.subheader("🛠 Relacionar Manualmente")

    debitos_pendientes = df[
        (df["Estado"] == "Pendiente")
        & (df["Débito"] > 0)
    ]

    creditos_pendientes = df[
        (df["Estado"] == "Pendiente")
        & (df["Crédito"] > 0)
    ]

    if not debitos_pendientes.empty and not creditos_pendientes.empty:

        debito_sel = st.multiselect(
            "Seleccionar Débitos",
            debitos_pendientes.index.tolist(),
            format_func=lambda x:
                f"{df.loc[x,'Fecha']} | "
                f"{df.loc[x,'Concepto']} | "
                f"Débito: {df.loc[x,'Débito']:,.2f}",
            key="debito_manual"
        )

        credito_sel = st.multiselect(
            "Seleccionar Créditos",
            creditos_pendientes.index.tolist(),
            format_func=lambda x:
                f"{df.loc[x,'Fecha']} | "
                f"{df.loc[x,'Concepto']} | "
                f"Crédito: {df.loc[x,'Crédito']:,.2f}",
            key="credito_manual"
        )

        total_debitos_manual = (
            df.loc[debito_sel, "Débito"].sum()
            if debito_sel else 0
        )

        total_creditos_manual = (
            df.loc[credito_sel, "Crédito"].sum()
            if credito_sel else 0
        )

        diferencia_manual = (
            total_debitos_manual
            - total_creditos_manual
        )

        st.info(
            f"""
💸 Total Débitos: S/ {total_debitos_manual:,.2f}

💰 Total Créditos: S/ {total_creditos_manual:,.2f}

📌 Diferencia: S/ {diferencia_manual:,.2f}
"""
        )

        if st.button("✅ Relacionar Manualmente"):

            grupo_manual = (
                f"MANUAL "
                f"{len(df[df['Grupo'].astype(str).str.contains('MANUAL', na=False)]) + 1}"
            )

            # =====================================
            # DEBITOS
            # =====================================

            for idx in debito_sel:

                df.at[idx, "Estado"] = "Regularizado Manual"

                df.at[idx, "Espejo"] = True

                df.at[idx, "Grupo"] = grupo_manual

                df.at[idx, "Riesgo"] = "🔵 Regularizado"

            # =====================================
            # CREDITOS
            # =====================================

            for idx in credito_sel:

                df.at[idx, "Estado"] = "Regularizado Manual"

                df.at[idx, "Espejo"] = True

                df.at[idx, "Grupo"] = grupo_manual

                df.at[idx, "Riesgo"] = "🔵 Regularizado"

            st.session_state.df_master = df

            st.success(
                f"✅ Grupo manual creado: {grupo_manual}"
            )

            st.rerun()

    else:

        st.info(
            "No existen pendientes para relacionar"
        )

    # =====================================
    # EXPORTAR
    # =====================================

    output = BytesIO()

    with pd.ExcelWriter(
        output,
        engine="openpyxl"
    ) as writer:

        df.to_excel(
            writer,
            index=False,
            sheet_name="Analisis"
        )

        dup_df.to_excel(
            writer,
            index=False,
            sheet_name="Duplicados"
        )

        pendientes_df.to_excel(
            writer,
            index=False,
            sheet_name="Pendientes"
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
