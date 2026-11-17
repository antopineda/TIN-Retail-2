# -*- coding: utf-8 -*-
"""Documentación generada en cada corrida: diccionario de datos, supuestos y resumen de hallazgos."""
from datetime import datetime

import pandas as pd

import config
import limpieza as L
import metricas as M

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
    'mart_kpi_resumen': 'Cifras principales del análisis. Grano: 1 KPI.',
    'mart_episodios_inactividad': 'Base del caso de negocio: días desde cada compra hasta la siguiente (o hasta el 31-12-2025). Grano: 1 compra válida de un cliente.',
    'mart_caso_contacto': 'Costo y margen recuperado de contactar a los clientes al cumplir N días sin comprar (supuestos S18, S19). Grano: 1 día de contacto.',
    'mart_campanas': '¿Las campañas retienen? Vuelta a comprar en 90 días de quienes usaron cada acción vs. quienes compraron sin usarla. Grano: acción × grupo.',
    'mart_perfil_local': 'Perfil de los clientes activos al 1-oct-2025 por local principal, para explicar por qué unos retienen más. Grano: 1 local.',
    'estado_fuentes': 'Estado de cada fuente en la última corrida (ok / respaldo) con su huella SHA-256. Grano: 1 fuente.',
    'historial_corridas': 'Una fila por ejecución de la cadena: pruebas en verde, estado del IPC y cifra principal. Grano: 1 corrida.',
    'validaciones': 'Resultado de las pruebas de calidad de la última corrida. Grano: 1 prueba.',
    'mart_una_sola_vez': 'Clientes sin segunda compra dentro de 90 días desde la primera, por cohorte (horizonte fijo). Grano: tipo de cohorte × trimestre de llegada.',
    'fact_cliente_trimestre': 'Hecho donde se calcula la retención (snapshot periódico): estado de cada cliente en cada trimestre y ventana. Grano: cliente × trimestre × ventana.',
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
    'region': 'Región (derivada de la comuna; La Florida corregida a Metropolitana). Para la Tienda Online es la región donde está registrada (Providencia), no donde están sus clientes: para cortes geográficos usar macrozona', 'macrozona': 'Metropolitana, Centro sur o Sur (README); la Tienda Online tiene macrozona "Online" porque vende a toda la cadena (S08)',
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
    'es_devolucion': 'Línea con cantidad negativa', 'flag_monto_inconsistente': 'Monto registrado difiere en más de CLP 2 del calculado',
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
    'activo_90d': 'Activo al cierre del mes (ventana 90 d)', 'activo_180d': 'Activo al cierre del mes (ventana 180 d)',
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
    'activo_90d_al_corte': 'Activo al 31-12-2025 (90 d)', 'activo_180d_al_corte': 'Activo al 31-12-2025 (180 d)',
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
    # E2: margen
    'venta_sin_iva': 'Venta neta sin IVA (CLP nominales): venta / 1,19 (S03, S17)', 'costo_linea': 'Unidades × costo unitario del maestro (CLP sin IVA); imputado si falta (S17)',
    'costo': 'Σ costo de las líneas de la boleta (CLP sin IVA)', 'margen_bruto': 'Margen bruto en CLP nominales sin IVA = venta sin IVA − costo (S17)',
    'flag_costo_imputado': 'El SKU no tiene costo en el maestro: costo imputado con la razón costo/venta del resto (S17)',
    'tiene_costo_imputado': 'Alguna línea de la boleta tiene costo imputado (S17)',
    'tramo_frecuencia_ene_sep': 'Compras válidas entre enero y septiembre de 2025 (0, 1, 2 a 4, 5 o más). Segmento por comportamiento; leer solo en Q4',
    'ic95_inf': 'Límite inferior del intervalo de confianza del 95% de la tasa (Wilson)', 'ic95_sup': 'Límite superior del intervalo de confianza del 95% de la tasa (Wilson)',
    'se_puede_rankear': f'activos_inicio >= {config.UMBRAL_MUESTRA_PEQUENA}: la tasa se puede ordenar en un ranking; si no, mostrar con su intervalo',
    'margen_trimestral_perdidos': 'Σ margen trimestral típico de los perdidos (CLP sin IVA)', 'margen_anual_en_riesgo': 'margen_trimestral_perdidos × 4 (CLP de margen bruto sin IVA por año, S20)',
    'margen_trimestral_promedio_activo': 'Margen trimestral promedio de los activos al 1-oct (CLP sin IVA)', 'margen_anual_1pp_retencion': '1% × activos_inicio_q4 × margen trimestral × 4 (CLP sin IVA por año)',
    'fecha_compra': 'Fecha de la compra válida que abre el episodio', 'dias_observados': 'Días hasta la siguiente compra o, si no hay, hasta el 31-12-2025',
    'censurado': 'True si no hubo otra compra antes del 31-12-2025 (el desenlace no se observa)', 'margen_anual_cliente': 'Margen bruto trimestral típico del cliente × 4 (CLP sin IVA)',
    'ticket_promedio_cliente': 'Venta promedio por compra del cliente en 2025 (CLP con IVA)',
    'dia_contacto': 'Días sin comprar al momento de contactar', 'contactados': 'Episodios que llegan a dia_contacto sin compra en 2025 (contactos en el año)',
    'vuelven_solos': 'Contactados que habrían vuelto antes de la ventana sin contacto (el cupón es costo sin beneficio)',
    'se_pierden': 'Contactados que llegan a ventana_dias sin comprar (se pierden)', 'sin_desenlace': 'Contactados cuyo desenlace no se observa porque terminó el año',
    'pct_contactos_desperdiciados': 'vuelven_solos / contactados', 'costo_cupon_unitario': 'Margen que cuesta un cupón: % cupón × ticket promedio / 1,19 (CLP)',
    'margen_anual_de_los_que_se_pierden': 'Σ margen anual de los clientes que se pierden (CLP sin IVA)', 'recuperados': 'tasa de recuperación (S19) × se_pierden',
    'costo_total': 'contactados × costo de envío + (vuelven_solos + recuperados) × cupón (CLP sin IVA por año)',
    'margen_recuperado': 'tasa de recuperación × margen anual de los que se pierden (CLP sin IVA por año)', 'resultado_neto': 'margen_recuperado − costo_total (CLP por año)',
    'tasa_equilibrio': 'Tasa de recuperación mínima para que la acción no pierda plata',
    'incorporados': 'nuevos + reactivados + primeras_obs_previos: los que entran a la base activa en el período',
    'pct_base_retenida': 'retenidos / activos_fin: qué parte de la base activa al cierre ya estaba al inicio (regla S22)',
    'veredicto': 'Regla S22: Retiene (pct_base_retenida >= 50%), Repone (si no, e incorporados >= perdidos) o Se achica',
    'clientes_evaluables': 'Clientes cuya primera compra deja 90 días completos dentro de 2025', 'sin_segunda_compra': 'Clientes sin segunda compra dentro de 90 días',
    'pct_una_sola_vez': 'sin_segunda_compra / clientes_evaluables', 'horizonte_dias': 'Días que se espera la segunda compra',
    'activo_inicio': 'Activo al cierre del día anterior al trimestre (A0)', 'activo_fin': 'Activo al cierre del trimestre (A1)',
    'compro_en_periodo': 'Compró dentro del trimestre', 'retenido': 'A0 y A1', 'perdido': 'A0 y no A1',
    'nuevo': 'Entra a A1 con primera compra en el trimestre y alta 2025', 'primera_obs_previo': 'Entra a A1 con primera compra observada y alta anterior a 2025',
    'reactivado': 'Entra a A1 tras estar inactivo', 'activo_inicio_y_compro': 'A0 y compró en el trimestre', 'nuevo_flujo': 'Primera compra en el trimestre y alta 2025',
    'accion_id': 'Identificador de la campaña o acción', 'accion': 'Nombre, descuento y tipo de la acción', 'ventana_ini': 'Inicio de la acción',
    'ventana_fin': 'Fin de la acción', 'seguimiento_hasta': 'Último día de la ventana de 90 días en que se mira si el cliente volvió', 'grupo': 'Usó la acción / compró en el período sin usarla',
    'clientes': 'Clientes identificados del grupo', 'volvieron_90d': 'Clientes del grupo con una compra válida en los 90 días siguientes al fin de la acción',
    'pct_volvio_90d': 'volvieron_90d / clientes', 'descuento_otorgado_sin_iva': 'Descuento entregado en las líneas de la acción (CLP sin IVA)',
    'margen_bruto_lineas_accion': 'Margen bruto de las líneas vendidas con la acción (CLP sin IVA)', 'diferencia_pp_vs_no_uso': 'pct_volvio_90d del grupo que la usó − el que no (puntos porcentuales). Correlación, no efecto causal',
    'tasa_retencion_q4': 'Retención Q4 2025 con la ventana principal', 'pct_nuevos_2025': 'Proporción de clientes con alta en 2025',
    'compras_ene_sep_por_cliente': 'Compras válidas promedio por cliente entre enero y septiembre', 'ticket_promedio_ene_sep': 'Venta promedio por compra entre enero y septiembre (CLP con IVA)',
    'margen_ene_sep_por_cliente': 'Margen bruto promedio por cliente entre enero y septiembre (CLP sin IVA)', 'pct_clientes_multilocal': 'Proporción de clientes que compró en más de un local',
    'pct_una_sola_compra_ene_sep': 'Proporción de clientes con una sola compra entre enero y septiembre', 'dias_entre_compras_mediana': 'Mediana de días entre compras de los clientes del local',
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


def metricas_df():
    """Las definiciones de la capa semántica (metricas.py) como tabla, para el informe y el prototipo."""
    return pd.DataFrame([{'metrica': k, **v} for k, v in M.METRICAS.items()])


def supuestos():
    s = pd.DataFrame(config.SUPUESTOS, columns=['id', 'tema', 'supuesto', 'por_que', 'efecto_si_falso', 'decidio', 'fecha'])
    s.insert(3, 'evidencia', s.id.map(config.EVIDENCIA_SUPUESTO))
    return s


def _pct(x):
    return f'{x * 100:.1f}%'.replace('.', ',')


def _dec(x):
    return f'{x:.2f}'.replace('.', ',')


def _num(x):
    return f'{x:,.0f}'.replace(',', '.')


def _clp(x):
    """Pesos chilenos con la unidad explícita (feedback P1: no usar solo '$')."""
    if abs(x) >= 1e6:
        return f'CLP {x / 1e6:,.2f} millones'.replace(',', 'X').replace('.', ',').replace('X', '.')
    return f'CLP {_num(x)}'


def resumen_hallazgos(oro, val):
    k = oro['mart_kpi_resumen'].set_index('kpi').valor
    m = oro['mart_retencion']
    q = m[(m.corte == 'Total') & (m.periodo_tipo == 'trimestre') & (m.ventana_dias == config.VENTANA_PRINCIPAL)].set_index('periodo')
    corte_q4 = lambda nombre: m[(m.corte == nombre) & (m.periodo == '2025Q4') & (m.ventana_dias == config.VENTANA_PRINCIPAL)].set_index('valor')
    w = config.VENTANA_PRINCIPAL
    lin = [f'# Resumen de hallazgos', '',
           f'Generado automáticamente por la cadena el {datetime.now():%d-%m-%Y %H:%M}. Todas las cifras salen de `datos/oro/`.',
           f'Validaciones: {(val.resultado == "OK").sum()} OK / {(val.resultado != "OK").sum()} con falla (ver `validaciones.csv`).', '',
           '## Contexto', '',
           f'- Boletas 2025: {_num(k.boletas_2025)}; venta neta: {_clp(k.venta_neta_2025)} nominales con IVA; venta real: {_clp(k.venta_real_2025)} de {config.IPC_BASE}; margen bruto: {_clp(k.margen_bruto_2025)} sin IVA ({_pct(k.pct_margen_bruto_2025)} de la venta sin IVA; {_pct(k.pct_venta_con_costo_real)} de la venta con costo del maestro).',
           f'- Identificación: {_pct(k.pct_boletas_identificadas)} de las boletas y {_pct(k.pct_venta_identificada)} de la venta tienen tarjeta. '
           f'La retención se mide sobre {_num(k.clientes_con_compra_2025)} clientes.', '',
           '## Retención (pregunta 1)', '',
           f'- Mediana entre compras: {k.intercompra_mediana_dias:.0f} días; p90: {k.intercompra_p90_dias:.0f} días. '
           f'Recompras dentro de 30 d: {_pct(k.pct_recompras_dentro_30d)}; dentro de 90 d: {_pct(k.pct_recompras_dentro_90d)}.',
           '- Clientes activos al 31-12-2025: ' + ' · '.join(f'{_pct(k[f"pct_activos_{v}d_al_corte"])} ({v} d)' for v in config.VENTANAS)
           + '. **La definición de "activo" cambia la cifra drásticamente.** (365 días se retiró: con un año de datos da 100% por construcción.)',
           f'- Compradores de una sola vez: {_pct(k.pct_una_sola_vez)}, calculado solo sobre los clientes que tuvieron al menos {w} días '
           f'para volver (primera compra hasta {(config.FECHA_CORTE - pd.Timedelta(days=w)).strftime("%d-%m-%Y")}).',
           f'- Retención trimestral (W={w} d, base confiable desde Q2): ' + ' · '.join(
               f'{p}: {_pct(r.tasa_retencion)}' for p, r in q.iterrows() if r.base_confiable) + '.',
           f'- Q4 con W={w} d: {_num(q.loc["2025Q4"].perdidos)} clientes perdidos vs. {_num(q.loc["2025Q4"].nuevos)} nuevos '
           f'(índice de reposición {_dec(q.loc["2025Q4"].indice_reposicion)}) y {_num(q.loc["2025Q4"].reactivados)} reactivados.',
           '- Sensibilidad Q4: retención ' + ' · '.join(f'{_pct(k[f"retencion_Q4_{v}d"])} ({v} d)' for v in config.VENTANAS) + '.',
           f'- **En margen (E2):** los clientes perdidos en Q4 dejaban {_clp(k[f"margen_anual_en_riesgo_{w}d"])} de margen bruto al año '
           f'(CLP nominales 2025 sin IVA; su margen trimestral típico × 4). Cada punto de retención vale {_clp(k[f"margen_anual_1pp_retencion_{w}d"])} de margen al año. '
           f'En la E1 se reportó la venta: {_clp(k[f"venta_anual_en_riesgo_{w}d"])} al año con IVA (misma regla, otra unidad).',
           f'- **Cobertura:** {_pct(k.pct_boletas_fuera_de_retencion)} de las boletas del origen queda fuera de la retención '
           f'(duplicadas, 2026, anónimas o solo devolución; ver `mart_cobertura`). Las compras usadas cubren {_pct(k.pct_venta_2025_en_retencion)} de la venta 2025.',
           ]
    if 'cohorte_Q1_nuevos_activos_en_Q4' in k:
        lin.append(f'- De los clientes nuevos que llegaron en Q1-2025, {_pct(k.cohorte_Q1_nuevos_activos_en_Q4)} compra en Q4.')
    # --- regla retiene / repone bajo cada ventana (feedback E1 y P1)
    lin += ['', '## ¿Retiene o repone? La misma regla bajo cada ventana (S22)', '', M.regla_veredicto(), '',
            '| Ventana | Trimestre | Retención | Nuevos por perdido | Base al cierre que ya estaba | Veredicto |', '|---|---|---|---|---|---|']
    vt = m[(m.corte == 'Total') & (m.periodo_tipo == 'trimestre') & m.base_confiable].sort_values(['ventana_dias', 'periodo'])
    for r in vt.itertuples():
        lin.append(f'| {r.ventana_dias} días | {r.periodo} | {_pct(r.tasa_retencion)} | {_dec(r.indice_reposicion)} | {_pct(r.pct_base_retenida)} | **{r.veredicto}** |')
    lin += ['', '- La conclusión **no** es la misma con cualquier ventana, así que se presenta condicionada: con 90 días (oficial) la cadena pasó de '
                '*retener* en Q3 a *reponer* en Q4; con 30 días pasó de *reponer* a *achicarse*; con 180 días *retiene* en ambos trimestres.',
            '- Lo que sí se sostiene con 30 y 90 días: Q4 está un escalón peor que Q3. Con 180 días no se ve, porque esa ventana cuenta como activo a quien lleva hasta 6 meses sin comprar.']
    u = oro['mart_una_sola_vez']
    un = u[u.tipo_cohorte == 'Nuevo 2025'].set_index('cohorte_trimestre')
    lin += ['', f'## Compradores de una sola vez (sin segunda compra en {config.HORIZONTE_SEGUNDA_COMPRA} días, horizonte fijo)', '',
            '| Clientes nuevos que llegaron en | Evaluables | Sin segunda compra | IC 95% |', '|---|---|---|---|']
    for coh, r in un.iterrows():
        lin.append(f'| {coh} | {_num(r.clientes_evaluables)} | {_pct(r.pct_una_sola_vez)} | {_pct(r.ic95_inf)}–{_pct(r.ic95_sup)} |')
    lin += ['', f'- {_pct(un.loc["Todo 2025"].pct_una_sola_vez)} de los clientes nuevos de 2025 no volvió a comprar en {config.HORIZONTE_SEGUNDA_COMPRA} días. '
                f'Entre los que llegaron en Q3 fue {_pct(un.loc["2025Q3"].pct_una_sola_vez)}, contra {_pct(un.loc["2025Q1"].pct_una_sola_vez)} y '
                f'{_pct(un.loc["2025Q2"].pct_una_sola_vez)} en Q1 y Q2: los clientes con que la cadena repone son cada vez más de una sola compra.',
            '- La cohorte Q4 tiene muy pocos clientes evaluables (su primera compra debe ser hasta el 2-oct) y no se interpreta.']
    # --- corte principal pedido por la contraparte: local
    tri = m[(m.corte == 'Tienda principal') & (m.periodo_tipo == 'trimestre') & (m.ventana_dias == w) & m.base_confiable]
    piv = tri.pivot(index='valor', columns='periodo', values='tasa_retencion').sort_index()   # orden alfabético: sin ranking (feedback E1)
    loc4 = corte_q4('Tienda principal')
    lin += ['', f'## Retención por local (corte pedido por la contraparte, W={w} d)', '',
            'Cada cliente se asigna a su local principal (S09). La Tienda Online es un décimo punto de venta (S08).', '',
            '| Local | ' + ' | '.join(piv.columns) + ' | IC 95% Q4 | Activos inicio Q4 |', '|---|' + '---|' * (len(piv.columns) + 2)]
    for v, r in piv.iterrows():
        lin.append(f'| {v} | ' + ' | '.join(_pct(x) for x in r) + f' | {_pct(loc4.loc[v].ic95_inf)}–{_pct(loc4.loc[v].ic95_sup)} | {_num(loc4.loc[v].activos_inicio)} |')
    peq = loc4[loc4.muestra_pequena]
    if len(peq):
        lin += ['', f'**Precaución:** {len(peq)} de {len(loc4)} locales parten Q4 con menos de {config.UMBRAL_MUESTRA_PEQUENA} clientes activos; '
                    'sus tasas cambian mucho entre trimestres. Por eso la tabla va en orden alfabético y no como ranking: '
                    'un local solo es distinto del total si su intervalo no incluye la retención de la cadena.']
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
    # --- caso de negocio
    caso = oro['mart_caso_contacto']
    lin += ['', f'## Caso de negocio: contactar al cliente antes de perderlo (W={w} d, supuestos S18 y S19)', '',
            f'Costo por contacto CLP {config.CONTACTO_COSTO_ENVIO_CLP}, cupón de {config.CONTACTO_CUPON_PCT}% y tasa de recuperación supuesta de '
            f'{_pct(config.CONTACTO_TASA_RECUPERACION)}. Cifras por año (2025), en CLP sin IVA.', '',
            '| Contactar al cumplir | Contactos | Habrían vuelto solos | Costo | Margen recuperado | Resultado | Tasa de equilibrio |',
            '|---|---|---|---|---|---|---|']
    for r in caso.itertuples():
        lin.append(f'| {r.dia_contacto} días | {_num(r.contactados)} | {_pct(r.pct_contactos_desperdiciados)} | {_clp(r.costo_total)} | '
                   f'{_clp(r.margen_recuperado)} | {_clp(r.resultado_neto)} | {_pct(r.tasa_equilibrio)} |')
    lin += ['', '- Contactar temprano (30 días) gasta en clientes que iban a volver solos; contactar tarde deja menos tiempo para recuperar. '
                'La tasa de equilibrio es la recuperación mínima para que la acción pague su costo.']
    # --- campañas
    ca = oro['mart_campanas']
    lin += ['', '## ¿Las campañas retienen? (vuelta a comprar en los 90 días siguientes)', '',
            '| Acción | Grupo | Clientes | Volvió en 90 d | IC 95% | Descuento otorgado |', '|---|---|---|---|---|---|']
    for r in ca.itertuples():
        lin.append(f'| {r.accion} | {r.grupo} | {_num(r.clientes)} | {_pct(r.pct_volvio_90d)} | {_pct(r.ic95_inf)}–{_pct(r.ic95_sup)} | '
                   + (_clp(r.descuento_otorgado_sin_iva) if pd.notna(r.descuento_otorgado_sin_iva) else '') + ' |')
    lin += ['', '- Es una comparación, no un efecto causal: no hubo grupo de control y quien usa una promoción ya es más activo.']
    # --- perfil por local
    pl_ = oro['mart_perfil_local']
    lin += ['', '## Por qué unos locales retienen más (clientes activos al 1-oct-2025)', '',
            '| Local | Retención Q4 (IC 95%) | Una sola compra ene–sep | Ticket promedio | Margen por cliente ene–sep |', '|---|---|---|---|---|']
    for r in pl_.itertuples():
        lin.append(f'| {r.tienda_principal} | {_pct(r.tasa_retencion_q4)} ({_pct(r.ic95_inf)}–{_pct(r.ic95_sup)}) | {_pct(r.pct_una_sola_compra_ene_sep)} | '
                   f'{_clp(r.ticket_promedio_ene_sep)} | {_clp(r.margen_ene_sep_por_cliente)} |')
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
    L.escribir_csv(metricas_df(), config.ORO / 'metricas.csv')
    (config.ORO / 'resumen_hallazgos.md').write_text(resumen_hallazgos(oro, val), encoding='utf-8')
    return dic
