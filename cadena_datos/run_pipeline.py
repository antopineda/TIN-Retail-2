# -*- coding: utf-8 -*-
"""
Cadena de datos ejecutable — Multitienda del Sur (Retail, grupo_2).

Uso (desde la raíz del repositorio):
    python cadena_datos/run_pipeline.py
    python cadena_datos/run_pipeline.py --refrescar-ipc          # vuelve a consultar la API del IPC
    python cadena_datos/run_pipeline.py --fuente RUTA             # otra carpeta de origen (por defecto: origen/)

Etapas: bronce (copia fiel) -> plata (limpieza R01..R27) -> oro (estrella + marts) -> validaciones -> documentación -> gráficos.
Termina con código 1 si alguna validación crítica falla.
"""
import argparse
import sys
import time
from pathlib import Path

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
from limpieza import LogCalidad  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--fuente', type=Path, default=config.FUENTE_DEFAULT, help='carpeta con las 3 fuentes (por defecto origen/)')
    ap.add_argument('--refrescar-ipc', action='store_true', help='consultar de nuevo la API del IPC')
    args = ap.parse_args()
    t0 = time.time()

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

    print('[4/6] Validaciones')
    val = validaciones.ejecutar(pl, oro, log)
    for r in val.itertuples():
        marca = 'OK   ' if r.resultado == 'OK' else ('FALLA' if r.severidad == 'critica' else 'AVISO')
        print(f'      {marca} {r.id} {r.validacion}' + (f'  [{r.detalle}]' if r.resultado != 'OK' else ''))

    print('[5/6] Documentación (diccionario, supuestos, log, resumen)')
    dic = documentacion.ejecutar(oro, log, val)
    sin_desc = dic[dic.descripcion == 'SIN DESCRIPCIÓN']
    if len(sin_desc):
        print(f'      AVISO: {len(sin_desc)} columnas sin descripción: {sin_desc.tabla.str.cat(sin_desc.columna, sep=".").tolist()}')

    print('[6/6] Gráficos')
    for nombre in graficos.ejecutar(oro):
        print(f'      datos/oro/graficos/{nombre}')

    criticas = val[(val.severidad == 'critica') & (val.resultado != 'OK')]
    print(f'\nListo en {time.time() - t0:.1f} s. Salidas en {config.DATOS}')
    if len(criticas):
        print(f'ERROR: {len(criticas)} validaciones críticas fallaron: {criticas.id.tolist()}')
        sys.exit(1)


if __name__ == '__main__':
    main()
