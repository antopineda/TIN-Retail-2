# Multitienda del Sur — Retención de clientes

Proyecto semestral IIC3752 Tecnologías para la Inteligencia de Negocio (PUC), caso Retail, Grupo 2.

Cadena de datos reproducible que integra las cuatro fuentes del caso, construye un modelo dimensional y calcula la
métrica que responde la pregunta de negocio:

> **¿La cadena está reteniendo a sus clientes o los está reponiendo con compradores de una sola vez?**

## Requisitos

- Python 3.10 o superior.
- Las dependencias de `cadena_datos/requirements.txt`: `pandas`, `numpy`, `matplotlib` y `pytest`.
- Conexión a internet para consultar la API del IPC. Si no hay conexión, la cadena usa un respaldo con los mismos
  valores y lo indica en la salida, así que el resultado es el mismo.

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

**Duración:** menos de un minuto (entre 15 y 30 segundos en un computador personal).

**Qué se espera ver al final:**
- seis pasos numerados de `[1/6]` a `[6/6]`;
- las 23 validaciones marcadas como `OK`;
- la línea `Listo en … s`.

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
[4/6] Validaciones
      OK    V01 Boletas plata = bronce − duplicados
      ...
      OK    V22 Embudo de cobertura cuadra: origen − exclusiones = compras usadas
[5/6] Documentación (diccionario, supuestos, log, resumen)
[6/6] Gráficos
      datos/oro/graficos/1_sensibilidad_ventana.png
      ...
Listo en 25.3 s. Salidas en .../datos
```

Si alguna validación crítica falla, la cadena termina con código de salida 1 y lo indica en pantalla.

Las cifras principales quedan en `datos/oro/resumen_hallazgos.md`. Por ejemplo, la retención del cuarto trimestre de
2025 con ventana de 90 días es **51,1%**.

### Pruebas

```bash
python -m pytest cadena_datos/tests -q
```

Resultado esperado: `65 passed`.

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
días, y también se reportan 30, 180 y 365 días como sensibilidad.

## Salidas principales (`datos/oro/`)

| Archivo | Contenido |
|---|---|
| `fact_venta_boleta.csv` y `dim_*.csv` | Modelo estrella |
| `mart_retencion.csv` | Retención por mes o trimestre, por ventana y por corte (total, local, formato, macrozona, segmento) |
| `mart_cohortes.csv` | Retención de cohortes de clientes por trimestre de llegada |
| `mart_cobertura.csv` | Registros excluidos del análisis y motivo |
| `mart_kpi_resumen.csv` | Cifras principales |
| `graficos/` | Visualizaciones, con su unidad en el título y su fuente al pie |
| `diccionario_datos.csv` | Definición de cada columna |
| `supuestos.csv` | Bitácora de supuestos |
| `log_calidad.csv` | Cada regla de limpieza con el número de registros afectados |
| `validaciones.csv` | Resultado de las validaciones automáticas |

## Estructura del repositorio

```
TIN-Retail-2/
├── origen/          fuentes de datos del caso
├── cadena_datos/    código de la cadena (detalle en cadena_datos/README.md)
│   ├── run_pipeline.py    punto de entrada
│   ├── config.py          parámetros y supuestos
│   └── tests/             pruebas unitarias
├── datos/oro/       resultados (se regeneran en cada ejecución)
└── exploracion/     perfilamiento inicial de las fuentes (solo lectura)
```

Los parámetros de negocio (período, ventanas de inactividad, supuestos) están en `cadena_datos/config.py`. Para
cambiar una definición, basta con editar ese archivo y volver a ejecutar la cadena.
