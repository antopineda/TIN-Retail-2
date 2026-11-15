# -*- coding: utf-8 -*-
"""
Prototipo — Multitienda del Sur: ¿retenemos a nuestros clientes o los reponemos?

Uso (desde la raíz del repositorio, después de correr la cadena):
    streamlit run prototipo/app.py

Lee solo datos/oro/ (lo que dejó la última corrida) y las definiciones de cadena_datos/metricas.py.
No calcula ninguna métrica por su cuenta: si la cadena vuelve a correr, la pantalla se actualiza al recargar.
"""
import sys
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / 'cadena_datos'))
import config  # noqa: E402
import metricas as M  # noqa: E402

ORO = config.ORO
VINO, GRIS, GRIS_CLARO = '#AD2C55', '#8A8A8A', '#D9D9D9'
TRIMESTRES = {'2025Q2': 'Q2 2025 (abr–jun)', '2025Q3': 'Q3 2025 (jul–sep)', '2025Q4': 'Q4 2025 (oct–dic)'}
VENTANAS = {90: '90 días (oficial)', 30: '30 días (alternativa: regla de un mes)', 180: '180 días'}
CORTES = {'Tienda principal': 'Local', 'Formato principal': 'Formato', 'Macrozona principal': 'Macrozona',
          'Segmento': 'Segmento de la tarjeta (Clásico, Plus, Black)', 'Compras ene–sep (comportamiento; leer solo Q4)': 'Compras ene–sep (comportamiento)'}

st.set_page_config(page_title='Retención de clientes · Multitienda del Sur', page_icon='🛒', layout='wide')


# ----------------------------------------------------------------- formato (unidades siempre explícitas)
def pct(x, dec=1):
    return '—' if pd.isna(x) else f'{x * 100:.{dec}f}%'.replace('.', ',')


def clp(x):
    if pd.isna(x):
        return '—'
    if abs(x) >= 1e6:
        return f'CLP {x / 1e6:,.2f} millones'.replace(',', 'X').replace('.', ',').replace('X', '.')
    return f'CLP {x:,.0f}'.replace(',', '.')


def num(x):
    return f'{x:,.0f}'.replace(',', '.')


@st.cache_data
def cargar(_marca):
    leer = lambda n, **kw: pd.read_csv(ORO / f'{n}.csv', encoding='utf-8-sig', **kw)
    return {n: leer(n) for n in ['mart_retencion', 'mart_valor_riesgo', 'mart_kpi_resumen', 'mart_episodios_inactividad',
                                  'mart_campanas', 'mart_perfil_local', 'mart_cobertura', 'validaciones', 'estado_fuentes',
                                  'historial_corridas']}


faltan = [n for n in ['mart_retencion', 'validaciones', 'estado_fuentes'] if not (ORO / f'{n}.csv').exists()]
if faltan:
    st.error('No hay datos de la cadena. Corre primero:  python cadena_datos/run_pipeline.py')
    st.stop()
D = cargar((ORO / 'historial_corridas.csv').stat().st_mtime)   # la caché se invalida cuando la cadena vuelve a correr
mret, kpi = D['mart_retencion'], D['mart_kpi_resumen'].set_index('kpi').valor
val, fuentes, hist = D['validaciones'], D['estado_fuentes'], D['historial_corridas']
ultima = hist.iloc[-1]

# ----------------------------------------------------------------- avisos de la corrida
bloquean = val[(val.accion == 'bloquea') & (val.resultado != 'OK')]
if len(bloquean):
    st.error(f'La última corrida NO pasó {len(bloquean)} prueba(s) que bloquean la publicación: '
             f'{", ".join(bloquean.id)}. Las cifras de esta pantalla no están certificadas.')
for f in fuentes[fuentes.estado != 'ok'].itertuples():
    st.warning(f'Fuente {f.archivo}: la API no respondió en la última corrida; se usó el último dato bueno guardado '
               f'({f.ruta_origen}). Solo afecta la venta deflactada; la retención y el margen no cambian.')

# ----------------------------------------------------------------- título, período y filtros
st.markdown('### ¿Estamos reteniendo a nuestros clientes o solo reponiéndolos?')
st.caption('Multitienda del Sur · clientes con tarjeta (compras identificadas) · 10 locales, incluida la Tienda Online · 2025')

c1, c2, c3 = st.columns([1.2, 1, 1.4])
w = c1.radio('Cliente activo = compró en los últimos…', list(VENTANAS), format_func=VENTANAS.get, horizontal=False)
trimestre = c2.selectbox('Trimestre', list(TRIMESTRES), index=2, format_func=TRIMESTRES.get)
c3.info(f'**Regla de lectura.** {M.regla_lectura(w)}  \n'
        f'Retención = retenidos / activos al inicio. Q1 no se mide: sin datos de 2024 no se sabe quién estaba activo al 1 de enero.')

r = M.retencion(mret, trimestre, w)
r_ofi = M.retencion(mret, trimestre, config.VENTANA_PRINCIPAL)
r_alt = M.retencion(mret, trimestre, 30)
idx = list(TRIMESTRES).index(trimestre)
r_prev = M.retencion(mret, list(TRIMESTRES)[idx - 1], w) if idx > 0 else None

# ----------------------------------------------------------------- cifra clave
st.divider()
k1, k2, k3, k4 = st.columns([1.3, 1, 1.2, 1])
k1.metric(f'Retención {TRIMESTRES[trimestre][:7]} · {w} días', pct(r.tasa_retencion),
          delta=(f'{(r.tasa_retencion - r_prev.tasa_retencion) * 100:+.1f} pp vs trimestre anterior'.replace('.', ',')
                 if r_prev is not None else None))
k1.caption(f'{num(r.retenidos)} de {num(r.activos_inicio)} clientes activos al inicio siguieron activos. '
           f'Oficial (90 d): **{pct(r_ofi.tasa_retencion)}** · alternativa (30 d): **{pct(r_alt.tasa_retencion)}**')
k2.metric('Clientes nuevos por cada perdido', f'{r.indice_reposicion:.2f}'.replace('.', ',') if pd.notna(r.indice_reposicion) else '—')
k2.caption(f'{num(r.nuevos)} nuevos vs {num(r.perdidos)} perdidos en el trimestre. Menor que 1 = la base se achica.')
riesgo = D['mart_valor_riesgo'].set_index('ventana_dias').loc[w]
if trimestre == '2025Q4':
    k3.metric('Margen anual en riesgo (clientes perdidos en Q4)', clp(riesgo.margen_anual_en_riesgo))
    k3.caption(f'CLP nominales 2025 de margen bruto sin IVA, por año. Cada punto de retención vale '
               f'{clp(riesgo.margen_anual_1pp_retencion)} de margen al año.')
else:
    k3.metric('Margen anual en riesgo', 'Solo Q4')
    k3.caption('El valor en riesgo se calcula para el último trimestre del año.')
k4.metric('Cobertura del análisis', pct(1 - kpi.pct_boletas_fuera_de_retencion))
k4.caption(f'de las boletas del origen ({pct(kpi.pct_venta_2025_en_retencion)} de la venta 2025). '
           f'Quedan fuera las anónimas, duplicadas, de 2026 y solo devoluciones.')

# ----------------------------------------------------------------- gráfico que explica la cifra
st.divider()
g1, g2 = st.columns([1, 1.15])
tri = mret[(mret.corte == 'Total') & (mret.periodo_tipo == 'trimestre') & (mret.ventana_dias == w) & mret.periodo.isin(TRIMESTRES)].copy()
tri['Trimestre'] = tri.periodo.map(lambda p: TRIMESTRES[p][:7])
tri['Retención'] = tri.tasa_retencion
with g1:
    st.markdown(f'**Retención por trimestre (% de clientes, ventana {w} días)**')
    base = alt.Chart(tri).encode(x=alt.X('Trimestre:N', title=None, sort=None))
    linea = base.mark_line(point=True, color=GRIS).encode(
        y=alt.Y('Retención:Q', axis=alt.Axis(format='%', title='% de clientes retenidos'), scale=alt.Scale(domain=[0, 1])))
    marca = base.transform_filter(alt.datum.periodo == trimestre).mark_point(size=160, filled=True, color=VINO).encode(y='Retención:Q')
    etiquetas = base.mark_text(dy=-14, color='#333').encode(y='Retención:Q', text=alt.Text('Retención:Q', format='.1%'))
    st.altair_chart(linea + marca + etiquetas, use_container_width=True)
with g2:
    st.markdown('**Clientes que entran y salen por trimestre (n° de clientes)**')
    flujo = tri.melt(id_vars='Trimestre', value_vars=['nuevos', 'perdidos', 'reactivados'], var_name='Tipo', value_name='Clientes')
    flujo['Tipo'] = flujo.Tipo.map({'nuevos': 'Nuevos', 'perdidos': 'Perdidos', 'reactivados': 'Reactivados'})
    barras = alt.Chart(flujo).mark_bar().encode(
        x=alt.X('Trimestre:N', title=None, sort=None), xOffset='Tipo:N',
        y=alt.Y('Clientes:Q', title='n° de clientes'),
        color=alt.Color('Tipo:N', scale=alt.Scale(domain=['Nuevos', 'Perdidos', 'Reactivados'], range=['#555555', VINO, GRIS_CLARO]),
                        legend=alt.Legend(orient='top', title=None)),
        tooltip=['Trimestre', 'Tipo', 'Clientes'])
    st.altair_chart(barras + barras.mark_text(dy=-6, color='#333').encode(text='Clientes:Q'), use_container_width=True)

# ----------------------------------------------------------------- corte por la dimensión principal
st.divider()
cc1, cc2 = st.columns([2, 1])
corte = cc2.selectbox('Ver por', list(CORTES), format_func=CORTES.get)
cc1.markdown(f'**Retención {TRIMESTRES[trimestre][:7]} por {CORTES[corte].lower()} (%, ventana {w} días) con su intervalo de confianza del 95%**')
cx = mret[(mret.corte == corte) & (mret.periodo == trimestre) & (mret.ventana_dias == w) & (mret.activos_inicio > 0)].copy()
cx['Grupo'] = cx.valor
cx['Lectura'] = cx.se_puede_rankear.map({True: f'{config.UMBRAL_MUESTRA_PEQUENA} o más clientes: comparable',
                                         False: f'Menos de {config.UMBRAL_MUESTRA_PEQUENA} clientes: no ordenar, mirar el intervalo'})
cx = cx.sort_values('tasa_retencion')
total = r.tasa_retencion
alto = max(180, 34 * len(cx))
y = alt.Y('Grupo:N', sort=cx.Grupo.tolist()[::-1], title=None, axis=alt.Axis(labelLimit=260))
puntos = alt.Chart(cx).mark_point(filled=True, size=110).encode(
    x=alt.X('tasa_retencion:Q', title='% de clientes retenidos', axis=alt.Axis(format='%'), scale=alt.Scale(domain=[0, 1])), y=y,
    color=alt.Color('Lectura:N', scale=alt.Scale(range=[VINO, GRIS]), legend=alt.Legend(orient='bottom', title=None, labelLimit=500)),
    tooltip=[alt.Tooltip('Grupo:N'), alt.Tooltip('tasa_retencion:Q', format='.1%', title='Retención'),
             alt.Tooltip('ic95_inf:Q', format='.1%', title='IC 95% desde'), alt.Tooltip('ic95_sup:Q', format='.1%', title='IC 95% hasta'),
             alt.Tooltip('activos_inicio:Q', title='Activos al inicio (n°)'), alt.Tooltip('perdidos:Q', title='Perdidos (n°)')])
ic = alt.Chart(cx).mark_rule(color=GRIS, strokeWidth=2).encode(x='ic95_inf:Q', x2='ic95_sup:Q', y=y)
n_txt = alt.Chart(cx).mark_text(align='left', dx=6, color=GRIS).encode(x=alt.value(0), y=y, text=alt.Text('activos_inicio:Q'))
ref = alt.Chart(pd.DataFrame({'x': [total]})).mark_rule(strokeDash=[4, 4], color='#333').encode(x='x:Q')
st.altair_chart((ic + puntos + ref).properties(height=alto), use_container_width=True)
st.caption(f'Línea punteada: total de la cadena ({pct(total)}). Barra gris: intervalo de confianza del 95% (Wilson). '
           f'Un local con pocos clientes puede subir o bajar 15 puntos por azar: si su barra cruza la línea punteada, '
           f'no es distinto del total. Cada cliente cuenta en su local principal (donde más compró en 2025).')
if corte.startswith('Compras'):
    st.caption('Este corte usa las compras de enero a septiembre, por eso solo tiene sentido en Q4. '
               'Separa mucho más que el segmento de la tarjeta: el cliente con una sola compra es el que se pierde.')

# ----------------------------------------------------------------- la decisión: contactar antes de perder al cliente
st.divider()
st.markdown('**La decisión: ¿a los cuántos días sin comprar conviene contactar al cliente, cuánto cuesta y cuánto margen recupera?**')
W0 = config.VENTANA_PRINCIPAL
st.caption(f'Simula haber contactado durante 2025 a cada cliente con tarjeta que cumplió N días sin comprar. '
           f'Un cliente se da por perdido al cumplir {W0} días: la definición oficial, sin importar la ventana elegida arriba '
           f'(con 30 días se daría por perdidos a clientes que vuelven solos). Montos en CLP nominales sin IVA, por año.')
s1, s2, s3, s4 = st.columns(4)
paso = 5
dia_max = W0 - paso
dia = s1.slider('Contactar al cumplir (días sin comprar)', 15, dia_max, min(config.CONTACTO_DIA_DEFECTO, dia_max), step=paso)
envio = s2.number_input('Costo por contacto (CLP)', 0, 5000, config.CONTACTO_COSTO_ENVIO_CLP, step=10)
cupon = s3.slider('Cupón de regreso (% del ticket)', 0, 30, config.CONTACTO_CUPON_PCT)
tasa = s4.slider('Clientes recuperados (% de los que se iban)', 0, 50, int(config.CONTACTO_TASA_RECUPERACION * 100)) / 100
caso = M.caso_contacto(D['mart_episodios_inactividad'], dia, W0, envio, cupon, tasa)
d1, d2, d3, d4 = st.columns(4)
d1.metric('Contactos en el año', num(caso['contactados']))
d1.caption(f'{pct(caso["pct_contactos_desperdiciados"], 0)} habría vuelto solo (el cupón se regala).')
d2.metric('Costo de la acción', clp(caso['costo_total']))
d2.caption('Envíos + cupones usados (también por los que habrían vuelto solos).')
d3.metric('Margen recuperado', clp(caso['margen_recuperado']))
d3.caption(f'{num(caso["recuperados"])} de {num(caso["se_pierden"])} clientes que se iban a perder.')
d4.metric('Resultado neto', clp(caso['resultado_neto']),
          delta='paga su costo' if caso['resultado_neto'] > 0 else 'pierde plata', delta_color='normal' if caso['resultado_neto'] > 0 else 'inverse')
d4.caption(f'Paga su costo si recupera al menos el **{pct(caso["tasa_equilibrio"])}** de los que se iban.')
curva = pd.DataFrame([M.caso_contacto(D['mart_episodios_inactividad'], d, W0, envio, cupon, tasa) for d in range(15, W0, 5)])
lin = alt.Chart(curva).mark_line(point=True, color=GRIS).encode(
    x=alt.X('dia_contacto:Q', title='Día de contacto (días sin comprar)', axis=alt.Axis(values=list(range(15, W0, 5)))),
    y=alt.Y('resultado_neto:Q', title='Resultado neto (CLP por año)', axis=alt.Axis(format=',.0f')),
    tooltip=[alt.Tooltip('dia_contacto:Q', title='Día'), alt.Tooltip('resultado_neto:Q', format=',.0f', title='CLP'),
             alt.Tooltip('tasa_equilibrio:Q', format='.1%', title='Tasa de equilibrio')])
cero = alt.Chart(pd.DataFrame({'y': [0]})).mark_rule(color='#333').encode(y='y:Q')
elegido = alt.Chart(pd.DataFrame({'x': [dia]})).mark_rule(color=VINO, strokeDash=[4, 4]).encode(x='x:Q')
st.altair_chart((lin + cero + elegido).properties(height=220), use_container_width=True)
st.caption('Supuestos S18 (costo) y S19 (recuperación): no están medidos. La tasa de recuperación real solo se conoce con un piloto con grupo de control.')

# ----------------------------------------------------------------- detalle
st.divider()
with st.expander('Detalle por local: quién retiene, cuántos clientes y por qué', expanded=False):
    pl_ = D['mart_perfil_local'].copy()
    det = mret[(mret.corte == 'Tienda principal') & (mret.periodo == trimestre) & (mret.ventana_dias == w)][
        ['valor', 'activos_inicio', 'retenidos', 'perdidos', 'nuevos', 'reactivados', 'tasa_retencion', 'ic95_inf', 'ic95_sup']]
    det = det.merge(pl_[['tienda_principal', 'pct_una_sola_compra_ene_sep', 'ticket_promedio_ene_sep', 'margen_ene_sep_por_cliente']],
                    left_on='valor', right_on='tienda_principal', how='left').drop(columns='tienda_principal')
    det = det.sort_values('tasa_retencion')
    st.dataframe(det.rename(columns={
        'valor': 'Local', 'activos_inicio': 'Activos al inicio (n°)', 'retenidos': 'Retenidos (n°)', 'perdidos': 'Perdidos (n°)',
        'nuevos': 'Nuevos (n°)', 'reactivados': 'Reactivados (n°)', 'tasa_retencion': 'Retención (%)', 'ic95_inf': 'IC 95% desde',
        'ic95_sup': 'IC 95% hasta', 'pct_una_sola_compra_ene_sep': 'Una sola compra ene–sep (%)',
        'ticket_promedio_ene_sep': 'Ticket promedio ene–sep (CLP)', 'margen_ene_sep_por_cliente': 'Margen por cliente ene–sep (CLP)'}),
        hide_index=True, use_container_width=True,
        column_config={c: st.column_config.NumberColumn(format='percent') for c in
                       ['Retención (%)', 'IC 95% desde', 'IC 95% hasta', 'Una sola compra ene–sep (%)']} |
                      {c: st.column_config.NumberColumn(format='localized') for c in
                       ['Ticket promedio ene–sep (CLP)', 'Margen por cliente ene–sep (CLP)']})
    st.caption('El perfil (una sola compra, ticket, margen) es de los clientes activos al 1-oct-2025 con ventana de 90 días.')

with st.expander('¿Las campañas de 2025 retuvieron clientes?', expanded=False):
    ca = D['mart_campanas'].copy()
    st.dataframe(ca[['accion', 'grupo', 'clientes', 'volvieron_90d', 'pct_volvio_90d', 'ic95_inf', 'ic95_sup', 'descuento_otorgado_sin_iva']].rename(columns={
        'accion': 'Acción', 'grupo': 'Grupo', 'clientes': 'Clientes (n°)', 'volvieron_90d': 'Volvieron en 90 días (n°)',
        'pct_volvio_90d': 'Volvieron (%)', 'ic95_inf': 'IC 95% desde', 'ic95_sup': 'IC 95% hasta',
        'descuento_otorgado_sin_iva': 'Descuento entregado (CLP sin IVA)'}), hide_index=True, use_container_width=True,
        column_config={c: st.column_config.NumberColumn(format='percent') for c in ['Volvieron (%)', 'IC 95% desde', 'IC 95% hasta']} |
                      {'Descuento entregado (CLP sin IVA)': st.column_config.NumberColumn(format='localized')})
    st.caption('Comparación, no efecto causal: no hubo grupo de control y quien usa una promoción ya compra más seguido.')

with st.expander('Calidad de los datos de esta corrida', expanded=False):
    st.dataframe(val[['id', 'validacion', 'accion', 'resultado', 'detalle']].rename(columns={
        'id': 'Prueba', 'validacion': 'Qué verifica', 'accion': 'Si falla', 'resultado': 'Resultado', 'detalle': 'Detalle'}),
        hide_index=True, use_container_width=True)
    st.dataframe(D['mart_cobertura'][['motivo', 'boletas', 'boletas_restantes', 'pct_del_origen']].rename(columns={
        'motivo': 'Paso', 'boletas': 'Boletas (n°)', 'boletas_restantes': 'Quedan (n°)', 'pct_del_origen': '% del origen'}),
        hide_index=True, use_container_width=True, column_config={'% del origen': st.column_config.NumberColumn(format='percent')})

# ----------------------------------------------------------------- pie: fuente, actualización, dueño
n_ok = int((val.resultado == 'OK').sum())
st.divider()
st.caption(
    f'**Fuente:** sistema de caja (origen_pos.sqlite), maestro de productos, campañas 2025 e IPC de mindicador.cl, procesados por la cadena '
    f'bronce → plata → oro.  ·  **Actualizado:** {pd.Timestamp(ultima.corrida):%d-%m-%Y %H:%M}  ·  '
    f'**Pruebas de calidad:** {n_ok} de {len(val)} en verde  ·  **Dueño de la métrica:** {config.DUENO_METRICA}  ·  '
    f'**Dueño del dato:** {config.DUENO_DATO}  ·  **Definiciones** (ventana, cliente nuevo, Tienda Online) confirmadas por la contraparte '
    f'en el correo del 13-10-2026.')
