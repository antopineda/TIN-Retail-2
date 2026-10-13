# -*- coding: utf-8 -*-
"""
PLATA: datos limpios, tipados e integrados, con flags de calidad.
Principio: marcar antes que borrar. Solo se eliminan duplicados exactos y filas basura del CSV.
Cada regla (R01..R27, ver diagnóstico) queda registrada en el log de calidad con su conteo.
"""
import json
import sqlite3

import numpy as np
import pandas as pd

import config
import limpieza as L


def _leer_pos():
    ruta = (config.BRONCE / 'origen_pos.sqlite').as_posix()
    with sqlite3.connect(f'file:{ruta}?mode=ro', uri=True) as con:
        return {t: pd.read_sql(f'select * from "{t}"', con) for t in config.TABLAS_POS}

# ----------------------------------------------------------------- geografía y tiendas
def _geografia(pos, log):
    reg, com = pos['regiones'].copy(), pos['comunas'].copy()
    huerf = ~com.region_id.isin(reg.region_id)
    for comuna_id, region_ok in config.CORRECCION_REGION_COMUNA.items():
        com.loc[(com.comuna_id == comuna_id) & huerf, 'region_id'] = region_ok
    log.registrar('R06', 'comunas', 'region_id', 'region_id inexistente (La Florida -> 9)',
                  'corregido según config.CORRECCION_REGION_COMUNA', huerf.sum())
    geo = com.merge(reg, on='region_id', how='left')
    geo['macrozona'] = geo.region.map(config.MACROZONA_POR_REGION)
    return geo


def _tiendas(pos, geo, log):
    t = pos['tiendas'].copy()
    cambia = t.formato != t.formato.map(config.FORMATO_TIENDA)
    t['formato'] = t.formato.map(config.FORMATO_TIENDA).fillna(t.formato)
    log.registrar('R06b', 'tiendas', 'formato', 'formato sin tilde ("Hiper")', 'normalizado a "Híper"', cambia.sum())
    t['es_online'] = (t.tienda_id == config.TIENDA_ONLINE_ID) | (t.formato == 'Online')
    t = t.merge(geo, on='comuna_id', how='left')
    t.loc[t.es_online, 'macrozona'] = config.MACROZONA_ONLINE
    log.registrar('R06c', 'tiendas', 'macrozona', 'Tienda Online registrada en Providencia pero vende a toda la cadena',
                  f'macrozona = "{config.MACROZONA_ONLINE}" (S08)', t.es_online.sum())
    return t

# ----------------------------------------------------------------- clientes
def _clientes(pos, log):
    c = pos['clientes'].copy()
    c['rut_normalizado'] = c.rut.map(L.normalizar_rut)
    c['flag_rut_invalido'] = ~c.rut_normalizado.map(L.rut_valido)
    reformateados = (c.rut.astype(str) != c.rut_normalizado.astype(str)).sum()
    log.registrar('R17', 'clientes', 'rut', 'formatos mixtos (puntos, espacios, sin guion)', 'normalizado a 12345678-K', reformateados)
    log.registrar('R17b', 'clientes', 'rut', 'dígito verificador inválido', 'flag_rut_invalido (se conserva)', c.flag_rut_invalido.sum())
    log.registrar('R17c', 'clientes', 'rut', 'RUT duplicado tras normalizar', 'revisión (no se fusiona)', c.rut_normalizado.duplicated(keep=False).sum())
    c['clasificacion_nombre'] = c.nombre.map(L.clasificacion_nombre)
    log.registrar('R18', 'clientes', 'nombre', 'nombre sugiere persona/hogar o negocio (no es campo de la empresa)',
                  f'clasificacion_nombre del equipo: {c.clasificacion_nombre.value_counts().to_dict()}', (c.clasificacion_nombre == 'Negocio').sum())
    c['formato_fecha_alta'] = c.fecha_alta.map(L.formato_fecha)
    c['fecha_alta'] = c.fecha_alta.map(L.parse_fecha)
    log.registrar('R19', 'clientes', 'fecha_alta', '2 formatos de fecha', 'parseado a fecha ISO', (c.formato_fecha_alta != 'iso').sum())
    log.registrar('R19b', 'clientes', 'fecha_alta', 'fecha no parseable', 'queda nula', c.fecha_alta.isna().sum())
    c['segmento'] = c.segmento.astype(str).str.strip()
    c['es_cliente_previo_2025'] = c.fecha_alta < config.PERIODO_INI
    return c[['cliente_id', 'rut_normalizado', 'flag_rut_invalido', 'nombre', 'clasificacion_nombre', 'fecha_alta',
              'es_cliente_previo_2025', 'comuna_id', 'segmento']]

# ----------------------------------------------------------------- boletas
def _boletas(pos, tiendas, clientes, log):
    b = pos['boletas'].copy()
    n0 = len(b)
    b = b.drop_duplicates()
    log.registrar('R01', 'boletas', '*', 'filas duplicadas exactas', 'eliminadas (se conserva 1)', n0 - len(b))
    dup_id = b.boleta_id.duplicated()
    log.registrar('R01b', 'boletas', 'boleta_id', 'boleta_id repetido con contenido distinto', 'se conserva la primera', dup_id.sum())
    b = b[~dup_id].copy()

    b['formato_fecha_origen'] = b.fecha.map(L.formato_fecha)
    b['fecha'] = b.fecha.map(L.parse_fecha)
    log.registrar('R02', 'boletas', 'fecha', '4 formatos de fecha', 'parseado a fecha ISO', (b.formato_fecha_origen != 'iso').sum())
    b['flag_fecha_invalida'] = b.fecha.isna()
    log.registrar('R02b', 'boletas', 'fecha', 'fecha no parseable', 'flag_fecha_invalida', b.flag_fecha_invalida.sum())
    b['flag_fuera_periodo'] = b.flag_fecha_invalida | ~b.fecha.between(config.PERIODO_INI, config.PERIODO_FIN)
    log.registrar('R03', 'boletas', 'fecha', 'fecha fuera de 2025', 'flag_fuera_periodo (fuera de métricas, supuesto S01)', b.flag_fuera_periodo.sum())

    b['flag_mes_inconsistente'] = pd.to_numeric(b.mes, errors='coerce') != b.fecha.dt.month
    log.registrar('R04', 'boletas', 'mes', 'no coincide con el mes de la fecha', 'columna descartada; mes se deriva de fecha', b.flag_mes_inconsistente.sum())
    reg_tienda = b.tienda_id.map(tiendas.set_index('tienda_id').region)
    b['flag_region_inconsistente'] = b.region != reg_tienda
    log.registrar('R05', 'boletas', 'region', 'no coincide con la región de la tienda', 'columna descartada; región se deriva de la tienda', b.flag_region_inconsistente.sum())

    b['cliente_id'] = b.cliente_id.astype('Int64')
    huerf = b.cliente_id.notna() & ~b.cliente_id.isin(clientes.cliente_id)
    b.loc[huerf, 'cliente_id'] = pd.NA
    log.registrar('R07b', 'boletas', 'cliente_id', 'cliente inexistente en clientes', 'tratado como anónimo', huerf.sum())
    b['es_identificada'] = b.cliente_id.notna()
    log.registrar('R07', 'boletas', 'cliente_id', 'boleta anónima (nulo)', 'cliente_key = -1 en oro', (~b.es_identificada).sum())
    b['canal'] = b.canal.astype(str).str.strip()
    for col, ref, key in [('tienda_id', tiendas, 'tienda_id'), ('medio_id', pos['medios_pago'], 'medio_id')]:
        log.registrar('R07c', 'boletas', col, 'llave foránea huérfana', 'revisión', (~b[col].isin(ref[key])).sum())
    return b[['boleta_id', 'fecha', 'tienda_id', 'cliente_id', 'canal', 'medio_id', 'es_identificada',
              'flag_fuera_periodo', 'flag_fecha_invalida', 'flag_mes_inconsistente', 'flag_region_inconsistente',
              'formato_fecha_origen']].sort_values('boleta_id').reset_index(drop=True)

# ----------------------------------------------------------------- productos
def _productos(log):
    crudo = (config.BRONCE / 'origen_maestro_productos.csv').read_bytes()
    no_utf8 = 0
    for linea in crudo.split(b'\n'):
        try:
            linea.decode('utf-8')
        except UnicodeDecodeError:
            no_utf8 += 1
    p = pd.read_csv(config.BRONCE / 'origen_maestro_productos.csv', sep=';', encoding=config.ENCODING_MAESTRO,
                    dtype=str, keep_default_na=False)
    log.registrar('R20', 'productos', '(archivo)', f'codificación {config.ENCODING_MAESTRO}, no UTF-8', 'leído como Latin-1 y escrito en UTF-8', no_utf8)
    basura = ~p.sku.str.strip().str.fullmatch(r'SKU-\d{4}')
    log.registrar('R21', 'productos', 'sku', f'filas que no son productos: {p.sku[basura].tolist()}', 'eliminadas', basura.sum())
    p = p[~basura].copy()
    p['sku'] = p.sku.str.strip()

    nombre_norm = p.nombre.map(L.nombre_producto)
    log.registrar('R25b', 'productos', 'nombre', 'espacios extremos / MAYÚSCULAS', 'strip y formato título', (nombre_norm != p.nombre).sum())
    p['nombre'] = nombre_norm
    p['categoria_origen'] = p.categoria
    p['categoria'] = p.categoria.map(L.categoria_canonica)
    log.registrar('R23', 'productos', 'categoria', f'{p.categoria_origen.nunique()} grafías distintas',
                  f'mapeadas a {p.categoria.nunique()} categorías canónicas', (p.categoria != p.categoria_origen).sum())
    log.registrar('R23b', 'productos', 'categoria', 'grafía sin mapeo', 'queda nula (agregar a config)', p.categoria.isna().sum())
    moda = p.groupby('subcategoria').categoria.agg(lambda s: s.mode().iat[0] if s.notna().any() else None)
    conflicto = p.categoria != p.subcategoria.map(moda)
    log.registrar('R23c', 'productos', 'categoria', 'categoría distinta a la del resto de su subcategoría', 'revisión', conflicto.sum())

    for col_o, col in [('costo_unitario', 'costo_unitario'), ('precio_lista', 'precio_lista')]:
        crudo_col = p[col_o]
        p[col] = crudo_col.map(L.parse_monto)
        log.registrar('R24', 'productos', col_o, 'formatos mixtos ($, punto de miles, coma decimal, N/A)', 'convertido a número',
                      (~crudo_col.str.fullmatch(r'\d+')).sum())
    p['flag_costo_invalido'] = p.costo_unitario.isna() | (p.costo_unitario <= 0)
    log.registrar('R24b', 'productos', 'costo_unitario', 'costo no numérico (N/A)', 'nulo + flag_costo_invalido', p.flag_costo_invalido.sum())
    p['activo'] = p.activo.map(L.parse_activo)
    log.registrar('R25', 'productos', 'activo', 'variantes 1/Sí/si/SI/No/vacío', 'convertido a booleano', p.activo.notna().sum())

    p['_prioridad'] = p.activo.map({True: 0, False: 2}).fillna(1)     # activo primero, luego sin dato, luego inactivo
    p = p.sort_values(['sku', '_prioridad'], kind='stable')
    dup = p.sku.duplicated()
    log.registrar('R22', 'productos', 'sku', f'SKU duplicado: {p.sku[dup].tolist()}', 'se conserva la fila activa', dup.sum())
    p = p[~dup]
    return p[['sku', 'nombre', 'categoria', 'subcategoria', 'marca', 'proveedor', 'costo_unitario', 'precio_lista',
              'activo', 'flag_costo_invalido', 'categoria_origen']].reset_index(drop=True)

# ----------------------------------------------------------------- campañas e IPC
def _campanas(productos, log):
    raw = json.loads((config.BRONCE / 'origen_promociones.json').read_text(encoding='utf-8'))
    filas, skus = [], []
    for c in raw['campanas']:
        filas.append({'campana_id': c['campana_id'], 'nombre': c['nombre'], 'tipo': c['tipo'],
                      'fecha_ini': pd.Timestamp(c['fecha_ini'][:10]), 'fecha_fin': pd.Timestamp(c['fecha_fin'][:10]),
                      'descuento_pct': L.parse_descuento(c['descuento_pct']), 'descuento_pct_origen': str(c['descuento_pct']),
                      'canales': '|'.join(c['canales'])})
        skus += [{'campana_id': c['campana_id'], 'sku': s} for s in c['skus']]
    camp, cs = pd.DataFrame(filas), pd.DataFrame(skus)
    log.registrar('R26', 'campanas', 'descuento_pct', 'tipos mixtos ("25%" texto / 50 número)', 'convertido a porcentaje numérico',
                  (~camp.descuento_pct_origen.str.fullmatch(r'\d+')).sum())
    cs['flag_sku_sin_maestro'] = ~cs.sku.isin(productos.sku)
    log.registrar('R26b', 'campana_sku', 'sku', 'SKU de campaña sin maestro', 'flag_sku_sin_maestro', cs.flag_sku_sin_maestro.sum())
    return camp, cs


def _ipc(log):
    raw = json.loads((config.BRONCE / 'ipc_2025_raw.json').read_text(encoding='utf-8'))
    serie = pd.DataFrame([{'anio_mes': x['fecha'][:7], 'ipc_var_pct': float(x['valor'])} for x in raw['serie']])
    serie = serie.drop_duplicates('anio_mes').sort_values('anio_mes')
    base = pd.DataFrame([{'anio_mes': config.IPC_BASE, 'ipc_var_pct': np.nan}])
    ipc = pd.concat([base, serie], ignore_index=True)
    ipc['ipc_indice'] = 100 * (1 + ipc.ipc_var_pct.fillna(0) / 100).cumprod()
    ipc['factor_a_pesos_base'] = 100 / ipc.ipc_indice
    log.registrar('R27', 'ipc', 'valor', 'la API entrega variación % mensual, no índice',
                  f'índice encadenado base {config.IPC_BASE}=100 ({raw.get("_metadatos_cadena", {}).get("origen", "?")})', len(serie))
    return ipc

# ----------------------------------------------------------------- detalle
def _detalle(pos, boletas, productos, camp, cs, log):
    d = pos['boleta_detalle'].copy()
    d['_orden'] = np.arange(len(d))
    huerf = ~d.boleta_id.isin(boletas.boleta_id)
    log.registrar('R08c', 'boleta_detalle', 'boleta_id', 'línea sin boleta', 'revisión', huerf.sum())

    d['precio_unitario_n'] = d.precio_unitario.map(L.parse_monto)
    d['monto_linea_n'] = d.monto_linea.map(L.parse_monto)
    d['descuento_pct'] = d.descuento.map(L.parse_descuento)
    log.registrar('R09', 'boleta_detalle', 'precio_unitario', 'texto con punto de miles', 'convertido a entero', d.precio_unitario.astype(str).str.contains(r'\.').sum())
    log.registrar('R10', 'boleta_detalle', 'monto_linea', 'texto con punto de miles', 'convertido a entero', d.monto_linea.astype(str).str.contains(r'\.').sum())
    log.registrar('R10b', 'boleta_detalle', 'monto_linea', 'valores mal formados ("-.905")', 'reconstruidos (-905)', d.monto_linea.astype(str).str.fullmatch(r'-?\.\d{3}').sum())
    log.registrar('R11', 'boleta_detalle', 'descuento', '7 notaciones (10, 10%, 0,10 ...)', 'convertido a % entero', (~d.descuento.astype(str).str.fullmatch(r'\d+')).sum())
    d['flag_descuento_fuera_dominio'] = ~d.descuento_pct.isin(config.DESCUENTOS_VALIDOS)
    log.registrar('R11b', 'boleta_detalle', 'descuento', f'fuera de {sorted(config.DESCUENTOS_VALIDOS)}', 'flag', d.flag_descuento_fuera_dominio.sum())

    d = d.sort_values(['boleta_id', 'linea', '_orden'])
    d['flag_linea_repetida_origen'] = d.duplicated(['boleta_id', 'linea'], keep=False)
    d['flag_linea_posible_duplicada'] = d.duplicated(['boleta_id', 'linea', 'sku', 'cantidad', 'precio_unitario_n', 'descuento_pct', 'monto_linea_n'], keep=False)
    d['linea_seq'] = d.groupby('boleta_id').cumcount() + 1
    log.registrar('R08', 'boleta_detalle', 'linea', '(boleta_id, linea) no es único', 'renumerado en linea_seq; no se borra', d.flag_linea_repetida_origen.sum())
    log.registrar('R08b', 'boleta_detalle', 'linea', 'misma boleta, línea, SKU y monto', 'flag_linea_posible_duplicada; se conserva', d.flag_linea_posible_duplicada.sum())

    d['monto_calculado'] = (d.cantidad * d.precio_unitario_n * (1 - d.descuento_pct.fillna(0) / 100)).round(2)
    d['dif_monto'] = d.monto_linea_n - d.monto_calculado
    d['flag_monto_inconsistente'] = d.dif_monto.abs() > config.TOLERANCIA_MONTO
    log.registrar('R12', 'boleta_detalle', 'monto_linea', 'no cuadra con cantidad × precio × (1 − desc)',
                  'se usa el registrado (S02); el calculado queda como control', d.flag_monto_inconsistente.sum())
    d['es_devolucion'] = d.cantidad < 0
    log.registrar('R13', 'boleta_detalle', 'cantidad', 'cantidad negativa', 'es_devolucion (resta de la venta, S04)', d.es_devolucion.sum())
    d['flag_volumen_mayorista'] = d.cantidad.abs() >= config.CANTIDAD_MAYORISTA
    log.registrar('R14', 'boleta_detalle', 'cantidad', f'cantidad >= {config.CANTIDAD_MAYORISTA}', 'flag; se conserva', d.flag_volumen_mayorista.sum())
    d['flag_sku_sin_maestro'] = ~d.sku.isin(productos.sku)
    log.registrar('R15', 'boleta_detalle', 'sku', f'SKU sin maestro ({d.sku[d.flag_sku_sin_maestro].nunique()} SKU distintos)',
                  'se conserva como "Sin maestro"', d.flag_sku_sin_maestro.sum())

    # campañas: SKU en campaña + fecha en ventana + canal habilitado
    d = d.merge(boletas[['boleta_id', 'fecha', 'canal', 'es_identificada']], on='boleta_id', how='left')
    d['campana_id'] = None
    for _, c in camp.iterrows():
        skus = set(cs.loc[cs.campana_id == c.campana_id, 'sku'])
        m = d.sku.isin(skus) & d.fecha.between(c.fecha_ini, c.fecha_fin) & d.canal.isin(c.canales.split('|')) & d.campana_id.isna()
        d.loc[m, 'campana_id'] = c.campana_id
    pct_camp = d.campana_id.map(camp.set_index('campana_id').descuento_pct)
    d['tipo_descuento'] = np.select(
        [d.descuento_pct == 0, d.campana_id.notna() & (d.descuento_pct == pct_camp), (d.descuento_pct == 10) & d.es_identificada],
        ['sin_descuento', 'campana', 'beneficio_tarjeta'], 'no_explicado')
    log.registrar('R16', 'boleta_detalle', 'descuento', f'origen del descuento: {d.tipo_descuento.value_counts().to_dict()}',
                  'tipo_descuento (10% identificado = beneficio tarjeta, S05)', (d.tipo_descuento == 'beneficio_tarjeta').sum())
    d = d.rename(columns={'linea': 'linea_origen', 'precio_unitario_n': 'precio_unitario_num', 'monto_linea_n': 'monto_linea_num'})
    return d[['boleta_id', 'linea_seq', 'linea_origen', 'sku', 'cantidad', 'precio_unitario_num', 'descuento_pct',
              'monto_linea_num', 'monto_calculado', 'dif_monto', 'campana_id', 'tipo_descuento', 'es_devolucion',
              'flag_monto_inconsistente', 'flag_volumen_mayorista', 'flag_sku_sin_maestro', 'flag_linea_repetida_origen',
              'flag_linea_posible_duplicada', 'flag_descuento_fuera_dominio']].rename(
        columns={'precio_unitario_num': 'precio_unitario', 'monto_linea_num': 'monto_linea'}).reset_index(drop=True)

# ----------------------------------------------------------------- orquestación
def ejecutar(log):
    pos = _leer_pos()
    geo = _geografia(pos, log)
    tiendas = _tiendas(pos, geo, log)
    clientes = _clientes(pos, log)
    boletas = _boletas(pos, tiendas, clientes, log)
    productos = _productos(log)
    camp, cs = _campanas(productos, log)
    ipc = _ipc(log)
    detalle = _detalle(pos, boletas, productos, camp, cs, log)
    salida = {'geografia': geo, 'tiendas': tiendas, 'medios_pago': pos['medios_pago'], 'clientes': clientes,
              'boletas': boletas, 'boleta_detalle': detalle, 'productos': productos, 'campanas': camp,
              'campana_sku': cs, 'ipc_mensual': ipc}
    for nombre, df in salida.items():
        L.escribir_csv(df, config.PLATA / f'{nombre}.csv')
    salida['_n_bronce'] = {t: len(pos[t]) for t in config.TABLAS_POS}
    return salida
