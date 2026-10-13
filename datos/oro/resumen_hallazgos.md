# Resumen de hallazgos para reportería

Generado automáticamente por la cadena el 13-10-2026 19:56. Todas las cifras salen de `datos/oro/`.
Validaciones: 23 OK / 0 con falla (ver `validaciones.csv`).

## Contexto

- Boletas 2025: 6.153; venta neta nominal: $77.003.763; venta real (pesos de 2024-12): $74.989.710.
- Identificación: 86,9% de las boletas y 93,5% de la venta tienen tarjeta. La retención se mide sobre 1.192 clientes.

## Retención (pregunta 1)

- Mediana entre compras: 15 días; p90: 74 días. Recompras dentro de 30 d: 69,1%; dentro de 90 d: 92,8%.
- Clientes activos al 31-12-2025: 30,8% (30 d) · 56,5% (90 d) · 81,1% (180 d) · 100,0% (365 d). **La definición de "activo" cambia la cifra drásticamente.** Con 365 d todos quedan activos: con 12 meses de datos esa ventana no discrimina.
- Compradores de una sola vez: 29,9%, calculado solo sobre los clientes que tuvieron al menos 90 días para volver (primera compra hasta 02-10-2025).
- Retención trimestral (W=90 d, base confiable desde Q2): 2025Q2: 62,4% · 2025Q3: 63,7% · 2025Q4: 51,1%.
- Q4 con W=90 d: 287 clientes perdidos vs. 306 nuevos (índice de reposición 1,07) y 50 reactivados.
- Sensibilidad Q4: retención 33,2% (30 d) · 51,1% (90 d) · 82,5% (180 d) · 100,0% (365 d).
- **En pesos:** los clientes perdidos en Q4 compraban $31.787.944 al año (su gasto trimestral típico × 4). Cada punto de retención vale $713.464 al año.
- **Cobertura:** 15,1% de las boletas del origen queda fuera de la retención (duplicadas, 2026, anónimas o solo devolución; ver `mart_cobertura`). Las compras usadas cubren 93,7% de la venta 2025.
- De los clientes nuevos que llegaron en Q1-2025, 31,9% compra en Q4.

## Retención por local (corte pedido por la contraparte, W=90 d)

Cada cliente se asigna a su local principal (S09). La Tienda Online es un décimo punto de venta (S08).

| Local | 2025Q2 | 2025Q3 | 2025Q4 | Activos inicio Q4 |
|---|---|---|---|---|
| Súper Viña | 63,0% | 61,0% | 60,9% | 46 |
| Súper Temuco | 60,0% | 51,5% | 60,6% | 33 |
| Express Puerto Montt | 65,8% | 59,1% | 56,8% | 44 |
| Tienda Online | 68,2% | 69,2% | 54,0% | 226 |
| Súper Osorno | 61,1% | 67,6% | 51,2% | 41 |
| Express La Florida | 61,3% | 59,4% | 46,3% | 41 |
| Express Providencia | 52,8% | 73,0% | 45,5% | 44 |
| Híper Puente Alto | 31,6% | 61,1% | 44,8% | 29 |
| Súper Maipú | 66,7% | 44,0% | 40,5% | 37 |
| Híper Concepción | 59,4% | 62,9% | 37,0% | 46 |

**Precaución:** 9 de 10 locales parten Q4 con menos de 50 clientes activos; sus tasas cambian mucho entre trimestres. Leer la tendencia junto con el total, no un trimestre aislado.

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

## Cómo leer las tablas

- `mart_retencion`: filtrar `ventana_dias = 90` (principal) y `base_confiable = True`. Usar `corte`/`valor` para los cortes.
- `mart_cohortes`: usar `tipo_cohorte = "Nuevo 2025"` para curvas de cohorte (la cohorte Q1 "Todos" mezcla clientes antiguos).
- `fact_venta_boleta`: filtrar `en_periodo = True`. Para retención, además `es_compra_valida = True` y `es_identificada = True`.
- Supuestos en `supuestos.csv`; definiciones en `diccionario_datos.csv`; reglas de limpieza en `log_calidad.csv`.
