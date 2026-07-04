# PROMPT PARA CLAUDE CODE — Rediseño integral de Liquidaciones JNT

> Copiá todo el contenido desde "## PROMPT" hasta el final y pegalo en Claude Code
> abierto en la raíz de este repositorio.

---

## PROMPT

Sos un desarrollador senior especializado en Python/Streamlit y en diseño de
interfaces institucionales. Vas a transformar esta aplicación de liquidaciones
laborales de la Justicia Nacional del Trabajo (Argentina) en una herramienta de
uso diario: sobria, elegante, metódica y con identidad visual del Poder Judicial
y del derecho del trabajo. La usan a diario empleados judiciales que hacen
liquidaciones de despido y de riesgos del trabajo; tiene que sorprender tanto a
jueces como a informáticos.

Antes de escribir una línea de código, leé en este orden: `CLAUDE.md`,
`utils.py`, `app_liquidacion.py`, `app_lrt.py`, `streamlit_app.py`,
`pages/1_Liquidacion_Despido.py`, `pages/2_Riesgos_Trabajo.py`,
`tests/test_lrt.py`.

### Restricciones inviolables (según CLAUDE.md)

- Stack fijo: Streamlit multipage, `float`, `requests`, `XlsxWriter`, estructura flat, dominio en español.
- NO agregar dependencias salvo las explícitamente autorizadas acá (ninguna nueva es necesaria; todo el diseño se hace con CSS inline y SVG embebido).
- NO tocar la lógica jurídica de cálculo (fórmulas, rubros, multas, coeficientes). Los números que hoy salen deben seguir saliendo idénticos. Los tests existentes de `tests/test_lrt.py` deben seguir pasando.
- NO crear `pyproject.toml`, paquetes, ni SQLite.
- NO subir ni modificar `config.yaml` (contiene credenciales reales).
- Fechas siempre `DD/MM/YYYY` en UI.

Trabajá por fases, en este orden, haciendo commit al final de cada fase con mensaje descriptivo en español.

---

### FASE 1 — Backend: una sola fuente de verdad para los rubros

Hoy la lista de rubros del despido está construida DOS veces: en
`LiquidadorLaboral.generar_excel()` (app_liquidacion.py) y de nuevo, duplicada a
mano, en `pages/1_Liquidacion_Despido.py` (sección "CONSTRUCCIÓN DE RUBROS").
Cualquier corrección futura puede divergir. Refactorizá:

1. Creá en `LiquidadorLaboral` un método `calcular_rubros()` que devuelva un dict:
   `{"rubros": [(seccion, label, monto), ...], "total_historico": float, "capital_neto": float, "coef": float, "capital_actualizado": float, "dias": int, "interes_puro": float, "total_final": float}`.
   El campo `seccion` clasifica cada rubro en: `"indemnizatorios"`, `"salariales"`, `"multas"`, `"adicionales"` — vas a usarlo para agrupar visualmente la tabla y el Excel.
2. `generar_excel()` y la página 1 deben consumir EXCLUSIVAMENTE ese método. Eliminá la duplicación de la página (el bloque entre "CONSTRUCCIÓN DE RUBROS" y el cálculo de `total_final`).
3. Escribí `tests/test_despido.py` (pytest, espejo del estilo de `tests/test_lrt.py`) con casos que fijen el comportamiento ACTUAL antes del refactor: antigüedad art. 245 (con y sin redondeo de +3 meses), preaviso 1 y 2 meses, integración, SAC proporcional y semestre anterior, vacaciones por escala, Vizzoti (piso 67% y tope CCT), cada multa (25.323 arts. 1/2, 24.013 arts. 8/9/10/15, art. 80, Dto. 34/2019), pagos a cuenta, y actualización IPC + 3%. Corré los tests antes y después del refactor: mismos números.
4. Robustez del cliente API (`_obtener_serie`): agregá reintento simple (2 intentos) y creá `data/ipc_seed.json` (mismo formato que `ripte_seed.json`) generándolo con una llamada real a la serie `145.3_INGNACNAL_DICI_M_15`; si la API falla, la página de despido debe ofrecer el seed local como fallback con un aviso "Fuente: seed local al MM/AAAA — verificar si hay índice más reciente". Cacheá las llamadas API con `st.cache_data(ttl=3600)` en un wrapper fino del lado de la página (no dentro de app_liquidacion.py, que también se usa por CLI).
5. Sanitización de nombre de archivo: la página 1 usa `caratula.replace(" ", "_")` para el nombre del Excel; reutilizá la sanitización con `re.sub(r'[^\w\s-]', '_', ...)` que ya existe en `generar_excel` (extraela a una función `sanitizar_nombre()` en `utils.py`).
6. En `utils.py` agregá `monto_en_letras(valor: float) -> str` SIN dependencias nuevas: convierte un monto a letras en español estilo sentencia judicial, p. ej. `1_234_567.89` → `"PESOS UN MILLÓN DOSCIENTOS TREINTA Y CUATRO MIL QUINIENTOS SESENTA Y SIETE CON 89/100"`. Cubrí hasta miles de millones, con tests en `tests/test_utils.py` (incluí 0, 1, 21, 100, 101, 1000, 1.000.000, decimales).

### FASE 2 — Sistema de diseño institucional (utils.py + tema)

Creá `.streamlit/config.toml` con tema claro institucional:

```toml
[theme]
primaryColor = "#B8860B"        # dorado judicial (acciones)
backgroundColor = "#FAF8F3"     # marfil
secondaryBackgroundColor = "#EFEBE2"
textColor = "#1F2A38"           # azul medianoche
font = "serif"
```

Reescribí `utils.py` como un mini design-system (todo CSS/SVG embebido, sin archivos externos ni dependencias):

- **Paleta** en variables CSS: `--jnt-azul: #1F2A38`, `--jnt-azul-claro: #2C3E50`, `--jnt-dorado: #B8860B`, `--jnt-dorado-suave: #C9A227`, `--jnt-marfil: #FAF8F3`, `--jnt-borde: #D8D2C4`, `--jnt-exito: #2E6B4F`, `--jnt-alerta: #8C2F39`.
- **Tipografía**: títulos con serif institucional (stack `Georgia, 'Times New Roman', serif`), cuerpo sans (`'Segoe UI', system-ui, sans-serif`). Nada de emojis en títulos: reemplazá ⚖️ 📄 🏥 📋 📥 por SVG inline monocromos (balanza de la justicia, legajo, casco/cruz sanitaria, columna de tribunal) definidos una vez en `utils.py` como funciones que devuelven el `<svg>` (currentColor, 20–28 px).
- **`encabezado_institucional(titulo, subtitulo)`**: banda superior con SVG de balanza a la izquierda, título serif, subtítulo, y debajo una doble línea horizontal fina (una azul, una dorada) — el clásico filete de documento judicial. Incluir leyenda pequeña en mayúsculas espaciadas: `PODER JUDICIAL DE LA NACIÓN · JUSTICIA NACIONAL DEL TRABAJO`.
- **`tarjeta_metrica(label, valor, tono)`**: tarjetas de resultado con borde superior de 3px dorado, valor grande serif, label en versalitas. Tonos: neutro/exito/alerta.
- **`chip_norma(texto)`**: pequeño badge con borde dorado y fondo marfil para citar normas ("art. 245 LCT", "Ley 25.323"), usado en la tabla de rubros.
- **Tabla `table-jnt` mejorada**: mantener la clase actual pero: encabezado azul medianoche con texto marfil, filas cebra sutiles, montos alineados a derecha con tabular-nums, filas de sección (indemnizatorios / salariales / multas / adicionales) como subencabezados con fondo marfil oscuro y símbolo `§` antes del nombre, fila total con doble borde superior (estilo suma contable).
- **`sello_fuente(texto)`**: caja tipo "sello" (borde doble, texto en mayúsculas pequeñas, levemente rotado -1°) para indicar fuente de índices: "FUENTE: IPC INDEC — SERIE 145.3 — CONSULTADO DD/MM/AAAA". Detalle judicial distintivo.
- **`mostrar_footer()`**: rediseñar — línea dorada fina, `§` centrado, "Justicia Nacional del Trabajo — Sistema de Liquidaciones", crédito del autor y versión de la app (constante `VERSION = "2.0"` en utils.py).
- **Impresión**: bloque `@media print` que oculte sidebar, botones y header de Streamlit, para que Ctrl+P produzca una planilla limpia.
- Ocultar el menú hamburguesa y el footer "Made with Streamlit" (`#MainMenu`, `footer {visibility: hidden}`), manteniendo accesible el botón de colapso del sidebar.
- Todos los estilos deben verse bien con el tema claro configurado; no usar colores hardcodeados que dependan del modo oscuro.

### FASE 3 — Página de Despido: flujo metódico de trabajo diario

`pages/1_Liquidacion_Despido.py`:

1. **Encabezado**: usar `encabezado_institucional("Liquidación por Despido", "Arts. 245, 232, 233 LCT — Actualización IPC INDEC + 3% anual")`.
2. **Sidebar como expediente, en pasos numerados**: reorganizá los controles actuales (sin quitar ninguno) en `st.expander` numerados que guíen el orden de carga:
   - `I · Expediente` (carátula, fechas ingreso/despido/liquidación, remuneración)
   - `II · Causa de extinción`
   - `III · Multas e incrementos` (todo lo de 25.323 / 24.013 / art. 80 / Dto. 34)
   - `IV · Vizzoti y rubros adicionales` (Vizzoti, salarios adeudados, otros rubros, pagos a cuenta)
   - `V · Índices IPC` (con el sello de fuente y estado)
   El paso I abierto por defecto, el resto colapsado. Cada checkbox de multa conserva su `help` actual y suma al lado un `chip_norma` con enlace a la norma en InfoLEG (`target="_blank"`): 25.323 → texto en infoleg.gob.ar, ídem 24.013, LCT y Dto. 34/2019. Buscá los enlaces reales de InfoLEG.
   - **Semáforo de completitud**: arriba del sidebar, una línea con 5 puntos (●○○○○) que se van llenando en dorado según qué pasos ya tienen datos válidos; usa los datos ya presentes en session_state, sin lógica nueva de validación.
3. **Zona principal — resultados**:
   - Tres `tarjeta_metrica`: "Antigüedad computada" / "Coeficiente IPC" / "Total actualizado". Debajo, el "Tope mínimo 67%".
   - **Monto en letras**: debajo del total, el resultado de `monto_en_letras(total_final)` en un recuadro serif con comillas de sentencia — es el texto que el empleado copia al proyecto de sentencia.
   - **Tabla de rubros agrupada** por las secciones de `calcular_rubros()` con subencabezados `§ RUBROS INDEMNIZATORIOS`, `§ RUBROS SALARIALES`, `§ MULTAS E INCREMENTOS`, `§ ADICIONALES`, y bloque final de actualización (coef. IPC, capital actualizado, interés puro 3%, TOTAL) con la fila total a doble raya.
   - **Bloque "Texto para la sentencia"**: un `st.code`/text_area de solo lectura con la liquidación redactada en prosa judicial lista para copiar y pegar, por ejemplo: `"Conforme surge de la liquidación practicada, corresponde condenar al pago de la suma de $ X.XXX.XXX,XX (PESOS ... ), comprensiva de los rubros indemnización por antigüedad ($...), preaviso ($...), [...], con más la actualización por IPC INDEC (coef. X,XXXX) e interés puro del 3% anual (XXX días)."` Generá ese texto en un método `texto_sentencia()` de `LiquidadorLaboral` para que sea testeable.
   - **Exportación**: botón de descarga del Excel (igual que hoy) + botón "Vista de impresión" que muestre la planilla sola aprovechando el CSS `@media print`.
4. Mantener TODAS las validaciones existentes, pero mostrarlas con el estilo del design system (alerta bordó, no el rojo default).

### FASE 4 — Página LRT: mismo tratamiento

`pages/2_Riesgos_Trabajo.py`: aplicar exactamente el mismo patrón — encabezado institucional ("Riesgos del Trabajo — Ley 24.557 · art. 3 Ley 26.773"), sidebar en pasos (`I · Expediente y trabajador`, `II · Incapacidad`, `III · IBM`, `IV · Índice RIPTE`), tarjetas métricas (Edad al accidente / Coef. RIPTE / Capital final), monto en letras, chips de norma con enlaces InfoLEG (24.557, 26.773), sello de fuente "RIPTE — SRT — ÍNDICE NO DECRECIENTE BASE 07/94", tabla de desglose con estilo `table-jnt` mejorado, texto para sentencia (`CalculadoraLRT.texto_sentencia()`), y aviso destacado cuando aplica el piso legal (mostrar la norma del piso como chip). Conservar intacta la advertencia de incapacidad ≥ 66% y la tabla de salarios del Modo B (dale el mismo estilo de tabla).

### FASE 5 — Portada y login con identidad judicial

`streamlit_app.py`:

1. **Login**: pantalla centrada tipo "mesa de entradas": tarjeta marfil con doble borde (azul + dorado), SVG de balanza grande arriba, título serif "Sistema de Liquidación Laboral", leyenda "JUSTICIA NACIONAL DEL TRABAJO", y el formulario de `streamlit_authenticator` debajo. Mensaje de error de credenciales con el estilo bordó del design system.
2. **Portada post-login**: saludo formal ("Bienvenido/a, Dr./Dra. {nombre}" — usar el nombre tal cual viene de config), y dos tarjetas-herramienta grandes tipo carátula de expediente: borde, esquina superior con etiqueta dorada ("LCT — DESPIDO" / "LRT — LEY 24.557"), SVG correspondiente, descripción de una línea de qué calcula cada una, y hover con elevación sutil. Debajo, una franja discreta con el estado de los índices: última fecha IPC disponible y último período RIPTE del seed (leelos con las funciones existentes, con manejo de error silencioso si no hay red).
3. Sidebar de navegación: nombre del usuario con ícono SVG de toga/persona, botón "Cerrar sesión" estilizado, y los enlaces de página con los mismos SVG.

### FASE 6 — Excel con la misma identidad

En `generar_excel()` de ambas clases (sin cambiar ningún número):

- Paleta coherente: encabezados azul `#1F2A38` con texto marfil, acentos dorado `#B8860B`, fila de total con doble borde y fondo `#EFEBE2`.
- Título del documento en la fila 1 combinando celdas: "JUSTICIA NACIONAL DEL TRABAJO — LIQUIDACIÓN" + carátula.
- Subencabezados de sección (los mismos `§` de la UI) usando `calcular_rubros()`.
- `freeze_panes` bajo el encabezado, área de impresión definida, pie de página de impresión con fecha de generación y "Sistema de Liquidaciones JNT v2.0".
- Al final, una fila con el monto en letras (`monto_en_letras`).

### FASE 7 — Verificación final (obligatoria)

1. `pytest -q` — todos los tests (LRT existentes + los nuevos de despido y utils) en verde.
2. Levantá la app (`streamlit run streamlit_app.py`) y verificá que arranca sin excepciones; probá un caso completo de despido (con 3 multas y Vizzoti) y uno de LRT Modo B, comparando el total contra el cálculo previo al refactor (los tests de la Fase 1 son la red de seguridad).
3. Verificá que el Excel descarga y abre (generalo a un buffer en un script de prueba).
4. Revisá que `config.yaml` no haya sido modificado ni incluido en ningún commit.
5. Actualizá `CLAUDE.md`: sumá una sección corta "Design system (utils.py)" documentando paleta, componentes y la regla de que TODA página nueva debe usarlos; y documentá `calcular_rubros()` como única fuente de verdad de los rubros.

### Criterios de aceptación

- Cero cambios en los resultados numéricos (tests lo prueban).
- Ninguna dependencia nueva en `requirements.txt`.
- Ningún emoji en la UI; toda la iconografía es SVG monocromo institucional.
- La app se ve como un instrumento del Poder Judicial: marfil, azul medianoche, dorado, serif en títulos, filetes dobles, sellos, `§`, montos en letras.
- Un empleado puede: cargar un caso siguiendo los pasos I→V, leer el resultado agrupado, copiar el texto de sentencia, y descargar el Excel — sin fricción, en ese orden.
