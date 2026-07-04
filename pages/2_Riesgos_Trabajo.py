import io
import streamlit as st
import pandas as pd
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from app_lrt import CalculadoraLRT, cargar_ripte_seed, cargar_pisos
from utils import (
    aplicar_estilos, aplicar_estilos_tabla, mostrar_footer, sanitizar_nombre,
    encabezado_institucional, tarjeta_metrica, chip_norma, sello_fuente,
    caja_monto_letras, alerta, monto_en_letras,
)

# Enlaces oficiales InfoLEG
LEY_24557 = "https://servicios.infoleg.gob.ar/infolegInternet/verNorma.do?id=27971"
LEY_26773 = "https://servicios.infoleg.gob.ar/infolegInternet/verNorma.do?id=203798"

st.set_page_config(
    page_title="Riesgos del Trabajo - Liquidaciones JNT",
    page_icon="logo.png",
    layout="wide",
    initial_sidebar_state="expanded"
)

aplicar_estilos()
aplicar_estilos_tabla()


def _cargar_ripte_inicial():
    if "lrt_ripte_serie" not in st.session_state:
        st.session_state["lrt_ripte_serie"] = cargar_ripte_seed()
        st.session_state["lrt_ripte_fuente"] = "local"


def main():
    _cargar_ripte_inicial()

    encabezado_institucional(
        "Riesgos del Trabajo",
        "Ley 24.557 · art. 3 Ley 26.773 — Prestación Dineraria por Incapacidad Permanente Parcial",
    )
    st.markdown(
        chip_norma("Ley 24.557 (InfoLEG)", LEY_24557) + " " + chip_norma("Ley 26.773 (InfoLEG)", LEY_26773),
        unsafe_allow_html=True,
    )

    # ── SIDEBAR: EXPEDIENTE POR PASOS ─────────────────────────────────────────
    with st.sidebar:
        if st.button("Nueva Liquidación LRT", type="primary", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

        with st.expander("I · Expediente y trabajador", expanded=True):
            caratula = st.text_input(
                "Carátula / Expediente", value="",
                placeholder="Ej: García c/ Empresa S.A. s/ Accidente",
                key="lrt_caratula"
            )
            f_nacimiento = st.date_input(
                "Fecha de Nacimiento", value=date(1970, 1, 1),
                min_value=date(1900, 1, 1), max_value=date.today(),
                format="DD/MM/YYYY", key="lrt_f_nac"
            )
            f_accidente = st.date_input(
                "Fecha del Accidente", value=date.today(),
                min_value=date(1950, 1, 1), max_value=date(2100, 12, 31),
                format="DD/MM/YYYY", key="lrt_f_acc"
            )
            f_sentencia = st.date_input(
                "Fecha de Sentencia / Liquidación", value=date.today(),
                min_value=date(1950, 1, 1), max_value=date(2100, 12, 31),
                format="DD/MM/YYYY", key="lrt_f_sent"
            )

        with st.expander("II · Incapacidad", expanded=False):
            incapacidad = st.number_input(
                "% Incapacidad", min_value=0.0, max_value=100.0,
                value=0.0, step=0.01, format="%.2f", key="lrt_incap"
            )
            if incapacidad >= 66.0:
                alerta(
                    "Incapacidad ≥ 66%: verificar si corresponde art. 14.2.b "
                    "(Gran Invalidez). Este módulo calcula solo IPP."
                )

        with st.expander("III · IBM", expanded=False):
            modo = st.radio(
                "Ingresar IBM como:",
                ["IBM Directo (Modo A)", "Promedio de Salarios (Modo B)"],
                key="lrt_modo",
                help=(
                    "**Modo A:** usar cuando el IBM (Ingreso Base Mensual) ya fue determinado "
                    "judicialmente o consta en la pericia contable como un valor único. "
                    "Se actualiza por RIPTE entre accidente y sentencia.\n\n"
                    "**Modo B:** usar cuando se reconstruye el IBM desde los 12 salarios del "
                    "año previo al accidente. Cada salario se actualiza por RIPTE hasta el mes "
                    "del accidente y luego se promedian."
                )
            )

            ibm_historico = None
            salarios = None

            if modo == "IBM Directo (Modo A)":
                ibm_historico = st.number_input(
                    "IBM Histórico ($)", min_value=0.0, value=0.0,
                    step=100.0, format="%.2f", key="lrt_ibm"
                )
            else:
                st.markdown("Ingresar los 12 salarios del año previo al accidente:")

                col_pi, col_btn = st.columns([3, 2])
                with col_pi:
                    periodo_inicial = st.text_input(
                        "Período inicial (MM/AAAA)",
                        placeholder="Ej: 07/2014",
                        key="lrt_periodo_inicial"
                    )
                with col_btn:
                    st.markdown("<div style='margin-top:28px'></div>", unsafe_allow_html=True)
                    if st.button("Completar 12 períodos", key="lrt_btn_completar"):
                        try:
                            mes0 = datetime.strptime(periodo_inicial.strip(), "%m/%Y")
                            periodos = [(mes0 + relativedelta(months=i)).strftime("%m/%Y") for i in range(12)]
                            st.session_state["lrt_salarios_data"] = pd.DataFrame({
                                "Período (MM/AAAA)": periodos,
                                "Importe ($)": [0.0] * 12,
                            })
                            st.session_state["lrt_sal_v"] = st.session_state.get("lrt_sal_v", 0) + 1
                        except ValueError:
                            alerta("Formato inválido. Use MM/AAAA (ej: 07/2014)")

                sal_v = st.session_state.get("lrt_sal_v", 0)
                df_inicial = st.session_state.get("lrt_salarios_data", pd.DataFrame({
                    "Período (MM/AAAA)": [""] * 12,
                    "Importe ($)": [0.0] * 12,
                }))
                edited_sal = st.data_editor(
                    df_inicial,
                    num_rows="fixed",
                    use_container_width=True,
                    key=f"lrt_salarios_{sal_v}",
                    column_config={
                        "Período (MM/AAAA)": st.column_config.TextColumn(
                            "Período (MM/AAAA)", help="Formato: MM/AAAA, ej: 06/2015"
                        ),
                        "Importe ($)": st.column_config.NumberColumn(
                            "Importe ($)", format="%.2f", min_value=0.0
                        ),
                    },
                )
                salarios_raw = []
                for _, row in edited_sal.iterrows():
                    periodo = str(row["Período (MM/AAAA)"]).strip()
                    importe = float(row["Importe ($)"])
                    if periodo and importe > 0:
                        salarios_raw.append({"periodo": periodo, "importe": importe})
                salarios = salarios_raw if salarios_raw else None

        with st.expander("IV · Índice RIPTE", expanded=False):
            ripte_serie_actual = st.session_state.get("lrt_ripte_serie", {})
            n_periodos = len(ripte_serie_actual)
            ultimo_periodo = max(ripte_serie_actual.keys()) if ripte_serie_actual else "N/D"
            try:
                ultimo_display = datetime.strptime(ultimo_periodo, "%Y-%m-%d").strftime("%m/%Y")
            except ValueError:
                ultimo_display = ultimo_periodo

            sello_fuente(f"RIPTE — SRT — ÍNDICE NO DECRECIENTE BASE 07/94 · {n_periodos} períodos, último {ultimo_display}")

            with st.expander("Agregar períodos RIPTE"):
                st.caption(
                    "Fuente oficial: cuadro SRT en "
                    "https://www.argentina.gob.ar/trabajo/seguridadsocial/ripte  "
                    "— usar la columna **'Índice No Decreciente Base 07/94 = 100'**."
                )
                col_rp, col_rv = st.columns(2)
                with col_rp:
                    nuevo_periodo = st.text_input(
                        "Período (MM/AAAA)", placeholder="Ej: 03/2026",
                        key="lrt_ripte_nuevo_periodo"
                    )
                with col_rv:
                    nuevo_valor = st.number_input(
                        "Índice No Decreciente", min_value=0.0, value=0.0,
                        format="%.2f", key="lrt_ripte_nuevo_valor"
                    )
                if st.button("Agregar período", key="lrt_btn_agregar_ripte"):
                    if nuevo_periodo and nuevo_valor > 0:
                        try:
                            mes = datetime.strptime(nuevo_periodo.strip(), "%m/%Y")
                            clave = mes.strftime("%Y-%m-01")
                            serie = dict(st.session_state["lrt_ripte_serie"])
                            serie[clave] = nuevo_valor
                            st.session_state["lrt_ripte_serie"] = serie
                            st.success(f"Período {nuevo_periodo} agregado (índice: {nuevo_valor:,.2f}).")
                            st.rerun()
                        except ValueError:
                            alerta("Formato inválido. Use MM/AAAA (ej: 03/2026)")
                    else:
                        alerta("Complete el período y el valor antes de agregar.")

        mostrar_footer()

    # ── LÓGICA DE CÁLCULO ────────────────────────────────────────────────────
    listo_a = (modo == "IBM Directo (Modo A)" and ibm_historico is not None and ibm_historico > 0)
    listo_b_parcial = (modo == "Promedio de Salarios (Modo B)" and salarios)
    listo_b = listo_b_parcial and len(salarios) == 12

    if incapacidad <= 0:
        st.info("Ingrese el porcentaje de incapacidad y los datos del caso para calcular.")
        return

    if not listo_a and not listo_b_parcial:
        msg = (
            "Ingrese el IBM Histórico para calcular."
            if modo == "IBM Directo (Modo A)"
            else "Ingrese al menos un salario en la tabla para calcular."
        )
        st.info(msg)
        return

    if listo_b_parcial and not listo_b:
        n_sal = len(salarios)
        alerta(
            f"Se ingresaron {n_sal} salario{'s' if n_sal != 1 else ''} con importe mayor a cero. "
            f"Se requieren exactamente 12 para calcular el IBM promedio."
        )
        return

    try:
        pisos = cargar_pisos()
        ripte_serie = st.session_state["lrt_ripte_serie"]

        calc = CalculadoraLRT(
            caratula=caratula or "Sin carátula",
            fecha_nacimiento=f_nacimiento.strftime("%d/%m/%Y"),
            fecha_accidente=f_accidente.strftime("%d/%m/%Y"),
            fecha_sentencia=f_sentencia.strftime("%d/%m/%Y"),
            incapacidad_pct=incapacidad,
            ibm_historico=ibm_historico,
            salarios=salarios,
            ripte_serie=ripte_serie,
            pisos=pisos,
        )

        d = calc.desglose()

        # ── AVISO RIPTE FALLBACK ─────────────────────────────────────────────
        if d["ripte_sentencia_fallback"]:
            periodo_display = datetime.strptime(d["ripte_sentencia_periodo_real"], "%Y-%m-%d").strftime("%m/%Y")
            st.info(
                f"**RIPTE de sentencia:** se usa el último índice publicado ({periodo_display}), "
                f"ya que el período {f_sentencia.strftime('%m/%Y')} aún no está disponible."
            )

        # ── MÉTRICAS RÁPIDAS ─────────────────────────────────────────────────
        col1, col2, col3 = st.columns(3)
        with col1:
            tarjeta_metrica("Edad al accidente", f"{d['edad']} años")
        with col2:
            tarjeta_metrica("Coef. RIPTE", f"{d['coef_ripte']:.4f}")
        with col3:
            tarjeta_metrica("Capital Final", f"${d['capital_final']:,.2f}", tono="exito")

        if d["aplica_piso"]:
            st.markdown(
                f"Se aplica el **piso legal**: {chip_norma(d['piso_norma'])}",
                unsafe_allow_html=True,
            )

        # ── MONTO EN LETRAS ───────────────────────────────────────────────────
        caja_monto_letras(monto_en_letras(d["capital_final"]))

        # ── DESGLOSE ─────────────────────────────────────────────────────────
        st.subheader("Desglose de la Liquidación")

        periodo_ripte_sent = datetime.strptime(d["ripte_sentencia_periodo_real"], "%Y-%m-%d").strftime("%m/%Y")
        label_ripte_sent = (
            f"RIPTE mes de sentencia ({periodo_ripte_sent} — último publicado)"
            if d["ripte_sentencia_fallback"]
            else f"RIPTE mes de sentencia ({periodo_ripte_sent})"
        )

        # ── TABLA ACTUALIZACIÓN DE SALARIOS (solo Modo B) ───────────────────
        if modo != "IBM Directo (Modo A)" and d["ibm_promedio_en_accidente"] is not None:
            st.subheader("Actualización de Salarios por RIPTE")
            detalle = calc.detalle_salarios_actualizados()
            if detalle:
                ibm_acc = d["ibm_promedio_en_accidente"]
                n = len(detalle)
                min_hist = min(r["historico"] for r in detalle)

                if ibm_acc < min_hist:
                    alerta(
                        f"El IBM calculado (${ibm_acc:,.2f}) es menor al salario histórico más bajo "
                        f"(${min_hist:,.2f}). Verificá que los importes estén ingresados en pesos "
                        f"con punto como separador decimal (ej.: 11894.28, no 11.894,28)."
                    )

                filas_sal = [
                    [r["periodo"], f"${r['historico']:,.2f}", f"{r['ripte_mes']:,.2f}",
                     f"{r['coef']:.6f}", f"${r['actualizado']:,.2f}"]
                    for r in detalle
                ]
                filas_sal.append([
                    f"IBM (total/{n})", "", f"RIPTE acc.: {detalle[0]['ripte_acc']:,.2f}",
                    "", f"${ibm_acc:,.2f}"
                ])
                df_sal = pd.DataFrame(
                    filas_sal,
                    columns=["Mes", "Salario histórico", "RIPTE del mes",
                             "Coef. RIPTE", "Salario actualizado"]
                )
                c_sal, _ = st.columns([0.75, 0.25])
                with c_sal:
                    html_sal = df_sal.to_html(index=False, classes="table-jnt", border=0, justify="center")
                    st.markdown(html_sal, unsafe_allow_html=True)

            st.markdown("---")

        # ── DESGLOSE PRINCIPAL ───────────────────────────────────────────────
        filas_desglose = [
            ("Fecha del accidente",                         f_accidente.strftime("%d/%m/%Y")),
            ("Fecha de sentencia / liquidación",            f_sentencia.strftime("%d/%m/%Y")),
            ("Edad al accidente",                           f"{d['edad']} años"),
            ("Coeficiente de edad (65 / edad)",             f"{d['coef_edad']:.4f}"),
            ("RIPTE mes del accidente",                     f"${d['ripte_accidente']:,.4f}"),
            (label_ripte_sent,                              f"${d['ripte_sentencia']:,.4f}"),
            ("Coeficiente RIPTE (sent. / acc.)",            f"{d['coef_ripte']:.4f}"),
        ]
        if d["ibm_promedio_en_accidente"] is not None:
            filas_desglose.append(
                ("IBM promedio al accidente (Modo B)",      f"${d['ibm_promedio_en_accidente']:,.2f}")
            )
        filas_desglose += [
            ("IBM actualizado a sentencia",                 f"${d['ibm_actualizado']:,.2f}"),
            ("Indemnización base (art. 14.2.a Ley 24.557)", f"${d['indemnizacion_base']:,.2f}"),
            ("Adicional art. 3 Ley 26.773 (20%)",           f"${d['adicional_art3']:,.2f}"),
            ("Subtotal LRT",                                f"${d['subtotal_lrt']:,.2f}"),
            (f"Piso legal ({d['piso_norma']})",             f"${d['piso_monto_total']:,.2f}"),
            (f"Piso aplicable ({incapacidad:.2f}%)",        f"${d['piso_aplicable']:,.2f}"),
        ]

        df_desglose = pd.DataFrame(filas_desglose, columns=["Concepto", "Valor"])
        df_capital = pd.DataFrame(
            [["CAPITAL FINAL", f"${d['capital_final']:,.2f}"]],
            columns=["Concepto", "Valor"]
        )
        df_tabla = pd.concat([df_desglose, df_capital], ignore_index=True)

        c_tabla, _ = st.columns([0.65, 0.35])
        with c_tabla:
            html = df_tabla.to_html(index=False, classes="table-jnt", border=0, justify="center")
            st.markdown(html, unsafe_allow_html=True)

        # ── TEXTO PARA LA SENTENCIA ────────────────────────────────────────
        st.subheader("Texto para la sentencia")
        st.text_area(
            "Listo para copiar al proyecto de sentencia",
            value=calc.texto_sentencia(),
            height=160,
            disabled=True,
        )

        # ── EXPORTACIÓN ────────────────────────────────────────────────────
        st.subheader("Exportar Liquidación LRT")
        excel_buffer = io.BytesIO()
        calc.generar_excel(buffer=excel_buffer)
        excel_data = excel_buffer.getvalue()

        st.download_button(
            label="Descargar Excel",
            data=excel_data,
            file_name=f"LRT_{sanitizar_nombre(caratula or 'LRT')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except ValueError as e:
        alerta(f"Error de validación: {e}")
        st.caption("Verifique que las fechas tengan índice RIPTE disponible y que los datos sean correctos.")
    except Exception as e:
        alerta(f"Error en el cálculo: {e}")
        st.caption("Verifique las fechas, el índice RIPTE y los datos ingresados.")


if __name__ == "__main__":
    main()
