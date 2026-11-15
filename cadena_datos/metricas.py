# -*- coding: utf-8 -*-
"""
Capa semántica: cada métrica se define UNA vez, aquí. La cadena (etapa_oro, documentacion) y el prototipo
(prototipo/app.py) importan estas definiciones; nadie recalcula la fórmula por su cuenta.

Métrica principal: TASA DE RETENCIÓN TRIMESTRAL.
  Regla de lectura: un cliente se RETIENE en el trimestre si estaba activo al inicio (compró en los W días previos
  al primer día) y sigue activo al cierre (compró en los W días previos al último día).
  tasa = retenidos / activos al inicio.     Ventana oficial W = 90 días; alternativa = 30 días.
"""
import math

import numpy as np
import pandas as pd

import config

METRICAS = {
    'tasa_retencion': {
        'nombre': 'Retención trimestral de clientes con tarjeta',
        'formula': 'clientes activos al inicio del trimestre que siguen activos al cierre / clientes activos al inicio',
        'unidad': '% de clientes',
        'definicion_oficial': f'ventana de {config.VENTANA_PRINCIPAL} días',
        'definicion_alternativa': 'ventana de 30 días (regla de un mes que hoy usa la empresa)',
    },
    'indice_reposicion': {
        'nombre': 'Índice de reposición',
        'formula': 'clientes nuevos del trimestre / clientes perdidos del trimestre',
        'unidad': 'clientes nuevos por cada cliente perdido (< 1 = la base se achica)',
    },
    'margen_anual_en_riesgo': {
        'nombre': 'Margen anual en riesgo',
        'formula': 'Σ margen bruto trimestral típico de los clientes perdidos en el trimestre × 4',
        'unidad': 'CLP nominales 2025 de margen bruto (sin IVA) por año',
    },
    'veredicto': {
        'nombre': 'Veredicto retiene / repone',
        'formula': (f'RETIENE si retenidos / activos al cierre >= {config.UMBRAL_BASE_RETENIDA:.0%}; si no, REPONE si '
                    '(nuevos + reactivados + primeras compras de previos) >= perdidos; si no, SE ACHICA'),
        'unidad': 'categoría (la misma regla para cualquier ventana)',
    },
    'pct_una_sola_vez': {
        'nombre': 'Clientes nuevos de una sola vez',
        'formula': f'clientes nuevos 2025 sin una segunda compra dentro de {config.HORIZONTE_SEGUNDA_COMPRA} días de la primera / clientes nuevos evaluables',
        'unidad': '% de clientes nuevos (horizonte fijo, no depende de la ventana)',
    },
    'cobertura': {
        'nombre': 'Cobertura de la retención',
        'formula': 'boletas del origen que entran a la retención / boletas del origen',
        'unidad': '% de boletas (y % de la venta 2025)',
    },
}


def regla_lectura(ventana):
    return (f'Un cliente se retiene si compró en los {ventana} días previos al inicio del trimestre '
            f'y vuelve a aparecer activo al cierre (alguna compra en los {ventana} días previos al último día).')


def veredicto(retenidos, activos_fin, perdidos, incorporados, umbral=config.UMBRAL_BASE_RETENIDA):
    """Regla S22. Devuelve 'Retiene', 'Repone', 'Se achica' o None si no hay base."""
    if not activos_fin or pd.isna(activos_fin) or activos_fin <= 0:
        return None
    if retenidos / activos_fin >= umbral:
        return 'Retiene'
    return 'Repone' if incorporados >= perdidos else 'Se achica'


def regla_veredicto():
    return (f'La cadena RETIENE si al menos el {config.UMBRAL_BASE_RETENIDA:.0%} de sus clientes activos al cierre ya estaban activos al inicio. '
            'Si no, REPONE si los que llegan (nuevos y reactivados) cubren a los perdidos; si tampoco, la base SE ACHICA.')


def wilson(k, n, z=config.Z_IC95):
    """Intervalo de confianza de Wilson para una proporción k/n. Devuelve (inf, sup) o (nan, nan) si n = 0."""
    if not n or n <= 0 or pd.isna(n):
        return (np.nan, np.nan)
    p = k / n
    den = 1 + z ** 2 / n
    centro = (p + z ** 2 / (2 * n)) / den
    mitad = z * math.sqrt(p * (1 - p) / n + z ** 2 / (4 * n ** 2)) / den
    return (max(0.0, centro - mitad), min(1.0, centro + mitad))


def margen_linea(monto_linea, cantidad, costo_unitario, razon_costo_imputada):
    """Margen bruto de una línea en CLP sin IVA. Si falta el costo, se imputa con la razón costo/venta sin IVA (S17)."""
    venta_sin_iva = monto_linea / config.FACTOR_IVA
    costo = cantidad * costo_unitario
    imputado = costo.isna()
    costo = costo.where(~imputado, venta_sin_iva * razon_costo_imputada)
    return venta_sin_iva, costo, venta_sin_iva - costo, imputado


def retencion(mret, periodo='2025Q4', ventana=config.VENTANA_PRINCIPAL, corte='Total', valor='Total'):
    """Una fila de mart_retencion: la cifra oficial se lee siempre por aquí."""
    m = mret[(mret.corte == corte) & (mret.valor == valor) & (mret.periodo == periodo) & (mret.ventana_dias == ventana)]
    return m.iloc[0] if len(m) else None


def caso_contacto(episodios, dia_contacto=config.CONTACTO_DIA_DEFECTO, ventana=config.VENTANA_PRINCIPAL,
                  costo_envio=config.CONTACTO_COSTO_ENVIO_CLP, cupon_pct=config.CONTACTO_CUPON_PCT,
                  tasa_recuperacion=config.CONTACTO_TASA_RECUPERACION):
    """Cuánto cuesta y cuánto recupera contactar a los clientes cuando cumplen `dia_contacto` días sin comprar (2025).

    episodios: mart_episodios_inactividad (una fila por compra válida: días hasta la siguiente o hasta el corte).
    - contactados: episodios que llegan a `dia_contacto` días sin compra.
    - vuelven_solos: de ellos, los que vuelven antes de `ventana` días sin que nadie los llame (el cupón es costo puro).
    - se_pierden: los que llegan a `ventana` días sin comprar (cruzan la definición de perdido).
    - sin_desenlace: el año terminó antes de saber si volvían (se contactan, pero no suman valor: criterio conservador).
    Todo en CLP nominales 2025 sin IVA. El valor es margen bruto anual de los recuperados (S20); el costo, envío + cupón.
    """
    e = episodios
    llegan = e[e.dias_observados >= dia_contacto]
    solos = llegan[~llegan.censurado & (llegan.dias_observados < ventana)]
    pierden = llegan[llegan.dias_observados >= ventana]
    sin_des = llegan[llegan.censurado & (llegan.dias_observados < ventana)]
    cupon_unit = (cupon_pct / 100) * e.ticket_promedio_cliente.mean() / config.FACTOR_IVA
    margen_pierden = pierden.margen_anual_cliente.clip(lower=0).sum()
    recuperados = tasa_recuperacion * len(pierden)
    costo_fijo = len(llegan) * costo_envio + len(solos) * cupon_unit
    costo = costo_fijo + recuperados * cupon_unit
    beneficio = tasa_recuperacion * margen_pierden
    den = margen_pierden - len(pierden) * cupon_unit
    equilibrio = costo_fijo / den if den > 0 else np.nan
    return {'dia_contacto': dia_contacto, 'ventana_dias': ventana, 'contactados': len(llegan), 'vuelven_solos': len(solos),
            'se_pierden': len(pierden), 'sin_desenlace': len(sin_des),
            'pct_contactos_desperdiciados': len(solos) / len(llegan) if len(llegan) else np.nan,
            'costo_cupon_unitario': cupon_unit, 'margen_anual_de_los_que_se_pierden': margen_pierden,
            'recuperados': recuperados, 'costo_total': costo, 'margen_recuperado': beneficio,
            'resultado_neto': beneficio - costo, 'tasa_equilibrio': equilibrio}
