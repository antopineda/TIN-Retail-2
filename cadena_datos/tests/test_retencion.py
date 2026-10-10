# -*- coding: utf-8 -*-
"""Tests de la lógica de actividad y retención con clientes sintéticos de resultado conocido."""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import retencion as R  # noqa: E402


def _f(*fechas):
    return R.fechas_por_cliente(pd.DataFrame({'cliente_id': 1, 'fecha': pd.to_datetime(list(fechas))}))[1]


def test_activo_en_borde_de_ventana():
    f = _f('2025-01-01')
    assert R.activo_en(f, '2025-01-30', 30)        # 29 días: activo
    assert not R.activo_en(f, '2025-01-31', 30)    # 30 días: (t − 30, t] ya no incluye el 1-ene
    assert not R.activo_en(f, '2024-12-31', 30)    # antes de la primera compra


def test_compro_entre_y_dias_desde_ultima():
    f = _f('2025-02-10', '2025-05-05')
    assert R.compro_entre(f, '2025-05-01', '2025-05-31')
    assert not R.compro_entre(f, '2025-03-01', '2025-04-30')
    assert R.dias_desde_ultima(f, '2025-05-31') == 26


def test_estados_trimestre():
    compras = pd.DataFrame({'cliente_id': [1, 1, 2, 3, 3, 4], 'fecha': pd.to_datetime(
        ['2025-03-15', '2025-05-10',   # 1: activo al inicio de Q2 y compra en Q2 -> retenido
         '2025-03-20',                 # 2: activo al inicio de Q2 (W=60), no vuelve -> perdido
         '2025-01-05', '2025-06-01',   # 3: inactivo al 31-mar (W=60) y vuelve en Q2 -> reactivado
         '2025-05-15'])})              # 4: primera compra en Q2 y sigue activo al cierre -> nuevo
    fechas = R.fechas_por_cliente(compras)
    per = R.periodos('2025-04-01', '2025-06-30').query('periodo == "2025Q2"')
    est = R.estados_cliente_periodo(fechas, {1: False, 2: False, 3: False, 4: True}, per, [60]).set_index('cliente_id')
    assert est.loc[1, 'retenido']
    assert est.loc[2, 'perdido']
    assert est.loc[3, 'reactivado']
    assert est.loc[4, 'nuevo']
    ag = R.agregar_retencion(est.reset_index(), pd.DataFrame({'periodo_tipo': ['trimestre'], 'periodo': ['2025Q2'],
                                                              'ventana_dias': [60], 'base_confiable': [True]}))
    r = ag.iloc[0]
    assert (r.activos_inicio, r.retenidos, r.perdidos, r.nuevos, r.reactivados) == (2, 1, 1, 1, 1)
    assert r.tasa_retencion == 0.5
    assert r.activos_fin == r.retenidos + r.nuevos + r.reactivados + r.primeras_obs_previos


def test_primera_obs_de_cliente_previo_no_es_nuevo():
    compras = pd.DataFrame({'cliente_id': [9], 'fecha': pd.to_datetime(['2025-05-15'])})
    per = R.periodos('2025-04-01', '2025-06-30').query('periodo == "2025Q2"')
    est = R.estados_cliente_periodo(R.fechas_por_cliente(compras), {9: False}, per, [90]).iloc[0]
    assert est.primera_obs_previo and not est.nuevo


def test_nuevo_que_se_va_en_el_mismo_periodo_cuenta_solo_en_flujo():
    compras = pd.DataFrame({'cliente_id': [5], 'fecha': pd.to_datetime(['2025-04-02'])})
    per = R.periodos('2025-04-01', '2025-06-30').query('periodo == "2025Q2"')
    est = R.estados_cliente_periodo(R.fechas_por_cliente(compras), {5: True}, per, [60]).iloc[0]
    assert not est.nuevo and est.nuevo_flujo and not est.activo_fin
