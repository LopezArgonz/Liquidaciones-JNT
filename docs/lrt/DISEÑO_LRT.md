# Diseño — Módulo LRT (Ley 24.557) dentro de Liquidador_Tribunal

> Especificación funcional y plan de implementación del módulo "Riesgos del Trabajo" para integrarlo al proyecto **Liquidador_Tribunal** existente.
> Antes de leer este documento, leer `CLAUDE.md` en la raíz del proyecto para entender las convenciones.

---

## 1. Contexto

El proyecto ya tiene una calculadora funcional de **Liquidación por Despido** que implementa:

- Indemnización art. 245 LCT (con Vizzoti)
- Multas: 25.323, 24.013 (arts. 8, 9, 10, 15), art. 80 LCT, Dto. 34/2019
- Actualización por IPC INDEC (vía API datos.gob.ar) + interés puro 3% anual
- Exportación a Excel con XlsxWriter

Falta la calculadora de **Riesgos del Trabajo (Ley 24.557)**, que está como placeholder en `pages/2_Riesgos_Trabajo.py`. Este documento especifica qué hay que construir.

---

## 2. Análisis funcional de la planilla original

La planilla `docs/lrt/planilla_original.xlsx` tiene 4 hojas que se encadenan. La replicamos así:

### 2.1 Caso A — IBM conocido (hoja `FORMULA`)

Inputs típicos:

| Campo | Ejemplo | Notas |
|---|---|---|
| Fecha de nacimiento | 1946-08-21 | Para edad al accidente |
| Fecha del accidente | 2011-08-31 | Define RIPTE de origen |
| IBM histórico | 9.179,12 | Provisto por la pericia / liquidación |
| % incapacidad | 22% | De la pericia |
| Fecha de sentencia | 2024-06-01 | Define RIPTE de cierre |

Cálculo:

```
edad           = años_completos(nacimiento → accidente)
coef_edad      = 65 / edad
ripte_acc      = obtener_ripte(fecha_accidente)
ripte_sent     = obtener_ripte(fecha_sentencia)
coef_RIPTE     = ripte_sent / ripte_acc
ibm_actual     = ibm_historico * coef_RIPTE
indemniz_base  = 53 * ibm_actual * coef_edad * (incap_pct / 100)
art3_26773     = indemniz_base * 0.20
subtotal       = indemniz_base + art3_26773

piso_aplic     = piso_vigente(fecha_accidente).monto * (incap_pct / 100)
capital_final  = max(subtotal, piso_aplic)
```

### 2.2 Caso B — IBM por promedio de salarios (hoja `ACTUALIZACION`)

Cuando la pericia no da un IBM directo y hay 12 salarios mensuales previos al accidente:

```
Para cada salario s_i del mes m_i:
    coef_i = ripte(mes_accidente) / ripte(m_i)
    s_i_actualizado = s_i * coef_i

ibm_a_fecha_accidente = sum(s_i_actualizado) / len(salarios)
```

**Importante:** ese IBM ya está expresado al valor del mes del accidente. Para llevarlo al mes de la sentencia hay que aplicarle todavía el coeficiente RIPTE accidente→sentencia. **No se actualiza dos veces** — se actualiza una sola vez de mes_salario a mes_sentencia (lo cual matemáticamente equivale a: actualizar a mes_accidente y después a mes_sentencia).

Una vez calculado el IBM, se aplica la misma fórmula del caso A.

### 2.3 Pisos legales (Ley 26.773)

23 entradas con `desde`, `hasta`, `monto`, `norma` ya extraídas a `data/pisos.json`. Cubren desde Dto. 1694/09 hasta Res. SRT 12/2023. Cuando salga una nueva resolución, se agrega una entrada al JSON sin tocar código.

### 2.4 Serie RIPTE

Tabla mensual desde 2008-01 a 2026-02 (212 meses) ya extraída a `data/ripte_seed.json`. En runtime se intenta refrescar contra `apis.datos.gob.ar`; si falla, se usa el seed.

### 2.5 Bugs en la planilla original — NO replicar

Al portar a Python, **corregir** estos errores que están en el Excel:

1. `FORMULA!B3` y `B7` usan `VLOOKUP(..., col_index=5, FALSE)` sobre rango de 2 columnas. Debería ser `col_index=2`.
2. `ACTUALIZACION!C7..C9` usan `VLOOKUP(A6, ...)` repetido por copy-paste. Cada fila debe usar su propia celda de mes (A7, A8, A9).
3. `RIPTE!B82` tenía `'6,670.93'` como string. Ya está corregido en `ripte_seed.json`.

---

## 3. Plan de integración con el proyecto existente

### 3.1 Archivos a crear

| Archivo | Propósito |
|---|---|
| `app_lrt.py` | Clase `CalculadoraLRT` (espejo del patrón de `LiquidadorLaboral`) |
| `pages/2_Riesgos_Trabajo.py` | **Reemplaza** el placeholder. UI Streamlit con sidebar + resultados |

### 3.2 Archivos a modificar

| Archivo | Cambio |
|---|---|
| `app_liquidacion.py` | Refactor mínimo: extraer `_obtener_serie(serie_id, fecha_objetivo)` para reutilizarla desde el RIPTE. **Mantener `obtener_datos_online` como wrapper retrocompatible** para no romper la página de despido. |

### 3.3 Archivos NO tocar

- `streamlit_app.py` — el botón "Riesgos del Trabajo" ya existe y apunta a la página correcta.
- `requirements.txt` — todo lo necesario ya está (`streamlit`, `requests`, `pandas`, `XlsxWriter`, `python-dateutil`).
- `pages/1_Liquidacion_Despido.py` — funciona, no se toca.

### 3.4 Datos a usar

- `data/pisos.json` — ya provisto, 23 entradas.
- `data/ripte_seed.json` — ya provisto, 212 meses (2008-01 → 2026-02).
- `docs/lrt/planilla_original.xlsx` — referencia para extraer casos de prueba numéricos.

---

## 4. Diseño detallado

### 4.1 `app_lrt.py` — clase `CalculadoraLRT`

Patrón espejo de `LiquidadorLaboral`. Recibe inputs en el constructor y expone métodos de cálculo. Todos los `float` (no `Decimal`).

```python
import json
from datetime import datetime
from dateutil.relativedelta import relativedelta
import requests

# Constante de la serie RIPTE en datos.gob.ar — confirmar en implementación
SERIE_ID_RIPTE = "<PENDIENTE>"  # buscar en https://datos.gob.ar/series/api/search?q=RIPTE

class CalculadoraLRT:
    """
    Calculadora de prestaciones dinerarias por incapacidad permanente parcial
    bajo Ley 24.557 + art. 3 Ley 26.773.

    Soporta dos modos:
      A) IBM ya conocido (caso "FORMULA")
      B) IBM reconstruido desde 12 salarios mensuales (caso "ACTUALIZACION")
    """

    def __init__(self,
                 caratula,
                 fecha_nacimiento,        # "DD/MM/YYYY"
                 fecha_accidente,         # "DD/MM/YYYY"
                 fecha_sentencia,         # "DD/MM/YYYY"
                 incapacidad_pct,         # 22.0 (no 0.22)
                 ibm_historico=None,      # opción A
                 salarios=None,           # opción B: [{"periodo": "MM/YYYY", "importe": 14256.5}, ...]
                 ripte_serie=None,        # dict {"YYYY-MM-01": valor} — inyectable para tests
                 pisos=None):             # list[dict] — inyectable para tests
        self.caratula = caratula
        self.fecha_nacimiento = datetime.strptime(fecha_nacimiento, "%d/%m/%Y")
        self.fecha_accidente = datetime.strptime(fecha_accidente, "%d/%m/%Y")
        self.fecha_sentencia = datetime.strptime(fecha_sentencia, "%d/%m/%Y")
        self.incapacidad_pct = incapacidad_pct
        self.ibm_historico = ibm_historico
        self.salarios = salarios or []
        self.ripte_serie = ripte_serie or {}
        self.pisos = pisos or []

        if (ibm_historico is None) == (not self.salarios):
            raise ValueError("Provea IBM histórico O salarios mensuales, no ambos ni ninguno.")

    # --- Métodos de cálculo ---
    def edad_al_accidente(self):
        return relativedelta(self.fecha_accidente, self.fecha_nacimiento).years

    def coef_edad(self):
        return 65 / self.edad_al_accidente()

    def ripte(self, fecha):
        """Devuelve el RIPTE del mes de `fecha`. Normaliza a día 1."""
        clave = fecha.strftime("%Y-%m-01")
        if clave not in self.ripte_serie:
            raise ValueError(f"RIPTE no disponible para {clave}")
        return self.ripte_serie[clave]

    def ibm_actualizado(self):
        ripte_acc = self.ripte(self.fecha_accidente)
        ripte_sent = self.ripte(self.fecha_sentencia)

        if self.ibm_historico is not None:
            return self.ibm_historico * (ripte_sent / ripte_acc)

        # Caso B: promedio de salarios actualizados al mes del accidente,
        # luego trasladados al mes de la sentencia.
        suma = 0.0
        for s in self.salarios:
            mes = datetime.strptime(s["periodo"], "%m/%Y")
            r_mes = self.ripte(mes)
            suma += s["importe"] * (ripte_acc / r_mes)
        ibm_a_fecha_accidente = suma / len(self.salarios)
        return ibm_a_fecha_accidente * (ripte_sent / ripte_acc)

    def indemnizacion_base(self):
        return 53 * self.ibm_actualizado() * self.coef_edad() * (self.incapacidad_pct / 100)

    def adicional_art3_26773(self):
        return self.indemnizacion_base() * 0.20

    def subtotal_lrt(self):
        return self.indemnizacion_base() + self.adicional_art3_26773()

    def piso_vigente(self):
        for p in self.pisos:
            desde = datetime.strptime(p["desde"], "%Y-%m-%d")
            hasta = datetime.strptime(p["hasta"], "%Y-%m-%d")
            if desde <= self.fecha_accidente <= hasta:
                return p
        return None  # sin piso definido para esa fecha

    def piso_aplicable(self):
        p = self.piso_vigente()
        if p is None:
            return 0.0
        return p["monto"] * (self.incapacidad_pct / 100)

    def capital_final(self):
        return max(self.subtotal_lrt(), self.piso_aplicable())

    def desglose(self):
        """Devuelve dict con todos los pasos para mostrar en UI / exportar."""
        return {
            "edad": self.edad_al_accidente(),
            "coef_edad": self.coef_edad(),
            "ripte_accidente": self.ripte(self.fecha_accidente),
            "ripte_sentencia": self.ripte(self.fecha_sentencia),
            "ibm_actualizado": self.ibm_actualizado(),
            "indemnizacion_base": self.indemnizacion_base(),
            "adicional_art3": self.adicional_art3_26773(),
            "subtotal_lrt": self.subtotal_lrt(),
            "piso_vigente": self.piso_vigente(),
            "piso_aplicable": self.piso_aplicable(),
            "capital_final": self.capital_final(),
        }

    def generar_excel(self, buffer=None):
        """Genera Excel con la liquidación. Patrón idéntico al de LiquidadorLaboral.generar_excel()."""
        # implementar con XlsxWriter copiando estilos de app_liquidacion.py
        pass


# --- Carga de datos de referencia ---
def cargar_pisos(path="data/pisos.json"):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def cargar_ripte_seed(path="data/ripte_seed.json"):
    with open(path, encoding="utf-8") as f:
        seed = json.load(f)
    return {item["periodo"]: item["valor"] for item in seed}


# --- Cliente API RIPTE ---
def obtener_ripte(fecha_objetivo=None):
    """
    Consulta la serie RIPTE en datos.gob.ar.
    Devuelve (valor, fecha_str) o (None, None) si falla.
    Patrón idéntico a obtener_datos_online del módulo IPC.
    """
    try:
        url = "https://apis.datos.gob.ar/series/api/series/"
        params = {"ids": SERIE_ID_RIPTE, "format": "json", "limit": 5000}
        response = requests.get(url, params=params, timeout=10).json()
        data = response["data"]

        if fecha_objetivo:
            f_dt = datetime.strptime(fecha_objetivo, "%d/%m/%Y")
            target = f_dt.strftime("%Y-%m-01")
            for entry in data:
                if entry[0] == target:
                    return entry[1], datetime.strptime(entry[0], "%Y-%m-%d").strftime("%d/%m/%Y")
            last = data[-1]
            return last[1], datetime.strptime(last[0], "%Y-%m-%d").strftime("%d/%m/%Y")
        else:
            last = data[-1]
            return last[1], datetime.strptime(last[0], "%Y-%m-%d").strftime("%d/%m/%Y")
    except Exception as e:
        print(f"Error API RIPTE: {e}")
        return None, None


def obtener_serie_ripte_completa(seed_fallback=True):
    """Devuelve dict {YYYY-MM-01: valor} con la serie completa.
    Intenta API; si falla y seed_fallback=True, usa data/ripte_seed.json."""
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
```

### 4.2 Refactor sugerido en `app_liquidacion.py`

Para evitar duplicación HTTP, extraer una función privada y dejar `obtener_datos_online` como wrapper retrocompatible:

```python
SERIE_ID_IPC = "145.3_INGNACNAL_DICI_M_15"

def _obtener_serie(serie_id, fecha_objetivo=None):
    """Cliente genérico de datos.gob.ar Series. Devuelve (valor, fecha_str) o (None, None)."""
    try:
        url = "https://apis.datos.gob.ar/series/api/series/"
        params = {"ids": serie_id, "format": "json", "limit": 5000}
        response = requests.get(url, params=params, timeout=10).json()
        data = response['data']
        if fecha_objetivo:
            f_dt = datetime.strptime(fecha_objetivo, "%d/%m/%Y")
            target = f_dt.strftime("%Y-%m-01")
            for entry in data:
                if entry[0] == target:
                    return entry[1], datetime.strptime(entry[0], "%Y-%m-%d").strftime("%d/%m/%Y")
            last_entry = data[-1]
            last_dt = datetime.strptime(last_entry[0], "%Y-%m-%d")
            if f_dt >= last_dt:
                return last_entry[1], last_dt.strftime("%d/%m/%Y")
            return data[0][1], datetime.strptime(data[0][0], "%Y-%m-%d").strftime("%d/%m/%Y")
        else:
            last_entry = data[-1]
            return last_entry[1], datetime.strptime(last_entry[0], "%Y-%m-%d").strftime("%d/%m/%Y")
    except Exception as e:
        print(f"Error API: {e}")
        return None, None


def obtener_datos_online(fecha_objetivo=None):
    """Wrapper retrocompatible: IPC INDEC."""
    return _obtener_serie(SERIE_ID_IPC, fecha_objetivo)
```

Luego en `app_lrt.py` se usa: `_obtener_serie(SERIE_ID_RIPTE, fecha)`.

### 4.3 `pages/2_Riesgos_Trabajo.py` — UI

Reemplaza el placeholder. Estructura inspirada en `pages/1_Liquidacion_Despido.py`:

**Sidebar:**
- Carátula
- Fecha nacimiento, fecha accidente, fecha sentencia
- Selector: "IBM directo" / "Por promedio de salarios"
- Si IBM directo: input numérico
- Si por salarios: `st.data_editor` con 12 filas editables (`Mes` `MM/YYYY` + `Importe`)
- % incapacidad
- Botón "🔄 Actualizar RIPTE Online"

**Main:**
- Tabla de desglose (edad, coef edad, IBM actualizado, indemniz base, art. 3, subtotal, piso, capital final)
- Comparación visual subtotal vs piso (cuál se aplica y por qué)
- Botón "📥 Exportar a Excel"

**Estilo:** mantener el mismo CSS y patrón de `1_Liquidacion_Despido.py` para consistencia visual.

---

## 5. Plan de fases

Dejar el código en verde después de cada fase antes de pasar a la siguiente.

### Fase 1 — Cliente RIPTE
- [ ] Confirmar `SERIE_ID_RIPTE` en `https://datos.gob.ar/series/api/search?q=RIPTE`
- [ ] Refactorizar `app_liquidacion.py`: extraer `_obtener_serie`, mantener `obtener_datos_online` como wrapper.
- [ ] Crear `app_lrt.py` con `obtener_ripte()`, `obtener_serie_ripte_completa()`, `cargar_ripte_seed()`, `cargar_pisos()`.
- [ ] Smoke test manual: `python -c "from app_lrt import obtener_ripte; print(obtener_ripte())"`.

### Fase 2 — Lógica de cálculo
- [ ] Implementar `CalculadoraLRT` en `app_lrt.py` (sin la UI, sin el Excel).
- [ ] Crear `tests/test_lrt.py` con 3-5 casos de paridad: extraer valores calculados de `docs/lrt/planilla_original.xlsx` con `openpyxl(data_only=True)` y verificar que `CalculadoraLRT.capital_final()` coincida al peso (margen de error 0.01).
- [ ] Cubrir caso A (IBM directo) y caso B (salarios) en los tests.

### Fase 3 — UI Streamlit
- [ ] Reemplazar `pages/2_Riesgos_Trabajo.py` con la página real.
- [ ] Implementar el sidebar con los dos modos.
- [ ] Mostrar desglose en tabla (`st.dataframe` o `pd.DataFrame` con formato).
- [ ] Botón "Actualizar RIPTE Online" con `st.spinner`, igual que el botón IPC.

### Fase 4 — Export a Excel
- [ ] Método `CalculadoraLRT.generar_excel(buffer)` con XlsxWriter.
- [ ] Copiar la paleta de formatos de `LiquidadorLaboral.generar_excel`.
- [ ] Botón de descarga en la página con `st.download_button`.

### Fase 5 — Pulido
- [ ] Validaciones cruzadas (sentencia ≥ accidente, edad > 0, suma de %incapacidad ≤ 100, etc.).
- [ ] Mensajes de error amigables si el RIPTE no está disponible para una fecha.
- [ ] Caso límite: incap ≥ 66% no debería usar art. 14.2.a — emitir warning ("considerar art. 14.2.b").

**Estimado:** 3-4 días de trabajo dedicado.

---

## 6. Tests críticos

### 6.1 Test de paridad con la planilla

El más importante. Plantilla:

```python
# tests/test_lrt_paridad.py
from openpyxl import load_workbook
from app_lrt import CalculadoraLRT, cargar_pisos, cargar_ripte_seed

def test_caso_formula_de_la_planilla():
    """Toma valores calculados directamente del Excel original."""
    wb = load_workbook("docs/lrt/planilla_original.xlsx", data_only=True)
    ws = wb["FORMULA"]
    esperado_total = ws["B22"].value  # capital final calculado por Excel

    calc = CalculadoraLRT(
        caratula="Test paridad FORMULA",
        fecha_nacimiento="21/08/1946",
        fecha_accidente="31/08/2011",
        fecha_sentencia="01/06/2024",
        incapacidad_pct=22.0,
        ibm_historico=9179.12,
        ripte_serie=cargar_ripte_seed(),
        pisos=cargar_pisos(),
    )
    assert abs(calc.subtotal_lrt() - esperado_total) < 0.01
```

### 6.2 Tests unitarios mínimos

- `test_coef_edad`: `65/40 == 1.625`
- `test_ibm_actualizado_caso_a`
- `test_ibm_actualizado_caso_b`: 12 salarios mockeados, RIPTE mockeado.
- `test_piso_vigente`: bordes de banda (29/02 en años bisiestos, transiciones 31/08 → 01/09).
- `test_capital_aplica_piso_si_es_mayor`.
- `test_capital_aplica_subtotal_si_es_mayor`.

---

## 7. Casos de prueba a extraer de la planilla

Para `tests/test_lrt_paridad.py`, abrir `docs/lrt/planilla_original.xlsx` con openpyxl(data_only=True) y leer:

| Caso | Hoja | Celda esperada |
|---|---|---|
| Caso A — IBM directo, sentencia 2024 | FORMULA | B22 (total) y B20 (base) |
| Caso B — salarios, sentencia 2015 | ACTUALIZACION | H12 (total) y H10 (base) |

Para encontrar los datos de entrada del caso A, leer también `B2`, `B4`, `B6`, `B13`, `B14`, `B17` (mes accidente, IBM histórico, fecha sentencia, nacimiento, accidente, % incapacidad).

Para el caso B: `H3`, `H4`, `H7` (nacimiento, accidente, % incapacidad) y la tabla `A5:B16` (12 salarios).

---

## 8. Consideraciones legales y de mantenimiento

- **Pisos legales nuevos:** cuando salga una resolución posterior a la última cargada, agregar entrada a `data/pisos.json`. **No tocar código.**
- **Reformas a la LRT:** si cambia la fórmula del art. 14 (ej: nueva ley), eso sí requiere cambio en `CalculadoraLRT`. Marcar el rango de fechas donde aplica cada fórmula.
- **Decreto 669/2019 (intereses):** explícitamente **fuera de v1**. La hoja `CON 66919` de la planilla cubre esto y queda para v2.
- **Casos de incapacidad total (≥66%):** la fórmula del art. 14.2.a no aplica. Emitir warning en UI.

---

## 9. Decisiones tomadas y por qué

| Decisión | Por qué |
|---|---|
| `CalculadoraLRT` como clase monolítica | Espejo del patrón de `LiquidadorLaboral`; consistencia interna del proyecto |
| `float` en vez de `Decimal` | El proyecto entero usa float; introducir `Decimal` ahora rompería consistencia y obligaría a migrar el resto |
| Reemplazar el placeholder de la página, no crear archivo nuevo | El botón en `streamlit_app.py` ya apunta a `pages/2_Riesgos_Trabajo.py` |
| `requests` (no `httpx`) | Ya está en `requirements.txt` |
| `XlsxWriter` (no openpyxl) | Coincide con `LiquidadorLaboral.generar_excel` |
| JSON en `data/` (no SQLite) | Datos chicos y estables; el JSON se versiona limpio en git |
| Seed RIPTE como fallback | API puede caer; RIPTE rara vez cambia retroactivamente |
| Refactor de `obtener_datos_online` con wrapper retrocompatible | No romper la página de despido que está en producción |
