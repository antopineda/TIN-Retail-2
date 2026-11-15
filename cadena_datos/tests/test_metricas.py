# -*- coding: utf-8 -*-
"""Tests de la capa semántica (metricas.py) con casos de resultado conocido."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import metricas as M  # noqa: E402


def test_wilson_contiene_la_proporcion_y_se_achica_con_n():
    lo, hi = M.wilson(51, 100)
    assert lo < 0.51 < hi
    lo2, hi2 = M.wilson(510, 1000)
    assert (hi2 - lo2) < (hi - lo)
    assert M.wilson(0, 10)[0] == 0.0 and M.wilson(10, 10)[1] == 1.0
    assert all(np.isnan(M.wilson(0, 0)))


def test_margen_linea_sin_iva_e_imputacion():
    monto = pd.Series([1190.0, 2380.0])
    venta, costo, margen, imp = M.margen_linea(monto, pd.Series([1, 2]), pd.Series([700.0, np.nan]), 0.5)
    assert venta.tolist() == pytest.approx([1000.0, 2000.0])
    assert costo.tolist() == pytest.approx([700.0, 1000.0])       # la segunda línea se imputa con 50% de la venta sin IVA
    assert margen.tolist() == pytest.approx([300.0, 1000.0])
    assert imp.tolist() == [False, True]


def _episodios():
    # dias_observados, censurado, margen anual del cliente, ticket
    filas = [(10, False), (50, False), (70, False), (120, False), (95, True), (65, True)]
    return pd.DataFrame([{'cliente_key': i, 'dias_observados': d, 'censurado': c, 'margen_anual_cliente': 3000.0,
                          'ticket_promedio_cliente': 11900.0} for i, (d, c) in enumerate(filas)])


def test_caso_contacto_clasifica_episodios():
    r = M.caso_contacto(_episodios(), dia_contacto=60, ventana=90, costo_envio=100, cupon_pct=10, tasa_recuperacion=0.5)
    assert r['contactados'] == 4          # 70, 120, 95c, 65c
    assert r['vuelven_solos'] == 1        # 70 (volvió antes de 90)
    assert r['se_pierden'] == 2           # 120 y 95c
    assert r['sin_desenlace'] == 1        # 65c
    cupon = 0.10 * 11900 / 1.19           # 1.000 CLP de margen por cupón
    assert r['costo_cupon_unitario'] == pytest.approx(cupon)
    assert r['costo_total'] == pytest.approx(4 * 100 + (1 + 1) * cupon)
    assert r['margen_recuperado'] == pytest.approx(0.5 * 6000)
    # equilibrio: costo fijo (envíos + cupones de los que vuelven solos) / (margen de los que se pierden − sus cupones)
    assert r['tasa_equilibrio'] == pytest.approx((400 + cupon) / (6000 - 2 * cupon))


def test_contactar_mas_tarde_desperdicia_menos_contactos():
    e = _episodios()
    temprano, tarde = M.caso_contacto(e, 30, 90), M.caso_contacto(e, 75, 90)
    assert temprano['contactados'] >= tarde['contactados']
    assert temprano['vuelven_solos'] >= tarde['vuelven_solos']


def test_regla_de_lectura_menciona_la_ventana():
    assert '90 días' in M.regla_lectura(90)
