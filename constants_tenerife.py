# Constants for Tenerife Bot - Spanish Language

# Button Labels - Main Menu
B1 = '💶 Por PRECIO'
B2 = '🚗🚜 Por COMBUSTIBLE'  
B3 = '🏘 Por MUNICIPIO'
B4 = '👁‍🗨 +INFO'
B5 = '🔙 Atrás'

# Price-related buttons
B6 = '✅ 5 más baratas'
B7 = '‼️ 5 más caras'

# Fuel type buttons (ordered by popularity - most common first)
B8 = '🟢 Gasolina 95 E5'      # Most common
B9 = '⚫️ Gasóleo A'           # Most common diesel
B10 = '🔵 Gasolina 98 E5'     # Premium gasoline
B11 = '🟠 Gasóleo Premium'    # Premium diesel
B12 = '⚪️ GLP'               # LPG
B13 = '🟤 Gasóleo B'          # Commercial diesel
B14 = '🔴 AdBlue'             # Diesel additive
B15 = '🟡 Gas Natural Licuado' # LNG
B16 = '🟣 Gas Natural Comprimido' # CNG
B17 = '🟢 Gasolina 95 E10'
B18 = '🟢 Gasolina 95 E25'
B19 = '🟢 Gasolina 95 E85'
B20 = '🔵 Gasolina 98 E10'
B21 = '🟢 Gasolina 95 E5 Premium'
B22 = '🔋 Hidrógeno'
B23 = '🌱 Biodiésel'
B24 = '🌱 Bioetanol'
B25 = '🌱 Gasolina Renovable'
B26 = '🌱 Diésel Renovable'
B27 = '🌱 Biogás Natural Comprimido'
B28 = '🌱 Biogás Natural Licuado'
B29 = '🔬 Amoníaco'
B30 = '🔬 Metanol'

# New feature buttons
B31 = '📊 Gráficos de precios'
B32 = '📍 Cerca de mí'
B33 = '🔔 Alertas de precio'
B34 = '📅 Última semana'
B35 = '📅 Último mes'
B36 = '🎯 5km radio'
B37 = '🎯 10km radio'
B38 = '✅ Crear alerta'
B39 = '❌ Eliminar alerta'
B40 = '📋 Mis alertas'

# Pagination buttons
B41 = '⬅️ Anterior'
B42 = '➡️ Siguiente'
B43 = '🔍 Buscar municipio'
B44 = '🏠 Inicio'

# Municipality buttons (first page - most populated)
B_MUN_1 = 'Santa Cruz de Tenerife'
B_MUN_2 = 'San Cristóbal de La Laguna'
B_MUN_3 = 'Arona'
B_MUN_4 = 'Adeje'
B_MUN_5 = 'Granadilla de Abona'
B_MUN_6 = 'Puerto de la Cruz'

# Callback data prefixes
TOWN_PREFIX = 'town_'
FUEL_PREFIX = 'fuel_'
CHART_PREFIX = 'chart_'
CHART_FUEL_PREFIX = 'chartfuel_'
LOCATION_PREFIX = 'location_'
ALERT_PREFIX = 'alert_'
PAGE_PREFIX = 'page_'
RESULT_PREFIX = 'result_'

# Messages
M_INSTRUCT = "▪️*Selecciona una opción:*"
M_CHART_SELECT = "📊 *Selecciona el combustible para ver la evolución de precios:*"
M_LOCATION_REQUEST = "📍 *Comparte tu ubicación para encontrar estaciones cerca*"
M_ALERT_SELECT = "🔔 *Gestiona tus alertas de precio:*"
M_MUNICIPALITY_SELECT = "🏘 *Selecciona un municipio* (orden alfabético):"
M_FUEL_SELECT = "*Selecciona un combustible:*"
M_SEARCH_MUNICIPALITY = "🔍 *Escribe el nombre del municipio a buscar:*"
M_NO_RESULTS = "😨❌ No hay datos disponibles en estos momentos"
M_LOADING = "⏳ Cargando datos..."
M_PAGE_INFO = "📍 Página {current} de {total}"

# Callback Data
(
    PREU, COMBUSTIBLE, POBLE, INFO, BARATES, CARES, INICI,
    CHARTS, LOCATION, ALERTS, MUNICIPALITIES, SEARCH_MUN, NEXT_PAGE, PREV_PAGE,
    NEXT_RESULTS, PREV_RESULTS
) = map(str, range(16))

# Fuel types mapping (internal name -> display name)
FUEL_TYPES = {
    # Most common fuels (shown first)
    'GASOLINA_95_E5': {
        'display': 'Gasolina 95 E5',
        'button': B8,
        'column': 'Precio_Gasolina_95_E5',
        'priority': 1
    },
    'GASOLEO_A': {
        'display': 'Gasóleo A', 
        'button': B9,
        'column': 'Precio_Gasoleo_A',
        'priority': 2
    },
    'GASOLINA_98_E5': {
        'display': 'Gasolina 98 E5',
        'button': B10,
        'column': 'Precio_Gasolina_98_E5', 
        'priority': 3
    },
    'GASOLEO_PREMIUM': {
        'display': 'Gasóleo Premium',
        'button': B11,
        'column': 'Precio_Gasoleo_Premium',
        'priority': 4
    },
    'GLP': {
        'display': 'GLP',
        'button': B12,
        'column': 'Precio_Gases_licuados_del_petroleo',
        'priority': 5
    },
    
    # Less common fuels
    'GASOLEO_B': {
        'display': 'Gasóleo B',
        'button': B13,
        'column': 'Precio_Gasoleo_B',
        'priority': 6
    },
    'ADBLUE': {
        'display': 'AdBlue',
        'button': B14,
        'column': 'Precio_Adblue',
        'priority': 7
    },
    'GAS_NATURAL_LICUADO': {
        'display': 'Gas Natural Licuado',
        'button': B15,
        'column': 'Precio_Gas_Natural_Licuado',
        'priority': 8
    },
    'GAS_NATURAL_COMPRIMIDO': {
        'display': 'Gas Natural Comprimido',
        'button': B16,
        'column': 'Precio_Gas_Natural_Comprimido',
        'priority': 9
    },
    'GASOLINA_95_E10': {
        'display': 'Gasolina 95 E10',
        'button': B17,
        'column': 'Precio_Gasolina_95_E10',
        'priority': 10
    },
    'GASOLINA_95_E25': {
        'display': 'Gasolina 95 E25',
        'button': B18,
        'column': 'Precio_Gasolina_95_E25',
        'priority': 11
    },
    'GASOLINA_95_E85': {
        'display': 'Gasolina 95 E85',
        'button': B19,
        'column': 'Precio_Gasolina_95_E85',
        'priority': 12
    },
    'GASOLINA_98_E10': {
        'display': 'Gasolina 98 E10',
        'button': B20,
        'column': 'Precio_Gasolina_98_E10',
        'priority': 13
    },
    'GASOLINA_95_E5_PREMIUM': {
        'display': 'Gasolina 95 E5 Premium',
        'button': B21,
        'column': 'Precio_Gasolina_95_E5_Premium',
        'priority': 14
    },
    'HIDROGENO': {
        'display': 'Hidrógeno',
        'button': B22,
        'column': 'Precio_Hidrogeno',
        'priority': 15
    },
    'BIODIESEL': {
        'display': 'Biodiésel',
        'button': B23,
        'column': 'Precio_Biodiesel',
        'priority': 16
    },
    'BIOETANOL': {
        'display': 'Bioetanol',
        'button': B24,
        'column': 'Precio_Bioetanol',
        'priority': 17
    },
    'GASOLINA_RENOVABLE': {
        'display': 'Gasolina Renovable',
        'button': B25,
        'column': 'Precio_Gasolina_Renovable',
        'priority': 18
    },
    'DIESEL_RENOVABLE': {
        'display': 'Diésel Renovable',
        'button': B26,
        'column': 'Precio_Diesel_Renovable',
        'priority': 19
    },
    'BIOGAS_NATURAL_COMPRIMIDO': {
        'display': 'Biogás Natural Comprimido',
        'button': B27,
        'column': 'Precio_Biogas_Natural_Comprimido',
        'priority': 20
    },
    'BIOGAS_NATURAL_LICUADO': {
        'display': 'Biogás Natural Licuado',
        'button': B28,
        'column': 'Precio_Biogas_Natural_Licuado',
        'priority': 21
    },
    'AMONIACO': {
        'display': 'Amoníaco',
        'button': B29,
        'column': 'Precio_Amoniaco',
        'priority': 22
    },
    'METANOL': {
        'display': 'Metanol',
        'button': B30,
        'column': 'Precio_Metanol',
        'priority': 23
    }
}

# Tenerife municipalities (all 31) with IDs - ALPHABETICAL ORDER
MUNICIPALITIES = {
    # Page 1 - A-C (6 municipalities: Adeje to Candelaria)
    'ADEJE': {
        'display': 'Adeje',
        'id': '5691',
        'priority': 1,
        'page': 1
    },
    'ARAFO': {
        'display': 'Arafo',
        'id': '5694',
        'priority': 2,
        'page': 1
    },
    'ARICO': {
        'display': 'Arico',
        'id': '5695',
        'priority': 3,
        'page': 1
    },
    'ARONA': {
        'display': 'Arona',
        'id': '5696',
        'priority': 4,
        'page': 1
    },
    'BUENAVISTA': {
        'display': 'Buenavista del Norte',
        'id': '5700',
        'priority': 5,
        'page': 1
    },
    'CANDELARIA': {
        'display': 'Candelaria',
        'id': '5701',
        'priority': 6,
        'page': 1
    },
    
    # Page 2 - E-G (6 municipalities: El Rosario to Granadilla)
    'EL_ROSARIO': {
        'display': 'El Rosario',
        'id': '5721',
        'priority': 7,
        'page': 2
    },
    'EL_SAUZAL': {
        'display': 'El Sauzal',
        'id': '5731',
        'priority': 8,
        'page': 2
    },
    'EL_TANQUE': {
        'display': 'El Tanque',
        'id': '5734',
        'priority': 9,
        'page': 2
    },
    'FASNIA': {
        'display': 'Fasnia',
        'id': '5702',
        'priority': 10,
        'page': 2
    },
    'GARACHICO': {
        'display': 'Garachico',
        'id': '5705',
        'priority': 11,
        'page': 2
    },
    'GRANADILLA': {
        'display': 'Granadilla de Abona',
        'id': '5707',
        'priority': 12,
        'page': 2
    },
    
    # Page 3 - G-L (6 municipalities: Guía de Isora to La Orotava)
    'GUIA_ISORA': {
        'display': 'Guía de Isora',
        'id': '5709',
        'priority': 13,
        'page': 3
    },
    'GUIMAR': {
        'display': 'Güímar',
        'id': '5710',
        'priority': 14,
        'page': 3
    },
    'ICOD_VINOS': {
        'display': 'Icod de los Vinos',
        'id': '5712',
        'priority': 15,
        'page': 3
    },
    'LA_GUANCHA': {
        'display': 'La Guancha',
        'id': '5708',
        'priority': 16,
        'page': 3
    },
    'LA_MATANZA': {
        'display': 'La Matanza de Acentejo',
        'id': '5714',
        'priority': 17,
        'page': 3
    },
    'LA_OROTAVA': {
        'display': 'La Orotava',
        'id': '5715',
        'priority': 18,
        'page': 3
    },
    
    # Page 4 - L-S (6 municipalities: La Victoria to San Juan)
    'LA_VICTORIA': {
        'display': 'La Victoria de Acentejo',
        'id': '5741',
        'priority': 19,
        'page': 4
    },
    'LOS_REALEJOS': {
        'display': 'Los Realejos',
        'id': '5720',
        'priority': 20,
        'page': 4
    },
    'LOS_SILOS': {
        'display': 'Los Silos',
        'id': '5732',
        'priority': 21,
        'page': 4
    },
    'PUERTO_CRUZ': {
        'display': 'Puerto de la Cruz',
        'id': '5717',
        'priority': 22,
        'page': 4
    },
    'LA_LAGUNA': {
        'display': 'San Cristóbal de La Laguna', 
        'id': '5723',
        'priority': 23,
        'page': 4
    },
    'SAN_JUAN_RAMBLA': {
        'display': 'San Juan de la Rambla',
        'id': '5724',
        'priority': 24,
        'page': 4
    },
    
    # Page 5 - S-V (7 municipalities: San Miguel to Vilaflor)
    'SAN_MIGUEL': {
        'display': 'San Miguel de Abona',
        'id': '5725',
        'priority': 25,
        'page': 5
    },
    'SANTA_CRUZ': {
        'display': 'Santa Cruz de Tenerife',
        'id': '5728',
        'priority': 26,
        'page': 5
    },
    'SANTA_URSULA': {
        'display': 'Santa Úrsula',
        'id': '5729',
        'priority': 27,
        'page': 5
    },
    'SANTIAGO_TEIDE': {
        'display': 'Santiago del Teide',
        'id': '5730',
        'priority': 28,
        'page': 5
    },
    'TACORONTE': {
        'display': 'Tacoronte',
        'id': '5733',
        'priority': 29,
        'page': 5
    },
    'TEGUESTE': {
        'display': 'Tegueste',
        'id': '5736',
        'priority': 30,
        'page': 5
    },
    'VILAFLOR': {
        'display': 'Vilaflor de Chasna',
        'id': '5742',
        'priority': 31,
        'page': 5
    }
}

# Pagination constants
MUNICIPALITIES_PER_PAGE = 6
TOTAL_MUNICIPALITY_PAGES = 5
RESULTS_PER_PAGE = 5

# Conversation States
NIVELL0, NIVELL1, NIVELL2, NIVELL3, SEARCH_STATE, ALERT_FUEL_SELECT, ALERT_PRICE_INPUT = range(7)

# Alert-related buttons
B_ALERT_CREATE = '🔔 Crear alerta de precio'
B_ALERT_LIST = '📋 Ver mis alertas'
B_ALERT_DELETE = '🗑️ Eliminar alerta'

# Alert messages
M_ALERT_CREATE_START = "🔔 *Crear alerta de precio*\n\nSelecciona el combustible para crear la alerta:"
M_ALERT_PRICE_INPUT = "💰 *Precio de alerta*\n\nEscribe el precio máximo (ej: 1.50) para recibir notificaciones cuando esté por debajo:"
M_ALERT_CREATED = "✅ *Alerta creada correctamente*\n\nTe notificaremos cuando el precio baje de {price}€ en {municipality}.\n\n💡 *Nota:* La alerta se eliminará automáticamente después de enviarte la notificación."
M_ALERT_LIST_EMPTY = "📋 *No tienes alertas activas*\n\nPuedes crear una nueva alerta desde cualquier municipio."

# Alert callback data  
ALERT_CREATE = f'{ALERT_PREFIX}CREATE'
ALERT_REMOVE = f'{ALERT_PREFIX}REMOVE'
ALERT_LIST = f'{ALERT_PREFIX}LIST'
ALERT_DELETE = f'{ALERT_PREFIX}DELETE'
ALERT_FUEL_SELECT = f'{ALERT_PREFIX}FUEL'

# Location callback data
LOCATION_5KM = f'{LOCATION_PREFIX}5KM'
LOCATION_10KM = f'{LOCATION_PREFIX}10KM'

# Chart callback data examples (can be generated dynamically)
CHART_GASOLINA_7 = f'{CHART_PREFIX}GASOLINA_95_E5_7'
CHART_GASOLINA_30 = f'{CHART_PREFIX}GASOLINA_95_E5_30' 