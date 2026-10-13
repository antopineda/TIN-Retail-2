# Cadena de datos ejecutable — Multitienda del Sur (Retail, grupo_2)

Lleva las fuentes del caso desde su estado crudo hasta tablas confiables para responder
**¿la cadena está reteniendo a sus clientes o los está reponiendo con compradores de una sola vez?**

```
origen/ ────────► BRONCE ──► PLATA ──► ORO ──► validaciones ──► documentación
                    copia      limpieza  estrella   22 chequeos    diccionario, supuestos,
                    + hash     R01–R27   + marts    (exit 1 si     log de calidad,
                    + IPC                           falla crítica) resumen de hallazgos
```

## Cómo correrla

Requisitos: Python 3.10+ con `pandas` y `numpy` (`pip install -r cadena_datos/requirements.txt`).

Desde la raíz del repositorio:

```bash
python cadena_datos/run_pipeline.py
```

Opciones:

- `--refrescar-ipc`: vuelve a consultar la API del IPC. Por defecto se usa el snapshot guardado en bronce, así la cadena es reproducible sin internet.
- `--fuente RUTA`: usa otra carpeta de origen. Por defecto es `origen/`.

La corrida completa toma unos 10 segundos. Termina con código 1 si falla alguna validación crítica.

Tests de las reglas de limpieza y de la lógica de retención:

```bash
python -m pytest cadena_datos/tests -q
```

## Estructura

| Archivo | Qué hace |
|---|---|
| `config.py` | Rutas, parámetros de negocio (período, ventanas, mapeos) y **supuestos S01–S16**. Si la contraparte responde algo distinto, se cambia aquí y se vuelve a correr la cadena. |
| `limpieza.py` | Funciones puras de limpieza: fechas en 4 formatos, montos, descuentos, RUT, tipo de cliente, categorías. |
| `etapa_bronce.py` | Copia fiel de las fuentes, manifiesto SHA-256 y snapshot del IPC. |
| `etapa_plata.py` | Reglas R01–R27. Cada regla registra cuántas filas afecta. |
| `retencion.py` | Lógica de cliente activo, retenido, perdido, nuevo y reactivado. |
| `etapa_oro.py` | Dimensiones, hechos, marts y KPIs. |
| `validaciones.py` | Integridad, conciliación de montos, ausencia de datos personales y coherencia de los marts. |
| `documentacion.py` | Diccionario de datos, supuestos, log y `resumen_hallazgos.md`. |
| `referencias/feriados_chile_2025.csv` | Calendario de feriados (fuente externa, no viene en el caso). |

## Salidas (`datos/`)

| Carpeta | Contenido | ¿Se comparte? |
|---|---|---|
| `bronce/` | Copia exacta de las fuentes + `manifiesto_bronce.csv` + `ipc_2025_raw.json` | No: contiene RUT y nombres |
| `plata/` | Tablas limpias y tipadas con flags de calidad | No: `clientes.csv` contiene RUT y nombres (uso interno) |
| `oro/` | Modelo estrella + marts + documentación | **Sí: esto es lo que recibe reportería** |

Todos los CSV están en UTF-8 (con BOM, para que Excel muestre bien las tildes), separados por coma, con punto decimal y fechas AAAA-MM-DD.

### Tablas oro para reportería

| Tabla | Grano | Para qué |
|---|---|---|
| `fact_venta_boleta` | 1 boleta | Hecho principal (grano del informe). Filtrar `en_periodo = True`. |
| `fact_venta_linea` | 1 línea de boleta | Preguntas futuras de producto y promociones. |
| `dim_cliente`, `dim_tienda`, `dim_tiempo`, `dim_medio_pago`, `dim_producto`, `dim_campana` | — | Dimensiones del modelo estrella. `cliente_key = -1` es el cliente anónimo. |
| `mart_retencion` | corte × valor × período × ventana | **Gráfico principal de P1.** Filtrar `ventana_dias = 90` y `base_confiable = True`. |
| `mart_cohortes` | cohorte × trimestre | Curvas de cohorte. Usar `tipo_cohorte = "Nuevo 2025"`. |
| `mart_cliente_mes` | cliente × mes | Estado de cada cliente mes a mes (nuevo, recurrente, reactivado, inactivo…). |
| `mart_rfm_cliente` | 1 cliente | Recencia, frecuencia, monto y actividad al 31-12-2025. |
| `mart_venta_mensual` | corte × mes | Contexto: venta nominal/real y % identificado. |
| `mart_kpi_resumen` | 1 KPI | Cifras de cabecera para el dashboard y el PPT. |
| `diccionario_datos.csv` | 1 columna | Definición de cada columna (la "biblia del dato"). |
| `supuestos.csv`, `log_calidad.csv`, `validaciones.csv` | — | Anexos del informe. |
| `resumen_hallazgos.md` | — | Hallazgos con cifras, regenerado en cada corrida. |

## Definiciones clave

- **Compra válida**: boleta identificada, de 2025, con venta neta > 0. Las boletas con solo devoluciones no cuentan.
- **Cliente activo (W)**: tiene al menos una compra válida en los últimos W días. La ventana principal es W = 90; también se calculan 30 y 180 como sensibilidad.
- **Retención del período**: de los activos al inicio, cuántos siguen activos al cierre (`retenidos / activos_inicio`).
- **Nuevo**: primera compra observada en el período y alta en 2025.
- **Primera obs. previo**: cliente con alta antes de 2025 que vemos comprar por primera vez. Se separa de "nuevo" porque no hay datos de 2024.
- **`base_confiable`**: hay al menos W días de historia antes del período. Antes de eso, los activos al inicio están subestimados por falta de datos de 2024.

## Supuestos

La contraparte respondió el 13-10 (ver el README principal). La cadena opera bajo los supuestos S01–S16 de `config.py` (también exportados a `oro/supuestos.csv`). Los más relevantes:

- **S02**: la venta es el `monto_linea` registrado, sumado por boleta. La diferencia con el monto recalculado es de 0,8% en 2025.
- **S06** (confirmado 13-10): la fecha de alta no es la primera compra ni la inscripción; no se corrige. Nuevo = alta en 2025 y primera compra en el período.
- **S07** (confirmado 13-10): tipo de cliente = segmento + local. Persona/negocio (`clasificacion_nombre`) es una clasificación del equipo, solo complementaria.
- **S08** (confirmado 13-10): Online es un décimo punto de venta, se incluye en el cálculo principal y tiene macrozona "Online".
