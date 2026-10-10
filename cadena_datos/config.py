# -*- coding: utf-8 -*-
"""
Configuración y supuestos de la cadena de datos (Retail, grupo_2).

Todo parámetro de negocio vive aquí: si la contraparte responde algo distinto
a lo supuesto, se cambia este archivo y se vuelve a correr la cadena.
"""
from pathlib import Path
import pandas as pd

# ---------------------------------------------------------------- rutas
RAIZ = Path(__file__).resolve().parent.parent
FUENTE_DEFAULT = RAIZ / 'origen'     # set de datos 2 (idéntico a casos/retail_multitienda/grupo_2 del repo del curso)
DATOS = RAIZ / 'datos'
BRONCE, PLATA, ORO = DATOS / 'bronce', DATOS / 'plata', DATOS / 'oro'

ARCHIVOS_FUENTE = ['origen_pos.sqlite', 'origen_maestro_productos.csv', 'origen_promociones.json']
TABLAS_POS = ['regiones', 'comunas', 'tiendas', 'medios_pago', 'clientes', 'boletas', 'boleta_detalle']
ENCODING_MAESTRO = 'latin-1'          # medido: 84 líneas con tildes no son UTF-8 válido
ENCODING_SALIDA = 'utf-8-sig'         # UTF-8 con BOM: Excel abre bien las tildes; Power BI/pandas lo leen igual

# ---------------------------------------------------------------- IPC
IPC_URL = 'https://mindicador.cl/api/ipc/2025'
# Respaldo si la API no responde y no hay snapshot en bronce (valores consultados el 28-09-2026, var. % mensual)
IPC_RESPALDO_2025 = {1: 1.1, 2: 0.4, 3: 0.5, 4: 0.2, 5: 0.2, 6: -0.4, 7: 0.9, 8: 0.0, 9: 0.4, 10: 0.0, 11: 0.3, 12: -0.2}
IPC_BASE = '2024-12'                  # índice = 100 en dic-2024; venta real en pesos de dic-2024

# ---------------------------------------------------------------- período y ventanas
PERIODO_INI = pd.Timestamp('2025-01-01')
PERIODO_FIN = pd.Timestamp('2025-12-31')
FECHA_CORTE = PERIODO_FIN             # corte de recencia / RFM
VENTANAS = [30, 90, 180]              # días de inactividad evaluados
VENTANA_PRINCIPAL = 90                # p90 intercompra = 74 d; 92,8% recompras <= 90 d (medido)
UMBRAL_N_MIN = 10                     # cortes con base < 10 clientes se marcan como no concluyentes

# ---------------------------------------------------------------- maestros y correcciones
MACROZONA_POR_REGION = {              # README del caso
    'Metropolitana': 'Metropolitana',
    'Valparaíso': 'Centro sur', 'Biobío': 'Centro sur',
    'Araucanía': 'Sur', 'Los Lagos': 'Sur',
}
CORRECCION_REGION_COMUNA = {4: 1}     # La Florida trae region_id=9 (inexistente) -> Metropolitana
FORMATO_TIENDA = {'Express': 'Express', 'Supermercado': 'Supermercado', 'Hiper': 'Híper', 'Híper': 'Híper', 'Online': 'Online'}
TIENDA_ONLINE_ID = 10

CATEGORIA_CANONICA = {                # 26 grafías -> 8 categorías (validado contra subcategoría)
    'abarrotes': 'Abarrotes', 'abarr': 'Abarrotes',
    'bebidas': 'Bebidas', 'beb': 'Bebidas',
    'lacteos': 'Lácteos', 'lact': 'Lácteos',
    'snacks': 'Snacks', 'snk': 'Snacks',
    'limpieza': 'Limpieza', 'aseo': 'Limpieza',
    'perfumeria': 'Perfumería', 'perf': 'Perfumería',
    'carnes': 'Carnes', 'carn': 'Carnes',
    'panaderia': 'Panadería', 'pan': 'Panadería',
}
PREFIJOS_TIPO_CLIENTE = {             # heurística por prefijo del nombre (no es un dato de la fuente)
    'Persona/Hogar': ['Sr.', 'Sra.', 'Familia'],
    'Negocio': ['Distribuidora', 'Almacén', 'Kiosco', 'Botillería', 'Comercial', 'Minimarket', 'Inversiones'],
}
DESCUENTOS_VALIDOS = {0, 10, 25}
CANTIDAD_MAYORISTA = 10               # cantidades >= 10 se marcan (el resto está entre 1 y 4)
TOLERANCIA_MONTO = 2                  # pesos de diferencia aceptados entre monto registrado y calculado

# ---------------------------------------------------------------- supuestos (el ayudante no respondió)
SUPUESTOS = [
    ('S01', 'Período de análisis', 'Enero–diciembre 2025. Las 37 boletas con fecha 2026 se conservan con flag_fuera_periodo=1 y quedan fuera de las métricas.', 'Decisión del equipo'),
    ('S02', 'Monto de venta', 'Venta de una boleta = suma de monto_linea registrado. El monto recalculado (cantidad × precio × (1 − desc)) queda como columna de control. Diferencia total 2025: 0,81%.', 'Pregunta descartada; grano boleta'),
    ('S03', 'IVA', 'Precios y montos con IVA incluido (precio de góndola).', 'Sin respuesta'),
    ('S04', 'Devoluciones', 'Líneas con cantidad negativa restan de la venta. Una boleta con venta neta <= 0 (solo devoluciones, o devolución mayor que la compra) no cuenta como compra para la retención.', 'Sin respuesta'),
    ('S05', 'Descuento 10% sin campaña', 'Se trata como beneficio permanente de la tarjeta (solo ocurre en compras identificadas).', 'Sin respuesta'),
    ('S06', 'Fecha de alta', 'Registra la inscripción, no la primera compra. Cliente previo = alta anterior a 2025; cliente nuevo = alta en 2025 (su primera compra observada define la cohorte).', 'Pregunta 1 sin respuesta'),
    ('S07', 'Tipo de cliente', 'Se reportan dos cortes: segmento de la tarjeta y persona/hogar vs. negocio (inferido del prefijo del nombre).', 'Pregunta 2 sin respuesta'),
    ('S08', 'Canal Online', 'Se incluye como un local más (tienda 10), con es_online para filtrarlo.', 'Pregunta 3 sin respuesta'),
    ('S09', 'Local de un cliente', 'Local principal = tienda con más compras válidas en 2025; empate -> la de la compra más reciente.', 'Decisión del equipo'),
    ('S10', 'Cliente', 'cliente_id = tarjeta del hogar (acta). No se intenta separar personas.', 'Acta'),
    ('S11', 'Ventana de inactividad', '90 días como principal; 30 (creencia de la empresa) y 180 como sensibilidad.', 'Informe + datos'),
    ('S12', 'Duplicados', 'Las 61 boletas idénticas se eliminan. Pares (boleta, línea) repetidos con SKU distinto son productos distintos: se renumeran, no se borran.', 'Decisión del equipo'),
    ('S13', 'Columnas mes y region de boletas', 'Se descartan; mes y región se derivan de la fecha y de la tienda.', 'Decisión del equipo'),
    ('S14', 'Productos', 'SKU-9xxx sin maestro se conservan como "Sin maestro". SKU-0001 duplicado: se conserva la fila activa. ASEO = Limpieza (mismas subcategorías).', 'Decisión del equipo'),
    ('S15', 'Datos personales', 'RUT y nombre solo existen en plata (uso interno). Oro no contiene identificadores directos (minimización, Ley 21.719).', 'Criterio más restrictivo'),
    ('S16', 'Deflactor', 'IPC general de mindicador.cl, índice base dic-2024 = 100.', 'Fuente obligatoria del caso'),
]
