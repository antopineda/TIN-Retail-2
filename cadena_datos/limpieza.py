# -*- coding: utf-8 -*-
"""Funciones puras de limpieza y utilidades comunes (log de calidad, escritura de CSV)."""
import re
import unicodedata
import numpy as np
import pandas as pd

import config

# ================================================================= log de calidad
class LogCalidad:
    """Registra cada regla aplicada con el número de filas afectadas (alimenta oro/log_calidad.csv)."""

    def __init__(self):
        self.filas = []

    def registrar(self, regla, tabla, columna, problema, accion, filas_afectadas):
        self.filas.append({'regla': regla, 'tabla': tabla, 'columna': columna, 'problema': problema,
                           'accion': accion, 'filas_afectadas': int(filas_afectadas)})

    def df(self):
        return pd.DataFrame(self.filas)


def escribir_csv(df, ruta):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(ruta, index=False, encoding=config.ENCODING_SALIDA, date_format='%Y-%m-%d', lineterminator='\n')


def es_nulo(x):
    return x is None or (isinstance(x, float) and np.isnan(x)) or (isinstance(x, str) and x.strip() in ('', 'None', 'nan', 'NaN'))

# ================================================================= fechas
MESES_ES = {'ene': 1, 'feb': 2, 'mar': 3, 'abr': 4, 'may': 5, 'jun': 6,
            'jul': 7, 'ago': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dic': 12}
FORMATOS_FECHA = [
    ('iso', re.compile(r'^(\d{4})-(\d{2})-(\d{2})(?:[ T].*)?$')),     # 2025-07-25 / con hora
    ('dd/mm/yyyy', re.compile(r'^(\d{1,2})/(\d{1,2})/(\d{4})$')),     # 06/07/2025 (validado: día/mes)
    ('dd-mm-yy', re.compile(r'^(\d{1,2})-(\d{1,2})-(\d{2})$')),       # 09-10-25 (siglo 20xx)
    ('d-mmm-yyyy', re.compile(r'^(\d{1,2})-([A-Za-z]{3})-(\d{4})$')), # 19-dic-2025
]


def formato_fecha(s):
    if es_nulo(s):
        return 'nulo'
    s = str(s).strip()
    for nombre, patron in FORMATOS_FECHA:
        if patron.match(s):
            return nombre
    return 'desconocido'


def parse_fecha(s):
    """Convierte los 4 formatos observados a Timestamp; NaT si no calza o la fecha es imposible."""
    if es_nulo(s):
        return pd.NaT
    s = str(s).strip()
    try:
        for nombre, patron in FORMATOS_FECHA:
            m = patron.match(s)
            if not m:
                continue
            a, b, c = m.groups()
            if nombre == 'iso':
                return pd.Timestamp(int(a), int(b), int(c))
            if nombre == 'dd/mm/yyyy':
                return pd.Timestamp(int(c), int(b), int(a))
            if nombre == 'dd-mm-yy':
                return pd.Timestamp(2000 + int(c), int(b), int(a))
            if nombre == 'd-mmm-yyyy':
                mes = MESES_ES.get(b.lower())
                return pd.Timestamp(int(c), mes, int(a)) if mes else pd.NaT
    except ValueError:
        return pd.NaT
    return pd.NaT

# ================================================================= montos y descuentos
def parse_monto(s):
    """'1.940' -> 1940 ; '$1.200' -> 1200 ; '1.202,00' -> 1202 ; '-.905' -> -905 ; 'N/A' -> NaN."""
    if es_nulo(s):
        return np.nan
    t = str(s).strip().replace('$', '').replace(' ', '')
    if re.fullmatch(r'-?\d+', t):
        return float(t)
    m = re.fullmatch(r'(-?)\.(\d{3})', t)                 # miles con el cero perdido: '-.905'
    if m:
        return float(m.group(1) + m.group(2))
    if re.fullmatch(r'-?\d{1,3}(\.\d{3})+', t):           # punto de miles
        return float(t.replace('.', ''))
    if re.fullmatch(r'-?\d{1,3}(\.\d{3})*,\d+', t) or re.fullmatch(r'-?\d+,\d+', t):  # coma decimal
        return float(t.replace('.', '').replace(',', '.'))
    if re.fullmatch(r'-?\d+\.\d{1,2}', t):                # punto decimal
        return float(t)
    return np.nan


def parse_descuento(s):
    """'10' / '10%' / '0,10' -> 10.0 (porcentaje)."""
    if es_nulo(s):
        return np.nan
    t = str(s).strip()
    try:
        if t.endswith('%'):
            return float(t[:-1].replace(',', '.'))
        if ',' in t:
            return round(float(t.replace(',', '.')) * 100, 6)
        v = float(t)
        return v * 100 if 0 < v < 1 else v
    except ValueError:
        return np.nan

# ================================================================= RUT
def normalizar_rut(s):
    """' 16.612.622-3' -> '16612622-3'. Devuelve None si no tiene forma de RUT."""
    if es_nulo(s):
        return None
    t = re.sub(r'[\s.]', '', str(s)).upper()
    t = t.replace('-', '')
    if not re.fullmatch(r'\d{6,8}[\dK]', t):
        return None
    return f'{t[:-1]}-{t[-1]}'


def rut_valido(rut_normalizado):
    """Valida el dígito verificador (módulo 11)."""
    if rut_normalizado is None:
        return False
    cuerpo, dv = rut_normalizado.split('-')
    suma, mult = 0, 2
    for d in reversed(cuerpo):
        suma += int(d) * mult
        mult = 2 if mult == 7 else mult + 1
    esperado = 11 - suma % 11
    esperado = '0' if esperado == 11 else 'K' if esperado == 10 else str(esperado)
    return esperado == dv

# ================================================================= texto y categorías
def sin_tildes(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')


def clasificacion_nombre(nombre):
    """Clasificación del equipo por prefijo del nombre (no es una categoría de la empresa)."""
    if es_nulo(nombre):
        return 'No determinado'
    n = str(nombre).strip()
    for tipo, prefijos in config.PREFIJOS_CLASIFICACION_NOMBRE.items():
        if any(n.startswith(p + ' ') or n == p for p in prefijos):
            return tipo
    return 'No determinado'


def categoria_canonica(s):
    if es_nulo(s):
        return None
    return config.CATEGORIA_CANONICA.get(sin_tildes(str(s)).strip().lower())


def parse_activo(s):
    if es_nulo(s):
        return None
    t = sin_tildes(str(s)).strip().lower()
    if t in ('1', 'si', 's', 'true', 'activo'):
        return True
    if t in ('0', 'no', 'n', 'false', 'inactivo'):
        return False
    return None


def nombre_producto(s):
    if es_nulo(s):
        return None
    t = re.sub(r'\s+', ' ', str(s)).strip()
    return t.title() if t.isupper() else t
