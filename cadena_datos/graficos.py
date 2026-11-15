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
    """La misma regla (S22) bajo cada ventana: retención y nuevos por perdido de Q4, con el veredicto escrito."""
    q4 = mret[(mret.corte == 'Total') & (mret.periodo == '2025Q4')].set_index('ventana_dias')
    etiqueta = {30: '30 días\n(regla de un mes)', 90: '90 días\n(oficial)', 180: '180 días'}
    ws = config.VENTANAS
    colores = [AZUL if w == config.VENTANA_PRINCIPAL else AZUL_CLARO for w in ws]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.8))
    a1, a2 = axes
    b = a1.bar(range(len(ws)), [q4.loc[w].tasa_retencion for w in ws], color=colores, width=0.6, edgecolor=FONDO, linewidth=2)
    for bar, w in zip(b, ws):
        v = q4.loc[w].tasa_retencion
        a1.text(bar.get_x() + bar.get_width() / 2, v + 0.02, _pct(v), ha='center', fontsize=11, color=TINTA, fontweight='bold')
    a1.set_ylim(0, 1.05)
    a1.yaxis.set_major_formatter(lambda y, _: _pct(y, 0))
    a1.set_title('Retención Q4-2025 (% de activos al 1-oct que siguen activos al 31-dic)', fontsize=10.5, color=TINTA_2, loc='left')
    b = a2.bar(range(len(ws)), [q4.loc[w].indice_reposicion for w in ws], color=colores, width=0.6, edgecolor=FONDO, linewidth=2)
    for bar, w in zip(b, ws):
        r = q4.loc[w]
        a2.text(bar.get_x() + bar.get_width() / 2, r.indice_reposicion + 0.06, f'{r.indice_reposicion:.2f}'.replace('.', ','),
                ha='center', fontsize=11, color=TINTA, fontweight='bold')
        a2.text(bar.get_x() + bar.get_width() / 2, r.indice_reposicion + 0.32, r.veredicto.upper(), ha='center', fontsize=10,
                color=NARANJO, fontweight='bold')
    a2.axhline(1, color=TINTA_2, linestyle='--', linewidth=1.2)
    a2.text(1.5, 0.95, '1 nuevo\npor perdido', color=TINTA_2, fontsize=9, ha='center', va='top')
    a2.set_ylim(0, max(q4.loc[w].indice_reposicion for w in ws) * 1.3)
    a2.set_title('Clientes nuevos por cada perdido en Q4 (n°) y veredicto de la regla', fontsize=10.5, color=TINTA_2, loc='left')
    for ax in axes:
        ax.set_xticks(range(len(ws)), [etiqueta.get(w, f'{w} días') for w in ws], fontsize=9.5)
        _grilla(ax)
    v = {w: q4.loc[w].veredicto.lower() for w in ws}
    _cerrar(fig, ruta, f'Q4-2025: con 90 días la cadena {v[90]}, con 30 {v[30]} y con 180 {v[180]}',
            'mart_retencion. Regla S22: retiene si >= 50% de los activos al cierre ya estaban al inicio; si no, repone si los que entran cubren a los perdidos')


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
    """Sin ranking (feedback E1): orden alfabético, cada tasa con su intervalo del 95% y la línea del total."""
    w = config.VENTANA_PRINCIPAL
    loc = mret[(mret.corte == 'Tienda principal') & (mret.periodo == '2025Q4') & (mret.ventana_dias == w)].sort_values('valor', ascending=False)
    total = mret[(mret.corte == 'Total') & (mret.periodo == '2025Q4') & (mret.ventana_dias == w)].iloc[0]
    fig, ax = plt.subplots(figsize=(11, 5.6))
    ys = range(len(loc))
    ax.axvspan(total.ic95_inf, total.ic95_sup, color=GRILLA, alpha=0.6, zorder=0)
    ax.axvline(total.tasa_retencion, color=TINTA_2, linestyle='--', linewidth=1.2, zorder=1)
    ax.hlines(ys, loc.ic95_inf, loc.ic95_sup, color=AZUL_CLARO, linewidth=5, zorder=2)
    ax.scatter(loc.tasa_retencion, ys, color=AZUL, s=60, zorder=3)
    for y, (_, r) in zip(ys, loc.iterrows()):
        ax.text(r.ic95_sup + 0.012, y, f'{_pct(r.tasa_retencion)}  (n = {_num(r.activos_inicio)})', va='center', fontsize=9.5, color=TINTA)
    ax.set_yticks(list(ys), loc.valor)
    ax.text(total.tasa_retencion, len(loc) - 0.4, f' Total cadena: {_pct(total.tasa_retencion)}', color=TINTA_2, fontsize=9.5, va='bottom')
    ax.set_xlim(0, 1)
    ax.xaxis.set_major_formatter(lambda x, _: _pct(x, 0))
    _grilla(ax, 'x')
    fuera = loc[(loc.ic95_sup < total.tasa_retencion) | (loc.ic95_inf > total.tasa_retencion)]
    titulo = (f'Retención Q4-2025 por local (%), ventana {w} días: ' +
              ('ningún local es distinto del total con seguridad' if fuera.empty else f'{len(fuera)} local(es) distinto(s) del total'))
    _cerrar(fig, ruta, titulo, 'mart_retencion. Punto = tasa; barra = intervalo de confianza del 95% (Wilson); n = clientes activos al 1-oct. Orden alfabético, no ranking')


def una_sola_vez(usv, ruta):
    u = usv[(usv.tipo_cohorte == 'Nuevo 2025') & usv.cohorte_trimestre.isin(['2025Q1', '2025Q2', '2025Q3'])].sort_values('cohorte_trimestre')
    fig, ax = plt.subplots(figsize=(11, 4.6))
    b = ax.bar(range(len(u)), u.pct_una_sola_vez, color=[AZUL_CLARO, AZUL_CLARO, NARANJO][:len(u)], width=0.55, edgecolor=FONDO, linewidth=2)
    ax.errorbar(range(len(u)), u.pct_una_sola_vez, yerr=[u.pct_una_sola_vez - u.ic95_inf, u.ic95_sup - u.pct_una_sola_vez],
                fmt='none', ecolor=TINTA_2, capsize=6, linewidth=1.2)
    for bar, (_, r) in zip(b, u.iterrows()):
        ax.text(bar.get_x() + bar.get_width() / 2 + 0.17, r.pct_una_sola_vez + 0.01, f'{_pct(r.pct_una_sola_vez)}\n(n = {_num(r.clientes_evaluables)})',
                ha='left', fontsize=10, color=TINTA)
    ax.set_xticks(range(len(u)), [f'Llegaron en {c}' for c in u.cohorte_trimestre])
    ax.set_ylim(0, 0.65)
    ax.yaxis.set_major_formatter(lambda y, _: _pct(y, 0))
    _grilla(ax)
    _cerrar(fig, ruta, f'Los clientes nuevos de Q3 son más a menudo de una sola compra (% sin segunda compra en {config.HORIZONTE_SEGUNDA_COMPRA} días)',
            'mart_una_sola_vez, clientes con alta 2025. Horizonte fijo de 90 días desde la primera compra; barra = IC 95%')


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
        '6_una_sola_vez.png': lambda r: una_sola_vez(oro['mart_una_sola_vez'], r),
    }
    for nombre, fn in figuras.items():
        fn(carpeta / nombre)
    return sorted(figuras)
