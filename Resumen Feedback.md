# Resumen del feedback de la Entrega 1 y la Presentación 1

Grupo 2 · Retail (Multitienda del Sur) · actualizado el 15-11-2026.

Hay cinco fuentes de feedback: la corrección del informe E1, la corrección de la Presentación 1 (con rúbrica), lo que dijo el profesor en clase (para Retail y para todos), el anexo del enunciado E2 y nuestra propia revisión. **Todas cuentan para el registro de mejora** (componente A, 20% de la E2): cada observación va en la tabla, con lo que hicimos y dónde está el cambio. Las que no atendamos también van, con el argumento.

La columna **Estado** dice si ya está resuelto en el repositorio (✅), si falta hacerlo en el informe o la presentación (📝) o si es parcial (◐).

---

## 1. Notas que sacamos

**Informe E1: 6,5**

| Criterio | Peso | Nota |
|---|---|---|
| A. Mandato y foco | 15% | 7,0 |
| B. Cadena ejecutable | 25% | 7,0 |
| C. Modelo dimensional | 15% | 6,8 |
| D. Métrica y sensibilidad | 25% | **6,0** |
| E. Evidencia y recomendación | 15% | **5,8** |
| F. Cobertura, bitácora, IA | 5% | 6,8 |

**Presentación 1: 31 de 35 puntos**

| Criterio | Puntos | Nivel |
|---|---|---|
| 1. Respuesta directa a la pregunta | 7/7 | Logrado |
| 2. Defensa de la decisión de definición | **5/7** | **Parcial** |
| 3. Evidencia visual | 6/7 | Logrado |
| 4. Lenguaje de negocio | 6/7 | Logrado |
| 5. Tiempo y equipo | 7/7 | Logrado |

**Lo que hicimos bien (hay que mantenerlo):** la cadena corrió de cero en un clon limpio (23 validaciones, 65 pruebas, tablas idénticas). El mandato está muy bien trabajado: fuimos el único grupo de Retail que usó el hilo de correo con la contraparte y lo citamos como origen de las decisiones. La sensibilidad a la ventana está cuantificada y la cobertura bien reportada. La primera lámina respondía de inmediato. Las gráficas tenían título que afirma, unidad y fuente, y la acción (contactar entre 60 y 75 días) era concreta.

**Dónde perdimos puntos:** la definición (D en el informe, criterio 2 en la presentación) y la evidencia y recomendación (E). Ahí se concentran las observaciones de abajo.

---

## 2. Observaciones del informe E1 (corrección del ayudante)

| # | Observación | Qué hicimos | Estado |
|---|---|---|---|
| I1 | **Una regla que sostenga la conclusión.** Con 30 días la reposición es 0,76, con 90 es 1,07 y con 180 es 2,34. Fijar una regla formal que decida entre "retiene" y "repone" y mostrar si se sostiene al cambiar la ventana. Si no se sostiene, presentar la respuesta condicionada a la ventana. | Regla S22, definida una sola vez en `metricas.py`: la cadena **retiene** si al menos 50% de sus clientes activos al cierre ya estaban al inicio; si no, **repone** si los que entran cubren a los perdidos; si tampoco, **se achica**. En Q4: se achica con 30 días, repone con 90 y retiene con 180. **No se sostiene**, así que la respuesta va condicionada. Lo que sí se sostiene con 30 y 90 días es que Q4 queda un escalón peor que Q3. Está en el prototipo, en el gráfico 1 y en el resumen. | ✅ |
| I2 | **Medir a los compradores de una sola vez.** La pregunta los nombra y el informe no los midió (la cadena ya calculaba 29,9%). | Nueva medición con horizonte fijo: un cliente nuevo es "de una sola vez" si no vuelve en 90 días. Así las cohortes se comparan bien. El 33,4% de los clientes nuevos de 2025 lo fue, y entre los que llegaron en Q3 fue el **42,0%**, contra 29,2% (Q1) y 24,7% (Q2). La cadena repone con clientes que cada vez vuelven menos. Está en `mart_una_sola_vez`, en el gráfico 6 y en el prototipo. | ✅ |
| I3 | **Retención por local:** con 29 a 46 clientes por local no hay masa crítica para un ranking ni para recomendar auditar los tres más bajos. Intervalos de confianza o sin ranking. | Las dos cosas: cada tasa tiene su intervalo del 95% y los locales van en orden alfabético (gráfico 3, resumen y prototipo). Conclusión: **ningún local es distinto del total con seguridad**. Se retira la recomendación de auditar los tres más bajos. | ✅ |
| I4 | **Pesos en margen y con costo.** Los CLP 31,8 millones eran venta nominal. El maestro trae el costo real: pasar a margen y estimar cuánto cuesta la acción, **evitando supuestos externos** que no salen de los datos ni del acta. | Margen bruto con el costo del maestro: CLP 4,57 millones de margen al año en riesgo. La acción tiene costo: el cupón de 10% es el mismo descuento que la tarjeta ya da (sale de los datos), y el ticket es el medido. Quedan dos supuestos externos (costo por envío y tasa de recuperación). Por eso la recomendación se presenta con el **punto de equilibrio**, que no depende de la tasa, y con un piloto para medirla. | ◐ (ver nota) |
| I5 | **Ventana de 365 días:** el 100% es un artefacto de tener un año de datos, no un hallazgo. Retirarlo de la tabla. | Se retiró de la cadena, los gráficos, el resumen y el prototipo. | ✅ |
| I6 | **Figuras en el cuerpo**, junto al argumento que respaldan, no en un anexo. | Hay que armarlo así en el informe. Los 6 gráficos están en `datos/oro/graficos/`. | 📝 |
| I7 | **Bitácora:** el supuesto del gasto trimestral × 4 sostenía los CLP 31,8 millones pero no tenía cuantificado su impacto. | Ahora es S20 (en margen) y está cuantificado: si se usa el margen que los perdidos dejaron en Q3 × 4, el valor baja de CLP 4,57 a 4,03 millones (−12%). También se cuantificaron S18, S19 y S22. | ✅ |
| I8 | **Modelo dimensional:** al diagrama le falta la tabla cliente-mes, donde se calcula la retención. | La retención se calcula en una tabla cliente × trimestre que antes no se guardaba. Ahora se guarda como `fact_cliente_trimestre` y el diagrama nuevo la muestra, junto con `mart_cliente_mes` (`docs/arquitectura.md`, sección 1b). | ✅ (falta pasar el diagrama al informe 📝) |

**Nota sobre I4:** el ayudante criticó un supuesto externo ("presupuesto de capacitación masiva"). Nuestro costo por envío (CLP 50) y la tasa de recuperación (10%) también son externos. Para que no se caiga en la defensa: la cifra que se presenta es **"paga su costo si recupera al menos el 3,4%"**, y el 10% aparece solo como ejemplo. Si la contraparte da un costo real de envío, se cambia en `config.py` o directo en el prototipo.

---

## 3. Observaciones de la Presentación 1 (corrección con rúbrica)

| # | Observación | Qué hicimos | Estado |
|---|---|---|---|
| P1 | **Criterio 2 (5/7):** reconocimos y cuantificamos las ventanas, pero no mostramos que la conclusión ("apenas repone") se sostenga con otra ventana. Con 180 días no dijimos cuántos nuevos por perdido hay. Faltó la regla que decide entre retiene y repone, como la que fijaron los otros dos grupos. | Igual que I1. El gráfico 1 muestra retención y nuevos por perdido bajo las tres ventanas, con el veredicto escrito. | ✅ |
| P2 | **Criterio 2:** no justificamos los 90 días en términos de la decisión. | El 92,8% de los que vuelven lo hace dentro de 90 días: a los 90 días un cliente se puede dar por perdido. Además, la decisión de cuándo contactar cambia con la ventana: contactar a los 30 días pierde plata porque el 47% habría vuelto solo. Está en S11 y en el simulador del prototipo. | ✅ (decirlo así en la P2 📝) |
| P3 | **Rúbrica, criterio 2 (Logrado):** distinguir lo verbalizado, lo medido y lo inferido. | La bitácora tiene una columna nueva, `evidencia`, que marca cada supuesto como verbalizado, medido o inferido. | ✅ (usarlo en el informe 📝) |
| P4 | **Criterio 3 (6/7):** el ranking de locales con menos de 50 clientes sostenía una recomendación que la misma lámina relativizaba, y el 100% a 365 días es un artefacto. | Igual que I3 e I5. | ✅ |
| P5 | **Criterio 4 (6/7):** pesos en venta nominal, sin margen ni costo. | Igual que I4. | ◐ |
| P6 | **Para la P2:** una regla de lectura explícita y el índice de reposición bajo las tres ventanas en la misma lámina; locales con intervalo o sin ranking; pesos en margen. | El gráfico 1 sirve como esa lámina, y el bloque "¿Retiene o repone?" del prototipo muestra lo mismo en vivo. | ✅ |

---

## 4. Lo que dijo el profesor en clase

### Para los grupos de Retail

| # | Lo que dijeron | Qué hicimos | Estado |
|---|---|---|---|
| R1 | **El "doble clic" en las campañas:** ¿tuvieron efecto? Si damos descuento y no cambia nada, ¿para qué? | `mart_campanas`: la campaña de Septiembre (25%) no muestra una diferencia demostrable en la vuelta a comprar (61,5% vs 57,6%, los intervalos se cruzan) y costó CLP 392 mil de descuento. Ninguna campaña tuvo grupo de control. | ✅ |
| R2 | **El doble clic en las categorías (Clásico, Plus, Black):** "¿y ahora qué?", falta una recomendación práctica. | El segmento de la tarjeta no separa (47,5% a 53,1%). Lo que sí separa es la cantidad de compras: los clientes con una sola compra retienen 17,2%. Recomendación: segmentar por comportamiento y apuntar a la segunda compra. | ✅ |
| R3 | **La comparación entre tiendas estuvo bien:** ahora, ¿por qué unas pierden más? | `mart_perfil_local`: los locales que menos retienen tienen más clientes de una sola compra y tickets más bajos. Pero ningún local es distinto del total con seguridad (I3). | ✅ |

### Para todos los grupos

| # | Lo que dijeron | Qué significa para nosotros | Estado |
|---|---|---|---|
| G1 | Números claros y pocos: uno o dos que respondan la pregunta. | Primera lámina y primera pantalla: el 51,1% y el valor en margen. | 📝 |
| G2 | Aprovechar los datos y comparar entre tiendas: el promedio esconde cosas. | Corte por local con intervalo. | ✅ |
| G3 | Recomendaciones y próximos pasos. | Recomendación con costo, piloto y plan de adopción (`Entrega2.md`). | ◐ |
| G4 | Lenguaje de negocio: los zapatos del gerente. | Clientes, locales, pesos de margen, decisiones. | 📝 |
| G5 | Rol de consultor externo: no "nuestras tiendas"; se le habla a la gerencia, no al profe; no explicarles su propio rubro. | Decir "sus locales", "la cadena", "ustedes". | 📝 |
| G6 | Siempre las unidades: no solo "$" (¿pesos o dólares?), y el período (¿mes, trimestre, año?). | "CLP", "con/sin IVA" y "por año" en cada cifra del prototipo y del resumen. | ✅ (cuidarlo en el informe 📝) |
| G7 | La respuesta tiene que ser defendible y no caerse con la primera pregunta. | Preguntas difíciles preparadas en `Entrega2.md`, sección 4. | 📝 |
| G8 | Un descuento tiene costo: considerarlo. | Igual que R1 e I4. | ✅ |

---

## 5. Lo que la gerencia va a mirar en el prototipo (anexo del enunciado E2)

| # | Lo que el prototipo tiene que permitir | Estado |
|---|---|---|
| A1 | Cambiar la ventana (30, 90 o 180 días) con la misma fecha base y ver retención y reposición bajo cada una | ✅ |
| A2 | La regla de lectura escrita en pantalla ("retiene si…") | ✅ |
| A3 | Locales con pocos clientes sin ranking, o con su intervalo | ✅ |
| A4 | Pesos en margen | ✅ |
| A5 | Responder "Si yo uso 180 días, ¿cambia su conclusión?" | ✅ Sí cambia (retiene en vez de repone), y la pantalla lo muestra |
| A6 | Responder "¿Cuánto cuesta contactar a los que se van entre los días 30 y 45, y cuánto recupero?" | ✅ Simulador de contacto |

---

## 6. Lo que queda para el equipo

Todo lo marcado con 📝: armar el informe con las figuras en el cuerpo (I6) y el diagrama nuevo del modelo (I8), usar verbalizado/medido/inferido (P3), justificar los 90 días por la decisión en la presentación (P2), lenguaje de consultor externo (G4, G5) y preparar la defensa (G7). La lista completa de pendientes está al final de `Entrega2.md`.
