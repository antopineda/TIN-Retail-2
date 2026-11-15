# -*- coding: utf-8 -*-
"""
Cadena de datos ejecutable — Multitienda del Sur (Retail, grupo_2).

Uso (desde la raíz del repositorio):
    python cadena_datos/run_pipeline.py
    python cadena_datos/run_pipeline.py --refrescar-ipc          # vuelve a consultar la API del IPC
    python cadena_datos/run_pipeline.py --fuente RUTA             # otra carpeta de origen (por defecto: origen/)
    python cadena_datos/run_pipeline.py --simular-falla-api       # demostración: la API del IPC no responde

Etapas: bronce (copia fiel) -> plata (limpieza R01..R27) -> oro (estrella + marts) -> pruebas de calidad -> documentación -> gráficos.
Carga completa e idempotente: cada corrida reescribe bronce, plata y oro desde el origen (no hay duplicados ni registros perdidos).
Termina con código 1 si alguna prueba que bloquea falla. Prototipo: streamlit run prototipo/app.py
"""
import argparse
import sys
import time
from types import SimpleNamespace
from datetime import datetime
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

import config  # noqa: E402
import documentacion  # noqa: E402
import etapa_bronce  # noqa: E402
import etapa_oro  # noqa: E402
import etapa_plata  # noqa: E402
import graficos  # noqa: E402
import validaciones  # noqa: E402
import limpieza as L  # noqa: E402
from limpieza import LogCalidad  # noqa: E402


def main():
    """Línea de comandos: python cadena_datos/run_pipeline.py [opciones]. Termina con código 1 si no se publica."""
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--fuente', type=Path, default=config.FUENTE_DEFAULT, help='carpeta con las 3 fuentes (por defecto origen/)')
    ap.add_argument('--refrescar-ipc', action='store_true', help='consultar de nuevo la API del IPC')
    ap.add_argument('--simular-falla-api', action='store_true',
                    help='demostración: la API del IPC no responde; la cadena usa el último snapshot bueno y avisa (S21)')
    ap.add_argument('--simular-falla-calidad', action='store_true',
                    help='demostración: duplica una boleta en el hecho; la prueba M01 bloquea y oro NO se publica')
    a = ap.parse_args()
    r = ejecutar(a.fuente, a.refrescar_ipc, a.simular_falla_api, a.simular_falla_calidad)
    if not r['publicada']:
        sys.exit(1)


def ejecutar(fuente=config.FUENTE_DEFAULT, refrescar_ipc=False, simular_falla_api=False, simular_falla_calidad=False):
    """Corre la cadena completa. La usan la línea de comandos (main) y los notebooks de Databricks (databricks/).
    Devuelve {'publicada', 'corrida', 'oro', 'plata', 'validaciones', 'manifiesto'}; oro solo se escribe si publicada."""
    args = SimpleNamespace(fuente=Path(fuente), refrescar_ipc=refrescar_ipc, simular_falla_api=simular_falla_api,
                           simular_falla_calidad=simular_falla_calidad)
    if args.simular_falla_api:
        config.IPC_URL = 'https://api-inexistente.invalid/ipc/2025'
        args.refrescar_ipc = True
    t0 = time.time()
    corrida = datetime.now().isoformat(timespec='seconds')

    print(f'[1/6] Bronce  <- {args.fuente}')
    man = etapa_bronce.ejecutar(args.fuente, args.refrescar_ipc)
    for r in man.itertuples():
        print(f'      {r.archivo:<32} {r.bytes:>9,} bytes  sha256 {r.sha256[:12]}…  ({r.ruta_origen if "ipc" in r.archivo else "copia"})')

    print('[2/6] Plata   (reglas de limpieza)')
    log = LogCalidad()
    pl = etapa_plata.ejecutar(log)
    for t in ['boletas', 'boleta_detalle', 'clientes', 'productos']:
        print(f'      {t:<16} {len(pl[t]):>7,} filas')

    print('[3/6] Oro     (modelo estrella + marts, en memoria hasta pasar las pruebas)')
    oro = etapa_oro.ejecutar(pl)
    if args.simular_falla_calidad:
        fb = oro['fact_venta_boleta']
        oro['fact_venta_boleta'] = pd.concat([fb, fb.iloc[[0]]], ignore_index=True)
    for t, df in oro.items():
        if not t.startswith('_'):
            print(f'      {t:<20} {len(df):>7,} filas')

    print('[4/6] Pruebas de calidad')
    val = validaciones.ejecutar(pl, oro, log)
    val['corrida'] = corrida
    for r in val.itertuples():
        marca = 'OK   ' if r.resultado == 'OK' else ('FALLA' if r.severidad == 'critica' else 'AVISO')
        print(f'      {marca} {r.id} {r.validacion}' + (f'  [{r.detalle}]' if r.resultado != 'OK' else ''))
    n_ok, n_tot = int((val.resultado == 'OK').sum()), len(val)
    print(f'      -> {n_ok} de {n_tot} pruebas en verde')
    criticas = val[(val.severidad == 'critica') & (val.resultado != 'OK')]
    publicada = len(criticas) == 0
    w = config.VENTANA_PRINCIPAL
    k = oro['mart_kpi_resumen'].set_index('kpi').valor

    # historial de pruebas: cada prueba de cada corrida queda guardada (no solo impresa)
    _anexar(val, config.ORO / 'historial_pruebas.csv')

    if publicada:
        print('[5/6] Publicación en oro + documentación (diccionario, supuestos, log, resumen)')
        etapa_oro.publicar(oro)
        fuentes = man[['archivo', 'estado', 'ruta_origen', 'bytes', 'sha256', 'copiado']].assign(corrida=corrida)
        fuentes['ruta_origen'] = fuentes.ruta_origen.str.replace(str(config.RAIZ), '.', regex=False)
        L.escribir_csv(fuentes, config.ORO / 'estado_fuentes.csv')   # el prototipo lo lee para avisar si se usó un respaldo
        dic = documentacion.ejecutar(oro, log, val)
        sin_desc = dic[dic.descripcion == 'SIN DESCRIPCIÓN']
        if len(sin_desc):
            print(f'      AVISO: {len(sin_desc)} columnas sin descripción: {sin_desc.tabla.str.cat(sin_desc.columna, sep=".").tolist()}')
        print('[6/6] Gráficos')
        for nombre in graficos.ejecutar(oro):
            print(f'      datos/oro/graficos/{nombre}')
    else:
        # cuarentena: oro y el prototipo quedan con la última corrida buena; las pruebas fallidas quedan para revisar
        cuarentena = config.DATOS / 'cuarentena'
        L.escribir_csv(val, cuarentena / f'validaciones_{corrida.replace(":", "")}.csv')
        print(f'[5/6] NO SE PUBLICA: {len(criticas)} prueba(s) que bloquean fallaron. datos/oro/ queda con la última corrida buena.')
        print(f'      Detalle en {cuarentena}/')
        print('[6/6] Gráficos: no se regeneran')

    duracion = time.time() - t0
    _anexar(pd.DataFrame([{'corrida': corrida, 'publicada': publicada, 'duracion_s': round(duracion, 1), 'pruebas': n_tot,
                           'pruebas_ok': n_ok, 'fallas_que_bloquean': len(criticas),
                           'pruebas_fallidas': '|'.join(val.loc[val.resultado != 'OK', 'id']), 'estado_ipc': man.estado.iloc[-1],
                           f'retencion_q4_{w}d': round(k[f'retencion_Q4_{w}d'], 4),
                           f'margen_anual_en_riesgo_{w}d_clp': round(k[f'margen_anual_en_riesgo_{w}d'])}]),
            config.ORO / 'historial_corridas.csv')
    print(f'\nListo en {duracion:.1f} s. Salidas en {config.DATOS}')
    print(f'Retención Q4 2025 ({w} días): {k[f"retencion_Q4_{w}d"]:.1%}  ·  pruebas {n_ok}/{n_tot}  ·  IPC: {man.estado.iloc[-1]}'
          f'  ·  {"PUBLICADA" if publicada else "NO PUBLICADA"}')
    if not publicada:
        print(f'ERROR: {len(criticas)} pruebas que bloquean fallaron: {criticas.id.tolist()}')
    return {'publicada': publicada, 'corrida': corrida, 'oro': oro, 'plata': pl, 'validaciones': val, 'manifiesto': man}


def _anexar(df, ruta):
    """Agrega filas a un registro histórico (nunca lo reescribe desde cero)."""
    if ruta.exists():
        df = pd.concat([pd.read_csv(ruta, encoding=config.ENCODING_SALIDA), df], ignore_index=True)
    L.escribir_csv(df, ruta)


if __name__ == '__main__':
    main()
