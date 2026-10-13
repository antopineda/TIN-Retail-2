# -*- coding: utf-8 -*-
# Chequeos puntuales de SOLO LECTURA (Retail grupo_2). Reutiliza 01_perfilamiento.py.
import io, contextlib, runpy, json, urllib.request
from pathlib import Path
import pandas as pd, numpy as np
with contextlib.redirect_stdout(io.StringIO()):
    g = runpy.run_path(str(Path(__file__).parent / '01_perfilamiento.py'))
b, d, cl = g['b'], g['d'], g['cl']
bu = b.drop_duplicates()
tot = d.groupby('boleta_id').ml.sum(); bu = bu.assign(total=bu.boleta_id.map(tot))
print('ticket medio anónimo vs identificado:', bu.groupby(bu.cliente_id.isna()).total.agg(['mean', 'median', 'count']).round(0).to_dict())
print('% venta anónima (sin dups, todo el periodo):', round(bu[bu.cliente_id.isna()].total.sum() / bu.total.sum() * 100, 2))
x = d.merge(bu[['boleta_id', 'cliente_id', 'canal', 'f', 'tienda_id']], on='boleta_id').merge(cl[['cliente_id', 'segmento']], on='cliente_id', how='left')
x['seg'] = x.segmento.fillna('anónimo')
print('% líneas con desc 10 por segmento:', (x.groupby('seg').desc.apply(lambda s: (s == 10).mean() * 100)).round(1).to_dict())
print('% líneas con desc 10 por canal:', (x.groupby('canal').desc.apply(lambda s: (s == 10).mean() * 100)).round(1).to_dict())
print('% líneas con desc 10 por tienda:', (x.groupby('tienda_id').desc.apply(lambda s: (s == 10).mean() * 100)).round(1).to_dict())
print('ticket medio por segmento:', bu.merge(cl[['cliente_id', 'segmento']], on='cliente_id', how='left').groupby('segmento').total.mean().round(0).to_dict())
print('boletas por cliente por segmento:', bu.merge(cl[['cliente_id', 'segmento']], on='cliente_id').groupby('segmento').cliente_id.apply(lambda s: s.value_counts().mean()).round(2).to_dict())
# líneas que se duplicarían al unir detalle con cabecera sin deduplicar
j = d.merge(b[['boleta_id']], on='boleta_id')
print('filas detalle', len(d), ' tras join con cabecera con dups:', len(j), ' inflación $:', round(j.ml.sum() - d.ml.sum()))
# rango de fechas Online vs resto
bo = bu[bu.tienda_id == 10]; print('Online primera/última boleta:', bo.f.min().date(), bo.f.max().date(), ' % boletas 2025:', round(len(bo[bo.f.dt.year == 2025]) / len(bu[bu.f.dt.year == 2025]) * 100, 1))
# Clientes presentes en >1 macrozona (tarjeta por hogar / o dato ruidoso)
# API IPC
try:
    with urllib.request.urlopen('https://mindicador.cl/api/ipc/2025', timeout=15) as r:
        ipc = json.load(r)
    s = sorted((x['fecha'][:7], x['valor']) for x in ipc['serie'])
    print('IPC 2025 (var % mensual):', s, ' acumulado aprox:', round((np.prod([1 + v / 100 for _, v in s]) - 1) * 100, 2))
except Exception as e:
    print('API IPC no disponible:', repr(e))
# duplicados probables tras quitar exactos
bi = bu[bu.cliente_id.notna()]
k = ['cliente_id', 'f', 'tienda_id']
dp = bi[bi.duplicated(k, keep=False)]
print('tras quitar dups exactos: filas con mismo cliente+fecha+tienda:', len(dp), ' grupos:', dp.groupby(k).ngroups,
      ' de ellos con mismo total:', dp.groupby(k).total.nunique().eq(1).sum())
print('cliente-día con >1 boleta (sin dups exactos):', (bi.groupby(['cliente_id', 'f']).size() > 1).sum())
# huella de boleta: mismo set de (sku,cantidad) para mismo cliente y fecha
fp = d.sort_values(['boleta_id', 'sku']).groupby('boleta_id').apply(lambda s: tuple(zip(s.sku, s.cantidad)))
bi = bi.assign(fp=bi.boleta_id.map(fp))
print('boletas con mismo cliente+fecha+mismos productos (id distinto):', bi.duplicated(['cliente_id', 'f', 'fp'], keep=False).sum())
