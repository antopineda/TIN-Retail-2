# -*- coding: utf-8 -*-
"""
Profundización de SOLO LECTURA sobre hallazgos del 01_perfilamiento.py (Retail grupo_2).
Reutiliza los parsers de 01 sin modificar fuentes.
Uso:  python exploracion/02_profundizacion.py > exploracion/salida_profundizacion.txt
"""
import io, contextlib, runpy
from pathlib import Path
import numpy as np, pandas as pd

# Ejecuta 01 en silencio para reutilizar sus DataFrames ya parseados
with contextlib.redirect_stdout(io.StringIO()):
    g = runpy.run_path(str(Path(__file__).parent / '01_perfilamiento.py'))
T, b, d, cl, prod, promo, tt = g['T'], g['b'], g['d'], g['cl'], g['prod'], g['promo'], g['tt']
parse_monto, fmt_fecha = g['parse_monto'], g['fmt_fecha']
def h(t): print('\n' + '=' * 10, t, '=' * 10)

h('1. MONTO_LINEA vs cantidad*precio*(1-desc): ¿IVA?')
r = (d.ml / d.ml_calc)
disc = (d.dif.abs() > 2)
print('discrepantes', disc.sum(), 'de', len(d), f'({disc.mean()*100:.2f}%)')
print('ratio redondeado (discrepantes):\n', r[disc].round(2).value_counts().sort_index().head(40).to_string())
print('ratio en [1.185,1.195] (≈IVA 19%):', (disc & r.between(1.185, 1.195)).sum())
print('ejemplos con "-.905":', d[d.monto_linea.isin(['-.905', '-.884'])][['boleta_id', 'linea', 'sku', 'cantidad', 'precio_unitario', 'descuento', 'monto_linea']].to_string())
print('discrepantes por formato monto_linea:\n', d[disc].monto_linea.map(g['fmt_monto']).value_counts().to_string())
print('discrepantes con cantidad<0:', (disc & (d.cantidad < 0)).sum())

h('2. DEVOLUCIONES (cantidad < 0)')
dev = d[d.cantidad < 0]
print('líneas', len(dev), ' boletas', dev.boleta_id.nunique(), ' monto', dev.ml.sum())
bl = d.groupby('boleta_id').agg(n=('linea', 'size'), neg=('cantidad', lambda s: (s < 0).sum()))
print('boletas con TODAS las líneas negativas:', ((bl.neg == bl.n) & (bl.neg > 0)).sum(), ' mixtas:', ((bl.neg > 0) & (bl.neg < bl.n)).sum())
print('signo monto coincide con signo cantidad:', (np.sign(dev.ml) == -1).mean())
ex = dev.merge(b[['boleta_id', 'f', 'cliente_id', 'tienda_id']], on='boleta_id')
print('devoluciones con cliente identificado:', ex.cliente_id.notna().sum())
# ¿existe venta previa del mismo sku al mismo cliente?
vta = d[d.cantidad > 0].merge(b[['boleta_id', 'f', 'cliente_id']], on='boleta_id')
m = ex.merge(vta, on=['cliente_id', 'sku'], suffixes=('_dev', '_vta'))
m = m[m.f_vta <= m.f_dev]
print('devoluciones con compra previa del mismo sku por el mismo cliente:', m[['boleta_id_dev', 'linea_dev']].drop_duplicates().shape[0], 'de', ex.cliente_id.notna().sum())

h('3. CANTIDADES GRANDES (10-40) Y CLIENTES TIPO EMPRESA')
cl2 = cl.copy()
cl2['tipo_nombre'] = np.select(
    [cl2.nombre.str.match(r'^(Sr\.|Sra\.|Familia)'), cl2.nombre.str.match(r'^(Comercial|Distribuidora|Almacén|Kiosco|Botillería|Minimarket|Inversiones)')],
    ['persona/hogar', 'negocio'], 'otro')
print(cl2.tipo_nombre.value_counts().to_string())
print('prefijos:', cl2.nombre.str.split().str[0].value_counts().to_dict())
big = d[d.cantidad >= 10].merge(b[['boleta_id', 'cliente_id']], on='boleta_id').merge(cl2[['cliente_id', 'tipo_nombre']], on='cliente_id', how='left')
print('líneas cantidad>=10 por tipo cliente:', big.tipo_nombre.fillna('anónimo').value_counts().to_dict(), ' boletas', big.boleta_id.nunique())
print('cantidad>=10 por sku (top):', big.sku.value_counts().head(5).to_dict())
bt = b[b.cliente_id.notna()].merge(cl2[['cliente_id', 'tipo_nombre', 'segmento']], on='cliente_id')
print('boletas por tipo cliente:', bt.tipo_nombre.value_counts().to_dict())
print('segmento x tipo:\n', pd.crosstab(cl2.segmento, cl2.tipo_nombre).to_string())
tot = d.groupby('boleta_id').ml.sum()
bt['total'] = bt.boleta_id.map(tot)
print('ticket promedio por tipo cliente:\n', bt.groupby('tipo_nombre').total.agg(['mean', 'median', 'count']).round(0).to_string())

h('4. DUPLICADOS DE (boleta_id, linea) EN DETALLE')
dd = d[d.duplicated(['boleta_id', 'linea'], keep=False)].sort_values(['boleta_id', 'linea'])
print('filas involucradas', len(dd), ' boletas', dd.boleta_id.nunique())
print(dd[['boleta_id', 'linea', 'sku', 'cantidad', 'precio_unitario', 'descuento', 'monto_linea']].head(16).to_string())
# ¿coinciden las boletas duplicadas del header?
bdup = b[b.boleta_id.duplicated(keep=False)]
print('boleta_id duplicados en cabecera:', bdup.boleta_id.nunique(), ' ¿de ellos con dup de líneas en detalle?:', bdup.boleta_id.isin(dd.boleta_id).sum())
print('¿la cabecera duplicada es idéntica?:', bdup.drop(columns=['fmt', 'f', 'mes_n', 'mes_ok'], errors='ignore').duplicated(keep=False).all())
# mismas líneas: ¿mismo sku distinto formato? (misma boleta, misma línea, mismo sku, mismo valor parseado)
same = dd.groupby(['boleta_id', 'linea']).agg(nsku=('sku', 'nunique'), nml=('ml', 'nunique'), npu=('pu', 'nunique'), ncant=('cantidad', 'nunique'))
print('grupos (boleta,linea) duplicados: con distinto sku', (same.nsku > 1).sum(), ' mismo sku y mismo monto parseado', ((same.nsku == 1) & (same.nml == 1)).sum(), ' total grupos', len(same))
print('líneas por boleta con dups:', dd.groupby('boleta_id').linea.max().describe().to_string())

h('5. COLUMNA mes vs FECHA')
mm = b[~b.mes_ok]
print('no coinciden', len(mm), f'({len(mm)/len(b)*100:.1f}%)')
print('diferencia mes_col - mes_fecha:\n', (mm.mes_n - mm.f.dt.month).value_counts().sort_index().to_string())
print('de estas, fecha en 2026:', (mm.f.dt.year == 2026).sum())
print('coincidencia en 2025 solamente:', b[b.f.dt.year == 2025].mes_ok.mean().round(4))
fut = b[b.f.dt.year == 2026]
print('boletas 2026:', len(fut), ' formatos:', fut.fmt.value_counts().to_dict())
print('2026: mes columna vs mes fecha:', list(zip(fut.fecha, fut.mes))[:20])
print('2026 si fuera 2025 (restando 1 año) ¿coincide mes?:', (fut.f.dt.month == fut.mes_n).mean())
print('2026: canal', fut.canal.value_counts().to_dict(), ' clientes', fut.cliente_id.nunique())

h('6. REGION DE LA BOLETA ≠ REGION DE LA TIENDA')
clr = cl[['cliente_id', 'comuna_id']].merge(T['comunas'], on='comuna_id').merge(T['regiones'], on='region_id', how='left').rename(columns={'region': 'region_cliente'})
bb = b.merge(tt[['tienda_id', 'nombre', 'region']].rename(columns={'region': 'region_tienda'}), on='tienda_id').merge(clr[['cliente_id', 'region_cliente']], on='cliente_id', how='left')
mis = bb[bb.region != bb.region_tienda]
print('mismatch', len(mis), '  de ellos región boleta == región del cliente:', (mis.region == mis.region_cliente).sum(), ' anónimos:', mis.cliente_id.isna().sum())
print('mismatch excluyendo Online:', (mis.nombre != 'Tienda Online').sum())
print('Online: region boleta vs region cliente coincide:', (bb[bb.nombre == 'Tienda Online'].region == bb[bb.nombre == 'Tienda Online'].region_cliente).mean().round(3))
print('Nota La Florida: tienda 4 comuna 4 -> region_id 9 (no existe). Region en tienda (via join):', tt[tt.tienda_id == 4][['nombre', 'region']].to_dict('records'))

h('7. FECHA_ALTA vs PRIMERA COMPRA')
bi = b[b.cliente_id.notna()]
prim = bi.groupby('cliente_id').f.min()
c3 = cl.set_index('cliente_id').assign(primera=prim)
c3['dif'] = (c3.primera - c3.alta).dt.days
print('alta en 2024:', (c3.alta.dt.year == 2024).sum(), ' alta en 2025:', (c3.alta.dt.year == 2025).sum())
print('primera compra ANTES del alta:', (c3.dif < 0).sum(), ' dif min', c3.dif.min(), ' distribución dif<0:', c3[c3.dif < 0].dif.describe().round(1).to_dict())
print('alta == primera compra:', (c3.dif == 0).sum())
print('alta 2024 -> primera compra observada (todas en 2025 por cobertura de datos):', c3[c3.alta.dt.year == 2024].primera.dt.year.value_counts().to_dict())
print('dif<0 por formato fecha_alta:', c3[c3.dif < 0].fmt_alta.value_counts().to_dict(), ' total por formato:', c3.fmt_alta.value_counts().to_dict())
# ¿inversión dd/mm vs mm/dd en fecha_alta explica?
alt = cl[cl.fmt_alta == 'dd/mm/yyyy'].set_index('cliente_id').fecha_alta.map(lambda s: pd.to_datetime(s, format='%m/%d/%Y', errors='coerce'))
print('fecha_alta dd/mm con día>12 (no ambigua):', cl[cl.fmt_alta == 'dd/mm/yyyy'].fecha_alta.str[:2].astype(int).gt(12).sum(), 'de', (cl.fmt_alta == 'dd/mm/yyyy').sum())

h('8. RETENCIÓN — CIFRAS DE CONTEXTO (solo 2025, sin dups, identificados)')
b25 = b.drop_duplicates().copy(); b25 = b25[b25.f.dt.year == 2025]
ide = b25[b25.cliente_id.notna()]
ref = pd.Timestamp('2025-12-31')
last = ide.groupby('cliente_id').f.max(); first = ide.groupby('cliente_id').f.min(); nb = ide.groupby('cliente_id').size()
print('clientes 2025:', ide.cliente_id.nunique(), ' boletas identificadas 2025:', len(ide), ' anónimas 2025:', b25.cliente_id.isna().sum(), f'({b25.cliente_id.isna().mean()*100:.1f}%)')
print('clientes con 1 sola boleta en 2025:', (nb == 1).sum(), f'({(nb==1).mean()*100:.1f}%)')
rec = (ref - last).dt.days
for w in [30, 60, 90, 180]: print(f'  activos al 31-12-2025 ventana {w}d: {(rec <= w).sum()} ({(rec <= w).mean()*100:.1f}%)')
gap = ide.sort_values(['cliente_id', 'f']).groupby('cliente_id').f.diff().dt.days.dropna()
print('intercompra (días) p50/p75/p80/p90/p95:', gap.quantile([.5, .75, .8, .9, .95]).round(0).tolist())
print('% intercompras <= 30d:', round((gap <= 30).mean() * 100, 1), ' <= 90d:', round((gap <= 90).mean() * 100, 1))
# retención mensual: clientes del mes m que vuelven en m+1
cm = ide.assign(m=ide.f.dt.to_period('M')).groupby('m').cliente_id.apply(set)
rows = []
for i in range(len(cm) - 1):
    a, bnx = cm.iloc[i], cm.iloc[i + 1]
    rows.append((str(cm.index[i]), len(a), len(a & bnx), round(len(a & bnx) / len(a) * 100, 1)))
print('retención mes a mes (clientes mes m, que vuelven en m+1, %):'); [print('  ', r) for r in rows]
# nuevos vs recurrentes por mes (nuevo = primera compra observada en ese mes)
fm = first.dt.to_period('M')
nv = ide.assign(m=ide.f.dt.to_period('M')).groupby('m').cliente_id.apply(lambda s: (fm.loc[s.unique()] == s.name).sum())
act = ide.assign(m=ide.f.dt.to_period('M')).groupby('m').cliente_id.nunique()
print('clientes activos mes / nuevos (primera compra observada):'); print(pd.DataFrame({'activos': act, 'nuevos_obs': nv}).to_string())
# cohortes trimestrales
q = first.dt.to_period('Q')
ide2 = ide.assign(q=ide.f.dt.to_period('Q'), cq=ide.cliente_id.map(q))
coh = ide2.groupby(['cq', 'q']).cliente_id.nunique().unstack()
print('cohortes trimestrales (clientes únicos por trimestre):\n', coh.to_string())
print('ventas 2025 sin dups ($ nominal, líneas netas incl devoluciones):', round(d[d.boleta_id.isin(b25.boleta_id)].ml.sum()))
print('ventas 2025 H1 vs H2:', round(d[d.boleta_id.isin(b25[b25.f.dt.month <= 6].boleta_id)].ml.sum()), round(d[d.boleta_id.isin(b25[b25.f.dt.month > 6].boleta_id)].ml.sum()))

h('9. PRECIOS: precio_unitario/precio_lista por mes (señal inflación, P4)')
dl = d.merge(b.drop_duplicates()[['boleta_id', 'f']], on='boleta_id')
print(dl.groupby(dl.f.dt.to_period('M')).ratio_pl.mean().round(4).to_string())
# precio del mismo sku enero vs diciembre
pm = dl[dl.f.dt.year == 2025].groupby([dl.f.dt.month, 'sku']).pu.median().unstack(0)
print('variación mediana precio mismo SKU dic/ene -1:', round((pm[12] / pm[1] - 1).median() * 100, 2), '%  (n skus con ambos meses:', pm[[1, 12]].dropna().shape[0], ')')

h('10. PROMOCIONES — detalle')
c5 = [c for c in promo['campanas'] if c['campana_id'] == 'CAMP-2025-05'][0]
w5 = dl[dl.sku.isin(c5['skus']) & dl.f.between('2025-05-05', '2025-05-20')]
print('CAMP-2025-05 (2x1) líneas en ventana:', len(w5), ' cantidades:', w5.cantidad.value_counts().to_dict(), ' desc:', w5.desc.value_counts().to_dict())
print('ventas de SKUs lácteos campaña por quincena abr-jun:', dl[dl.sku.isin(c5['skus']) & dl.f.between('2025-04-01', '2025-06-30')].groupby(dl.f.dt.to_period('W')).cantidad.sum().to_dict())
print('SKU-9001/9007 en detalle:', d.sku.isin(['SKU-9001', 'SKU-9007']).sum())
s9 = dl[dl.sku.str.match(r'SKU-9\d{3}')]
print('SKUs 9xxx: líneas', len(s9), ' skus', s9.sku.nunique(), ' por mes', s9.f.dt.month.value_counts().sort_index().to_dict(), ' desc', s9.desc.value_counts().to_dict(), ' precio mediano', s9.pu.median())
print('descuento 10% fuera de campañas: líneas', ((dl.desc == 10)).sum(), ' por mes', dl[dl.desc == 10].f.dt.month.value_counts().sort_index().to_dict())
print('desc 25% fuera de sept:', ((dl.desc == 25) & (dl.f.dt.month != 9)).sum())
sep = dl[(dl.f.dt.month == 9) & (dl.f.dt.year == 2025)]
print('Sept: líneas con desc 25 en SKUs NO campaña:', ((sep.desc == 25) & ~sep.sku.isin(promo['campanas'][0]['skus'])).sum())
print('Sept: canal de líneas con desc 25:', sep[sep.desc == 25].merge(b[['boleta_id', 'canal']].drop_duplicates('boleta_id'), on='boleta_id').canal.value_counts().to_dict())

h('11. MAESTRO — filas especiales')
print(prod[prod.sku.isin(['sku', 'TOTAL']) | (prod.nombre.str.strip() == '') | prod.costo_unitario.map(g['fmt_monto']).isin(['OTRO', 'VACIO']) | prod.precio_lista.map(g['fmt_monto']).isin(['OTRO', 'VACIO'])].drop(columns=['costo', 'precio', 'margen_pct']).to_string())
print('activo "No":', prod[prod.activo == 'No'][['sku', 'nombre']].to_dict('records'))
print('marca != proveedor:', prod[prod.marca != prod.proveedor][['sku', 'marca', 'proveedor']].to_dict('records'))
# SKU de productos del maestro nunca vendidos
print('nunca vendidos:', sorted(set(prod.sku) - set(d.sku) - {'sku', 'TOTAL'}))

h('12. MEDIO DE PAGO EN WEB y cliente-día')
print('Web pagadas en Efectivo:', ((b.canal == 'Web') & (b.medio_id == 1)).sum())
print('App en Presencial:', ((b.canal == 'Presencial') & (b.medio_id == 4)).sum())
