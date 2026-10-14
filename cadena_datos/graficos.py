# -*- coding: utf-8 -*-
"""
Visualizaciones del análisis, generadas desde las tablas oro.
Cada gráfico lleva la unidad en el título y la fuente al pie. Se regeneran en cada corrida,
así las cifras de las figuras siempre calzan con las de las tablas.
Paleta: instancia de referencia validada para daltonismo (azul, naranjo, aqua, amarillo).
"""
import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

import config  # noqa: E402

AZUL, NARANJO, AQUA, AMARILLO = '#2a78d6', '#eb6834', '#1baf7a', '#eda100'
AZUL_CLARO = '#b7d3f6'                       # mismo tono que AZUL, para las alternativas
TINTA, TINTA_2, GRILLA, FONDO = '#0b0b0b', '#52514e', '#e4e2dd', '#fcfcfb'
FUENTE = 'Fuente: POS Multitienda del Sur (origen_pos.sqlite), compras identificadas 2025. Elaboración propia, cadena_datos'

plt.rcParams.update({'font.size': 11, 'axes.edgecolor': TINTA_2, 'axes.labelcolor': TINTA_2, 'xtick.color': TINTA_2,
                     'ytick.color': TINTA_2, 'axes.spines.top': False, 'axes.spines.right': False,
                     'figure.facecolor': FONDO, 'axes.facecolor': FONDO, 'savefig.facecolor': FONDO})


def _pct(x, dec=1):
    return f'{x * 100:.{dec}f}%'.replace('.', ',')


def _num(x):
    return f'{x:,.0f}'.replace(',', '.')


def _cerrar(fig, ruta, titulo, tabla):
    fig.suptitle(titulo, x=0.01, ha='left', fontsize=13, color=TINTA, fontweight='bold')
    fig.text(0.01, 0.01, f'{FUENTE}.\nTabla: {tabla}.', fontsize=8, color=TINTA_2, linespacing=1.4)
    fig.tight_layout(rect=(0, 0.07, 1, 0.94))
    fig.savefig(ruta, dpi=200)
    plt.close(fig)


def _grilla(ax, eje='y'):
    ax.grid(axis=eje, color=GRILLA, linewidth=0.8)
    ax.set_axisbelow(True)


def sensibilidad_ventana(kpi, mret, ruta):
    k = kpi.set_index('kpi').valor
    q4 = mret[(mret.corte == 'Total') & (mret.periodo == '2025Q4')].set_index('ventana_dias')
    etiqueta = {30: '30 días\n(creencia empresa)', 90: '90 días\n(principal)', 180: '180 días', 365: '365 días\n(no discrimina)'}
    ws = config.VENTANAS
    colores = [AZUL if w == config.VENTANA_PRINCIPAL else AZUL_CLARO for w in ws]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.6))
    series = [([k[f'pct_activos_{w}d_al_corte'] for w in ws], 'Clientes activos al 31-12-2025\n(% de los clientes con compra en 2025)'),
              ([q4.loc[w].tasa_retencion for w in ws], 'Retención en Q4-2025\n(% de activos al 1-oct que siguen activos al 31-dic)')]
    for ax, (vals, sub) in zip(axes, series):
        barras = ax.bar(range(len(ws)), vals, color=colores, width=0.6, edgecolor=FONDO, linewidth=2)
        for b, v in zip(barras, vals):
            ax.text(b.get_x() + b.get_width() / 2, v + 0.02, _pct(v), ha='center', fontsize=11, color=TINTA, fontweight='bold')
        ax.set_xticks(range(len(ws)), [etiqueta.get(w, f'{w} días') for w in ws], fontsize=9.5)
        ax.set_ylim(0, 1.12)
        ax.yaxis.set_major_formatter(lambda y, _: _pct(y, 0))
        ax.set_title(sub, fontsize=10.5, color=TINTA_2, loc='left')
        _grilla(ax)
    _cerrar(fig, ruta, 'La definición de "cliente activo" cambia la respuesta (%)', 'mart_kpi_resumen, mart_retencion')


def retencion_trimestral(mret, ruta):
    t = mret[(mret.corte == 'Total') & (mret.periodo_tipo == 'trimestre') & (mret.ventana_dias == config.VENTANA_PRINCIPAL)
             & mret.base_confiable].set_index('periodo')
    per = list(t.index)
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4.6), gridspec_kw={'width_ratios': [1, 1.4]})
    b = a1.bar(per, t.tasa_retencion, color=AZUL, width=0.55, edgecolor=FONDO, linewidth=2)
    for bar, v in zip(b, t.tasa_retencion):
        a1.text(bar.get_x() + bar.get_width() / 2, v + 0.02, _pct(v), ha='center', fontweight='bold', color=TINTA)
    a1.set_ylim(0, 0.85)
    a1.yaxis.set_major_formatter(lambda y, _: _pct(y, 0))
    a1.set_title('Tasa de retención trimestral (%)', fontsize=10.5, color=TINTA_2, loc='left')
    _grilla(a1)
    series = [('nuevos', 'Nuevos', AZUL), ('perdidos', 'Perdidos', NARANJO), ('reactivados', 'Reactivados', AQUA)]
    ancho = 0.26
    for i, (col, nombre, color) in enumerate(series):
        xs = [j + (i - 1) * ancho for j in range(len(per))]
        barras = a2.bar(xs, t[col], width=ancho, color=color, label=nombre, edgecolor=FONDO, linewidth=2)
        for bar, v in zip(barras, t[col]):
            a2.text(bar.get_x() + bar.get_width() / 2, v + 5, _num(v), ha='center', fontsize=9, color=TINTA)
    a2.set_xticks(range(len(per)), per)
    a2.set_title('Clientes que entran y salen en cada trimestre (n° de clientes)', fontsize=10.5, color=TINTA_2, loc='left')
    a2.legend(frameon=False, ncol=3, loc='upper left', fontsize=9.5)
    a2.set_ylim(0, max(t[c].max() for c, _, _ in series) * 1.25)
    _grilla(a2)
    _cerrar(fig, ruta, f'Retención trimestral y movimiento de clientes, ventana {config.VENTANA_PRINCIPAL} días',
            'mart_retencion; Q1 omitido: sin datos 2024 no hay base para medir')


def retencion_por_local(mret, ruta):
    w = config.VENTANA_PRINCIPAL
    loc = mret[(mret.corte == 'Tienda principal') & (mret.periodo == '2025Q4') & (mret.ventana_dias == w)].sort_values('tasa_retencion')
    total = mret[(mret.corte == 'Total') & (mret.periodo == '2025Q4') & (mret.ventana_dias == w)].tasa_retencion.iloc[0]
    fig, ax = plt.subplots(figsize=(11, 5.6))
    barras = ax.barh(loc.valor, loc.tasa_retencion, color=AZUL, height=0.6, edgecolor=FONDO, linewidth=2)
    for bar, (_, r) in zip(barras, loc.iterrows()):
        ax.text(r.tasa_retencion + 0.01, bar.get_y() + bar.get_height() / 2,
                f'{_pct(r.tasa_retencion)}  (n = {_num(r.activos_inicio)})', va='center', fontsize=9.5, color=TINTA,
                bbox={'facecolor': FONDO, 'edgecolor': 'none', 'pad': 1.5}, zorder=4)
    ax.axvline(total, color=TINTA_2, linestyle='--', linewidth=1.2, zorder=1)
    ax.text(total, len(loc) - 0.35, f' Total cadena: {_pct(total)}', color=TINTA_2, fontsize=9.5, va='bottom')
    ax.set_xlim(0, 0.85)
    ax.xaxis.set_major_formatter(lambda x, _: _pct(x, 0))
    _grilla(ax, 'x')
    _cerrar(fig, ruta, f'Retención Q4-2025 por local principal (%), ventana {w} días',
            'mart_retencion. n = clientes activos al inicio de Q4; con n < 50 la tasa es volátil')


def cohortes_nuevos(mcoh, ruta):
    c = mcoh[(mcoh.tipo_cohorte == 'Nuevo 2025')]
    cohortes = sorted(c.cohorte_trimestre.unique())[:-1]          # la última cohorte solo tiene su trimestre de ingreso
    fig, ax = plt.subplots(figsize=(11, 4.8))
    for coh, color in zip(cohortes, [AZUL, NARANJO, AQUA, AMARILLO]):
        g = c[c.cohorte_trimestre == coh].sort_values('trimestres_desde_ingreso')
        n = int(g.tamano_cohorte.iloc[0])
        ax.plot(g.trimestres_desde_ingreso, g.pct_activos, color=color, linewidth=2, marker='o', markersize=8,
                markeredgecolor=FONDO, markeredgewidth=2, label=f'Llegaron en {coh} (n = {n})')
        u = g.iloc[-1]
        ax.text(u.trimestres_desde_ingreso + 0.06, u.pct_activos - 0.05, _pct(u.pct_activos), va='center', fontsize=10,
                color=TINTA, fontweight='bold')
    ax.set_xticks(range(4), ['Trimestre de\ningreso', '1 trimestre\ndespués', '2 trimestres\ndespués', '3 trimestres\ndespués'])
    ax.set_ylim(0, 1.08)
    ax.set_xlim(-0.2, 3.4)
    ax.yaxis.set_major_formatter(lambda y, _: _pct(y, 0))
    ax.legend(frameon=False, loc='lower left', fontsize=9.5)
    _grilla(ax)
    _cerrar(fig, ruta, 'Clientes nuevos 2025 que siguen comprando, por trimestre de llegada (% de la cohorte)',
            'mart_cohortes, tipo_cohorte = "Nuevo 2025"')


def composicion_mensual(mcm, ruta):
    col = f'estado_{config.VENTANA_PRINCIPAL}d'
    m = mcm[mcm.compro_en_mes].groupby(['anio_mes', col]).size().unstack(fill_value=0)
    capas = [('recurrente', 'Recurrentes', AZUL), ('nuevo', 'Nuevos (alta 2025)', NARANJO),
             ('reactivado', 'Reactivados', AQUA), ('primera_obs_previo', 'Primera compra de cliente previo (alta 2024)', AMARILLO)]
    meses = list(m.index)
    etiquetas = [pd.Period(x).strftime('%b').capitalize() for x in meses]
    nombres_mes = {'Jan': 'Ene', 'Apr': 'Abr', 'Aug': 'Ago', 'Dec': 'Dic'}
    etiquetas = [nombres_mes.get(e, e) for e in etiquetas]
    fig, ax = plt.subplots(figsize=(11, 5))
    base = pd.Series(0, index=meses)
    for clave, nombre, color in capas:
        v = m[clave] if clave in m else pd.Series(0, index=meses)
        ax.bar(range(len(meses)), v, bottom=base, color=color, label=nombre, width=0.7, edgecolor=FONDO, linewidth=2)
        base = base + v
    for i, tot in enumerate(base):
        ax.text(i, tot + 4, _num(tot), ha='center', fontsize=9, color=TINTA)
    ax.set_xticks(range(len(meses)), etiquetas)
    ax.set_ylim(0, base.max() * 1.18)
    ax.legend(frameon=False, ncol=2, loc='upper left', fontsize=9.5)
    _grilla(ax)
    _cerrar(fig, ruta, f'Clientes que compran cada mes según su estado (n° de clientes), ventana {config.VENTANA_PRINCIPAL} días',
            'mart_cliente_mes. Enero: todos aparecen por primera vez porque no hay datos 2024')


def ejecutar(oro):
    carpeta = config.ORO / 'graficos'
    carpeta.mkdir(parents=True, exist_ok=True)
    figuras = {
        '1_sensibilidad_ventana.png': lambda r: sensibilidad_ventana(oro['mart_kpi_resumen'], oro['mart_retencion'], r),
        '2_retencion_trimestral.png': lambda r: retencion_trimestral(oro['mart_retencion'], r),
        '3_retencion_por_local.png': lambda r: retencion_por_local(oro['mart_retencion'], r),
        '4_cohortes_nuevos.png': lambda r: cohortes_nuevos(oro['mart_cohortes'], r),
        '5_composicion_mensual.png': lambda r: composicion_mensual(oro['mart_cliente_mes'], r),
    }
    for nombre, fn in figuras.items():
        fn(carpeta / nombre)
    return sorted(figuras)
