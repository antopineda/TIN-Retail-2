# Resumen de hallazgos para reportería

Generado automáticamente por la cadena el 10-10-2026 09:11. Todas las cifras salen de `datos/oro/`.
Validaciones: 22 OK / 0 con falla (ver `validaciones.csv`).

## Contexto

- Boletas 2025: 6.153; venta neta nominal: $77.003.763; venta real (pesos de 2024-12): $74.989.710.
- Identificación: 86,9% de las boletas y 93,5% de la venta tienen tarjeta. La retención se mide sobre 1.192 clientes.

## Retención (pregunta 1)

- Mediana entre compras: 15 días; p90: 74 días. Recompras dentro de 30 d: 69,1%; dentro de 90 d: 92,8%.
- Clientes activos al 31-12-2025: 30,8% (30 d) · 56,5% (90 d) · 81,1% (180 d). **La definición de "activo" cambia la cifra drásticamente.**
- Compradores de una sola vez (con al menos 90 días para volver): 29,9%.
- Retención trimestral (W=90 d, base confiable desde Q2): 2025Q2: 62,4% · 2025Q3: 63,7% · 2025Q4: 51,1%.
- Q4 con W=90 d: 287 clientes perdidos vs. 306 nuevos (índice de reposición 1,07) y 50 reactivados.
- Sensibilidad Q4: retención 33,2% (30 d) · 51,1% (90 d) · 82,5% (180 d).
- De los clientes nuevos que llegaron en Q1-2025, 31,9% compra en Q4.

## Cortes en Q4 (W=90 d)

| Corte | Valor | Activos inicio | Retención | Reposición |
|---|---|---|---|---|
| Tipo de cliente | Negocio | 363 | 50,1% | 1,08 |
| Tipo de cliente | Persona/Hogar | 224 | 52,7% | 1,05 |
| Segmento | Black | 197 | 52,3% | 1,09 |
| Segmento | Clásico | 177 | 47,5% | 1,14 |
| Segmento | Plus | 213 | 53,1% | 0,98 |
| Formato principal | Express | 129 | 49,6% | 1,38 |
| Formato principal | Híper | 75 | 40,0% | 1,00 |
| Formato principal | Online | 226 | 54,0% | 0,88 |
| Formato principal | Supermercado | 157 | 53,5% | 1,10 |

## Cómo leer las tablas

- `mart_retencion`: filtrar `ventana_dias = 90` (principal) y `base_confiable = True`. Usar `corte`/`valor` para los cortes.
- `mart_cohortes`: usar `tipo_cohorte = "Nuevo 2025"` para curvas de cohorte (la cohorte Q1 "Todos" mezcla clientes antiguos).
- `fact_venta_boleta`: filtrar `en_periodo = True`. Para retención, además `es_compra_valida = True` y `es_identificada = True`.
- Supuestos en `supuestos.csv`; definiciones en `diccionario_datos.csv`; reglas de limpieza en `log_calidad.csv`.
