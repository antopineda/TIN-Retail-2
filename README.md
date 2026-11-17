# Multitienda del Sur — Retención de clientes

Proyecto semestral IIC3752 Tecnologías para la Inteligencia de Negocio (PUC), caso Retail, Grupo 2.

Cadena de datos reproducible que integra las cuatro fuentes del caso, construye un modelo dimensional y calcula la
métrica que responde la pregunta de negocio:

> **¿La cadena está reteniendo a sus clientes o los está reponiendo con compradores de una sola vez?**

## Requisitos

- Python 3.10 o superior.
- Las dependencias de `cadena_datos/requirements.txt`: `pandas`, `numpy`, `matplotlib`, `pytest`, `certifi`, `streamlit` y `altair`.
- Conexión a internet para consultar la API del IPC. Si no hay conexión, la cadena usa la última respuesta buena
  guardada en `cadena_datos/referencias/ipc_2025_snapshot.json`, lo avisa (prueba F05) y el prototipo lo muestra.
  La retención y el margen no dependen del IPC.

## Instalación

```bash
git clone https://github.com/antopineda/TIN-Retail-2.git
cd TIN-Retail-2
pip install -r cadena_datos/requirements.txt
```

## Ejecución

Desde la raíz del repositorio:

```bash
python cadena_datos/run_pipeline.py
```

**Duración:** menos de un minuto (unos 30 segundos la primera vez, 5 segundos las siguientes).

**Qué se espera ver al final:**
- seis pasos numerados de `[1/6]` a `[6/6]`;
- las 36 pruebas de calidad marcadas como `OK` y la línea `-> 36 de 36 pruebas en verde`;
- al final: `Retención Q4 2025 (90 días): 51.1%  ·  pruebas 36/36  ·  IPC: ok`.

La salida se ve así (abreviada):

```
[1/6] Bronce  <- .../origen
      origen_pos.sqlite                  942,080 bytes  sha256 4e9f0c36d2a9…  (copia)
      ...
[2/6] Plata   (reglas de limpieza)
      boletas            6,190 filas
      boleta_detalle    14,344 filas
[3/6] Oro     (modelo estrella + marts)
      fact_venta_boleta      6,190 filas
      mart_retencion         1,536 filas
      ...
[4/6] Pruebas de calidad
      OK    F01 Fuente SQLite (POS): están las 7 tablas y hay boletas
      ...
      OK    M08 Acuerdo de servicio, completitud: cada mes con >= 80% de boletas con tarjeta
      -> 36 de 36 pruebas en verde
[5/6] Documentación (diccionario, supuestos, log, resumen)
[6/6] Gráficos
      datos/oro/graficos/1_sensibilidad_ventana.png
      ...
Listo en 4.7 s. Salidas en .../datos
Retención Q4 2025 (90 días): 51.1%  ·  pruebas 36/36  ·  IPC: ok
```

Si alguna prueba que bloquea falla, la cadena **no publica** `datos/oro/` (queda la última corrida buena), deja el detalle en `datos/cuarentena/` y termina con código de salida 1.

Las cifras principales quedan en `datos/oro/resumen_hallazgos.md`. Por ejemplo, la retención del cuarto trimestre de
2025 con ventana de 90 días es **51,1%**.

### Pruebas

```bash
python -m pytest cadena_datos/tests -q
```

Resultado esperado: `71 passed`.

### Prototipo

Después de correr la cadena:

```bash
streamlit run prototipo/app.py
```

Se abre en el navegador (http://localhost:8501). La pantalla lee solo `datos/oro/`: si la cadena vuelve a correr,
basta con recargar la página. Responde la pregunta en una pantalla: cifra clave con su comparación, tendencia,
corte por local con su intervalo de confianza, el simulador de la decisión (a los cuántos días contactar, cuánto
cuesta y cuánto margen recupera) y el detalle en tablas. El pie muestra la fuente, la fecha de la última corrida,
las pruebas en verde y el dueño del dato.

Para mostrar qué pasa si la API del IPC no responde: `python cadena_datos/run_pipeline.py --simular-falla-api`.
Para mostrar qué pasa si falla una prueba que bloquea (oro no se publica y el prototipo avisa):
`python cadena_datos/run_pipeline.py --simular-falla-calidad`. Después, correr la cadena normal para volver a publicar.

## Versión Databricks (opcional)

La rama `databricks` agrega la misma cadena en Databricks (fuentes crudas en Unity Catalog, tablas Delta, job de 3 tareas
y tablero AI/BI), reutilizando el código de `cadena_datos/`. No cambia nada de la versión local. Ver
[`databricks/README.md`](databricks/README.md).

## Fuentes de datos

Las cuatro fuentes del caso están en `origen/` y nunca se modifican:

| Fuente | Formato | Contenido |
|---|---|---|
| `origen_pos.sqlite` | SQLite | Sistema de caja: boletas, detalle, clientes, tiendas, comunas, regiones y medios de pago |
| `origen_maestro_productos.csv` | CSV (Latin-1, `;`) | Maestro de productos |
| `origen_promociones.json` | JSON | Campañas de marketing 2025 |
| `https://mindicador.cl/api/ipc/2025` | API | Variación mensual del IPC |

## Cómo funciona

La cadena se organiza en tres capas (arquitectura medallón):

| Capa | Contenido | Se publica |
|---|---|---|
| `datos/bronce/` | Copia exacta de las fuentes, con su huella SHA-256 | No (contiene datos personales) |
| `datos/plata/` | Datos normalizados e integrados, con marcas de calidad | No (contiene datos personales) |
| `datos/oro/` | Modelo estrella, tablas de métricas, gráficos y documentación | Sí (sin datos personales) |

Las capas bronce y plata no se publican, pero se regeneran al ejecutar la cadena.

**Modelo dimensional.** Una fila de la tabla de hechos (`fact_venta_boleta`) es una boleta. Las dimensiones son
`dim_cliente`, `dim_tienda`, `dim_tiempo` y `dim_medio_pago`.

**Métrica.** La tasa de retención se calcula como:

```
tasa de retención = clientes activos al inicio que siguen activos al cierre / clientes activos al inicio
```

Un cliente está activo si tiene al menos una compra válida en los últimos *W* días. La ventana principal es de 90
días, y también se reportan 30 y 180 días como sensibilidad (365 días se retiró: con un año de datos da 100%). Cada métrica se define una sola vez en
`cadena_datos/metricas.py` (capa semántica); el resumen y el prototipo la leen de ahí.

Capas, decisiones de arquitectura, pruebas, linaje y acuerdo de servicio: [`docs/arquitectura.md`](docs/arquitectura.md).

## Salidas principales (`datos/oro/`)

| Archivo | Contenido |
|---|---|
| `fact_venta_boleta.csv` y `dim_*.csv` | Modelo estrella |
| `mart_retencion.csv` | Retención por mes o trimestre, por ventana y por corte (total, local, formato, macrozona, segmento) |
| `mart_cohortes.csv` | Retención de cohortes de clientes por trimestre de llegada |
| `mart_cobertura.csv` | Registros excluidos del análisis y motivo |
| `mart_valor_riesgo.csv` | Clientes perdidos en Q4 en venta y en margen, por ventana |
| `mart_caso_contacto.csv` | Costo y margen recuperado de contactar a los 30, 45, 60 y 75 días sin comprar |
| `mart_campanas.csv` | Vuelta a comprar de quienes usaron cada campaña vs. quienes no |
| `mart_perfil_local.csv` | Perfil de los clientes de cada local (una sola compra, ticket, margen) |
| `mart_kpi_resumen.csv` | Cifras principales |
| `graficos/` | Visualizaciones, con su unidad en el título y su fuente al pie |
| `diccionario_datos.csv` | Definición de cada columna |
| `supuestos.csv` | Bitácora de supuestos |
| `log_calidad.csv` | Cada regla de limpieza con el número de registros afectados |
| `validaciones.csv` | Resultado de las 36 pruebas de calidad de la última corrida (bloquea o avisa) |
| `estado_fuentes.csv` | Estado de cada fuente en la última corrida (ok o respaldo) |
| `historial_corridas.csv` | Una fila por corrida: si se publicó, pruebas en verde, estado del IPC y cifra principal |
| `historial_pruebas.csv` | Cada prueba de cada corrida, con cuántas filas fallaron |
| `metricas.csv` | Definición de cada métrica (capa semántica) |

## Estructura del repositorio

```
TIN-Retail-2/
├── origen/          fuentes de datos del caso
├── cadena_datos/    código de la cadena (detalle en cadena_datos/README.md)
│   ├── run_pipeline.py    punto de entrada
│   ├── config.py          parámetros y supuestos
│   ├── metricas.py        capa semántica (definición única de cada métrica)
│   └── tests/             pruebas unitarias
├── prototipo/       app.py: el prototipo (Streamlit)
├── docs/            arquitectura.md
├── datos/oro/       resultados (se regeneran en cada ejecución)
└── exploracion/     perfilamiento inicial de las fuentes (solo lectura)
```

Los parámetros de negocio (período, ventanas de inactividad, supuestos) están en `cadena_datos/config.py`. Para
cambiar una definición, basta con editar ese archivo y volver a ejecutar la cadena.
