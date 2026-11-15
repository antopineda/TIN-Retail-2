# Databricks notebook source
# MAGIC %md
# MAGIC # 02 · Plata y oro: transformar en la plataforma y publicar solo si pasan las pruebas
# MAGIC
# MAGIC Corre **el mismo código** de `cadena_datos/` que la versión local (una sola definición de cada regla y de cada métrica:
# MAGIC `cadena_datos/metricas.py`). Lo único que cambia es dónde se leen las fuentes (el Volume que llenó el notebook 01)
# MAGIC y dónde se guardan los resultados (tablas Delta).
# MAGIC
# MAGIC 1. La cadena arma plata y oro y corre las 36 pruebas de calidad.
# MAGIC 2. **Si todas las que bloquean pasan:** reemplaza las tablas `plata_*` y oro (carga completa, idempotente).
# MAGIC 3. **Si alguna falla:** no toca ninguna tabla de plata ni de oro (el tablero sigue con la última corrida buena),
# MAGIC    guarda las pruebas fallidas en `cuarentena_validaciones` y el job termina en error.
# MAGIC 4. En los dos casos agrega la corrida a `historial_corridas` y sus pruebas a `historial_pruebas`.
# MAGIC
# MAGIC Datos personales: `plata_clientes` se publica **sin RUT ni nombre** (Ley 21.719, minimización). Oro no los tiene (pruebas V17, V17b).

# COMMAND ----------

# MAGIC %pip install -q "pandas>=2.0" "numpy>=1.24" "matplotlib>=3.5" certifi

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

# MAGIC %run ./_comun

# COMMAND ----------

dbutils.widgets.dropdown("simular_falla_calidad", "no", ["no", "si"], "Demostración: duplicar una boleta")
SIMULAR = dbutils.widgets.get("simular_falla_calidad") == "si"

import shutil

import config
import run_pipeline

# La cadena parte de lo que dejó el notebook 01: fuentes en el Volume y la respuesta del IPC ya guardada en bronce
shutil.rmtree(config.DATOS, ignore_errors=True)
config.BRONCE.mkdir(parents=True, exist_ok=True)
shutil.copyfile(Path(VOLUMEN) / "bronce" / "ipc_2025_raw.json", config.BRONCE / "ipc_2025_raw.json")

r = run_pipeline.ejecutar(fuente=Path(VOLUMEN) / "origen", refrescar_ipc=False, simular_falla_calidad=SIMULAR)
val = r["validaciones"]
print(f"\nPublicada: {r['publicada']} · pruebas {int((val.resultado == 'OK').sum())}/{len(val)}")

# COMMAND ----------

# Historial: siempre se agrega (es un registro, no un hecho; no hay riesgo de duplicar ventas)
ultima = pd.read_csv(config.ORO / "historial_corridas.csv", encoding=config.ENCODING_SALIDA,
                     dtype={"pruebas_fallidas": str, "estado_ipc": str}).tail(1)
ultima["pruebas_fallidas"] = ultima.pruebas_fallidas.fillna("")      # siempre texto, para que el append no cambie el tipo
guardar(ultima, "historial_corridas", modo="append")
guardar(val, "historial_pruebas", modo="append")

if not r["publicada"]:
    guardar(val[val.resultado != "OK"], "cuarentena_validaciones", modo="append")
    fallidas = val.loc[(val.accion == "bloquea") & (val.resultado != "OK"), "id"].tolist()
    raise Exception(f"No se publicó: fallaron pruebas que bloquean {fallidas}. Plata y oro quedan con la última corrida buena.")

# COMMAND ----------

# Publicación (solo llega aquí si pasaron todas las pruebas que bloquean)
publicadas = []
for nombre, df in r["plata"].items():
    if nombre.startswith("_"):
        continue
    if nombre == "clientes":
        df = df.drop(columns=[c for c in df.columns if c.lower().startswith("rut") or c == "nombre"])
    publicadas.append((guardar(df, f"plata_{nombre}"), len(df)))

for nombre, df in r["oro"].items():
    if not nombre.startswith("_"):
        publicadas.append((guardar(df, nombre), len(df)))

for extra in ["validaciones", "supuestos", "diccionario_datos", "log_calidad", "metricas", "estado_fuentes"]:
    df = pd.read_csv(config.ORO / f"{extra}.csv", encoding=config.ENCODING_SALIDA)
    publicadas.append((guardar(df, extra), len(df)))

# Gráficos y resumen al Volume (para el informe)
graf = Path(VOLUMEN) / "graficos"
graf.mkdir(parents=True, exist_ok=True)
for png in (config.ORO / "graficos").glob("*.png"):
    shutil.copyfile(png, graf / png.name)
shutil.copyfile(config.ORO / "resumen_hallazgos.md", Path(VOLUMEN) / "resumen_hallazgos.md")

display(pd.DataFrame(publicadas, columns=["tabla", "filas"]))
