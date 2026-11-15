# Power BI: qué hay que hacer (para Javiera)

Grupo 2 · Retail · 15-11-2026

## 1. Primero: ¿hay que hacer algo en Power BI?

**No es obligatorio.** Ni el enunciado E2 ni la cápsula del ayudante exigen Power BI:

- El enunciado: "puede salir de Power BI, Tableau, Looker Studio, Streamlit o código, siempre que se navegue en vivo y se actualice cuando la cadena vuelve a correr".
- La cápsula: las herramientas "no son obligatorias"; Streamlit y Python local aparecen como alternativas válidas. El ayudante *recomienda* Databricks o Fabric/Power BI para aprender, pero la pauta no lo exige.

**Lo que ya tenemos cubre el componente D:** el prototipo en Streamlit (`prototipo/app.py`) responde la pregunta en una pantalla, sigue la anatomía de la clase 7, se actualiza cuando la cadena corre y funciona en Mac y en Windows.

### Recomendación

| Opción | Qué implica | Recomendada |
|---|---|---|
| **A. No hacer Power BI** | Javiera se enfoca en lo que falta y sí pesa: la prueba de uso con 2 personas ajenas, la evaluación de la contraparte, el informe | **Sí**, por el plazo (entrega el miércoles 18) |
| B. Power BI como segunda capa de consumo | Un `.pbix` que lee las mismas tablas de `datos/oro/`. Se puede mostrar como "también funciona en Power BI", pero la demo principal sigue siendo Streamlit | Solo si sobra tiempo después de la prueba de uso |

**Riesgos de la opción B** (por eso no es la principal):

1. **Una segunda fórmula.** La cápsula lo advierte: si el número se calcula en DAX, tiene que ser *el mismo cálculo* que el del informe. Si en Power BI se recalcula la retención con otra lógica, tendríamos dos definiciones y bajaría el componente C. Las instrucciones de abajo evitan esto: Power BI **solo lee** cifras ya calculadas, no las recalcula.
2. **Power BI Desktop no corre en Mac.** El viernes 20 la demo dependería del computador de Javiera.
3. **El simulador de la decisión** (a los cuántos días contactar, cuánto cuesta) no se puede replicar en Power BI sin volver a escribir la fórmula en DAX. En Power BI solo se mostraría la tabla fija de 30, 45, 60 y 75 días.

**Si el equipo elige A, aquí termina el documento.** Lo de abajo es solo para la opción B.

---

## 2. Opción B: armar el Power BI paso a paso

### 2.1 Preparar los datos (una vez)

1. Instalar Power BI Desktop (gratis, desde Microsoft Store) en Windows.
2. Clonar el repositorio y cambiarse a la rama `entrega-2`.
3. Instalar Python 3.10 o superior y correr, desde la carpeta del repositorio:

   ```
   pip install -r cadena_datos/requirements.txt
   python cadena_datos/run_pipeline.py
   ```

   Al final debe decir `Retención Q4 2025 (90 días): 51.1% · pruebas 36/36 · IPC: ok · PUBLICADA`.
4. Las tablas quedan en `datos/oro/`. Power BI lee solo esa carpeta.

### 2.2 Cargar las tablas

En Power BI: **Obtener datos → Texto/CSV**, una por una. Cargar solo estas:

| Archivo | Para qué |
|---|---|
| `mart_retencion.csv` | La cifra principal, la regla retiene/repone y el corte por local |
| `mart_valor_riesgo.csv` | Margen anual en riesgo |
| `mart_kpi_resumen.csv` | Cobertura y otras cifras |
| `mart_una_sola_vez.csv` | Compradores de una sola vez |
| `mart_caso_contacto.csv` | Tabla del caso de negocio (30, 45, 60, 75 días) |
| `historial_corridas.csv` | Fecha de la última corrida publicada (pie) |
| `estado_fuentes.csv` | Aviso si la API del IPC usó el respaldo (pie) |

**Cuidado con los decimales (esto es lo que más falla).** Los CSV usan punto decimal (`0.511`) y Power BI en español puede leerlo como 511. En cada tabla, en **Transformar datos** (Power Query):
- En el cuadro de carga, elegir **Origen del archivo: 65001: Unicode (UTF-8)**.
- Para cada columna numérica: clic derecho → **Cambiar tipo → Usando configuración regional…** → tipo *Número decimal*, configuración regional **Inglés (Estados Unidos)**.
- Revisar: en `mart_retencion`, `tasa_retencion` tiene que verse entre 0 y 1 (por ejemplo 0,511), no 511.

**Filtros en Power Query para `mart_retencion`:** dejar solo `periodo_tipo = "trimestre"` y `base_confiable = TRUE`.

### 2.3 Medidas DAX: solo leen, no recalculan

Para no tener una segunda fórmula, las medidas **toman el valor ya calculado** por la cadena (que sale de `cadena_datos/metricas.py`). Crear en la tabla `mart_retencion`:

```
Retención = SELECTEDVALUE ( mart_retencion[tasa_retencion] )
Nuevos por perdido = SELECTEDVALUE ( mart_retencion[indice_reposicion] )
Veredicto = SELECTEDVALUE ( mart_retencion[veredicto] )
Base al cierre que ya estaba = SELECTEDVALUE ( mart_retencion[pct_base_retenida] )
IC 95% desde = SELECTEDVALUE ( mart_retencion[ic95_inf] )
IC 95% hasta = SELECTEDVALUE ( mart_retencion[ic95_sup] )
```

`SELECTEDVALUE` devuelve el valor solo cuando los filtros dejan exactamente una fila. Por eso cada visual tiene que filtrar `corte`, `valor`, `periodo` y `ventana_dias` (ver 2.4). Si la tarjeta aparece en blanco, falta un filtro.

En `mart_valor_riesgo`:

```
Margen anual en riesgo (M CLP) = SELECTEDVALUE ( mart_valor_riesgo[margen_anual_en_riesgo] ) / 1000000
```

**No escribir** medidas como `DIVIDE(SUM(retenidos), SUM(activos_inicio))` sobre varias filas ni recalcular quién está activo: esa lógica vive en la cadena.

Formato: las tasas con formato *Porcentaje, 1 decimal*; el margen con 2 decimales y el título "millones de CLP, margen bruto sin IVA, por año".

### 2.4 Una pantalla (anatomía de la clase 7)

Una página, de arriba hacia abajo:

1. **Título** (cuadro de texto): "¿Estamos reteniendo a nuestros clientes o solo reponiéndolos?" y debajo "Clientes con tarjeta · 10 locales incluida la Tienda Online · 2025".
2. **Filtros (segmentaciones):**
   - `ventana_dias` (30, 90, 180), con 90 seleccionado por defecto. Título: "Cliente activo = compró en los últimos… días".
   - `periodo` (2025Q2, 2025Q3, 2025Q4), con 2025Q4 por defecto.
   - Un cuadro de texto con la regla de lectura: "Un cliente se retiene si compró en los W días previos al inicio del trimestre y sigue activo al cierre. La cadena RETIENE si al menos el 50% de sus activos al cierre ya estaban al inicio; si no, REPONE si los que llegan cubren a los perdidos; si tampoco, SE ACHICA."
3. **Cifra clave** (tarjetas), con el filtro del visual `corte = Total`:
   - Retención (grande) · Nuevos por perdido · Veredicto · Margen anual en riesgo (filtrar `mart_valor_riesgo[ventana_dias]` con la misma segmentación) · Cobertura: tarjeta con `mart_kpi_resumen` filtrado a `kpi = pct_boletas_fuera_de_retencion`, mostrada como 1 − valor (84,9%).
4. **Gráfico que explica la cifra:** líneas con eje X = `periodo`, valor = `tasa_retencion`, filtro `corte = Total` (sin el filtro de período, para ver la tendencia).
5. **Corte por local:** barras horizontales, eje = `valor`, valor = `tasa_retencion`, filtro `corte = Tienda principal`; **ordenar alfabéticamente** (no como ranking, feedback E1). Agregar `ic95_inf` e `ic95_sup` en la información sobre herramientas, y una línea de referencia constante en el total (51,1% con 90 días).
6. **Detalle en tabla:** `mart_retencion` con `corte = Tienda principal`: valor, activos_inicio, retenidos, perdidos, tasa_retencion, ic95_inf, ic95_sup.
7. **Pie** (cuadro de texto + tarjeta): "Fuente: sistema de caja, maestro de productos, campañas 2025 e IPC (mindicador.cl), cadena bronce → plata → oro. Dueño de la métrica: Subgerente de Clientes y Fidelización. Dueño del dato: Jefe de BI." Una tarjeta con la `corrida` de la última fila de `historial_corridas` con `publicada = TRUE`, y otra con `estado` de `estado_fuentes` para el archivo del IPC (si dice `respaldo`, la API falló).

Opcional, en una segunda página (para la decisión, no para otra pregunta): una tabla con `mart_caso_contacto` (día de contacto, contactos, costo_total, tasa_equilibrio).

### 2.5 Verificar que los números son los mismos (obligatorio si se usa)

Antes de entregar, con los filtros indicados la pantalla tiene que mostrar exactamente:

| Ventana | Trimestre | Retención | Nuevos por perdido | Veredicto |
|---|---|---|---|---|
| 90 | 2025Q4 | 51,1% | 1,07 | Repone |
| 30 | 2025Q4 | 33,2% | 0,76 | Se achica |
| 180 | 2025Q4 | 82,5% | 2,34 | Retiene |
| 90 | 2025Q3 | 63,7% | 1,26 | Retiene |

Margen anual en riesgo con 90 días: 4,57 millones de CLP. Si algún número no calza, casi siempre es el problema de los decimales (2.2).

### 2.6 Cómo se actualiza

1. Correr `python cadena_datos/run_pipeline.py`.
2. En Power BI: **Inicio → Actualizar**.

Si la cadena falla una prueba que bloquea, no publica: `datos/oro/` queda con la última corrida buena y Power BI sigue mostrando esos datos. `historial_corridas.csv` registra la corrida fallida con `publicada = FALSE`.

### 2.7 Guardar y entregar

- Guardar como `prototipo/power_bi/retencion_multitienda.pbix` y subirlo a la rama `entrega-2`.
- Si cambias la carpeta de los CSV, Power BI pierde la ruta. Para que funcione en otro computador: **Transformar datos → Configuración de origen de datos → Cambiar origen** y apuntar a la carpeta `datos/oro/` de ese computador.
- En el informe, decir que la demo principal es Streamlit y que Power BI lee las mismas tablas con medidas que solo leen valores ya calculados (una sola definición).
