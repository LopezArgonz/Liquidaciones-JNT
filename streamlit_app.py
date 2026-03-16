import streamlit as st
import pandas as pd
from datetime import datetime, date
import io
from app_liquidacion import LiquidadorLaboral, obtener_datos_online

# Configuración de la página
st.set_page_config(
    page_title="Liquidador Laboral - Tribunal",
    page_icon="logo.png",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos personalizados
st.markdown("""
    <style>
    .main {
        background-color: #f8f9fa;
    }
    h1 {
        color: #2c3e50;
    }
    .stButton>button {
        background-color: #2c3e50;
        color: white;
        border-radius: 8px;
        width: 100%;
        border: none;
        padding: 0.5rem 1rem;
        font-weight: 500;
        transition: all 0.3s ease;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .stButton>button:hover {
        background-color: #34495e;
        box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        transform: translateY(-1px);
    }
    .stButton>button:active {
        transform: translateY(0px);
    }
    .css-1d391kg {
        padding-top: 2rem;
    }
    </style>
    """, unsafe_allow_html=True)

def main():
    # Encabezado con alineación personalizada
    st.markdown("""
        <div style="display: inline-block; text-align: right;">
            <h1 style="margin: 0; padding: 0; font-size: 3rem;">⚖️ Sistema de Liquidación Laboral</h1>
            <h3 style="margin: 0; padding: 0; color: #555; font-weight: normal;">para la Justicia Nacional del Trabajo</h3>
        </div>
        """, unsafe_allow_html=True)
    st.markdown("---")

    # --- PANEL LATERAL ---
    with st.sidebar:
        st.header("📋 Datos del Expediente")
        
        # Botón para limpiar todo
        if st.button("Nueva Liquidación", type="primary", use_container_width=True):
            # Borramos absolutamente todo el estado
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
            
        caratula = st.text_input("Carátula / Expediente", value="", placeholder="Ej: García c/ Pérez s/ Despido", key="caratula")
        
        col1, col2 = st.columns(2)
        with col1:
            f_ingreso = st.date_input("Fecha Ingreso", value=date.today(), min_value=date(1950, 1, 1), max_value=date(2100, 12, 31), format="DD/MM/YYYY", key="f_ingreso")
        with col2:
            f_despido = st.date_input("Fecha Despido", value=date.today(), min_value=date(1950, 1, 1), max_value=date(2100, 12, 31), format="DD/MM/YYYY", key="f_despido")
            
        sueldo = st.number_input("Mejor Remuneración ($)", min_value=0.0, value=0.0, step=1000.0, format="%.2f", key="sueldo")
        
        st.subheader("Configuración")
        causa = st.selectbox("Causa de Extinción", ["Sin Causa", "Con causa / Renuncia", "Mutuo Acuerdo"], key="causa")
        
        fuente_ipc = st.radio("Fuente de Actualización", ["INDEC", "CABA", "TIM BCRA"], index=0, key="fuente_ipc")
        
        st.markdown("##### Multas Ley 25.323")
        art1 = st.checkbox("Art. 1 (Relación no registrada)", value=False, key="art1")
        art2 = st.checkbox("Art. 2 (Falta de pago)", value=False, key="art2")
        
        st.markdown("##### Fallo Vizzoti")
        aplicar_vizzoti = st.checkbox("Aplicar Tope / Fallo Vizzoti", value=False, key="aplicar_vizzoti")
        tope_cct = 0.0
        if aplicar_vizzoti:
             tope_cct = st.number_input("Monto Tope Convencional ($)", min_value=0.0, value=0.0, step=1000.0, format="%.2f", key="tope_cct")
        
        st.markdown("##### Rubros Adicionales")
        
        rubros_extras = []
        
        # 1. Salarios Adeudados
        with st.expander("Salarios Adeudados (Predeterminado)"):
            c_sal1, c_sal2 = st.columns(2)
            with c_sal1:
                 cant_meses_adeudados = st.number_input("Cantidad de Meses Adeudados", min_value=0, step=1, format="%d", key="cant_meses")
            with c_sal2:
                 usar_mrmnh = st.checkbox("Utilizar MRMNH", value=True, help="Usa la Mejor Remuneración ingresada arriba", key="usar_mrmnh")
                 if usar_mrmnh:
                     remu_calculo = sueldo
                     st.caption(f"Base: ${remu_calculo:,.2f}")
                 else:
                     remu_calculo = st.number_input("Remuneración Específica ($)", value=0.0, min_value=0.0, key="remu_calculo")
            
            if cant_meses_adeudados > 0:
                total_sal_adeudados = remu_calculo * cant_meses_adeudados
                rubros_extras.append((f"Salarios adeudados ({int(cant_meses_adeudados)} meses)", total_sal_adeudados))
                st.write(f"Subtotal: **${total_sal_adeudados:,.2f}**")

        # 2. Otros Rubros (Tabla)
        with st.expander("Otros Rubros Extras"):
            df_adicionales = pd.DataFrame(columns=["Concepto", "Monto"])
            edited_df = st.data_editor(df_adicionales, num_rows="dynamic", use_container_width=True, key="df_adicionales")
            # Convertir a lista de tuplas (Concepto, Monto) validando que haya datos
            for index, row in edited_df.iterrows():
                if row["Concepto"] and row["Monto"]:
                     rubros_extras.append((row["Concepto"], float(row["Monto"])))

        st.markdown("---")
        
        # Variables de índices/tasas
        ipc_inicio = 1.0
        ipc_fin = 1.0
        tasa_tim = 0.0
        serie_id_tim = "168.1_T_ACT_G_D_D_0_38" # Default inicial

        if fuente_ipc in ["INDEC", "CABA"]:
             # ... (Bloque IPC existente) ...
             if st.button("🔄 Actualizar Índices Online"):
                with st.spinner('Consultando API del gobierno...'):
                    try:
                        # Intentamos obtener valores online
                        val_ini = obtener_datos_online(fuente_ipc, fecha_inicio=f_despido.strftime("%d/%m/%Y"))
                        val_fin_data = obtener_datos_online(fuente_ipc)
                        
                        if val_ini and val_fin_data:
                            val_fin, fecha_fin = val_fin_data
                            st.session_state['ipc_inicio'] = val_ini
                            st.session_state['ipc_fin'] = val_fin
                            st.session_state['fecha_ipc_fin'] = fecha_fin
                            st.success(f"Índices actualizados ({fecha_fin})")
                        else:
                            st.error("No se pudieron obtener datos online.")
                    except Exception as e:
                        st.error(f"Error de conexión: {e}")
             
             # Inputs manuales o automáticos para IPC
             ipc_inicio = st.number_input("IPC Inicio (Fecha Despido)", 
                                         value=st.session_state.get('ipc_inicio', 100.0), 
                                         format="%.4f")
             ipc_fin = st.number_input(f"IPC Cierre ({st.session_state.get('fecha_ipc_fin', 'Actual')})", 
                                      value=st.session_state.get('ipc_fin', 500.0), 
                                      format="%.4f")
        
        else:
            # Opción TIM BCRA
            st.info("ℹ️ Para TIM BCRA, el sistema consulta la **Variable 1197** (Tasa de Intereses Moratorios) del Banco Central.")
            
            # Opción de Capitalización (Anatocismo) Art 770 CCyC
            capitalizar_intereses = st.checkbox("Capitalizar intereses en fecha específica (Art. 770 CCyC)", value=False)
            fecha_capitalizacion = None
            tasa_tim_2 = 0.0
            
            if capitalizar_intereses:
                fecha_capitalizacion = st.date_input("Fecha de Capitalización (Corte)", value=date.today(), min_value=f_despido, max_value=date.today(), format="DD/MM/YYYY")
            
            if st.button("🔄 Consultar BCRA Online"):
                 with st.spinner('Conectando a api.bcra.gob.ar (Var. 1197)...'):
                    try:
                         f_ini_str = f_despido.strftime("%d/%m/%Y")
                         f_fin_str = datetime.now().strftime("%d/%m/%Y")
                         
                         if capitalizar_intereses and fecha_capitalizacion:
                             # Dos períodos
                             f_cap_str = fecha_capitalizacion.strftime("%d/%m/%Y")
                             
                             val_tasa_1 = obtener_datos_online("TIM BCRA", fecha_inicio=f_ini_str, fecha_fin=f_cap_str)
                             val_tasa_2 = obtener_datos_online("TIM BCRA", fecha_inicio=f_cap_str, fecha_fin=f_fin_str)
                             
                             if val_tasa_1 is not None and val_tasa_2 is not None:
                                 st.session_state['tasa_tim'] = val_tasa_1
                                 st.session_state['tasa_tim_2'] = val_tasa_2
                                 st.success(f"Tasas obtenidas: P1 ({f_ini_str}-{f_cap_str}): {val_tasa_1}% | P2 ({f_cap_str}-{f_fin_str}): {val_tasa_2}%")
                             else:
                                 st.error("Error al obtener tasas para los períodos indicados.")
                         else:
                             # Un solo período
                             val_tasa = obtener_datos_online("TIM BCRA", fecha_inicio=f_ini_str, fecha_fin=f_fin_str)
                             
                             if val_tasa is not None:
                                 st.session_state['tasa_tim'] = val_tasa
                                 st.session_state['tasa_tim_2'] = 0.0
                                 st.success(f"Tasa BCRA acumulada: {val_tasa}% ({f_ini_str} - {f_fin_str})")
                             else:
                                 st.error("No se pudieron obtener datos del BCRA.")
                    except Exception as e:
                        st.error(f"Error: {e}")

            if capitalizar_intereses:
                 c_t1, c_t2 = st.columns(2)
                 tasa_tim = c_t1.number_input("Tasa Interés P1 (Al Corte) %", value=st.session_state.get('tasa_tim', 50.0), step=1.0, format="%.2f")
                 tasa_tim_2 = c_t2.number_input("Tasa Interés P2 (Desde Corte) %", value=st.session_state.get('tasa_tim_2', 50.0), step=1.0, format="%.2f")
            else:
                 tasa_tim = st.number_input("Tasa Interés Acumulada (%)", value=st.session_state.get('tasa_tim', 100.0), step=1.0, format="%.2f")

    # --- LÓGICA DE CÁLCULO ---
    if sueldo > 0:
        try:
            # Crear instancia del liquidador
            liquidador = LiquidadorLaboral(
                caratula=caratula,
                ingreso=f_ingreso.strftime("%d/%m/%Y"),
                despido=f_despido.strftime("%d/%m/%Y"),
                sueldo=sueldo,
                causa=causa,
                art1=art1,
                art2=art2,
                ipc_inicio=ipc_inicio,
                ipc_fin=ipc_fin,
                fuente_ipc=fuente_ipc,
                tasa_tim=tasa_tim,
                fecha_capitalizacion=fecha_capitalizacion.strftime("%d/%m/%Y") if (fuente_ipc == "TIM BCRA" and capitalizar_intereses and fecha_capitalizacion) else None,
                tasa_tim_2=tasa_tim_2 if (fuente_ipc == "TIM BCRA" and capitalizar_intereses) else 0.0,
                aplicar_vizzoti=aplicar_vizzoti,
                tope_cct=tope_cct if aplicar_vizzoti else None,
                rubros_adicionales=rubros_extras
            )
            
            # --- VISUALIZACIÓN DE RESULTADOS ---
            col_res1, col_res2, col_res3 = st.columns(3)
            
            # Cálculos auxiliares para mostrar en pantalla
            anios = liquidador.antiguedad.years
            meses = liquidador.antiguedad.months
            periodos = liquidador.calcular_periodos_245()
            base_indem = liquidador.calcular_base_245()
            
            rubros = []

            # Rubro: Días trabajados (mes despido) - SE CALCULA SIEMPRE
            monto_dias_trab = liquidador.calcular_dias_trabajados_mes_despido()
            rubros.append((f"Días trabajados mes despido ({f_despido.day} días)", monto_dias_trab))

            if causa == "Sin Causa":
                label_245 = "Indemnización por antigüedad (art. 245 LCT cfr. tope \"Vizzoti\" CSJN)" if aplicar_vizzoti else "Indemnización por antigüedad (art. 245 LCT)"
                rubros.append((label_245, base_indem * periodos))
                rubros.append(("Indemnización sustitutiva del preaviso (art. 232 LCT)", (liquidador.sueldo * (2 if anios >= 5 else 1))))
                rubros.append(("SAC sobre preaviso", (liquidador.sueldo * (2 if anios >= 5 else 1)) / 12))
                rubros.append(("Integración del mes de despido (art. 233 LCT)", liquidador.calcular_integracion_mes()))
                rubros.append(("SAC sobre integración", liquidador.calcular_integracion_mes() / 12))
            
            rubros.append(("SAC Prop.", liquidador.calcular_sac_prop()))
            rubros.append(("Vacaciones Prop.", liquidador.calcular_vacaciones_prop()))

            # Multas para visualización
            monto_multas = 0
            if art1: 
                monto_art1 = base_indem * periodos
                rubros.append(("Art. 1º Ley 25.323", monto_art1))
                monto_multas += monto_art1
            
            total_historico = sum(m for r, m in rubros)
            
            if art2: 
                # Simplificación visual, usamos el total acumulado parecido a la logica del excel
                monto_art2 = total_historico * 0.5  
                rubros.append(("Art. 2º Ley 25.323", monto_art2))
                total_historico += monto_art2

            # Sumar rubros adicionales al display
            if rubros_extras:
                for c, m in rubros_extras:
                    rubros.append((c, m))
                    total_historico += m

            # Cálculo de actualización para visualización
            if fuente_ipc == "TIM BCRA":
                coef = 0 # No aplica
                if capitalizar_intereses and fecha_capitalizacion:
                    int_p1 = total_historico * (tasa_tim / 100)
                    cap_cap = total_historico + int_p1
                    int_p2 = cap_cap * (tasa_tim_2 / 100)
                    capital_act = cap_cap + int_p2
                    texto_coef = f"Tasas: {tasa_tim}% + {tasa_tim_2}%"
                    texto_cap = f"Total Final (Capitalizado):"
                else:
                    monto_interes = total_historico * (tasa_tim / 100)
                    capital_act = total_historico + monto_interes
                    texto_coef = f"Tasa: {tasa_tim}%"
                    texto_cap = f"Total Final (c/ Int.):"
            else:
                coef = ipc_fin / ipc_inicio
                capital_act = total_historico * coef
                texto_coef = f"Coef. IPC:"
                texto_cap = f"Capital Actualizado:"
            
            with col_res1:
                st.info(f"**Antigüedad:** {anios} años, {meses} meses")
            with col_res2:
                if fuente_ipc == "TIM BCRA":
                     st.warning(f"**{texto_coef}**")
                else:
                     st.warning(f"**{texto_coef}** {coef:.4f}")
            with col_res3:
                st.success(f"**{texto_cap}** ${capital_act:,.2f}")

            if aplicar_vizzoti:
                if base_indem == sueldo * 0.67:
                    st.caption(f"ℹ️ Se aplica **Piso Vizzoti**: Base ${base_indem:,.2f} (67% de Remuneración)")
                elif base_indem == tope_cct:
                     st.caption(f"ℹ️ Se aplica **Tope CCT**: Base ${base_indem:,.2f}")
                else:
                     st.caption(f"ℹ️ Base s/ Tope: ${base_indem:,.2f} (Sueldo o Tope superior al 67%)")

            st.subheader("Resumen de Rubros (Estimado)")
            # Usamos HTML generado por Pandas para asegurar que no se muestre el índice y tener control total
            c_tabla, c_vacio = st.columns([0.65, 0.35]) 
            with c_tabla:
                # Crear DataFrame y agregar fila de Total
                df_resumen = pd.DataFrame(rubros, columns=["Rubro", "Monto"])
                # Agregar fila de total
                df_total = pd.DataFrame([["TOTAL HISTÓRICO", total_historico]], columns=["Rubro", "Monto"])
                df_final = pd.concat([df_resumen, df_total], ignore_index=True)

                # Formatear Monto a string y generar HTML sin índice
                df_final["Monto"] = df_final["Monto"].apply(lambda x: f"${x:,.2f}")
                
                # HTML base
                html = df_final.to_html(index=False, classes='table-style', border=0, justify='center')
                
                # CSS Personalizado para que se vea bien en ambos modos
                st.markdown("""
                <style>
                .table-style {
                    width: 100% !important;
                    border-collapse: collapse !important;
                    font-family: sans-serif;
                    font-size: 0.9rem;
                    color: inherit !important;
                }
                .table-style thead tr th {
                    text-align: center !important;
                    background-color: rgba(128, 128, 128, 0.15);
                    padding: 10px;
                    border-bottom: 2px solid rgba(128, 128, 128, 0.3);
                    color: inherit !important;
                }
                .table-style tbody tr td {
                    padding: 10px;
                    border-bottom: 1px solid rgba(128, 128, 128, 0.1);
                    color: inherit !important;
                }
                /* Alinear segunda columna (Monto) a la derecha */
                .table-style tbody tr td:nth-child(2) {
                    text-align: right !important;
                    white-space: nowrap;
                }
                /* Estilo para la fila de Total */
                .table-style tbody tr:last-child {
                    font-weight: bold;
                    background-color: rgba(128, 128, 128, 0.1);
                    border-top: 2px solid rgba(128, 128, 128, 0.3);
                }
                </style>
                """, unsafe_allow_html=True)
                
                st.markdown(html, unsafe_allow_html=True)

            # --- BOTÓN DE DESCARGA ---
            st.markdown("### 📥 Exportar Liquidación")
            
            # Generar el Excel en memoria
            excel_buffer = io.BytesIO()
            liquidador.generar_excel(buffer=excel_buffer)
            excel_data = excel_buffer.getvalue()
            
            filename = f"Liquidacion_{caratula.replace(' ', '_')}.xlsx"
            
            st.download_button(
                label="📄 Descargar Excel Completo",
                data=excel_data,
                file_name=filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            
        except Exception as e:
            st.error(f"Error en el cálculo: {e}")
            st.write("Verifique las fechas ingresadas.")
    else:
        st.info("Ingrese un sueldo mayor a 0 para comenzar.")

if __name__ == "__main__":
    main()
