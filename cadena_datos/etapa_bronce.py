# -*- coding: utf-8 -*-
"""
BRONCE: copia fiel de las fuentes, sin ninguna transformación.
- Copia los 3 archivos de origen/ y registra su hash SHA-256 (manifiesto).
- Guarda un snapshot de la API del IPC (para que la cadena sea reproducible sin internet).
"""
import hashlib
import json
import shutil
import ssl
import urllib.request
from datetime import datetime

import pandas as pd

import config


def _sha256(ruta):
    h = hashlib.sha256()
    with open(ruta, 'rb') as f:
        for bloque in iter(lambda: f.read(1 << 16), b''):
            h.update(bloque)
    return h.hexdigest()


def _contexto_ssl():
    """Python de python.org en macOS no trae certificados raíz: si certifi está instalado, se usa."""
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def _snapshot_ipc(refrescar):
    """Devuelve (ruta, origen, estado). estado: 'ok' (API o snapshot de esta máquina) o 'respaldo' (la API falló)."""
    destino = config.BRONCE / 'ipc_2025_raw.json'
    if destino.exists() and not refrescar:
        meta = json.loads(destino.read_text(encoding='utf-8')).get('_metadatos_cadena', {})
        return destino, f'snapshot existente en bronce ({meta.get("origen", "?")})', meta.get('estado', 'ok')
    try:
        with urllib.request.urlopen(config.IPC_URL, timeout=config.IPC_TIMEOUT_S, context=_contexto_ssl()) as r:
            crudo = json.load(r)
        origen, estado = f'API {config.IPC_URL}', 'ok'
    except Exception as e:  # sin internet, API caída o certificado
        motivo = e.__class__.__name__
        if config.IPC_SNAPSHOT_VERSIONADO.exists():
            crudo = json.loads(config.IPC_SNAPSHOT_VERSIONADO.read_text(encoding='utf-8'))
            origen = f'snapshot versionado {config.IPC_SNAPSHOT_VERSIONADO.name} (API no respondió: {motivo})'
        else:
            crudo = {'serie': [{'fecha': f'2025-{m:02d}-01T03:00:00.000Z', 'valor': v}
                               for m, v in config.IPC_RESPALDO_2025.items()]}
            origen = f'respaldo embebido en config.py (API no respondió: {motivo})'
        estado = 'respaldo'
    crudo['_metadatos_cadena'] = {'origen': origen, 'estado': estado, 'consultado': datetime.now().isoformat(timespec='seconds')}
    destino.write_text(json.dumps(crudo, ensure_ascii=False, indent=1), encoding='utf-8')
    return destino, origen, estado


def ejecutar(fuente, refrescar_ipc=False):
    config.BRONCE.mkdir(parents=True, exist_ok=True)
    manifiesto = []
    for nombre in config.ARCHIVOS_FUENTE:
        origen = fuente / nombre
        if not origen.exists():
            raise FileNotFoundError(f'No se encontró la fuente {origen}')
        destino = config.BRONCE / nombre
        shutil.copy2(origen, destino)
        h_o, h_d = _sha256(origen), _sha256(destino)
        if h_o != h_d:
            raise RuntimeError(f'La copia de {nombre} no es idéntica al original')
        manifiesto.append({'archivo': nombre, 'ruta_origen': str(origen), 'estado': 'ok', 'bytes': destino.stat().st_size,
                           'sha256': h_d, 'copiado': datetime.now().isoformat(timespec='seconds')})
    ruta_ipc, origen_ipc, estado_ipc = _snapshot_ipc(refrescar_ipc)
    manifiesto.append({'archivo': ruta_ipc.name, 'ruta_origen': origen_ipc, 'estado': estado_ipc, 'bytes': ruta_ipc.stat().st_size,
                       'sha256': _sha256(ruta_ipc), 'copiado': datetime.now().isoformat(timespec='seconds')})
    df = pd.DataFrame(manifiesto)
    df.to_csv(config.BRONCE / 'manifiesto_bronce.csv', index=False, encoding=config.ENCODING_SALIDA, lineterminator='\n')
    return df
