# -*- coding: utf-8 -*-
"""
Lógica de actividad y retención de clientes (separada para poder testearla).

Definiciones (ver diccionario de métricas):
- activo(c, t, W): el cliente tiene al menos una compra válida en (t − W, t]   (t y fechas a nivel de día)
- Para un período P = [ini, fin]:
    A0 = activos al cierre del día anterior a ini;  A1 = activos al cierre de fin
    retenidos = A0 ∩ A1          perdidos = A0 − A1
    incorporados = A1 − A0 = nuevos + reactivados + primeras_obs_previos
      nuevos               : primera compra observada en P y alta en 2025
      primeras_obs_previos : primera compra observada en P y alta anterior a 2025 (clientes antiguos que recién vemos)
      reactivados          : ya habían comprado antes de P, estaban inactivos al inicio y volvieron
    nuevos_flujo = todos los clientes nuevos con primera compra en P, aunque ya no estén activos al cierre
      (un nuevo que llega y se va dentro del mismo período no está en A1 y no cuenta en 'nuevos')
"""
import numpy as np
import pandas as pd


def fechas_por_cliente(compras):
    """compras: DataFrame [cliente_id, fecha] -> {cliente_id: np.array ordenado de datetime64[D]}"""
    return {c: np.sort(g.fecha.values.astype('datetime64[D]')) for c, g in compras.groupby('cliente_id')}


def _dia(t):
    return np.datetime64(pd.Timestamp(t).date(), 'D')


def activo_en(fechas, t, ventana):
    t = _dia(t)
    i = np.searchsorted(fechas, t, side='right') - 1
    return bool(i >= 0 and (t - fechas[i]).astype(int) < ventana)


def compro_entre(fechas, ini, fin):
    ini, fin = _dia(ini), _dia(fin)
    return bool(np.searchsorted(fechas, fin, side='right') > np.searchsorted(fechas, ini, side='left'))


def dias_desde_ultima(fechas, t):
    t = _dia(t)
    i = np.searchsorted(fechas, t, side='right') - 1
    return int((t - fechas[i]).astype(int)) if i >= 0 else np.nan


def periodos(ini, fin):
    """Meses y trimestres del período de análisis -> DataFrame [periodo_tipo, periodo, ini, fin]."""
    filas = []
    for freq, tipo in [('M', 'mes'), ('Q', 'trimestre')]:
        for p in pd.period_range(ini, fin, freq=freq):
            filas.append({'periodo_tipo': tipo, 'periodo': str(p), 'ini': p.start_time.normalize(), 'fin': p.end_time.normalize()})
    return pd.DataFrame(filas)


def estados_cliente_periodo(fechas_dict, es_nuevo, per, ventanas):
    """Una fila por cliente × período × ventana con los indicadores de estado (base para agregar por cualquier corte)."""
    filas = []
    for c, f in fechas_dict.items():
        primera = f[0]
        for p in per.itertuples(index=False):
            ini, fin = _dia(p.ini), _dia(p.fin)
            compro = compro_entre(f, p.ini, p.fin)
            primera_en_p = ini <= primera <= fin
            compro_antes = primera < ini
            for w in ventanas:
                a0 = activo_en(f, p.ini - pd.Timedelta(days=1), w)
                a1 = activo_en(f, p.fin, w)
                filas.append((c, p.periodo_tipo, p.periodo, w, a0, a1, compro, a0 and a1, a0 and not a1,
                              (not a0) and a1 and primera_en_p and es_nuevo.get(c, False),
                              (not a0) and a1 and primera_en_p and not es_nuevo.get(c, False),
                              (not a0) and a1 and compro_antes,
                              a0 and compro,
                              primera_en_p and es_nuevo.get(c, False)))
    return pd.DataFrame(filas, columns=['cliente_id', 'periodo_tipo', 'periodo', 'ventana_dias', 'activo_inicio', 'activo_fin',
                                        'compro_en_periodo', 'retenido', 'perdido', 'nuevo', 'primera_obs_previo',
                                        'reactivado', 'activo_inicio_y_compro', 'nuevo_flujo'])


def agregar_retencion(estados, base_ok):
    """Suma los estados de un grupo de clientes y calcula las tasas."""
    s = estados.groupby(['periodo_tipo', 'periodo', 'ventana_dias'])[
        ['activo_inicio', 'activo_fin', 'retenido', 'perdido', 'nuevo', 'primera_obs_previo', 'reactivado',
         'activo_inicio_y_compro', 'compro_en_periodo', 'nuevo_flujo']].sum().reset_index()
    s = s.rename(columns={'activo_inicio': 'activos_inicio', 'activo_fin': 'activos_fin', 'retenido': 'retenidos',
                          'perdido': 'perdidos', 'nuevo': 'nuevos', 'primera_obs_previo': 'primeras_obs_previos',
                          'reactivado': 'reactivados', 'activo_inicio_y_compro': 'activos_inicio_que_compraron',
                          'compro_en_periodo': 'clientes_con_compra', 'nuevo_flujo': 'nuevos_flujo'})
    with np.errstate(divide='ignore', invalid='ignore'):
        s['tasa_retencion'] = np.where(s.activos_inicio > 0, s.retenidos / s.activos_inicio, np.nan)
        s['tasa_churn'] = np.where(s.activos_inicio > 0, s.perdidos / s.activos_inicio, np.nan)
        s['tasa_recompra_periodo'] = np.where(s.activos_inicio > 0, s.activos_inicio_que_compraron / s.activos_inicio, np.nan)
        s['indice_reposicion'] = np.where(s.perdidos > 0, s.nuevos / s.perdidos, np.nan)
        s['indice_reposicion_total'] = np.where(s.perdidos > 0, (s.nuevos + s.reactivados + s.primeras_obs_previos) / s.perdidos, np.nan)
    s = s.merge(base_ok, on=['periodo_tipo', 'periodo', 'ventana_dias'], how='left')
    return s
