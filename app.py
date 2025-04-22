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
        # Descartar columnas futuras o de año, ajustando según la lógica original
        # Usamos la lógica de descarte de tu código original
        descartar = [col for col in df.columns if "MES_" in col and "2024_2025" in col and int(col.split("_")[-1]) > 16]
        descartar += [col for col in df.columns if "ANO_" in col]
        df.drop(columns=descartar, inplace=True, errors='ignore') # Añadimos errors='ignore' por seguridad
        df["CLASE"] = df["RUBRO"].replace("ACUARISMO", "COMERCIO")
        return df
    except Exception as e:
        st.error(f"Error al cargar el archivo: {e}")
        return None

def clasificar_cliente(row, columnas_meses):
    """Clasifica al cliente basado en la frecuencia y el promedio de compra."""
    # Mantenemos la lógica de clasificación original, que usa el promedio solo de meses con compra.
    # Si quisieras que esta clasificación usara el promedio sobre 12 meses (incluyendo ceros),
    # habría que redefinir las reglas aquí, lo cual no es el objetivo actual.
    compras = row[columnas_meses]
    frecuencia = (compras > 0).sum()
    monto_total = compras.sum()
    promedio_mensual = monto_total / frecuencia if frecuencia > 0 else 0

    ultimos_6_meses = columnas_meses[-6:] if len(columnas_meses) >= 6 else columnas_meses # Asegurar que haya al menos 6 meses
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
        # Asegurarse de que solo se seleccionen columnas de meses válidas y ordenarlas
        # Usamos la clave de ordenamiento de tu código original, con pequeña mejora de seguridad
        columnas_meses = sorted(
            [col for col in ventas.columns if "MES_" in col and len(col.split('_')) >= 3 and col.split('_')[-1].isdigit()],
            key=lambda x: (int(x.split("_")[0]) if x.split("_")[0].isdigit() else 0, int(x.split("_")[-1]) if x.split("_")[-1].isdigit() else 0) # Manejo básico de error por si el split falla
        )

        # Asegurarse de que las columnas de meses existan antes de usarlas
        if not columnas_meses:
            st.error("No se encontraron columnas de meses válidas en el archivo. Asegúrate de que tengan el formato 'AÑO_MES_NUMERO' (Ej: 2023_MES_1, 2024_MES_15).")
            st.stop() # Detiene la ejecución si no hay columnas de meses

        ventas[columnas_meses] = ventas[columnas_meses].fillna(0).astype(float)

        ventas["CLASE_CLIENTE"] = ventas.apply(lambda row: clasificar_cliente(row, columnas_meses), axis=1)
        ventas["ACCION_MARKETING"] = ventas["CLASE_CLIENTE"].map(ACCIONES_MARKETING)

        # Determinar mes actual y de proyección (ajustar índices si es necesario)
        mes_actual = columnas_meses[-1] if columnas_meses else None
        mes_proyeccion = columnas_meses[-2] if len(columnas_meses) > 1 else None

        # --- SIDEBAR ---
        st.sidebar.header("🔎 Búsqueda de Cliente")
        modo_busqueda = st.sidebar.radio("Modo de Búsqueda", ["Por Cliente", "Por Segmento"])

        # --- MODO CLIENTE ---
        if modo_busqueda == "Por Cliente":
            cliente_codigo = st.sidebar.text_input("Código del Cliente:")
            # Ajuste: solo mostrar selectbox si no hay código y hay nombres
            cliente_nombre = None
            if not cliente_codigo and not ventas["NOM_LEGAL"].dropna().empty:
                 cliente_nombre = st.sidebar.selectbox("Seleccioná un cliente", sorted(ventas["NOM_LEGAL"].dropna().unique()))


            df_filtrado = pd.DataFrame() # Inicializar vacío
            if cliente_codigo:
                df_filtrado = ventas[ventas["CODIGO"].astype(str).str.strip() == cliente_codigo.strip()].copy() # Usar .copy() para evitar SettingWithCopyWarning
            elif cliente_nombre:
                df_filtrado = ventas[ventas["NOM_LEGAL"] == cliente_nombre].copy() # Usar .copy()


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

                    # --- CALCULO DE PROMEDIO ULTIMOS 12 MESES (INCLUYENDO CEROS) ---
                    # Tomamos los últimos 12 meses o menos si no hay tantos
                    meses_ultimos_12 = columnas_meses[-12:] if len(columnas_meses) >= 12 else columnas_meses
                    total_ultimos_12 = cliente[meses_ultimos_12].sum()
                    # Dividimos por la cantidad total de meses evaluados
                    num_meses_evaluar_cliente = len(meses_ultimos_12)

                    # Calcular promedio incluyendo ceros
                    promedio_ultimos_12_con_ceros = total_ultimos_12 / num_meses_evaluar_cliente if num_meses_evaluar_cliente > 0 else 0
                    # --- FIN CALCULO PROMEDIO CON CEROS ---

                    # Mostramos el nuevo promedio calculado
                    st.markdown(f"- **Promedio Compra ({num_meses_evaluar_cliente} meses, incl. ceros):** ${promedio_ultimos_12_con_ceros:,.2f}")
                    st.markdown(f"- **Total Comprado ({num_meses_evaluar_cliente} meses):** ${total_ultimos_12:,.2f}") # Mantenemos el total de los meses evaluados

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
                st.markdown("### 📊 Evolución de Compras") # Título más genérico
                # Asegurarse de tener suficientes meses para graficar los últimos 24
                num_meses_total = len(columnas_meses)
                meses_para_grafico = columnas_meses[-24:] if num_meses_total >= 24 else columnas_meses # Graficar hasta 24 meses o todos

                df_historial_grafico = pd.DataFrame({
                     "🗓️ Mes": meses_para_grafico,
                     "💰 Monto Comprado": cliente[meses_para_grafico].values
                })


                fig, ax = plt.subplots(figsize=(14, 6))
                sns.barplot(data=df_historial_grafico, x="🗓️ Mes", y="💰 Monto Comprado", palette="coolwarm", ax=ax)

                ax.set_title(f"📈 Evolución de Compras - Últimos {len(meses_para_grafico)} Meses", fontsize=18, weight='bold')
                ax.set_xlabel("Mes", fontsize=12)
                ax.set_ylabel("Monto Comprado ($)", fontsize=12)
                ax.tick_params(axis='x', rotation=45)
                ax.grid(axis="y", linestyle='--', alpha=0.4)
                plt.tight_layout()

                st.pyplot(fig)

                # --- OBJETIVOS ---
                st.markdown("### 🎯 Evaluación de Objetivos")
                # Usar el último mes y el penúltimo para la evaluación del objetivo
                valor_mes_actual = cliente.get(mes_actual, 0) if mes_actual else 0
                valor_mes_proyeccion = cliente.get(mes_proyeccion, 0) if mes_proyeccion else 0 # Asumiendo que el penúltimo es el mes del objetivo
                objetivo = OBJETIVOS.get(cliente["CLASE"], {}).get("OBJETIVO", 0)
                cumplio = "✅ Sí" if valor_mes_proyeccion >= objetivo else "❌ No"
                faltante = max(0, objetivo - valor_mes_actual) # Faltante basado en el último mes completo

                col3, col4 = st.columns(2)
                if mes_proyeccion:
                     col3.metric(f"¿Cumplió objetivo en {mes_proyeccion}?", cumplio, delta=f"${valor_mes_proyeccion:,.0f}")
                else:
                     col3.info("No hay suficientes meses para evaluar un objetivo histórico.")

                if mes_actual:
                    col4.metric(f"Faltante estimado para {mes_actual} vs objetivo", f"${faltante:,.0f}")
                else:
                    col4.info("No hay datos del último mes para estimar faltante.")


            else:
                st.warning("⚠️ No se encontraron resultados para esa búsqueda.")

        # --- MODO SEGMENTO ---
        else:
            st.sidebar.subheader("⚙️ Filtros de Segmentación")

            # Asegurarse de que hay suficientes meses para la frecuencia y promedio
            meses_para_filtros = columnas_meses[-12:] if len(columnas_meses) >= 12 else columnas_meses
            num_meses_filtros = len(meses_para_filtros)

            # Mensaje si hay menos de 12 meses
            if len(columnas_meses) > 0 and len(columnas_meses) < 12:
                st.warning(f"Solo se encontraron {len(columnas_meses)} meses de datos. Los filtros de frecuencia y promedio se aplicarán sobre los meses disponibles.")
            elif len(columnas_meses) == 0:
                 st.warning("No se encontraron columnas de meses válidas para los filtros.")

            # Filtro de Frecuencia con slider (como en tu código)
            segmento_frecuencia = st.sidebar.slider(f"Frecuencia de Compra ({num_meses_filtros} meses)", 0, num_meses_filtros, (0, num_meses_filtros))


            st.sidebar.subheader(f"💰 Filtrar por Promedio Mensual de Compra ({num_meses_filtros} meses, incl. ceros)")
            # --- CAMBIO: Usar number_input en lugar de slider para el promedio ---
            # Calculamos un valor por defecto para el máximo, pero el input permite escribir más
            max_total_posible = ventas[meses_para_filtros].sum(axis=1).max() if num_meses_filtros > 0 and not ventas[meses_para_filtros].empty else 0
            max_promedio_sugerido = (max_total_posible / num_meses_filtros) if num_meses_filtros > 0 and max_total_posible > 0 else 1000000
            max_promedio_default = int(max_promedio_sugerido * 1.5) + 100000

            min_promedio = st.sidebar.number_input("Mínimo Promedio Mensual", min_value=0, step=100_000, value=0)
            max_promedio = st.sidebar.number_input("Máximo Promedio Mensual", min_value=0, step=100_000, value=max_promedio_default) # Puedes ajustar el 'value' inicial
            # --- FIN CAMBIO number_input ---


            st.sidebar.subheader("⚙️ Filtrar por Rubro")
            # Usamos los checkboxes originales de tu código
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


            # Aplicar filtro de rubro primero
            if rubros_seleccionados:
                 df_segmento_filtrado = ventas[ventas['RUBRO'].isin(rubros_seleccionados)].copy()
            else:
                 df_segmento_filtrado = ventas[ventas['RUBRO'].isin([])].copy() # Retorna vacío si no hay rubros

            # --- CALCULAR FRECUENCIA Y EL NUEVO PROMEDIO PARA EL FILTRADO ---
            if num_meses_filtros > 0 and not df_segmento_filtrado.empty:
                 # Frecuencia (meses con compra > 0) - se mantiene este cálculo para el filtro de frecuencia
                 df_segmento_filtrado['FRECUENCIA_FILTRO'] = df_segmento_filtrado[meses_para_filtros].apply(lambda row: (row > 0).sum(), axis=1)

                 # Nuevo Promedio (total comprado en el período dividido por el número total de meses en el período)
                 total_comprado_filtro = df_segmento_filtrado[meses_para_filtros].sum(axis=1)
                 df_segmento_filtrado['PROMEDIO_FILTRO'] = total_comprado_filtro / num_meses_filtros # ¡Este es el cambio clave!
            else:
                 # Si no hay meses de filtro o el dataframe está vacío, estas columnas estarán vacías
                 df_segmento_filtrado['FRECUENCIA_FILTRO'] = pd.Series(dtype=float)
                 df_segmento_filtrado['PROMEDIO_FILTRO'] = pd.Series(dtype=float)
            # --- FIN CALCULOS PARA FILTRADO ---


            # --- APLICAR FILTROS (FRECUENCIA Y NUEVO PROMEDIO) ---
            # Solo aplicar si hay meses de filtro disponibles, de lo contrario df_segmento_final estará vacío
            if num_meses_filtros > 0:
                 df_segmento_final = df_segmento_filtrado[
                     (df_segmento_filtrado['FRECUENCIA_FILTRO'] >= segmento_frecuencia[0]) &
                     (df_segmento_filtrado['FRECUENCIA_FILTRO'] <= segmento_frecuencia[1]) &
                     (df_segmento_filtrado['PROMEDIO_FILTRO'] >= min_promedio) & # Usamos min_promedio
                     (df_segmento_filtrado['PROMEDIO_FILTRO'] <= max_promedio) # Usamos max_promedio
                 ].copy()
            else:
                 # Si num_meses_filtros es 0, no hay datos para filtrar, se usa el df vacío inicial
                 df_segmento_final = df_segmento_filtrado # Que ya estará vacío
            # --- FIN APLICAR FILTROS ---


            # --- MOSTRAR SEGMENTO FILTRADO ---
            st.subheader(f"📋 Segmento Filtrado ({len(df_segmento_final)} clientes)")
            # Columnas a mostrar en la tabla del segmento
            # Mantenemos las columnas definidas en tu código original, incluyendo CLASE
            # Añadimos los nombres dinámicos para Frecuencia y Promedio
            columnas_a_mostrar = [
                "CODIGO",
                "NOM_LEGAL",
                "CLASE", # Mantenemos la CLASE original si es útil
                "E_MAIL",
                "TELEFONO",
                "PROVINCIA",
                f"Frecuencia ({num_meses_filtros}m)", # Nombre dinámico
                f"Promedio ({num_meses_filtros}m incl. 0)", # Nombre dinámico para el nuevo promedio
            ]

            # Renombrar las columnas calculadas para que coincidan con los nombres a mostrar
            # Solo intentamos renombrar si las columnas originales existen (ej: si num_meses_filtros > 0)
            nombres_calculados_map = {
                 'FRECUENCIA_FILTRO': f"Frecuencia ({num_meses_filtros}m)",
                 'PROMEDIO_FILTRO': f"Promedio ({num_meses_filtros}m incl. 0)"
            }
            cols_to_rename = {k: v for k, v in nombres_calculados_map.items() if k in df_segmento_final.columns}
            if cols_to_rename:
                 df_segmento_final.rename(columns=cols_to_rename, inplace=True)

            # Asegurarnos de que solo mostramos columnas que realmente existen en el dataframe final
            columnas_a_mostrar_existentes = [col for col in columnas_a_mostrar if col in df_segmento_final.columns]

            # Formatear el promedio para mostrar en la tabla
            nombre_col_promedio_final = f"Promedio ({num_meses_filtros}m incl. 0)"
            if nombre_col_promedio_final in columnas_a_mostrar_existentes:
                 styled_segment_df = df_segmento_final[columnas_a_mostrar_existentes].style \
                     .format({nombre_col_promedio_final: "${:,.0f}"})
            else:
                 # Si la columna de promedio no existe (ej: 0 meses de datos), mostrar sin formato especial
                 styled_segment_df = df_segmento_final[columnas_a_mostrar_existentes]


            st.dataframe(styled_segment_df, use_container_width=True)

            # --- CAMBIO: Eliminar el bloque de análisis del segmento (incluida la gráfica) ---
            # Eliminamos todo el bloque que empieza con st.markdown("### 📊 Análisis del Segmento")
            # --- FIN CAMBIO ---

else:
    st.info("⬆️ Por favor, sube un archivo Excel para comenzar el análisis.")
