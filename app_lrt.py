import json
import re
from datetime import datetime
from dateutil.relativedelta import relativedelta
from functools import lru_cache
import requests
import pandas as pd

from app_liquidacion import _obtener_serie

SERIE_ID_RIPTE = "158.1_REPTE_0_0_5"  # RIPTE mensual — Secretaría de Trabajo (datos.gob.ar)


# ---------------------------------------------------------------------------
# Carga de datos de referencia
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def cargar_pisos(path="data/pisos.json"):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def cargar_ripte_seed(path="data/ripte_seed.json"):
    with open(path, encoding="utf-8") as f:
        seed = json.load(f)
    return {item["periodo"]: item["valor"] for item in seed}


# ---------------------------------------------------------------------------
# Cliente API RIPTE
# ---------------------------------------------------------------------------

def obtener_ripte(fecha_objetivo=None):
    """
    Devuelve (valor, fecha_str) del RIPTE para el mes de fecha_objetivo,
    o el último disponible si es None. Retorna (None, None) si falla.
    """
    return _obtener_serie(SERIE_ID_RIPTE, fecha_objetivo)


def obtener_serie_ripte_completa(seed_fallback=True):
    """
    ADVERTENCIA: La serie 158.1_REPTE_0_0_5 de datos.gob.ar devuelve el RIPTE
    en pesos corrientes (columna "Monto en $" del cuadro SRT). Para cálculos
    de Ley 24.557 se debe usar el "Índice No Decreciente Base 07/94=100",
    que NO está disponible en datos.gob.ar. Esta función NO debe usarse para
    actualizar el seed de LRT; se mantiene solo como referencia.
    """
    try:
        url = "https://apis.datos.gob.ar/series/api/series/"
        params = {"ids": SERIE_ID_RIPTE, "format": "json", "limit": 5000}
        data = requests.get(url, params=params, timeout=10).json()["data"]
        return {entry[0]: entry[1] for entry in data}
    except Exception as e:
        print(f"Error API RIPTE (usando seed): {e}")
        if seed_fallback:
            return cargar_ripte_seed()
        raise


# ---------------------------------------------------------------------------
# Clase CalculadoraLRT
# ---------------------------------------------------------------------------

class CalculadoraLRT:
    """
    Calculadora de prestación dineraria por incapacidad permanente parcial
    bajo Ley 24.557 + art. 3 Ley 26.773.

    Modo A — IBM directo: se provee ibm_historico.
    Modo B — IBM por promedio: se proveen salarios = [{"periodo": "MM/YYYY", "importe": float}, ...].
    """

    def __init__(self,
                 caratula,
                 fecha_nacimiento,
                 fecha_accidente,
                 fecha_sentencia,
                 incapacidad_pct,
                 ibm_historico=None,
                 salarios=None,
                 ripte_serie=None,
                 pisos=None):
        self.caratula = caratula
        self.fecha_nacimiento = datetime.strptime(fecha_nacimiento, "%d/%m/%Y")
        self.fecha_accidente = datetime.strptime(fecha_accidente, "%d/%m/%Y")
        self.fecha_sentencia = datetime.strptime(fecha_sentencia, "%d/%m/%Y")
        self.incapacidad_pct = float(incapacidad_pct)
        self.ibm_historico = float(ibm_historico) if ibm_historico is not None else None
        self.salarios = salarios or []
        self.ripte_serie = ripte_serie or {}
        self.pisos = pisos or []

        tiene_ibm = self.ibm_historico is not None
        tiene_salarios = len(self.salarios) > 0
        if tiene_ibm == tiene_salarios:
            raise ValueError("Provea IBM histórico O salarios mensuales, no ambos ni ninguno.")
        if self.fecha_accidente <= self.fecha_nacimiento:
            raise ValueError("La fecha del accidente debe ser posterior a la fecha de nacimiento.")
        if self.fecha_sentencia < self.fecha_accidente:
            raise ValueError("La fecha de sentencia no puede ser anterior a la fecha del accidente.")

    # --- Helpers -----------------------------------------------------------

    def _ripte(self, fecha):
        """Valor RIPTE del mes de fecha. Normaliza al día 1. Lanza ValueError si no está."""
        clave = fecha.strftime("%Y-%m-01")
        if clave not in self.ripte_serie:
            raise ValueError(f"RIPTE no disponible para {clave}. Actualice los índices online.")
        return self.ripte_serie[clave]

    def _ripte_con_fallback(self, fecha):
        """
        RIPTE del mes de fecha. Si el período aún no está publicado (fecha posterior
        al último disponible), usa el último período publicado y lo informa.
        Devuelve (valor, clave_real_usada).
        """
        clave = fecha.strftime("%Y-%m-01")
        if clave in self.ripte_serie:
            return self.ripte_serie[clave], clave
        if not self.ripte_serie:
            raise ValueError("La serie RIPTE está vacía.")
        ultima_clave = max(self.ripte_serie.keys())
        if clave > ultima_clave:
            return self.ripte_serie[ultima_clave], ultima_clave
        raise ValueError(f"RIPTE no disponible para {clave}. Actualice los índices online.")

    # --- Cálculos ----------------------------------------------------------

    def edad_al_accidente(self):
        return relativedelta(self.fecha_accidente, self.fecha_nacimiento).years

    def coef_edad(self):
        edad = self.edad_al_accidente()
        if edad <= 0:
            raise ValueError("La edad al momento del accidente debe ser mayor a cero.")
        return 65.0 / edad

    def ripte_accidente(self):
        return self._ripte(self.fecha_accidente)

    def ripte_sentencia(self):
        valor, _ = self._ripte_con_fallback(self.fecha_sentencia)
        return valor

    def ripte_sentencia_periodo_real(self):
        """Período RIPTE efectivamente usado para la sentencia (puede ser el último publicado)."""
        _, clave = self._ripte_con_fallback(self.fecha_sentencia)
        return clave

    def coef_ripte(self):
        return self.ripte_sentencia() / self.ripte_accidente()

    def ibm_promedio_en_accidente(self):
        """Modo B: promedio de los 12 salarios actualizados al mes del accidente por RIPTE."""
        if self.ibm_historico is not None:
            return None
        if len(self.salarios) != 12:
            raise ValueError(
                f"Se requieren exactamente 12 salarios para calcular el IBM (se ingresaron {len(self.salarios)})."
            )
        ripte_acc = self.ripte_accidente()
        suma = 0.0
        for s in self.salarios:
            mes = datetime.strptime(s["periodo"], "%m/%Y")
            r_mes = self._ripte(mes)
            suma += float(s["importe"]) * (ripte_acc / r_mes)
        return suma / len(self.salarios)

    def detalle_salarios_actualizados(self):
        """Modo B: detalle de la actualización RIPTE de cada salario hasta el accidente."""
        if self.ibm_historico is not None:
            return []
        ripte_acc = self.ripte_accidente()
        rows = []
        for s in self.salarios:
            mes = datetime.strptime(s["periodo"], "%m/%Y")
            r_mes = self._ripte(mes)
            coef = ripte_acc / r_mes
            rows.append({
                "periodo":     s["periodo"],
                "historico":   float(s["importe"]),
                "ripte_mes":   r_mes,
                "ripte_acc":   ripte_acc,
                "coef":        coef,
                "actualizado": float(s["importe"]) * coef,
            })
        return rows

    def ibm_actualizado(self):
        ripte_acc = self.ripte_accidente()
        ripte_sent = self.ripte_sentencia()

        if self.ibm_historico is not None:
            # Modo A: actualiza el IBM directamente del accidente a la sentencia
            return self.ibm_historico * (ripte_sent / ripte_acc)

        # Modo B: promedio de salarios al accidente, luego a sentencia
        return self.ibm_promedio_en_accidente() * (ripte_sent / ripte_acc)

    def indemnizacion_base(self):
        return 53.0 * self.ibm_actualizado() * self.coef_edad() * (self.incapacidad_pct / 100.0)

    def adicional_art3_26773(self):
        return self.indemnizacion_base() * 0.20

    def subtotal_lrt(self):
        return self.indemnizacion_base() + self.adicional_art3_26773()

    def piso_vigente(self):
        """Devuelve el dict del piso aplicable a la fecha del accidente, o None."""
        for p in self.pisos:
            desde = datetime.strptime(p["desde"], "%Y-%m-%d")
            hasta = datetime.strptime(p["hasta"], "%Y-%m-%d")
            if desde <= self.fecha_accidente <= hasta:
                return p
        return None

    def piso_aplicable(self):
        p = self.piso_vigente()
        if p is None:
            return 0.0
        return p["monto"] * (self.incapacidad_pct / 100.0)

    def capital_final(self):
        return max(self.subtotal_lrt(), self.piso_aplicable())

    def desglose(self):
        """Dict con todos los pasos intermedios, listo para UI y Excel."""
        piso = self.piso_vigente()
        periodo_sent_real = self.ripte_sentencia_periodo_real()
        periodo_sent_esperado = self.fecha_sentencia.strftime("%Y-%m-01")
        return {
            "edad": self.edad_al_accidente(),
            "coef_edad": self.coef_edad(),
            "ripte_accidente": self.ripte_accidente(),
            "ripte_sentencia": self.ripte_sentencia(),
            "ripte_sentencia_periodo_real": periodo_sent_real,
            "ripte_sentencia_fallback": periodo_sent_real != periodo_sent_esperado,
            "coef_ripte": self.coef_ripte(),
            "ibm_promedio_en_accidente": self.ibm_promedio_en_accidente(),
            "ibm_actualizado": self.ibm_actualizado(),
            "indemnizacion_base": self.indemnizacion_base(),
            "adicional_art3": self.adicional_art3_26773(),
            "subtotal_lrt": self.subtotal_lrt(),
            "piso_norma": piso["norma"] if piso else "Sin piso cargado para esa fecha",
            "piso_monto_total": piso["monto"] if piso else 0.0,
            "piso_aplicable": self.piso_aplicable(),
            "aplica_piso": self.piso_aplicable() > self.subtotal_lrt(),
            "capital_final": self.capital_final(),
        }

    def generar_excel(self, buffer=None):
        """Genera planilla Excel con la liquidación LRT. Implementado en Fase 4."""
        if buffer:
            writer = pd.ExcelWriter(buffer, engine="xlsxwriter")
        else:
            caratula_limpia = re.sub(r"[^\w\s-]", "_", self.caratula).strip().replace(" ", "_")
            nombre_archivo = f"LRT_{caratula_limpia}.xlsx"
            writer = pd.ExcelWriter(nombre_archivo, engine="xlsxwriter")

        wb = writer.book
        ws = wb.add_worksheet("Liquidación LRT")

        fmt_tit = wb.add_format({"bold": True, "bg_color": "#2F5597", "font_color": "white", "border": 1, "align": "center"})
        fmt_mon = wb.add_format({"num_format": "$#,##0.00", "border": 1})
        fmt_txt = wb.add_format({"border": 1})
        fmt_bold = wb.add_format({"bold": True, "border": 1})
        fmt_tot = wb.add_format({"bold": True, "bg_color": "#EBF1DE", "border": 1, "num_format": "$#,##0.00"})
        fmt_num4 = wb.add_format({"num_format": "0.0000", "border": 1})

        ws.set_column("A:A", 58)
        ws.set_column("B:B", 25)

        d = self.desglose()

        periodo_sent_real = datetime.strptime(d["ripte_sentencia_periodo_real"], "%Y-%m-%d").strftime("%m/%Y")
        label_ripte_sent = (
            f"RIPTE mes de sentencia ({periodo_sent_real} — último publicado)"
            if d["ripte_sentencia_fallback"]
            else f"RIPTE mes de sentencia ({periodo_sent_real})"
        )

        ws.write("A1", "EXPEDIENTE:", fmt_bold);          ws.write("B1", self.caratula, fmt_txt)
        ws.write("A2", "FECHA DE NACIMIENTO:", fmt_bold); ws.write("B2", self.fecha_nacimiento.strftime("%d/%m/%Y"), fmt_txt)
        ws.write("A3", "FECHA DEL ACCIDENTE:", fmt_bold); ws.write("B3", self.fecha_accidente.strftime("%d/%m/%Y"), fmt_txt)
        ws.write("A4", "FECHA DE SENTENCIA:", fmt_bold);  ws.write("B4", self.fecha_sentencia.strftime("%d/%m/%Y"), fmt_txt)
        ws.write("A5", "% INCAPACIDAD:", fmt_bold);       ws.write("B5", f"{self.incapacidad_pct:.2f}%", fmt_txt)

        ws.write("A7", "CONCEPTO", fmt_tit); ws.write("B7", "MONTO / VALOR", fmt_tit)

        ibm_inicial = self.ibm_historico if self.ibm_historico is not None else d["ibm_promedio_en_accidente"]
        label_ibm_inicial = "IBM Histórico (ingresado)" if self.ibm_historico is not None else "IBM Promedio al accidente (Modo B)"

        filas = [
            ("Edad al accidente (años)", d["edad"]),
            ("Coeficiente de edad (65 / edad)", d["coef_edad"]),
            ("RIPTE mes del accidente", d["ripte_accidente"]),
            (label_ripte_sent, d["ripte_sentencia"]),
            ("Coeficiente RIPTE (sent. / acc.)", d["coef_ripte"]),
            (label_ibm_inicial, ibm_inicial),
            ("IBM actualizado a sentencia", d["ibm_actualizado"]),
            ("Indemnización base (art. 14.2.a Ley 24.557)", d["indemnizacion_base"]),
            ("Adicional art. 3 Ley 26.773 (20%)", d["adicional_art3"]),
            ("Subtotal LRT", d["subtotal_lrt"]),
            (f"Piso legal ({d['piso_norma']})", d["piso_monto_total"]),
            (f"Piso aplicable ({self.incapacidad_pct:.2f}% del piso)", d["piso_aplicable"]),
        ]

        row = 8
        for lab, val in filas:
            ws.write(row, 0, lab, fmt_txt)
            if isinstance(val, int):
                ws.write(row, 1, val, fmt_txt)
            elif val == d["coef_edad"] or val == d["coef_ripte"]:
                ws.write(row, 1, val, fmt_num4)
            else:
                ws.write(row, 1, val, fmt_mon)
            row += 1

        row += 1
        aplica = "PISO LEGAL" if d["aplica_piso"] else "SUBTOTAL LRT"
        ws.write(row, 0, f"CAPITAL FINAL (aplica {aplica}):", fmt_bold)
        ws.write(row, 1, d["capital_final"], fmt_tot)

        # Hoja de detalle de salarios (solo Modo B)
        if self.ibm_historico is None:
            detalle = self.detalle_salarios_actualizados()
            if detalle:
                ws2 = wb.add_worksheet("Detalle Salarios")
                ws2.set_column("A:A", 20)
                ws2.set_column("B:F", 20)

                fmt_tit2 = wb.add_format({"bold": True, "bg_color": "#2F5597", "font_color": "white",
                                          "border": 1, "align": "center"})
                encabezados = ["Período", "Salario histórico ($)", "RIPTE del mes",
                               "RIPTE al accidente", "Coeficiente", "Salario actualizado ($)"]
                for col, h in enumerate(encabezados):
                    ws2.write(0, col, h, fmt_tit2)

                for r, row_d in enumerate(detalle, start=1):
                    ws2.write(r, 0, row_d["periodo"], fmt_txt)
                    ws2.write(r, 1, row_d["historico"], fmt_mon)
                    ws2.write(r, 2, row_d["ripte_mes"], fmt_mon)
                    ws2.write(r, 3, row_d["ripte_acc"], fmt_mon)
                    ws2.write(r, 4, row_d["coef"], fmt_num4)
                    ws2.write(r, 5, row_d["actualizado"], fmt_mon)

                # Fila de IBM promedio
                r_ibm = len(detalle) + 1
                ws2.write(r_ibm, 0, f"IBM Promedio (÷ {len(detalle)})", fmt_bold)
                ws2.write(r_ibm, 5, d["ibm_promedio_en_accidente"], fmt_tot)

        wb.close()
        if not buffer:
            print(f"\n>>> LIQUIDACIÓN LRT CREADA: LRT_{self.caratula}.xlsx <<<")
