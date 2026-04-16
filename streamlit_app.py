import streamlit as st
import pandas as pd
from datetime import datetime, date
import io
from app_liquidacion import LiquidadorLaboral, obtener_datos_online

# Configuración de la página
st.set_page_config(
    page_title="Liquidaciones JNT",
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
        
        col1, col2, col3 = st.columns(3)
        with col1:
            f_ingreso = st.date_input("Fecha Ingreso", value=date.today(), min_value=date(1950, 1, 1), max_value=date(2100, 12, 31), format="DD/MM/YYYY", key="f_ingreso")
        with col2:
            f_despido = st.date_input("Fecha Despido", value=date.today(), min_value=date(1950, 1, 1), max_value=date(2100, 12, 31), format="DD/MM/YYYY", key="f_despido")
        with col3:
            f_liquidacion = st.date_input("Fecha Liquidación", value=date.today(), min_value=date(1950, 1, 1), max_value=date(2100, 12, 31), format="DD/MM/YYYY", key="f_liquidacion")
            
        sueldo = st.number_input("Mejor Remuneración ($)", min_value=0.0, value=0.0, step=1000.0, format="%.2f", key="sueldo")
        
        st.subheader("Configuración")
        causa = st.selectbox("Causa de Extinción", ["Sin Causa", "Con causa / Renuncia", "Mutuo Acuerdo"], key="causa")
        
        st.markdown("##### Multas LCT y Ley 25.323")
        art1 = st.checkbox("Art. 1 Ley 25.323 (Relación no registrada)", value=False, key="art1")
        art2 = st.checkbox("Art. 2 Ley 25.323 (Falta de pago)", value=False, key="art2")
        art80 = st.checkbox("Art. 80 LCT (Certificados)", value=False, key="art80")
        dto34 = st.checkbox("Dto. 34/2019 (Doble Indemnización)", value=False, key="dto34")
        
        # Opción SAC adeudado (Solo Julio o Enero)
        incluir_sac_ant = False
        if f_despido.month in (1, 7):
            label_sac = "¿Incluir SAC 1er Semestre adeudado?" if f_despido.month == 7 else "¿Incluir SAC 2do Semestre (año ant.) adeudado?"
            incluir_sac_ant = st.checkbox(label_sac, value=True, key="incluir_sac_ant", help="Marcar si al momento del despido aún no se había percibido el SAC del semestre anterior.")
        
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
        
        # Variables de índices
        ipc_inicio = 1.0
        ipc_fin = 1.0

        if st.button("🔄 Actualizar Índices Online"):
            with st.spinner('Consultando API del INDEC (Datos Argentina)...'):
                try:
                    # Intentamos obtener valores online con las fechas exactas
                    val_ini_data = obtener_datos_online(fecha_objetivo=f_despido.strftime("%d/%m/%Y"))
                    val_fin_data = obtener_datos_online(fecha_objetivo=f_liquidacion.strftime("%d/%m/%Y"))
                    
                    if val_ini_data and val_fin_data and val_ini_data[0] and val_fin_data[0]:
                        val_ini, fecha_ini_real = val_ini_data
                        val_fin, fecha_fin_real = val_fin_data
                        st.session_state['ipc_inicio'] = val_ini
                        st.session_state['ipc_fin'] = val_fin
                        st.session_state['fecha_ipc_ini'] = fecha_ini_real
                        st.session_state['fecha_ipc_fin'] = fecha_fin_real
                        st.success(f"Índices obtenidos! Inicio ({fecha_ini_real}) | Cierre ({fecha_fin_real})")
                    else:
                        st.error("No se pudieron obtener datos online para esas fechas.")
                except Exception as e:
                    st.error(f"Error de conexión: {e}")
            
        # Inputs manuales o automáticos para IPC
        ipc_inicio = st.number_input(f"IPC Inicio ({st.session_state.get('fecha_ipc_ini', 'Despido')})", 
                                    value=st.session_state.get('ipc_inicio', 100.0), 
                                    format="%.4f")
        ipc_fin = st.number_input(f"IPC Cierre ({st.session_state.get('fecha_ipc_fin', 'Liquidación')})", 
                                value=st.session_state.get('ipc_fin', 500.0), 
                                format="%.4f")

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
                aplicar_vizzoti=aplicar_vizzoti,
                tope_cct=tope_cct if aplicar_vizzoti else None,
                rubros_adicionales=rubros_extras,
                fecha_liquidacion=f_liquidacion.strftime("%d/%m/%Y"),
                incluir_sac_anterior=incluir_sac_ant,
                art80=art80,
                dto34=dto34
            )
            
            # --- VISUALIZACIÓN DE RESULTADOS ---
            col_res1, col_res2, col_res3 = st.columns(3)
            
            # Cálculos auxiliares para mostrar en pantalla
            anios = liquidador.antiguedad.years
            meses = liquidador.antiguedad.months
            periodos = liquidador.calcular_periodos_245()
            base_indem = liquidador.calcular_base_245()
            
            # --- REORDENAMIENTO DE RUBROS SEGÚN SOLICITUD ---
            rubros = []

            # 1. Indemnización por antigüedad (art. 245 LCT)
            monto_245 = base_indem * periodos
            if causa == "Sin Causa":
                label_245 = "Indemnización por antigüedad (art. 245 LCT cfr. tope \"Vizzoti\" CSJN)" if aplicar_vizzoti else "Indemnización por antigüedad (art. 245 LCT)"
                rubros.append((label_245, monto_245))

                # 2. Indemnización sustitutiva del preaviso (art. 232 LCT)
                monto_preaviso = liquidador.sueldo * (2 if anios >= 5 else 1)
                rubros.append(("Indemnización sustitutiva del preaviso (art. 232 LCT)", monto_preaviso))

                # 3. SAC sobre preaviso
                rubros.append(("SAC sobre preaviso", monto_preaviso / 12))

                # 4. Integración del mes de despido (art. 233 LCT)
                monto_integracion = liquidador.calcular_integracion_mes()
                if monto_integracion > 0:
                    rubros.append(("Integración del mes de despido (art. 233 LCT)", monto_integracion))
                    # 5. SAC sobre integración
                    rubros.append(("SAC sobre integración", monto_integracion / 12))
                
                # Dto. 34/2019
                if dto34:
                    monto_dto34 = monto_245 + monto_preaviso + (monto_preaviso / 12) + monto_integracion + (monto_integracion / 12 if monto_integracion > 0 else 0)
                    rubros.append(("Incremento Indemnizatorio Dto. 34/2019", monto_dto34))
            else:
                 monto_preaviso = 0
                 monto_integracion = 0
            
            # 6. Días trabajados mes despido
            monto_dias_trab = liquidador.calcular_dias_trabajados_mes_despido()
            rubros.append((f"Días trabajados mes despido ({f_despido.day} días)", monto_dias_trab))

            # SAC Semestre Anterior (si corresponde)
            sac_ant = liquidador.calcular_sac_semestre_anterior()
            if sac_ant > 0:
                rubros.append(("SAC Semestre Anterior Adeudado", sac_ant))

            # 7. SAC Prop.
            rubros.append(("SAC Prop.", liquidador.calcular_sac_prop()))

            # 8. Vacaciones Prop.
            vacaciones_prop, vac_dias_ui = liquidador.calcular_vacaciones_prop()
            rubros.append((f"Vacaciones Prop. ({vac_dias_ui:.2f} días)", vacaciones_prop))

            # 9. SAC s/ vacaciones
            rubros.append(("SAC s/ vacaciones", vacaciones_prop / 12))

            # 10. Salarios adeudados (Rubros adicionales predeterminados)
            # Buscamos en rubros_extras si hay salarios adeudados
            otros_extras_visual = []
            if rubros_extras:
                for c, m in rubros_extras:
                    if "Salarios adeudados" in c:
                        rubros.append((c, m))
                    else:
                        otros_extras_visual.append((c, m))

            # 11. Art. 1º Ley 25.323
            if art1: 
                rubros.append(("Art. 1º Ley 25.323", monto_245))
            
            # 12. Art. 2º Ley 25.323
            if art2: 
                monto_art2 = (monto_245 + monto_preaviso + monto_integracion) * 0.5
                rubros.append(("Art. 2º Ley 25.323", monto_art2))

            # 13. Art. 80 LCT
            if art80:
                rubros.append(("Multa Art. 80 LCT", sueldo * 3))

            # Resto de rubros adicionales
            for c, m in otros_extras_visual:
                rubros.append((c, m))

            total_historico = sum(m for r, m in rubros)

            # Sumar rubros adicionales al display
            if rubros_extras:
                for c, m in rubros_extras:
                    rubros.append((c, m))
                    total_historico += m

            # Cálculo de actualización para visualización
            coef = ipc_fin / ipc_inicio
            capital_act = total_historico * coef
            
            # Cálculo exacto de días transcurridos
            dias_pasados = max(0, (f_liquidacion - f_despido).days)
            porcentaje_acumulado = dias_pasados * (0.03 / 365)
            int_puro = capital_act * porcentaje_acumulado
            
            texto_coef = f"Coef. IPC:"
            texto_cap = f"Total (+3% an. - {dias_pasados} d. - {porcentaje_acumulado*100:.2f}% ac.):"
            
            with col_res1:
                st.info(f"**Antigüedad:** {anios} años, {meses} meses")
            with col_res2:
                st.warning(f"**{texto_coef}** {coef:.4f}")
            with col_res3:
                st.success(f"**{texto_cap}** ${(capital_act + int_puro):,.2f}")

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
