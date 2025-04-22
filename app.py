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
        # Ajuste para leer 'AÑO_MES_NUMERO' independientemente del año específico 2024_2025
        # Descartamos cualquier columna MES_ que no contenga un número al final válido
        descartar = [col for col in df.columns if "MES_" in col and not col.split("_")[-1].isdigit()]
        # Descartamos columnas de AÑO_
        descartar += [col for col in df.columns if "ANO_" in col]

        # Lógica para descartar meses futuros si la columna tiene un formato específico (opcional, si aplica)
        # Aquí se asume que las columnas que terminan en _17, _18, etc., son futuras para el período 2024_2025
        # Puedes ajustar esta lógica si tus datos tienen otra convención
        descartar += [col for col in df.columns if "MES_" in col and "2024_2025" in col and int(col.split("_")[-1]) > 16] # Ejemplo de descarte específico

        df.drop(columns=descartar, errors='ignore', inplace=True) # Usar errors='ignore' para no fallar si alguna columna no existe
        df["CLASE"] = df["RUBRO"].replace("ACUARISMO", "COMERCIO") # Ajuste de rubro
        return df
    except Exception as e:
        st.error(f"Error al cargar el archivo: {e}")
        return None

def clasificar_cliente(row, columnas_meses):
    """Clasifica al cliente basado en la frecuencia y el promedio de compra (lógica original)."""
    # OJO: Esta función usa la lógica original de promedio sobre MESES CON COMPRA > 0.
    # Si quieres que la clasificación use el promedio sobre los 12 meses (incluyendo ceros),
    # habría que modificar esta función y redefinir las reglas de clasificación.
    # Por ahora, la mantenemos igual para no alterar las categorías existentes.
    compras = row[columnas_meses]
    frecuencia = (compras > 0).sum()
    monto_total = compras.sum()
    promedio_mensual = monto_total / frecuencia if frecuencia > 0 else 0

    # Lógica para identificar actividad reciente
    ultimos_6_meses = columnas_meses[-6:] if len(columnas_meses) >= 6 else columnas_meses
    compras_ultimos_6 = row[ultimos_6_meses]
    activo_ultimos_6 = (compras_ultimos_6 > 0).any()

    if frecuencia == 0 or promedio_mensual < 300_000:
        return "potencial"

    # Ajuste en la lógica inactivo para asegurar que haya tenido compras alguna vez
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
        # La clave de ordenamiento mejorada maneja mejor formatos como '2023_MES_1', '2024_MES_15'
        columnas_meses = sorted(
            [col for col in ventas.columns if "MES_" in col and len(col.split('_')) >= 3 and col.split('_')[-1].isdigit()],
            key=lambda x: (int(x.split("_")[0]) if x.split("_")[0].isdigit() else 0, int(x.split("_")[-1]) if x.split("_")[-1].isdigit() else 0)
        )

        # Asegurarse de que las columnas de meses existan antes de usarlas
        if not columnas_meses:
            st.error("No se encontraron columnas de meses válidas en el archivo. Asegúrate de que tengan el formato 'AÑO_MES_NUMERO' (Ej: 2023_MES_1, 2024_MES_15).")
            st.stop() # Detiene la ejecución si no hay columnas de meses

        ventas[columnas_meses] = ventas[columnas_meses].fillna(0).astype(float)

        # Aplicar clasificación original
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
            # Asegurarse de que haya clientes antes de llenar el selectbox
            # Mostrar selectbox solo si no se ingresó código y hay nombres disponibles
            if not cliente_codigo and not ventas["NOM_LEGAL"].dropna().empty:
                cliente_nombre = st.sidebar.selectbox("Seleccioná un cliente", sorted(ventas["NOM_LEGAL"].dropna().unique()))
            else:
                cliente_nombre = None
                # st.sidebar.warning("No hay nombres de clientes disponibles o se buscó por código.") # Comentado para no saturar

            df_filtrado = pd.DataFrame() # Inicializar vacío
            if cliente_codigo:
                df_filtrado = ventas[ventas["CODIGO"].astype(str).str.strip() == cliente_codigo.strip()].copy()
            elif cliente_nombre:
                df_filtrado = ventas[ventas["NOM_LEGAL"] == cliente_nombre].copy()
            # Si no se ingresa código ni se selecciona nombre, df_filtrado permanece vacío


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

                    # --- CALCULO DE PROMEDIO Y TOTAL ULTIMOS 12 MESES (INCLUYENDO CEROS) ---
                    meses_ultimos_12 = columnas_meses[-12:] if len(columnas_meses) >= 12 else columnas_meses
                    total_ultimos_12 = cliente[meses_ultimos_12].sum()
                    num_meses_evaluar_cliente = len(meses_ultimos_12)

                    # Calcular promedio incluyendo ceros
                    promedio_ultimos_12_con_ceros = total_ultimos_12 / num_meses_evaluar_cliente if num_meses_evaluar_cliente > 0 else 0
                    # --- FIN CALCULO PROMEDIO CON CEROS ---


                    st.markdown(f"- **Promedio Compra ({num_meses_evaluar_cliente} meses, incl. ceros):** ${promedio_ultimos_12_con_ceros:,.2f}")
                    st.markdown(f"- **Total Comprado ({num_meses_evaluar_cliente} meses):** ${total_ultimos_12:,.2f}")

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
                st.markdown("### 📊 Evolución de Compras")
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

            # --- FILTRO POR RUBRO ---
            st.sidebar.subheader("⚙️ Filtrar por Rubro")
            # Obtener la lista única de rubros del dataset cargado (excluyendo NaN)
            rubros_disponibles = sorted(ventas['RUBRO'].dropna().unique())
            # Añadir una opción para seleccionar todos por defecto o permitir vacio para no filtrar
            rubros_seleccionados = st.sidebar.multiselect("Selecciona Rubro(s)", rubros_disponibles, default=rubros_disponibles)

            # Aplicar filtro de rubro
            if rubros_seleccionados:
                 df_segmento_filtrado = ventas[ventas['RUBRO'].isin(rubros_seleccionados)].copy()
            else:
                 df_segmento_filtrado = ventas[ventas['RUBRO'].isin([])].copy() # Devuelve un DataFrame vacío si no hay rubros seleccionados
            # --- FIN FILTRO POR RUBRO ---


            # Asegurarse de que hay suficientes meses para la frecuencia y promedio de 12 meses *después de filtrar por rubro*
            if len(columnas_meses) < 12:
                 # Solo emitir la advertencia si el dataframe filtrado no está vacío
                 if not df_segmento_filtrado.empty:
                    st.warning(f"Solo se encontraron {len(columnas_meses)} meses de datos en el archivo. Los filtros de frecuencia y promedio se aplicarán sobre los meses disponibles.")
                 meses_para_filtros = columnas_meses
                 num_meses_filtros = len(columnas_meses)
            else:
                 meses_para_filtros = columnas_meses[-12:]
                 num_meses_filtros = 12


            # Asegurarse de que num_meses_filtros sea mayor que 0 para evitar división por cero
            if num_meses_filtros == 0:
                st.warning("No hay columnas de meses válidas para calcular la frecuencia o el promedio.")
                # Definir un DataFrame vacío con las columnas que deberían mostrarse
                columnas_segmento_base = [
                    "CODIGO", "NOM_LEGAL", "CLASE", "E_MAIL", "TELEFONO", "PROVINCIA",
                    f"Frecuencia (0m)", f"Promedio (0m incl. 0)"
                    ]
                df_segmento_final = pd.DataFrame(columns=columnas_segmento_base)

            else:

                segmento_frecuencia = st.sidebar.slider(f"Frecuencia de Compra ({num_meses_filtros} meses)", 0, num_meses_filtros, (0, num_meses_filtros))

                st.sidebar.subheader(f"💰 Filtrar por Promedio Mensual de Compra ({num_meses_filtros} meses, incl. ceros)")
                # Calcular el máximo promedio posible para el slider *sobre el dataframe filtrado por rubro*
                max_monto_global_filtrado = df_segmento_filtrado[meses_para_filtros].values.max() if not df_segmento_filtrado[meses_para_filtros].empty else 0
                max_promedio_posible = (max_monto_global_filtrado / num_meses_filtros) if num_meses_filtros > 0 and max_monto_global_filtrado > 0 else 1000000 # Evitar division por cero o valores muy bajos
                max_promedio_default = int(max_promedio_posible * 1.5) + 100000 # Un poco por encima del max real


                min_promedio = st.sidebar.number_input("Mínimo Promedio Mensual", min_value=0, step=100_000, value=0)
                max_promedio = st.sidebar.number_input("Máximo Promedio Mensual", min_value=0, step=100_000, value=max_promedio_default)


                # --- CALCULAR FRECUENCIA Y PROMEDIO PARA EL FILTRADO (SOBRE LOS MESES SELECCIONADOS Y RUBRO FILTRADO) ---
                # Asegurarse de que df_segmento_filtrado no esté vacío antes de calcular
                if not df_segmento_filtrado.empty:
                    df_segmento_filtrado['FRECUENCIA_FILTRO'] = df_segmento_filtrado[meses_para_filtros].apply(lambda row: (row > 0).sum(), axis=1)
                    total_comprado_filtro = df_segmento_filtrado[meses_para_filtros].sum(axis=1)
                    df_segmento_filtrado['PROMEDIO_FILTRO'] = total_comprado_filtro / num_meses_filtros
                else:
                     # Si el dataframe está vacío después del filtro de rubro, añadir las columnas calculadas vacías
                     df_segmento_filtrado['FRECUENCIA_FILTRO'] = pd.Series(dtype=float)
                     df_segmento_filtrado['PROMEDIO_FILTRO'] = pd.Series(dtype=float)

                # --- FIN CALCULOS PARA FILTRADO ---


                # --- APLICAR FILTROS ---
                df_segmento_final = df_segmento_filtrado[
                    (df_segmento_filtrado['FRECUENCIA_FILTRO'] >= segmento_frecuencia[0]) &
                    (df_segmento_filtrado['FRECUENCIA_FILTRO'] <= segmento_frecuencia[1]) &
                    (df_segmento_filtrado['PROMEDIO_FILTRO'] >= min_promedio) &
                    (df_segmento_filtrado['PROMEDIO_FILTRO'] <= max_promedio)
                ].copy()
                # --- FIN APLICAR FILTROS ---

            # --- MOSTRAR SEGMENTO FILTRADO ---
            st.subheader(f"📋 Segmento Filtrado ({len(df_segmento_final)} clientes)")
            # Columnas a mostrar en la tabla del segmento
            # Eliminamos 'CLASE_CLIENTE' como solicitaste
            columnas_a_mostrar = [
                "CODIGO",
                "NOM_LEGAL",
                "CLASE", # Mantener la CLASE original si es útil
                "E_MAIL",
                "TELEFONO",
                "PROVINCIA",
                 f"Frecuencia ({num_meses_filtros}m)", # Renombrar para claridad
                 f"Promedio ({num_meses_filtros}m incl. 0)", # Renombrar para claridad
            ]

            # Asegurarse de que las columnas calculadas existan antes de intentar renombrar
            # Esto también cubre el caso donde num_meses_filtros es 0 y df_segmento_final está vacío
            nombres_calculados = {
                'FRECUENCIA_FILTRO': f"Frecuencia ({num_meses_filtros}m)",
                'PROMEDIO_FILTRO': f"Promedio ({num_meses_filtros}m incl. 0)"
            }
            columnas_en_df_final = df_segmento_final.columns

            # Renombrar solo si las columnas originales existen
            cols_to_rename = {k: v for k, v in nombres_calculados.items() if k in columnas_en_df_final}
            if cols_to_rename:
                 df_segmento_final.rename(columns=cols_to_rename, inplace=True)


            # Asegurarse de que solo mostramos columnas que realmente existen en el dataframe final
            columnas_a_mostrar_existentes = [col for col in columnas_a_mostrar if col in df_segmento_final.columns]


            # Formatear el promedio para mostrar en la tabla
            # Asegurarse de que la columna de promedio exista antes de formatear
            nombre_col_promedio = f"Promedio ({num_meses_filtros}m incl. 0)"
            if nombre_col_promedio in columnas_a_mostrar_existentes:
                 styled_segment_df = df_segmento_final[columnas_a_mostrar_existentes].style \
                     .format({nombre_col_promedio: "${:,.0f}"})
            else:
                 # Si no hay datos o columna de promedio, mostrar el dataframe sin formato especial en esa columna
                 styled_segment_df = df_segmento_final[columnas_a_mostrar_existentes]


            st.dataframe(styled_segment_df, use_container_width=True)

            # Análisis del segmento (opcional)
            # Solo mostrar el gráfico si hay datos en el segmento final
            if not df_segmento_final.empty:
                st.markdown("### 📊 Análisis del Segmento")
                col_seg1 = st.columns(1)[0]
                with col_seg1:
                    # Podríamos graficar la distribución de la CLASE_CLIENTE original si es relevante para el segmento
                    st.markdown("#### Distribución de Clases de Clientes (Clasificación Original)")
                    # Asegurarse de que 'CLASE_CLIENTE' existe en el df final (debería existir si no está vacío)
                    if 'CLASE_CLIENTE' in df_segmento_final.columns:
                        clase_counts = df_segmento_final['CLASE_CLIENTE'].value_counts()
                        if not clase_counts.empty: # Asegurarse de que hay counts para graficar
                             fig_clase, ax_clase = plt.subplots()
                             ax_clase.pie(clase_counts, labels=clase_counts.index, autopct='%1.1f%%', startangle=90)
                             st.pyplot(fig_clase)
                        else:
                             st.info("No hay datos de clases de clientes en el segmento filtrado para mostrar el gráfico.")
                    else:
                         st.info("La columna 'CLASE_CLIENTE' no está disponible en el dataframe filtrado.")

else:
    st.info("⬆️ Por favor, sube un archivo Excel para comenzar el análisis.")
