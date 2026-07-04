import streamlit as st
import pandas as pd
from datetime import datetime, date
import io
from app_liquidacion import LiquidadorLaboral, obtener_datos_online, cargar_ipc_seed
from utils import (
    aplicar_estilos, aplicar_estilos_tabla, mostrar_footer, sanitizar_nombre,
    encabezado_institucional, tarjeta_metrica, sello_fuente,
    caja_monto_letras, alerta, monto_en_letras,
)

SECCION_LABELS = {
    "indemnizatorios": "§ RUBROS INDEMNIZATORIOS",
    "salariales": "§ RUBROS SALARIALES",
    "multas": "§ MULTAS E INCREMENTOS",
    "adicionales": "§ ADICIONALES",
}


@st.cache_data(ttl=3600)
def _ipc_online_cacheado(fecha_objetivo):
    """Wrapper cacheado (1h) sobre obtener_datos_online, del lado de la página."""
    return obtener_datos_online(fecha_objetivo=fecha_objetivo)


st.set_page_config(
    page_title="Liquidaciones JNT",
    page_icon="logo.png",
    layout="wide",
    initial_sidebar_state="expanded"
)

aplicar_estilos()


def _semaforo_completitud():
    """Puntos que se llenan en dorado según qué pasos ya tienen datos, sin validación nueva."""
    pasos = [
        bool(st.session_state.get("caratula")) and (st.session_state.get("sueldo") or 0) > 0,
        "causa" in st.session_state,
        any(st.session_state.get(k) for k in
            ("art1", "art2", "art80", "dto34", "art8_24013", "art9", "art10", "art15_24013")),
        bool(st.session_state.get("aplicar_vizzoti")) or (st.session_state.get("cant_meses") or 0) > 0
        or bool(st.session_state.get("aplicar_pagos_cuenta")),
        bool(st.session_state.get("ipc_actualizado")),
    ]
    puntos = "".join("●" if p else "○" for p in pasos)
    st.markdown(
        f"<div style='letter-spacing:0.35em; font-size:1.15rem; color:var(--jnt-dorado, #B8860B); "
        f"text-align:center; margin-bottom:0.75rem;'>{puntos}</div>",
        unsafe_allow_html=True,
    )


def main():
    encabezado_institucional(
        "Liquidación por Despido",
        "Arts. 245, 232, 233 LCT — Actualización IPC INDEC + 3% anual",
    )

    # ── PANEL LATERAL: EXPEDIENTE POR PASOS ───────────────────────────────────
    with st.sidebar:
        _semaforo_completitud()

        if st.button("Nueva Liquidación", type="primary", use_container_width=True):
            for key in list(st.session_state.keys()):
                if not key.startswith("authentication") and key != "name" and key != "username":
                    del st.session_state[key]
            st.rerun()

        with st.expander("I · Expediente", expanded=True):
            caratula = st.text_input("Carátula / Expediente", value="",
                                     placeholder="Ej: García c/ Pérez s/ Despido", key="caratula")

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

            incluir_sac_ant = False
            if f_despido.month in (1, 7):
                label_sac = ("¿Incluir SAC 1er Semestre adeudado?"
                             if f_despido.month == 7
                             else "¿Incluir SAC 2do Semestre (año ant.) adeudado?")
                incluir_sac_ant = st.checkbox(label_sac, value=True, key="incluir_sac_ant",
                                              help="Marcar si al momento del despido aún no se había percibido el SAC del semestre anterior.")

        with st.expander("II · Causa de extinción", expanded=False):
            causa = st.selectbox("Causa", ["Sin Causa", "Con causa / Renuncia", "Mutuo Acuerdo"], key="causa")

        with st.expander("III · Multas e incrementos", expanded=False):
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

        with st.expander("IV · Vizzoti y rubros adicionales", expanded=False):
            st.markdown("**Fallo Vizzoti**")
            aplicar_vizzoti = st.checkbox("Aplicar Tope / Fallo Vizzoti", value=False, key="aplicar_vizzoti")
            tope_cct = 0.0
            if aplicar_vizzoti:
                tope_cct = st.number_input("Monto Tope Convencional ($)", min_value=0.0,
                                           value=0.0, step=1000.0, format="%.2f", key="tope_cct")

            st.markdown("---")
            st.markdown("**Rubros Adicionales**")

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
            st.markdown("**Pagos a Cuenta**")
            aplicar_pagos_cuenta = st.checkbox("Habilitar Pagos a Cuenta", value=False,
                                               key="aplicar_pagos_cuenta")
            monto_pagos_cuenta = 0.0
            if aplicar_pagos_cuenta:
                monto_pagos_cuenta = st.number_input("Monto pagado a cuenta ($)", min_value=0.0,
                                                     value=0.0, step=1000.0, format="%.2f",
                                                     key="monto_pagos_cuenta")

        with st.expander("V · Índices IPC", expanded=False):
            ipc_actualizado = st.session_state.get("ipc_actualizado", False)
            if ipc_actualizado:
                fuente_txt = "en línea" if st.session_state.get("ipc_fuente") == "online" else "seed local"
                st.success(f"Índices actualizados ({fuente_txt}).")
            else:
                alerta("Índices no actualizados — presione el botón antes de calcular.")

            if st.button("Actualizar Índices Online"):
                with st.spinner("Consultando API del INDEC..."):
                    try:
                        val_ini_data = _ipc_online_cacheado(f_despido.strftime("%d/%m/%Y"))
                        val_fin_data = _ipc_online_cacheado(f_liquidacion.strftime("%d/%m/%Y"))
                        if val_ini_data and val_fin_data and val_ini_data[0] and val_fin_data[0]:
                            val_ini, fecha_ini_real = val_ini_data
                            val_fin, fecha_fin_real = val_fin_data
                            st.session_state["ipc_inicio"] = val_ini
                            st.session_state["ipc_fin"] = val_fin
                            st.session_state["fecha_ipc_ini"] = fecha_ini_real
                            st.session_state["fecha_ipc_fin"] = fecha_fin_real
                            st.session_state["ipc_actualizado"] = True
                            st.session_state["ipc_fuente"] = "online"
                            st.success(f"IPC obtenido: {fecha_ini_real} → {fecha_fin_real}")
                            st.rerun()
                        else:
                            raise RuntimeError("Sin datos de la API para esas fechas.")
                    except Exception:
                        # Fallback: seed local de IPC (data/ipc_seed.json)
                        try:
                            seed = cargar_ipc_seed()

                            def _buscar_en_seed(fecha_objetivo):
                                clave = fecha_objetivo.strftime("%Y-%m-01")
                                if clave in seed:
                                    return seed[clave], fecha_objetivo.strftime("%d/%m/%Y")
                                ultima_clave = max(seed.keys())
                                return seed[ultima_clave], datetime.strptime(ultima_clave, "%Y-%m-%d").strftime("%d/%m/%Y")

                            val_ini, fecha_ini_real = _buscar_en_seed(f_despido)
                            val_fin, fecha_fin_real = _buscar_en_seed(f_liquidacion)
                            st.session_state["ipc_inicio"] = val_ini
                            st.session_state["ipc_fin"] = val_fin
                            st.session_state["fecha_ipc_ini"] = fecha_ini_real
                            st.session_state["fecha_ipc_fin"] = fecha_fin_real
                            st.session_state["ipc_actualizado"] = True
                            st.session_state["ipc_fuente"] = "seed"
                            ultimo_periodo = datetime.strptime(max(seed.keys()), "%Y-%m-%d").strftime("%m/%Y")
                            sello_fuente(f"Fuente: seed local al {ultimo_periodo} — verificar si hay índice más reciente")
                            st.rerun()
                        except FileNotFoundError:
                            alerta("No se pudieron obtener datos online ni el seed local de IPC.")

            if st.session_state.get("ipc_fuente") == "seed":
                ultimo = st.session_state.get("fecha_ipc_fin", "N/D")
                sello_fuente(f"Fuente: seed local — último período {ultimo}")

            fecha_ipc_ini_label = st.session_state.get("fecha_ipc_ini", "Mes Despido")
            fecha_ipc_fin_label = st.session_state.get("fecha_ipc_fin", "Liquidación")

            ipc_inicio = st.number_input(f"IPC Inicio ({fecha_ipc_ini_label})",
                                         value=st.session_state.get("ipc_inicio", None),
                                         format="%.4f", key="ipc_inicio_input")
            ipc_fin = st.number_input(f"IPC Cierre ({fecha_ipc_fin_label})",
                                      value=st.session_state.get("ipc_fin", None),
                                      format="%.4f", key="ipc_fin_input")

        mostrar_footer()

    # ── VALIDACIONES ──────────────────────────────────────────────────────────
    if sueldo <= 0:
        st.info("Ingrese un sueldo mayor a 0 para comenzar.")
        return

    if f_ingreso > f_despido:
        alerta("La fecha de ingreso no puede ser posterior a la fecha de despido.")
        return

    if f_despido > f_liquidacion:
        alerta("La fecha de despido no puede ser posterior a la fecha de liquidación.")
        return

    if art10_24013 and fecha_inicio_art10 and fecha_fin_art10:
        if fecha_inicio_art10 > fecha_fin_art10:
            alerta("La fecha de inicio del período (Art. 10) no puede ser posterior a la fecha de fin.")
            return

    if ipc_inicio is None or ipc_fin is None or ipc_inicio <= 0 or ipc_fin <= 0:
        alerta("Actualice los índices IPC antes de calcular (paso V del expediente).")
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
        base_indem = liquidador.calcular_base_245()

        # ── RUBROS (única fuente de verdad: LiquidadorLaboral.calcular_rubros) ──
        r = liquidador.calcular_rubros()

        total_historico = r["total_historico"]
        capital_historico_neto = r["capital_neto"]
        coef = r["coef"]
        capital_act = r["capital_actualizado"]
        dias_pasados = r["dias"]
        int_puro = r["interes_puro"]
        total_final = r["total_final"]

        # ── MÉTRICAS ──────────────────────────────────────────────────────
        col_res1, col_res2, col_res3 = st.columns(3)
        with col_res1:
            tarjeta_metrica("Antigüedad computada", f"{anios} años, {meses} meses")
        with col_res2:
            tarjeta_metrica("Coeficiente IPC", f"{coef:.4f}")
        with col_res3:
            tarjeta_metrica("Total actualizado", f"${total_final:,.2f}", tono="exito")

        tope_minimo = total_final * 0.67
        st.caption(f"Tope Mínimo (67% LCT): ${tope_minimo:,.2f}")

        if aplicar_vizzoti:
            if base_indem == sueldo * 0.67:
                st.caption(f"Se aplica **Piso Vizzoti**: Base ${base_indem:,.2f} (67% de Remuneración)")
            elif base_indem == tope_cct:
                st.caption(f"Se aplica **Tope CCT**: Base ${base_indem:,.2f}")

        # ── MONTO EN LETRAS ─────────────────────────────────────────────────
        caja_monto_letras(f"{monto_en_letras(total_final)}")

        # ── TABLA DE RUBROS AGRUPADA POR SECCIÓN ──────────────────────────
        st.subheader("Resumen de Rubros")
        c_tabla, _ = st.columns([0.65, 0.35])
        with c_tabla:
            aplicar_estilos_tabla()

            filas_html = ""
            for seccion in ("indemnizatorios", "salariales", "multas", "adicionales"):
                items = [(label, monto) for sec, label, monto in r["rubros"] if sec == seccion]
                if not items:
                    continue
                filas_html += f'<tr class="jnt-seccion"><td colspan="2">{SECCION_LABELS[seccion]}</td></tr>'
                for label, monto in items:
                    filas_html += f'<tr><td>{label}</td><td>${monto:,.2f}</td></tr>'

            filas_html += f'<tr><td>Capital Histórico</td><td>${total_historico:,.2f}</td></tr>'
            if monto_pagos_cuenta > 0:
                filas_html += f'<tr><td>Pagos a cuenta (al despido)</td><td>-${monto_pagos_cuenta:,.2f}</td></tr>'
                filas_html += f'<tr><td><b>Capital Histórico Neto</b></td><td><b>${capital_historico_neto:,.2f}</b></td></tr>'

            filas_html += '<tr class="jnt-seccion"><td colspan="2">§ ACTUALIZACIÓN E INTERESES</td></tr>'
            filas_html += f'<tr><td>Coeficiente IPC INDEC</td><td>{coef:.4f}</td></tr>'
            filas_html += f'<tr><td>Capital Actualizado (IPC)</td><td>${capital_act:,.2f}</td></tr>'
            filas_html += f'<tr><td>Interés Puro (3% anual — {dias_pasados} días)</td><td>${int_puro:,.2f}</td></tr>'
            filas_html += f'<tr><td><b>TOTAL FINAL</b></td><td><b>${total_final:,.2f}</b></td></tr>'

            html = f"""
            <table class="table-jnt">
                <thead><tr><th>Rubro</th><th>Monto</th></tr></thead>
                <tbody>{filas_html}</tbody>
            </table>"""
            st.markdown(html, unsafe_allow_html=True)

        # ── TEXTO PARA LA SENTENCIA ────────────────────────────────────────
        st.subheader("Texto para la sentencia")
        st.text_area(
            "Listo para copiar al proyecto de sentencia",
            value=liquidador.texto_sentencia(),
            height=160,
            disabled=True,
        )

        # ── EXPORTACIÓN ────────────────────────────────────────────────────
        st.subheader("Exportar Liquidación")
        excel_buffer = io.BytesIO()
        liquidador.generar_excel(
            buffer=excel_buffer,
            fecha_ipc_ini=st.session_state.get("fecha_ipc_ini"),
            fecha_ipc_fin=st.session_state.get("fecha_ipc_fin"),
        )
        col_exp1, col_exp2 = st.columns(2)
        with col_exp1:
            st.download_button(
                label="Descargar Excel Completo",
                data=excel_buffer.getvalue(),
                file_name=f"Liquidacion_{sanitizar_nombre(caratula)}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
        with col_exp2:
            if st.button("Vista de impresión", use_container_width=True):
                st.info("Presione Ctrl+P (Cmd+P en Mac) para imprimir: el diseño oculta automáticamente el panel lateral y los botones.")

    except Exception as e:
        alerta(f"Error en el cálculo: {e}")
        st.write("Verifique las fechas y los datos ingresados.")


if __name__ == "__main__":
    main()
