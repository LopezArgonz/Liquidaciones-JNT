import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils import monto_en_letras, sanitizar_nombre


class TestSanitizarNombre(unittest.TestCase):
    def test_espacios_a_guion_bajo(self):
        self.assertEqual(sanitizar_nombre("Garcia c Perez"), "Garcia_c_Perez")

    def test_caracteres_especiales(self):
        self.assertEqual(sanitizar_nombre("Expte. Nro 1234/2020"), "Expte__Nro_1234_2020")

    def test_ya_limpio(self):
        self.assertEqual(sanitizar_nombre("Caso_Simple"), "Caso_Simple")


class TestMontoEnLetras(unittest.TestCase):
    def test_cero(self):
        self.assertEqual(monto_en_letras(0), "PESOS CERO CON 00/100")

    def test_uno(self):
        self.assertEqual(monto_en_letras(1), "PESOS UNO CON 00/100")

    def test_veintiuno(self):
        self.assertEqual(monto_en_letras(21), "PESOS VEINTIUNO CON 00/100")

    def test_cien(self):
        self.assertEqual(monto_en_letras(100), "PESOS CIEN CON 00/100")

    def test_ciento_uno(self):
        self.assertEqual(monto_en_letras(101), "PESOS CIENTO UNO CON 00/100")

    def test_mil(self):
        self.assertEqual(monto_en_letras(1000), "PESOS MIL CON 00/100")

    def test_un_millon(self):
        self.assertEqual(monto_en_letras(1_000_000), "PESOS UN MILLÓN CON 00/100")

    def test_decimales(self):
        self.assertEqual(monto_en_letras(0.5), "PESOS CERO CON 50/100")

    def test_ejemplo_completo(self):
        self.assertEqual(
            monto_en_letras(1_234_567.89),
            "PESOS UN MILLÓN DOSCIENTOS TREINTA Y CUATRO MIL QUINIENTOS SESENTA Y SIETE CON 89/100",
        )

    def test_veintiun_mil_apocope(self):
        self.assertEqual(monto_en_letras(21_000), "PESOS VEINTIÚN MIL CON 00/100")

    def test_treinta_y_un_millones_apocope(self):
        self.assertEqual(monto_en_letras(31_000_000), "PESOS TREINTA Y UN MILLONES CON 00/100")

    def test_redondeo_centavos_a_100(self):
        # 99.999999... debe redondear a 100.00, no a "99 CON 100/100"
        self.assertEqual(monto_en_letras(99.999), "PESOS CIEN CON 00/100")

    def test_dos_mil_millones(self):
        self.assertEqual(monto_en_letras(2_000_000_000), "PESOS DOS MIL MILLONES CON 00/100")


if __name__ == "__main__":
    unittest.main(verbosity=2)
