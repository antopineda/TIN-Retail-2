# Databricks notebook source
# MAGIC %md
# MAGIC # 01 · Bronce: guardar lo recibido, tal como llegó
# MAGIC
# MAGIC **Arquitectura en Databricks: ELT.** Primero se *cargan* las fuentes crudas a la plataforma (Volume + tablas Delta
# MAGIC `bronce_*`, todo como texto, sin limpiar) y después se *transforman* con el cómputo de Databricks (notebook 02).
# MAGIC Es el ejemplo de ELT de la cápsula: "en un lakehouse, guardar las fuentes crudas y luego producir plata u oro con su motor".
# MAGIC
# MAGIC | Fuente | Dónde queda |
# MAGIC |---|---|
# MAGIC | `origen_pos.sqlite` (7 tablas) | `/Volumes/.../archivos/origen/` + `bronce_pos_<tabla>` |
# MAGIC | `origen_maestro_productos.csv` | `.../origen/` + `bronce_maestro_productos` |
# MAGIC | `origen_promociones.json` | `.../origen/` + `bronce_promociones` |
# MAGIC | API mindicador.cl (IPC) | `.../bronce/ipc_2025_raw.json` + `bronce_ipc` |
# MAGIC
# MAGIC Cada carga reemplaza la anterior (carga completa): correr dos veces deja las mismas tablas. El registro de cada carga se
# MAGIC **agrega** a `bronce_manifiesto` (historial: qué llegó, con qué huella SHA-256 y si la API respondió).

# COMMAND ----------

# MAGIC %pip install -q "pandas>=2.0" "numpy>=1.24" "matplotlib>=3.5" certifi

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

# MAGIC %run ./_comun

# COMMAND ----------

import hashlib
import json
import shutil
import sqlite3
from datetime import datetime

import config
import etapa_bronce

corrida = datetime.now().isoformat(timespec="seconds")
origen_vol = Path(VOLUMEN) / "origen"
bronce_vol = Path(VOLUMEN) / "bronce"
origen_vol.mkdir(parents=True, exist_ok=True)
bronce_vol.mkdir(parents=True, exist_ok=True)


def sha256(ruta):
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for b in iter(lambda: f.read(1 << 16), b""):
            h.update(b)
    return h.hexdigest()


# 1) Archivos: del repositorio al Volume, verificando que la copia es idéntica
manifiesto = []
for nombre in config.ARCHIVOS_FUENTE:
    desde, hacia = RAIZ / "origen" / nombre, origen_vol / nombre
    shutil.copyfile(desde, hacia)
    if sha256(desde) != sha256(hacia):
        raise RuntimeError(f"La copia de {nombre} en el Volume no es idéntica al original")
    manifiesto.append({"corrida": corrida, "archivo": nombre, "estado": "ok", "origen": f"repositorio/origen/{nombre}",
                       "bytes": hacia.stat().st_size, "sha256": sha256(hacia)})

# 2) API del IPC con su respaldo (misma función que la cadena local: valida la respuesta y, si falla, usa el último snapshot bueno)
config.BRONCE.mkdir(parents=True, exist_ok=True)
ruta_ipc, origen_ipc, estado_ipc = etapa_bronce._snapshot_ipc(refrescar=True)
shutil.copyfile(ruta_ipc, bronce_vol / "ipc_2025_raw.json")
manifiesto.append({"corrida": corrida, "archivo": "ipc_2025_raw.json", "estado": estado_ipc, "origen": origen_ipc,
                   "bytes": ruta_ipc.stat().st_size, "sha256": sha256(ruta_ipc)})
print(f"IPC: {estado_ipc} · {origen_ipc}")
if estado_ipc != "ok":
    print("AVISO: la API no respondió con datos válidos; se usó el último snapshot bueno (S21). Es esperable en Databricks Free Edition (red restringida).")

# COMMAND ----------

# 3) Tablas Delta bronce: todo como texto, sin ninguna limpieza
def como_texto(pdf):
    return celdas(pdf.astype(object).where(pdf.notna(), None), lambda v: None if v is None else str(v))


tablas = []
local_sqlite = "/tmp/retail_g2/origen_pos.sqlite"
Path(local_sqlite).parent.mkdir(parents=True, exist_ok=True)
shutil.copyfile(origen_vol / "origen_pos.sqlite", local_sqlite)       # SQLite se lee desde disco local
with sqlite3.connect(local_sqlite) as con:
    for t in config.TABLAS_POS:
        pdf = como_texto(pd.read_sql(f"select * from {t}", con)).assign(_corrida=corrida)
        tablas.append((guardar(pdf, f"bronce_pos_{t}"), len(pdf)))

maestro = pd.read_csv(origen_vol / "origen_maestro_productos.csv", sep=";", encoding=config.ENCODING_MAESTRO, dtype=str)
tablas.append((guardar(como_texto(maestro).assign(_corrida=corrida), "bronce_maestro_productos"), len(maestro)))

promo = json.loads((origen_vol / "origen_promociones.json").read_text(encoding="utf-8"))
camp = pd.DataFrame([{"campana_id": c.get("campana_id"), "json_crudo": json.dumps(c, ensure_ascii=False), "_corrida": corrida}
                     for c in promo["campanas"]])
tablas.append((guardar(camp, "bronce_promociones"), len(camp)))

ipc = json.loads((bronce_vol / "ipc_2025_raw.json").read_text(encoding="utf-8"))
ipc_df = pd.DataFrame([{"fecha": x["fecha"], "valor": str(x["valor"]), "_origen": origen_ipc, "_corrida": corrida} for x in ipc["serie"]])
tablas.append((guardar(ipc_df, "bronce_ipc"), len(ipc_df)))

tablas.append((guardar(pd.DataFrame(manifiesto), "bronce_manifiesto", modo="append"), len(manifiesto)))
display(pd.DataFrame(tablas, columns=["tabla", "filas"]))
