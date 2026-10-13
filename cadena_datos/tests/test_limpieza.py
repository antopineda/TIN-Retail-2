# -*- coding: utf-8 -*-
"""Tests de las reglas de limpieza con ejemplos reales del set grupo_2."""
import math
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import limpieza as L  # noqa: E402


@pytest.mark.parametrize('crudo, esperado', [
    ('2025-10-26', '2025-10-26'),          # ISO
    ('06/07/2025', '2025-07-06'),          # dd/mm/yyyy (día primero, validado contra columna mes)
    ('09-10-25', '2025-10-09'),            # dd-mm-yy
    ('19-dic-2025', '2025-12-19'),         # d-mmm-yyyy en español
    ('7-sep-2025', '2025-09-07'),
    ('2025-09-01T00:00:00', '2025-09-01'),  # ISO con hora (promociones)
])
def test_parse_fecha(crudo, esperado):
    assert L.parse_fecha(crudo) == pd.Timestamp(esperado)


@pytest.mark.parametrize('crudo', ['', None, '31/02/2025', '12-xyz-2025', 'ayer'])
def test_parse_fecha_invalida(crudo):
    assert pd.isna(L.parse_fecha(crudo))


@pytest.mark.parametrize('crudo, esperado', [
    ('1.940', 1940), ('6908', 6908), ('$1.200', 1200), ('1.202,00', 1202), ('$979', 979),
    ('-.905', -905), ('-1542', -1542), ('17.231', 17231), (' 2.038 ', 2038),
])
def test_parse_monto(crudo, esperado):
    assert L.parse_monto(crudo) == esperado


def test_parse_monto_no_numerico():
    assert math.isnan(L.parse_monto('N/A'))


@pytest.mark.parametrize('crudo, esperado', [
    ('0', 0), ('10', 10), ('10%', 10), ('0,10', 10), ('25', 25), ('25%', 25), ('0,25', 25), (50, 50), ('25%', 25),
])
def test_parse_descuento(crudo, esperado):
    assert L.parse_descuento(crudo) == pytest.approx(esperado)


@pytest.mark.parametrize('crudo, esperado', [
    ('13173783-1', '13173783-1'), ('14.055.309-3', '14055309-3'), (' 16.612.622-3', '16612622-3'),
    ('10017312  3', '10017312-3'), ('12345678k', '12345678-K'),
])
def test_normalizar_rut(crudo, esperado):
    assert L.normalizar_rut(crudo) == esperado


def test_rut_valido():
    assert L.rut_valido('11111111-1')
    assert L.rut_valido('12345678-5')
    assert not L.rut_valido('12345678-4')
    assert not L.rut_valido(None)


@pytest.mark.parametrize('nombre, tipo', [
    ('Sra. Vega', 'Persona/Hogar'), ('Familia Sepúlveda', 'Persona/Hogar'), ('Sr. Rojas', 'Persona/Hogar'),
    ('Comercial Flores', 'Negocio'), ('Kiosco Torres', 'Negocio'), ('Botillería Díaz', 'Negocio'),
    ('Juan Pérez', 'No determinado'), ('Srta Pérez', 'No determinado'),
])
def test_clasificacion_nombre(nombre, tipo):
    assert L.clasificacion_nombre(nombre) == tipo


@pytest.mark.parametrize('crudo, esperado', [
    ('ABARR', 'Abarrotes'), ('abarrotes', 'Abarrotes'), ('Lácteos', 'Lácteos'), ('lacteos', 'Lácteos'),
    ('LACT', 'Lácteos'), ('ASEO', 'Limpieza'), ('PERF', 'Perfumería'), ('perfumeria', 'Perfumería'), ('SNK', 'Snacks'),
])
def test_categoria_canonica(crudo, esperado):
    assert L.categoria_canonica(crudo) == esperado


@pytest.mark.parametrize('crudo, esperado', [('1', True), ('Sí', True), ('si', True), ('SI', True), ('No', False), ('', None)])
def test_parse_activo(crudo, esperado):
    assert L.parse_activo(crudo) is esperado


def test_nombre_producto():
    assert L.nombre_producto('ARROZ TUCAPEL F1  ') == 'Arroz Tucapel F1'
    assert L.nombre_producto('Arroz Tucapel F1') == 'Arroz Tucapel F1'
