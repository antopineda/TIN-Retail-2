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

Requisitos: Python 3.10 o superior, con `pandas`, `numpy` y `matplotlib` (se instalan con el primer comando). Se necesita internet solo para consultar la API del IPC; si no hay conexión, la cadena usa un respaldo y lo avisa.

```bash
pip install -r cadena_datos/requirements.txt
python cadena_datos/run_pipeline.py
```

Se corre desde la raíz del repositorio y tarda unos 20–30 segundos. **Qué se espera ver al final:**

- 6 pasos numerados `[1/6]` a `[6/6]`, con las filas de cada tabla.
- Las 23 validaciones en `OK`.
- La lista de los 5 gráficos generados y la línea `Listo en … s`.

Las tablas quedan en `datos/oro/`, los gráficos en `datos/oro/graficos/` y las cifras principales en `datos/oro/resumen_hallazgos.md`. **Todas las cifras y figuras del informe salen de esta corrida.**

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
- La fecha de alta del cliente no corresponde a su primera compra, contrario a lo que se dijo en la reunión (coincide en solo 17 de 1.200 clientes); la contraparte lo confirmó después por correo.
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
| tiendas | La Tienda Online está registrada en Providencia, pero vende a clientes de toda la cadena | Se le asigna la macrozona "Online" para no inflar la Metropolitana | 1 tienda (401 clientes) |
| detalle | Precios y montos guardados como texto (`1.940`, `-.905`) | Se convierten a número | 6.931 |
| detalle | Descuento escrito de 7 formas (`10`, `10%`, `0,10`…) | Se convierte a porcentaje (0, 10 o 25) | 2.465 |
| detalle | Dos productos con el mismo número de línea | Se renumeran las líneas; no se borra nada | 790 |
| detalle | El monto registrado no cuadra con cantidad × precio − descuento | Se usa el registrado y el calculado queda como control (diferencia total: 0,8%) | 717 |
| detalle | Cantidades negativas (devoluciones) | Se marcan; restan de la venta | 143 |
| detalle | Compras de 10 a 40 unidades | Se marcan como volumen mayorista; se conservan | 57 |
| detalle | Productos que no están en el maestro (SKU-9xxx) | Se conservan como "Producto sin maestro" | 215 |
| detalle | Descuento de 10% sin campaña, solo con tarjeta | Se clasifica como beneficio de la tarjeta | 3.103 |
| clientes | RUT en formatos mezclados; 16 con dígito verificador inválido | Se normalizan y se validan; el RUT **no pasa a oro** | 849 |
| clientes | El nombre sugiere persona/hogar (Sr., Sra., Familia) o negocio (Distribuidora, Kiosco…) | Se crea `clasificacion_nombre`, una clasificación **del equipo** y no de la empresa; el nombre **no pasa a oro** | 1.200 |
| clientes | Fecha de alta en 2 formatos | Se convierte a fecha | 600 |
| productos | Archivo en codificación Latin-1 (tildes rotas en UTF-8) | Se lee correctamente y se guarda en UTF-8 | 84 |
| productos | Encabezado repetido y fila "TOTAL" | Se eliminan | 2 |
| productos | 24 formas de escribir 8 categorías (`ABARR`, `abarrotes`, `LACT`…) | Se unifican en 8 categorías | 131 |
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
| `mart_retencion` | Por mes o trimestre: cuántos clientes estaban activos, cuántos se retuvieron, se perdieron, llegaron nuevos o volvieron. Incluye ventanas de 30, 90, 180 y 365 días, con cortes por **local** (9 tiendas + Online), formato, macrozona y segmento. **Es la tabla principal para P1.** |
| `mart_cohortes` | De los clientes que llegaron en cada trimestre, qué porcentaje sigue comprando después. |
| `mart_cliente_mes` | El estado de cada cliente mes a mes: nuevo, recurrente, reactivado o inactivo. |
| `mart_rfm_cliente` | Recencia, frecuencia y monto de cada cliente al 31-12-2025, y si compró una sola vez. |
| `mart_venta_mensual` | Venta nominal y real (con IPC) y porcentaje de ventas con tarjeta, por mes. |
| `mart_cobertura` | Qué porcentaje de boletas quedó fuera del análisis y por qué (anexo de cobertura). |
| `mart_valor_riesgo` | Los clientes perdidos traducidos a pesos, para cada ventana. |
| `mart_kpi_resumen` | Las cifras de cabecera para el informe y la presentación. |

**Gráficos** (`datos/oro/graficos/`, componente E del enunciado; cada uno con su unidad en el título y su fuente al pie):

1. `1_sensibilidad_ventana.png`: clientes activos y retención según la ventana (30 / 90 / 180 / 365 días).
2. `2_retencion_trimestral.png`: retención trimestral, y clientes nuevos vs. perdidos vs. reactivados.
3. `3_retencion_por_local.png`: retención Q4 por local, con el tamaño de muestra.
4. `4_cohortes_nuevos.png`: qué porcentaje de los clientes nuevos sigue comprando, por trimestre de llegada.
5. `5_composicion_mensual.png`: quiénes compran cada mes (recurrentes, nuevos, reactivados).

**Cómo se mide la retención.** Un cliente está **activo** si compró en los últimos *W* días (principal: 90). Para
cada período se comparan los activos al inicio con los activos al final:

- **retenidos** = activos al inicio que siguen activos al final → **tasa de retención** = retenidos / activos al inicio
- **perdidos** = activos al inicio que ya no lo están al final
- **nuevos** = su primera compra cae en el período y su alta es de 2025 · **reactivados** = habían comprado antes, estaban inactivos y volvieron
- **primeras compras de clientes previos** = clientes con alta en 2024 que vemos comprar por primera vez en el extracto. No se cuentan como nuevos,
  porque pudieron comprar antes de 2025 (la contraparte lo pidió así)
- **índice de reposición** = nuevos / perdidos (menor que 1 significa que no alcanza a reponer lo que pierde)

Usamos 90 días porque el 92,8% de las recompras ocurre dentro de ese plazo. La empresa piensa en 30 días, así que
también reportamos 30, 180 y 365 días para mostrar cuánto cambia el resultado según la definición. **365 días no
discrimina con estos datos:** como el extracto cubre un solo año, todo cliente que compró en 2025 sigue "activo" al
31-12 y la retención da 100% por construcción. Eso también es un hallazgo: con un año de datos, esa ventana no sirve.

### Paso 6 — Validaciones automáticas

`cadena_datos/validaciones.py` revisa 23 condiciones en cada corrida. Si una crítica falla, la cadena termina con
error y no entrega datos inconsistentes. Entre otras:

- No se pierden líneas de detalle entre bronce y plata.
- Todas las llaves del modelo estrella cruzan con sus dimensiones.
- La suma de las líneas es igual a la suma de las boletas.
- Oro no contiene RUT ni nombres.
- Las cuentas de retención cuadran (activos al final = retenidos + nuevos + reactivados + primeras compras de clientes antiguos).
- El embudo de cobertura cuadra: boletas del origen − exclusiones = compras usadas.

El resultado queda en `datos/oro/validaciones.csv`.

### Paso 7 — Documentación generada

En cada corrida se regeneran, dentro de `datos/oro/`:

- `diccionario_datos.csv`: qué significa cada columna de cada tabla (la "biblia del dato" que pidió la empresa).
- `supuestos.csv`: la **bitácora de supuestos** (anexo obligatorio): cada supuesto con por qué se tomó, qué pasaría si fuera falso, y quién lo decidió y cuándo.
- `log_calidad.csv`: cada regla de limpieza con su conteo.
- `resumen_hallazgos.md`: las cifras principales, siempre actualizadas.
- `graficos/`: las 5 visualizaciones del informe.

---

## Respuesta de la contraparte (13-10-2026)

Enviamos 3 preguntas y la contraparte respondió. Esto es lo que confirmó y cómo quedó en la cadena:

| Tema | Lo que dijo la contraparte | Cómo quedó en la cadena |
|---|---|---|
| Fecha de alta | No es la primera compra ni una fecha de inscripción: no hay un evento detrás. No se debe corregir ni usar como primera compra. Las boletas anteriores al alta son compras. | La fecha de alta se deja tal cual y las boletas se conservan. Solo se usa para separar a los clientes que ya existían antes del extracto (alta en 2024). |
| Cliente nuevo | No hay criterio oficial: lo definimos nosotras y lo dejamos escrito. Un cliente con alta en 2024 no es nuevo solo porque su primera boleta del extracto sea de 2025. | **Nuevo** = alta en 2025 y primera compra en el período. Los clientes con alta en 2024 quedan como "primera compra de cliente previo". |
| Tipo de cliente | Significa el **segmento** de la tarjeta y el **local**, no persona/negocio. El segmento sale parejo: no insistir. | El corte principal pasa a ser el **local** (9 tiendas + Online). El segmento se muestra una vez. Persona/negocio queda como clasificación nuestra, complementaria. |
| Canal Online | Es un décimo punto de venta, con ventas todo el año y clientes de toda la cadena. Sus compras se incluyen en el cálculo principal. | Online se incluye, y en los cortes geográficos tiene macrozona "Online" (antes inflaba la Metropolitana). |
| Anónimos, duplicados y ventana | Las boletas sin cliente quedan fuera de la retención; los duplicados idénticos cuentan una vez; no hay ventana oficial. | Ya se hacía así. La ventana de 90 días queda documentada como decisión nuestra. |

## Supuestos

Todo lo que la contraparte no definió queda como supuesto o decisión del equipo, en `cadena_datos/config.py`. Si algo
cambia, se edita ese archivo y se vuelve a correr la cadena.

| Id | Supuesto |
|---|---|
| S01 | El período es enero–diciembre de 2025; las 37 boletas de 2026 quedan fuera de las métricas. |
| S02 | La venta de una boleta es la suma de sus montos registrados (grano boleta). |
| S03 | Los precios incluyen IVA. |
| S04 | Las devoluciones restan; una boleta con venta neta ≤ 0 no cuenta como compra. |
| S05 | El descuento de 10% sin campaña es un beneficio de la tarjeta. |
| S06 | **(Confirmado)** La fecha de alta no es la primera compra ni la inscripción; no se corrige. Nuevo = alta en 2025 y primera compra en el período; previo = alta antes de 2025. Limitación: 54 clientes con alta entre el 1 y el 27 de enero podrían haber comprado en diciembre de 2024. |
| S07 | **(Confirmado)** "Tipo de cliente" = segmento + local. Persona/negocio es una clasificación del equipo y solo complementaria. |
| S08 | **(Confirmado)** Online es un décimo punto de venta, se incluye en el cálculo principal y tiene macrozona "Online". |
| S09 | El local de un cliente es donde más compra (corte pedido por la contraparte). |
| S10 | Un cliente es una tarjeta, que corresponde a un hogar. |
| S11 | No hay ventana oficial: elegimos 90 días como principal, con 30, 180 y 365 como sensibilidad. |
| S12–S16 | Duplicados, columnas redundantes, productos sin maestro, datos personales y deflactor IPC (ver `supuestos.csv`). |

## Qué deja como resultado

Las tablas de `datos/oro/` son lo que recibe reportería. Las cifras principales están en
`datos/oro/resumen_hallazgos.md`, que se regenera en cada corrida. Al 13-10-2026:

- **La definición de "activo" cambia mucho la respuesta:** al 31-12-2025 hay 30,8% de clientes activos con ventana de 30 días, 56,5% con 90 días y 81,1% con 180 días.
- La retención trimestral (90 días) es de 62–64% en Q2 y Q3 y **cae a 51,1% en Q4**.
- En Q4 se perdieron 287 clientes y llegaron 306 nuevos (índice de reposición 1,07): la cadena **apenas repone lo que pierde**.
- El 29,9% de los clientes compró una sola vez (262 de 875). Se calcula **solo sobre los clientes que tuvieron al menos 90 días para volver**, es decir, cuya primera compra fue hasta el 2-10-2025. Sin ese filtro daría 37,8%, porque incluiría a quienes compraron por primera vez a fin de año y no alcanzaron a volver.
- **En pesos:** los 287 clientes perdidos en Q4 compraban unos **$31,8 millones al año** (su gasto trimestral típico × 4). Cada punto porcentual de retención vale cerca de **$713 mil al año**.
- **Cobertura:** el 15,1% de las boletas del origen queda fuera de la retención (61 duplicadas, 37 de 2026, 803 anónimas y 45 con venta neta ≤ 0). Las compras usadas cubren el 93,7% de la venta 2025.
- **Por local** (Q4, 90 días): Súper Viña (60,9%) y Súper Temuco (60,6%) retienen más; Híper Concepción (37,0%) y Súper Maipú (40,5%), menos. Ojo: 9 de las 10 tiendas parten Q4 con menos de 50 clientes activos, así que sus tasas cambian mucho entre trimestres.
- **Por macrozona:** las tiendas físicas de la Metropolitana son las que peor retienen (44,4%), y el Sur el que mejor (55,9%). Antes de separar Online, la Metropolitana aparecía con 50,1% porque absorbía a los clientes Online.
- El segmento (47,5%–53,1%) y la clasificación persona/negocio (50,1%–52,7%) **no separan** la retención, como anticipó la contraparte.

## Recomendaciones para después

**Para reportería**

- Usar `mart_retencion` filtrando `ventana_dias = 90` y `base_confiable = True`. Antes de abril los datos no alcanzan para medir con 90 días, porque no hay información de 2024.
- Los 5 gráficos de `datos/oro/graficos/` ya cumplen lo que pide el enunciado (unidad en el título y fuente al pie). Se pueden usar tal cual en el informe y en las láminas.
- Para las curvas de cohorte, usar `mart_cohortes` con `tipo_cohorte = "Nuevo 2025"`. La cohorte de Q1 "Todos" mezcla clientes antiguos.
- El corte principal es el **local**. Mostrar las tasas por tienda junto a la tendencia (Q2–Q4) y con la advertencia de muestra pequeña (columna `muestra_pequena`).
- El segmento se muestra una vez, como dato: no separa la retención.
- `clasificacion_nombre` (persona/negocio) es una clasificación nuestra, no de la empresa. Si se muestra, debe decirlo así.

**Para el informe**

- La sección "Cadena de datos ejecutable" puede basarse en este README (pasos 2 a 7) y en `log_calidad.csv`.
- La "Ficha de la métrica" puede tomar las definiciones de la sección "Cómo se mide la retención" y de `diccionario_datos.csv`.
- Corregir en "Modelo dimensional" lo que los datos y la contraparte contradicen:
  - El canal Online no se excluye: es un décimo punto de venta con el 25% de las boletas (confirmado 13-10).
  - `fecha_alta` no es la primera compra ni la inscripción: no se usa para definir la primera compra (confirmado 13-10).
  - El cuarto medio de pago es "App", no "otro".
  - `es_feriado` viene de un calendario externo.
- **Alcance:** el acta dejaba fuera la desagregación por los 9 locales, pero la contraparte la volvió a pedir (13-10) y la cadena ya la calcula. Hay que actualizar "Qué queda fuera de la Entrega 1".
- **Ficha de la métrica:** escribir la definición de cliente nuevo (S06) e interpretar la diferencia entre las ventanas de 30, 90, 180 y 365 días, como pide el acta.
- **Cobertura de datos** (pide "un número, no un párrafo"): 15,1% de las boletas quedó fuera de la retención; el detalle está en `mart_cobertura`.
- **Caso de negocio en pesos:** usar `venta_anual_en_riesgo_90d` y `valor_anual_1pp_retencion_90d` de `mart_kpi_resumen`.
- Anexos: bitácora (`supuestos.csv`), `log_calidad.csv`, `validaciones.csv`, el acta y la declaración de uso de IA.

**Para el análisis**

- Investigar la caída de la retención en Q4. Una hipótesis a revisar: clientes que llegaron atraídos por la campaña de septiembre y no volvieron.
- Pedir datos de 2024 si hay otra instancia. Sin ellos, la retención de enero a marzo no se puede medir con 90 días y los clientes previos no se distinguen bien.
- Opcional, como sugirió la contraparte: mostrar la retención por canal (presencial / online) **al lado** de la principal, sin sacar las compras online del cálculo principal.
- Revisar qué pasa en las tiendas físicas de la Metropolitana (44,4%) y en Híper Concepción.
- La cadena ya deja base para las otras preguntas:
  - `mart_rfm_cliente` para P2 (clientes más valiosos).
  - `fact_venta_linea` + `dim_campana` para P3 (promociones).
  - `venta_real_base` para P4 (inflación).

**Sobre los datos personales**

- `origen/origen_pos.sqlite` contiene RUT y nombres, y este repositorio es público. Son datos ficticios del curso,
  pero conviene hacer el repositorio privado o sacar `origen/` del historial.
- `datos/bronce/` y `datos/plata/` nunca se suben (están en `.gitignore`).
