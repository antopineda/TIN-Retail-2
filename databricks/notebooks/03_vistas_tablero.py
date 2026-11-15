# Databricks notebook source
# MAGIC %md
# MAGIC # 03 · Vistas para el tablero (capa de consumo)
# MAGIC
# MAGIC El tablero AI/BI lee **solo estas vistas**. Las vistas no recalculan ninguna métrica: seleccionan columnas que ya calculó
# MAGIC la cadena con `cadena_datos/metricas.py`. Así el número del tablero es el mismo del informe y del prototipo Streamlit.

# COMMAND ----------

dbutils.widgets.text("catalogo", "workspace", "Catálogo (Unity Catalog)")
dbutils.widgets.text("esquema", "retail_g2", "Esquema")
D = f"{dbutils.widgets.get('catalogo')}.{dbutils.widgets.get('esquema')}"

VISTAS = {
    # Cifra clave, comparación con el trimestre anterior y regla retiene / repone, para cada ventana y trimestre
    "v_retencion_trimestral": f"""
        SELECT periodo AS trimestre, ventana_dias,
               tasa_retencion, LAG(tasa_retencion) OVER (PARTITION BY ventana_dias ORDER BY periodo) AS tasa_trimestre_anterior,
               indice_reposicion, pct_base_retenida, veredicto,
               activos_inicio, retenidos, perdidos, nuevos, reactivados, ic95_inf, ic95_sup
        FROM {D}.mart_retencion
        WHERE corte = 'Total' AND periodo_tipo = 'trimestre' AND base_confiable""",
    # Corte por la dimensión principal: local, con intervalo (sin ranking: el tablero ordena por nombre)
    "v_retencion_local": f"""
        SELECT r.periodo AS trimestre, r.ventana_dias, r.valor AS local, r.activos_inicio, r.retenidos, r.perdidos,
               r.tasa_retencion, r.ic95_inf, r.ic95_sup, r.se_puede_rankear, t.tasa_retencion AS tasa_total_cadena
        FROM {D}.mart_retencion r
        JOIN {D}.mart_retencion t
          ON t.corte = 'Total' AND t.periodo = r.periodo AND t.ventana_dias = r.ventana_dias AND t.periodo_tipo = 'trimestre'
        WHERE r.corte = 'Tienda principal' AND r.periodo_tipo = 'trimestre' AND r.base_confiable""",
    # Margen en riesgo por ventana (Q4)
    "v_margen_en_riesgo": f"""
        SELECT ventana_dias, perdidos_q4, activos_inicio_q4,
               margen_anual_en_riesgo, margen_anual_en_riesgo / 1e6 AS margen_anual_en_riesgo_millones_clp,
               margen_anual_1pp_retencion
        FROM {D}.mart_valor_riesgo""",
    # Cobertura y compradores de una sola vez (no dependen de la ventana)
    "v_cobertura_y_una_sola_vez": f"""
        SELECT
          (SELECT 1 - valor FROM {D}.mart_kpi_resumen WHERE kpi = 'pct_boletas_fuera_de_retencion') AS cobertura_boletas,
          (SELECT valor FROM {D}.mart_kpi_resumen WHERE kpi = 'pct_venta_2025_en_retencion') AS cobertura_venta,
          (SELECT pct_una_sola_vez FROM {D}.mart_una_sola_vez WHERE tipo_cohorte = 'Nuevo 2025' AND cohorte_trimestre = 'Todo 2025') AS pct_nuevos_una_sola_vez,
          (SELECT pct_una_sola_vez FROM {D}.mart_una_sola_vez WHERE tipo_cohorte = 'Nuevo 2025' AND cohorte_trimestre = '2025Q3') AS pct_nuevos_q3_una_sola_vez""",
    # Caso de negocio (tabla fija con los supuestos por defecto S18 y S19)
    "v_caso_contacto": f"""
        SELECT dia_contacto, contactados, pct_contactos_desperdiciados, costo_total, margen_recuperado, resultado_neto, tasa_equilibrio
        FROM {D}.mart_caso_contacto""",
    # Pie: última corrida publicada, pruebas y estado de la API
    "v_pie": f"""
        SELECT h.corrida AS ultima_corrida_publicada, h.pruebas_ok, h.pruebas,
               (SELECT estado FROM {D}.estado_fuentes WHERE archivo LIKE '%ipc%') AS estado_api_ipc,
               (SELECT MAX(corrida) FROM {D}.historial_corridas) AS ultimo_intento,
               (SELECT CAST(publicada AS STRING) FROM {D}.historial_corridas ORDER BY corrida DESC LIMIT 1) AS ultimo_intento_publicado
        FROM {D}.historial_corridas h
        WHERE CAST(h.publicada AS STRING) IN ('true', 'True')
        ORDER BY h.corrida DESC LIMIT 1""",
}

for nombre, sql in VISTAS.items():
    spark.sql(f"CREATE OR REPLACE VIEW {D}.{nombre} AS {sql}")
    print(f"{D}.{nombre}")

# COMMAND ----------

# Control: el número que ve el tablero tiene que ser el mismo del informe (mart_kpi_resumen, de la misma corrida)
fila = spark.sql(f"SELECT tasa_retencion, veredicto FROM {D}.v_retencion_trimestral WHERE trimestre = '2025Q4' AND ventana_dias = 90").first()
informe = spark.sql(f"SELECT valor FROM {D}.mart_kpi_resumen WHERE kpi = 'retencion_Q4_90d'").first().valor
print(f"Retención Q4 2025 (90 días): tablero {fila.tasa_retencion:.1%} · informe {informe:.1%} · veredicto: {fila.veredicto}")
assert abs(fila.tasa_retencion - informe) < 1e-12, "El número del tablero no coincide con el del informe"
