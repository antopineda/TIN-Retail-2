# Resumen de hallazgos

Generado automáticamente por la cadena el 15-11-2026 16:48. Todas las cifras salen de `datos/oro/`.
Validaciones: 36 OK / 0 con falla (ver `validaciones.csv`).

## Contexto

- Boletas 2025: 6.153; venta neta: CLP 77,00 millones nominales con IVA; venta real: CLP 74,99 millones de 2024-12; margen bruto: CLP 11,57 millones sin IVA (17,9% de la venta sin IVA; 98,4% de la venta con costo del maestro).
- Identificación: 86,9% de las boletas y 93,5% de la venta tienen tarjeta. La retención se mide sobre 1.192 clientes.

## Retención (pregunta 1)

- Mediana entre compras: 15 días; p90: 74 días. Recompras dentro de 30 d: 69,1%; dentro de 90 d: 92,8%.
- Clientes activos al 31-12-2025: 30,8% (30 d) · 56,5% (90 d) · 81,1% (180 d). **La definición de "activo" cambia la cifra drásticamente.** (365 días se retiró: con un año de datos da 100% por construcción.)
- Compradores de una sola vez: 29,9%, calculado solo sobre los clientes que tuvieron al menos 90 días para volver (primera compra hasta 02-10-2025).
- Retención trimestral (W=90 d, base confiable desde Q2): 2025Q2: 62,4% · 2025Q3: 63,7% · 2025Q4: 51,1%.
- Q4 con W=90 d: 287 clientes perdidos vs. 306 nuevos (índice de reposición 1,07) y 50 reactivados.
- Sensibilidad Q4: retención 33,2% (30 d) · 51,1% (90 d) · 82,5% (180 d).
- **En margen (E2):** los clientes perdidos en Q4 dejaban CLP 4,57 millones de margen bruto al año (CLP nominales 2025 sin IVA; su margen trimestral típico × 4). Cada punto de retención vale CLP 104.751 de margen al año. En la E1 se reportó la venta: CLP 31,79 millones al año con IVA (misma regla, otra unidad).
- **Cobertura:** 15,1% de las boletas del origen queda fuera de la retención (duplicadas, 2026, anónimas o solo devolución; ver `mart_cobertura`). Las compras usadas cubren 93,7% de la venta 2025.
- De los clientes nuevos que llegaron en Q1-2025, 31,9% compra en Q4.

## ¿Retiene o repone? La misma regla bajo cada ventana (S22)

La cadena RETIENE si al menos el 50% de sus clientes activos al cierre ya estaban activos al inicio. Si no, REPONE si los que llegan (nuevos y reactivados) cubren a los perdidos; si tampoco, la base SE ACHICA.

| Ventana | Trimestre | Retención | Nuevos por perdido | Base al cierre que ya estaba | Veredicto |
|---|---|---|---|---|---|
| 30 días | 2025Q2 | 36,2% | 0,78 | 32,7% | **Repone** |
| 30 días | 2025Q3 | 49,0% | 1,04 | 33,2% | **Repone** |
| 30 días | 2025Q4 | 33,2% | 0,76 | 34,3% | **Se achica** |
| 90 días | 2025Q2 | 62,4% | 1,14 | 53,2% | **Retiene** |
| 90 días | 2025Q3 | 63,7% | 1,26 | 51,4% | **Retiene** |
| 90 días | 2025Q4 | 51,1% | 1,07 | 44,5% | **Repone** |
| 180 días | 2025Q3 | 83,5% | 2,13 | 68,9% | **Retiene** |
| 180 días | 2025Q4 | 82,5% | 2,34 | 64,7% | **Retiene** |

- La conclusión **no** es la misma con cualquier ventana, así que se presenta condicionada: con 90 días (oficial) la cadena pasó de *retener* en Q3 a *reponer* en Q4; con 30 días pasó de *reponer* a *achicarse*; con 180 días *retiene* en ambos trimestres.
- Lo que sí se sostiene con 30 y 90 días: Q4 está un escalón peor que Q3. Con 180 días no se ve, porque esa ventana cuenta como activo a quien lleva hasta 6 meses sin comprar.

## Compradores de una sola vez (sin segunda compra en 90 días, horizonte fijo)

| Clientes nuevos que llegaron en | Evaluables | Sin segunda compra | IC 95% |
|---|---|---|---|
| 2025Q1 | 113 | 29,2% | 21,6%–38,2% |
| 2025Q2 | 174 | 24,7% | 18,9%–31,6% |
| 2025Q3 | 219 | 42,0% | 35,7%–48,6% |
| 2025Q4 | 12 | 41,7% | 19,3%–68,0% |
| Todo 2025 | 518 | 33,4% | 29,5%–37,6% |

- 33,4% de los clientes nuevos de 2025 no volvió a comprar en 90 días. Entre los que llegaron en Q3 fue 42,0%, contra 29,2% y 24,7% en Q1 y Q2: los clientes con que la cadena repone son cada vez más de una sola compra.
- La cohorte Q4 tiene muy pocos clientes evaluables (su primera compra debe ser hasta el 2-oct) y no se interpreta.

## Retención por local (corte pedido por la contraparte, W=90 d)

Cada cliente se asigna a su local principal (S09). La Tienda Online es un décimo punto de venta (S08).

| Local | 2025Q2 | 2025Q3 | 2025Q4 | IC 95% Q4 | Activos inicio Q4 |
|---|---|---|---|---|---|
| Express La Florida | 61,3% | 59,4% | 46,3% | 32,1%–61,3% | 41 |
| Express Providencia | 52,8% | 73,0% | 45,5% | 31,7%–59,9% | 44 |
| Express Puerto Montt | 65,8% | 59,1% | 56,8% | 42,2%–70,3% | 44 |
| Híper Concepción | 59,4% | 62,9% | 37,0% | 24,5%–51,4% | 46 |
| Híper Puente Alto | 31,6% | 61,1% | 44,8% | 28,4%–62,5% | 29 |
| Súper Maipú | 66,7% | 44,0% | 40,5% | 26,3%–56,5% | 37 |
| Súper Osorno | 61,1% | 67,6% | 51,2% | 36,5%–65,7% | 41 |
| Súper Temuco | 60,0% | 51,5% | 60,6% | 43,7%–75,3% | 33 |
| Súper Viña | 63,0% | 61,0% | 60,9% | 46,5%–73,6% | 46 |
| Tienda Online | 68,2% | 69,2% | 54,0% | 47,5%–60,4% | 226 |

**Precaución:** 9 de 10 locales parten Q4 con menos de 50 clientes activos; sus tasas cambian mucho entre trimestres. Por eso la tabla va en orden alfabético y no como ranking: un local solo es distinto del total si su intervalo no incluye la retención de la cadena.

## Otros cortes en Q4 (W=90 d)

| Corte | Valor | Activos inicio | Retención | Reposición |
|---|---|---|---|---|
| Formato principal | Express | 129 | 49,6% | 1,38 |
| Formato principal | Híper | 75 | 40,0% | 1,00 |
| Formato principal | Online | 226 | 54,0% | 0,88 |
| Formato principal | Supermercado | 157 | 53,5% | 1,10 |
| Macrozona principal | Centro sur | 92 | 48,9% | 1,09 |
| Macrozona principal | Metropolitana | 151 | 44,4% | 1,17 |
| Macrozona principal | Online | 226 | 54,0% | 0,88 |
| Macrozona principal | Sur | 118 | 55,9% | 1,27 |
| Segmento | Black | 197 | 52,3% | 1,09 |
| Segmento | Clásico | 177 | 47,5% | 1,14 |
| Segmento | Plus | 213 | 53,1% | 0,98 |
| Persona/negocio (clasificación del equipo) | Negocio | 363 | 50,1% | 1,08 |
| Persona/negocio (clasificación del equipo) | Persona/Hogar | 224 | 52,7% | 1,05 |

- **Segmento** (pedido por la contraparte): la retención va de 47,5% a 53,1%. Queda pareja, como anticipó la contraparte: el segmento hoy no separa al cliente frecuente del ocasional.
- **Persona/negocio** (clasificación del equipo, no de la empresa): 50,1% a 52,7%. No separa el comportamiento; se deja solo como dato complementario.
- **Macrozona "Online"**: clientes cuyo local principal es la Tienda Online, que viven en toda la cadena (S08).

## Caso de negocio: contactar al cliente antes de perderlo (W=90 d, supuestos S18 y S19)

Costo por contacto CLP 50, cupón de 10% y tasa de recuperación supuesta de 10,0%. Cifras por año (2025), en CLP sin IVA.

| Contactar al cumplir | Contactos | Habrían vuelto solos | Costo | Margen recuperado | Resultado | Tasa de equilibrio |
|---|---|---|---|---|---|---|
| 30 días | 2.143 | 47,2% | CLP 1,34 millones | CLP 1,23 millones | CLP -111.467 | 11,0% |
| 45 días | 1.589 | 34,6% | CLP 792.602 | CLP 1,23 millones | CLP 439.181 | 6,1% |
| 60 días | 1.259 | 23,1% | CLP 484.697 | CLP 1,23 millones | CLP 747.086 | 3,4% |
| 75 días | 991 | 10,4% | CLP 258.955 | CLP 1,23 millones | CLP 972.827 | 1,5% |

- Contactar temprano (30 días) gasta en clientes que iban a volver solos; contactar tarde deja menos tiempo para recuperar. La tasa de equilibrio es la recuperación mínima para que la acción pague su costo.

## ¿Las campañas retienen? (vuelta a comprar en los 90 días siguientes)

| Acción | Grupo | Clientes | Volvió en 90 d | IC 95% | Descuento otorgado |
|---|---|---|---|---|---|
| Septiembre Imperdible (25%, descuento_directo) | Usó la acción | 262 | 61,5% | 55,4%–67,1% | CLP 392.335 |
| Septiembre Imperdible (25%, descuento_directo) | Compró en el período sin usarla | 118 | 57,6% | 48,6%–66,2% |  |
| Otoño Lácteos (50%, 2x1) | Usó la acción | 9 | 55,6% | 26,7%–81,1% | CLP 447 |
| Otoño Lácteos (50%, 2x1) | Compró en el período sin usarla | 151 | 80,1% | 73,1%–85,7% |  |
| Beneficio tarjeta 10% (permanente), medido en Q3 | Usó la acción | 333 | 58,3% | 52,9%–63,4% | CLP 304.117 |
| Beneficio tarjeta 10% (permanente), medido en Q3 | Compró en el período sin usarla | 259 | 42,1% | 36,2%–48,2% |  |

- Es una comparación, no un efecto causal: no hubo grupo de control y quien usa una promoción ya es más activo.

## Por qué unos locales retienen más (clientes activos al 1-oct-2025)

| Local | Retención Q4 (IC 95%) | Una sola compra ene–sep | Ticket promedio | Margen por cliente ene–sep |
|---|---|---|---|---|
| Híper Concepción | 37,0% (24,5%–51,4%) | 28,3% | CLP 8.180 | CLP 5.472 |
| Súper Maipú | 40,5% (26,3%–56,5%) | 37,8% | CLP 8.249 | CLP 5.982 |
| Híper Puente Alto | 44,8% (28,4%–62,5%) | 37,9% | CLP 9.737 | CLP 5.841 |
| Express Providencia | 45,5% (31,7%–59,9%) | 22,7% | CLP 11.575 | CLP 10.103 |
| Express La Florida | 46,3% (32,1%–61,3%) | 29,3% | CLP 10.298 | CLP 7.866 |
| Súper Osorno | 51,2% (36,5%–65,7%) | 9,8% | CLP 12.471 | CLP 10.718 |
| Tienda Online | 54,0% (47,5%–60,4%) | 18,1% | CLP 11.080 | CLP 9.529 |
| Express Puerto Montt | 56,8% (42,2%–70,3%) | 25,0% | CLP 8.986 | CLP 6.949 |
| Súper Temuco | 60,6% (43,7%–75,3%) | 21,2% | CLP 10.227 | CLP 7.500 |
| Súper Viña | 60,9% (46,5%–73,6%) | 10,9% | CLP 9.329 | CLP 6.226 |

## Cómo leer las tablas

- `mart_retencion`: filtrar `ventana_dias = 90` (principal) y `base_confiable = True`. Usar `corte`/`valor` para los cortes.
- `mart_cohortes`: usar `tipo_cohorte = "Nuevo 2025"` para curvas de cohorte (la cohorte Q1 "Todos" mezcla clientes antiguos).
- `fact_venta_boleta`: filtrar `en_periodo = True`. Para retención, además `es_compra_valida = True` y `es_identificada = True`.
- Supuestos en `supuestos.csv`; definiciones en `diccionario_datos.csv`; reglas de limpieza en `log_calidad.csv`.
