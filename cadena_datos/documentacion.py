# -*- coding: utf-8 -*-
"""Documentación generada en cada corrida: diccionario de datos, supuestos y resumen de hallazgos."""
from datetime import datetime

import pandas as pd

import config
import limpieza as L

TABLAS = {
    'dim_tiempo': 'Calendario diario (2025 + días de las boletas fuera de período). Grano: 1 día.',
    'dim_tienda': 'Locales (9 físicos + Tienda Online). Grano: 1 tienda.',
    'dim_medio_pago': 'Medios de pago. Grano: 1 medio.',
    'dim_producto': 'Maestro de productos limpio + SKU vendidos sin maestro. Grano: 1 SKU.',
    'dim_campana': 'Campañas de marketing 2025. Grano: 1 campaña.',
    'dim_cliente': 'Clientes del programa (sin RUT ni nombre) + miembro -1 "Anónimo". Grano: 1 tarjeta/hogar.',
    'fact_venta_boleta': 'Hecho principal (grano del informe): 1 boleta única. Incluye boletas fuera de período con flag.',
    'fact_venta_linea': 'Hecho de detalle: 1 línea de boleta (para preguntas futuras de producto/promoción).',
    'mart_cliente_mes': 'Estado de cada cliente con compras en 2025, mes a mes. Grano: cliente × mes.',
    'mart_retencion': 'Retención por período, ventana y corte. Grano: corte × valor × período × ventana.',
    'mart_cohortes': 'Actividad de cohortes trimestrales. Grano: tipo de cohorte × cohorte × trimestre de actividad.',
    'mart_rfm_cliente': 'Recencia, frecuencia, monto y estado al corte 31-12-2025. Grano: 1 cliente.',
    'mart_venta_mensual': 'Venta y cobertura de identificación por mes y corte. Grano: corte × valor × mes.',
    'mart_cobertura': 'Embudo de cobertura: boletas del origen que quedan fuera de la retención y por qué. Grano: 1 paso.',
    'mart_valor_riesgo': 'Clientes perdidos en Q4 traducidos a pesos, por ventana. Grano: 1 ventana.',
    'mart_kpi_resumen': 'KPIs de cabecera para el informe y la presentación. Grano: 1 KPI.',
}

COLUMNAS = {
    # comunes
    'fecha': 'Fecha (AAAA-MM-DD)', 'anio_mes': 'Año-mes (AAAA-MM)', 'boleta_id': 'Número de boleta (POS)',
    'tienda_key': 'Llave de tienda (= tienda_id del POS)', 'cliente_key': 'Llave de cliente (= cliente_id del POS; -1 = anónimo)',
    'medio_key': 'Llave de medio de pago', 'sku_key': 'Código de producto (SKU)', 'canal': 'Presencial o Web',
    'es_online': 'True si la compra/tienda es del canal Online (tienda 10)', 'venta_neta': 'Venta en CLP nominales con IVA: Σ monto_linea registrado, neto de devoluciones (S02, S03, S04)',
    # dim_tiempo
    'anio': 'Año', 'mes': 'Mes (1-12)', 'trimestre': 'Trimestre (AAAAQn)', 'semana_iso': 'Semana ISO', 'dia_semana': 'Día de la semana',
    'es_fin_de_semana': 'Sábado o domingo', 'nombre_feriado': 'Nombre del feriado (referencias/feriados_chile_2025.csv)',
    'es_feriado': 'Feriado nacional (vacío si el año no está en el calendario de referencia)', 'en_periodo_analisis': 'Fecha dentro de 2025',
    'campanas_vigentes': 'Campañas vigentes ese día (separadas por |)', 'ipc_var_pct': 'Variación % mensual del IPC (mindicador.cl)',
    'ipc_indice': f'Índice IPC encadenado, base {config.IPC_BASE} = 100',
    # dim_tienda / medio / producto / campaña
    'nombre': 'Nombre de la tienda / producto / campaña', 'formato': 'Express, Supermercado, Híper u Online', 'comuna': 'Comuna',
    'region': 'Región (derivada de la comuna; La Florida corregida a Metropolitana)', 'macrozona': 'Metropolitana, Centro sur o Sur (README); la Tienda Online tiene macrozona "Online" porque vende a toda la cadena (S08)',
    'medio': 'Efectivo, Débito, Crédito o App', 'categoria': 'Categoría canónica (8) o "No informada"', 'subcategoria': 'Subcategoría',
    'marca': 'Marca', 'proveedor': 'Proveedor', 'costo_unitario': 'Costo unitario del maestro (CLP; supuesto sin IVA)',
    'precio_lista': 'Precio de lista del maestro (CLP)', 'activo': 'Producto activo en el maestro',
    'flag_costo_invalido': 'Costo no numérico o ausente', 'es_sin_maestro': 'SKU vendido que no existe en el maestro (SKU-9xxx)',
    'campana_id': 'Campaña que aplica a la línea (SKU + fecha + canal)', 'tipo': 'Tipo de campaña', 'fecha_ini': 'Inicio de campaña',
    'fecha_fin': 'Fin de campaña', 'descuento_pct': 'Descuento en %', 'canales': 'Canales habilitados (separados por |)',
    # dim_cliente
    'clasificacion_nombre': 'Persona/Hogar, Negocio o No determinado. Clasificación del equipo por prefijo del nombre, NO una categoría de la empresa (S07)', 'segmento': 'Clásico, Plus o Black (valor actual, SCD1)',
    'comuna_residencia': 'Comuna del cliente', 'region_residencia': 'Región del cliente', 'macrozona_residencia': 'Macrozona del cliente',
    'fecha_alta': 'Fecha de alta del maestro, tal como viene. No es la primera compra ni una inscripción (S06); solo separa clientes previos (alta < 2025)', 'es_cliente_previo_2025': 'Alta anterior a 2025',
    'es_nuevo_2025': 'Alta en 2025 (S06)', 'tipo_cohorte': 'Nuevo 2025 / Previo (alta antes de 2025)',
    'fecha_primera_compra': 'Primera compra válida observada en 2025', 'fecha_ultima_compra': 'Última compra válida en 2025',
    'n_compras_2025': 'Compras válidas en 2025', 'cohorte_trimestre': 'Trimestre de la primera compra observada',
    'tienda_principal_key': 'Tienda con más compras del cliente en 2025 (S09)', 'tienda_principal': 'Nombre de la tienda principal',
    'formato_principal': 'Formato de la tienda principal', 'macrozona_principal': 'Macrozona de la tienda principal',
    'flag_rut_invalido': 'RUT con dígito verificador inválido en el origen', 'flag_alta_posterior_compra': 'Compró antes de su fecha de alta',
    'dias_alta_a_primera_compra': 'Días entre alta y primera compra (negativo = compró antes del alta)',
    # hechos
    'linea_seq': 'Número de línea renumerado dentro de la boleta (R08)', 'cantidad': 'Unidades (negativo = devolución)',
    'precio_unitario': 'Precio unitario cobrado (CLP)', 'venta_lista': 'cantidad × precio_unitario',
    'descuento_monto': 'venta_lista − monto calculado con descuento', 'monto_linea': 'Monto registrado de la línea (oficial, S02)',
    'monto_calculado': 'cantidad × precio × (1 − descuento) (control)', 'tipo_descuento': 'sin_descuento, campana, beneficio_tarjeta (S05) o no_explicado',
    'es_devolucion': 'Línea con cantidad negativa', 'flag_monto_inconsistente': 'Monto registrado difiere > $2 del calculado',
    'flag_volumen_mayorista': f'Cantidad >= {config.CANTIDAD_MAYORISTA} unidades', 'flag_sku_sin_maestro': 'SKU no existe en el maestro',
    'flag_linea_posible_duplicada': 'Misma boleta, línea, SKU y monto que otra línea (se conserva)',
    'es_identificada': 'Boleta con tarjeta (cliente identificado)', 'n_lineas': 'Líneas de la boleta', 'unidades': 'Unidades netas',
    'unidades_devueltas': 'Unidades devueltas', 'venta_neta_calculada': 'Σ monto_calculado (control de S02)',
    'monto_devolucion': 'Σ monto de líneas de devolución (negativo)', 'venta_real_base': f'venta_neta en pesos de {config.IPC_BASE} (IPC, S16)',
    'es_solo_devolucion': 'Todas las líneas son devoluciones', 'es_compra_valida': 'venta_neta > 0 y no es solo devolución (cuenta para retención)',
    'en_periodo': 'Fecha dentro de 2025', 'tiene_linea_campana': 'Alguna línea en campaña', 'tiene_beneficio_tarjeta': 'Alguna línea con descuento de tarjeta',
    'flag_fuera_periodo': 'Fecha fuera de 2025 (S01)', 'flag_mes_inconsistente': 'La columna mes del origen no coincidía con la fecha (R04)',
    'flag_region_inconsistente': 'La columna region del origen no coincidía con la tienda (R05)',
    # marts
    'n_compras': 'Compras válidas en el mes', 'compro_en_mes': 'Tuvo al menos una compra válida en el mes',
    'dias_desde_ultima_compra': 'Días desde la última compra al cierre del mes', 'activo_30d': 'Activo al cierre del mes (ventana 30 d)',
    'activo_90d': 'Activo al cierre del mes (ventana 90 d)', 'activo_180d': 'Activo al cierre del mes (ventana 180 d)', 'activo_365d': 'Activo al cierre del mes (ventana 365 d)',
    'estado_90d': 'aun_sin_compras, nuevo, primera_obs_previo, reactivado, recurrente, activo_sin_compra o inactivo (ventana 90 d)',
    'corte': 'Dimensión de corte (Total, Tienda principal, Formato principal, Macrozona principal, Segmento, Persona/negocio; en ventas también Canal)', 'valor': 'Valor del corte',
    'periodo_tipo': 'mes o trimestre', 'periodo': 'Período (AAAA-MM o AAAAQn)', 'ventana_dias': 'Ventana de inactividad W (días)',
    'activos_inicio': 'A0: activos al cierre del día anterior al período', 'activos_fin': 'A1: activos al cierre del período',
    'retenidos': 'A0 ∩ A1', 'perdidos': 'A0 − A1', 'nuevos': 'Entran a A1 con primera compra en el período y alta 2025',
    'primeras_obs_previos': 'Entran a A1 con primera compra observada en el período pero alta anterior a 2025',
    'reactivados': 'Entran a A1 tras estar inactivos (ya habían comprado antes)', 'nuevos_flujo': 'Todos los clientes nuevos con primera compra en el período (aunque no sigan activos al cierre)', 'activos_inicio_que_compraron': 'De A0, los que compraron dentro del período',
    'clientes_con_compra': 'Clientes con compra en el período', 'tasa_retencion': 'retenidos / activos_inicio',
    'tasa_churn': 'perdidos / activos_inicio', 'tasa_recompra_periodo': 'activos_inicio_que_compraron / activos_inicio',
    'indice_reposicion': 'nuevos / perdidos (<1: no alcanza a reponer)', 'indice_reposicion_total': '(nuevos + reactivados + primeras_obs_previos) / perdidos',
    'base_confiable': 'True si hay >= W días de historia antes del período (si no, A0 está subestimado por falta de datos 2024)',
    'es_ventana_principal': f'ventana_dias == {config.VENTANA_PRINCIPAL}', 'n_suficiente': f'activos_inicio >= {config.UMBRAL_N_MIN}', 'muestra_pequena': f'activos_inicio < {config.UMBRAL_MUESTRA_PEQUENA}: tasa volátil, mostrar con advertencia',
    'tamano_cohorte': 'Clientes de la cohorte', 'trimestre_actividad': 'Trimestre observado', 'trimestres_desde_ingreso': '0 = trimestre de ingreso',
    'clientes_activos': 'Clientes de la cohorte con compra en el trimestre', 'pct_activos': 'clientes_activos / tamano_cohorte', 'compras': 'Compras válidas',
    'recencia_dias': 'Días entre la última compra y el 31-12-2025', 'frecuencia': 'Compras válidas en 2025', 'monto': 'Σ venta_neta de compras válidas 2025',
    'r_score': 'Quintil de recencia (5 = más reciente)', 'f_score': 'Quintil de frecuencia (5 = más frecuente)', 'm_score': 'Quintil de monto (5 = mayor)',
    'segmento_rfm': 'Campeones, Leales, Recientes, En riesgo, Hibernando / perdidos, Necesitan atención',
    'una_compra_evaluable': f'Primera compra <= {config.VENTANA_PRINCIPAL} días antes del corte (tuvo tiempo de volver)',
    'es_una_sola_vez': 'Una sola compra y evaluable', 'activo_30d_al_corte': 'Activo al 31-12-2025 (30 d)',
    'activo_90d_al_corte': 'Activo al 31-12-2025 (90 d)', 'activo_180d_al_corte': 'Activo al 31-12-2025 (180 d)', 'activo_365d_al_corte': 'Activo al 31-12-2025 (365 d)',
    'paso': 'Orden del paso en el embudo', 'motivo': 'Motivo de exclusión (o total)', 'boletas_restantes': 'Boletas que siguen después del paso',
    'pct_del_origen': 'boletas del paso / boletas del origen', 'pct_venta_2025': 'venta del paso / venta 2025',
    'perdidos_q4': 'Clientes activos al 1-oct que ya no lo están al 31-dic', 'gasto_trimestral_perdidos': 'Σ gasto trimestral de los perdidos (venta 2025 / trimestres entre su primera y última compra)',
    'venta_anual_en_riesgo': 'gasto_trimestral_perdidos × 4 (supone que el gasto se habría mantenido)', 'activos_inicio_q4': 'Clientes activos al 1-oct-2025',
    'gasto_trimestral_promedio_activo': 'Gasto trimestral promedio de los activos al 1-oct (misma definición)', 'valor_anual_1pp_retencion': '1% × activos_inicio_q4 × gasto trimestral × 4',
    'tema': 'Tema del supuesto', 'supuesto': 'Qué se asume', 'por_que': 'Por qué se tomó', 'efecto_si_falso': 'Qué pasaría con el resultado si fuera falso',
    'decidio': 'Quién lo decidió', 'id': 'Identificador del supuesto',
    'boletas': 'Boletas', 'boletas_identificadas': 'Boletas con tarjeta', 'clientes_unicos': 'Clientes distintos',
    'venta_identificada': 'Venta de boletas con tarjeta', 'ticket_promedio': 'Promedio de venta por compra válida',
    'ticket_mediano': 'Mediana de venta por compra válida', 'pct_boletas_identificadas': 'boletas_identificadas / boletas',
    'pct_venta_identificada': 'venta_identificada / venta_neta', 'kpi': 'Nombre del KPI', 'unidad': 'Unidad', 'definicion': 'Definición',
}


def diccionario(oro):
    filas = []
    for t, df in oro.items():
        if t.startswith('_'):
            continue
        for c in df.columns:
            filas.append({'tabla': t, 'descripcion_tabla': TABLAS.get(t, ''), 'columna': c, 'tipo': str(df[c].dtype),
                          'descripcion': COLUMNAS.get(c, 'SIN DESCRIPCIÓN'), 'nulos': int(df[c].isna().sum()), 'filas': len(df)})
    return pd.DataFrame(filas)


def supuestos():
    return pd.DataFrame(config.SUPUESTOS, columns=['id', 'tema', 'supuesto', 'por_que', 'efecto_si_falso', 'decidio', 'fecha'])


def _pct(x):
    return f'{x * 100:.1f}%'.replace('.', ',')


def _dec(x):
    return f'{x:.2f}'.replace('.', ',')


def _num(x):
    return f'{x:,.0f}'.replace(',', '.')


def resumen_hallazgos(oro, val):
    k = oro['mart_kpi_resumen'].set_index('kpi').valor
    m = oro['mart_retencion']
    q = m[(m.corte == 'Total') & (m.periodo_tipo == 'trimestre') & (m.ventana_dias == config.VENTANA_PRINCIPAL)].set_index('periodo')
    corte_q4 = lambda nombre: m[(m.corte == nombre) & (m.periodo == '2025Q4') & (m.ventana_dias == config.VENTANA_PRINCIPAL)].set_index('valor')
    w = config.VENTANA_PRINCIPAL
    lin = [f'# Resumen de hallazgos para reportería', '',
           f'Generado automáticamente por la cadena el {datetime.now():%d-%m-%Y %H:%M}. Todas las cifras salen de `datos/oro/`.',
           f'Validaciones: {(val.resultado == "OK").sum()} OK / {(val.resultado != "OK").sum()} con falla (ver `validaciones.csv`).', '',
           '## Contexto', '',
           f'- Boletas 2025: {_num(k.boletas_2025)}; venta neta nominal: ${_num(k.venta_neta_2025)}; venta real (pesos de {config.IPC_BASE}): ${_num(k.venta_real_2025)}.',
           f'- Identificación: {_pct(k.pct_boletas_identificadas)} de las boletas y {_pct(k.pct_venta_identificada)} de la venta tienen tarjeta. '
           f'La retención se mide sobre {_num(k.clientes_con_compra_2025)} clientes.', '',
           '## Retención (pregunta 1)', '',
           f'- Mediana entre compras: {k.intercompra_mediana_dias:.0f} días; p90: {k.intercompra_p90_dias:.0f} días. '
           f'Recompras dentro de 30 d: {_pct(k.pct_recompras_dentro_30d)}; dentro de 90 d: {_pct(k.pct_recompras_dentro_90d)}.',
           '- Clientes activos al 31-12-2025: ' + ' · '.join(f'{_pct(k[f"pct_activos_{v}d_al_corte"])} ({v} d)' for v in config.VENTANAS)
           + '. **La definición de "activo" cambia la cifra drásticamente.** Con 365 d todos quedan activos: con 12 meses de datos esa ventana no discrimina.',
           f'- Compradores de una sola vez: {_pct(k.pct_una_sola_vez)}, calculado solo sobre los clientes que tuvieron al menos {w} días '
           f'para volver (primera compra hasta {(config.FECHA_CORTE - pd.Timedelta(days=w)).strftime("%d-%m-%Y")}).',
           f'- Retención trimestral (W={w} d, base confiable desde Q2): ' + ' · '.join(
               f'{p}: {_pct(r.tasa_retencion)}' for p, r in q.iterrows() if r.base_confiable) + '.',
           f'- Q4 con W={w} d: {_num(q.loc["2025Q4"].perdidos)} clientes perdidos vs. {_num(q.loc["2025Q4"].nuevos)} nuevos '
           f'(índice de reposición {_dec(q.loc["2025Q4"].indice_reposicion)}) y {_num(q.loc["2025Q4"].reactivados)} reactivados.',
           '- Sensibilidad Q4: retención ' + ' · '.join(f'{_pct(k[f"retencion_Q4_{v}d"])} ({v} d)' for v in config.VENTANAS) + '.',
           f'- **En pesos:** los clientes perdidos en Q4 compraban ${_num(k[f"venta_anual_en_riesgo_{w}d"])} al año '
           f'(su gasto trimestral típico × 4). Cada punto de retención vale ${_num(k[f"valor_anual_1pp_retencion_{w}d"])} al año.',
           f'- **Cobertura:** {_pct(k.pct_boletas_fuera_de_retencion)} de las boletas del origen queda fuera de la retención '
           f'(duplicadas, 2026, anónimas o solo devolución; ver `mart_cobertura`). Las compras usadas cubren {_pct(k.pct_venta_2025_en_retencion)} de la venta 2025.',
           ]
    if 'cohorte_Q1_nuevos_activos_en_Q4' in k:
        lin.append(f'- De los clientes nuevos que llegaron en Q1-2025, {_pct(k.cohorte_Q1_nuevos_activos_en_Q4)} compra en Q4.')
    # --- corte principal pedido por la contraparte: local
    tri = m[(m.corte == 'Tienda principal') & (m.periodo_tipo == 'trimestre') & (m.ventana_dias == w) & m.base_confiable]
    piv = tri.pivot(index='valor', columns='periodo', values='tasa_retencion').sort_values('2025Q4', ascending=False)
    loc4 = corte_q4('Tienda principal')
    lin += ['', f'## Retención por local (corte pedido por la contraparte, W={w} d)', '',
            'Cada cliente se asigna a su local principal (S09). La Tienda Online es un décimo punto de venta (S08).', '',
            '| Local | ' + ' | '.join(piv.columns) + ' | Activos inicio Q4 |', '|---|' + '---|' * (len(piv.columns) + 1)]
    for v, r in piv.iterrows():
        lin.append(f'| {v} | ' + ' | '.join(_pct(x) for x in r) + f' | {_num(loc4.loc[v].activos_inicio)} |')
    peq = loc4[loc4.muestra_pequena]
    if len(peq):
        lin += ['', f'**Precaución:** {len(peq)} de {len(loc4)} locales parten Q4 con menos de {config.UMBRAL_MUESTRA_PEQUENA} clientes activos; '
                    'sus tasas cambian mucho entre trimestres. Leer la tendencia junto con el total, no un trimestre aislado.']
    # --- otros cortes
    lin += ['', f'## Otros cortes en Q4 (W={w} d)', '', '| Corte | Valor | Activos inicio | Retención | Reposición |', '|---|---|---|---|---|']
    for nombre in ['Formato principal', 'Macrozona principal', 'Segmento', config.CORTE_CLASIFICACION_NOMBRE]:
        for v, r in corte_q4(nombre).iterrows():
            lin.append(f'| {nombre} | {v} | {_num(r.activos_inicio)} | {_pct(r.tasa_retencion)} | {_dec(r.indice_reposicion)} |')
    sg, cn = corte_q4('Segmento'), corte_q4(config.CORTE_CLASIFICACION_NOMBRE)
    lin += ['', f'- **Segmento** (pedido por la contraparte): la retención va de {_pct(sg.tasa_retencion.min())} a {_pct(sg.tasa_retencion.max())}. '
                'Queda pareja, como anticipó la contraparte: el segmento hoy no separa al cliente frecuente del ocasional.',
            f'- **Persona/negocio** (clasificación del equipo, no de la empresa): {_pct(cn.tasa_retencion.min())} a {_pct(cn.tasa_retencion.max())}. '
                'No separa el comportamiento; se deja solo como dato complementario.',
            '- **Macrozona "Online"**: clientes cuyo local principal es la Tienda Online, que viven en toda la cadena (S08).']
    lin += ['', '## Cómo leer las tablas', '',
            '- `mart_retencion`: filtrar `ventana_dias = 90` (principal) y `base_confiable = True`. Usar `corte`/`valor` para los cortes.',
            '- `mart_cohortes`: usar `tipo_cohorte = "Nuevo 2025"` para curvas de cohorte (la cohorte Q1 "Todos" mezcla clientes antiguos).',
            '- `fact_venta_boleta`: filtrar `en_periodo = True`. Para retención, además `es_compra_valida = True` y `es_identificada = True`.',
            '- Supuestos en `supuestos.csv`; definiciones en `diccionario_datos.csv`; reglas de limpieza en `log_calidad.csv`.']
    return '\n'.join(lin) + '\n'


def ejecutar(oro, log, val):
    dic = diccionario(oro)
    L.escribir_csv(dic, config.ORO / 'diccionario_datos.csv')
    L.escribir_csv(supuestos(), config.ORO / 'supuestos.csv')
    L.escribir_csv(log.df(), config.ORO / 'log_calidad.csv')
    L.escribir_csv(val, config.ORO / 'validaciones.csv')
    (config.ORO / 'resumen_hallazgos.md').write_text(resumen_hallazgos(oro, val), encoding='utf-8')
    return dic
