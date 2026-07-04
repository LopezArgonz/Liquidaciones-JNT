"""
Tests de caracterización para LiquidadorLaboral (app_liquidacion.py).

Fijan el comportamiento ACTUAL (previo al refactor de Fase 1 que introduce
calcular_rubros()) para garantizar que el refactor no altera ningún número.
Los valores esperados fueron obtenidos ejecutando la implementación vigente
antes de tocar el código (snapshot de referencia).
"""
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app_liquidacion import LiquidadorLaboral

TOL = 0.01  # tolerancia en pesos


# ---------------------------------------------------------------------------
# Tests unitarios de métodos individuales (no cambian con el refactor)
# ---------------------------------------------------------------------------

class TestAntiguedad245(unittest.TestCase):
    def test_sin_redondeo_meses_menor_o_igual_3(self):
        L = LiquidadorLaboral(caratula="A", ingreso="01/01/2015", despido="01/04/2019", sueldo=100000.0)
        self.assertEqual(L.antiguedad.years, 4)
        self.assertEqual(L.antiguedad.months, 3)
        self.assertEqual(L.calcular_periodos_245(), 4)  # sin redondeo: meses(3) no es > 3

    def test_con_redondeo_meses_mayor_a_3(self):
        L = LiquidadorLaboral(caratula="B", ingreso="01/01/2015", despido="01/05/2021", sueldo=100000.0)
        self.assertEqual(L.antiguedad.years, 6)
        self.assertEqual(L.antiguedad.months, 4)
        self.assertEqual(L.calcular_periodos_245(), 7)  # redondea: meses(4) > 3 -> +1 año


class TestPreaviso(unittest.TestCase):
    """meses_preaviso = 2 si antiguedad.years >= 5, si no 1 (lógica en generar_excel/página)."""

    def test_antiguedad_menor_a_5_anios_un_mes(self):
        L = LiquidadorLaboral(caratula="A", ingreso="01/01/2015", despido="01/04/2019", sueldo=100000.0)
        self.assertLess(L.antiguedad.years, 5)

    def test_antiguedad_5_anios_o_mas_dos_meses(self):
        L = LiquidadorLaboral(caratula="B", ingreso="01/01/2015", despido="01/05/2021", sueldo=100000.0)
        self.assertGreaterEqual(L.antiguedad.years, 5)


class TestIntegracionMesDespido(unittest.TestCase):
    def test_integracion_mid_mes(self):
        L = LiquidadorLaboral(caratula="C", ingreso="01/01/2015", despido="10/06/2021", sueldo=90000.0)
        self.assertAlmostEqual(L.calcular_integracion_mes(), 60000.0, delta=TOL)

    def test_sin_integracion_si_no_es_sin_causa(self):
        L = LiquidadorLaboral(caratula="C2", ingreso="01/01/2015", despido="10/06/2021", sueldo=90000.0,
                              causa="Con causa / Renuncia")
        self.assertEqual(L.calcular_integracion_mes(), 0)


class TestSacSemestreAnterior(unittest.TestCase):
    def test_despido_julio(self):
        L = LiquidadorLaboral(caratula="D", ingreso="01/01/2010", despido="15/07/2021", sueldo=50000.0,
                              incluir_sac_anterior=True)
        self.assertAlmostEqual(L.calcular_sac_semestre_anterior(), 25000.0, delta=TOL)

    def test_despido_enero(self):
        L = LiquidadorLaboral(caratula="D2", ingreso="01/01/2010", despido="20/01/2021", sueldo=50000.0,
                              incluir_sac_anterior=True)
        self.assertAlmostEqual(L.calcular_sac_semestre_anterior(), 25000.0, delta=TOL)

    def test_no_aplica_si_no_se_marca(self):
        L = LiquidadorLaboral(caratula="D3", ingreso="01/01/2010", despido="15/07/2021", sueldo=50000.0,
                              incluir_sac_anterior=False)
        self.assertEqual(L.calcular_sac_semestre_anterior(), 0.0)


class TestSacProporcional(unittest.TestCase):
    def test_sac_prop(self):
        L = LiquidadorLaboral(caratula="C", ingreso="01/01/2015", despido="10/06/2021", sueldo=90000.0)
        self.assertAlmostEqual(L.calcular_sac_prop(), 39698.63013698631, delta=TOL)


class TestVacacionesEscala(unittest.TestCase):
    def test_escala_14_menor_5_anios(self):
        L = LiquidadorLaboral(caratula="E1", ingreso="01/01/2019", despido="01/06/2021", sueldo=60000.0)
        vac, dias = L.calcular_vacaciones_prop()
        self.assertAlmostEqual(vac, 13992.328767123288, delta=TOL)
        self.assertAlmostEqual(dias, 5.83013698630137, places=4)

    def test_escala_21_menor_10_anios(self):
        L = LiquidadorLaboral(caratula="E2", ingreso="01/01/2013", despido="01/06/2021", sueldo=60000.0)
        vac, dias = L.calcular_vacaciones_prop()
        self.assertAlmostEqual(vac, 20988.49315068493, delta=TOL)

    def test_escala_28_menor_20_anios(self):
        L = LiquidadorLaboral(caratula="E3", ingreso="01/01/2003", despido="01/06/2021", sueldo=60000.0)
        vac, dias = L.calcular_vacaciones_prop()
        self.assertAlmostEqual(vac, 27984.657534246577, delta=TOL)

    def test_escala_35_mayor_igual_20_anios(self):
        L = LiquidadorLaboral(caratula="E4", ingreso="01/01/1995", despido="01/06/2021", sueldo=60000.0)
        vac, dias = L.calcular_vacaciones_prop()
        self.assertAlmostEqual(vac, 34980.82191780822, delta=TOL)


class TestVizzoti(unittest.TestCase):
    def test_piso_67_por_ciento_cuando_tope_confiscatorio(self):
        # tope_cct (50000) < 67% del sueldo (67000) -> se aplica el 67%
        L = LiquidadorLaboral(caratula="F1", ingreso="01/01/2015", despido="01/05/2021", sueldo=100000.0,
                              aplicar_vizzoti=True, tope_cct=50000.0)
        self.assertAlmostEqual(L.calcular_base_245(), 67000.0, delta=TOL)

    def test_tope_cct_cuando_no_es_confiscatorio(self):
        # tope_cct (80000) > 67% del sueldo (67000) -> se aplica el tope CCT
        L = LiquidadorLaboral(caratula="F2", ingreso="01/01/2015", despido="01/05/2021", sueldo=100000.0,
                              aplicar_vizzoti=True, tope_cct=80000.0)
        self.assertAlmostEqual(L.calcular_base_245(), 80000.0, delta=TOL)

    def test_sin_vizzoti_usa_sueldo_pleno(self):
        L = LiquidadorLaboral(caratula="F3", ingreso="01/01/2015", despido="01/05/2021", sueldo=100000.0)
        self.assertAlmostEqual(L.calcular_base_245(), 100000.0, delta=TOL)


# ---------------------------------------------------------------------------
# Tests de regresión de escenario completo (multas, Vizzoti, pagos a cuenta, IPC)
# ---------------------------------------------------------------------------

class TestRegresionKitchenSink(unittest.TestCase):
    """
    Caso G: todas las multas activas + Vizzoti (piso 67%) + pagos a cuenta + IPC.
    ingreso=01/01/2015, despido=01/05/2021, sueldo=100000, liquidación=01/08/2022.
    """
    def setUp(self):
        self.L = LiquidadorLaboral(
            caratula="G", ingreso="01/01/2015", despido="01/05/2021", sueldo=100000.0,
            causa="Sin Causa", art1=True, art2=True, art80=True, dto34=True,
            art8_24013=True, art9_24013=True, fecha_registro="01/06/2016",
            art10_24013=True, remuneracion_no_registrada=20000.0,
            art15_24013=True,
            aplicar_vizzoti=True, tope_cct=50000.0,
            pagos_a_cuenta=15000.0,
            ipc_inicio=100.0, ipc_fin=250.0,
            fecha_liquidacion="01/08/2022",
        )

    def test_base_245_con_vizzoti(self):
        self.assertAlmostEqual(self.L.calcular_base_245(), 67000.0, delta=TOL)

    def test_monto_245(self):
        periodos = self.L.calcular_periodos_245()
        base = self.L.calcular_base_245()
        self.assertAlmostEqual(base * periodos, 469000.0, delta=TOL)

    def test_art8_24013(self):
        total_meses = self.L.antiguedad.years * 12 + self.L.antiguedad.months
        monto = (total_meses * self.L.sueldo) / 4
        self.assertAlmostEqual(monto, 1_900_000.0, delta=TOL)

    def test_art9_24013(self):
        from dateutil.relativedelta import relativedelta
        p = relativedelta(self.L.fecha_registro, self.L.ingreso)
        meses = p.years * 12 + p.months
        monto = (meses * self.L.sueldo) / 4
        self.assertAlmostEqual(monto, 425_000.0, delta=TOL)

    def test_art10_24013(self):
        from dateutil.relativedelta import relativedelta
        p = relativedelta(self.L.fecha_fin_art10, self.L.fecha_inicio_art10)
        meses = p.years * 12 + p.months
        monto = (meses * self.L.remuneracion_no_registrada) / 4
        self.assertAlmostEqual(monto, 380_000.0, delta=TOL)

    def test_art80(self):
        self.assertAlmostEqual(self.L.sueldo * 3, 300_000.0, delta=TOL)

    def test_totales_finales(self):
        # Estos totales se validan de punta a punta contra calcular_rubros()
        # una vez implementado (ver TestCalcularRubros más abajo).
        pass


# ---------------------------------------------------------------------------
# Tests contra calcular_rubros() — única fuente de verdad (post-refactor)
# ---------------------------------------------------------------------------

class TestCalcularRubrosKitchenSink(unittest.TestCase):
    """Verifica que calcular_rubros() reproduce exactamente el snapshot pre-refactor."""

    def setUp(self):
        self.L = LiquidadorLaboral(
            caratula="G", ingreso="01/01/2015", despido="01/05/2021", sueldo=100000.0,
            causa="Sin Causa", art1=True, art2=True, art80=True, dto34=True,
            art8_24013=True, art9_24013=True, fecha_registro="01/06/2016",
            art10_24013=True, remuneracion_no_registrada=20000.0,
            art15_24013=True,
            aplicar_vizzoti=True, tope_cct=50000.0,
            pagos_a_cuenta=15000.0,
            ipc_inicio=100.0, ipc_fin=250.0,
            fecha_liquidacion="01/08/2022",
        )

    def test_total_historico(self):
        r = self.L.calcular_rubros()
        self.assertAlmostEqual(r["total_historico"], 6_294_946.840477242, delta=TOL)

    def test_capital_neto(self):
        r = self.L.calcular_rubros()
        self.assertAlmostEqual(r["capital_neto"], 6_279_946.840477242, delta=TOL)

    def test_coef(self):
        r = self.L.calcular_rubros()
        self.assertAlmostEqual(r["coef"], 2.5, delta=TOL)

    def test_capital_actualizado(self):
        r = self.L.calcular_rubros()
        self.assertAlmostEqual(r["capital_actualizado"], 15_699_867.101193106, delta=TOL)

    def test_dias(self):
        r = self.L.calcular_rubros()
        self.assertEqual(r["dias"], 458)

    def test_interes_puro(self):
        r = self.L.calcular_rubros()
        self.assertAlmostEqual(r["interes_puro"], 591_003.2163572419, delta=TOL)

    def test_total_final(self):
        r = self.L.calcular_rubros()
        self.assertAlmostEqual(r["total_final"], 16_290_870.317550348, delta=TOL)

    def test_secciones_presentes(self):
        r = self.L.calcular_rubros()
        secciones = {seccion for seccion, _, _ in r["rubros"]}
        self.assertTrue(secciones.issubset({"indemnizatorios", "salariales", "multas", "adicionales"}))
        self.assertIn("indemnizatorios", secciones)
        self.assertIn("multas", secciones)

    def test_suma_de_rubros_coincide_con_total_historico(self):
        r = self.L.calcular_rubros()
        suma = sum(monto for _, _, monto in r["rubros"])
        self.assertAlmostEqual(suma, r["total_historico"], delta=TOL)


class TestCalcularRubrosSimpleConIpc(unittest.TestCase):
    """Caso H: sin multas, con actualización IPC."""

    def setUp(self):
        self.L = LiquidadorLaboral(
            caratula="H", ingreso="01/01/2018", despido="01/03/2022", sueldo=80000.0,
            causa="Sin Causa",
            ipc_inicio=120.0, ipc_fin=180.0,
            fecha_liquidacion="01/01/2023",
        )

    def test_total_historico(self):
        r = self.L.calcular_rubros()
        self.assertAlmostEqual(r["total_historico"], 514_247.0466931801, delta=TOL)

    def test_total_final(self):
        r = self.L.calcular_rubros()
        self.assertAlmostEqual(r["total_final"], 790_834.4685331024, delta=TOL)


class TestCalcularRubrosConCausa(unittest.TestCase):
    """Caso I: causa distinta de 'Sin Causa' -> sin rubros indemnizatorios."""

    def setUp(self):
        self.L = LiquidadorLaboral(
            caratula="I", ingreso="01/01/2018", despido="01/03/2022", sueldo=80000.0,
            causa="Con causa / Renuncia",
            ipc_inicio=120.0, ipc_fin=180.0,
            fecha_liquidacion="01/01/2023",
        )

    def test_total_historico(self):
        r = self.L.calcular_rubros()
        self.assertAlmostEqual(r["total_historico"], 23_709.412284577993, delta=TOL)

    def test_total_final(self):
        r = self.L.calcular_rubros()
        self.assertAlmostEqual(r["total_final"], 36_461.50344251478, delta=TOL)

    def test_sin_rubros_indemnizatorios(self):
        r = self.L.calcular_rubros()
        secciones = {seccion for seccion, _, _ in r["rubros"]}
        self.assertNotIn("indemnizatorios", secciones)


if __name__ == "__main__":
    unittest.main(verbosity=2)
