# Entrega 2: qué hay que hacer, qué ya está hecho y qué falta

Grupo 2 · Retail (Multitienda del Sur) · actualizado el 15-11-2026

**Fechas:** Entrega 2 el miércoles 18 de noviembre a las 23:59 (informe PDF + repositorio con etiqueta E2 + prototipo). Presentación 2 el viernes 20 de noviembre, con demostración en vivo.

Este documento mapea el enunciado E2 paso a paso. Para cada componente dice qué pide, qué cambiamos en el código y qué falta hacer a mano. El feedback que recibimos está resumido en [`Resumen Feedback.md`](Resumen%20Feedback.md) y los detalles técnicos de la arquitectura en [`docs/arquitectura.md`](docs/arquitectura.md).

---

## 0. En 30 segundos

- **La pregunta es la misma:** ¿la cadena retiene a sus clientes o los repone con compradores nuevos? El enunciado pide cerrar el alcance, no ampliarlo.
- **El número principal no cambió:** retención Q4 2025 con ventana de 90 días = **51,1%** (ahora con intervalo de confianza del 95%: 47,1% a 55,1%).
- **Cambió la unidad del valor:** en la E1 dijimos "CLP 31,8 millones de **venta** al año en riesgo". Ahora es **CLP 4,57 millones de margen bruto al año** (sin IVA). No es un error corregido: es un cambio de definición que pide el enunciado (margen, no venta).
- **Lo nuevo que pesa más:** un prototipo navegable (Streamlit) y una arquitectura con decisiones, 36 pruebas de calidad y un plan para cuando una fuente falla. Juntos valen el 50% de la nota.
- **La recomendación ahora tiene costo:** contactar a los clientes cuando cumplen entre 60 y 75 días sin comprar cuesta unos CLP 0,48 millones al año y paga su costo si recupera al menos al 3,4% de los que se iban.

## 1. Cómo correr todo

```bash
pip install -r cadena_datos/requirements.txt
```

```bash
python cadena_datos/run_pipeline.py
```

```bash
streamlit run prototipo/app.py
```

El segundo comando corre la cadena completa (unos 30 segundos la primera vez, 5 segundos después) y al final dice `Retención Q4 2025 (90 días): 51.1% · pruebas 36/36 · IPC: ok`. El tercero abre el prototipo en el navegador (http://localhost:8501).

Para mostrar en la presentación qué pasa si la API del IPC se cae:

```bash
python cadena_datos/run_pipeline.py --simular-falla-api
```

Lo probamos de cero en una carpeta limpia, con un ambiente de Python nuevo: corre, deja 36 de 36 pruebas en verde, 70 de 70 pruebas unitarias en verde, y produce exactamente los mismos archivos.

---

## 2. Paso a paso por componente del informe

El informe es la E1 corregida más tres secciones nuevas (arquitectura, prototipo y adopción). Máximo 10 páginas de cuerpo. Orden obligatorio: A, B, C, D, E, F.

### A. Registro de mejora (20%) · máximo 1 página · va primero

**Qué pide:** una tabla con cada observación recibida, qué hicimos y en qué sección y página está el cambio. Las que no atendimos, con el argumento. El número de la E1 y el de hoy lado a lado.

**Borrador de la tabla** (falta completar la columna de página cuando el informe esté armado):

| Observación | Origen | Qué hicimos | Dónde |
|---|---|---|---|
| El valor estaba en venta, no en margen | Enunciado E2 / revisión propia | Calculamos el margen bruto de cada línea con el costo del maestro (S17). El valor en riesgo y el caso de negocio ahora están en CLP de margen sin IVA | Secc. E, p. __ |
| La recomendación no tenía costo | Enunciado E2 | Caso de negocio con costo de contacto y cupón, margen recuperado y punto de equilibrio (S18, S19) | Secc. E, p. __ |
| ¿Las campañas tuvieron efecto? (R1) | Feedback P1, Retail | Comparamos la vuelta a comprar en 90 días de quienes usaron cada campaña vs. quienes compraron sin usarla, con su costo | Secc. E, p. __ |
| ¿Qué hacer con los segmentos Clásico/Plus/Black? (R2) | Feedback P1, Retail | Probamos un segmento por comportamiento (compras de enero a septiembre). Separa mucho más que la tarjeta. Recomendación concreta | Secc. E, p. __ |
| ¿Por qué unos locales pierden más? (R3) | Feedback P1, Retail | Perfil de los clientes de cada local (una sola compra, ticket, margen) + intervalo de confianza de cada tasa | Secc. D/E, p. __ |
| Locales con pocos clientes, sin ranking o con intervalo (A3) | Anexo E2 | Intervalo de Wilson al 95% en cada tasa; el prototipo no ordena los locales con menos de 50 clientes y lo dice | Secc. D, p. __ |
| Cambiar la ventana 30/90/180 en pantalla (A1) y la regla de lectura escrita (A2) | Anexo E2 | Selector de ventana en el prototipo y la regla "un cliente se retiene si…" siempre visible | Secc. D, p. __ |
| Unidades siempre explícitas (G6) | Feedback P1, todos | "CLP", "con/sin IVA", "por año", "trimestre" en cada cifra del prototipo y del resumen | Todo el informe |
| Números claros y pocos (G1) | Feedback P1, todos | Una cifra clave arriba (51,1%) y una en pesos (margen en riesgo) | Primera página y primera pantalla |
| Recomendaciones y próximos pasos (G3) | Feedback P1, todos | Recomendación con dueño, costo, piloto y plan de adopción | Secc. E, p. __ |
| "Revisar Híper Concepción, Súper Maipú e Híper Puente Alto" | Revisión propia | **Se matiza**: con el intervalo, ningún local es distinto del total con seguridad. El foco pasa a los clientes de una sola compra, que están en todos los locales | Secc. E, p. __ |
| La bitácora decía "Equipo" sin nombre | Enunciado E2 | Las filas nuevas (S17–S21) tienen nombre y fecha. **Falta poner nombre a las filas S01–S16** (ver pendientes) | Anexo bitácora |
| Lenguaje de consultor externo (G5) y de negocio (G4) | Feedback P1, todos | Se atiende en el informe y la presentación ("sus locales", "la cadena") | Todo el informe |
| La defensa tiene que ser sólida (G7) | Feedback P1, todos | Respuestas preparadas a las preguntas del anexo (ver sección 4 de este documento) | Presentación |

**Número de la E1 vs. hoy:**

| Cifra | Entrega 1 | Hoy | Por qué cambió |
|---|---|---|---|
| Retención Q4 2025, ventana 90 días | 51,1% | **51,1%** (IC 95%: 47,1%–55,1%) | No cambió. Mismas reglas. Se agregó el intervalo |
| Alternativa, ventana 30 días | 33,2% | 33,2% | No cambió |
| Clientes nuevos por cada perdido (Q4) | 1,07 | 1,07 | No cambió |
| Valor anual en riesgo | CLP 31,8 millones de **venta** con IVA | **CLP 4,57 millones de margen bruto** sin IVA | Cambio de definición: el enunciado pide margen. Margen = 17,9% de la venta sin IVA |
| Valor de un punto de retención | CLP 713 mil de venta al año | CLP 105 mil de margen al año | Mismo cambio de definición |
| Boletas fuera del análisis | 15,1% | 15,1% (cubre 93,7% de la venta) | No cambió: mismas exclusiones (anónimas, duplicadas, 2026, solo devolución) |
| Pruebas de calidad | 23 de 23 | 36 de 36 | Se agregaron 5 por fuente y 8 que protegen la métrica |

### B. Arquitectura e integración (25%)

**Qué pide:** diagrama por capas, tres decisiones defendidas (ETL/ELT, carga completa/incremental, falla de una fuente), pruebas de calidad por fuente y por métrica con su resultado, linaje, acuerdo de servicio con dueño, que corra de cero, README actualizado.

**Qué hicimos:** todo está escrito en [`docs/arquitectura.md`](docs/arquitectura.md), listo para pasar al informe. Resumen:

1. **Capas:** orígenes → bronce (copia fiel) → plata (limpieza) → oro (modelo y marts) → capa semántica (`metricas.py`) → consumo (prototipo e informe). Cada capa tiene una razón para existir.
2. **ETL:** transformamos en Python antes de cargar, porque las fuentes vienen en 3 formatos que una base de datos no lee directo y el volumen es chico.
3. **Carga completa e idempotente:** cada corrida reescribe todo desde el origen. La retención depende de 90 días hacia atrás, así que una carga incremental recalcularía igual esas ventanas. La prueba M02 verifica que no se duplica ni se pierde nada.
4. **Falla de la API:** antes, si la API del IPC fallaba, se usaban valores escritos a mano en el código. Ahora se usa la última respuesta buena guardada en el repositorio (`cadena_datos/referencias/ipc_2025_snapshot.json`), la prueba F05 avisa en amarillo y el prototipo muestra un aviso arriba. **También arreglamos un error real:** en un Mac con Python instalado desde python.org, la API fallaba por un problema de certificados y la cadena usaba el respaldo sin que se notara (en otros computadores sí respondía). Ahora usa `certifi` y, si igual falla, lo avisa.
5. **36 pruebas**, todas en verde: 5 por fuente (F01–F05), 23 de integridad de la E1 (V01–V22) y 8 que protegen la métrica (M01–M08). Cada una dice si bloquea o avisa.
6. **Linaje** de cada campo de la métrica, desde la fuente hasta la pantalla del prototipo (diagrama en `docs/arquitectura.md`).
7. **Acuerdo de servicio:** frescura mensual, completitud ≥ 80% de boletas con tarjeta por mes, 100% de las pruebas que bloquean en verde. Dueño: Subgerente de Clientes y Fidelización (métrica) y Jefe de BI (dato). **Son cargos propuestos: confirmarlos.**
8. Cada corrida queda registrada en `datos/oro/historial_corridas.csv` (fecha, pruebas en verde, estado del IPC, cifra principal).

### C. Modelo dimensional y una sola definición (10%)

**Qué pide:** modelo corregido con el grano en una frase, diccionario de hechos y dimensiones, la métrica definida una sola vez y consumida desde ahí, y la definición alternativa disponible en el prototipo.

**Qué hicimos:**
- **Grano (sin cambio):** "una fila de `fact_venta_boleta` es una boleta única". No cambió porque la retención depende de si hubo compra, y la boleta es la unidad de compra.
- **Qué cambió en el modelo:** el hecho ahora tiene `venta_sin_iva`, `costo` y `margen_bruto` (y la línea, `costo_linea` y `flag_costo_imputado`). `dim_cliente` tiene `tramo_frecuencia_ene_sep` (segmento por comportamiento). Nada se quitó.
- **Una sola definición:** `cadena_datos/metricas.py` define nombre, fórmula, unidad y regla de lectura de cada métrica. El resumen y el prototipo la importan; ninguno recalcula por su cuenta. La prueba M05 verifica que la cifra oficial coincide con un recálculo independiente. Las definiciones también quedan en `datos/oro/metricas.csv`.
- **Alternativa en el prototipo:** el selector de ventana muestra 30, 90 y 180 días, y la tarjeta principal siempre dice "Oficial (90 d): 51,1% · alternativa (30 d): 33,2%".
- **Diccionario:** `datos/oro/diccionario_datos.csv`, generado en cada corrida. Todas las columnas tienen descripción, origen y unidad (la cadena avisa si falta alguna).

### D. Prototipo (25%)

**Qué pide:** una pantalla que responde la pregunta, con la anatomía de la clase 7, que se actualiza cuando la cadena corre, audiencia y frecuencia declaradas, prueba de uso con 2 personas ajenas, y la lista de verificación de 6 líneas.

**Qué hicimos:** `prototipo/app.py` (Streamlit). Lee solo `datos/oro/` y `metricas.py`. Si la cadena vuelve a correr, la pantalla se actualiza al recargar.

Anatomía de la pantalla, de arriba hacia abajo:
1. **Título con la pregunta**, período y filtros: ventana (30 / 90 oficial / 180 días) y trimestre (Q2, Q3, Q4 2025). La regla de lectura escrita al lado.
2. **Cifra clave:** retención con su variación contra el trimestre anterior, y al lado la oficial y la alternativa. Después: clientes nuevos por perdido, margen anual en riesgo (CLP) y cobertura.
3. **Gráfico que explica la cifra:** retención por trimestre + clientes nuevos, perdidos y reactivados.
4. **Corte por la dimensión principal:** retención por local con su intervalo del 95% y la línea del total. Se puede cambiar a formato, macrozona, segmento de tarjeta o compras de enero a septiembre.
5. **La decisión:** simulador de "¿a los cuántos días contactar, cuánto cuesta, cuánto recupera?", con costo por contacto, cupón y tasa de recuperación editables.
6. **Detalle en tabla** (desplegables): detalle por local, campañas, calidad de los datos.
7. **Pie:** fuente, fecha de la última corrida, pruebas en verde, dueño de la métrica y del dato.

**Audiencia y frecuencia (propuesta para el informe):** la mira el Subgerente de Clientes y Fidelización, una vez al mes en la reunión de cierre comercial, para decidir a qué clientes contactar ese mes y con qué incentivo.

**Lista de verificación de la clase 7 (borrador de las seis líneas):**
1. Qué pregunta responde: ¿la cadena retiene a sus clientes con tarjeta o solo los repone?
2. Para quién y cada cuánto: Subgerente de Clientes y Fidelización, mensual.
3. Dónde está la cifra clave: arriba a la izquierda, retención del trimestre con su variación.
4. Cada gráfico calza con su pregunta: tendencia (línea), flujo de clientes (barras agrupadas), comparación entre locales (puntos con intervalo).
5. Ejes truncados o totales que no cierran: el eje de retención va de 0% a 100%; perdidos + retenidos = activos al inicio (prueba V18).
6. Quién certificó las definiciones del pie: la contraparte confirmó ventana, cliente nuevo y Tienda Online por correo el 13-10-2026. **Falta que certifique la definición de margen.**

**Falta (equipo):** la prueba de uso. Ver la sección 5.

### E. Caso de negocio, recomendación y adopción (15%)

**Qué pide:** recomendación en margen y con costo, la prueba ácida en 3 líneas, qué reemplaza el prototipo, plan de adopción completo y la evaluación de la contraparte citada textual.

**Lo que dicen los datos ahora (todo sale de `datos/oro/resumen_hallazgos.md`):**

**1. ¿A los cuántos días contactar?** (CLP sin IVA por año, cupón de 10%, CLP 50 por contacto, 10% de recuperación supuesta)

| Contactar al cumplir | Contactos al año | Habrían vuelto solos | Costo | Margen recuperado | Resultado | Paga su costo desde |
|---|---|---|---|---|---|---|
| 30 días | 2.143 | 47% | CLP 1,34 millones | CLP 1,23 millones | **−CLP 0,11 millones** | 11,0% de recuperación |
| 45 días | 1.589 | 35% | CLP 0,79 millones | CLP 1,23 millones | CLP 0,44 millones | 6,1% |
| 60 días | 1.259 | 23% | CLP 0,48 millones | CLP 1,23 millones | CLP 0,75 millones | 3,4% |
| 75 días | 991 | 10% | CLP 0,26 millones | CLP 1,23 millones | CLP 0,97 millones | 1,5% |

Lectura: contactar a los 30 días (la regla de un mes de la empresa) **pierde plata**, porque casi la mitad de los contactados habría vuelto solo y se le regala el cupón. Esto responde directo a la pregunta de la gerencia sobre los días 30 a 45. El modelo supone la misma tasa de recuperación en cualquier día; en la realidad, esperar más probablemente recupera menos. Por eso recomendamos el rango 60–75 y probarlo en un piloto.

**2. ¿Las campañas retienen?** (vuelta a comprar en los 90 días siguientes)
- *Septiembre Imperdible (25%):* volvió el 61,5% de quienes la usaron vs. 57,6% de quienes compraron sin usarla. Los intervalos se cruzan: **no hay diferencia demostrable**. Costó CLP 392 mil de descuento (sin IVA).
- *Otoño Lácteos (2x1):* solo 9 clientes identificados la usaron; no se puede medir.
- *Beneficio de tarjeta 10% (permanente):* 58,3% vs. 42,1%, pero quien usa el beneficio ya compra más seguido, así que no prueba que el beneficio retenga. Costó CLP 304 mil en Q3.
- Conclusión: ninguna campaña de 2025 tuvo grupo de control, así que nadie puede saber si retuvo. **Recomendación:** que la próxima acción tenga grupo de control.

**3. ¿Qué hacer con los segmentos Clásico/Plus/Black?**
- Por segmento de tarjeta, la retención Q4 va de 47,5% a 53,1% y los intervalos se cruzan: el segmento no separa.
- Por comportamiento (compras de enero a septiembre), sí separa: **los clientes con una sola compra retienen 17,2%**, los de 2 a 4 compras 73,8% y los de 5 o más 48,3%.
- **Recomendación:** no eliminar la tarjeta (es la que permite identificar al cliente), pero dejar de usar el segmento para decidir retención y usar en su lugar "cuántas veces compró". El momento crítico es la segunda compra.

**4. ¿Por qué unos locales pierden más?**
- Los tres locales que menos retienen (Híper Concepción 37,0%, Súper Maipú 40,5%, Híper Puente Alto 44,8%) tienen más clientes de una sola compra (28%–38%) y tickets más bajos (CLP 8.180–9.737 con IVA) que los que más retienen (Súper Viña 10,9% de una sola compra, Súper Osorno 9,8%).
- Pero cada local parte Q4 con 29 a 46 clientes: **ningún intervalo queda completamente bajo el total**. La diferencia entre locales se explica más por cuántos clientes de una sola compra tiene cada uno que por el local mismo.

**Borrador de la recomendación E2:**
> Contactar a los clientes con tarjeta cuando cumplan entre 60 y 75 días sin comprar, con un cupón de 10% en la próxima compra, partiendo con los clientes que han comprado una sola vez. Empezar con un piloto de 3 meses con grupo de control. Cuesta unos CLP 0,48 millones al año, recupera CLP 1,23 millones de margen al año si vuelve el 10% de los que se iban, y paga su costo desde un 3,4%. Adoptar la retención a 90 días como cifra oficial.

**Prueba ácida (borrador):** habilita decidir a qué clientes contactar este mes y con qué incentivo · la toma el Subgerente de Clientes y Fidelización · cada mes.

**Plan de adopción (borrador, completar con nombres y fechas):**

| Casilla | Propuesta |
|---|---|
| Quién lo usa primero | Subgerente de Clientes y Fidelización, en la reunión mensual de cierre comercial |
| Qué puede hacer que no lo use | Que su meta actual se mida con la regla de un mes (30 días): con 90 días su número cambia. Que la cifra no coincida con el reporte de ventas, que mira venta de todos los clientes y no margen de clientes con tarjeta |
| Qué protege esa persona | Su meta y la comparabilidad con lo que reportó antes. Se le muestra la alternativa de 30 días al lado, sin recalcular nada |
| Métrica de adopción | Reuniones mensuales en que se usa la pantalla (meta: 3 de 3 en el primer trimestre) y % de los clientes del listado que efectivamente se contactan. Se mide en marzo de 2027 |
| Quién lo sostiene | Jefe de BI: corre la cadena el día hábil 3 de cada mes y revisa las pruebas |
| Qué reemplaza | **Por confirmar con la contraparte**: el conteo mensual de "clientes inactivos a un mes" que mencionaron en la reunión, y las horas-persona que libera |

**Falta (equipo):** la evaluación de la contraparte ("¿le sirve para decidir?"), citada textual. La ventana de consultas cerró el 11 de noviembre, así que tiene que salir del hilo de correo (si ya se preguntó) o de la prueba de uso.

### F. Calidad, bitácora y declaración de IA (5%)

| Qué pide | Estado |
|---|---|
| Cobertura junto a la cifra principal, comparada con la E1 | Listo: 15,1% de las boletas fuera (igual que la E1), en la tarjeta del prototipo y en el resumen |
| Resultado de las pruebas de la última corrida | Listo: 36 de 36 en verde, en `datos/oro/validaciones.csv` y en el prototipo |
| Bitácora con dueño y fecha en cada fila | **Parcial:** S17–S21 tienen nombre y fecha. Las filas S01–S16 que dicen "Equipo" necesitan el nombre de quien decidió (se edita en `cadena_datos/config.py`, lista `SUPUESTOS`) |
| Una sola definición por regla | Listo en el código (todo sale de `config.py` y `metricas.py`). Revisar que el informe no repita una regla con otro valor |
| Declaración de uso de IA | **Falta escribirla.** Debe decir qué herramienta, para qué y qué verificamos a mano |

---

## 3. Qué cambió en el repositorio

| Archivo | Cambio |
|---|---|
| `cadena_datos/metricas.py` | **Nuevo.** Capa semántica: definición única de cada métrica, intervalo de Wilson, margen y caso de contacto |
| `prototipo/app.py` | **Nuevo.** Prototipo navegable (Streamlit) |
| `docs/arquitectura.md` | **Nuevo.** Capas, decisiones, pruebas, linaje y acuerdo de servicio |
| `cadena_datos/etapa_oro.py` | Margen bruto en los hechos; intervalo de confianza en `mart_retencion`; nuevos marts: `mart_episodios_inactividad`, `mart_caso_contacto`, `mart_campanas`, `mart_perfil_local`; corte por compras de enero a septiembre |
| `cadena_datos/validaciones.py` | 13 pruebas nuevas (F01–F05, M01–M08) y columna "accion" (bloquea o avisa) |
| `cadena_datos/etapa_bronce.py` | Arreglo de certificados para la API; respaldo con el último snapshot bueno; estado de cada fuente |
| `cadena_datos/run_pipeline.py` | `estado_fuentes.csv`, `historial_corridas.csv`, opción `--simular-falla-api` |
| `cadena_datos/config.py` | Parámetros de margen, caso de contacto, dueño y acuerdo de servicio; supuestos S17–S21 |
| `cadena_datos/documentacion.py` | Resumen en CLP con unidades, caso de negocio, campañas y perfil por local; diccionario de todas las columnas nuevas |
| `cadena_datos/tests/test_metricas.py` | **Nuevo.** Pruebas unitarias de la capa semántica (70 en total) |
| `cadena_datos/referencias/ipc_2025_snapshot.json` | **Nuevo.** Última respuesta buena de la API del IPC |
| `cadena_datos/requirements.txt` | Se agregan `streamlit`, `altair` y `certifi` |

---

## 4. Preguntas que va a hacer la gerencia (anexo del enunciado) y cómo responderlas en el prototipo

**"Si yo uso 180 días, ¿cambia su conclusión?"** Sí, y hay que decirlo sin esconderlo. En el prototipo, elegir 180 días: la retención Q4 sube a 82,5% (Q3: 83,5%) y la caída casi desaparece; por cada perdido entran 2,34 nuevos. **Defensa:** el 92,8% de los clientes que vuelven lo hace dentro de 90 días, así que con 180 días se cuenta como "activo" a alguien que lleva 5 meses sin comprar. Esa ventana no ve la fuga de Q4 que sí se ve con 30 y con 90 días.

**"¿Cuánto cuesta contactar a los que se van entre los días 30 y 45, y cuánto recupero?"** En el simulador, poner 30 y después 45. A los 30 días la acción pierde unos CLP 0,11 millones al año porque el 47% de los contactados habría vuelto solo. A los 45 deja unos CLP 0,44 millones y paga su costo desde un 6,1% de recuperación. Por eso proponemos 60–75 días.

**Otras que conviene ensayar:** "¿Qué local está peor?" (Híper Concepción, pero su intervalo toca el total: no se puede afirmar que sea peor). "¿Por qué el margen en riesgo es tanto menor que lo que dijeron en octubre?" (antes era venta con IVA; ahora es margen bruto sin IVA, que es el 17,9% de la venta sin IVA). "¿De dónde sale el 10% de recuperación?" (es un supuesto; por eso mostramos el punto de equilibrio y proponemos un piloto con grupo de control).

---

## 5. Pendientes del equipo (no se pueden hacer desde el código)

- [ ] **Prueba de uso** con al menos 2 personas ajenas al grupo (otro grupo o la contraparte), sin ayuda. Registrar quién, cuánto demoró, qué no entendió y qué cambiamos después. Tres preguntas propuestas:
  1. ¿Cuál es la retención de Q4 2025 con la definición oficial y cuánto baja si se usan 30 días? (51,1% y 33,2%)
  2. ¿Qué local retiene menos en Q4 y se puede decir que es peor que el total de la cadena? (Híper Concepción, 37,0%; no, su intervalo llega a 51,4%)
  3. Si contactamos a los clientes a los 45 días sin comprar, ¿cuánto cuesta al año y desde qué tasa de recuperación paga su costo? (CLP 0,79 millones; 6,1%)
- [ ] **Evaluación de la contraparte** ("¿le sirve para decidir?"), citada textual y marcada como verbalizada.
- [ ] **Confirmar los cargos** del dueño de la métrica y del dato, y qué reporte o planilla reemplaza el prototipo (con horas-persona).
- [ ] **Bitácora:** cambiar "Equipo" por el nombre de quien decidió en S01–S16 (`cadena_datos/config.py`) y volver a correr la cadena.
- [ ] **Revisar los supuestos S17–S21** (margen, costo de contacto, tasa de recuperación): los propuse yo; si alguien decide otro valor, se cambia en `config.py` y se corre de nuevo.
- [ ] **Informe PDF** con las secciones A a F en orden, máximo 10 páginas de cuerpo, con el enlace al repositorio en la portada.
- [ ] **Declaración de uso de IA.**
- [ ] **Etiqueta E2** en el repositorio cuando todo esté listo (`git tag E2`).
- [ ] **Presentación:** primera lámina con el número, la recomendación con valor y costo, y qué cambió desde la P1. Máximo 6 láminas, una sola técnica (la arquitectura). Al menos 2 minutos de demostración en vivo. Presenta alguien distinto que en la P1.
- [ ] **Llevar una copia local** del prototipo funcionando el viernes 20 (correr la cadena antes y probar `streamlit run prototipo/app.py` en el computador que se va a usar).
