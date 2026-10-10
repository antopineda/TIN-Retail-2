# -*- coding: utf-8 -*-
"""
Perfilamiento de SOLO LECTURA del set de datos Retail - grupo_2.
No modifica ningún archivo original: la SQLite se abre en modo ro y el CSV/JSON solo se leen.
Uso:  python exploracion/01_perfilamiento.py  > exploracion/salida_perfilamiento.txt
"""
import json, re, sqlite3
from pathlib import Path
import pandas as pd
import numpy as np

pd.set_option('display.width', 250); pd.set_option('display.max_columns', 50); pd.set_option('display.max_rows', 200)
BASE = Path(__file__).resolve().parent.parent / 'origen'
con = sqlite3.connect(f"file:{(BASE/'origen_pos.sqlite').as_posix()}?mode=ro", uri=True)
T = {t: pd.read_sql(f'select * from {t}', con) for t in
     ['regiones', 'comunas', 'tiendas', 'medios_pago', 'clientes', 'boletas', 'boleta_detalle']}
prod = pd.read_csv(BASE/'origen_maestro_productos.csv', sep=';', encoding='latin-1', dtype=str, keep_default_na=False)
promo = json.load(open(BASE/'origen_promociones.json', encoding='utf-8'))

def h(t): print('\n' + '=' * 10, t, '=' * 10)

# ---------- helpers de clasificación de formatos ----------
PAT_FECHA = {
    'ISO yyyy-mm-dd': r'^\d{4}-\d{2}-\d{2}$',
    'dd/mm/yyyy': r'^\d{2}/\d{2}/\d{4}$',
    'dd-mm-yy': r'^\d{2}-\d{2}-\d{2}$',
    'ISO con hora': r'^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}',
    'd-mmm-yyyy (mes en español)': r'^\d{1,2}-[a-zA-Z]{3}-\d{4}$',
}
MESES = {'ene': 1, 'feb': 2, 'mar': 3, 'abr': 4, 'may': 5, 'jun': 6, 'jul': 7, 'ago': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dic': 12}
def fmt_fecha(s):
    if s is None or (isinstance(s, float) and np.isnan(s)): return 'NULO'
    s = str(s).strip()
    for k, p in PAT_FECHA.items():
        if re.match(p, s): return k
    return 'OTRO:' + s
def parse_fecha(s):
    if s is None or (isinstance(s, float) and np.isnan(s)): return pd.NaT
    s = str(s).strip(); f = fmt_fecha(s)
    try:
        if f.startswith('ISO'): return pd.to_datetime(s[:10], format='%Y-%m-%d')
        if f == 'dd/mm/yyyy': return pd.to_datetime(s, format='%d/%m/%Y')
        if f == 'dd-mm-yy': return pd.to_datetime(s, format='%d-%m-%y')
        if f.startswith('d-mmm'):
            dd_, mm_, yy_ = s.split('-'); return pd.Timestamp(int(yy_), MESES[mm_.lower()], int(dd_))
    except Exception: return pd.NaT
    return pd.NaT

def fmt_monto(s):
    if s is None: return 'NULO'
    s = str(s)
    if s.strip() == '': return 'VACIO'
    if s != s.strip(): return 'con espacios'
    if s.startswith('$'): return 'con $'
    if re.fullmatch(r'-?\d+', s): return 'entero plano'
    if re.fullmatch(r'-?\d{1,3}(\.\d{3})+', s): return 'miles con punto'
    if re.fullmatch(r'-?\d{1,3}(\.\d{3})*,\d+', s): return 'miles punto + decimal coma'
    if re.fullmatch(r'-?\d+\.\d{1,2}', s): return 'decimal con punto'
    if re.fullmatch(r'-?\d+,\d+', s): return 'decimal con coma'
    return 'OTRO'
def parse_monto(s):
    if s is None: return np.nan
    s = str(s).strip().replace('$', '').strip()
    if s == '': return np.nan
    if re.fullmatch(r'-?\d{1,3}(\.\d{3})+', s): return float(s.replace('.', ''))
    if ',' in s: return float(s.replace('.', '').replace(',', '.'))
    try: return float(s)
    except ValueError: return np.nan

# =================== DIMENSIONES CHICAS ===================
h('REGIONES / COMUNAS / TIENDAS / MEDIOS')
for t in ['regiones', 'comunas', 'tiendas', 'medios_pago']:
    print(t, T[t].shape, 'dup exactos:', T[t].duplicated().sum())
print('comunas con region_id huérfano:', T['comunas'][~T['comunas'].region_id.isin(T['regiones'].region_id)].to_dict('records'))
print('tiendas con comuna_id huérfano:', T['tiendas'][~T['tiendas'].comuna_id.isin(T['comunas'].comuna_id)].to_dict('records'))
print('regiones sin tiendas:', set(T['regiones'].region_id) - set(T['comunas'][T['comunas'].comuna_id.isin(T['tiendas'].comuna_id)].region_id))

# =================== CLIENTES ===================
h('CLIENTES')
cl = T['clientes'].copy()
print(cl.dtypes.to_string()); print('filas', len(cl))
print('nulos %:\n', (cl.isna().mean() * 100).round(2).to_string())
print('vacíos (string ""):', {c: int((cl[c].astype(str).str.strip() == '').sum()) for c in cl.columns if cl[c].dtype == object})
print('cliente_id únicos:', cl.cliente_id.nunique(), ' dup exactos:', cl.duplicated().sum(), ' dup cliente_id:', cl.cliente_id.duplicated().sum())
print('rango cliente_id', cl.cliente_id.min(), cl.cliente_id.max())
# RUT
rut = cl.rut.astype(str)
print('RUT con espacios extremos:', (rut != rut.str.strip()).sum())
print('RUT con puntos:', rut.str.contains(r'\.').sum(), ' sin guion:', (~rut.str.contains('-')).sum(), ' DV K/k:', rut.str.strip().str[-1].isin(['K', 'k']).sum())
print('RUT con espacios internos:', rut.str.strip().str.contains(' ').sum())
rn = rut.str.replace(r'\s', '', regex=True).str.replace('.', '', regex=False).str.replace('-', '', regex=False).str.upper()
def dv_ok(r):
    if not re.fullmatch(r'\d{6,8}[\dK]', r): return None
    cuerpo, dv = r[:-1], r[-1]; s, m = 0, 2
    for d in reversed(cuerpo): s += int(d) * m; m = 2 if m == 7 else m + 1
    esp = 11 - s % 11; esp = '0' if esp == 11 else 'K' if esp == 10 else str(esp)
    return esp == dv
v = rn.map(dv_ok)
print('RUT formato inválido:', v.isna().sum(), ' DV correcto:', (v == True).sum(), ' DV incorrecto:', (v == False).sum())
print('RUT normalizado duplicado (filas):', rn.duplicated(keep=False).sum(), ' grupos:', rn[rn.duplicated(keep=False)].nunique())
print('ejemplos RUT formato inválido:', rut[v.isna()].head(15).tolist())
print('ejemplos RUT DV incorrecto:', rut[v == False].head(10).tolist())
# nombres
print('nombres únicos:', cl.nombre.nunique())
pref = cl.nombre.astype(str).str.extract(r'^(Sr\.|Sra\.|Comercial|Distribuidora|Inversiones|Sociedad|Almacén|Minimarket)?')[0].fillna('(otro)')
print('prefijo nombre:\n', pref.value_counts().to_string())
print('ejemplos otros:', cl.nombre[pref == '(otro)'].head(10).tolist())
# fecha_alta
cl['fmt_alta'] = cl.fecha_alta.map(fmt_fecha); print('formatos fecha_alta:\n', cl.fmt_alta.value_counts().to_string())
cl['alta'] = cl.fecha_alta.map(parse_fecha)
print('fecha_alta rango:', cl.alta.min(), cl.alta.max(), ' no parseables:', cl.alta.isna().sum() - cl.fecha_alta.isna().sum())
print('fecha_alta por mes:\n', cl.alta.dt.to_period('M').value_counts().sort_index().to_string())
print('segmento:\n', cl.segmento.value_counts(dropna=False).to_string())
print('comuna_id:\n', cl.comuna_id.value_counts(dropna=False).sort_index().to_string())
print('comuna_id huérfana:', (~cl.comuna_id.isin(T['comunas'].comuna_id) & cl.comuna_id.notna()).sum())

# =================== BOLETAS ===================
h('BOLETAS')
b = T['boletas'].copy()
print('filas', len(b), ' boleta_id únicos', b.boleta_id.nunique(), ' dup exactos', b.duplicated().sum())
print('nulos %:\n', (b.isna().mean() * 100).round(2).to_string())
b['fmt'] = b.fecha.map(fmt_fecha); print('formatos fecha:\n', b.fmt.value_counts().to_string())
b['f'] = b.fecha.map(parse_fecha)
print('fecha rango', b.f.min(), b.f.max(), ' no parseables', b.f.isna().sum())
print('fechas > 2025-12-31:', (b.f > '2025-12-31').sum(), ' < 2025-01-01:', (b.f < '2025-01-01').sum())
# ambigüedad dd-mm-yy vs yy-mm-dd: ¿mes coincide con columna mes?
b['mes_n'] = pd.to_numeric(b.mes, errors='coerce')
print('mes texto no numérico:', b.mes_n.isna().sum())
b['mes_ok'] = b.f.dt.month == b.mes_n
print('coincide mes(fecha)==col mes, por formato:\n', b.groupby('fmt').mes_ok.mean().round(4).to_string())
# alternativa: dd/mm/yyyy podría ser mm/dd/yyyy
alt = b[b.fmt == 'dd/mm/yyyy'].fecha.map(lambda s: pd.to_datetime(s, format='%m/%d/%Y', errors='coerce'))
print('dd/mm/yyyy interpretado como mm/dd: coincide mes', (alt.dt.month == b.loc[alt.index, 'mes_n']).mean().round(4))
print('boletas por mes (fecha parseada):\n', b.f.dt.to_period('M').value_counts().sort_index().to_string())
# región redundante vs tienda
tt = T['tiendas'].merge(T['comunas'], on='comuna_id', how='left').merge(T['regiones'], on='region_id', how='left')
bb = b.merge(tt[['tienda_id', 'nombre', 'formato', 'region']].rename(columns={'region': 'region_tienda'}), on='tienda_id', how='left')
print('region boleta != region de la tienda:', (bb.region != bb.region_tienda).sum())
print(pd.crosstab(bb.nombre, bb.region).to_string())
print('canal x tienda:\n', pd.crosstab(bb.nombre, bb.canal).to_string())
print('canal Web por mes:\n', pd.crosstab(bb.f.dt.to_period('M'), bb.canal).to_string())
print('medio x canal:\n', pd.crosstab(bb.medio_id, bb.canal).to_string())
print('cliente_id nulo (anónimo):', b.cliente_id.isna().sum(), f'({b.cliente_id.isna().mean()*100:.2f}%)')
print('anónimo por tienda %:\n', (bb.groupby('nombre').cliente_id.apply(lambda s: s.isna().mean() * 100)).round(1).to_string())
print('cliente_id huérfano (no está en clientes):', (b.cliente_id.notna() & ~b.cliente_id.isin(cl.cliente_id)).sum())
print('clientes sin ninguna boleta:', (~cl.cliente_id.isin(b.cliente_id)).sum())
print('tienda_id huérfana:', (~b.tienda_id.isin(T['tiendas'].tienda_id)).sum(), ' medio_id huérfano:', (~b.medio_id.isin(T['medios_pago'].medio_id)).sum())
# duplicados probables: mismo cliente, misma fecha, misma tienda
k = ['cliente_id', 'f', 'tienda_id', 'canal', 'medio_id']
dp = b[b.cliente_id.notna()].duplicated(subset=k, keep=False)
print('dup probables boleta (mismo cliente+fecha+tienda+canal+medio):', dp.sum())
# gaps en boleta_id
ids = set(b.boleta_id); print('ids faltantes en rango:', (b.boleta_id.max() - b.boleta_id.min() + 1) - len(ids))
# boletas sin detalle
d = T['boleta_detalle'].copy()
print('boletas sin detalle:', (~b.boleta_id.isin(d.boleta_id)).sum(), ' detalle sin boleta:', (~d.boleta_id.isin(b.boleta_id)).sum(),
      ' (filas detalle huérfanas:', (~d.boleta_id.isin(b.boleta_id)).sum(), ', boletas huérfanas distintas:', d[~d.boleta_id.isin(b.boleta_id)].boleta_id.nunique(), ')')
# boletas antes de fecha_alta del cliente
ba = b.merge(cl[['cliente_id', 'alta']], on='cliente_id', how='left')
ba = ba[ba.cliente_id.notna()]
print('boletas con fecha < fecha_alta del cliente:', (ba.f < ba.alta).sum(), ' clientes afectados:', ba[ba.f < ba.alta].cliente_id.nunique())
prim = ba.groupby('cliente_id').agg(primera=('f', 'min'), alta=('alta', 'first'))
dd = (prim.primera - prim.alta).dt.days
print('diferencia primera compra - fecha_alta (días): ==0:', (dd == 0).sum(), ' >0:', (dd > 0).sum(), ' <0:', (dd < 0).sum(), ' NaN:', dd.isna().sum())
print(dd.describe().to_string())

# =================== DETALLE ===================
h('BOLETA_DETALLE')
print('filas', len(d), ' dup exactos', d.duplicated().sum(), ' dup (boleta_id,linea)', d.duplicated(['boleta_id', 'linea']).sum())
print('dup (boleta,linea) con contenido distinto:', d[d.duplicated(['boleta_id', 'linea'], keep=False)].drop_duplicates().duplicated(['boleta_id', 'linea']).sum())
print('dup (boleta_id, sku) en líneas distintas:', d.duplicated(['boleta_id', 'sku'], keep=False).sum())
print('nulos %:\n', (d.isna().mean() * 100).round(2).to_string())
print(d.dtypes.to_string())
for c in ['precio_unitario', 'monto_linea', 'descuento']:
    print(f'formatos {c}:\n', d[c].map(fmt_monto).value_counts().to_string())
print('descuento valores:\n', d.descuento.value_counts(dropna=False).to_string())
d['pu'] = d.precio_unitario.map(parse_monto); d['ml'] = d.monto_linea.map(parse_monto)
def parse_desc(x):
    # '10', '10%' -> 10 ; '0,10' -> fracción -> 10
    x = str(x).strip()
    if x in ('', 'None', 'nan'): return np.nan
    if x.endswith('%'): return float(x[:-1])
    if ',' in x: return float(x.replace(',', '.')) * 100
    return float(x)
d['desc'] = d.descuento.map(parse_desc)
print('descuento normalizado (%):', d.desc.value_counts(dropna=False).to_dict())
print('monto_linea formato OTRO:', d.monto_linea[d.monto_linea.map(fmt_monto) == 'OTRO'].tolist())
print('cantidad:\n', d.cantidad.describe().to_string()); print('cantidad value_counts:\n', d.cantidad.value_counts().sort_index().to_string())
print('precio_unitario:\n', d.pu.describe().to_string()); print('monto_linea:\n', d.ml.describe().to_string())
print('pu<=0:', (d.pu <= 0).sum(), ' ml<0:', (d.ml < 0).sum(), ' ml==0:', (d.ml == 0).sum(), ' cantidad<=0:', (d.cantidad <= 0).sum())
d['ml_calc'] = d.cantidad * d.pu * (1 - d.desc.fillna(0) / 100)
d['dif'] = d.ml - d.ml_calc
print('|monto_linea - cant*pu*(1-desc)| > 2 pesos:', (d.dif.abs() > 2).sum())
print(d[d.dif.abs() > 2].head(15).to_string())
print('ratio ml/ml_calc para discrepantes:\n', (d.ml / d.ml_calc)[d.dif.abs() > 2].describe().to_string())
# outliers
q1, q3 = d.ml.quantile([.25, .75]); iqr = q3 - q1
print('monto_linea outliers IQR (>q3+3iqr):', (d.ml > q3 + 3 * iqr).sum(), ' top:', d.ml.nlargest(8).tolist())
print('precio_unitario top:', d.pu.nlargest(8).tolist(), ' bottom:', d.pu.nsmallest(8).tolist())
# SKU
print('SKU distintos en detalle:', d.sku.nunique(), ' formato raro:', (~d.sku.astype(str).str.fullmatch(r'SKU-\d{4}')).sum())
print('SKU raros:', d.sku[~d.sku.astype(str).str.fullmatch(r'SKU-\d{4}')].value_counts().head(10).to_dict())
# líneas por boleta
lpb = d.groupby('boleta_id').size(); print('líneas por boleta:\n', lpb.describe().to_string())

# =================== PRODUCTOS ===================
h('MAESTRO PRODUCTOS (CSV)')
print('filas', len(prod), ' cols', list(prod.columns))
print('dup exactos', prod.duplicated().sum(), ' sku únicos', prod.sku.nunique(), ' filas con sku repetido', prod.sku.duplicated(keep=False).sum())
print('vacíos por col:', {c: int((prod[c].str.strip() == '').sum()) for c in prod.columns})
print('categoria:\n', prod.categoria.value_counts().to_string())
print('subcategoria:\n', prod.subcategoria.value_counts().to_string())
print('activo:\n', prod.activo.value_counts().to_string())
print('nombre con espacios extremos:', (prod.nombre != prod.nombre.str.strip()).sum(), ' nombre en MAYÚSCULAS:', (prod.nombre == prod.nombre.str.upper()).sum())
for c in ['costo_unitario', 'precio_lista']:
    print(f'formatos {c}:\n', prod[c].map(fmt_monto).value_counts().to_string())
prod['costo'] = prod.costo_unitario.map(parse_monto); prod['precio'] = prod.precio_lista.map(parse_monto)
print(prod[['costo', 'precio']].describe().to_string())
print('costo >= precio:', (prod.costo >= prod.precio).sum(), ' costo<=0:', (prod.costo <= 0).sum(), ' precio<=0:', (prod.precio <= 0).sum())
print(prod[(prod.costo >= prod.precio) | (prod.costo <= 0) | (prod.precio <= 0)].to_string())
prod['margen_pct'] = 1 - prod.costo / prod.precio; print('margen % lista:\n', prod.margen_pct.describe().round(3).to_string())
dup = prod[prod.sku.duplicated(keep=False)].sort_values('sku'); print('SKU duplicados:\n', dup.to_string())
print('SKU formato raro:', prod.sku[~prod.sku.str.fullmatch(r'SKU-\d{4}')].tolist())
print('marca/proveedor distintos:', prod.marca.nunique(), prod.proveedor.nunique(), ' marca!=proveedor:', (prod.marca != prod.proveedor).sum())
# nombre normalizado repetido con SKU distinto
nn = prod.nombre.str.strip().str.lower()
g = prod.assign(nn=nn).groupby('nn').sku.nunique(); print('nombres normalizados con >1 SKU:', (g > 1).sum(), g[g > 1].head(10).to_dict())
# integración detalle-producto
print('SKU en detalle que no están en maestro:', sorted(set(d.sku) - set(prod.sku)), ' líneas afectadas:', (~d.sku.isin(prod.sku)).sum())
print('SKU del maestro nunca vendidos:', len(set(prod.sku) - set(d.sku)))
# precio vendido vs precio lista
pm = prod.drop_duplicates('sku', keep='first').set_index('sku').precio
d['plista'] = d.sku.map(pm); d['ratio_pl'] = d.pu / d.plista
print('precio_unitario / precio_lista:\n', d.ratio_pl.describe().round(3).to_string())
print('ratio fuera [0.5, 2]:', ((d.ratio_pl < 0.5) | (d.ratio_pl > 2)).sum())

# =================== PROMOCIONES ===================
h('PROMOCIONES (JSON)')
for c in promo['campanas']:
    print(c['campana_id'], c['nombre'], c['tipo'], c['fecha_ini'], c['fecha_fin'], repr(c['descuento_pct']), c['canales'], len(c['skus']))
    print('  skus no en maestro:', [s for s in c['skus'] if s not in set(prod.sku)])
print('canales en boletas:', b.canal.unique().tolist())
# ventas de skus de campaña dentro/fuera de ventana, y descuento aplicado
dl = d.merge(b[['boleta_id', 'f', 'canal', 'cliente_id']], on='boleta_id', how='left')
for c in promo['campanas']:
    ini, fin = pd.Timestamp(c['fecha_ini'][:10]), pd.Timestamp(c['fecha_fin'][:10])
    m = dl.sku.isin(c['skus'])
    win = m & dl.f.between(ini, fin)
    print(c['campana_id'], 'líneas skus campaña total:', m.sum(), ' dentro ventana:', win.sum())
    print('  descuento aplicado dentro ventana:', dl[win].desc.value_counts().to_dict())
    print('  descuento aplicado fuera ventana (mismos skus):', dl[m & ~win].desc.value_counts().head(8).to_dict())
    print('  líneas por mes skus campaña:', dl[m].f.dt.month.value_counts().sort_index().to_dict())
print('descuento por mes (media %):\n', dl.groupby(dl.f.dt.month).desc.mean().round(2).to_string())
print('descuento != 0 por mes (n):\n', dl[dl.desc > 0].groupby(dl.f.dt.month).size().to_string())

# =================== MÉTRICAS DE CONTEXTO (para P1) ===================
h('CONTEXTO RETENCIÓN')
ven = d.groupby('boleta_id').ml.sum()
b2 = b.assign(total=b.boleta_id.map(ven))
print('venta total (suma monto_linea, $ nominal):', round(b2.total.sum()))
print('venta por mes:\n', b2.groupby(b2.f.dt.to_period('M')).total.sum().round(0).to_string())
ide = b2[b2.cliente_id.notna()]
print('% venta identificada:', round(ide.total.sum() / b2.total.sum() * 100, 2))
print('clientes con compra:', ide.cliente_id.nunique())
fq = ide.groupby('cliente_id').size(); print('boletas por cliente:\n', fq.describe().to_string()); print('clientes con 1 sola boleta:', (fq == 1).sum())
ide = ide.sort_values(['cliente_id', 'f'])
gap = ide.groupby('cliente_id').f.diff().dt.days.dropna()
print('días entre compras sucesivas:\n', gap.describe(percentiles=[.25, .5, .75, .8, .9, .95]).round(1).to_string())
print('gaps == 0 (misma fecha):', (gap == 0).sum())
last = ide.groupby('cliente_id').f.max(); ref = b.f.max()
rec = (ref - last).dt.days; print('recencia al', ref.date(), ':\n', rec.describe(percentiles=[.25, .5, .75, .9]).round(1).to_string())
for w in [30, 60, 90, 180]: print(f'  activos ventana {w}d:', (rec <= w).sum())
fp = ide.groupby('cliente_id').f.min(); print('primera compra por trimestre (cohorte):\n', fp.dt.to_period('Q').value_counts().sort_index().to_string())
print('segmento de clientes compradores:\n', cl[cl.cliente_id.isin(ide.cliente_id)].segmento.value_counts(dropna=False).to_string())
# tarjeta compartida: mismo cliente compra en regiones distintas
mr = bb[bb.cliente_id.notna()].groupby('cliente_id').region.nunique(); print('clientes que compran en >1 región:', (mr > 1).sum())
mt = bb[bb.cliente_id.notna() & (bb.canal == 'Presencial')].groupby('cliente_id').tienda_id.nunique(); print('clientes en >1 tienda física:', (mt > 1).sum())
# boletas por cliente por día
bpd = ide.groupby(['cliente_id', 'f']).size(); print('cliente-día con >1 boleta:', (bpd > 1).sum())
