# -*- coding: utf-8 -*-
"""
ORO: modelo estrella + marts de retención listos para el análisis.
Sin identificadores directos (RUT, nombre): la llave del cliente es cliente_key (= cliente_id, -1 = anónimo).
"""
import numpy as np
import pandas as pd

import config
import limpieza as L
import retencion as R

DIAS_SEMANA = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']

# ----------------------------------------------------------------- dimensiones
def dim_tiempo(boletas, camp, ipc):
    fechas = pd.date_range(min(config.PERIODO_INI, boletas.fecha.min()), max(config.PERIODO_FIN, boletas.fecha.max()), freq='D')
    t = pd.DataFrame({'fecha': fechas})
    t['anio'], t['mes'] = t.fecha.dt.year, t.fecha.dt.month
    t['anio_mes'] = t.fecha.dt.strftime('%Y-%m')
    t['trimestre'] = t.fecha.dt.to_period('Q').astype(str)
    t['semana_iso'] = t.fecha.dt.isocalendar().week.astype(int)
    t['dia_semana'] = t.fecha.dt.dayofweek.map(dict(enumerate(DIAS_SEMANA)))
    t['es_fin_de_semana'] = t.fecha.dt.dayofweek >= 5
    fer = pd.read_csv(config.RAIZ / 'cadena_datos' / 'referencias' / 'feriados_chile_2025.csv', parse_dates=['fecha'])
    t = t.merge(fer, on='fecha', how='left')
    anios_cubiertos = set(fer.fecha.dt.year)
    t['es_feriado'] = np.where(t.anio.isin(anios_cubiertos), t.nombre_feriado.notna(), None)
    t['en_periodo_analisis'] = t.fecha.between(config.PERIODO_INI, config.PERIODO_FIN)
    t['campanas_vigentes'] = [
        '|'.join(camp.loc[(camp.fecha_ini <= f) & (camp.fecha_fin >= f), 'campana_id']) or None for f in t.fecha]
    t = t.merge(ipc[['anio_mes', 'ipc_var_pct', 'ipc_indice']], on='anio_mes', how='left')
    return t


def dim_tienda(tiendas):
    return tiendas.rename(columns={'tienda_id': 'tienda_key'})[
        ['tienda_key', 'nombre', 'formato', 'es_online', 'comuna', 'region', 'macrozona']]


def dim_medio_pago(medios):
    return medios.rename(columns={'medio_id': 'medio_key'})


def dim_producto(productos, detalle):
    p = productos.drop(columns=['categoria_origen']).assign(es_sin_maestro=False)
    sin = sorted(set(detalle.sku) - set(p.sku))
    extra = pd.DataFrame({'sku': sin, 'nombre': 'Producto sin maestro', 'categoria': 'No informada',
                          'subcategoria': 'No informada', 'marca': None, 'proveedor': None, 'costo_unitario': np.nan,
                          'precio_lista': np.nan, 'activo': None, 'flag_costo_invalido': True, 'es_sin_maestro': True})
    return pd.concat([p, extra], ignore_index=True).rename(columns={'sku': 'sku_key'})

# ----------------------------------------------------------------- hechos
def fact_venta_linea(detalle, boletas):
    f = detalle.merge(boletas[['boleta_id', 'fecha']], on='boleta_id', how='left')
    f['venta_lista'] = f.cantidad * f.precio_unitario
    f['descuento_monto'] = f.venta_lista - f.monto_calculado
    f = f.rename(columns={'sku': 'sku_key'})
    cols = ['boleta_id', 'linea_seq', 'fecha', 'sku_key', 'cantidad', 'precio_unitario', 'descuento_pct', 'venta_lista',
            'descuento_monto', 'monto_linea', 'monto_calculado', 'campana_id', 'tipo_descuento', 'es_devolucion',
            'flag_monto_inconsistente', 'flag_volumen_mayorista', 'flag_sku_sin_maestro', 'flag_linea_posible_duplicada']
    return f[cols]


def fact_venta_boleta(boletas, detalle, tiendas, ipc):
    d = detalle.assign(venta_lista=detalle.cantidad * detalle.precio_unitario,
                       monto_dev=detalle.monto_linea.where(detalle.es_devolucion, 0),
                       unid_dev=(-detalle.cantidad).where(detalle.es_devolucion, 0),
                       con_campana=detalle.campana_id.notna(),
                       con_tarjeta=detalle.tipo_descuento.eq('beneficio_tarjeta'))
    ag = d.groupby('boleta_id').agg(
        n_lineas=('linea_seq', 'size'), unidades=('cantidad', 'sum'), unidades_devueltas=('unid_dev', 'sum'),
        venta_neta=('monto_linea', 'sum'), venta_neta_calculada=('monto_calculado', 'sum'), venta_lista=('venta_lista', 'sum'),
        monto_devolucion=('monto_dev', 'sum'), lineas_devolucion=('es_devolucion', 'sum'),
        tiene_linea_campana=('con_campana', 'any'), tiene_beneficio_tarjeta=('con_tarjeta', 'any'),
        flag_monto_inconsistente=('flag_monto_inconsistente', 'any')).reset_index()
    f = boletas.merge(ag, on='boleta_id', how='left')
    f['descuento_monto'] = f.venta_lista - f.venta_neta_calculada
    f['es_solo_devolucion'] = f.lineas_devolucion == f.n_lineas
    f['es_compra_valida'] = (f.venta_neta > 0) & ~f.es_solo_devolucion
    f['en_periodo'] = ~f.flag_fuera_periodo
    f['anio_mes'] = f.fecha.dt.strftime('%Y-%m')
    f['es_online'] = f.tienda_id.map(tiendas.set_index('tienda_id').es_online)
    f['venta_real_base'] = (f.venta_neta * f.anio_mes.map(ipc.set_index('anio_mes').factor_a_pesos_base)).where(f.en_periodo)
    f['cliente_key'] = f.cliente_id.fillna(-1).astype(int)
    f = f.rename(columns={'tienda_id': 'tienda_key', 'medio_id': 'medio_key'})
    return f[['boleta_id', 'fecha', 'anio_mes', 'tienda_key', 'cliente_key', 'medio_key', 'canal', 'es_online',
              'es_identificada', 'n_lineas', 'unidades', 'unidades_devueltas', 'venta_lista', 'descuento_monto',
              'venta_neta', 'venta_neta_calculada', 'monto_devolucion', 'venta_real_base', 'es_solo_devolucion',
              'es_compra_valida', 'en_periodo', 'tiene_linea_campana', 'tiene_beneficio_tarjeta',
              'flag_monto_inconsistente', 'flag_fuera_periodo', 'flag_mes_inconsistente', 'flag_region_inconsistente']]

# ----------------------------------------------------------------- cliente
def compras_validas(fb):
    """Compras que cuentan para retención: identificadas, válidas y dentro del período."""
    c = fb[fb.es_identificada & fb.es_compra_valida & fb.en_periodo]
    return c.rename(columns={'cliente_key': 'cliente_id'})[['cliente_id', 'boleta_id', 'fecha', 'tienda_key', 'venta_neta']]


def _tienda_principal(compras):
    cnt = compras.groupby(['cliente_id', 'tienda_key']).agg(n=('boleta_id', 'size'), ultima=('fecha', 'max')).reset_index()
    cnt = cnt.sort_values(['cliente_id', 'n', 'ultima'], ascending=[True, False, False])
    return cnt.drop_duplicates('cliente_id').set_index('cliente_id').tienda_key


def dim_cliente(clientes, geo, compras, tiendas):
    c = clientes.merge(geo[['comuna_id', 'comuna', 'region', 'macrozona']], on='comuna_id', how='left')
    res = compras.groupby('cliente_id').agg(fecha_primera_compra=('fecha', 'min'), fecha_ultima_compra=('fecha', 'max'),
                                            n_compras_2025=('boleta_id', 'size'))
    c = c.merge(res, left_on='cliente_id', right_index=True, how='left')
    c['n_compras_2025'] = c.n_compras_2025.fillna(0).astype(int)
    c['es_nuevo_2025'] = c.fecha_alta >= config.PERIODO_INI
    c['tipo_cohorte'] = np.where(c.es_nuevo_2025, 'Nuevo 2025', 'Previo (alta antes de 2025)')
    c['cohorte_trimestre'] = c.fecha_primera_compra.dt.to_period('Q').astype(str).where(c.fecha_primera_compra.notna())
    c['flag_alta_posterior_compra'] = c.fecha_primera_compra < c.fecha_alta
    c['dias_alta_a_primera_compra'] = (c.fecha_primera_compra - c.fecha_alta).dt.days
    tp = _tienda_principal(compras)
    ti = tiendas.set_index('tienda_id')
    c['tienda_principal_key'] = c.cliente_id.map(tp).astype('Int64')
    c['tienda_principal'] = c.tienda_principal_key.map(ti.nombre)
    c['formato_principal'] = c.tienda_principal_key.map(ti.formato)
    c['macrozona_principal'] = c.tienda_principal_key.map(ti.macrozona)
    c = c.rename(columns={'cliente_id': 'cliente_key', 'macrozona': 'macrozona_residencia', 'region': 'region_residencia',
                          'comuna': 'comuna_residencia'})
    cols = ['cliente_key', 'segmento', 'clasificacion_nombre', 'comuna_residencia', 'region_residencia', 'macrozona_residencia',
            'fecha_alta', 'es_cliente_previo_2025', 'es_nuevo_2025', 'tipo_cohorte', 'fecha_primera_compra',
            'fecha_ultima_compra', 'n_compras_2025', 'cohorte_trimestre', 'tienda_principal_key', 'tienda_principal',
            'formato_principal', 'macrozona_principal', 'flag_rut_invalido', 'flag_alta_posterior_compra',
            'dias_alta_a_primera_compra']
    anon = pd.DataFrame([{'cliente_key': -1, 'clasificacion_nombre': 'Anónimo', 'segmento': 'Anónimo', 'tipo_cohorte': 'Anónimo',
                          'n_compras_2025': 0}])
    return pd.concat([c[cols], anon], ignore_index=True)[cols]

# ----------------------------------------------------------------- marts
def mart_cliente_mes(fechas, dimc, compras):
    meses = pd.period_range(config.PERIODO_INI, config.PERIODO_FIN, freq='M')
    es_nuevo = dimc.set_index('cliente_key').es_nuevo_2025.to_dict()
    vta = compras.assign(m=compras.fecha.dt.to_period('M')).groupby(['cliente_id', 'm']).agg(
        n_compras=('boleta_id', 'size'), venta_neta=('venta_neta', 'sum'))
    filas = []
    for c, f in fechas.items():
        primera = pd.Timestamp(f[0])
        for m in meses:
            ini, fin = m.start_time.normalize(), m.end_time.normalize()
            compro = R.compro_entre(f, ini, fin)
            act = {w: R.activo_en(f, fin, w) for w in config.VENTANAS}
            act_prev = R.activo_en(f, ini - pd.Timedelta(days=1), config.VENTANA_PRINCIPAL)
            if primera > fin:
                estado = 'aun_sin_compras'
            elif ini <= primera <= fin:
                estado = 'nuevo' if es_nuevo.get(c, False) else 'primera_obs_previo'
            elif compro and not act_prev:
                estado = 'reactivado'
            elif compro:
                estado = 'recurrente'
            elif act[config.VENTANA_PRINCIPAL]:
                estado = 'activo_sin_compra'
            else:
                estado = 'inactivo'
            n, v = vta.loc[(c, m)] if (c, m) in vta.index else (0, 0.0)
            filas.append({'cliente_key': c, 'anio_mes': str(m), 'n_compras': int(n), 'venta_neta': float(v), 'compro_en_mes': compro,
                          'dias_desde_ultima_compra': R.dias_desde_ultima(f, fin),
                          **{f'activo_{w}d': a for w, a in act.items()}, f'estado_{config.VENTANA_PRINCIPAL}d': estado})
    return pd.DataFrame(filas)


# Cortes pedidos por la contraparte (13-10): local y segmento. Persona/negocio es solo complementario (clasificación del equipo).
CORTES = [('Total', None), ('Tienda principal', 'tienda_principal'), ('Formato principal', 'formato_principal'),
          ('Macrozona principal', 'macrozona_principal'), ('Segmento', 'segmento'),
          (config.CORTE_CLASIFICACION_NOMBRE, 'clasificacion_nombre')]


def mart_retencion(fechas, dimc):
    per = R.periodos(config.PERIODO_INI, config.PERIODO_FIN)
    es_nuevo = dimc.set_index('cliente_key').es_nuevo_2025.to_dict()
    est = R.estados_cliente_periodo(fechas, es_nuevo, per, config.VENTANAS)
    base = per.merge(pd.DataFrame({'ventana_dias': config.VENTANAS}), how='cross')
    base['base_confiable'] = (base.ini - pd.to_timedelta(base.ventana_dias, unit='D')) >= config.PERIODO_INI
    base = base[['periodo_tipo', 'periodo', 'ventana_dias', 'base_confiable']]
    attrs = dimc.set_index('cliente_key')
    salida = []
    for corte, col in CORTES:
        valores = est.assign(valor='Total') if col is None else est.assign(valor=est.cliente_id.map(attrs[col]))
        for valor, g in valores.groupby('valor'):
            ag = R.agregar_retencion(g, base)
            ag.insert(0, 'valor', valor)
            ag.insert(0, 'corte', corte)
            salida.append(ag)
    m = pd.concat(salida, ignore_index=True)
    m['es_ventana_principal'] = m.ventana_dias == config.VENTANA_PRINCIPAL
    m['n_suficiente'] = m.activos_inicio >= config.UMBRAL_N_MIN
    m['muestra_pequena'] = m.activos_inicio < config.UMBRAL_MUESTRA_PEQUENA
    return m, est


def mart_cohortes(compras, dimc):
    c = compras.merge(dimc[['cliente_key', 'cohorte_trimestre', 'tipo_cohorte']], left_on='cliente_id', right_on='cliente_key')
    c['trimestre_actividad'] = c.fecha.dt.to_period('Q')
    salida = []
    for tipo, g in [('Todos', c)] + list(c.groupby('tipo_cohorte')):
        tam = g.groupby('cohorte_trimestre').cliente_id.nunique()
        act = g.groupby(['cohorte_trimestre', 'trimestre_actividad']).agg(
            clientes_activos=('cliente_id', 'nunique'), compras=('boleta_id', 'size'), venta_neta=('venta_neta', 'sum')).reset_index()
        act['tipo_cohorte'] = tipo
        act['tamano_cohorte'] = act.cohorte_trimestre.map(tam)
        act['pct_activos'] = act.clientes_activos / act.tamano_cohorte
        act['trimestres_desde_ingreso'] = (act.trimestre_actividad - pd.PeriodIndex(act.cohorte_trimestre, freq='Q')).apply(lambda x: x.n)
        act['trimestre_actividad'] = act.trimestre_actividad.astype(str)
        salida.append(act)
    return pd.concat(salida, ignore_index=True)[['tipo_cohorte', 'cohorte_trimestre', 'tamano_cohorte', 'trimestre_actividad',
                                                 'trimestres_desde_ingreso', 'clientes_activos', 'pct_activos', 'compras', 'venta_neta']]


def _segmento_rfm(r, f):
    if r >= 4 and f >= 4: return 'Campeones'
    if r >= 3 and f >= 3: return 'Leales'
    if r >= 4 and f <= 2: return 'Recientes'
    if r <= 2 and f >= 3: return 'En riesgo'
    if r <= 2 and f <= 2: return 'Hibernando / perdidos'
    return 'Necesitan atención'


def mart_rfm(fechas, compras, dimc):
    corte = config.FECHA_CORTE
    g = compras.groupby('cliente_id').agg(ultima=('fecha', 'max'), primera=('fecha', 'min'),
                                          frecuencia=('boleta_id', 'size'), monto=('venta_neta', 'sum')).sort_index()
    g['recencia_dias'] = (corte - g.ultima).dt.days
    q = lambda s, labels: pd.qcut(s.rank(method='first'), 5, labels=labels).astype(int)
    g['r_score'] = q(g.recencia_dias, [5, 4, 3, 2, 1])
    g['f_score'] = q(g.frecuencia, [1, 2, 3, 4, 5])
    g['m_score'] = q(g.monto, [1, 2, 3, 4, 5])
    g['segmento_rfm'] = [_segmento_rfm(r, f) for r, f in zip(g.r_score, g.f_score)]
    limite = corte - pd.Timedelta(days=config.VENTANA_PRINCIPAL)
    g['una_compra_evaluable'] = g.primera <= limite
    g['es_una_sola_vez'] = (g.frecuencia == 1) & g.una_compra_evaluable
    for w in config.VENTANAS:
        g[f'activo_{w}d_al_corte'] = [R.activo_en(fechas[c], corte, w) for c in g.index]
    g = g.reset_index().rename(columns={'cliente_id': 'cliente_key', 'ultima': 'fecha_ultima_compra', 'primera': 'fecha_primera_compra'})
    return g.merge(dimc[['cliente_key', 'segmento', 'clasificacion_nombre', 'tipo_cohorte', 'tienda_principal', 'formato_principal']],
                   on='cliente_key', how='left')


def mart_venta_mensual(fb, dt):
    f = fb[fb.en_periodo].merge(dt[['tienda_key', 'nombre', 'formato', 'macrozona']], on='tienda_key', how='left')
    cortes = [('Total', None), ('Tienda', 'nombre'), ('Formato', 'formato'), ('Macrozona', 'macrozona'), ('Canal', 'canal')]
    salida = []
    for corte, col in cortes:
        x = f.assign(valor='Total' if col is None else f[col])
        for (valor, mes), g in x.groupby(['valor', 'anio_mes']):
            cv = g[g.es_compra_valida]
            salida.append({'corte': corte, 'valor': valor, 'anio_mes': mes, 'boletas': len(g),
                           'boletas_identificadas': int(g.es_identificada.sum()),
                           'clientes_unicos': g.loc[g.es_identificada, 'cliente_key'].nunique(),
                           'venta_neta': g.venta_neta.sum(), 'venta_identificada': g.loc[g.es_identificada, 'venta_neta'].sum(),
                           'venta_real_base': g.venta_real_base.sum(), 'descuento_monto': g.descuento_monto.sum(),
                           'monto_devolucion': g.monto_devolucion.sum(), 'unidades': g.unidades.sum(),
                           'ticket_promedio': cv.venta_neta.mean(), 'ticket_mediano': cv.venta_neta.median()})
    m = pd.DataFrame(salida)
    m['pct_boletas_identificadas'] = m.boletas_identificadas / m.boletas
    m['pct_venta_identificada'] = m.venta_identificada / m.venta_neta
    return m

# ----------------------------------------------------------------- KPIs
def kpi_resumen(fb, compras, rfm, mret, mcoh, fechas):
    k = []
    add = lambda kpi, v, u, d: k.append({'kpi': kpi, 'valor': v, 'unidad': u, 'definicion': d})
    p = fb[fb.en_periodo]
    add('boletas_2025', len(p), 'boletas', 'Boletas únicas con fecha 2025 (incluye solo-devolución)')
    add('venta_neta_2025', p.venta_neta.sum(), 'CLP nominal', 'Σ monto_linea registrado, neto de devoluciones (S02)')
    add('venta_real_2025', p.venta_real_base.sum(), f'CLP de {config.IPC_BASE}', 'Venta deflactada con IPC (S16)')
    add('pct_boletas_identificadas', p.es_identificada.mean(), 'proporción', 'Boletas con tarjeta / boletas 2025')
    add('pct_venta_identificada', p.loc[p.es_identificada, 'venta_neta'].sum() / p.venta_neta.sum(), 'proporción', 'Venta con tarjeta / venta 2025')
    add('clientes_con_compra_2025', compras.cliente_id.nunique(), 'clientes', 'Clientes con al menos una compra válida en 2025')
    ev = rfm[rfm.una_compra_evaluable]
    add('pct_una_sola_vez', ev.es_una_sola_vez.mean(), 'proporción',
        f'Clientes con 1 sola compra, entre los que tuvieron >= {config.VENTANA_PRINCIPAL} días para volver')
    gaps = pd.Series(np.concatenate([np.diff(f).astype(int) for f in fechas.values() if len(f) > 1]))
    add('intercompra_mediana_dias', gaps.median(), 'días', 'Mediana de días entre compras sucesivas del mismo cliente')
    add('intercompra_p90_dias', gaps.quantile(.9), 'días', 'Percentil 90 de días entre compras')
    for w in config.VENTANAS:
        add(f'pct_recompras_dentro_{w}d', (gaps <= w).mean(), 'proporción', f'Recompras que ocurren dentro de {w} días')
        add(f'activos_{w}d_al_corte', int(rfm[f'activo_{w}d_al_corte'].sum()), 'clientes', f'Activos al {config.FECHA_CORTE.date()} con ventana {w} d')
        add(f'pct_activos_{w}d_al_corte', rfm[f'activo_{w}d_al_corte'].mean(), 'proporción', f'Activos {w} d / clientes 2025')
    tot = mret[(mret.corte == 'Total') & (mret.periodo_tipo == 'trimestre')]
    for w in config.VENTANAS:
        q4 = tot[(tot.ventana_dias == w) & (tot.periodo == '2025Q4')].iloc[0]
        add(f'retencion_Q4_{w}d', q4.tasa_retencion, 'proporción', f'Activos al inicio de Q4 que siguen activos al cierre (W={w})')
        add(f'indice_reposicion_Q4_{w}d', q4.indice_reposicion, 'razón', f'Nuevos / perdidos en Q4 (W={w}); <1 = no repone')
    c = mcoh[(mcoh.tipo_cohorte == 'Nuevo 2025') & (mcoh.cohorte_trimestre == '2025Q1')]
    if len(c):
        add('cohorte_Q1_nuevos_activos_en_Q4', c.loc[c.trimestre_actividad == '2025Q4', 'pct_activos'].sum(), 'proporción',
            'Clientes nuevos que llegaron en Q1-2025 y compran en Q4-2025')
    return pd.DataFrame(k)

def mart_cobertura(n_origen, fb, compras):
    """Embudo de cobertura: cuántas boletas del origen quedan fuera de la retención y por qué."""
    p = fb[fb.en_periodo]
    ident = p[p.es_identificada]
    venta_2025 = p.venta_neta.sum()
    pasos = [('Boletas en el origen (POS)', n_origen, None),
             ('Duplicados exactos (se cuentan una vez)', -(n_origen - len(fb)), None),
             ('Fecha fuera de 2025', -int((~fb.en_periodo).sum()), fb.loc[~fb.en_periodo, 'venta_neta'].sum()),
             ('Anónimas, sin tarjeta (fuera de la retención de identificados)', -int((~p.es_identificada).sum()),
              p.loc[~p.es_identificada, 'venta_neta'].sum()),
             ('Venta neta <= 0: devoluciones sin compra neta (no es una compra)', -int((~ident.es_compra_valida).sum()),
              ident.loc[~ident.es_compra_valida, 'venta_neta'].sum())]
    filas, restante = [], 0
    for paso, (motivo, n, venta) in enumerate(pasos, start=1):
        restante = n if paso == 1 else restante + n
        filas.append({'paso': paso, 'motivo': motivo, 'boletas': n, 'boletas_restantes': restante, 'venta_neta': venta})
    filas.append({'paso': len(pasos) + 1, 'motivo': 'Compras usadas en la retención', 'boletas': len(compras),
                  'boletas_restantes': len(compras), 'venta_neta': compras.venta_neta.sum()})
    c = pd.DataFrame(filas)
    c['pct_del_origen'] = c.boletas.abs() / n_origen
    c['pct_venta_2025'] = c.venta_neta.abs() / venta_2025
    return c


def mart_valor_riesgo(estados, compras):
    """Traduce la pérdida de clientes de Q4 a pesos: gasto trimestral de esos clientes mientras estuvieron activos, anualizado.
    Gasto trimestral de un cliente = su venta 2025 / n° de trimestres entre su primera y su última compra (inclusive)."""
    g = compras.groupby('cliente_id').agg(venta=('venta_neta', 'sum'), ini=('fecha', 'min'), fin=('fecha', 'max'))
    trimestres = (g.fin.dt.to_period('Q') - g.ini.dt.to_period('Q')).apply(lambda x: x.n) + 1
    gasto_q3 = g.venta / trimestres                               # gasto trimestral típico de cada cliente
    filas = []
    for w in config.VENTANAS:
        e = estados[(estados.periodo == '2025Q4') & (estados.ventana_dias == w)]
        perdidos, activos = e.loc[e.perdido, 'cliente_id'], e.loc[e.activo_inicio, 'cliente_id']
        venta_perd = gasto_q3.reindex(perdidos).fillna(0).sum()
        gasto_prom = gasto_q3.reindex(activos).fillna(0).mean() if len(activos) else np.nan
        filas.append({'ventana_dias': w, 'perdidos_q4': len(perdidos), 'gasto_trimestral_perdidos': venta_perd,
                      'venta_anual_en_riesgo': venta_perd * 4, 'activos_inicio_q4': len(activos),
                      'gasto_trimestral_promedio_activo': gasto_prom,
                      'valor_anual_1pp_retencion': 0.01 * len(activos) * gasto_prom * 4})
    return pd.DataFrame(filas)


def kpi_cobertura_riesgo(cob, rie):
    k = []
    add = lambda kpi, v, u, d: k.append({'kpi': kpi, 'valor': v, 'unidad': u, 'definicion': d})
    usadas = cob.iloc[-1]
    add('pct_boletas_fuera_de_retencion', 1 - usadas.boletas / cob.iloc[0].boletas, 'proporción',
        'Boletas del origen que no entran a la retención (duplicadas, 2026, anónimas o solo devolución); ver mart_cobertura')
    add('pct_venta_2025_en_retencion', usadas.pct_venta_2025, 'proporción', 'Venta 2025 cubierta por las compras usadas en la retención')
    r = rie.set_index('ventana_dias').loc[config.VENTANA_PRINCIPAL]
    add(f'venta_anual_en_riesgo_{config.VENTANA_PRINCIPAL}d', r.venta_anual_en_riesgo, 'CLP nominal / año',
        'Gasto trimestral de los clientes perdidos en Q4 (mientras estuvieron activos) × 4; supone que su gasto se habría mantenido')
    add(f'valor_anual_1pp_retencion_{config.VENTANA_PRINCIPAL}d', r.valor_anual_1pp_retencion, 'CLP nominal / año',
        'Venta anual que significa retener 1 punto porcentual más de los activos al inicio de Q4')
    return pd.DataFrame(k)

# ----------------------------------------------------------------- orquestación
def ejecutar(pl):
    dt = dim_tiempo(pl['boletas'], pl['campanas'], pl['ipc_mensual'])
    dti = dim_tienda(pl['tiendas'])
    dmp = dim_medio_pago(pl['medios_pago'])
    dpr = dim_producto(pl['productos'], pl['boleta_detalle'])
    dca = pl['campanas'].drop(columns=['descuento_pct_origen'])
    fl = fact_venta_linea(pl['boleta_detalle'], pl['boletas'])
    fb = fact_venta_boleta(pl['boletas'], pl['boleta_detalle'], pl['tiendas'], pl['ipc_mensual'])
    compras = compras_validas(fb)
    fechas = R.fechas_por_cliente(compras)
    dcl = dim_cliente(pl['clientes'], pl['geografia'], compras, pl['tiendas'])
    mcm = mart_cliente_mes(fechas, dcl, compras)
    mret, estados = mart_retencion(fechas, dcl)
    mcoh = mart_cohortes(compras, dcl)
    rfm = mart_rfm(fechas, compras, dcl)
    mvm = mart_venta_mensual(fb, dti)
    cob = mart_cobertura(pl['_n_bronce']['boletas'], fb, compras)
    rie = mart_valor_riesgo(estados, compras)
    kpi = pd.concat([kpi_resumen(fb, compras, rfm, mret, mcoh, fechas), kpi_cobertura_riesgo(cob, rie)], ignore_index=True)
    oro = {'dim_tiempo': dt, 'dim_tienda': dti, 'dim_medio_pago': dmp, 'dim_producto': dpr, 'dim_campana': dca,
           'dim_cliente': dcl, 'fact_venta_boleta': fb, 'fact_venta_linea': fl, 'mart_cliente_mes': mcm,
           'mart_retencion': mret, 'mart_cohortes': mcoh, 'mart_rfm_cliente': rfm, 'mart_venta_mensual': mvm,
           'mart_cobertura': cob, 'mart_valor_riesgo': rie, 'mart_kpi_resumen': kpi}
    for nombre, df in oro.items():
        L.escribir_csv(df, config.ORO / f'{nombre}.csv')
    oro['_estados'] = estados
    return oro
