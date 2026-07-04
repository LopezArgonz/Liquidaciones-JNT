import re
import streamlit as st

CSS_BASE = """
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
</style>
"""

CSS_TABLA = """
<style>
.table-jnt {
    width: 100% !important;
    border-collapse: collapse !important;
    font-family: sans-serif;
    font-size: 0.9rem;
    color: inherit !important;
}
.table-jnt thead tr th {
    text-align: center !important;
    background-color: rgba(128, 128, 128, 0.15);
    padding: 10px;
    border-bottom: 2px solid rgba(128, 128, 128, 0.3);
    color: inherit !important;
}
.table-jnt tbody tr td {
    padding: 8px 10px;
    border-bottom: 1px solid rgba(128, 128, 128, 0.1);
    color: inherit !important;
}
.table-jnt tbody tr td:nth-child(2) {
    text-align: right !important;
    white-space: nowrap;
}
.table-jnt tbody tr:last-child {
    font-weight: bold;
    background-color: rgba(128, 128, 128, 0.1);
    border-top: 2px solid rgba(128, 128, 128, 0.3);
}
.table-jnt tr.separador td {
    border-top: 2px solid rgba(44, 62, 80, 0.3);
    font-weight: bold;
    background-color: rgba(44, 62, 80, 0.05);
}
</style>
"""


def aplicar_estilos():
    st.markdown(CSS_BASE, unsafe_allow_html=True)


def aplicar_estilos_tabla():
    st.markdown(CSS_TABLA, unsafe_allow_html=True)


def mostrar_footer():
    st.markdown(
        "<div style='text-align: center; color: #888; font-size: 0.85rem; margin-top: 20px;'>"
        "Desarrollado por: <br><b>Gastón López Argonz</b>"
        "</div>",
        unsafe_allow_html=True,
    )


def sanitizar_nombre(nombre):
    """Sanitiza un nombre para usarlo como nombre de archivo (sin espacios ni caracteres especiales)."""
    return re.sub(r'[^\w\s-]', '_', nombre).strip().replace(' ', '_')


_UNIDADES = ["CERO", "UNO", "DOS", "TRES", "CUATRO", "CINCO", "SEIS", "SIETE", "OCHO", "NUEVE",
             "DIEZ", "ONCE", "DOCE", "TRECE", "CATORCE", "QUINCE", "DIECISÉIS", "DIECISIETE",
             "DIECIOCHO", "DIECINUEVE", "VEINTE"]
_DECENA_20 = ["VEINTE", "VEINTIUNO", "VEINTIDÓS", "VEINTITRÉS", "VEINTICUATRO", "VEINTICINCO",
              "VEINTISÉIS", "VEINTISIETE", "VEINTIOCHO", "VEINTINUEVE"]
_DECENAS = {3: "TREINTA", 4: "CUARENTA", 5: "CINCUENTA", 6: "SESENTA",
            7: "SETENTA", 8: "OCHENTA", 9: "NOVENTA"}
_CENTENAS = ["", "CIENTO", "DOSCIENTOS", "TRESCIENTOS", "CUATROCIENTOS", "QUINIENTOS",
             "SEISCIENTOS", "SETECIENTOS", "OCHOCIENTOS", "NOVECIENTOS"]


def _apocope_uno(texto):
    """Convierte la terminación 'UNO' en 'UN' (apócope) para preceder MIL/MILLÓN/MILLONES."""
    if texto == "UNO":
        return "UN"
    if texto.endswith("VEINTIUNO"):
        return texto[: -len("VEINTIUNO")] + "VEINTIÚN"
    if texto.endswith(" Y UNO"):
        return texto[: -len(" Y UNO")] + " Y UN"
    return texto


def _decena_a_letras(n):
    """Convierte un número de 1 a 99 a letras."""
    if n <= 20:
        return _UNIDADES[n]
    if n < 30:
        return _DECENA_20[n - 20]
    decena, unidad = divmod(n, 10)
    texto = _DECENAS[decena]
    if unidad:
        texto += " Y " + _UNIDADES[unidad]
    return texto


def _centena_a_letras(n):
    """Convierte un número de 1 a 999 a letras."""
    if n == 100:
        return "CIEN"
    centena, resto = divmod(n, 100)
    partes = []
    if centena:
        partes.append(_CENTENAS[centena])
    if resto:
        partes.append(_decena_a_letras(resto))
    return " ".join(partes)


def _entero_a_letras(n):
    """Convierte un entero no negativo (hasta 999 miles de millones) a letras."""
    if n == 0:
        return "CERO"

    miles_de_millones, resto = divmod(n, 1_000_000_000)
    millones, resto = divmod(resto, 1_000_000)
    miles, unidades = divmod(resto, 1000)

    partes = []
    if miles_de_millones:
        if miles_de_millones == 1:
            partes.append("MIL MILLONES")
        else:
            partes.append(_apocope_uno(_centena_a_letras(miles_de_millones)) + " MIL MILLONES")
    if millones:
        if millones == 1:
            partes.append("UN MILLÓN")
        else:
            partes.append(_apocope_uno(_centena_a_letras(millones)) + " MILLONES")
    if miles:
        if miles == 1:
            partes.append("MIL")
        else:
            partes.append(_apocope_uno(_centena_a_letras(miles)) + " MIL")
    if unidades:
        partes.append(_centena_a_letras(unidades))

    return " ".join(partes)


def monto_en_letras(valor):
    """
    Convierte un monto en pesos a letras, estilo sentencia judicial.
    Ej.: 1_234_567.89 -> "PESOS UN MILLÓN DOSCIENTOS TREINTA Y CUATRO MIL
    QUINIENTOS SESENTA Y SIETE CON 89/100"
    """
    valor = round(float(valor), 2)
    entero = int(valor)
    centavos = round((valor - entero) * 100)
    if centavos == 100:  # corrige el redondeo de punto flotante (p.ej. 99.999999 -> 100)
        entero += 1
        centavos = 0
    return f"PESOS {_entero_a_letras(entero)} CON {centavos:02d}/100"
