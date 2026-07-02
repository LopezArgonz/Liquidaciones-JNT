import streamlit as st
import pandas as pd
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
import io
from app_liquidacion import LiquidadorLaboral, obtener_datos_online
from utils import aplicar_estilos, aplicar_estilos_tabla, mostrar_footer

st.set_page_config(
    page_title="Liquidaciones JNT",
    page_icon="logo.png",
    layout="wide",
    initial_sidebar_state="expanded"
)

aplicar_estilos()


def main():
    st.markdown("""
        <div style="display: inline-block; text-align: right;">
            <h1 style="margin: 0; padding: 0; font-size: 3rem;">⚖️ Sistema de Liquidación Laboral</h1>
            <h3 style="margin: 0; padding: 0; color: #555; font-weight: normal;">para la Justicia Nacional del Trabajo</h3>
        </div>
        """, unsafe_allow_html=True)
    st.markdown("---")

    # ── PANEL LATERAL ─────────────────────────────────────────────────────────
    with st.sidebar:
        st.header("📋 Datos del Expediente")

        if st.button("Nueva Liquidación", type="primary", use_container_width=True):
            for key in list(st.session_state.keys()):
                if not key.startswith("authentication") and key != "name" and key != "username":
                    del st.session_state[key]
            st.rerun()

        caratula = st.text_input("Carátula / Expediente", value="",
                                 placeholder="Ej: García c/ Pérez s/ Despido", key="caratula")

        # Fechas: 2 columnas (ingreso/despido) + liquidación sola
        col1, col2 = st.columns(2)
        with col1:
            f_ingreso = st.date_input("Fecha Ingreso", value=date.today(),
                                      min_value=date(1950, 1, 1), max_value=date(2100, 12, 31),
                                      format="DD/MM/YYYY", key="f_ingreso")
        with col2:
            f_despido = st.date_input("Fecha Despido", value=date.today(),
                                      min_value=date(1950, 1, 1), max_value=date(2100, 12, 31),
                                      format="DD/MM/YYYY", key="f_despido")
        f_liquidacion = st.date_input("Fecha Liquidación", value=date.today(),
                                      min_value=date(1950, 1, 1), max_value=date(2100, 12, 31),
                                      format="DD/MM/YYYY", key="f_liquidacion")

        sueldo = st.number_input("Mejor Remuneración ($)", min_value=0.0, value=0.0,
                                 step=1000.0, format="%.2f", key="sueldo")

        st.markdown("---")
        st.subheader("Causa de Extinción")
        causa = st.selectbox("Causa", ["Sin Causa", "Con causa / Renuncia", "Mutuo Acuerdo"], key="causa",
                             label_visibility="collapsed")

        st.markdown("---")
        st.markdown("##### Multas y Leyes especiales")

        art1 = st.checkbox("Art. 1° Ley 25.323", value=False, key="art1",
                           help="Relación no registrada: duplica la indemnización por antigüedad.")
        art2 = st.checkbox("Art. 2° Ley 25.323", value=False, key="art2",
                           help="Falta de pago a tiempo: 50% sobre art. 245 + preaviso + integración.")
        art8_24013 = st.checkbox("Art. 8° Ley 24.013", value=False, key="art8_24013",
                                 help="Relación no registrada: 25% del total de remuneraciones por el período no registrado.")

        art9_24013 = st.checkbox("Art. 9° Ley 24.013", value=False, key="art9",
                                 help="Registro tardío: 25% de las remuneraciones devengadas desde el ingreso hasta el registro.")
        fecha_registro = None
        if art9_24013:
            fecha_registro = st.date_input("Fecha de Registro", value=f_ingreso,
                                           min_value=f_ingreso, max_value=f_despido,
                                           format="DD/MM/YYYY")

        art10_24013 = st.checkbox("Art. 10 Ley 24.013", value=False, key="art10",
                                  help="Remuneración no registrada: 25% de la diferencia salarial no registrada.")
        remuneracion_no_registrada = 0.0
        fecha_inicio_art10 = None
        fecha_fin_art10 = None
        if art10_24013:
            remuneracion_no_registrada = st.number_input("Remuneración no registrada ($)",
                                                         min_value=0.0, value=0.0, step=1000.0, format="%.2f")
            limitar_corte = st.checkbox("Período Específico (Modificar fechas)", value=False)
            if limitar_corte:
                col_i, col_f = st.columns(2)
                with col_i:
                    fecha_inicio_art10 = st.date_input("Inicio del Período", value=f_ingreso,
                                                       format="DD/MM/YYYY")
                with col_f:
                    fecha_fin_art10 = st.date_input("Fin del Período", value=f_despido,
                                                    format="DD/MM/YYYY")

        art15_24013 = st.checkbox("Art. 15 Ley 24.013", value=False, key="art15_24013",
                                  help="Despido tras intimación de registro: duplica la indemnización.")
        art80 = st.checkbox("Art. 80 LCT", value=False, key="art80",
                            help="Falta de entrega de certificados de trabajo: 3 sueldos.")
        dto34 = st.checkbox("Dto. 34/2019 (Doble Indemnización)", value=False, key="dto34",
                            help="Incremento indemnizatorio del 100% sobre los rubros indemnizatorios.")

        # SAC semestre anterior
        incluir_sac_ant = False
        if f_despido.month in (1, 7):
            label_sac = ("¿Incluir SAC 1er Semestre adeudado?"
                         if f_despido.month == 7
                         else "¿Incluir SAC 2do Semestre (año ant.) adeudado?")
            incluir_sac_ant = st.checkbox(label_sac, value=True, key="incluir_sac_ant",
                                          help="Marcar si al momento del despido aún no se había percibido el SAC del semestre anterior.")

        st.markdown("---")
        st.markdown("##### Fallo Vizzoti")
        aplicar_vizzoti = st.checkbox("Aplicar Tope / Fallo Vizzoti", value=False, key="aplicar_vizzoti")
        tope_cct = 0.0
        if aplicar_vizzoti:
            tope_cct = st.number_input("Monto Tope Convencional ($)", min_value=0.0,
                                       value=0.0, step=1000.0, format="%.2f", key="tope_cct")

        st.markdown("---")
        st.markdown("##### Rubros Adicionales")

        rubros_extras = []

        with st.expander("Salarios Adeudados"):
            c_sal1, c_sal2 = st.columns(2)
            with c_sal1:
                cant_meses_adeudados = st.number_input("Meses Adeudados", min_value=0,
                                                       step=1, format="%d", key="cant_meses")
            with c_sal2:
                usar_mrmnh = st.checkbox("Usar Mejor Remuneración", value=True, key="usar_mrmnh")
                if usar_mrmnh:
                    remu_calculo = sueldo
                    st.caption(f"Base: ${remu_calculo:,.2f}")
                else:
                    remu_calculo = st.number_input("Remuneración Específica ($)", value=0.0,
                                                   min_value=0.0, key="remu_calculo")
            if cant_meses_adeudados > 0:
                total_sal_adeudados = remu_calculo * cant_meses_adeudados
                rubros_extras.append((f"Salarios adeudados ({int(cant_meses_adeudados)} meses)",
                                      total_sal_adeudados))
                st.write(f"Subtotal: **${total_sal_adeudados:,.2f}**")

        with st.expander("Otros Rubros"):
            df_adicionales = pd.DataFrame(columns=["Concepto", "Monto"])
            edited_df = st.data_editor(df_adicionales, num_rows="dynamic",
                                       use_container_width=True, key="df_adicionales")
            for _, row in edited_df.iterrows():
                if row["Concepto"] and row["Monto"]:
                    rubros_extras.append((row["Concepto"], float(row["Monto"])))

        st.markdown("---")
        st.markdown("##### Pagos a Cuenta")
        aplicar_pagos_cuenta = st.checkbox("Habilitar Pagos a Cuenta", value=False,
                                           key="aplicar_pagos_cuenta")
        monto_pagos_cuenta = 0.0
        if aplicar_pagos_cuenta:
            monto_pagos_cuenta = st.number_input("Monto pagado a cuenta ($)", min_value=0.0,
                                                 value=0.0, step=1000.0, format="%.2f",
                                                 key="monto_pagos_cuenta")

        st.markdown("---")
        st.markdown("##### Índices IPC INDEC")

        ipc_actualizado = st.session_state.get("ipc_actualizado", False)
        if ipc_actualizado:
            st.success("✅ Índices actualizados")
        else:
            st.warning("⚠️ Índices no actualizados — presione el botón antes de calcular.")

        if st.button("🔄 Actualizar Índices Online"):
            with st.spinner("Consultando API del INDEC..."):
                try:
                    val_ini_data = obtener_datos_online(
                        fecha_objetivo=f_despido.strftime("%d/%m/%Y"))
                    val_fin_data = obtener_datos_online(
                        fecha_objetivo=f_liquidacion.strftime("%d/%m/%Y"))
                    if val_ini_data and val_fin_data and val_ini_data[0] and val_fin_data[0]:
                        val_ini, fecha_ini_real = val_ini_data
                        val_fin, fecha_fin_real = val_fin_data
                        st.session_state["ipc_inicio"] = val_ini
                        st.session_state["ipc_fin"] = val_fin
                        st.session_state["fecha_ipc_ini"] = fecha_ini_real
                        st.session_state["fecha_ipc_fin"] = fecha_fin_real
                        st.session_state["ipc_actualizado"] = True
                        st.success(f"IPC obtenido: {fecha_ini_real} → {fecha_fin_real}")
                        st.rerun()
                    else:
                        st.error("No se pudieron obtener datos para esas fechas.")
                except Exception as e:
                    st.error(f"Error de conexión: {e}")

        fecha_ipc_ini_label = st.session_state.get("fecha_ipc_ini", "Mes Despido")
        fecha_ipc_fin_label = st.session_state.get("fecha_ipc_fin", "Liquidación")

        ipc_inicio = st.number_input(f"IPC Inicio ({fecha_ipc_ini_label})",
                                     value=st.session_state.get("ipc_inicio", None),
                                     format="%.4f", key="ipc_inicio_input")
        ipc_fin = st.number_input(f"IPC Cierre ({fecha_ipc_fin_label})",
                                  value=st.session_state.get("ipc_fin", None),
                                  format="%.4f", key="ipc_fin_input")

        st.markdown("---")
        mostrar_footer()

    # ── VALIDACIONES ──────────────────────────────────────────────────────────
    if sueldo <= 0:
        st.info("Ingrese un sueldo mayor a 0 para comenzar.")
        return

    if f_ingreso > f_despido:
        st.error("La fecha de ingreso no puede ser posterior a la fecha de despido.")
        return

    if f_despido > f_liquidacion:
        st.error("La fecha de despido no puede ser posterior a la fecha de liquidación.")
        return

    if art10_24013 and fecha_inicio_art10 and fecha_fin_art10:
        if fecha_inicio_art10 > fecha_fin_art10:
            st.error("La fecha de inicio del período (Art. 10) no puede ser posterior a la fecha de fin.")
            return

    if ipc_inicio is None or ipc_fin is None or ipc_inicio <= 0 or ipc_fin <= 0:
        st.warning("⚠️ Actualice los índices IPC antes de calcular (botón en el panel lateral).")
        return

    # ── LÓGICA DE CÁLCULO ─────────────────────────────────────────────────────
    try:
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
            dto34=dto34,
            art8_24013=art8_24013,
            art15_24013=art15_24013,
            pagos_a_cuenta=monto_pagos_cuenta,
            art9_24013=art9_24013,
            fecha_registro=fecha_registro.strftime("%d/%m/%Y") if fecha_registro else None,
            art10_24013=art10_24013,
            remuneracion_no_registrada=remuneracion_no_registrada,
            fecha_inicio_art10=fecha_inicio_art10.strftime("%d/%m/%Y") if fecha_inicio_art10 else None,
            fecha_fin_art10=fecha_fin_art10.strftime("%d/%m/%Y") if fecha_fin_art10 else None,
        )

        anios = liquidador.antiguedad.years
        meses = liquidador.antiguedad.months
        periodos = liquidador.calcular_periodos_245()
        base_indem = liquidador.calcular_base_245()

        # ── CONSTRUCCIÓN DE RUBROS ─────────────────────────────────────────
        rubros = []
        monto_245 = 0.0
        monto_preaviso = 0.0
        monto_integracion = 0.0

        if causa == "Sin Causa":
            monto_245 = base_indem * periodos
            label_245 = ("Indemnización por antigüedad (art. 245 LCT cfr. tope \"Vizzoti\" CSJN)"
                         if aplicar_vizzoti
                         else "Indemnización por antigüedad (art. 245 LCT)")
            rubros.append((label_245, monto_245))

            meses_preaviso = 2 if anios >= 5 else 1
            monto_preaviso = sueldo * meses_preaviso
            rubros.append((f"Indemnización sustitutiva del preaviso (art. 232 LCT) ({meses_preaviso} mes/es)",
                           monto_preaviso))
            rubros.append(("SAC sobre preaviso", monto_preaviso / 12))

            monto_integracion = liquidador.calcular_integracion_mes()
            if monto_integracion > 0:
                rubros.append(("Integración del mes de despido (art. 233 LCT)", monto_integracion))
                rubros.append(("SAC sobre integración", monto_integracion / 12))

            if dto34:
                monto_dto34 = (monto_245 + monto_preaviso + (monto_preaviso / 12)
                               + monto_integracion + (monto_integracion / 12 if monto_integracion > 0 else 0))
                rubros.append(("Incremento Indemnizatorio Dto. 34/2019", monto_dto34))

        monto_dias_trab = liquidador.calcular_dias_trabajados_mes_despido()
        rubros.append((f"Días trabajados mes despido ({f_despido.day} días)", monto_dias_trab))

        sac_ant = liquidador.calcular_sac_semestre_anterior()
        if sac_ant > 0:
            rubros.append(("SAC Semestre Anterior Adeudado", sac_ant))

        rubros.append(("SAC Proporcional", liquidador.calcular_sac_prop()))

        vacaciones_prop, vac_dias_ui = liquidador.calcular_vacaciones_prop()
        rubros.append((f"Vacaciones Proporcionales ({vac_dias_ui:.2f} días)", vacaciones_prop))
        rubros.append(("SAC s/ vacaciones", vacaciones_prop / 12))

        # Salarios adeudados primero
        otros_extras_visual = []
        for c, m in rubros_extras:
            if "Salarios adeudados" in c:
                rubros.append((c, m))
            else:
                otros_extras_visual.append((c, m))

        # Multas
        es_inicio_multas = len(rubros)  # índice donde empiezan las multas

        if art1:
            rubros.append(("Art. 1° Ley 25.323", monto_245))
        if art2:
            rubros.append(("Art. 2° Ley 25.323", (monto_245 + monto_preaviso + monto_integracion) * 0.5))
        if art80:
            rubros.append(("Multa Art. 80 LCT", sueldo * 3))
        if art8_24013:
            total_meses_ui = anios * 12 + meses
            rubros.append((f"Multa Art. 8° Ley 24.013 ({total_meses_ui} meses)",
                           (total_meses_ui * sueldo) / 4))
        if art9_24013 and fecha_registro:
            periodo_ui_9 = relativedelta(fecha_registro, f_ingreso)
            meses_ui_9 = periodo_ui_9.years * 12 + periodo_ui_9.months
            if meses_ui_9 > 0:
                rubros.append((f"Multa Art. 9° Ley 24.013 ({meses_ui_9} meses)",
                               (meses_ui_9 * sueldo) / 4))
        if art10_24013 and remuneracion_no_registrada > 0:
            f_in = fecha_inicio_art10 if fecha_inicio_art10 else f_ingreso
            f_out = fecha_fin_art10 if fecha_fin_art10 else f_despido
            periodo_ui_10 = relativedelta(f_out, f_in)
            meses_ui_10 = periodo_ui_10.years * 12 + periodo_ui_10.months
            if meses_ui_10 > 0:
                rubros.append((f"Multa Art. 10 Ley 24.013 ({meses_ui_10} meses s/ ${remuneracion_no_registrada:,.2f})",
                               (meses_ui_10 * remuneracion_no_registrada) / 4))
        if art15_24013:
            monto_art15_ui = (monto_245 + monto_preaviso + (monto_preaviso / 12)
                              + monto_integracion + (monto_integracion / 12 if monto_integracion > 0 else 0))
            rubros.append(("Multa Art. 15 Ley 24.013", monto_art15_ui))

        for c, m in otros_extras_visual:
            rubros.append((c, m))

        hay_multas = len(rubros) > es_inicio_multas

        total_rubros = sum(m for _, m in rubros)
        capital_historico_neto = total_rubros - monto_pagos_cuenta
        total_historico = capital_historico_neto

        coef = ipc_fin / ipc_inicio
        capital_act = total_historico * coef
        dias_pasados = max(0, (f_liquidacion - f_despido).days) + 1
        porcentaje_acumulado = dias_pasados * (0.03 / 365)
        int_puro = capital_act * porcentaje_acumulado
        total_final = capital_act + int_puro

        # ── MÉTRICAS ──────────────────────────────────────────────────────
        col_res1, col_res2, col_res3 = st.columns(3)
        with col_res1:
            st.info(f"**Antigüedad:** {anios} años, {meses} meses")
        with col_res2:
            st.warning(f"**Coef. IPC:** {coef:.4f}")
        with col_res3:
            st.success(f"**Total (+3% an. — {dias_pasados} d.):** ${total_final:,.2f}")

        tope_minimo = total_final * 0.67
        st.markdown(f"**Tope Mínimo (67% LCT):** ${tope_minimo:,.2f}")

        if aplicar_vizzoti:
            if base_indem == sueldo * 0.67:
                st.caption(f"ℹ️ Se aplica **Piso Vizzoti**: Base ${base_indem:,.2f} (67% de Remuneración)")
            elif base_indem == tope_cct:
                st.caption(f"ℹ️ Se aplica **Tope CCT**: Base ${base_indem:,.2f}")

        # ── TABLA DE RUBROS ───────────────────────────────────────────────
        st.subheader("Resumen de Rubros")
        c_tabla, _ = st.columns([0.65, 0.35])
        with c_tabla:
            aplicar_estilos_tabla()

            filas_html = ""
            for i, (label, monto) in enumerate(rubros):
                # Separador antes de la primera multa
                clase = "separador" if (hay_multas and i == es_inicio_multas) else ""
                filas_html += f'<tr class="{clase}"><td>{label}</td><td>${monto:,.2f}</td></tr>'

            if monto_pagos_cuenta > 0:
                filas_html += f'<tr><td>SUBTOTAL CAPITAL HISTÓRICO</td><td>${total_rubros:,.2f}</td></tr>'
                filas_html += f'<tr><td>Pagos a cuenta (al despido)</td><td>-${monto_pagos_cuenta:,.2f}</td></tr>'
                filas_html += f'<tr><td><b>CAPITAL HISTÓRICO NETO</b></td><td><b>${capital_historico_neto:,.2f}</b></td></tr>'
            else:
                filas_html += f'<tr><td><b>TOTAL HISTÓRICO</b></td><td><b>${total_historico:,.2f}</b></td></tr>'

            html = f"""
            <table class="table-jnt">
                <thead><tr><th>Rubro</th><th>Monto</th></tr></thead>
                <tbody>{filas_html}</tbody>
            </table>"""
            st.markdown(html, unsafe_allow_html=True)

        # ── DESCARGA EXCEL ────────────────────────────────────────────────
        st.markdown("### 📥 Exportar Liquidación")
        excel_buffer = io.BytesIO()
        liquidador.generar_excel(
            buffer=excel_buffer,
            fecha_ipc_ini=st.session_state.get("fecha_ipc_ini"),
            fecha_ipc_fin=st.session_state.get("fecha_ipc_fin"),
        )
        st.download_button(
            label="📄 Descargar Excel Completo",
            data=excel_buffer.getvalue(),
            file_name=f"Liquidacion_{caratula.replace(' ', '_')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    except Exception as e:
        st.error(f"Error en el cálculo: {e}")
        st.write("Verifique las fechas y los datos ingresados.")


if __name__ == "__main__":
    main()
