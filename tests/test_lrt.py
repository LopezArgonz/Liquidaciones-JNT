"""
Tests para CalculadoraLRT (app_lrt.py).

Nota sobre "paridad con la planilla":
La planilla_original.xlsx tiene varios bugs documentados en DISEÑO_LRT.md
(VLOOKUP con col_index erróneo, copy-paste de RIPTE en C7:C9, edad incorrecta).
Los valores en B22 y H12 de la planilla son por tanto incorrectos (#REF! y
calculados con datos erróneos respectivamente). Los expected values de estos
tests se derivan de la implementación CORRECTA de la fórmula, usando los
inputs de la planilla como punto de partida.
"""
import sys
import os
import unittest
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app_lrt import CalculadoraLRT, cargar_ripte_seed, cargar_pisos

SEED = cargar_ripte_seed()
PISOS = cargar_pisos()

TOL = 0.01  # tolerancia en pesos


# ---------------------------------------------------------------------------
# Tests unitarios — métodos individuales
# ---------------------------------------------------------------------------

class TestCoefEdad(unittest.TestCase):
    def _calc(self, nacimiento, accidente):
        return CalculadoraLRT(
            caratula="u", fecha_nacimiento=nacimiento, fecha_accidente=accidente,
            fecha_sentencia=accidente, incapacidad_pct=10.0,
            ibm_historico=1000.0, ripte_serie=SEED, pisos=PISOS,
        )

    def test_edad_exacta(self):
        # 1946-08-21 → 2011-08-31: cumpleaños ya pasó → 65 años
        c = self._calc("21/08/1946", "31/08/2011")
        self.assertEqual(c.edad_al_accidente(), 65)
        self.assertAlmostEqual(c.coef_edad(), 65 / 65, places=10)

    def test_edad_antes_cumple(self):
        # 1957-05-28 → 2015-06-05: cumpleaños (mayo) ya pasó en junio → 58 años
        c = self._calc("28/05/1957", "05/06/2015")
        self.assertEqual(c.edad_al_accidente(), 58)
        self.assertAlmostEqual(c.coef_edad(), 65 / 58, places=10)

    def test_coef_40_anios(self):
        c = self._calc("01/01/1970", "01/01/2010")
        self.assertEqual(c.edad_al_accidente(), 40)
        self.assertAlmostEqual(c.coef_edad(), 65 / 40, places=10)


class TestPisoVigente(unittest.TestCase):
    def _calc(self, fecha_accidente):
        return CalculadoraLRT(
            caratula="u", fecha_nacimiento="01/01/1970",
            fecha_accidente=fecha_accidente, fecha_sentencia=fecha_accidente,
            incapacidad_pct=10.0, ibm_historico=1000.0,
            ripte_serie=SEED, pisos=PISOS,
        )

    def test_dto1694_09_inicio(self):
        c = self._calc("06/11/2009")
        p = c.piso_vigente()
        self.assertIsNotNone(p)
        self.assertEqual(p["norma"], "Dto. 1694/09")
        self.assertAlmostEqual(p["monto"], 80000.0)

    def test_entrada_22_corregida(self):
        # Bug corregido: desde=2022-09-01 (era 2023-06-08), norma Res SRT 51/2022
        c = self._calc("15/10/2022")
        p = c.piso_vigente()
        self.assertIsNotNone(p)
        self.assertIn("51/2022", p["norma"])
        self.assertAlmostEqual(p["monto"], 8433218.0)

    def test_sin_cobertura_post_2023(self):
        # Después del último piso (31/08/2023) no hay cobertura aún
        c = self._calc("01/01/2024")
        self.assertIsNone(c.piso_vigente())
        self.assertAlmostEqual(c.piso_aplicable(), 0.0)


class TestPisoAplicable(unittest.TestCase):
    def test_proporcional_a_incapacidad(self):
        # Dto. 1694/09 monto=80000, incap=22% → 17600
        c = CalculadoraLRT(
            caratula="u", fecha_nacimiento="21/08/1946",
            fecha_accidente="31/08/2011", fecha_sentencia="31/08/2011",
            incapacidad_pct=22.0, ibm_historico=100.0,
            ripte_serie=SEED, pisos=PISOS,
        )
        self.assertAlmostEqual(c.piso_aplicable(), 80000.0 * 0.22, places=4)

    def test_sin_piso_da_cero(self):
        c = CalculadoraLRT(
            caratula="u", fecha_nacimiento="01/01/1970",
            fecha_accidente="01/01/2024", fecha_sentencia="01/01/2024",
            incapacidad_pct=50.0, ibm_historico=1000.0,
            ripte_serie=SEED, pisos=PISOS,
        )
        self.assertAlmostEqual(c.piso_aplicable(), 0.0)


class TestCapitalFinal(unittest.TestCase):
    def test_aplica_subtotal_cuando_es_mayor(self):
        # IBM alto → subtotal >> piso
        c = CalculadoraLRT(
            caratula="u", fecha_nacimiento="21/08/1946",
            fecha_accidente="31/08/2011", fecha_sentencia="01/06/2024",
            incapacidad_pct=22.0, ibm_historico=9179.12,
            ripte_serie=SEED, pisos=PISOS,
        )
        self.assertAlmostEqual(c.capital_final(), c.subtotal_lrt(), places=4)
        self.assertFalse(c.desglose()["aplica_piso"])

    def test_aplica_piso_cuando_es_mayor(self):
        # IBM muy bajo + sentencia=accidente → subtotal < piso Dto.1694/09
        # Con IBM=800, incap=50%, edad=50: subtotal=33072, piso=40000
        ripte_mini = {"2010-01-01": SEED["2010-01-01"]}
        c = CalculadoraLRT(
            caratula="u", fecha_nacimiento="15/01/1960",
            fecha_accidente="15/01/2010", fecha_sentencia="15/01/2010",
            incapacidad_pct=50.0, ibm_historico=800.0,
            ripte_serie=ripte_mini, pisos=PISOS,
        )
        self.assertGreater(c.piso_aplicable(), c.subtotal_lrt())
        self.assertAlmostEqual(c.capital_final(), c.piso_aplicable(), places=4)
        self.assertTrue(c.desglose()["aplica_piso"])


class TestConstructorValidacion(unittest.TestCase):
    def test_ninguno_raises(self):
        with self.assertRaises(ValueError):
            CalculadoraLRT(
                caratula="u", fecha_nacimiento="01/01/1970",
                fecha_accidente="01/01/2020", fecha_sentencia="01/01/2024",
                incapacidad_pct=20.0,
                ripte_serie=SEED, pisos=PISOS,
            )

    def test_ambos_raises(self):
        with self.assertRaises(ValueError):
            CalculadoraLRT(
                caratula="u", fecha_nacimiento="01/01/1970",
                fecha_accidente="01/01/2020", fecha_sentencia="01/01/2024",
                incapacidad_pct=20.0,
                ibm_historico=5000.0,
                salarios=[{"periodo": "01/2020", "importe": 5000.0}],
                ripte_serie=SEED, pisos=PISOS,
            )

    def test_ripte_faltante_raises(self):
        with self.assertRaises(ValueError):
            c = CalculadoraLRT(
                caratula="u", fecha_nacimiento="01/01/1970",
                fecha_accidente="01/06/1980",  # fecha anterior al seed
                fecha_sentencia="01/01/2024",
                incapacidad_pct=20.0, ibm_historico=5000.0,
                ripte_serie=SEED, pisos=PISOS,
            )
            c.ibm_actualizado()  # dispara el acceso a RIPTE


# ---------------------------------------------------------------------------
# Tests de regresión — Caso A y Caso B completos
#
# Inputs del Caso A: DISEÑO_LRT.md §6
# Inputs del Caso B: planilla_original.xlsx hoja ACTUALIZACION (inputs crudos)
#
# Los expected values se calculan con la implementación CORRECTA de la
# fórmula (no con la planilla, que tiene bugs documentados en DISEÑO §2.5).
# ---------------------------------------------------------------------------

class TestRegresionCasoA(unittest.TestCase):
    """
    Caso A — IBM directo.
    nacimiento=1946-08-21, accidente=2011-08-31, sentencia=2024-06-01,
    IBM=9179.12, incap=22%.
    """
    def setUp(self):
        self.calc = CalculadoraLRT(
            caratula="Regresion A",
            fecha_nacimiento="21/08/1946",
            fecha_accidente="31/08/2011",
            fecha_sentencia="01/06/2024",
            incapacidad_pct=22.0,
            ibm_historico=9179.12,
            ripte_serie=SEED,
            pisos=PISOS,
        )

    def test_edad(self):
        self.assertEqual(self.calc.edad_al_accidente(), 65)

    def test_coef_edad(self):
        self.assertAlmostEqual(self.calc.coef_edad(), 1.0, places=8)

    def test_ibm_actualizado(self):
        self.assertAlmostEqual(self.calc.ibm_actualizado(), 1_757_067.2064, delta=TOL)

    def test_indemnizacion_base(self):
        self.assertAlmostEqual(self.calc.indemnizacion_base(), 20_487_403.6267, delta=TOL)

    def test_subtotal(self):
        self.assertAlmostEqual(self.calc.subtotal_lrt(), 24_584_884.3521, delta=TOL)

    def test_piso_aplicable(self):
        # Piso Dto. 1694/09: 80000 × 0.22 = 17600
        self.assertAlmostEqual(self.calc.piso_aplicable(), 17_600.0, delta=TOL)

    def test_capital_final_es_subtotal(self):
        self.assertAlmostEqual(self.calc.capital_final(), 24_584_884.3521, delta=TOL)


class TestRegresionCasoB(unittest.TestCase):
    """
    Caso B — IBM por promedio de 12 salarios.
    Inputs salariales: planilla_original.xlsx ACTUALIZACION!A5:B16.
    nacimiento=1957-05-28, accidente=2015-06-05, sentencia=2015-06-05 (coef=1),
    incap=33.03%.

    Los 3 meses con RIPTE erróneo en la planilla (sep/oct/nov 2014) se corrigen
    aquí usando los valores reales del seed.
    """
    SALARIOS = [
        {"periodo": "07/2014", "importe": 11894.28},
        {"periodo": "08/2014", "importe": 14256.50},
        {"periodo": "09/2014", "importe": 14386.74},
        {"periodo": "10/2014", "importe": 15548.23},
        {"periodo": "11/2014", "importe": 12588.84},
        {"periodo": "12/2014", "importe": 21498.67},
        {"periodo": "01/2015", "importe": 14848.98},
        {"periodo": "02/2015", "importe": 21514.81},
        {"periodo": "03/2015", "importe": 19874.73},
        {"periodo": "04/2015", "importe": 23040.50},
        {"periodo": "05/2015", "importe": 16522.10},
        {"periodo": "06/2015", "importe": 17983.72},
    ]

    def setUp(self):
        self.calc = CalculadoraLRT(
            caratula="Regresion B",
            fecha_nacimiento="28/05/1957",
            fecha_accidente="05/06/2015",
            fecha_sentencia="05/06/2015",
            incapacidad_pct=33.03,
            salarios=self.SALARIOS,
            ripte_serie=SEED,
            pisos=PISOS,
        )

    def test_edad(self):
        self.assertEqual(self.calc.edad_al_accidente(), 58)

    def test_coef_ripte_es_uno(self):
        # sentencia = accidente → coef debe ser 1.0 exacto
        self.assertAlmostEqual(self.calc.coef_ripte(), 1.0, places=10)

    def test_ibm_actualizado(self):
        self.assertAlmostEqual(self.calc.ibm_actualizado(), 19_540.5665, delta=TOL)

    def test_indemnizacion_base(self):
        self.assertAlmostEqual(self.calc.indemnizacion_base(), 383_360.1412, delta=TOL)

    def test_subtotal(self):
        self.assertAlmostEqual(self.calc.subtotal_lrt(), 460_032.1694, delta=TOL)

    def test_piso_vigente(self):
        p = self.calc.piso_vigente()
        self.assertIsNotNone(p)
        self.assertIn("6/2015", p["norma"])

    def test_capital_final_es_subtotal(self):
        # subtotal (460032) > piso (235661) → capital = subtotal
        self.assertAlmostEqual(self.calc.capital_final(), 460_032.1694, delta=TOL)


if __name__ == "__main__":
    unittest.main(verbosity=2)
