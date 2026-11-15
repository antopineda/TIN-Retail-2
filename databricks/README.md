# Versión Databricks de la cadena (rama `databricks`)

Grupo 2 · Retail (Multitienda del Sur) · 15-11-2026

Esta carpeta lleva la misma cadena a Databricks: fuentes crudas en Unity Catalog, transformación en la plataforma, tablas Delta y un tablero AI/BI. **No reemplaza nada:** la versión local (Python + Streamlit) sigue intacta y funcionando igual.

> **Estado honesto:** los notebooks se probaron localmente con un Spark simulado: corren de punta a punta, las 51 tablas tienen tipos compatibles y la publicación condicionada funciona. **Todavía no se corrieron en un workspace real de Databricks.** La primera corrida en Databricks es el paso 2 de abajo; si algo falla, es ahí donde se va a ver.

## 1. Qué cambia respecto de la versión local

| | Local (rama `entrega-2`) | Databricks (esta rama) |
|---|---|---|
| Patrón | **ETL**: se transforma en Python antes de cargar a CSV | **ELT**: primero se cargan las fuentes crudas a la plataforma (Volume + tablas `bronce_*`) y después se transforman con el cómputo de Databricks |
| Capa cruda | `datos/bronce/` (no se sube a git) | Volume `/Volumes/<catálogo>/<esquema>/archivos/` + tablas Delta `bronce_*` (todo como texto) |
| Plata y oro | CSV en `datos/` | Tablas Delta `plata_*`, `fact_*`, `dim_*`, `mart_*` |
| Lógica | `cadena_datos/` | **El mismo código** de `cadena_datos/`, llamado desde el notebook 02 |
| Pruebas | 36 en cada corrida; oro se publica solo si pasan las que bloquean | Igual. Si fallan, el job termina en error y no toca plata ni oro |
| Historial | `historial_corridas.csv`, `historial_pruebas.csv` | Tablas Delta `historial_corridas`, `historial_pruebas` (se agregan), `cuarentena_validaciones` |
| Orquestación | `python cadena_datos/run_pipeline.py` | Job de 3 tareas (`databricks.yml`), programado mensual (pausado) |
| Prototipo | Streamlit (`prototipo/app.py`) | Tablero AI/BI sobre las vistas `v_*` |

**Una sola definición:** la fórmula de la retención, la regla retiene/repone y el margen siguen viviendo solo en `cadena_datos/metricas.py`. Las vistas del tablero no recalculan nada: seleccionan columnas que la cadena ya calculó. El notebook 03 verifica que el número del tablero sea el mismo del informe.

**Para el informe:** si el grupo presenta la versión Databricks, la decisión ETL/ELT cambia a **ELT** y hay que explicarlo así en la sección B. Si presenta la local, es ETL. No mezclar las dos en el mismo informe.

## 2. Ponerlo a correr (unos 30 minutos la primera vez)

1. **Cuenta:** crear una cuenta en Databricks Free Edition (gratis, con el correo de la universidad). Trae cómputo serverless y un catálogo llamado `workspace`.
2. **Traer el repositorio:** en el workspace, **Workspace → Create → Git folder**, pegar la URL del repositorio de GitHub y elegir la rama `databricks`. (Si el repositorio es privado, primero conectar GitHub en *Settings → Linked accounts*.)
3. **Correr a mano, en orden** (sirve para la primera prueba): abrir `databricks/notebooks/01_bronce`, conectarlo a *Serverless* y presionar *Run all*. Después `02_plata_oro` y `03_vistas_tablero`.
   - Al final del 02 tiene que decir `Publicada: True · pruebas 36/36`.
   - Al final del 03: `Retención Q4 2025 (90 días): tablero 51,1% · informe 51,1% · veredicto: Repone`.
   - Si el 01 dice que la API del IPC no respondió, es esperable en Free Edition (red restringida): se usa el último snapshot bueno y la prueba F05 queda en aviso. La retención y el margen no cambian.
4. **Crear el job** (para la demo y el acuerdo de servicio):
   - *Con la CLI de Databricks:* desde la raíz del repositorio, `databricks bundle deploy` y después `databricks bundle run cadena_retail`.
   - *Sin CLI:* **Jobs & Pipelines → Create job**, 3 tareas tipo *Notebook* desde el Git folder: `bronce` (01), `plata_oro` (02, depende de bronce) y `vistas_tablero` (03, depende de plata_oro). Parámetros del job: `catalogo = workspace`, `esquema = retail_g2`. Programación: mensual, día 3, 7:00, America/Santiago.
5. **Demostrar la falla de calidad:** correr el notebook 02 con el parámetro `simular_falla_calidad = si`. El notebook termina en error, `historial_corridas` registra la corrida con `publicada = false` y las tablas de oro no cambian. Después, volver a correrlo con `no`.

## 3. Armar el tablero AI/BI (una pantalla, anatomía de la clase 7)

**Dashboards → Create dashboard.** En la pestaña *Data*, agregar estos datasets (cambiar `workspace.retail_g2` si usaron otro esquema):

```sql
-- retencion
SELECT * FROM workspace.retail_g2.v_retencion_trimestral
-- locales
SELECT * FROM workspace.retail_g2.v_retencion_local ORDER BY local
-- margen
SELECT * FROM workspace.retail_g2.v_margen_en_riesgo
-- cobertura
SELECT * FROM workspace.retail_g2.v_cobertura_y_una_sola_vez
-- pie
SELECT * FROM workspace.retail_g2.v_pie
-- caso
SELECT * FROM workspace.retail_g2.v_caso_contacto
```

En la pestaña del lienzo, de arriba hacia abajo:

1. **Título** (texto): "¿Estamos reteniendo a nuestros clientes o solo reponiéndolos?" y debajo la regla de lectura: "Un cliente se retiene si compró en los W días previos al inicio del trimestre y sigue activo al cierre. La cadena RETIENE si al menos el 50% de sus activos al cierre ya estaban al inicio; si no, REPONE si los que llegan cubren a los perdidos; si tampoco, SE ACHICA."
2. **Filtros** (widget *Filter → Single value*):
   - `ventana_dias`, aplicado a los datasets *retencion*, *locales* y *margen*. Valor por defecto: 90. Título: "Cliente activo = compró en los últimos… días (90 oficial, 30 alternativa)".
   - `trimestre`, aplicado a *retencion* y *locales*. Valor por defecto: 2025Q4.
3. **Cifra clave** (widgets *Counter*, del dataset *retencion*):
   - `tasa_retencion` (formato porcentaje, 1 decimal), con `tasa_trimestre_anterior` en un segundo contador al lado como comparación.
   - `indice_reposicion` ("Nuevos por cada perdido") y `veredicto`.
   - Del dataset *margen*: `margen_anual_en_riesgo_millones_clp`, con el título "Margen anual en riesgo (millones de CLP, margen bruto sin IVA)".
   - Del dataset *cobertura*: `cobertura_boletas` (porcentaje).
4. **Gráfico que explica la cifra:** *Line*, dataset *retencion*, eje X `trimestre`, eje Y `tasa_retencion`. Este gráfico no lleva el filtro de trimestre (quitarlo en *Filter → Datasets*), para que muestre la tendencia.
5. **Corte por local:** *Bar* horizontal, dataset *locales*, eje Y `local` **ordenado por nombre** (no ranking), eje X `tasa_retencion`. Agregar `ic95_inf`, `ic95_sup` y `activos_inicio` al tooltip.
6. **Detalle:** *Table* con el dataset *locales* (local, activos_inicio, retenidos, perdidos, tasa_retencion, ic95_inf, ic95_sup).
7. **Pie:** *Text* con "Fuente: sistema de caja, maestro de productos, campañas 2025 e IPC (mindicador.cl). Cadena bronce → plata → oro en Databricks. Dueño de la métrica: Subgerente de Clientes y Fidelización. Dueño del dato: Jefe de BI.", más un *Table* pequeño con el dataset *pie* (última corrida publicada, pruebas, estado de la API).
8. Opcional, segunda página (para la decisión): *Table* con el dataset *caso*.

**Publicar:** botón *Publish*. Para la demo, abrir el tablero publicado y mostrar que al cambiar la ventana a 180 el veredicto pasa a "Retiene".

### Verificación (tiene que dar exactamente esto)

| Ventana | Trimestre | Retención | Nuevos por perdido | Veredicto |
|---|---|---|---|---|
| 90 | 2025Q4 | 51,1% | 1,07 | Repone |
| 30 | 2025Q4 | 33,2% | 0,76 | Se achica |
| 180 | 2025Q4 | 82,5% | 2,34 | Retiene |
| 90 | 2025Q3 | 63,7% | 1,26 | Retiene |

Margen anual en riesgo con 90 días: 4,57 millones de CLP.

## 4. Límites conocidos

- **El simulador de la decisión** (cambiar día de contacto, costo y tasa) existe solo en Streamlit. En el tablero AI/BI se muestra la tabla fija de 30, 45, 60 y 75 días. Replicarlo en SQL sería una segunda fórmula.
- **Linaje en Unity Catalog:** Databricks dibuja solo el linaje de las vistas → tablas → tablero. El tramo bronce → plata → oro no aparece automáticamente, porque la transformación corre en pandas y no en Spark; ese linaje está documentado en `docs/arquitectura.md`.
- **Plata sin datos personales:** `plata_clientes` se publica sin RUT ni nombre. Las versiones con RUT existen solo en el disco temporal del cómputo, mientras corre el notebook 02.
- **Cómputo:** Free Edition tiene cuotas de uso. Una corrida completa de los 3 notebooks toma pocos minutos.

## 5. Archivos

| Archivo | Qué hace |
|---|---|
| `databricks/notebooks/_comun.py` | Parámetros (catálogo y esquema), ubica el repositorio, crea el esquema y el Volume, y guarda tablas Delta |
| `databricks/notebooks/01_bronce.py` | Fuentes al Volume (con su huella SHA-256), API del IPC con respaldo, y tablas `bronce_*` como texto |
| `databricks/notebooks/02_plata_oro.py` | Corre `cadena_datos/run_pipeline.ejecutar()`. Publica plata y oro solo si pasan las pruebas; si no, cuarentena y error |
| `databricks/notebooks/03_vistas_tablero.py` | Vistas `v_*` para el tablero, más el control de que el número del tablero es el del informe |
| `databricks.yml` | Job de 3 tareas, programación mensual pausada |
