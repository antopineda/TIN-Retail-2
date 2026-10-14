# cadena_datos

Código de la cadena de datos. Instrucciones de instalación y ejecución en el [README principal](../README.md).

```
origen/ ──► BRONCE ──► PLATA ──► ORO ──► validaciones ──► documentación ──► gráficos
            copia      limpieza  estrella   23 chequeos    diccionario,      visualizaciones
            + hash     R01–R27   + marts    (exit 1 si     bitácora, log
            + IPC                           falla crítica)
```

## Módulos

| Archivo | Qué hace |
|---|---|
| `run_pipeline.py` | Punto de entrada. Ejecuta las seis etapas en orden. |
| `config.py` | Rutas, parámetros de negocio (período, ventanas, mapeos) y bitácora de supuestos S01–S16. |
| `limpieza.py` | Funciones de limpieza: fechas en cuatro formatos, montos, descuentos, RUT y categorías. |
| `etapa_bronce.py` | Copia fiel de las fuentes con su huella SHA-256 y snapshot de la API del IPC. |
| `etapa_plata.py` | Reglas de limpieza R01–R27. Cada regla registra cuántos registros afecta. |
| `retencion.py` | Lógica de cliente activo, retenido, perdido, nuevo y reactivado. |
| `etapa_oro.py` | Dimensiones, hechos, tablas de métricas y KPIs. |
| `validaciones.py` | Integridad, conciliación de montos, ausencia de datos personales y coherencia de las métricas. |
| `documentacion.py` | Diccionario de datos, bitácora de supuestos, log de calidad y resumen de hallazgos. |
| `graficos.py` | Visualizaciones con su unidad en el título y su fuente al pie. |
| `referencias/feriados_chile_2025.csv` | Calendario de feriados (fuente externa al caso). |
| `tests/` | Pruebas unitarias de las reglas de limpieza y de la lógica de retención. |

## Opciones de ejecución

```bash
python cadena_datos/run_pipeline.py --refrescar-ipc     # vuelve a consultar la API del IPC
python cadena_datos/run_pipeline.py --fuente RUTA        # usa otra carpeta de origen (por defecto: origen/)
```

## Definiciones clave

- **Compra válida:** boleta de 2025, con cliente identificado y venta neta mayor que cero. Las boletas duplicadas se cuentan una sola vez.
- **Cliente activo (W):** tiene al menos una compra válida en los últimos W días. W = 90 es la ventana principal; 30, 180 y 365 se usan como sensibilidad.
- **Tasa de retención:** clientes activos al inicio del período que siguen activos al cierre, divididos por los clientes activos al inicio.
- **Cliente nuevo:** alta en 2025 y primera compra en el período. Los clientes con alta anterior a 2025 se tratan como previos.
- **`base_confiable`:** indica que hay al menos W días de historia antes del período. Sin datos de 2024, el primer trimestre no tiene base confiable.

Todos los supuestos, con su justificación y su efecto sobre el resultado, están en `config.py` y en `datos/oro/supuestos.csv`.
