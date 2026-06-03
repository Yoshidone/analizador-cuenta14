# ============================================================
# ANALIZADOR INTELIGENTE - CUENTA 14
# ============================================================

import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO

# ============================================================
# CONFIGURACIÓN DE PÁGINA
# ============================================================

st.set_page_config(
    page_title="Analizador Cuenta 14",
    layout="wide"
)

st.title("📊 Analizador Inteligente - Cuenta 14")

st.markdown("""
Sistema automático para detectar:
**Regularizaciones · Duplicados · Pendientes · Riesgos · Relación Manual · Exportación**
""")

# ============================================================
# SESSION STATE
# ============================================================

if "df_master" not in st.session_state:
    st.session_state.df_master = None


# ============================================================
# FUNCIONES DE CARGA Y LIMPIEZA
# ============================================================

def cargar_archivo(archivo):
    """Lee CSV o Excel y retorna un DataFrame."""
    if archivo.name.endswith(".csv"):
        return pd.read_csv(archivo)
    return pd.read_excel(archivo)


def limpiar_columnas(df):
    """Elimina espacios en blanco de los nombres de columnas."""
    df.columns = df.columns.astype(str).str.strip()
    return df


def convertir_numeros(df):
    """Convierte las columnas numéricas principales a float."""
    columnas_numericas = ["Débito", "Crédito", "Saldo", "T/C"]
    for col in columnas_numericas:
        if col in df.columns:
            df[col] = (
                df[col]
                .astype(str)
                .str.replace(",", "", regex=False)
                .str.strip()
            )
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


# ============================================================
# FUNCIONES DE ANÁLISIS
# ============================================================

def detectar_regularizacion(df):
    """
    Marca como 'Regularizado' los pares débito-crédito
    que coinciden por monto y palabras clave en Concepto.
    """
    df["Estado"] = "Pendiente"
    df["Espejo"] = False

    debitos  = df[df["Débito"]  > 0]
    creditos = df[df["Crédito"] > 0]
    creditos_usados = []

    for i, deb in debitos.iterrows():

        monto = deb["Débito"]
        palabras_clave = [
            p for p in str(deb.get("Concepto", "")).upper().split()
            if len(p) > 3
        ]

        posibles = creditos[
            (creditos["Crédito"] == monto)
            & (
                creditos["Concepto"]
                .astype(str)
                .str.upper()
                .apply(lambda x: any(p in x for p in palabras_clave))
            )
            & (~creditos.index.isin(creditos_usados))
        ]

        if not posibles.empty:
            idx = posibles.iloc[0].name
            df.at[i,   "Estado"] = "Regularizado"
            df.at[i,   "Espejo"] = True
            df.at[idx, "Estado"] = "Regularizado"
            df.at[idx, "Espejo"] = True
            creditos_usados.append(idx)

    return df


def detectar_duplicados(df):
    """Marca filas con datos exactamente iguales como duplicados."""
    columnas_dup = ["Cuenta", "Fecha", "Débito", "Crédito", "Concepto"]
    cols_existentes = [c for c in columnas_dup if c in df.columns]
    df["Duplicado"] = df.duplicated(subset=cols_existentes, keep=False)
    return df


def asignar_grupos(df):
    """
    Agrupa pares regularizados automáticamente bajo un mismo
    código 'GRUPO N' para facilitar la trazabilidad.
    """
    df["Grupo"] = ""
    contador = 1

    debitos  = df[df["Débito"]  > 0]
    creditos = df[df["Crédito"] > 0]
    creditos_usados = []

    for i, deb in debitos.iterrows():

        monto = deb["Débito"]
        palabras_clave = [
            p for p in str(deb.get("Concepto", "")).upper().split()
            if len(p) > 3
        ]

        posibles = creditos[
            (creditos["Crédito"] == monto)
            & (
                creditos["Concepto"]
                .astype(str)
                .str.upper()
                .apply(lambda x: any(p in x for p in palabras_clave))
            )
            & (~creditos.index.isin(creditos_usados))
        ]

        if not posibles.empty:
            idx = posibles.iloc[0].name
            grupo = f"GRUPO {contador}"
            df.at[i,   "Grupo"] = grupo
            df.at[idx, "Grupo"] = grupo
            creditos_usados.append(idx)
            contador += 1

    return df


# ============================================================
# ETIQUETA DE RIESGO
# ============================================================

def clasificar_riesgo(row):
    """Asigna una etiqueta de riesgo visual a cada fila."""
    if row["Duplicado"]:
        return "🔴 Duplicado"
    if row["Espejo"]:
        return "🔵 Regularizado"
    if row["Estado"] == "Pendiente":
        return "🟡 Pendiente"
    return "🟢 Normal"


# ============================================================
# ESTILOS DE TABLA
# ============================================================

def colorear_filas(row):
    """Aplica colores de fondo según el estado de cada fila."""
    if row["Espejo"]:
        return ["background-color: #99ccff"] * len(row)
    if row["Duplicado"]:
        return ["background-color: #ff9999"] * len(row)
    if row["Estado"] == "Pendiente":
        return ["background-color: #fff3b0"] * len(row)
    return [""] * len(row)


# ============================================================
# CARGA DE ARCHIVO
# ============================================================

archivo = st.file_uploader(
    "📂 Cargar Excel Cuenta 14",
    type=["xlsx", "xls", "csv"]
)

# ============================================================
# PROCESO PRINCIPAL
# ============================================================

if archivo:

    # --- Procesamiento inicial (solo una vez por sesión) ---
    if st.session_state.df_master is None:

        df = cargar_archivo(archivo)
        df = limpiar_columnas(df)
        df = convertir_numeros(df)

        if "Fecha" in df.columns:
            df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")

        df = detectar_regularizacion(df)
        df = detectar_duplicados(df)
        df = asignar_grupos(df)

        df["Riesgo"] = df.apply(clasificar_riesgo, axis=1)

        # Redondear columnas numéricas
        for col in ["Débito", "Crédito", "Saldo", "T/C"]:
            if col in df.columns:
                df[col] = df[col].astype(float).round(2)

        st.session_state.df_master = df

    # --- Leer desde sesión ---
    df = st.session_state.df_master

    # --- Orden de visualización ---
    df = df.sort_values(by=["Grupo", "Fecha"], ascending=True)

    # --------------------------------------------------------
    # KPIs
    # --------------------------------------------------------

    total_debito  = df["Débito"].sum()
    total_credito = df["Crédito"].sum()
    pendientes    = df[df["Estado"] == "Pendiente"]["Débito"].sum()
    n_duplicados  = df["Duplicado"].sum()
    n_regularizados = df["Espejo"].sum()

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("💸 Débito",        f"S/ {total_debito:,.2f}")
    col2.metric("💰 Crédito",       f"S/ {total_credito:,.2f}")
    col3.metric("🟡 Pendientes",    f"S/ {pendientes:,.2f}")
    col4.metric("🔴 Duplicados",    n_duplicados)
    col5.metric("🔵 Regularizados", n_regularizados)

    st.divider()

    # --------------------------------------------------------
    # FILTROS (SIDEBAR)
    # --------------------------------------------------------

    st.sidebar.header("🔎 Filtros")
    riesgo_select = st.sidebar.multiselect(
        "Riesgo",
        df["Riesgo"].unique(),
        default=df["Riesgo"].unique()
    )
    df_filtrado = df[df["Riesgo"].isin(riesgo_select)]

    # --------------------------------------------------------
    # TABLA PRINCIPAL
    # --------------------------------------------------------

    st.subheader("📄 Análisis Inteligente")

    columnas_mostrar = [
        "Cuenta", "Descripción", "Débito", "Crédito",
        "Saldo", "T/C", "Fecha", "Concepto",
        "Estado", "Duplicado", "Espejo", "Grupo", "Riesgo"
    ]
    cols_existentes = [c for c in columnas_mostrar if c in df_filtrado.columns]

    st.dataframe(
        df_filtrado[cols_existentes]
        .style
        .format({
            "Débito":  "{:,.2f}",
            "Crédito": "{:,.2f}",
            "Saldo":   "{:,.2f}",
            "T/C":     "{:,.3f}"
        })
        .apply(colorear_filas, axis=1),
        use_container_width=True,
        height=700
    )

    # --------------------------------------------------------
    # DASHBOARD
    # --------------------------------------------------------

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
    st.plotly_chart(fig, use_container_width=True)

    # --------------------------------------------------------
    # DUPLICADOS
    # --------------------------------------------------------

    st.subheader("🔴 Posibles Duplicados")

    dup_df = df_filtrado[df_filtrado["Duplicado"]]

    if not dup_df.empty:
        st.dataframe(
            dup_df.style.format({"Débito": "{:,.2f}", "Crédito": "{:,.2f}"}),
            use_container_width=True
        )
    else:
        st.success("✅ No se encontraron duplicados")

    # --------------------------------------------------------
    # PENDIENTES
    # --------------------------------------------------------

    st.subheader("🟡 Movimientos Pendientes")

    pendientes_df = df_filtrado[df_filtrado["Estado"] == "Pendiente"]

    if not pendientes_df.empty:
        st.dataframe(
            pendientes_df.style.format({
                "Débito":  "{:,.2f}",
                "Crédito": "{:,.2f}",
                "Saldo":   "{:,.2f}",
                "T/C":     "{:,.3f}"
            }),
            use_container_width=True
        )
    else:
        st.success("✅ No existen movimientos pendientes")

    # --------------------------------------------------------
    # RELACIÓN MANUAL
    # --------------------------------------------------------

    st.subheader("🛠 Relacionar Manualmente")

    debitos_pendientes  = df[(df["Estado"] == "Pendiente") & (df["Débito"]  > 0)]
    creditos_pendientes = df[(df["Estado"] == "Pendiente") & (df["Crédito"] > 0)]

    if not debitos_pendientes.empty and not creditos_pendientes.empty:

        debito_sel = st.multiselect(
            "Seleccionar Débitos",
            debitos_pendientes.index.tolist(),
            format_func=lambda x: (
                f"{df.loc[x,'Fecha']} | "
                f"{df.loc[x,'Concepto']} | "
                f"Débito: {df.loc[x,'Débito']:,.2f}"
            ),
            key="debito_manual"
        )

        credito_sel = st.multiselect(
            "Seleccionar Créditos",
            creditos_pendientes.index.tolist(),
            format_func=lambda x: (
                f"{df.loc[x,'Fecha']} | "
                f"{df.loc[x,'Concepto']} | "
                f"Crédito: {df.loc[x,'Crédito']:,.2f}"
            ),
            key="credito_manual"
        )

        total_deb_manual  = df.loc[debito_sel,  "Débito"].sum()  if debito_sel  else 0
        total_cred_manual = df.loc[credito_sel, "Crédito"].sum() if credito_sel else 0
        diferencia_manual = total_deb_manual - total_cred_manual

        st.info(
            f"💸 Total Débitos: S/ {total_deb_manual:,.2f}  \n"
            f"💰 Total Créditos: S/ {total_cred_manual:,.2f}  \n"
            f"📌 Diferencia: S/ {diferencia_manual:,.2f}"
        )

        if st.button("✅ Relacionar Manualmente"):

            n_manuales = df["Grupo"].astype(str).str.contains("MANUAL", na=False).sum()
            grupo_manual = f"MANUAL {n_manuales + 1}"

            for idx in debito_sel + credito_sel:
                df.at[idx, "Estado"] = "Regularizado Manual"
                df.at[idx, "Espejo"] = True
                df.at[idx, "Grupo"]  = grupo_manual
                df.at[idx, "Riesgo"] = "🔵 Regularizado"

            st.session_state.df_master = df
            st.success(f"✅ Grupo manual creado: {grupo_manual}")
            st.rerun()

    else:
        st.info("No existen pendientes para relacionar")

    # --------------------------------------------------------
    # EXPORTAR A EXCEL
    # --------------------------------------------------------

    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer,            index=False, sheet_name="Analisis")
        dup_df.to_excel(writer,        index=False, sheet_name="Duplicados")
        pendientes_df.to_excel(writer, index=False, sheet_name="Pendientes")
    output.seek(0)

    st.download_button(
        label="⬇️ Descargar análisis",
        data=output,
        file_name="Analisis_Cuenta14.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

else:
    st.info("👆 Carga un Excel para iniciar el análisis")
