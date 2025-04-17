import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

# --- CONFIGURACIÓN GENERAL ---
st.set_page_config(page_title="Clientes Millex", layout="wide")
st.title("📈 Dashboard de Clientes - Millex")
st.markdown("Análisis personalizado de clientes con clasificación y acciones de marketing sugeridas.")
st.markdown("---")

# --- FUNCIONES ---
@st.cache_data
def cargar_datos(uploaded_file):
    """Carga los datos desde un archivo Excel subido."""
    try:
        df = pd.read_excel(uploaded_file)
        df.columns = df.columns.str.replace(" ", "_").str.upper()
        descartar = [col for col in df.columns if "MES_" in col and "2024_2025" in col and int(col.split("_")[-1]) > 16]
        descartar += [col for col in df.columns if "ANO_" in col]
        df.drop(columns=descartar, inplace=True)
        df["CLASE"] = df["RUBRO"].replace("ACUARISMO", "COMERCIO")
        return df
    except Exception as e:
        st.error(f"Error al cargar el archivo: {e}")
        return None

def clasificar_cliente(row, columnas_meses):
    compras = row[columnas_meses]
    frecuencia = (compras > 0).sum()
    monto_total = compras.sum()
    promedio_mensual = monto_total / frecuencia if frecuencia > 0 else 0

    ultimos_6_meses = columnas_meses[-6:]
    compras_ultimos_6 = row[ultimos_6_meses]
    activo_ultimos_6 = (compras_ultimos_6 > 0).any()

    if frecuencia == 0 or promedio_mensual < 300_000:
        return "potencial"

    if not activo_ultimos_6 and frecuencia >= 1 and frecuencia <= 3:
        return "inactivo"

    if frecuencia >= 8:
        return "habitualgold" if promedio_mensual > 5_000_000 else "habitual"

    if 6 <= frecuencia <= 7:
        return "regular"

    if 4 <= frecuencia <= 5:
        return "esporadico"

    return "potencial" # Caso por defecto para evitar errores

# --- PARÁMETROS ---
OBJETIVOS = {
    "COMERCIO": {"OBJETIVO": 1_100_000, "DESCUENTO": "NC 10%"},
    "DISTRIBUIDOR": {"OBJETIVO": 5_000_000, "DESCUENTO": "25%"}
}

ACCIONES_MARKETING = {
    "habitualgold": "🎁 Programa de fidelidad exclusivo + regalos sorpresa",
    "habitual": "📢 Descuento adicional + referidos",
    "regular": "📬 Emails con novedades destacadas",
    "esporadico": "⚡ Promos flash personalizadas",
    "potencial": "🎉 Bienvenida + primer descuento",
    "inactivo": "🕑 Reactivación con beneficio extra"
}

# --- CARGA DE DATOS ---
st.sidebar.header("📁 Cargar Archivo")
uploaded_file = st.sidebar.file_uploader("Subir archivo Excel", type=["xlsx"])

if uploaded_file is not None:
    ventas = cargar_datos(uploaded_file)
    if ventas is not None:
        columnas_meses = sorted(
            [col for col in ventas.columns if "MES_" in col],
            key=lambda x: (int(x.split("_")[0]), int(x.split("_")[-1]))
        )
        ventas[columnas_meses] = ventas[columnas_meses].fillna(0).astype(float)

        ventas["CLASE_CLIENTE"] = ventas.apply(lambda row: clasificar_cliente(row, columnas_meses), axis=1)
        ventas["ACCION_MARKETING"] = ventas["CLASE_CLIENTE"].map(ACCIONES_MARKETING)

        mes_actual = columnas_meses[-1]
        mes_proyeccion = columnas_meses[-2] if len(columnas_meses) > 1 else None

        # --- SIDEBAR ---
        st.sidebar.header("🔎 Búsqueda de Cliente")
        modo_busqueda = st.sidebar.radio("Modo de Búsqueda", ["Por Cliente", "Por Segmento"])

        # --- MODO CLIENTE ---
        if modo_busqueda == "Por Cliente":
            cliente_codigo = st.sidebar.text_input("Código del Cliente:")
            cliente_nombre = st.sidebar.selectbox("Seleccioná un cliente", sorted(ventas["NOM_LEGAL"].dropna().unique()))

            if cliente_codigo:
                df_filtrado = ventas[ventas["CODIGO"].astype(str).str.strip() == cliente_codigo.strip()]
            elif cliente_nombre:
                df_filtrado = ventas[ventas["NOM_LEGAL"] == cliente_nombre]
            else:
                df_filtrado = ventas.copy()

            if not df_filtrado.empty:
                cliente = df_filtrado.iloc[0]
                col1, col2 = st.columns(2)

                with col1:
                    st.subheader(f"🧾 Cliente: {cliente['NOM_LEGAL']}")
                    st.markdown(f"- **Código:** {cliente['CODIGO']}")
                    st.markdown(f"- **Rubro:** {cliente['RUBRO']}")
                    st.markdown(f"- **Email:** {cliente.get('E_MAIL', 'No disponible')}")
                    st.markdown(f"- **Provincia:** {cliente.get('PROVINCIA', 'No disponible')}")
                    st.markdown(f"- **Teléfono:** {cliente.get('TELEFONO', 'No disponible')}")
                    total_ultimos_12 = cliente[columnas_meses[-12:]].sum()
                    frecuencia_ultimos_12 = (cliente[columnas_meses[-12:]] > 0).sum()
                    promedio_ultimos_12 = total_ultimos_12 / frecuencia_ultimos_12 if frecuencia_ultimos_12 > 0 else 0
                    st.markdown(f"- **Promedio Compra (Últ. 12 meses):** ${promedio_ultimos_12:,.2f}")
                    st.markdown(f"- **Total Comprado (Últ. 12 meses):** ${total_ultimos_12:,.2f}")
                    descuento = OBJETIVOS.get(cliente["CLASE"], {}).get("DESCUENTO", "No definido")
                    st.markdown(f"- **Descuento:** {descuento}")

                with col2:
                    st.subheader("📌 Acción de Marketing Sugerida")
                    st.info(cliente["ACCION_MARKETING"])

                # --- HISTORIAL DE COMPRAS EN TABLA ---
                st.markdown("### 💸 Historial de Compras Mensuales")
                df_historial = pd.DataFrame({
                    "🗓️ Mes": columnas_meses,
                    "💰 Monto Comprado": cliente[columnas_meses].values
                })

                styled_df = df_historial.style \
                    .format({"💰 Monto Comprado": "${:,.0f}"}) \
                    .background_gradient(cmap="YlGnBu", subset=["💰 Monto Comprado"]) \
                    .set_properties(**{
                        'font-size': '16px',
                        'font-family': 'Arial',
                        'text-align': 'center'
                    })

                st.dataframe(styled_df, use_container_width=True)

                # --- GRÁFICO DE BARRAS MEJORADO ---
                st.markdown("### 📊 Evolución de Compras (Últimos 24 Meses)")
                try:
                    idx_final = df_historial[df_historial["🗓️ Mes"] == "2024_2025_MES_16"].index[0]
                    df_historial_24 = df_historial.iloc[idx_final-23:idx_final+1]
                except:
                    df_historial_24 = df_historial.tail(24)

                fig, ax = plt.subplots(figsize=(14, 6))
                sns.barplot(data=df_historial_24, x="🗓️ Mes", y="💰 Monto Comprado", palette="coolwarm", ax=ax)

                ax.set_title("📈 Evolución de Compras - Últimos 24 Meses", fontsize=18, weight='bold')
                ax.set_xlabel("Mes", fontsize=12)
                ax.set_ylabel("Monto Comprado ($)", fontsize=12)
                ax.tick_params(axis='x', rotation=45)
                ax.grid(axis="y", linestyle='--', alpha=0.4)
                plt.tight_layout()

                st.pyplot(fig)

                # --- OBJETIVOS ---
                st.markdown("### 🎯 Evaluación de Objetivos")
                valor_mes_actual = cliente.get(mes_actual, 0)
                valor_mes_proyeccion = cliente.get(mes_proyeccion, 0) if mes_proyeccion else 0
                objetivo = OBJETIVOS.get(cliente["CLASE"], {}).get("OBJETIVO", 0)
                cumplio = "✅ Sí" if valor_mes_proyeccion >= objetivo else "❌ No"
                faltante = max(0, objetivo - valor_mes_actual)

                col3, col4 = st.columns(2)
                col3.metric(f"¿Cumplió objetivo en {mes_proyeccion}?", cumplio, delta=f"${valor_mes_proyeccion:,.0f}")
                col4.metric(f"Faltante estimado según {mes_actual}", f"${faltante:,.0f}")
            else:
                st.warning("⚠️ No se encontraron resultados para esa búsqueda.")

       # --- MODO SEGMENTO ---
        else:
            st.sidebar.subheader("⚙️ Filtros de Segmentación")
            segmento_frecuencia = st.sidebar.slider("Frecuencia de Compra (últimos 12 meses)", 0, 12, (0, 12))

            st.sidebar.subheader("💰 Filtrar por Promedio Mensual de Compra")
            min_promedio = st.sidebar.number_input("Mínimo Promedio Mensual de Compra", min_value=0, step=100000)
            max_promedio = st.sidebar.number_input("Máximo Promedio Mensual de Compra", min_value=0, step=100000, value=int(ventas[columnas_meses].max().max()) + 1000000)

            st.sidebar.subheader("⚙️ Filtrar por Rubro")
            mostrar_comercio = st.sidebar.checkbox("Comercio", value=True)
            mostrar_acuarismo = st.sidebar.checkbox("Acuarismo", value=True)
            mostrar_distribuidor = st.sidebar.checkbox("Distribuidor", value=True)

            rubros_seleccionados = []
            if mostrar_comercio:
                rubros_seleccionados.append("COMERCIO")
            if mostrar_acuarismo:
                rubros_seleccionados.append("ACUARISMO")
            if mostrar_distribuidor:
                rubros_seleccionados.append("DISTRIBUIDOR")

            df_segmento_filtrado = ventas.copy()
            df_segmento_filtrado = df_segmento_filtrado[df_segmento_filtrado['RUBRO'].isin(rubros_seleccionados)]

            # Calcular FRECUENCIA_12 y MONTO_TOTAL_12
            df_segmento_filtrado['FRECUENCIA_12'] = df_segmento_filtrado[columnas_meses[-12:]].apply(lambda row: (row > 0).sum(), axis=1)
            df_segmento_filtrado['MONTO_TOTAL_12'] = df_segmento_filtrado[columnas_meses[-12:]].sum(axis=1)

            # --- DataFrame base filtrado por frecuencia ---
            df_frecuencia_base = df_segmento_filtrado[(df_segmento_filtrado['FRECUENCIA_12'] >= segmento_frecuencia[0]) & (df_segmento_filtrado['FRECUENCIA_12'] <= segmento_frecuencia[1])].copy()

            # --- Filtrado por promedio (solo para el DataFrame base y clientes con compras) ---
            df_con_promedio = df_frecuencia_base[df_frecuencia_base['FRECUENCIA_12'] > 0].copy()
            df_con_promedio['PROMEDIO_MENSUAL_12'] = df_con_promedio['MONTO_TOTAL_12'] / df_con_promedio['FRECUENCIA_12']
            df_segmento_final = df_con_promedio[(df_con_promedio['PROMEDIO_MENSUAL_12'] >= min_promedio) & (df_con_promedio['PROMEDIO_MENSUAL_12'] <= max_promedio)].copy()

            # --- Filtrado de potenciales (SOLO los de frecuencia 0) ---
            df_potenciales = df_segmento_filtrado[df_segmento_filtrado['FRECUENCIA_12'] == 0].copy()
            # Agregamos los potenciales SOLO si el rango de frecuencia seleccionado incluye 0
            if segmento_frecuencia[0] == 0:
                df_segmento_final = pd.concat([df_segmento_final, df_potenciales]).drop_duplicates(subset=['CODIGO'])

            st.subheader(f"📋 Segmento Filtrado ({len(df_segmento_final)} clientes)")
            columnas_a_mostrar = ["CODIGO", "NOM_LEGAL", "CLASE", "E_MAIL", "TELEFONO", "PROVINCIA", "FRECUENCIA_12"]
            if 'PROMEDIO_MENSUAL_12' in df_segmento_final.columns:
                columnas_a_mostrar.append('PROMEDIO_MENSUAL_12')
            st.dataframe(df_segmento_final[columnas_a_mostrar], use_container_width=True)

            # Análisis del segmento (opcional)
            if not df_segmento_final.empty:
                st.markdown("### 📊 Análisis del Segmento")
                col_seg1 = st.columns(1)[0] # Ajustamos para una sola columna
                with col_seg1:
                    st.markdown("#### Distribución de Clases Originales")
                    clase_counts = df_segmento_final['CLASE'].value_counts()
                    fig_clase, ax_clase = plt.subplots()
                    ax_clase.pie(clase_counts, labels=clase_counts.index, autopct='%1.1f%%', startangle=90)
                    st.pyplot(fig_clase)
else:
    st.info("⬆️ Por favor, sube un archivo Excel para comenzar el análisis.")