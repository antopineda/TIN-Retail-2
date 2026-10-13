# -*- coding: utf-8 -*-
"""Validaciones automáticas de la cadena. Una falla 'critica' detiene la entrega (exit code 1)."""
import pandas as pd

import config


def ejecutar(pl, oro, log):
    res = []

    def chequear(vid, descripcion, severidad, ok, detalle=''):
        res.append({'id': vid, 'validacion': descripcion, 'severidad': severidad, 'resultado': 'OK' if ok else 'FALLA',
                    'detalle': detalle})

    nb = pl['_n_bronce']
    lg = log.df().set_index('regla').filas_afectadas
    b, d = pl['boletas'], pl['boleta_detalle']
    fb, fl = oro['fact_venta_boleta'], oro['fact_venta_linea']

    # --- integridad bronce -> plata
    esperado = nb['boletas'] - lg['R01'] - lg['R01b']
    chequear('V01', 'Boletas plata = bronce − duplicados', 'critica', len(b) == esperado, f'{nb["boletas"]} − {lg["R01"]} − {lg["R01b"]} = {esperado}; plata = {len(b)}')
    chequear('V02', 'boleta_id único en plata', 'critica', b.boleta_id.is_unique)
    chequear('V03', 'Ninguna línea de detalle se elimina', 'critica', len(d) == nb['boleta_detalle'], f'bronce {nb["boleta_detalle"]} / plata {len(d)}')
    chequear('V04', '(boleta_id, linea_seq) único', 'critica', not d.duplicated(['boleta_id', 'linea_seq']).any())
    chequear('V05', 'Todas las fechas de boleta parseadas', 'critica', b.fecha.notna().all(), f'nulas: {b.fecha.isna().sum()}')
    nulos = {c: int(d[c].isna().sum()) for c in ['precio_unitario', 'monto_linea', 'descuento_pct']}
    chequear('V06', 'Montos y descuentos parseados sin nulos', 'critica', sum(nulos.values()) == 0, str(nulos))
    chequear('V07', f'Descuentos en el dominio {sorted(config.DESCUENTOS_VALIDOS)}', 'advertencia', not d.flag_descuento_fuera_dominio.any(),
             f'fuera de dominio: {int(d.flag_descuento_fuera_dominio.sum())}')
    t = pl['tiendas']
    chequear('V08', 'Todas las tiendas tienen región y macrozona', 'critica', t.region.notna().all() and t.macrozona.notna().all(),
             t.loc[t.region.isna() | t.macrozona.isna(), 'nombre'].tolist())
    chequear('V09', 'SKU único en productos', 'critica', pl['productos'].sku.is_unique)
    chequear('V10', 'Todas las categorías de producto mapeadas', 'advertencia', pl['productos'].categoria.notna().all())

    # --- integridad referencial del modelo estrella
    fk = {'tienda_key': oro['dim_tienda'].tienda_key, 'medio_key': oro['dim_medio_pago'].medio_key,
          'cliente_key': oro['dim_cliente'].cliente_key, 'fecha': oro['dim_tiempo'].fecha}
    huerf = {k: int((~fb[k].isin(v)).sum()) for k, v in fk.items()}
    chequear('V11', 'FK fact_venta_boleta -> dimensiones', 'critica', sum(huerf.values()) == 0, str(huerf))
    h2 = {'boleta_id': int((~fl.boleta_id.isin(fb.boleta_id)).sum()), 'sku_key': int((~fl.sku_key.isin(oro['dim_producto'].sku_key)).sum())}
    chequear('V12', 'FK fact_venta_linea -> boleta y producto', 'critica', sum(h2.values()) == 0, str(h2))
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
    chequear('V17', 'Oro sin RUT ni nombre de cliente (S15)', 'critica', not pii, str(pii))
    patron_rut = r'\b\d{1,2}\.?\d{3}\.?\d{3}-?[\dkK]\b'
    con_rut = [f'{t}.{c}' for t, df in oro.items() if not t.startswith('_') for c in df.columns
               if df[c].dtype == object and df[c].astype(str).str.contains(patron_rut, regex=True).any()]
    chequear('V17b', 'Ningún valor de oro tiene forma de RUT', 'critica', not con_rut, str(con_rut))

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
    return pd.DataFrame(res)
