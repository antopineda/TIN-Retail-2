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
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--fuente', type=Path, default=config.FUENTE_DEFAULT, help='carpeta con las 3 fuentes (por defecto origen/)')
    ap.add_argument('--refrescar-ipc', action='store_true', help='consultar de nuevo la API del IPC')
    ap.add_argument('--simular-falla-api', action='store_true',
                    help='demostración: la API del IPC no responde; la cadena usa el último snapshot bueno y avisa (S21)')
    args = ap.parse_args()
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

    print('[3/6] Oro     (modelo estrella + marts)')
    oro = etapa_oro.ejecutar(pl)
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
    # estado de las fuentes (lo lee el prototipo para avisar si se usó un respaldo)
    fuentes = man[['archivo', 'estado', 'ruta_origen', 'bytes', 'sha256', 'copiado']].assign(corrida=corrida)
    fuentes['ruta_origen'] = fuentes.ruta_origen.str.replace(str(config.RAIZ), '.', regex=False)
    L.escribir_csv(fuentes, config.ORO / 'estado_fuentes.csv')

    print('[5/6] Documentación (diccionario, supuestos, log, resumen)')
    dic = documentacion.ejecutar(oro, log, val)
    sin_desc = dic[dic.descripcion == 'SIN DESCRIPCIÓN']
    if len(sin_desc):
        print(f'      AVISO: {len(sin_desc)} columnas sin descripción: {sin_desc.tabla.str.cat(sin_desc.columna, sep=".").tolist()}')

    print('[6/6] Gráficos')
    for nombre in graficos.ejecutar(oro):
        print(f'      datos/oro/graficos/{nombre}')

    criticas = val[(val.severidad == 'critica') & (val.resultado != 'OK')]
    duracion = time.time() - t0
    k = oro['mart_kpi_resumen'].set_index('kpi').valor
    w = config.VENTANA_PRINCIPAL
    hist = pd.DataFrame([{'corrida': corrida, 'duracion_s': round(duracion, 1), 'pruebas': n_tot, 'pruebas_ok': n_ok,
                          'fallas_que_bloquean': len(criticas), 'estado_ipc': man.estado.iloc[-1],
                          f'retencion_q4_{w}d': round(k[f'retencion_Q4_{w}d'], 4),
                          f'margen_anual_en_riesgo_{w}d_clp': round(k[f'margen_anual_en_riesgo_{w}d'])}])
    ruta_h = config.ORO / 'historial_corridas.csv'
    if ruta_h.exists():
        hist = pd.concat([pd.read_csv(ruta_h, encoding=config.ENCODING_SALIDA), hist], ignore_index=True)
    L.escribir_csv(hist, ruta_h)
    print(f'\nListo en {duracion:.1f} s. Salidas en {config.DATOS}')
    print(f'Retención Q4 2025 ({w} días): {k[f"retencion_Q4_{w}d"]:.1%}  ·  pruebas {n_ok}/{n_tot}  ·  IPC: {man.estado.iloc[-1]}')
    if len(criticas):
        print(f'ERROR: {len(criticas)} validaciones críticas fallaron: {criticas.id.tolist()}')
        sys.exit(1)


if __name__ == '__main__':
    main()
