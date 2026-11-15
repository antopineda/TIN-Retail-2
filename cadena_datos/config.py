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
IPC_TIMEOUT_S = 20
# Si la API falla, se usa la última respuesta buena versionada en el repositorio (consultada el 15-11-2026).
IPC_SNAPSHOT_VERSIONADO = RAIZ / 'cadena_datos' / 'referencias' / 'ipc_2025_snapshot.json'
# Último recurso si tampoco existe el snapshot (valores consultados el 28-09-2026, var. % mensual)
IPC_RESPALDO_2025 = {1: 1.1, 2: 0.4, 3: 0.5, 4: 0.2, 5: 0.2, 6: -0.4, 7: 0.9, 8: 0.0, 9: 0.4, 10: 0.0, 11: 0.3, 12: -0.2}
IPC_RANGO_VALIDO = (-2.0, 3.0)        # var. % mensual fuera de este rango = dato sospechoso (prueba F04)
IPC_BASE = '2024-12'                  # índice = 100 en dic-2024; venta real en pesos de dic-2024

# ---------------------------------------------------------------- período y ventanas
PERIODO_INI = pd.Timestamp('2025-01-01')
PERIODO_FIN = pd.Timestamp('2025-12-31')
FECHA_CORTE = PERIODO_FIN             # corte de recencia / RFM
VENTANAS = [30, 90, 180]              # días de inactividad evaluados. 365 se retiró (feedback E1): con 12 meses de datos da 100% por construcción
VENTANA_PRINCIPAL = 90                # p90 intercompra = 74 d; 92,8% recompras <= 90 d (medido)
# Regla de lectura "retiene / repone" (feedback E1 y P1): se aplica igual a cualquier ventana.
#   ¿De dónde sale la base de clientes activos al cierre del trimestre?
#   RETIENE  : al menos UMBRAL_BASE_RETENIDA de los activos al cierre ya estaban activos al inicio.
#   REPONE   : menos que eso, pero los que entran (nuevos + reactivados + primeras compras de previos) cubren a los perdidos.
#   SE ACHICA: los que entran no alcanzan a cubrir a los perdidos.
UMBRAL_BASE_RETENIDA = 0.50
HORIZONTE_SEGUNDA_COMPRA = 90         # días: un cliente nuevo es "de una sola vez" si no vuelve dentro de este plazo
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

CATEGORIA_CANONICA = {                # 24 grafías -> 8 categorías (validado contra subcategoría)
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

# ---------------------------------------------------------------- margen (E2: la recomendación va en pesos de margen, no de venta)
FACTOR_IVA = 1.19                     # venta registrada con IVA (S03); costo del maestro sin IVA (S17)
# margen bruto de una línea = monto_linea / FACTOR_IVA − cantidad × costo_unitario  [CLP nominales, sin IVA]

# ---------------------------------------------------------------- caso de negocio: contactar antes de perder al cliente
# Valores por defecto del prototipo; la gerencia los cambia en pantalla. Son supuestos (S18, S19), no mediciones.
CONTACTO_DIA_DEFECTO = 60             # se contacta al cliente cuando cumple N días sin comprar (E1: entre 60 y 75)
CONTACTO_COSTO_ENVIO_CLP = 50         # CLP por contacto (SMS/WhatsApp masivo + gestión); sin IVA
CONTACTO_CUPON_PCT = 10               # % de descuento del cupón de regreso, aplicado al ticket promedio
CONTACTO_TASA_RECUPERACION = 0.10     # proporción de los que se iban a perder que vuelven por el contacto (no medida)

# ---------------------------------------------------------------- gobierno: dueño y acuerdo de servicio (E2, componente B)
DUENO_METRICA = 'Gerencia Comercial (Subgerente de Clientes y Fidelización)'
DUENO_DATO = 'Jefe de BI (operación de la cadena de datos)'
SLA = {
    'frescura': 'Mensual: la cadena corre el día hábil 3 de cada mes con el cierre del mes anterior',
    'completitud_min_boletas_identificadas': 0.80,   # % mínimo de boletas del mes con tarjeta (2025: 86,9%)
    'calidad_min_pruebas_ok': 1.00,                  # 100% de las pruebas que bloquean en verde para publicar
}
Z_IC95 = 1.96                         # intervalo de confianza del 95% (Wilson) para tasas por local

# ---------------------------------------------------------------- bitácora de supuestos (anexo obligatorio de la E1)
# Cada supuesto: qué se asume, por qué, qué pasaría con el resultado si fuera falso, y quién lo decidió y cuándo.
SUPUESTOS = [
    {'id': 'S01', 'tema': 'Período de análisis',
     'supuesto': 'Enero–diciembre 2025. Las 37 boletas con fecha 2026 se conservan con flag_fuera_periodo y quedan fuera de las métricas.',
     'por_que': 'El caso es sobre 2025 y el IPC entregado es de 2025; las fechas 2026 son pocas y dispersas (contraparte: "unas pocas fechas de 2026").',
     'efecto_si_falso': 'Si fueran válidas, el corte de recencia se movería a junio de 2026 y casi todos los clientes quedarían inactivos. Son 0,6% de las boletas.',
     'decidio': 'Equipo', 'fecha': '09-10-2026'},
    {'id': 'S02', 'tema': 'Monto de venta',
     'supuesto': 'Venta de una boleta = suma de monto_linea registrado. El monto recalculado (cantidad × precio × (1 − desc)) queda como columna de control.',
     'por_que': 'El grano del modelo es la boleta y la retención depende de si hubo compra, no del monto.',
     'efecto_si_falso': 'Si el oficial fuera el recalculado, la venta 2025 baja 0,81% ($77,0 M -> $76,4 M). La retención no cambia.',
     'decidio': 'Equipo', 'fecha': '30-09-2026'},
    {'id': 'S03', 'tema': 'IVA',
     'supuesto': 'Precios y montos con IVA incluido (precio de góndola).',
     'por_que': 'Es como se registra una venta en caja (precio de góndola).',
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
     'por_que': 'La contraparte pidió la retención por local y 704 clientes compran en más de una tienda física: hay que asignarlos a uno para no contarlos dos veces.',
     'efecto_si_falso': 'Con otra asignación (por ejemplo, el local de la primera compra) cambian las tasas por local, no el total.',
     'decidio': 'Equipo', 'fecha': '09-10-2026'},
    {'id': 'S10', 'tema': 'Cliente = hogar',
     'supuesto': 'cliente_id es la tarjeta del hogar; no se separan personas.',
     'por_que': 'La contraparte dijo en la reunión que la tarjeta opera por hogar.',
     'efecto_si_falso': 'Si fuera por persona, la frecuencia por cliente estaría sobrestimada; no hay dato para separarlo.',
     'decidio': 'Acta de la reunión', 'fecha': '04-09-2026'},
    {'id': 'S11', 'tema': 'Ventana de inactividad',
     'supuesto': '90 días como ventana principal; 30 (regla de un mes de la empresa) y 180 días como alternativas. 365 días se retiró.',
     'por_que': 'No hay ventana oficial. El 92,8% de las recompras ocurre dentro de 90 días (p90 = 74 días): a los 90 días casi todos los que iban a volver ya volvieron, '
                'así que es el momento en que un cliente se puede dar por perdido y la acción de reactivación deja de gastar en clientes que vuelven solos. '
                'Con 365 días la retención da 100% solo porque hay un año de datos.',
     'efecto_si_falso': 'Retención Q4: 33,2% (30 d), 51,1% (90 d), 82,5% (180 d). Reposición: 0,76, 1,07 y 2,34. Veredicto de la regla S22 en Q4: '
                        'se achica (30 d), repone (90 d), retiene (180 d). La conclusión depende de la ventana y se presenta condicionada a ella.',
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
    {'id': 'S17', 'tema': 'Margen bruto',
     'supuesto': 'Margen bruto = venta sin IVA (monto_linea / 1,19) − unidades × costo_unitario del maestro. El costo del maestro está sin IVA. '
                 'Las líneas sin costo (SKU sin maestro o costo N/A, 1,6% de la venta) usan la razón costo/venta del resto (flag_costo_imputado).',
     'por_que': 'La E1 se observó por hablar de venta y no de margen. El maestro trae costo unitario para 98,4% de la venta.',
     'efecto_si_falso': 'Si el costo incluyera IVA, el margen subiría de ~18% a ~31% de la venta sin IVA y el valor en riesgo crecería en la misma proporción. '
                        'La retención no cambia.',
     'decidio': 'Antonia Pineda (Grupo 2)', 'fecha': '15-11-2026'},
    {'id': 'S18', 'tema': 'Costo de contactar a un cliente',
     'supuesto': f'CLP {CONTACTO_COSTO_ENVIO_CLP} por contacto + un cupón de {CONTACTO_CUPON_PCT}% sobre el ticket promedio, que usan todos los que vuelven '
                 '(también los que habrían vuelto solos).',
     'por_que': 'No hay dato de costo de campañas de la empresa. Es un orden de magnitud de un envío masivo por SMS/WhatsApp; se cambia en pantalla.',
     'efecto_si_falso': 'Contactando a los 60 días: con CLP 200 por contacto (en vez de 50) el costo sube de CLP 0,48 M a 0,67 M al año y el punto de equilibrio de 3,4% a 5,1%; '
                        'con un cupón de 15% el equilibrio también sube a 5,1%. La retención no cambia. El cupón de 10% no es externo: es el mismo descuento que ya da la tarjeta (S05).',
     'decidio': 'Antonia Pineda (Grupo 2)', 'fecha': '15-11-2026'},
    {'id': 'S19', 'tema': 'Tasa de recuperación del contacto',
     'supuesto': f'{CONTACTO_TASA_RECUPERACION:.0%} de los clientes que se iban a perder vuelve por el contacto. No está medida: '
                 'se reporta junto al punto de equilibrio (la tasa mínima para que la acción pague su costo).',
     'por_que': 'Las campañas de 2025 no tuvieron grupo de control; no hay forma de medir el efecto causal con estos datos.',
     'efecto_si_falso': 'Con 5% de recuperación (en vez de 10%) el resultado a los 60 días baja de CLP 0,75 M a 0,18 M al año; bajo 3,4% la acción pierde plata. '
                        'Por eso la recomendación se presenta con el punto de equilibrio y un piloto con grupo de control, no con el 10%.',
     'decidio': 'Antonia Pineda (Grupo 2)', 'fecha': '15-11-2026'},
    {'id': 'S20', 'tema': 'Valor en riesgo en margen',
     'supuesto': 'Margen anual en riesgo = margen trimestral típico de cada cliente perdido en Q4 (margen 2025 / trimestres entre su primera y última compra) × 4.',
     'por_que': 'Es la misma regla de la E1 (venta en riesgo), aplicada al margen en vez de la venta.',
     'efecto_si_falso': 'Si en vez del margen trimestral típico se usa el margen que los perdidos dejaron en Q3 (su último trimestre completo) × 4, '
                        'el margen en riesgo baja de CLP 4,57 M a CLP 4,03 M al año (−12%): ya venían comprando algo menos antes de irse.',
     'decidio': 'Antonia Pineda (Grupo 2)', 'fecha': '15-11-2026'},
    {'id': 'S21', 'tema': 'Falla de la API del IPC',
     'supuesto': 'Si mindicador.cl no responde, se usa el último snapshot bueno versionado en cadena_datos/referencias/ y la corrida queda marcada con aviso.',
     'por_que': 'El IPC solo afecta la venta real (deflactada); la retención y el margen nominal no dependen de él.',
     'efecto_si_falso': 'Si el IPC 2025 se revisara después del snapshot, la venta real cambiaría levemente; ninguna cifra de la respuesta cambia.',
     'decidio': 'Antonia Pineda (Grupo 2)', 'fecha': '15-11-2026'},
    {'id': 'S22', 'tema': 'Regla retiene / repone',
     'supuesto': f'En un trimestre la cadena RETIENE si al menos {UMBRAL_BASE_RETENIDA:.0%} de sus clientes activos al cierre ya estaban activos al inicio; '
                 'REPONE si no, pero los que entran cubren a los perdidos; SE ACHICA si los que entran no cubren a los perdidos. La misma regla para toda ventana.',
     'por_que': 'Feedback de la E1 y la P1: una regla que decida entre retener y reponer, independiente de la ventana. '
                'Responde la pregunta tal como está escrita: si la base de clientes activos se sostiene con los que se quedan o con los que llegan.',
     'efecto_si_falso': 'Con un umbral de 40% en vez de 50%, el veredicto con 90 días en Q4 pasa de "repone" (44,5%) a "retiene"; con 30 y 180 días no cambia.',
     'decidio': 'Antonia Pineda (Grupo 2)', 'fecha': '15-11-2026'},
]

# Tipo de evidencia de cada supuesto (rúbrica P1, criterio 2): verbalizado (lo dijo la contraparte), medido (sale de los datos)
# o inferido (decisión del grupo a partir de los datos).
EVIDENCIA_SUPUESTO = {
    'S01': 'verbalizado + medido', 'S02': 'inferido', 'S03': 'inferido', 'S04': 'inferido', 'S05': 'medido',
    'S06': 'verbalizado', 'S07': 'verbalizado', 'S08': 'verbalizado', 'S09': 'inferido', 'S10': 'verbalizado',
    'S11': 'medido', 'S12': 'verbalizado', 'S13': 'medido', 'S14': 'inferido', 'S15': 'inferido (norma legal)',
    'S16': 'verbalizado (acta y enunciado)', 'S17': 'medido (costo) + inferido (sin IVA)', 'S18': 'inferido',
    'S19': 'inferido', 'S20': 'inferido', 'S21': 'inferido', 'S22': 'inferido',
}
