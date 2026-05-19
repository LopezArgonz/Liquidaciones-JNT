# Liquidador_Tribunal — Sistema de Liquidación Laboral JNT

> Archivo leído automáticamente por Claude Code al abrir el proyecto. Contiene el contexto y las convenciones que ya están en uso. **No introducir tecnologías ni patrones nuevos sin revisar primero las convenciones de abajo.**

## Qué es

Aplicación Streamlit para la Justicia Nacional del Trabajo (Argentina) que calcula liquidaciones laborales y las exporta a Excel. Hoy tiene dos secciones:

1. **Liquidación por Despido** — funcional. Calcula art. 245 LCT, integración mes despido, SAC, vacaciones, multas (25.323, 24.013, art. 80, Dto. 34/2019), aplica Vizzoti, actualiza por IPC INDEC + 3% anual de interés puro.
2. **Riesgos del Trabajo (Ley 24.557)** — **pendiente de desarrollo**. Hay placeholder en `pages/2_Riesgos_Trabajo.py`. Toda la especificación, datos de referencia y plan están en `docs/lrt/`. Leerlos antes de tocar nada acá.

## Stack y convenciones

**No cambiar el stack sin razón fuerte.** Lo que está en uso:

| Aspecto | Convención |
|---|---|
| Python | Sin versión fijada explícita; el `.venv` es el de referencia |
| UI | **Streamlit multipage** (`streamlit_app.py` + `pages/`) |
| Cálculos numéricos | **`float`** (no `Decimal`). Es el existente. |
| HTTP | **`requests`** (no `httpx`). Coincide con `requirements.txt`. |
| Excel output | **`XlsxWriter`** (no openpyxl). El método `generar_excel` de `LiquidadorLaboral` ya tiene formato. |
| Fechas en UI | **DD/MM/YYYY** (`format="DD/MM/YYYY"` en `st.date_input`) |
| Fechas internas | `datetime` con `strptime("%d/%m/%Y")` |
| Idioma del dominio | **Español** (nombres de variables, atributos, rubros, mensajes) |
| Type hints | Mínimos / inexistentes en el código actual. Si agregás nuevo módulo, podés usar hints discretos pero no es obligatorio. |
| Estado UI | `st.session_state` con keys descriptivas |
| Estilo Streamlit | Bloques `st.markdown` con CSS inline (mantener look & feel existente) |
| Patrón de cálculo | **Clase monolítica** que recibe inputs en el constructor y expone métodos `calcular_X()`. Ejemplo: `LiquidadorLaboral`. |
| Patrón de API | **Función suelta** que devuelve `(valor, fecha_str)` o `(None, None)`. Ejemplo: `obtener_datos_online`. |

## Estructura actual

```
Liquidador_Tribunal/
├── app_liquidacion.py            # Clase LiquidadorLaboral + obtener_datos_online (IPC)
├── streamlit_app.py              # Landing con botones a las dos calculadoras
├── pages/
│   ├── 1_Liquidacion_Despido.py  # UI funcional
│   └── 2_Riesgos_Trabajo.py      # Placeholder — A REEMPLAZAR
├── requirements.txt              # streamlit, pandas, XlsxWriter, python-dateutil, requests
├── setup_og.py                   # Inyecta meta tags OpenGraph al index.html de Streamlit
├── ejecutar_aplicacion.bat       # Lanza streamlit run streamlit_app.py
├── logo.png
├── data/                         # NUEVO — datos de referencia para el módulo LRT
│   ├── pisos.json                # Pisos legales Ley 26.773 (23 entradas)
│   └── ripte_seed.json           # Serie RIPTE 2008-01 a 2026-02 (212 meses)
└── docs/
    └── lrt/                      # NUEVO — documentación del módulo LRT pendiente
        ├── DISEÑO_LRT.md         # Diseño completo del módulo
        ├── PROMPT_LRT.md         # Prompt para arrancar la implementación con Claude Code
        └── planilla_original.xlsx  # Planilla Excel de referencia (la que reemplaza el módulo)
```

## Cliente API — datos.gob.ar (importante para el módulo LRT)

Ya hay un cliente HTTP a `apis.datos.gob.ar` en `app_liquidacion.py:obtener_datos_online()` que consume la serie IPC INDEC (`series_id="145.3_INGNACNAL_DICI_M_15"`). El módulo LRT necesita **otra serie** del mismo endpoint: el RIPTE.

**No duplicar la función. Refactorizar.** Hay dos opciones razonables (elegir una al implementar):

- **Opción A — generalizar:** convertir `obtener_datos_online` en `obtener_serie(serie_id, fecha_objetivo=None)` con dos wrappers: `obtener_ipc(...)` y `obtener_ripte(...)`. Es lo más limpio.
- **Opción B — sibling:** dejar `obtener_datos_online` como está (no romper la firma usada por la página de despido) y agregar `obtener_ripte(fecha_objetivo=None)` al lado, refactorizando el código compartido a una función privada `_obtener_serie(serie_id, fecha_objetivo)`.

Ambas mantienen retrocompatibilidad. Documentar el `series_id` exacto del RIPTE como constante al tope del archivo.

## Convenciones para el módulo LRT (cuando se implemente)

Resumen — el detalle completo está en `docs/lrt/DISEÑO_LRT.md`:

- **Archivo principal:** `app_lrt.py` con clase `CalculadoraLRT` (espejo de `LiquidadorLaboral`).
- **Página UI:** **reemplazar** `pages/2_Riesgos_Trabajo.py` (no crear archivo nuevo). El botón ya existe en `streamlit_app.py`.
- **Datos:** `data/pisos.json` y `data/ripte_seed.json` (ya provistos). Cargar con `json.load`. Si la API RIPTE falla, usar `ripte_seed.json` como fallback.
- **No** introducir SQLite, pyproject.toml, ni packaging. Mantener el patrón flat del proyecto.
- **Scope v1:**
  1. Cálculo art. 14.2.a (53 × IBM × 65/edad × %incap)
  2. Adicional art. 3 Ley 26.773 (20%)
  3. Pisos legales (`max(subtotal, piso)`)
  4. Actualización del IBM por RIPTE entre accidente y sentencia
  5. Reconstrucción del IBM desde 12 salarios mensuales
- **Fuera de v1:** Decreto 669/2019 (intereses), arts. 14.2.b, 15, 17.

## Cosas que NO hacer

- ❌ Reemplazar `requests` por `httpx`, `XlsxWriter` por `openpyxl`, o `float` por `Decimal`. Romper consistencia.
- ❌ Crear `pyproject.toml` ni mover el código a un paquete. El proyecto es flat por diseño.
- ❌ Agregar SQLite o cualquier dependencia que no esté en `requirements.txt` sin justificarlo y agregarla.
- ❌ Tocar `app_liquidacion.py` salvo para refactorizar el cliente API (ver sección anterior).
- ❌ Crear un archivo nuevo de página LRT en `pages/` — reemplazar el placeholder `2_Riesgos_Trabajo.py`.
- ❌ Hardcodear los pisos legales o la serie RIPTE en código. Siempre vienen de `data/`.

## Comandos

```bash
# Levantar la app
.\.venv\Scripts\python.exe -m streamlit run streamlit_app.py
# o el .bat:
ejecutar_aplicacion.bat

# Instalar dependencias
.\.venv\Scripts\pip.exe install -r requirements.txt
```

## Cuando trabajés en el módulo LRT

Antes de escribir código, leer en este orden:

1. Este archivo (ya lo estás leyendo).
2. `docs/lrt/DISEÑO_LRT.md` — análisis funcional + plan + fórmula.
3. `docs/lrt/PROMPT_LRT.md` — qué hacer concretamente.
4. `app_liquidacion.py` y `pages/1_Liquidacion_Despido.py` — para imitar patrones.

Después arrancar con la **Fase 1** del plan en `DISEÑO_LRT.md`: confirmar el `series_id` del RIPTE en datos.gob.ar y refactorizar el cliente API.
