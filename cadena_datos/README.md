# cadena_datos

Código de la cadena de datos. Instrucciones de instalación y ejecución en el [README principal](../README.md).
Capas, decisiones, pruebas, linaje y acuerdo de servicio en [`docs/arquitectura.md`](../docs/arquitectura.md).

```
origen/ ──► BRONCE ──► PLATA ──► ORO ──► pruebas ──► documentación ──► gráficos ──► prototipo/app.py
            copia      limpieza  estrella   36 pruebas   diccionario,      visualizaciones  (lee oro +
            + hash     R01–R27   + marts    (exit 1 si   bitácora, log                     metricas.py)
            + IPC                + margen   alguna que
                                            bloquea falla)
```

## Módulos

| Archivo | Qué hace |
|---|---|
| `run_pipeline.py` | Punto de entrada. Ejecuta las seis etapas en orden. |
| `config.py` | Rutas, parámetros de negocio (período, ventanas, mapeos, margen, caso de contacto, dueño y acuerdo de servicio) y bitácora de supuestos S01–S21. |
| `metricas.py` | Capa semántica: nombre, fórmula, unidad y regla de lectura de cada métrica; intervalo de Wilson; margen; caso de contacto. La usan la cadena y el prototipo. |
| `limpieza.py` | Funciones de limpieza: fechas en cuatro formatos, montos, descuentos, RUT y categorías. |
| `etapa_bronce.py` | Copia fiel de las fuentes con su huella SHA-256 y snapshot de la API del IPC. Si la API falla, usa `referencias/ipc_2025_snapshot.json` y lo marca como respaldo. |
| `etapa_plata.py` | Reglas de limpieza R01–R27. Cada regla registra cuántos registros afecta. |
| `retencion.py` | Lógica de cliente activo, retenido, perdido, nuevo y reactivado. |
| `etapa_oro.py` | Dimensiones, hechos (con margen bruto), tablas de métricas, caso de negocio, campañas, perfil por local y KPIs. |
| `validaciones.py` | 36 pruebas: una por fuente (F01–F05), integridad y privacidad (V01–V22), y las que protegen la métrica (M01–M08). Cada una bloquea o avisa. |
| `documentacion.py` | Diccionario de datos, bitácora de supuestos, log de calidad y resumen de hallazgos. |
| `graficos.py` | Visualizaciones con su unidad en el título y su fuente al pie. |
| `referencias/feriados_chile_2025.csv` | Calendario de feriados (fuente externa al caso). |
| `referencias/ipc_2025_snapshot.json` | Última respuesta buena de la API del IPC (respaldo, S21). |
| `tests/` | Pruebas unitarias de las reglas de limpieza, la lógica de retención y la capa semántica (71). |

## Opciones de ejecución

```bash
python cadena_datos/run_pipeline.py --refrescar-ipc     # vuelve a consultar la API del IPC
python cadena_datos/run_pipeline.py --fuente RUTA        # usa otra carpeta de origen (por defecto: origen/)
python cadena_datos/run_pipeline.py --simular-falla-api  # demostración: la API del IPC no responde
python cadena_datos/run_pipeline.py --simular-falla-calidad  # demostración: falla una prueba que bloquea; oro no se publica
```

## Definiciones clave

- **Compra válida:** boleta de 2025, con cliente identificado y venta neta mayor que cero. Las boletas duplicadas se cuentan una sola vez.
- **Cliente activo (W):** tiene al menos una compra válida en los últimos W días. W = 90 es la ventana principal; 30 y 180 se usan como sensibilidad (365 se retiró: con un año de datos da 100% por construcción).
- **Tasa de retención:** clientes activos al inicio del período que siguen activos al cierre, divididos por los clientes activos al inicio.
- **Cliente nuevo:** alta en 2025 y primera compra en el período. Los clientes con alta anterior a 2025 se tratan como previos.
- **Margen bruto:** venta sin IVA (venta / 1,19) − unidades × costo unitario del maestro, en CLP nominales (S17).
- **Margen anual en riesgo:** margen trimestral típico de los clientes perdidos en el trimestre × 4 (S20).
- **`base_confiable`:** indica que hay al menos W días de historia antes del período. Sin datos de 2024, el primer trimestre no tiene base confiable.

Todos los supuestos, con su justificación y su efecto sobre el resultado, están en `config.py` y en `datos/oro/supuestos.csv`.
