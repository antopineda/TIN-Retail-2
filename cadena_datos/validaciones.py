# -*- coding: utf-8 -*-
"""Pruebas de calidad automáticas: corren en cada ejecución de la cadena.

- severidad 'critica'  -> accion 'bloquea': la cadena termina con código 1 y el prototipo muestra la corrida como no publicable.
- severidad 'advertencia' -> accion 'avisa': se publica, pero el aviso queda en validaciones.csv y en el pie del prototipo.

Grupos: F = una por fuente (SQLite, CSV, JSON, API); V = integridad bronce -> plata -> oro; M = protegen la métrica.
"""
import json
import sqlite3

import numpy as np
import pandas as pd

import config
import metricas as Mt


def ejecutar(pl, oro, log):
    res = []

    def chequear(vid, descripcion, severidad, ok, detalle='', filas=None):
        """filas: cuántas filas (o elementos) no cumplen. Si la prueba pasa es 0."""
        res.append({'id': vid, 'validacion': descripcion, 'severidad': severidad,
                    'accion': 'bloquea' if severidad == 'critica' else 'avisa', 'resultado': 'OK' if bool(ok) else 'FALLA',
                    'filas_fallidas': 0 if bool(ok) else (int(filas) if filas is not None else None), 'detalle': detalle})

    # --- una prueba por fuente (sobre la copia en bronce)
    with sqlite3.connect(config.BRONCE / 'origen_pos.sqlite') as con:
        tablas = set(pd.read_sql("select name from sqlite_master where type='table'", con).name)
        n_bol = con.execute('select count(*) from boletas').fetchone()[0] if 'boletas' in tablas else 0
    faltan = sorted(set(config.TABLAS_POS) - tablas)
    chequear('F01', 'Fuente SQLite (POS): están las 7 tablas y hay boletas', 'critica', not faltan and n_bol > 0,
             f'faltan: {faltan}; boletas: {n_bol}', filas=len(faltan))
    cab = pd.read_csv(config.BRONCE / 'origen_maestro_productos.csv', sep=';', encoding=config.ENCODING_MAESTRO, nrows=0).columns
    req = {'sku', 'categoria', 'costo_unitario', 'precio_lista', 'activo'}
    chequear('F02', 'Fuente CSV (maestro): columnas requeridas presentes y filas > 0', 'critica',
             req <= set(cab) and len(pl['productos']) > 0, f'faltan: {sorted(req - set(cab))}')
    js = json.loads((config.BRONCE / 'origen_promociones.json').read_text(encoding='utf-8'))
    camp = pl['campanas']
    chequear('F03', 'Fuente JSON (campañas): cada campaña tiene id y fechas dentro de 2025', 'critica',
             len(js.get('campanas', [])) == len(camp) and camp.fecha_ini.ge(config.PERIODO_INI).all()
             and camp.fecha_fin.le(config.PERIODO_FIN + pd.Timedelta(days=1)).all(), f'{len(camp)} campañas')
    ipc = pl['ipc_mensual'].dropna(subset=['ipc_var_pct'])
    lo, hi = config.IPC_RANGO_VALIDO
    chequear('F04', f'Fuente API (IPC): 12 meses de 2025 con variación entre {lo}% y {hi}%', 'critica',
             len(ipc) == 12 and ipc.ipc_var_pct.between(lo, hi).all(), f'{len(ipc)} meses',
             filas=abs(12 - len(ipc)) + int((~ipc.ipc_var_pct.between(lo, hi)).sum()))
    man = pd.read_csv(config.BRONCE / 'manifiesto_bronce.csv')
    est_ipc = man.loc[man.archivo.str.contains('ipc'), 'estado'].iloc[0] if 'estado' in man else 'ok'
    chequear('F05', 'Fuente API (IPC) respondió en esta corrida (si no: se usó el último snapshot bueno, S21)', 'advertencia',
             est_ipc == 'ok', man.loc[man.archivo.str.contains('ipc'), 'ruta_origen'].iloc[0])

    nb = pl['_n_bronce']
    lg = log.df().set_index('regla').filas_afectadas
    b, d = pl['boletas'], pl['boleta_detalle']
    fb, fl = oro['fact_venta_boleta'], oro['fact_venta_linea']

    # --- integridad bronce -> plata
    esperado = nb['boletas'] - lg['R01'] - lg['R01b']
    chequear('V01', 'Boletas plata = bronce − duplicados', 'critica', len(b) == esperado, f'{nb["boletas"]} − {lg["R01"]} − {lg["R01b"]} = {esperado}; plata = {len(b)}', filas=abs(len(b) - esperado))
    chequear('V02', 'boleta_id único en plata', 'critica', b.boleta_id.is_unique, filas=int(b.boleta_id.duplicated().sum()))
    chequear('V03', 'Ninguna línea de detalle se elimina', 'critica', len(d) == nb['boleta_detalle'], f'bronce {nb["boleta_detalle"]} / plata {len(d)}', filas=abs(nb['boleta_detalle'] - len(d)))
    chequear('V04', '(boleta_id, linea_seq) único', 'critica', not d.duplicated(['boleta_id', 'linea_seq']).any(),
             filas=int(d.duplicated(['boleta_id', 'linea_seq']).sum()))
    chequear('V05', 'Todas las fechas de boleta parseadas', 'critica', b.fecha.notna().all(), f'nulas: {b.fecha.isna().sum()}', filas=int(b.fecha.isna().sum()))
    nulos = {c: int(d[c].isna().sum()) for c in ['precio_unitario', 'monto_linea', 'descuento_pct']}
    chequear('V06', 'Montos y descuentos parseados sin nulos', 'critica', sum(nulos.values()) == 0, str(nulos), filas=sum(nulos.values()))
    chequear('V07', f'Descuentos en el dominio {sorted(config.DESCUENTOS_VALIDOS)}', 'advertencia', not d.flag_descuento_fuera_dominio.any(),
             f'fuera de dominio: {int(d.flag_descuento_fuera_dominio.sum())}', filas=int(d.flag_descuento_fuera_dominio.sum()))
    t = pl['tiendas']
    chequear('V08', 'Todas las tiendas tienen región y macrozona', 'critica', t.region.notna().all() and t.macrozona.notna().all(),
             t.loc[t.region.isna() | t.macrozona.isna(), 'nombre'].tolist())
    chequear('V09', 'SKU único en productos', 'critica', pl['productos'].sku.is_unique)
    chequear('V10', 'Todas las categorías de producto mapeadas', 'advertencia', pl['productos'].categoria.notna().all())

    # --- integridad referencial del modelo estrella
    fk = {'tienda_key': oro['dim_tienda'].tienda_key, 'medio_key': oro['dim_medio_pago'].medio_key,
          'cliente_key': oro['dim_cliente'].cliente_key, 'fecha': oro['dim_tiempo'].fecha}
    huerf = {k: int((~fb[k].isin(v)).sum()) for k, v in fk.items()}
    chequear('V11', 'FK fact_venta_boleta -> dimensiones', 'critica', sum(huerf.values()) == 0, str(huerf), filas=sum(huerf.values()))
    h2 = {'boleta_id': int((~fl.boleta_id.isin(fb.boleta_id)).sum()), 'sku_key': int((~fl.sku_key.isin(oro['dim_producto'].sku_key)).sum())}
    chequear('V12', 'FK fact_venta_linea -> boleta y producto', 'critica', sum(h2.values()) == 0, str(h2), filas=sum(h2.values()))
    chequear('V13', 'Llaves de dimensiones únicas', 'critica',
             all(oro[t][k].is_unique for t, k in [('dim_cliente', 'cliente_key'), ('dim_tienda', 'tienda_key'),
                                                  ('dim_producto', 'sku_key'), ('dim_tiempo', 'fecha')]))

    # --- conciliación de montos
    s_l, s_b, s_p = fl.monto_linea.sum(), fb.venta_neta.sum(), d.monto_linea.sum()
    chequear('V14', 'Σ líneas = Σ boletas (oro)', 'critica', abs(s_l - s_b) < 0.5, f'{s_l:,.0f} vs {s_b:,.0f}')
    chequear('V15', 'Σ detalle plata = Σ líneas oro', 'critica', abs(s_p - s_l) < 0.5, f'{s_p:,.0f} vs {s_l:,.0f}')
    p = fb[fb.en_periodo]
    dif = p.venta_neta.sum() / p.venta_neta_calculada.sum() - 1
    chequear('V16', 'Venta registrada vs calculada 2025 difiere < 2% (sustento S02)', 'advertencia', abs(dif) < 0.02, f'{dif:.2%}')

    # --- datos personales
    pii = [f'{t}.{c}' for t, df in oro.items() if not t.startswith('_') for c in df.columns
           if c.lower().startswith('rut') or (c == 'nombre' and t not in ('dim_tienda', 'dim_medio_pago', 'dim_producto', 'dim_campana'))]
    chequear('V17', 'Oro sin RUT ni nombre de cliente (S15)', 'critica', not pii, str(pii), filas=len(pii))
    patron_rut = r'\b\d{1,2}\.?\d{3}\.?\d{3}-?[\dkK]\b'
    con_rut = [f'{t}.{c}' for t, df in oro.items() if not t.startswith('_') for c in df.columns
               if df[c].dtype == object and df[c].astype(str).str.contains(patron_rut, regex=True).any()]
    chequear('V17b', 'Ningún valor de oro tiene forma de RUT', 'critica', not con_rut, str(con_rut), filas=len(con_rut))

    # --- coherencia de los marts
    m = oro['mart_retencion']
    ok1 = (m.activos_fin == m.retenidos + m.nuevos + m.reactivados + m.primeras_obs_previos).all()
    ok2 = (m.activos_inicio == m.retenidos + m.perdidos).all()
    chequear('V18', 'Identidad de retención (A1 = ret + nuevos + react + prim.obs; A0 = ret + perdidos)', 'critica', ok1 and ok2)
    tot = m[(m.corte == 'Total') & (m.periodo == '2025Q4')].set_index('ventana_dias').activos_fin
    rfm = oro['mart_rfm_cliente']
    coh = all(tot[w] == rfm[f'activo_{w}d_al_corte'].sum() for w in config.VENTANAS)
    chequear('V19', 'Activos al cierre de Q4 (mart_retencion) = activos al corte (RFM)', 'critica', coh,
             str({w: (int(tot[w]), int(rfm[f"activo_{w}d_al_corte"].sum())) for w in config.VENTANAS}))
    sumas_corte = m[(m.periodo_tipo == 'mes') & m.es_ventana_principal].groupby(['corte', 'periodo']).activos_fin.sum().unstack(0)
    chequear('V20', 'Cada corte reparte a todos los clientes (suma por corte = Total)', 'advertencia',
             sumas_corte.drop(columns='Total').eq(sumas_corte.Total, axis=0).all().all())
    mcm = oro['mart_cliente_mes']
    chequear('V21', 'mart_cliente_mes = clientes × 12 meses', 'critica', len(mcm) == rfm.cliente_key.nunique() * 12,
             f'{len(mcm)} filas')
    cob = oro['mart_cobertura']
    chequear('V22', 'Embudo de cobertura cuadra: origen − exclusiones = compras usadas', 'critica',
             cob.iloc[-2].boletas_restantes == cob.iloc[-1].boletas, f'{cob.iloc[-2].boletas_restantes} vs {cob.iloc[-1].boletas}')

    # --- pruebas que protegen la métrica
    chequear('M01', 'Clave del hecho única: boleta_id en fact_venta_boleta', 'critica', fb.boleta_id.is_unique,
             f'{int(fb.boleta_id.duplicated().sum())} boleta_id repetidos', filas=int(fb.boleta_id.duplicated().sum()))
    chequear('M02', 'Recarga sin duplicar ni perder: filas del hecho = boletas en plata', 'critica', len(fb) == len(b),
             f'hecho {len(fb)} / plata {len(b)}', filas=abs(len(fb) - len(b)))
    comp = fb[fb.es_identificada & fb.es_compra_valida & fb.en_periodo]
    chequear('M03', 'Fechas de las compras de la métrica dentro de 2025', 'critica',
             comp.fecha.between(config.PERIODO_INI, config.PERIODO_FIN).all(),
             f'{comp.fecha.min().date()} a {comp.fecha.max().date()}',
             filas=int((~comp.fecha.between(config.PERIODO_INI, config.PERIODO_FIN)).sum()))
    t = m.tasa_retencion.dropna()
    ic_ok = ((m.ic95_inf <= m.tasa_retencion + 1e-9) & (m.tasa_retencion <= m.ic95_sup + 1e-9)) | m.tasa_retencion.isna()
    chequear('M04', 'Tasas de retención entre 0 y 1, dentro de su intervalo de confianza', 'critica', t.between(0, 1).all() and ic_ok.all(),
             filas=int((~t.between(0, 1)).sum() + (~ic_ok).sum()))
    fct = oro['fact_cliente_trimestre']
    e = fct[(fct.trimestre == '2025Q4') & (fct.ventana_dias == config.VENTANA_PRINCIPAL)]
    directa = e.retenido.sum() / e.activo_inicio.sum()
    oficial = Mt.retencion(m).tasa_retencion
    chequear('M05', 'Cifra oficial (retención Q4, 90 d) = recálculo directo desde fact_cliente_trimestre', 'critica',
             abs(directa - oficial) < 1e-12 and fct.duplicated(['cliente_key', 'trimestre', 'ventana_dias']).sum() == 0, f'{oficial:.4f}')
    pv = fb[fb.en_periodo]
    pm = pv.margen_bruto.sum() / pv.venta_sin_iva.sum()
    chequear('M06', 'Margen bruto 2025 entre 0% y 60% de la venta sin IVA', 'critica', 0 < pm < 0.6, f'{pm:.1%}')
    lp = fl[fl.fecha.between(config.PERIODO_INI, config.PERIODO_FIN)]
    cob_costo = 1 - lp.loc[lp.flag_costo_imputado, 'monto_linea'].sum() / lp.monto_linea.sum()
    chequear('M07', 'Al menos 95% de la venta tiene costo del maestro (el resto se imputa, S17)', 'advertencia', cob_costo >= 0.95,
             f'{cob_costo:.1%}')
    mens = pv.groupby('anio_mes').es_identificada.mean()
    minimo = config.SLA['completitud_min_boletas_identificadas']
    chequear('M08', f'Acuerdo de servicio, completitud: cada mes con >= {minimo:.0%} de boletas con tarjeta', 'advertencia',
             (mens >= minimo).all(), f'mínimo mensual {mens.min():.1%} ({mens.idxmin()})', filas=int((mens < minimo).sum()))
    out = pd.DataFrame(res)
    out['filas_fallidas'] = out.filas_fallidas.astype('Int64')
    return out
