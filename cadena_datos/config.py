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
VENTANAS = [30, 90, 180, 365]         # días de inactividad evaluados (365: alternativa del enunciado; con 12 meses de datos no discrimina)
VENTANA_PRINCIPAL = 90                # p90 intercompra = 74 d; 92,8% recompras <= 90 d (medido)
UMBRAL_N_MIN = 10                     # cortes con base < 10 clientes se marcan como no concluyentes
UMBRAL_MUESTRA_PEQUENA = 50           # cortes con base < 50 clientes: tasas volátiles, mostrar con advertencia

# ---------------------------------------------------------------- maestros y correcciones
MACROZONA_POR_REGION = {              # README del caso
    'Metropolitana': 'Metropolitana',
    'Valparaíso': 'Centro sur', 'Biobío': 'Centro sur',
    'Araucanía': 'Sur', 'Los Lagos': 'Sur',
}
CORRECCION_REGION_COMUNA = {4: 1}     # La Florida trae region_id=9 (inexistente) -> Metropolitana
FORMATO_TIENDA = {'Express': 'Express', 'Supermercado': 'Supermercado', 'Hiper': 'Híper', 'Híper': 'Híper', 'Online': 'Online'}
TIENDA_ONLINE_ID = 10
MACROZONA_ONLINE = 'Online'           # Online vende a clientes de toda la cadena: no se asigna a la Metropolitana (contraparte 13-10)
CORTE_CLASIFICACION_NOMBRE = 'Persona/negocio (clasificación del equipo)'

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
PREFIJOS_CLASIFICACION_NOMBRE = {     # clasificación del equipo por prefijo del nombre; NO es un campo de la empresa (contraparte 13-10)
    'Persona/Hogar': ['Sr.', 'Sra.', 'Familia'],
    'Negocio': ['Distribuidora', 'Almacén', 'Kiosco', 'Botillería', 'Comercial', 'Minimarket', 'Inversiones'],
}
DESCUENTOS_VALIDOS = {0, 10, 25}
CANTIDAD_MAYORISTA = 10               # cantidades >= 10 se marcan (el resto está entre 1 y 4)
TOLERANCIA_MONTO = 2                  # pesos de diferencia aceptados entre monto registrado y calculado

# ---------------------------------------------------------------- bitácora de supuestos (anexo obligatorio de la E1)
# Cada supuesto: qué se asume, por qué, qué pasaría con el resultado si fuera falso, y quién lo decidió y cuándo.
SUPUESTOS = [
    {'id': 'S01', 'tema': 'Período de análisis',
     'supuesto': 'Enero–diciembre 2025. Las 37 boletas con fecha 2026 se conservan con flag_fuera_periodo y quedan fuera de las métricas.',
     'por_que': 'El caso es sobre 2025 y el IPC entregado es de 2025; las fechas 2026 son pocas y dispersas (contraparte: "unas pocas fechas de 2026").',
     'efecto_si_falso': 'Si fueran válidas, el corte de recencia se movería a junio de 2026 y casi todos los clientes quedarían inactivos. Son 0,6% de las boletas.',
     'decidio': 'Equipo (subgrupo de datos)', 'fecha': '09-10-2026'},
    {'id': 'S02', 'tema': 'Monto de venta',
     'supuesto': 'Venta de una boleta = suma de monto_linea registrado. El monto recalculado (cantidad × precio × (1 − desc)) queda como columna de control.',
     'por_que': 'El grano del modelo es la boleta y la retención depende de si hubo compra, no del monto.',
     'efecto_si_falso': 'Si el oficial fuera el recalculado, la venta 2025 baja 0,81% ($77,0 M -> $76,4 M). La retención no cambia.',
     'decidio': 'Equipo', 'fecha': '30-09-2026'},
    {'id': 'S03', 'tema': 'IVA',
     'supuesto': 'Precios y montos con IVA incluido (precio de góndola).',
     'por_que': 'Es como se registra una venta en caja; no se preguntó por el límite de 3 consultas.',
     'efecto_si_falso': 'Cambian los montos en pesos (factor 1,19), no las tasas de retención.',
     'decidio': 'Equipo', 'fecha': '09-10-2026'},
    {'id': 'S04', 'tema': 'Devoluciones',
     'supuesto': 'Las líneas con cantidad negativa restan de la venta. Una boleta con venta neta <= 0 no cuenta como compra.',
     'por_que': 'Una devolución no es una visita de compra; contarla inflaría la frecuencia.',
     'efecto_si_falso': 'Entrarían 5 clientes más a la retención (1.197 en vez de 1.192): efecto marginal.',
     'decidio': 'Equipo', 'fecha': '09-10-2026'},
    {'id': 'S05', 'tema': 'Descuento 10% sin campaña',
     'supuesto': 'Es un beneficio permanente de la tarjeta.',
     'por_que': 'Solo ocurre en compras identificadas, todos los meses y en todas las tiendas.',
     'efecto_si_falso': 'No cambia la retención; solo la lectura de los descuentos (pregunta de promociones, fuera de alcance).',
     'decidio': 'Equipo', 'fecha': '09-10-2026'},
    {'id': 'S06', 'tema': 'Fecha de alta y cliente nuevo',
     'supuesto': 'La fecha de alta no es la primera compra ni una inscripción: no se corrige ni se usa como primera compra. '
                 'Cliente previo = alta anterior a 2025. Cliente nuevo = alta en 2025 y primera compra en el período.',
     'por_que': 'La contraparte confirmó que no hay evento detrás de la fecha y que un cliente con alta 2024 pudo comprar antes del extracto. '
                'Limitación: 54 clientes con alta entre el 1 y el 27 de enero de 2025 podrían haber comprado en diciembre de 2024.',
     'efecto_si_falso': 'Si los 375 clientes previos que vemos comprar en 2025 se contaran como nuevos, los nuevos pasarían de 817 a 1.192 '
                        'y el índice de reposición se inflaría: la cadena parecería reponer mucho más de lo que realmente repone.',
     'decidio': 'Contraparte (correo) + definición del equipo', 'fecha': '13-10-2026'},
    {'id': 'S07', 'tema': 'Tipo de cliente',
     'supuesto': '"Tipo de cliente" = segmento de la tarjeta y local. Persona/negocio (clasificacion_nombre) es una clasificación del equipo, solo complementaria.',
     'por_que': 'Lo aclaró la contraparte; el segmento sale parejo y la contraparte pidió no insistir en él.',
     'efecto_si_falso': 'Si fuera persona/negocio, el corte existe igual en las tablas y no separa la retención (50,1% vs 52,7% en Q4).',
     'decidio': 'Contraparte (correo)', 'fecha': '13-10-2026'},
    {'id': 'S08', 'tema': 'Canal Online',
     'supuesto': 'La Tienda Online es un décimo punto de venta: sus compras entran al cálculo principal. En cortes geográficos tiene macrozona "Online".',
     'por_que': 'Lo confirmó la contraparte: vende todo el año a clientes de toda la cadena, con el mismo cliente_id.',
     'efecto_si_falso': 'Si se excluyera, se perdería 24,8% de las boletas y un cliente que vuelve por la web aparecería como perdido.',
     'decidio': 'Contraparte (correo)', 'fecha': '13-10-2026'},
    {'id': 'S09', 'tema': 'Local de un cliente',
     'supuesto': 'Local principal = tienda con más compras válidas en 2025; empate -> la de la compra más reciente.',
     'por_que': 'La contraparte pidió la retención por local y 706 clientes compran en más de un local: hay que asignarlos a uno para no contarlos dos veces.',
     'efecto_si_falso': 'Con otra asignación (por ejemplo, el local de la primera compra) cambian las tasas por local, no el total.',
     'decidio': 'Equipo', 'fecha': '09-10-2026'},
    {'id': 'S10', 'tema': 'Cliente = hogar',
     'supuesto': 'cliente_id es la tarjeta del hogar; no se separan personas.',
     'por_que': 'La contraparte dijo en la reunión que la tarjeta opera por hogar.',
     'efecto_si_falso': 'Si fuera por persona, la frecuencia por cliente estaría sobrestimada; no hay dato para separarlo.',
     'decidio': 'Acta de la reunión', 'fecha': '04-09-2026'},
    {'id': 'S11', 'tema': 'Ventana de inactividad',
     'supuesto': '90 días como ventana principal; 30, 180 y 365 días como sensibilidad.',
     'por_que': 'No hay ventana oficial. El 92,8% de las recompras ocurre dentro de 90 días (p90 = 74 días); 30 es la creencia de la empresa; '
                '365 es una alternativa del enunciado, pero con 12 meses de datos no discrimina.',
     'efecto_si_falso': 'La retención Q4 cambia según la ventana (ver mart_kpi_resumen: retencion_Q4_*). La conclusión depende de la definición.',
     'decidio': 'Equipo', 'fecha': '09-10-2026'},
    {'id': 'S12', 'tema': 'Duplicados y anónimos',
     'supuesto': 'Las 61 boletas idénticas cuentan una vez. Las boletas sin cliente quedan fuera de la retención, sin repartirlas.',
     'por_que': 'Lo confirmó la contraparte.',
     'efecto_si_falso': 'Sin quitar duplicados, la venta subiría $0,82 M y esos clientes tendrían compras de más.',
     'decidio': 'Equipo; confirmado por la contraparte', 'fecha': '13-10-2026'},
    {'id': 'S13', 'tema': 'Columnas mes y region de boletas',
     'supuesto': 'Se descartan; mes y región se derivan de la fecha y de la tienda.',
     'por_que': 'No coinciden con la fecha (438 boletas) ni con la tienda (397) y no siguen ningún patrón.',
     'efecto_si_falso': 'Si la fecha fuera la incorrecta, 438 boletas cambiarían de mes; no hay forma de verificarlo.',
     'decidio': 'Equipo', 'fecha': '09-10-2026'},
    {'id': 'S14', 'tema': 'Productos',
     'supuesto': 'SKU-9xxx sin maestro se conservan como "Sin maestro"; SKU-0001 duplicado: se conserva la fila activa; ASEO = Limpieza.',
     'por_que': 'No hay tabla de equivalencias ERP-POS; ASEO tiene las mismas subcategorías que Limpieza.',
     'efecto_si_falso': 'Sin efecto en la retención (el grano es la boleta).',
     'decidio': 'Equipo', 'fecha': '09-10-2026'},
    {'id': 'S15', 'tema': 'Datos personales',
     'supuesto': 'RUT y nombre solo existen en plata (uso interno); oro no tiene identificadores directos.',
     'por_que': 'Minimización (Ley 21.719).',
     'efecto_si_falso': 'Sin efecto en las cifras.',
     'decidio': 'Equipo', 'fecha': '28-09-2026'},
    {'id': 'S16', 'tema': 'Deflactor',
     'supuesto': 'IPC general de mindicador.cl, índice base dic-2024 = 100.',
     'por_que': 'Es la fuente obligatoria del caso; la empresa usa un 3% fijo.',
     'efecto_si_falso': 'Con el 3% fijo la venta real cambia levemente (inflación 2025 acumulada: 3,44%). No afecta la retención.',
     'decidio': 'Enunciado del caso / acta', 'fecha': '04-09-2026'},
]
