# TIN Retail — Grupo 2 · Multitienda del Sur SpA

Proyecto semestral IIC3752 (Tecnologías para la Inteligencia de Negocio), caso Retail, set de datos 2.

**Pregunta de negocio:** ¿la cadena está reteniendo a sus clientes o los está reponiendo con compradores de una sola vez?

Este repositorio contiene la **primera parte de la cadena**: inspección, limpieza, integración y procesamiento de los
datos, hasta dejar tablas confiables que el subgrupo de reportería usa para gráficos, dashboard y presentación.

---

## Estructura

```
TIN-Retail-2/
├── origen/                  datos entregados por la empresa (no se modifican nunca)
│   ├── origen_pos.sqlite             sistema de caja: boletas, detalle, clientes, tiendas, comunas, regiones, medios de pago
│   ├── origen_maestro_productos.csv  maestro de productos del área Comercial
│   └── origen_promociones.json       campañas de marketing 2025
├── cadena_datos/            código de la cadena ejecutable (ver cadena_datos/README.md para el detalle técnico)
├── datos/
│   ├── bronce/   (no se sube: tiene RUT y nombres; se regenera)
│   ├── plata/    (no se sube: tiene RUT y nombres; se regenera)
│   └── oro/      ← tablas finales para reportería (sin datos personales)
├── exploracion/             scripts del diagnóstico inicial (solo lectura) y sus salidas
└── reportes/
    └── diagnostico_retail_set2.html  diagnóstico de calidad de datos + plan de trabajo (abrir en el navegador)
```

## Cómo correrlo

Requisitos: Python 3.10 o superior, con `pandas` y `numpy`.

```bash
pip install -r cadena_datos/requirements.txt
python cadena_datos/run_pipeline.py
```

Se corre desde la raíz del repositorio y tarda unos 10–20 segundos. Al final debe decir `Listo` y mostrar las
validaciones en `OK`. Las tablas quedan en `datos/oro/`.

Para correr los tests de las reglas de limpieza y de la lógica de retención:

```bash
python -m pytest cadena_datos/tests -q
```

---

## Qué hicimos, paso a paso

### Paso 1 — Diagnóstico de los datos

Antes de limpiar nada, perfilamos cada tabla para medir sus problemas reales: nulos, duplicados, formatos,
llaves que no cruzan y valores imposibles. Los scripts están en `exploracion/` y el informe completo en
`reportes/diagnostico_retail_set2.html`, que incluye:

- el entendimiento del caso y la "prueba ácida" de cada pregunta de negocio,
- el perfilamiento tabla por tabla, con cada hallazgo etiquetado como **verbalizado** (lo dijo la contraparte),
  **medido** (lo contamos en los datos) o **inferido** (conclusión nuestra),
- el plan de trabajo, las decisiones que tomamos y las preguntas que enviamos a la contraparte.

Los hallazgos principales fueron:

- Fechas de boleta en 4 formatos distintos y 61 boletas duplicadas.
- Columnas de mes y región que contradicen a la fecha y a la tienda.
- Montos guardados como texto, con separadores mezclados, y descuentos escritos de 7 formas.
- La fecha de alta del cliente no corresponde a su primera compra, como se dijo en la reunión.
- El canal Online existe desde enero y concentra el 25% de las boletas, aunque en la reunión se dijo que había partido hace poco.

### Paso 2 — Arquitectura bronce → plata → oro

Organizamos el procesamiento en tres capas, cada una más limpia que la anterior. Es el esquema "medallón" visto en clase.

| Capa | Qué es | Regla de oro | Dónde |
|---|---|---|---|
| **Bronce** | Los datos **tal como llegaron**. Es una copia exacta, que sirve para volver al origen si algo sale mal. | No se toca nada. | `datos/bronce/` |
| **Plata** | Los datos **limpios e integrados**: tipos correctos, formatos unificados, llaves que cruzan y marcas (*flags*) en los registros dudosos. | Marcar antes que borrar. | `datos/plata/` |
| **Oro** | Los datos **listos para el negocio**: el modelo estrella (hechos y dimensiones) y tablas resumidas con las métricas de retención. | Sin datos personales y con definiciones documentadas. | `datos/oro/` |

### Paso 3 — Bronce: copia fiel

`cadena_datos/etapa_bronce.py` hace lo siguiente:

- Copia los 3 archivos de `origen/` y calcula su huella digital (SHA-256) en `manifiesto_bronce.csv`. Si la copia no es idéntica al original, la cadena se detiene.
- Consulta la API del IPC (`mindicador.cl`) y guarda la respuesta. Así la cadena se puede volver a correr sin internet y siempre da el mismo resultado.

### Paso 4 — Plata: limpieza (27 reglas)

`cadena_datos/etapa_plata.py` aplica una regla por cada problema del diagnóstico y anota en
`datos/oro/log_calidad.csv` cuántos registros afectó. **Solo se eliminan duplicados exactos y filas basura.**
Todo lo demás se corrige o se marca con un flag, para no perder información.

| Tabla | Problema | Qué hace la cadena | Registros |
|---|---|---|---|
| boletas | Boletas repetidas idénticas | Se elimina la copia | 61 |
| boletas | Fechas en 4 formatos (`2025-07-25`, `06/07/2025`, `09-10-25`, `19-dic-2025`) | Se convierten todas a fecha | 4.656 |
| boletas | Boletas con fecha de 2026 | Se marcan como fuera de período y quedan fuera de las métricas | 37 |
| boletas | Columna `mes` que no coincide con la fecha | Se descarta; el mes se saca de la fecha | 438 |
| boletas | Columna `region` que no coincide con la tienda | Se descarta; la región se saca de la tienda | 397 |
| boletas | Boletas sin cliente (anónimas) | Se asignan al cliente "Anónimo" (−1); cuentan en ventas pero no en retención | 807 |
| comunas | La Florida apunta a una región inexistente (9) | Se corrige a Metropolitana | 1 |
| detalle | Precios y montos guardados como texto (`1.940`, `-.905`) | Se convierten a número | 6.931 |
| detalle | Descuento escrito de 7 formas (`10`, `10%`, `0,10`…) | Se convierte a porcentaje (0, 10 o 25) | 2.465 |
| detalle | Dos productos con el mismo número de línea | Se renumeran las líneas; no se borra nada | 790 |
| detalle | El monto registrado no cuadra con cantidad × precio − descuento | Se usa el registrado y el calculado queda como control (diferencia total: 0,8%) | 717 |
| detalle | Cantidades negativas (devoluciones) | Se marcan; restan de la venta | 143 |
| detalle | Compras de 10 a 40 unidades | Se marcan como volumen mayorista; se conservan | 57 |
| detalle | Productos que no están en el maestro (SKU-9xxx) | Se conservan como "Producto sin maestro" | 215 |
| detalle | Descuento de 10% sin campaña, solo con tarjeta | Se clasifica como beneficio de la tarjeta | 3.103 |
| clientes | RUT en formatos mezclados; 16 con dígito verificador inválido | Se normalizan y se validan; el RUT **no pasa a oro** | 849 |
| clientes | El tipo de cliente solo se deduce del nombre (Distribuidora, Kiosco, Sra., Familia…) | Se crea `tipo_cliente` (Negocio / Persona-Hogar) y el nombre **no pasa a oro** | 1.200 |
| clientes | Fecha de alta en 2 formatos | Se convierte a fecha | 600 |
| productos | Archivo en codificación Latin-1 (tildes rotas en UTF-8) | Se lee correctamente y se guarda en UTF-8 | 84 |
| productos | Encabezado repetido y fila "TOTAL" | Se eliminan | 2 |
| productos | 26 formas de escribir 8 categorías (`ABARR`, `abarrotes`, `LACT`…) | Se unifican en 8 categorías | 131 |
| productos | Precios con `$`, coma decimal o `N/A` | Se convierten a número | 184 |
| productos | SKU-0001 duplicado | Se conserva la fila activa | 1 |
| campañas | Descuento como `"25%"` en una campaña y `50` en otra | Se convierte a número | 1 |
| IPC | La API entrega variación mensual, no un índice | Se construye un índice con base dic-2024 = 100 | 12 |

### Paso 5 — Oro: modelo estrella y tablas de retención

`cadena_datos/etapa_oro.py` construye lo siguiente:

**Modelo estrella** (grano: **una boleta**, como se declaró en el informe):

- `fact_venta_boleta`: el hecho principal, con una fila por boleta (venta, unidades, descuento, devoluciones y flags).
- `fact_venta_linea`: el detalle por producto, para preguntas futuras sobre productos o promociones.
- Dimensiones: `dim_cliente` (sin RUT ni nombre), `dim_tienda`, `dim_tiempo` (con feriados e IPC), `dim_medio_pago`, `dim_producto` y `dim_campana`.

**Tablas de métricas** (*marts*):

| Tabla | Qué responde |
|---|---|
| `mart_retencion` | Por mes o trimestre: cuántos clientes estaban activos, cuántos se retuvieron, se perdieron, llegaron nuevos o volvieron. Incluye ventanas de 30, 90 y 180 días, con cortes por tienda, formato, macrozona, tipo de cliente y segmento. **Es la tabla principal para P1.** |
| `mart_cohortes` | De los clientes que llegaron en cada trimestre, qué porcentaje sigue comprando después. |
| `mart_cliente_mes` | El estado de cada cliente mes a mes: nuevo, recurrente, reactivado o inactivo. |
| `mart_rfm_cliente` | Recencia, frecuencia y monto de cada cliente al 31-12-2025, y si compró una sola vez. |
| `mart_venta_mensual` | Venta nominal y real (con IPC) y porcentaje de ventas con tarjeta, por mes. |
| `mart_kpi_resumen` | Las cifras de cabecera para el dashboard y la presentación. |

**Cómo se mide la retención.** Un cliente está **activo** si compró en los últimos *W* días (principal: 90). Para
cada período se comparan los activos al inicio con los activos al final:

- **retenidos** = activos al inicio que siguen activos al final → **tasa de retención** = retenidos / activos al inicio
- **perdidos** = activos al inicio que ya no lo están al final
- **nuevos** = llegaron por primera vez (alta en 2025) · **reactivados** = habían comprado antes, estaban inactivos y volvieron
- **índice de reposición** = nuevos / perdidos (menor que 1 significa que no alcanza a reponer lo que pierde)

Usamos 90 días porque el 92,8% de las recompras ocurre dentro de ese plazo. La empresa piensa en 30 días, así que
también reportamos 30 y 180 días para mostrar cuánto cambia el resultado según la definición.

### Paso 6 — Validaciones automáticas

`cadena_datos/validaciones.py` revisa 22 condiciones en cada corrida. Si una crítica falla, la cadena termina con
error y no entrega datos inconsistentes. Entre otras:

- No se pierden líneas de detalle entre bronce y plata.
- Todas las llaves del modelo estrella cruzan con sus dimensiones.
- La suma de las líneas es igual a la suma de las boletas.
- Oro no contiene RUT ni nombres.
- Las cuentas de retención cuadran (activos al final = retenidos + nuevos + reactivados + primeras compras de clientes antiguos).

El resultado queda en `datos/oro/validaciones.csv`.

### Paso 7 — Documentación generada

En cada corrida se regeneran, dentro de `datos/oro/`:

- `diccionario_datos.csv`: qué significa cada columna de cada tabla (la "biblia del dato" que pidió la empresa).
- `supuestos.csv`: los supuestos S01–S16.
- `log_calidad.csv`: cada regla de limpieza con su conteo.
- `resumen_hallazgos.md`: las cifras principales, siempre actualizadas.

---

## Supuestos

Enviamos 3 preguntas a la contraparte y no hubo respuesta, así que la cadena trabaja bajo supuestos. Todos están en
`cadena_datos/config.py`: si la empresa responde distinto, se cambia ese archivo y se vuelve a correr la cadena.

| Id | Supuesto |
|---|---|
| S01 | El período es enero–diciembre de 2025; las 37 boletas de 2026 quedan fuera de las métricas. |
| S02 | La venta de una boleta es la suma de sus montos registrados (grano boleta). |
| S03 | Los precios incluyen IVA. |
| S04 | Las devoluciones restan; una boleta con venta neta ≤ 0 no cuenta como compra. |
| S05 | El descuento de 10% sin campaña es un beneficio de la tarjeta. |
| S06 | La fecha de alta es la inscripción. Nuevo = alta en 2025; previo = alta antes de 2025. |
| S07 | Se reportan dos cortes de "tipo de cliente": el segmento de la tarjeta y persona/negocio. |
| S08 | El canal Online se incluye, con un filtro para excluirlo si hace falta. |
| S09 | El local de un cliente es donde más compra. |
| S10 | Un cliente es una tarjeta, que corresponde a un hogar. |
| S11 | Ventana principal de 90 días; 30 y 180 como sensibilidad. |
| S12–S16 | Duplicados, columnas redundantes, productos sin maestro, datos personales y deflactor IPC (ver `supuestos.csv`). |

## Qué deja como resultado

Las tablas de `datos/oro/` son lo que recibe reportería. Las cifras principales están en
`datos/oro/resumen_hallazgos.md`, que se regenera en cada corrida. Al 10-10-2026:

- **La definición de "activo" cambia mucho la respuesta:** al 31-12-2025 hay 30,8% de clientes activos con ventana de 30 días, 56,5% con 90 días y 81,1% con 180 días.
- La retención trimestral (90 días) es de 62–64% en Q2 y Q3 y **cae a 51,1% en Q4**.
- En Q4 se perdieron 287 clientes y llegaron 306 nuevos (índice de reposición 1,07): la cadena **apenas repone lo que pierde**.
- El 29,9% de los clientes compró una sola vez.
- Ni el segmento (Clásico/Plus/Black) ni el tipo de cliente (persona/negocio) cambian la retención (todos entre 47% y 53%). El formato Híper es el más bajo (40%).

## Recomendaciones para después

**Para reportería**

- Usar `mart_retencion` filtrando `ventana_dias = 90` y `base_confiable = True`. Antes de abril los datos no alcanzan para medir con 90 días, porque no hay información de 2024.
- Un gráfico que vale la pena: la misma retención con 30, 90 y 180 días. Muestra por qué la empresa necesita una definición común.
- Para las curvas de cohorte, usar `mart_cohortes` con `tipo_cohorte = "Nuevo 2025"`. La cohorte de Q1 "Todos" mezcla clientes antiguos.
- Mostrar `tipo_cliente` como una inferencia a partir del nombre, no como un dato oficial.

**Para el informe**

- La sección "Cadena de datos ejecutable" puede basarse en este README (pasos 2 a 7) y en `log_calidad.csv`.
- La "Ficha de la métrica" puede tomar las definiciones de la sección "Cómo se mide la retención" y de `diccionario_datos.csv`.
- Corregir en "Modelo dimensional" lo que los datos contradicen:
  - El canal Online no es reciente (25% de las boletas).
  - El cuarto medio de pago es "App", no "otro".
  - `es_feriado` viene de un calendario externo.
- Anexos: `supuestos.csv`, `log_calidad.csv` y `validaciones.csv`.

**Para el análisis**

- Investigar la caída de la retención en Q4. Una hipótesis a revisar: clientes que llegaron atraídos por la campaña de septiembre y no volvieron.
- Validar los supuestos con la contraparte en la próxima instancia, sobre todo S06 (fecha de alta) y S07 (tipo de cliente), y pedir datos de 2024. Sin ellos no se pueden distinguir bien los clientes nuevos de los antiguos a comienzos de año.
- La cadena ya deja base para las otras preguntas:
  - `mart_rfm_cliente` para P2 (clientes más valiosos).
  - `fact_venta_linea` + `dim_campana` para P3 (promociones).
  - `venta_real_base` para P4 (inflación).
  - Retención por los 9 locales: el corte "Tienda principal" ya viene en `mart_retencion`.

**Sobre los datos personales**

- `origen/origen_pos.sqlite` contiene RUT y nombres, y este repositorio es público. Son datos ficticios del curso,
  pero conviene hacer el repositorio privado o sacar `origen/` del historial.
- `datos/bronce/` y `datos/plata/` nunca se suben (están en `.gitignore`).
