# Prompt para arrancar el módulo LRT con Claude Code

> Copiá y pegá el bloque de abajo como tu primer mensaje en Claude Code (en la terminal integrada de VS Code, dentro de `Liquidador_Tribunal`).

---

## Cómo arrancar

1. Abrir VS Code en el proyecto: `code C:\Users\lopez\Documents\Liquidador_Tribunal`
2. En la terminal integrada (Ctrl+`) ejecutar `claude`
3. Pegar el bloque de abajo

---

## Prompt para pegar (copiar todo desde acá)

```
Voy a sumar al proyecto la calculadora de Riesgos del Trabajo
(Ley 24.557) que hoy es solo un placeholder en pages/2_Riesgos_Trabajo.py.

Antes de tocar cualquier cosa, leé en este orden:

1. CLAUDE.md (raíz del proyecto) — convenciones del proyecto y stack
   en uso. Importante: el proyecto usa float (no Decimal), requests
   (no httpx), XlsxWriter (no openpyxl). No introducir tecnologías
   nuevas sin razón fuerte.

2. docs/lrt/DISEÑO_LRT.md — análisis funcional completo, diseño del
   módulo, plan de fases, y casos de prueba.

3. app_liquidacion.py y pages/1_Liquidacion_Despido.py — para imitar
   los patrones existentes (clase monolítica, función obtener_datos_online,
   estilo Streamlit con CSS inline).

Datos de referencia ya cargados en el proyecto:
- data/pisos.json — 23 pisos legales (Ley 26.773), Dto. 1694/09 hasta
  Res. SRT 12/2023.
- data/ripte_seed.json — serie RIPTE 2008-01 a 2026-02 (212 meses),
  útil como fallback offline.
- docs/lrt/planilla_original.xlsx — la planilla Excel que estamos
  reemplazando (fuente de los casos de paridad).

Plan de fases (de DISEÑO_LRT.md):
- Fase 1: Cliente RIPTE — confirmar series_id en datos.gob.ar,
  refactorizar app_liquidacion.py con _obtener_serie privada,
  crear app_lrt.py con obtener_ripte().
- Fase 2: Lógica de cálculo — clase CalculadoraLRT + tests de paridad
  contra la planilla original.
- Fase 3: UI Streamlit — reemplazar pages/2_Riesgos_Trabajo.py.
- Fase 4: Export a Excel con XlsxWriter (mismo patrón que LiquidadorLaboral).
- Fase 5: Pulido (validaciones, mensajes de error, caso incap≥66%).

Por favor:
1. Leé los tres archivos arriba.
2. Confirmá que entendiste la estructura del proyecto y las
   convenciones existentes.
3. Hacéme las preguntas que tengas (típicamente sobre el series_id
   del RIPTE, sobre algún detalle de la fórmula, o sobre alguna
   decisión de UI).
4. Cuando estemos alineados, arrancá con la Fase 1.

No saltees fases. No toques pages/1_Liquidacion_Despido.py ni
streamlit_app.py — funcionan y no necesitan cambios. El único
archivo existente que se modifica es app_liquidacion.py, y solo
para extraer una función privada (manteniendo obtener_datos_online
como wrapper retrocompatible).
```

---

## Si necesitás reanudar contexto en una sesión nueva

```
Reanudemos el módulo LRT. Leé CLAUDE.md y docs/lrt/DISEÑO_LRT.md.
Después inspeccioná app_lrt.py (si existe) y pages/2_Riesgos_Trabajo.py
para ver en qué fase estamos. Decime el próximo paso pendiente.
```

## Tips

- **Antes de la Fase 1**, Claude Code probablemente quiera buscar el `series_id` del RIPTE en datos.gob.ar. Si no encuentra el id correcto en la API de búsqueda, una alternativa es preguntarle al equipo de SSS o usar el seed JSON como única fuente y hacer refresh manual.
- **Test de paridad (Fase 2)**: pedile que extraiga primero los valores de `docs/lrt/planilla_original.xlsx` con `openpyxl(data_only=True)` antes de escribir el test, así el test usa números reales calculados por Excel.
- **Si propone cambiar de stack** (ej. introducir Decimal o httpx), redirigirlo a `CLAUDE.md` que prohíbe esos cambios.
- **Cuando salga una resolución nueva con un piso actualizado**, no es trabajo de código: agregar la entrada a `data/pisos.json` y listo.
