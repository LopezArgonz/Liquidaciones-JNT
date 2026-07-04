import re
import streamlit as st

VERSION = "2.0"

# ---------------------------------------------------------------------------
# Sistema de diseño institucional — Justicia Nacional del Trabajo
# ---------------------------------------------------------------------------
# Paleta: marfil / azul medianoche / dorado judicial. Tipografía serif en
# títulos, sans en cuerpo. Toda la iconografía es SVG monocromo (currentColor),
# sin emojis. Pensado para verse bien con el tema claro de .streamlit/config.toml.

CSS_BASE = """
<style>
:root {
    --jnt-azul: #1F2A38;
    --jnt-azul-claro: #2C3E50;
    --jnt-dorado: #B8860B;
    --jnt-dorado-suave: #C9A227;
    --jnt-marfil: #FAF8F3;
    --jnt-marfil-oscuro: #EFEBE2;
    --jnt-borde: #D8D2C4;
    --jnt-exito: #2E6B4F;
    --jnt-alerta: #8C2F39;
    --jnt-serif: Georgia, 'Times New Roman', serif;
    --jnt-sans: 'Segoe UI', system-ui, sans-serif;
}

h1, h2, h3, h4 {
    font-family: var(--jnt-serif) !important;
    color: var(--jnt-azul) !important;
    font-weight: 600 !important;
}

.stApp, p, span, div, label {
    font-family: var(--jnt-sans);
}

.stButton>button {
    background-color: var(--jnt-azul);
    color: var(--jnt-marfil);
    border-radius: 4px;
    width: 100%;
    border: 1px solid var(--jnt-azul);
    padding: 0.5rem 1rem;
    font-weight: 500;
    transition: all 0.2s ease;
}
.stButton>button:hover {
    background-color: var(--jnt-azul-claro);
    border-color: var(--jnt-dorado);
    color: var(--jnt-marfil);
}
.stButton>button:active {
    transform: translateY(1px);
}
.stButton>button[kind="primary"] {
    background-color: var(--jnt-dorado);
    border-color: var(--jnt-dorado);
    color: var(--jnt-azul);
}
.stButton>button[kind="primary"]:hover {
    background-color: var(--jnt-dorado-suave);
}

/* Ocultar el menú hamburguesa y el footer "Made with Streamlit" */
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
/* El botón de colapso del sidebar permanece accesible */
[data-testid="stSidebarCollapsedControl"] { visibility: visible; }

/* ── Encabezado institucional ──────────────────────────────────────── */
.jnt-encabezado { margin-bottom: 1.25rem; }
.jnt-encabezado-fila {
    display: flex;
    align-items: center;
    gap: 1rem;
}
.jnt-encabezado-icono { color: var(--jnt-dorado); flex-shrink: 0; }
.jnt-leyenda {
    font-family: var(--jnt-sans);
    font-size: 0.7rem;
    letter-spacing: 0.14em;
    color: var(--jnt-azul-claro);
    text-transform: uppercase;
    margin-bottom: 0.15rem;
}
.jnt-titulo {
    margin: 0 !important;
    padding: 0 !important;
    font-size: 2.1rem !important;
    line-height: 1.15 !important;
}
.jnt-subtitulo {
    margin: 0.15rem 0 0 0 !important;
    color: var(--jnt-azul-claro);
    font-weight: normal;
    font-size: 1rem;
}
.jnt-filete {
    margin-top: 0.9rem;
    border-top: 2px solid var(--jnt-azul);
    border-bottom: 1px solid var(--jnt-dorado);
    height: 3px;
}

/* ── Tarjetas métrica ───────────────────────────────────────────────── */
.jnt-metrica {
    background: var(--jnt-marfil);
    border: 1px solid var(--jnt-borde);
    border-top: 3px solid var(--jnt-dorado);
    border-radius: 4px;
    padding: 0.85rem 1rem;
    text-align: center;
}
.jnt-metrica-exito { border-top-color: var(--jnt-exito); }
.jnt-metrica-alerta { border-top-color: var(--jnt-alerta); }
.jnt-metrica-label {
    font-size: 0.72rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--jnt-azul-claro);
    margin-bottom: 0.3rem;
}
.jnt-metrica-valor {
    font-family: var(--jnt-serif);
    font-size: 1.5rem;
    font-weight: 600;
    color: var(--jnt-azul);
}

/* ── Chip de norma ──────────────────────────────────────────────────── */
.jnt-chip {
    display: inline-block;
    border: 1px solid var(--jnt-dorado);
    background: var(--jnt-marfil);
    color: var(--jnt-azul);
    border-radius: 3px;
    padding: 0.05rem 0.5rem;
    font-size: 0.75rem;
    text-decoration: none;
    margin: 0.1rem 0.2rem 0.1rem 0;
    white-space: nowrap;
}
.jnt-chip:hover { background: var(--jnt-marfil-oscuro); }

/* ── Sello de fuente ────────────────────────────────────────────────── */
.jnt-sello {
    display: inline-block;
    border: 2px double var(--jnt-azul);
    color: var(--jnt-azul-claro);
    background: var(--jnt-marfil);
    padding: 0.4rem 0.9rem;
    font-size: 0.72rem;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    transform: rotate(-1deg);
    border-radius: 2px;
    margin: 0.5rem 0;
}

/* ── Recuadro de monto en letras ────────────────────────────────────── */
.jnt-monto-letras {
    font-family: var(--jnt-serif);
    background: var(--jnt-marfil);
    border-left: 3px solid var(--jnt-dorado);
    padding: 0.9rem 1.2rem;
    font-size: 0.95rem;
    color: var(--jnt-azul);
    font-style: italic;
    margin: 0.75rem 0;
}

/* ── Alertas con estilo del design system ──────────────────────────── */
.jnt-alerta-caja {
    border: 1px solid var(--jnt-alerta);
    background: rgba(140, 47, 57, 0.08);
    color: var(--jnt-alerta);
    border-radius: 4px;
    padding: 0.6rem 0.9rem;
    font-size: 0.9rem;
    margin: 0.4rem 0;
}

/* ── Tarjeta de login (mesa de entradas) ────────────────────────────── */
.jnt-login-card {
    max-width: 440px;
    margin: 2rem auto 1.5rem auto;
    text-align: center;
    padding: 2rem 1.5rem 1.5rem 1.5rem;
    background: var(--jnt-marfil);
    border: 2px solid var(--jnt-azul);
    outline: 1px solid var(--jnt-dorado);
    outline-offset: -6px;
    border-radius: 6px;
}
.jnt-login-icono { color: var(--jnt-dorado); margin-bottom: 0.4rem; }
.jnt-login-titulo { font-size: 1.6rem !important; margin: 0.25rem 0 !important; }
.jnt-login-leyenda {
    font-size: 0.72rem;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: var(--jnt-azul-claro);
    margin-top: 0.25rem;
}

/* ── Tarjetas-herramienta (portada) ─────────────────────────────────── */
.jnt-tarjeta-herr {
    position: relative;
    border: 1px solid var(--jnt-borde);
    border-radius: 6px;
    padding: 1.9rem 1.25rem 1.25rem 1.25rem;
    background: var(--jnt-marfil);
    text-align: center;
    transition: box-shadow 0.2s ease, transform 0.2s ease;
    margin-bottom: 0.5rem;
}
.jnt-tarjeta-herr:hover {
    box-shadow: 0 6px 16px rgba(31, 42, 56, 0.15);
    transform: translateY(-2px);
}
.jnt-tarjeta-etiqueta {
    position: absolute;
    top: -0.6rem;
    left: 50%;
    transform: translateX(-50%);
    background: var(--jnt-dorado);
    color: var(--jnt-azul);
    font-size: 0.65rem;
    letter-spacing: 0.1em;
    padding: 0.15rem 0.7rem;
    border-radius: 3px;
    font-weight: 700;
    white-space: nowrap;
}
.jnt-tarjeta-icono { color: var(--jnt-azul); margin: 0.5rem 0; }
.jnt-tarjeta-titulo {
    font-family: var(--jnt-serif);
    font-size: 1.2rem;
    color: var(--jnt-azul);
    font-weight: 600;
    margin-bottom: 0.3rem;
}
.jnt-tarjeta-desc { font-size: 0.85rem; color: var(--jnt-azul-claro); }

/* ── Impresión ──────────────────────────────────────────────────────── */
@media print {
    [data-testid="stSidebar"], [data-testid="stHeader"],
    .stButton, #MainMenu, footer {
        display: none !important;
    }
    .stApp { background: white !important; }
}
</style>
"""

CSS_TABLA = """
<style>
.table-jnt {
    width: 100% !important;
    border-collapse: collapse !important;
    font-family: var(--jnt-sans, 'Segoe UI', sans-serif);
    font-size: 0.9rem;
    color: var(--jnt-azul, inherit) !important;
}
.table-jnt thead tr th {
    text-align: left !important;
    background-color: var(--jnt-azul, #1F2A38);
    color: var(--jnt-marfil, #FAF8F3) !important;
    padding: 10px 12px;
    font-weight: 600;
}
.table-jnt thead tr th:last-child { text-align: right !important; }
.table-jnt tbody tr td {
    padding: 7px 12px;
    border-bottom: 1px solid var(--jnt-borde, rgba(128,128,128,0.2));
    color: inherit !important;
}
.table-jnt tbody tr:nth-child(even) td {
    background-color: rgba(184, 134, 11, 0.04);
}
.table-jnt tbody tr td:last-child {
    text-align: right !important;
    white-space: nowrap;
    font-variant-numeric: tabular-nums;
}
.table-jnt tbody tr.jnt-seccion td {
    background-color: var(--jnt-marfil-oscuro, #EFEBE2);
    font-weight: 700;
    letter-spacing: 0.03em;
    text-transform: uppercase;
    font-size: 0.78rem;
    color: var(--jnt-azul, #1F2A38);
}
.table-jnt tbody tr.jnt-seccion td:last-child {
    text-align: left !important;
}
.table-jnt tbody tr:last-child td {
    font-weight: bold;
    background-color: var(--jnt-marfil-oscuro, rgba(128,128,128,0.1));
    border-top: 3px double var(--jnt-azul, #1F2A38);
}
.table-jnt tr.separador td {
    border-top: 2px solid var(--jnt-dorado, #B8860B);
    font-weight: bold;
    background-color: rgba(184, 134, 11, 0.08);
}
</style>
"""


def aplicar_estilos():
    st.markdown(CSS_BASE, unsafe_allow_html=True)


def aplicar_estilos_tabla():
    st.markdown(CSS_TABLA, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Iconografía SVG monocroma (currentColor) — reemplaza los emojis de la UI
# ---------------------------------------------------------------------------

def icono_balanza(size=28):
    """⚖ Balanza de la justicia."""
    return f"""<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none"
        stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
        <line x1="12" y1="3" x2="12" y2="21"/>
        <line x1="5" y1="7" x2="19" y2="7"/>
        <path d="M5 7 L2 13 a3.2 3.2 0 0 0 6 0 Z"/>
        <path d="M19 7 L16 13 a3.2 3.2 0 0 0 6 0 Z"/>
        <line x1="9" y1="21" x2="15" y2="21"/>
    </svg>"""


def icono_legajo(size=24):
    """📄 / 📋 Legajo / expediente."""
    return f"""<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none"
        stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
        <path d="M6 2.5h9l3 3V21a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V3.5a1 1 0 0 1 1-1Z"/>
        <path d="M15 2.5V6h3"/>
        <line x1="8" y1="10" x2="16" y2="10"/>
        <line x1="8" y1="13.5" x2="16" y2="13.5"/>
        <line x1="8" y1="17" x2="13" y2="17"/>
    </svg>"""


def icono_cruz(size=24):
    """🏥 Cruz sanitaria (Riesgos del Trabajo)."""
    return f"""<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none"
        stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
        <path d="M4 10V6a2 2 0 0 1 2-2h4V2h4v2h4a2 2 0 0 1 2 2v4h2v4h-2v4a2 2 0 0 1-2 2h-4v2h-4v-2H6a2 2 0 0 1-2-2v-4H2v-4Z"/>
        <line x1="12" y1="8" x2="12" y2="16"/>
        <line x1="8" y1="12" x2="16" y2="12"/>
    </svg>"""


def icono_columna(size=24):
    """Columna de tribunal."""
    return f"""<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none"
        stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
        <line x1="3" y1="3" x2="21" y2="3"/>
        <line x1="5" y1="6" x2="19" y2="6"/>
        <line x1="7" y1="6" x2="7" y2="18"/>
        <line x1="12" y1="6" x2="12" y2="18"/>
        <line x1="17" y1="6" x2="17" y2="18"/>
        <line x1="4" y1="21" x2="20" y2="21"/>
        <line x1="5" y1="18" x2="19" y2="18"/>
    </svg>"""


def icono_toga(size=20):
    """Persona / toga — usuario en el sidebar."""
    return f"""<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none"
        stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="7" r="3.2"/>
        <path d="M5 21c0-4.5 3-7 7-7s7 2.5 7 7"/>
        <line x1="12" y1="14" x2="12" y2="21"/>
    </svg>"""


def icono_descarga(size=20):
    """📥 Descarga (exportar Excel)."""
    return f"""<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none"
        stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
        <path d="M12 3v12"/>
        <path d="M7 10l5 5 5-5"/>
        <path d="M4 19h16"/>
    </svg>"""


# ---------------------------------------------------------------------------
# Componentes del design system
# ---------------------------------------------------------------------------

def encabezado_institucional(titulo, subtitulo=""):
    """Banda superior: balanza + título serif + leyenda + filete doble (azul/dorado)."""
    st.markdown(f"""
    <div class="jnt-encabezado">
      <div class="jnt-encabezado-fila">
        <div class="jnt-encabezado-icono">{icono_balanza(40)}</div>
        <div>
          <div class="jnt-leyenda">Poder Judicial de la Nación &middot; Justicia Nacional del Trabajo</div>
          <h1 class="jnt-titulo">{titulo}</h1>
          {f'<p class="jnt-subtitulo">{subtitulo}</p>' if subtitulo else ''}
        </div>
      </div>
      <div class="jnt-filete"></div>
    </div>
    """, unsafe_allow_html=True)


def tarjeta_metrica(label, valor, tono="neutro"):
    """Tarjeta de resultado con borde superior de 3px dorado (o exito/alerta)."""
    clase_tono = {"exito": "jnt-metrica-exito", "alerta": "jnt-metrica-alerta"}.get(tono, "")
    st.markdown(f"""
    <div class="jnt-metrica {clase_tono}">
        <div class="jnt-metrica-label">{label}</div>
        <div class="jnt-metrica-valor">{valor}</div>
    </div>
    """, unsafe_allow_html=True)


def chip_norma(texto, url=None):
    """Badge dorado para citar una norma. Devuelve el HTML (para insertar inline)."""
    if url:
        return f'<a class="jnt-chip" href="{url}" target="_blank" rel="noopener">{texto}</a>'
    return f'<span class="jnt-chip">{texto}</span>'


def sello_fuente(texto):
    """Caja tipo 'sello' rotada, para citar la fuente de un índice (IPC, RIPTE)."""
    st.markdown(f'<div class="jnt-sello">{texto}</div>', unsafe_allow_html=True)


def caja_monto_letras(texto):
    """Recuadro serif con el monto en letras, listo para copiar a la sentencia."""
    st.markdown(f'<div class="jnt-monto-letras">&ldquo;{texto}&rdquo;</div>', unsafe_allow_html=True)


def alerta(texto):
    """Alerta bordó del design system (reemplaza el rojo default de Streamlit)."""
    st.markdown(f'<div class="jnt-alerta-caja">{texto}</div>', unsafe_allow_html=True)


def mostrar_footer():
    st.markdown(f"""
    <div style="text-align:center; margin-top:2rem;">
        <div style="border-top:1px solid var(--jnt-dorado, #B8860B); margin-bottom:0.6rem;"></div>
        <div style="color:#888; font-size:0.78rem; letter-spacing:0.04em;">
            &sect; Justicia Nacional del Trabajo — Sistema de Liquidaciones<br>
            Desarrollado por <b>Gastón López Argonz</b> · v{VERSION}
        </div>
    </div>
    """, unsafe_allow_html=True)


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
