"""
Catálogo de normas citadas por la app, con enlace oficial a InfoLEG.
Única fuente de verdad de estos textos — no hardcodear URLs de InfoLEG
en las páginas de liquidación (Despido / LRT); esas ahora remiten a la
Biblioteca de Leyes (pages/3_Biblioteca_Legal.py).
"""

NORMAS = [
    {
        "clave": "lct",
        "nombre": "Ley 20.744 (LCT) — Contrato de Trabajo",
        "descripcion": "Régimen general del contrato de trabajo: indemnización por antigüedad (art. 245), "
                       "preaviso (art. 232), integración del mes de despido (art. 233), certificados de "
                       "trabajo (art. 80).",
        "url": "https://servicios.infoleg.gob.ar/infolegInternet/verNorma.do?id=25552",
        "area": "despido",
    },
    {
        "clave": "ley_25323",
        "nombre": "Ley 25.323 — Indemnizaciones Laborales",
        "descripcion": "Incremento de las indemnizaciones por relación no registrada (art. 1°) y por falta "
                       "de pago en término de las indemnizaciones (art. 2°).",
        "url": "https://servicios.infoleg.gob.ar/infolegInternet/verNorma.do?id=64555",
        "area": "despido",
    },
    {
        "clave": "ley_24013",
        "nombre": "Ley 24.013 — Ley de Empleo",
        "descripcion": "Regularización del empleo no registrado: relación no registrada (art. 8°), registro "
                       "tardío (art. 9°), remuneración no registrada (art. 10) y despido tras intimación "
                       "(art. 15).",
        "url": "https://servicios.infoleg.gob.ar/infolegInternet/verNorma.do?id=412",
        "area": "despido",
    },
    {
        "clave": "dto_34_2019",
        "nombre": "Decreto 34/2019 — Doble Indemnización",
        "descripcion": "Declara la emergencia ocupacional pública y duplica las indemnizaciones por despido "
                       "sin causa durante su vigencia.",
        "url": "https://servicios.infoleg.gob.ar/infolegInternet/anexos/330000-334999/333435/norma.htm",
        "area": "despido",
    },
    {
        "clave": "ley_24557",
        "nombre": "Ley 24.557 — Riesgos del Trabajo",
        "descripcion": "Régimen de prestaciones dinerarias y en especie por incapacidad laboral permanente "
                       "derivada de accidentes de trabajo o enfermedades profesionales (art. 14.2.a).",
        "url": "https://servicios.infoleg.gob.ar/infolegInternet/verNorma.do?id=27971",
        "area": "lrt",
    },
    {
        "clave": "ley_26773",
        "nombre": "Ley 26.773 — Reparación de Daños Derivados de Riesgos del Trabajo",
        "descripcion": "Régimen de ordenamiento de la reparación de daños derivados de accidentes de trabajo "
                       "y enfermedades profesionales; adicional del 20% (art. 3°).",
        "url": "https://servicios.infoleg.gob.ar/infolegInternet/verNorma.do?id=203798",
        "area": "lrt",
    },
]
