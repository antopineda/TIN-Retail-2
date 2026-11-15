# Databricks notebook source
# MAGIC %md
# MAGIC # Funciones comunes (se cargan con `%run ./_comun`)
# MAGIC
# MAGIC - Encuentra la raíz del repositorio (la carpeta Git del workspace) para importar `cadena_datos/`.
# MAGIC - Lee los parámetros del job: catálogo y esquema de Unity Catalog.
# MAGIC - Convierte tablas pandas a Spark y las guarda como Delta.

# COMMAND ----------

import os
import sys
from pathlib import Path

dbutils.widgets.text("catalogo", "workspace", "Catálogo (Unity Catalog)")
dbutils.widgets.text("esquema", "retail_g2", "Esquema")
CATALOGO = dbutils.widgets.get("catalogo")
ESQUEMA = dbutils.widgets.get("esquema")
DESTINO = f"{CATALOGO}.{ESQUEMA}"
VOLUMEN = f"/Volumes/{CATALOGO}/{ESQUEMA}/archivos"

# Carpeta de trabajo de la cadena en el disco local del cómputo (SQLite no funciona bien sobre un Volume).
os.environ["RETAIL_DATOS"] = "/tmp/retail_g2/datos"


def _raiz_repo():
    p = Path(os.getcwd()).resolve()
    for c in [p, *p.parents]:
        if (c / "cadena_datos" / "run_pipeline.py").exists():
            return c
    raise RuntimeError("No encontré cadena_datos/. Abre este notebook desde la carpeta Git del repositorio (rama databricks).")


RAIZ = _raiz_repo()
if str(RAIZ / "cadena_datos") not in sys.path:
    sys.path.insert(0, str(RAIZ / "cadena_datos"))

spark.sql(f"CREATE SCHEMA IF NOT EXISTS {DESTINO}")
spark.sql(f"CREATE VOLUME IF NOT EXISTS {DESTINO}.archivos")
print(f"Repositorio: {RAIZ}\nDestino: {DESTINO}\nVolumen: {VOLUMEN}")

# COMMAND ----------

import pandas as pd


def celdas(pdf, f):
    """Aplica f a cada celda (DataFrame.map en pandas >= 2.1; applymap antes)."""
    return pdf.map(f) if hasattr(pd.DataFrame, "map") else pdf.applymap(f)


def a_spark(pdf):
    """pandas -> Spark sin sorpresas de tipos: texto y mezclas a string (None se mantiene), enteros con nulos a decimal."""
    pdf = pdf.copy()
    for c in pdf.columns:
        s = pdf[c]
        if str(s.dtype) in ("Int64", "Int32", "Float64"):
            pdf[c] = s.astype("float64")
        elif str(s.dtype) == "boolean":
            pdf[c] = s.astype(object).where(s.notna(), None)
        elif s.dtype == object or str(s.dtype) == "string":
            v = s.astype(object).where(s.notna(), None)
            solo_bool = v.dropna().map(lambda x: isinstance(x, bool)).all() and v.notna().any()
            pdf[c] = v if solo_bool else v.map(lambda x: None if x is None else str(x))
    return spark.createDataFrame(pdf) if len(pdf) else spark.createDataFrame(pdf.astype(str))


def guardar(pdf, tabla, modo="overwrite"):
    """Guarda una tabla Delta. overwrite = carga completa e idempotente; append solo para registros históricos."""
    (a_spark(pdf).write.mode(modo).option("overwriteSchema", "true" if modo == "overwrite" else "false")
     .option("mergeSchema", "true").saveAsTable(f"{DESTINO}.{tabla}"))
    return f"{DESTINO}.{tabla}"
