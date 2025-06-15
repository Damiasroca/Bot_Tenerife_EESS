import os
from telegram.ext import (Application, CommandHandler, ConversationHandler, CallbackQueryHandler, 
                         CallbackContext, PicklePersistence, InlineQueryHandler, MessageHandler, filters)
from telegram import (InlineKeyboardMarkup, InlineKeyboardButton, Update, InlineQueryResultArticle, 
                     InputTextMessageContent, KeyboardButton, ReplyKeyboardMarkup)
from telegram.constants import ParseMode
from data_manager_tenerife import tenerife_data_manager
import logging
import sys
import secret
from uuid import uuid4
from constants_tenerife import *
import datetime
from functools import wraps
import time
import telegram

# Setup logging
log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger()
logger.setLevel(logging.WARNING)

# Console handler
stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setFormatter(log_formatter)
logger.addHandler(stream_handler)

# File handler
try:
    log_file_path = "logs/main_bot_tenerife.log"
    os.makedirs(os.path.dirname(log_file_path), exist_ok=True)
    file_handler = logging.FileHandler(log_file_path)
    file_handler.setFormatter(log_formatter)
    logger.addHandler(file_handler)
    logger.info(f"Logging to {log_file_path}")
except (OSError, IOError) as e:
    logger.warning(f"Could not set up file logging: {e}")

def create_back_to_main_keyboard():
    """Create a standard 'Back to Main Menu' keyboard for standalone messages."""
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🏠 Menú Principal", callback_data=str(INICI))
    ]])

def create_back_keyboard(callback_data):
    """Create a back button with custom callback data."""
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(B5, callback_data=callback_data)
    ]])

def error_handler(func):
    @wraps(func)
    async def wrapper(update: Update, context: CallbackContext, *args, **kwargs):
        try:
            # Track user interaction
            track_user_from_update(update)
            return await func(update, context, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error in handler {func.__name__}: {e}", exc_info=True)
            if query := update.callback_query:
                await query.answer(text="Ocurrió un error. Inténtalo de nuevo.", show_alert=True)
            elif update.message:
                await update.message.reply_text(
                    "Ocurrió un error. Por favor, inténtalo de nuevo.",
                    reply_markup=create_back_to_main_keyboard()
                )
            return ConversationHandler.END
    return wrapper

def track_user_from_update(update: Update):
    """Extract user info from update and track interaction."""
    try:
        user = None
        if update.message:
            user = update.message.from_user
        elif update.callback_query:
            user = update.callback_query.from_user
        elif update.inline_query:
            user = update.inline_query.from_user
            
        if user:
            tenerife_data_manager.track_user_interaction(
                user_id=user.id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name,
                language_code=user.language_code
            )
    except Exception as e:
        logger.error(f"Error tracking user interaction: {e}")

def format_station_message(station, show_fuels=None):
    """Format a station message with specified fuel types."""
    if show_fuels is None:
        show_fuels = ['precio_gasolina_95_e5', 'precio_gasoleo_a']
    
    # Create Google Maps link
    if station.get('latitud') and station.get('longitud_wgs84'):
        lat = str(station['latitud']).replace(',', '.')
        lon = str(station['longitud_wgs84']).replace(',', '.')
        maps_link = f'https://www.google.com/maps/@{lat},{lon},20z'
        header = f"🔸*{station.get('rotulo', 'Sin nombre')}*\n[{station.get('direccion', 'Sin dirección')}]({maps_link})"
    else:
        header = f"🔸*{station.get('rotulo', 'Sin nombre')}*\n{station.get('direccion', 'Sin dirección')}"
    
    # Add location info
    if station.get('localidad'):
        header += f"\n📍 {station['localidad']}"
    
    # Add fuel prices
    fuel_lines = []
    for fuel_col in show_fuels:
        if fuel_col in station and station[fuel_col] is not None and station[fuel_col] > 0:
            # Get display name for fuel type
            fuel_display = fuel_col.replace('precio_', '').replace('_', ' ').title()
            fuel_display = fuel_display.replace('95 E5', '95 E5').replace('Gasoleo', 'Gasóleo')
            if fuel_col == 'precio_gasolina_95_e5':
                fuel_display = 'Gasolina 95 E5'
            elif fuel_col == 'precio_gasoleo_a':
                fuel_display = 'Gasóleo A'
            elif fuel_col == 'precio_gasolina_98_e5':
                fuel_display = 'Gasolina 98 E5'
            elif fuel_col == 'precio_gasoleo_premium':
                fuel_display = 'Gasóleo Premium'
            elif fuel_col == 'precio_gases_licuados_del_petroleo':
                fuel_display = 'GLP'
            
            fuel_lines.append(f"{fuel_display}: *{station[fuel_col]}€*")
    
    if fuel_lines:
        header += "\n" + "\n".join(fuel_lines)
    
    # Add opening hours if available
    if station.get('horario'):
        header += f"\n⏰ {station['horario']}"
    
    return header

def get_municipality_buttons(page=1):
    """Get municipality buttons for a specific page."""
    municipalities_on_page = [(k, v) for k, v in MUNICIPALITIES.items() if v['page'] == page]
    municipalities_on_page.sort(key=lambda x: x[1]['priority'])
    
    buttons = []
    row = []
    
    for muni_key, muni_info in municipalities_on_page:
        button = InlineKeyboardButton(
            muni_info['display'], 
            callback_data=f"{TOWN_PREFIX}{muni_key}"
        )
        row.append(button)
        
        # Create rows of 2 buttons each
        if len(row) == 2:
            buttons.append(row)
            row = []
    
    # Add remaining buttons if any
    if row:
        buttons.append(row)
    
    # Add navigation buttons
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton(B41, callback_data=f"{PAGE_PREFIX}{page-1}"))
    if page < TOTAL_MUNICIPALITY_PAGES:
        nav_buttons.append(InlineKeyboardButton(B42, callback_data=f"{PAGE_PREFIX}{page+1}"))
    
    if nav_buttons:
        buttons.append(nav_buttons)
    
    # Add search and back buttons
    buttons.append([
        InlineKeyboardButton(B43, callback_data=str(SEARCH_MUN)),
        InlineKeyboardButton(B5, callback_data=str(INICI))
    ])
    
    return buttons

def get_fuel_buttons(page=1, per_page=10):
    """Get fuel type buttons ordered by popularity."""
    available_fuels = tenerife_data_manager.get_available_fuel_types()
    
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    page_fuels = available_fuels[start_idx:end_idx]
    
    buttons = []
    row = []
    
    for fuel in page_fuels:
        button = InlineKeyboardButton(
            f"{fuel['button']} ({fuel['stations_count']})",
            callback_data=f"{FUEL_PREFIX}{fuel['key']}"
        )
        row.append(button)
        
        # Create rows of 2 buttons each
        if len(row) == 2:
            buttons.append(row)
            row = []
    
    # Add remaining button if any
    if row:
        buttons.append(row)
    
    # Add navigation for fuel types if needed (should not be needed now)
    total_pages = (len(available_fuels) + per_page - 1) // per_page
    if total_pages > 1:
        nav_buttons = []
        if page > 1:
            nav_buttons.append(InlineKeyboardButton("⬅️", callback_data=f"fuelpage_{page-1}"))
        nav_buttons.append(InlineKeyboardButton(f"{page}/{total_pages}", callback_data="noop"))
        if page < total_pages:
            nav_buttons.append(InlineKeyboardButton("➡️", callback_data=f"fuelpage_{page+1}"))
        buttons.append(nav_buttons)
    
    # Add back button
    buttons.append([InlineKeyboardButton(B5, callback_data=str(INICI))])
    
    return buttons

@error_handler
async def start(update: Update, context: CallbackContext):
    user = update.message.from_user
    
    # Check if user has existing data (persistence working)
    existing_data = context.user_data
    if existing_data:
        logger.info(f"User {user.id} has existing data: {list(existing_data.keys())}")
        print(f"🔄 Restored data for user {user.id}: {list(existing_data.keys())}")
    else:
        print(f"🆕 New user session for {user.id}")
    
    welcome_msg = f"¡Bienvenido *{user.first_name}*! 🚗⛽\n"
    welcome_msg += "¡Más combustible por menos dinero!\n"
    welcome_msg += "Precios actualizados cada 10 minutos."

    button1 = InlineKeyboardButton(B1, callback_data=str(PREU))
    button2 = InlineKeyboardButton(B2, callback_data=str(COMBUSTIBLE))
    button3 = InlineKeyboardButton(B3, callback_data=str(POBLE))
    button4 = InlineKeyboardButton(B4, callback_data=str(INFO))
    button31 = InlineKeyboardButton(B31, callback_data=str(CHARTS))
    button32 = InlineKeyboardButton(B32, callback_data=str(LOCATION))
    button33 = InlineKeyboardButton(B33, callback_data=str(ALERTS))

    await update.message.reply_text(
        text=M_INSTRUCT, parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([
            [button1, button2],
            [button3, button4],
            [button31, button32],
            [button33]
        ])
    )
    return NIVELL1

@error_handler
async def start_over(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    button1 = InlineKeyboardButton(B1, callback_data=str(PREU))
    button2 = InlineKeyboardButton(B2, callback_data=str(COMBUSTIBLE))
    button3 = InlineKeyboardButton(B3, callback_data=str(POBLE))
    button4 = InlineKeyboardButton(B4, callback_data=str(INFO))
    button31 = InlineKeyboardButton(B31, callback_data=str(CHARTS))
    button32 = InlineKeyboardButton(B32, callback_data=str(LOCATION))
    button33 = InlineKeyboardButton(B33, callback_data=str(ALERTS))

    keyboard = InlineKeyboardMarkup([
        [button1, button2],
        [button3, button4],
        [button31, button32],
        [button33]
    ])

    try:
        # Try to edit the existing message. This works for text messages.
        await query.edit_message_text(
            text=M_INSTRUCT,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard
        )
    except telegram.error.BadRequest as e:
        # If the original message has no text (e.g., it's a photo), this error occurs.
        if 'There is no text in the message to edit' in str(e):
            # Send a new message with the main menu.
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=M_INSTRUCT,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=keyboard
            )
            # And try to remove the buttons from the old message so the user can't click them again.
            try:
                await query.edit_message_reply_markup(reply_markup=None)
            except Exception:
                pass  # It's not critical if this fails.
        else:
            # If it's a different kind of error, we should know about it.
            logger.error(f"Unhandled BadRequest in start_over: {e}")
            raise e

    return NIVELL1

@error_handler
async def price_menu(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    
    button5 = InlineKeyboardButton(B5, callback_data=str(INICI))
    button6 = InlineKeyboardButton(B6, callback_data=str(BARATES))
    button7 = InlineKeyboardButton(B7, callback_data=str(CARES))
    
    await query.edit_message_text(
        text="*Selecciona una opción:*", parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([
            [button6, button7],
            [button5]
        ])
    )
    return NIVELL2

@error_handler
async def cheapest_stations(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    
    # Get 5 cheapest stations for Gasolina 95 E5
    cheap_stations = tenerife_data_manager.get_stations_by_fuel_ascending('GASOLINA_95_E5', limit=5)
    
    if cheap_stations.empty:
        message = M_NO_RESULTS
    else:
        messages = []
        for _, station in cheap_stations.iterrows():
            station_msg = format_station_message(
                station.to_dict(), 
                ['precio_gasolina_95_e5', 'precio_gasoleo_a']
            )
            messages.append(station_msg)
        message = "\n\n".join(messages)
    
    button5 = InlineKeyboardButton(B5, callback_data=str(PREU))
    await query.edit_message_text(
        text=message, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True,
        reply_markup=InlineKeyboardMarkup([[button5]])
    )
    return NIVELL1

@error_handler
async def most_expensive_stations(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    
    # Get 5 most expensive stations for Gasolina 95 E5
    expensive_stations = tenerife_data_manager.get_stations_by_fuel_descending('GASOLINA_95_E5', limit=5)
    
    if expensive_stations.empty:
        message = M_NO_RESULTS
    else:
        messages = []
        for _, station in expensive_stations.iterrows():
            station_msg = format_station_message(
                station.to_dict(), 
                ['precio_gasolina_95_e5', 'precio_gasoleo_a']
            )
            messages.append(station_msg)
        message = "\n\n".join(messages)
    
    button5 = InlineKeyboardButton(B5, callback_data=str(PREU))
    await query.edit_message_text(
        text=message, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True,
        reply_markup=InlineKeyboardMarkup([[button5]])
    )
    return NIVELL1

@error_handler
async def fuel_type_menu(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    
    fuel_buttons = get_fuel_buttons(page=1)
    
    await query.edit_message_text(
        text=M_FUEL_SELECT, parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(fuel_buttons)
    )
    return NIVELL2

@error_handler
async def fuel_page_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    
    # Extract page number from callback data (fuelpage_X)
    page = int(query.data.split('_')[1])
    
    fuel_buttons = get_fuel_buttons(page=page)
    
    await query.edit_message_text(
        text=M_FUEL_SELECT, parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(fuel_buttons)
    )
    return NIVELL2

@error_handler
async def municipality_menu(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    
    # Get current page from user data, default to 1
    current_page = context.user_data.get('municipality_page', 1)
    municipality_buttons = get_municipality_buttons(current_page)
    
    # Define alphabetical ranges for each page
    page_ranges = {
        1: "A-C (Adeje → Candelaria)",
        2: "E-G (El Rosario → Granadilla)",
        3: "G-L (Guía de Isora → La Orotava)",
        4: "L-S (La Victoria → San Juan)",
        5: "S-V (San Miguel → Vilaflor)"
    }
    
    page_info = f"📍 Página {current_page} de {TOTAL_MUNICIPALITY_PAGES} • {page_ranges[current_page]}"
    message = f"{M_MUNICIPALITY_SELECT}\n{page_info}"
    
    await query.edit_message_text(
        text=message, parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(municipality_buttons)
    )
    return NIVELL2

@error_handler
async def municipality_page_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    
    # Extract page number from callback data
    page = int(query.data.split('_')[1])
    context.user_data['municipality_page'] = page
    
    municipality_buttons = get_municipality_buttons(page)
    
    # Define alphabetical ranges for each page
    page_ranges = {
        1: "A-C (Adeje → Candelaria)",
        2: "E-G (El Rosario → Granadilla)",
        3: "G-L (Guía de Isora → La Orotava)",
        4: "L-S (La Victoria → San Juan)",
        5: "S-V (San Miguel → Vilaflor)"
    }
    
    page_info = f"📍 Página {page} de {TOTAL_MUNICIPALITY_PAGES} • {page_ranges[page]}"
    message = f"{M_MUNICIPALITY_SELECT}\n{page_info}"
    
    await query.edit_message_text(
        text=message, parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(municipality_buttons)
    )
    return NIVELL2

@error_handler
async def search_municipality_start(update: Update, context: CallbackContext):
    """Start municipality search process."""
    query = update.callback_query
    await query.answer()
    
    # Set search state
    context.user_data['search_mode'] = 'municipality'
    
    # Create back button
    back_button = InlineKeyboardButton(B5, callback_data=str(POBLE))
    
    await query.edit_message_text(
        text=M_SEARCH_MUNICIPALITY,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([[back_button]])
    )
    return SEARCH_STATE

@error_handler
async def handle_search_input(update: Update, context: CallbackContext):
    """Handle search text input."""
    search_term = update.message.text.strip()
    search_mode = context.user_data.get('search_mode')
    
    if search_mode != 'municipality':
        return  # Not in search mode
    
    # Clear search mode
    context.user_data.pop('search_mode', None)
    
    if len(search_term) < 2:
        await update.message.reply_text(
            "❌ Por favor, escribe al menos 2 caracteres para buscar.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(B5, callback_data=str(POBLE))
            ]])
        )
        return NIVELL2
    
    # Search municipalities
    matches = tenerife_data_manager.search_municipalities(search_term)
    
    if not matches:
        await update.message.reply_text(
            f"❌ No se encontraron municipios que contengan '{search_term}'.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(B5, callback_data=str(POBLE))
            ]])
        )
        return NIVELL2
    
    # Create buttons for found municipalities
    buttons = []
    for muni_key, muni_display in matches[:10]:  # Limit to 10 results
        buttons.append([InlineKeyboardButton(
            muni_display,
            callback_data=f"{TOWN_PREFIX}{muni_key}"
        )])
    
    # Add back button
    buttons.append([InlineKeyboardButton(B5, callback_data=str(POBLE))])
    
    result_msg = f"🔍 *Resultados para '{search_term}'* ({len(matches)} encontrados):"
    if len(matches) > 10:
        result_msg += f"\n_Mostrando los primeros 10 resultados._"
    
    await update.message.reply_text(
        text=result_msg,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    return NIVELL2

@error_handler
async def municipality_info(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    
    # Extract municipality key from callback data
    municipality_key = query.data.replace(f'{TOWN_PREFIX}', '')
    
    # Store municipality and reset result page for pagination
    context.user_data['current_municipality'] = municipality_key
    context.user_data['result_page'] = 0
    
    # Get first page of results
    stations_data, total_count = tenerife_data_manager.get_stations_by_municipality(
        municipality_key, offset=0, limit=RESULTS_PER_PAGE
    )
    
    if stations_data.empty:
        message = f"No hay estaciones disponibles en {MUNICIPALITIES[municipality_key]['display']}"
        buttons = [[InlineKeyboardButton(B5, callback_data=str(POBLE))]]
    else:
        messages = []
        for _, station in stations_data.iterrows():
            station_msg = format_station_message(
                station.to_dict(),
                ['precio_gasolina_95_e5', 'precio_gasoleo_a', 'precio_gasolina_98_e5']
            )
            messages.append(station_msg)
        
        message = "\n\n".join(messages)
        
        # Add pagination info
        current_page = 1
        total_pages = (total_count + RESULTS_PER_PAGE - 1) // RESULTS_PER_PAGE
        if total_pages > 1:
            message += f"\n\n📄 Página {current_page} de {total_pages} ({total_count} estaciones)"
        
        # Create pagination buttons
        buttons = []
        nav_buttons = []
        
        if total_pages > 1:
            if current_page < total_pages:
                nav_buttons.append(InlineKeyboardButton("➡️ Siguiente", callback_data=f"{RESULT_PREFIX}next"))
        
        if nav_buttons:
            buttons.append(nav_buttons)
        
        # Add alert button for this municipality
        alert_button = InlineKeyboardButton(
            B_ALERT_CREATE, 
            callback_data=f"{ALERT_PREFIX}CREATE_{municipality_key}"
        )
        buttons.append([alert_button])
        
        buttons.append([InlineKeyboardButton(B5, callback_data=str(POBLE))])
    
    await query.edit_message_text(
        text=message, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True,
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    return NIVELL1

@error_handler
async def result_pagination_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    
    action = query.data.split('_')[1]
    municipality_key = context.user_data.get('current_municipality')
    current_page = context.user_data.get('result_page', 0)
    
    if not municipality_key:
        await query.answer("Error: no se encontró el municipio.")
        return NIVELL1
    
    # Calculate new page
    if action == 'next':
        new_page = current_page + 1
    elif action == 'prev':
        new_page = max(0, current_page - 1)
    else:
        new_page = current_page
    
    context.user_data['result_page'] = new_page
    offset = new_page * RESULTS_PER_PAGE
    
    # Get stations for new page
    stations_data, total_count = tenerife_data_manager.get_stations_by_municipality(
        municipality_key, offset=offset, limit=RESULTS_PER_PAGE
    )
    
    if stations_data.empty:
        message = "No hay más estaciones disponibles."
        buttons = [[InlineKeyboardButton(B5, callback_data=str(POBLE))]]
    else:
        messages = []
        for _, station in stations_data.iterrows():
            station_msg = format_station_message(
                station.to_dict(),
                ['precio_gasolina_95_e5', 'precio_gasoleo_a', 'precio_gasolina_98_e5']
            )
            messages.append(station_msg)
        
        message = "\n\n".join(messages)
        
        # Add pagination info
        current_page_display = new_page + 1
        total_pages = (total_count + RESULTS_PER_PAGE - 1) // RESULTS_PER_PAGE
        message += f"\n\n📄 Página {current_page_display} de {total_pages} ({total_count} estaciones)"
        
        # Create pagination buttons
        buttons = []
        nav_buttons = []
        
        if new_page > 0:
            nav_buttons.append(InlineKeyboardButton("⬅️ Anterior", callback_data=f"{RESULT_PREFIX}prev"))
        if current_page_display < total_pages:
            nav_buttons.append(InlineKeyboardButton("➡️ Siguiente", callback_data=f"{RESULT_PREFIX}next"))
        
        if nav_buttons:
            buttons.append(nav_buttons)
        
        buttons.append([InlineKeyboardButton(B5, callback_data=str(POBLE))])
    
    await query.edit_message_text(
        text=message, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True,
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    return NIVELL1

@error_handler
async def fuel_info(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    
    # Extract fuel type from callback data - fix parsing for keys with underscores
    fuel_type = query.data.replace(f'{FUEL_PREFIX}', '')
    
    # Get 5 cheapest stations for this fuel type
    cheap_stations = tenerife_data_manager.get_stations_by_fuel_ascending(fuel_type, limit=5)
    
    if cheap_stations.empty:
        message = f"No hay datos disponibles para {FUEL_TYPES.get(fuel_type, {}).get('display', fuel_type)}"
    else:
        fuel_display = FUEL_TYPES[fuel_type]['display']
        fuel_column = FUEL_TYPES[fuel_type]['column'].lower()
        
        messages = [f"*🔝 5 más baratas - {fuel_display}*\n"]
        
        for _, station in cheap_stations.iterrows():
            station_msg = format_station_message(
                station.to_dict(),
                [fuel_column]
            )
            messages.append(station_msg)
        
        message = "\n\n".join(messages)
    
    button5 = InlineKeyboardButton(B5, callback_data=str(COMBUSTIBLE))
    await query.edit_message_text(
        text=message, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True,
        reply_markup=InlineKeyboardMarkup([[button5]])
    )
    return NIVELL1

@error_handler
async def info(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    
    info_message = (
        "Datos extraídos del *Ministerio de Industria, Comercio y Turismo*.\n\n"
        "Se ha comprobado que algunas ubicaciones pueden no ser completamente precisas.\n"
        "Los errores han sido notificados.\n\n"
        f"*Última actualización:* {tenerife_data_manager.get_last_update_time()}\n\n"
        "Bot desarrollado para Tenerife.\n"
        "Código disponible en [GitHub](https://github.com/Damiasroca/Bot_Tenerife_EESS)"
    )
    
    button5 = InlineKeyboardButton(B5, callback_data=str(INICI))
    await query.edit_message_text(
        text=info_message, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=False,
        reply_markup=InlineKeyboardMarkup([[button5]])
    )
    return NIVELL1

@error_handler
async def location_search(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    
    # Request location
    location_keyboard = [[KeyboardButton("📍 Compartir ubicación", request_location=True)]]
    reply_markup = ReplyKeyboardMarkup(location_keyboard, one_time_keyboard=True, resize_keyboard=True)
    
    await query.edit_message_text(M_LOCATION_REQUEST, parse_mode=ParseMode.MARKDOWN)
    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text="👇 Usa el botón de abajo para compartir tu ubicación:",
        reply_markup=reply_markup
    )
    
    # Also send navigation buttons in case user doesn't want to share location
    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text="🔄 O regresa al menú principal:",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🏠 Menú Principal", callback_data=str(INICI))
        ]])
    )
    
    return NIVELL2

@error_handler
async def handle_location(update: Update, context: CallbackContext):
    user_location = update.message.location
    
    # Remove keyboard and show searching message with navigation
    await update.message.reply_text(
        "🔍 Buscando las estaciones más baratas en un radio de 10km...",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🏠 Menú Principal", callback_data=str(INICI))
        ]])
    )
    
    # Find nearby stations within a 10km radius.
    # The data manager sorts them by price ascending.
    nearby_stations = tenerife_data_manager.find_stations_near_location(
        user_location.latitude, user_location.longitude, radius_km=10
    )
    
    if not nearby_stations:
        message = "😔 No se encontraron estaciones en un radio de 10km."
        buttons = [[InlineKeyboardButton("🏠 Menú Principal", callback_data=str(INICI))]]
    else:

        messages = ["*⛽ Estaciones más baratas en 10km (Gasolina 95 E5)*\n"]
        
        for station in nearby_stations[:7]:  # Limit to 7 closest/cheapest
            station_msg = format_station_message(
                station,
                ['precio_gasolina_95_e5', 'precio_gasoleo_a']
            )
            station_msg += f"\n📏 *{station['distance']}km*"
            messages.append(station_msg)
        
        message = "\n\n".join(messages)
        buttons = [[InlineKeyboardButton(B5, callback_data=str(INICI))]]
    
    await update.message.reply_text(
        message, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True,
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    
    return NIVELL1

@error_handler
async def status_command(update: Update, context: CallbackContext):
    """Debug command to check persistence status."""
    user = update.message.from_user
    user_data = context.user_data
    
    status_msg = f"🔍 **Status Debug for {user.first_name}**\n\n"
    status_msg += f"User ID: `{user.id}`\n"
    status_msg += f"User data keys: `{list(user_data.keys()) if user_data else 'None'}`\n"
    status_msg += f"Current page (municipality): `{user_data.get('municipality_page', 'Not set')}`\n"
    status_msg += f"Current municipality: `{user_data.get('current_municipality', 'Not set')}`\n"
    status_msg += f"Result page: `{user_data.get('result_page', 'Not set')}`\n"
    
    # Test persistence by setting a test value
    test_time = int(time.time())
    user_data['last_status_check'] = test_time
    status_msg += f"\n✅ Set test value: `{test_time}`\n"
    status_msg += "Restart the bot and run /status again to verify persistence."
    
    await update.message.reply_text(
        status_msg, 
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=create_back_to_main_keyboard()
    )

@error_handler
async def get_id_command(update: Update, context: CallbackContext):
    """Simple command to get user's Telegram ID for admin setup."""
    user = update.message.from_user
    
    # Use HTML formatting instead of Markdown - much more robust
    def escape_html(text):
        if not text:
            return "Unknown"
        return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    
    id_msg = f"🆔 <b>Your Telegram Information</b>\n\n"
    id_msg += f"<b>User ID:</b> <code>{user.id}</code>\n"
    id_msg += f"<b>First Name:</b> {escape_html(user.first_name)}\n"
    if user.last_name:
        id_msg += f"<b>Last Name:</b> {escape_html(user.last_name)}\n"
    if user.username:
        id_msg += f"<b>Username:</b> @{escape_html(user.username)}\n"
    id_msg += f"<b>Language:</b> {user.language_code or 'Unknown'}\n\n"
    
    id_msg += f"💡 <b>For Admin Setup:</b>\n"
    id_msg += f"Copy this User ID: <code>{user.id}</code>\n"
    id_msg += f"See ADMIN_SETUP.md for instructions."
    
    await update.message.reply_text(
        id_msg, 
        parse_mode=ParseMode.HTML,
        reply_markup=create_back_to_main_keyboard()
    )

@error_handler
async def charts_menu(update: Update, context: CallbackContext):
    """Show charts menu with fuel type selection."""
    query = update.callback_query
    await query.answer()
    
    # Get top fuel types for charts
    fuel_buttons = []
    top_fuels = [
        ('GASOLINA_95_E5', '🟢 Gasolina 95 E5'),
        ('GASOLEO_A', '⚫️ Gasóleo A'),
        ('GASOLINA_98_E5', '🔵 Gasolina 98 E5'),
        ('GASOLEO_PREMIUM', '🟠 Gasóleo Premium'),
        ('GLP', '⚪️ GLP'),
        ('GASOLEO_B', '🟤 Gasóleo B')
    ]
    
    for fuel_key, fuel_display in top_fuels:
        # Create buttons for different time periods
        fuel_buttons.append([
            InlineKeyboardButton(
                f"{fuel_display} (7 días)",
                callback_data=f"{CHART_PREFIX}{fuel_key}_7"
            ),
            InlineKeyboardButton(
                f"{fuel_display} (30 días)",
                callback_data=f"{CHART_PREFIX}{fuel_key}_30"
            )
        ])
    
    # Add back button
    fuel_buttons.append([InlineKeyboardButton(B5, callback_data=str(INICI))])
    
    await query.edit_message_text(
        text=M_CHART_SELECT,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(fuel_buttons)
    )
    return NIVELL2

@error_handler
async def generate_chart(update: Update, context: CallbackContext):
    """Generate and send price evolution chart."""
    query = update.callback_query
    await query.answer()
    
    # Parse callback data: chart_FUEL_TYPE_DAYS
    callback_parts = query.data.split('_')
    if len(callback_parts) < 3:
        await query.answer("Error en los datos del gráfico.")
        return NIVELL1
    
    fuel_type = '_'.join(callback_parts[1:-1])  # Handle fuel types with underscores
    days = int(callback_parts[-1])
    
    # Show loading message with navigation
    await query.edit_message_text(
        "📊 Generando gráfico... Por favor espera.",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton(B5, callback_data=str(CHARTS))
        ]])
    )
    
    try:
        # Generate chart using data manager
        chart_path = tenerife_data_manager.generate_price_chart(fuel_type, days)
        
        if chart_path and os.path.exists(chart_path):
            # Send chart as photo with navigation buttons
            chart_buttons = InlineKeyboardMarkup([
                [InlineKeyboardButton("🏠 Menú Principal", callback_data=str(INICI))]
            ])
            
            with open(chart_path, 'rb') as chart_file:
                await context.bot.send_photo(
                    chat_id=query.message.chat_id,
                    photo=chart_file,
                    caption=f"📊 Evolución de precios - {FUEL_TYPES.get(fuel_type, {}).get('display', fuel_type)} ({days} días)",
                    reply_markup=chart_buttons
                )
            
            # Clean up chart file
            try:
                os.remove(chart_path)
            except:
                pass
            
            await query.delete_message()
        else:
            await query.edit_message_text(
                "❌ No hay suficientes datos históricos para generar el gráfico.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🏠 Menú Principal", callback_data=str(INICI))
                ]])
            )
    
    except Exception as e:
        logger.error(f"Error generating chart: {e}")
        await query.edit_message_text(
            "❌ Error al generar el gráfico. Inténtalo más tarde.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🏠 Menú Principal", callback_data=str(INICI))
            ]])
        )
    
    return NIVELL2

# Admin Commands System
ADMIN_USER_IDS = secret.secret.get('admin_user_ids', [])  # Read admin IDs from secret.py

def is_admin(user_id):
    """Check if user is an admin."""
    return user_id in ADMIN_USER_IDS

def admin_required(func):
    """Decorator to require admin privileges."""
    @wraps(func)
    async def wrapper(update: Update, context: CallbackContext, *args, **kwargs):
        user = update.message.from_user
        if not is_admin(user.id):
            await update.message.reply_text(
                "❌ Access denied. This command requires admin privileges.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=create_back_to_main_keyboard()
            )
            return
        return await func(update, context, *args, **kwargs)
    return wrapper

@admin_required
async def admin_stats(update: Update, context: CallbackContext):
    """Admin command to show bot usage statistics."""
    try:
        stats = tenerife_data_manager.get_admin_statistics()
        
        stats_msg = "📊 **Admin Dashboard - Bot Statistics**\n\n"
        stats_msg += f"👥 **Users:**\n"
        stats_msg += f"• Total users: {stats['total_users']}\n"
        stats_msg += f"• Active users (last 7 days): {stats['active_users_7d']}\n"
        stats_msg += f"• Active users (last 30 days): {stats['active_users_30d']}\n"
        stats_msg += f"• New users today: {stats['new_users_today']}\n\n"
        
        stats_msg += f"📈 **Interactions:**\n"
        stats_msg += f"• Total interactions: {stats['total_interactions']}\n"
        stats_msg += f"• Interactions today: {stats['interactions_today']}\n"
        stats_msg += f"• Average interactions per user: {stats['avg_interactions']:.1f}\n\n"
        
        stats_msg += f"🗄️ **Database:**\n"
        stats_msg += f"• Fuel stations: {stats['station_count']}\n"
        stats_msg += f"• Historical records: {stats['historical_count']}\n"
        stats_msg += f"• Last data update: {stats['last_update']}\n\n"
        
        stats_msg += f"🏆 **Top Municipalities:**\n"
        for i, (muni, count) in enumerate(stats['top_municipalities'][:5], 1):
            stats_msg += f"  {i}. {muni}: {count} stations\n"
        
        await update.message.reply_text(
            stats_msg, 
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=create_back_to_main_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Error in admin_stats: {e}")
        await update.message.reply_text(
            f"❌ Error retrieving statistics: {e}",
            reply_markup=create_back_to_main_keyboard()
        )

@admin_required
async def admin_users(update: Update, context: CallbackContext):
    """Admin command to show recent user activity."""
    try:
        # Get limit from command args, default to 20
        args = context.args
        limit = int(args[0]) if args and args[0].isdigit() else 20
        limit = min(limit, 100)  # Max 100 users
        
        users = tenerife_data_manager.get_recent_users(limit=limit)
        
        users_msg = f"👥 **Recent Users (last {limit})**\n\n"
        
        for i, user in enumerate(users, 1):
            user_id = user['user_id']
            username = f"@{user['username']}" if user['username'] else "No username"
            first_name = user['first_name'] or "Unknown"
            interactions = user['interaction_count']
            last_seen = user['last_seen'].strftime("%d/%m %H:%M") if user['last_seen'] else "Never"
            
            users_msg += f"{i}. **{first_name}** ({username})\n"
            users_msg += f"   ID: `{user_id}` | Interactions: {interactions}\n"
            users_msg += f"   Last seen: {last_seen}\n\n"
        
        users_msg += f"📝 Use `/admin_users [number]` to show more/fewer users (max 100)"
        
        await update.message.reply_text(
            users_msg, 
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=create_back_to_main_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Error in admin_users: {e}")
        await update.message.reply_text(
            f"❌ Error retrieving users: {e}",
            reply_markup=create_back_to_main_keyboard()
        )

@admin_required
async def admin_user_info(update: Update, context: CallbackContext):
    """Admin command to show detailed info about a specific user."""
    try:
        args = context.args
        if not args:
            await update.message.reply_text(
                "📝 Usage: `/admin_user [user_id]`\nExample: `/admin_user 123456789`",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=create_back_to_main_keyboard()
            )
            return
        
        user_id = int(args[0])
        user_info = tenerife_data_manager.get_user_details(user_id)
        
        if not user_info:
            await update.message.reply_text(
                f"❌ User ID {user_id} not found in database.",
                reply_markup=create_back_to_main_keyboard()
            )
            return
        
        info_msg = f"👤 **User Details**\n\n"
        info_msg += f"**Name:** {user_info['first_name']} {user_info['last_name'] or ''}".strip() + "\n"
        info_msg += f"**Username:** @{user_info['username']}" if user_info['username'] else "**Username:** No username\n"
        info_msg += f"**User ID:** `{user_info['user_id']}`\n"
        info_msg += f"**Language:** {user_info['language_code'] or 'Unknown'}\n\n"
        
        info_msg += f"📊 **Activity:**\n"
        info_msg += f"• Total interactions: {user_info['interaction_count']}\n"
        info_msg += f"• First seen: {user_info['first_seen'].strftime('%d/%m/%Y %H:%M')}\n"
        info_msg += f"• Last seen: {user_info['last_seen'].strftime('%d/%m/%Y %H:%M')}\n"
        info_msg += f"• Status: {'🟢 Active' if user_info['is_active'] else '🔴 Inactive'}\n"
        
        await update.message.reply_text(
            info_msg, 
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=create_back_to_main_keyboard()
        )
        
    except ValueError:
        await update.message.reply_text(
            "❌ Invalid user ID. Please provide a numeric user ID.",
            reply_markup=create_back_to_main_keyboard()
        )
    except Exception as e:
        logger.error(f"Error in admin_user_info: {e}")
        await update.message.reply_text(
            f"❌ Error retrieving user info: {e}",
            reply_markup=create_back_to_main_keyboard()
        )

@admin_required
async def admin_broadcast(update: Update, context: CallbackContext):
    """Admin command to broadcast a message to all users."""
    try:
        # Get message from command args
        args = context.args
        if not args:
            await update.message.reply_text(
                "📝 Usage: `/admin_broadcast [message]`\n"
                "Example: `/admin_broadcast Hello everyone! Bot maintenance at 10pm.`",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=create_back_to_main_keyboard()
            )
            return
        
        broadcast_message = " ".join(args)
        
        # Confirm broadcast
        confirm_msg = f"📢 **Broadcast Confirmation**\n\n"
        confirm_msg += f"Message: _{broadcast_message}_\n\n"
        confirm_msg += f"This will be sent to all bot users. Reply with 'CONFIRM' to proceed."
        
        # Store broadcast message in user data for confirmation
        context.user_data['pending_broadcast'] = broadcast_message
        
        await update.message.reply_text(
            confirm_msg, 
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=create_back_to_main_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Error in admin_broadcast: {e}")
        await update.message.reply_text(
            f"❌ Error preparing broadcast: {e}",
            reply_markup=create_back_to_main_keyboard()
        )

@admin_required
async def admin_data_status(update: Update, context: CallbackContext):
    """Admin command to check data and system status."""
    try:
        status = tenerife_data_manager.check_historical_data_status()
        
        status_msg = f"🔧 **System Status**\n\n"
        status_msg += f"**Database:**\n"
        status_msg += f"• Fuel stations: {status['station_count']}\n"
        status_msg += f"• Historical records: {status['historical_count']}\n"
        
        if status['date_range'][0]:
            status_msg += f"• Data range: {status['date_range'][0]} to {status['date_range'][1]}\n"
        else:
            status_msg += f"• Data range: No historical data\n"
        
        status_msg += f"\n**Recent snapshots:**\n"
        for date, count in status['recent_data'][:5]:
            status_msg += f"  {date}: {count} records\n"
        
        status_msg += f"\n**Charts status:**\n"
        if status['historical_count'] >= 2:
            status_msg += f"✅ Charts functional ({status['historical_count']} records)\n"
        else:
            status_msg += f"❌ Charts need more data (minimum 2 days)\n"
            status_msg += f"💡 Use: `/admin_create_historical` to fix\n"
        
        # System info
        import sys
        status_msg += f"\n**System:**\n"
        status_msg += f"• Python: {sys.version.split()[0]}\n"
        status_msg += f"• Uptime: Since last restart\n"
        
        await update.message.reply_text(
            status_msg, 
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=create_back_to_main_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Error in admin_data_status: {e}")
        await update.message.reply_text(
            f"❌ Error checking system status: {e}",
            reply_markup=create_back_to_main_keyboard()
        )

@admin_required
async def admin_create_historical(update: Update, context: CallbackContext):
    """Admin command to create historical data for charts."""
    try:
        await update.message.reply_text(
            "⏳ Creating historical data... This may take a moment.",
            reply_markup=create_back_to_main_keyboard()
        )
        
        # Create 30 days of historical data
        tenerife_data_manager.create_historical_backfill(days_back=30)
        
        # Check status after creation
        status = tenerife_data_manager.check_historical_data_status()
        
        result_msg = f"✅ **Historical Data Created**\n\n"
        result_msg += f"• Created records for 30 days\n"
        result_msg += f"• Total historical records: {status['historical_count']}\n"
        result_msg += f"• Charts should now work properly\n"
        
        await update.message.reply_text(
            result_msg, 
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=create_back_to_main_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Error in admin_create_historical: {e}")
        await update.message.reply_text(
            f"❌ Error creating historical data: {e}",
            reply_markup=create_back_to_main_keyboard()
        )

@admin_required
async def admin_help(update: Update, context: CallbackContext):
    """Admin command to show available admin commands."""
    help_msg = f"🛠️ **Admin Commands**\n\n"
    help_msg += f"📊 **Statistics:**\n"
    help_msg += f"• `/admin_stats` - Bot usage statistics\n"
    help_msg += f"• `/admin_data_status` - Database and system status\n"
    help_msg += f"• `/admin_alerts` - Price alerts statistics\n\n"
    
    help_msg += f"👥 **User Management:**\n"
    help_msg += f"• `/admin_users [count]` - Recent users (default 20)\n"
    help_msg += f"• `/admin_user [user_id]` - Detailed user info\n\n"
    
    help_msg += f"🔧 **System:**\n"
    help_msg += f"• `/admin_broadcast [message]` - Broadcast to all users\n"
    help_msg += f"• `/admin_create_historical` - Create chart data\n\n"
    
    help_msg += f"ℹ️ **Info:**\n"
    help_msg += f"• `/admin_help` - This help message\n\n"
    
    help_msg += f"🔐 **Note:** All commands require admin privileges."
    
    await update.message.reply_text(
        help_msg, 
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=create_back_to_main_keyboard()
    )

@admin_required
async def admin_alerts(update: Update, context: CallbackContext):
    """Admin command to show alert system statistics."""
    try:
        alert_stats = tenerife_data_manager.get_alert_statistics()
        
        alert_msg = "🔔 **Alert System Statistics**\n\n"
        alert_msg += f"📊 **Overview:**\n"
        alert_msg += f"• Total active alerts: {alert_stats['total_alerts']}\n\n"
        
        if alert_stats['alerts_by_fuel']:
            alert_msg += f"⛽ **Most Popular Fuel Types:**\n"
            for fuel_type, count in alert_stats['alerts_by_fuel'][:5]:
                fuel_display = FUEL_TYPES.get(fuel_type, {}).get('display', fuel_type)
                alert_msg += f"• {fuel_display}: {count} alerts\n"
            alert_msg += "\n"
        
        if alert_stats['alerts_by_municipality']:
            alert_msg += f"🏘️ **Most Popular Municipalities:**\n"
            for municipality, count in alert_stats['alerts_by_municipality'][:5]:
                alert_msg += f"• {municipality}: {count} alerts\n"
        
        await update.message.reply_text(
            alert_msg, 
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=create_back_to_main_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Error in admin_alerts: {e}")
        await update.message.reply_text(
            f"❌ Error retrieving alert statistics: {e}",
            reply_markup=create_back_to_main_keyboard()
        )

async def handle_broadcast_confirmation(update: Update, context: CallbackContext):
    """Handle broadcast confirmation from admin."""
    if not is_admin(update.message.from_user.id):
        return
    
    if update.message.text == "CONFIRM" and 'pending_broadcast' in context.user_data:
        try:
            broadcast_message = context.user_data.pop('pending_broadcast')
            
            await update.message.reply_text(
                "📡 Starting broadcast...",
                reply_markup=create_back_to_main_keyboard()
            )
            
            # Get all active users
            users = tenerife_data_manager.get_all_active_users()
            success_count = 0
            error_count = 0
            
            # Create navigation keyboard for broadcast messages
            broadcast_keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("🏠 Menú Principal", callback_data=str(INICI))
            ]])
            
            for user in users:
                try:
                    await context.bot.send_message(
                        chat_id=user['user_id'], 
                        text=f"📢 **Mensaje del administrador:**\n\n{broadcast_message}",
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=broadcast_keyboard
                    )
                    success_count += 1
                except Exception as e:
                    error_count += 1
                    logger.warning(f"Failed to send broadcast to {user['user_id']}: {e}")
            
            result_msg = f"✅ **Broadcast Complete**\n\n"
            result_msg += f"• Sent to: {success_count} users\n"
            result_msg += f"• Failed: {error_count} users\n"
            result_msg += f"• Total attempts: {success_count + error_count}\n"
            
            await update.message.reply_text(
                result_msg, 
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=create_back_to_main_keyboard()
            )
            
        except Exception as e:
            logger.error(f"Error in broadcast: {e}")
            await update.message.reply_text(
                f"❌ Broadcast failed: {e}",
                reply_markup=create_back_to_main_keyboard()
            )
    
    elif update.message.text == "CANCEL" and 'pending_broadcast' in context.user_data:
        context.user_data.pop('pending_broadcast', None)
        await update.message.reply_text(
            "❌ Broadcast cancelled.",
            reply_markup=create_back_to_main_keyboard()
        )

# Alert Management Handlers
@error_handler
async def alert_create_start(update: Update, context: CallbackContext):
    """Start alert creation process for a specific municipality."""
    query = update.callback_query
    await query.answer()
    
    # Extract municipality key from callback data (alert_CREATE_MUNICIPALITY_KEY)
    callback_parts = query.data.split('_')
    if len(callback_parts) < 3:
        await query.answer("Error en los datos de la alerta.")
        return NIVELL1
    
    municipality_key = '_'.join(callback_parts[2:])  # Handle municipality keys with underscores
    
    # Store municipality for alert creation
    context.user_data['alert_municipality'] = municipality_key
    
    # Get top fuel types for alert creation
    fuel_buttons = []
    top_fuels = [
        ('GASOLINA_95_E5', '🟢 Gasolina 95 E5'),
        ('GASOLEO_A', '⚫️ Gasóleo A'),
        ('GASOLINA_98_E5', '🔵 Gasolina 98 E5'),
        ('GASOLEO_PREMIUM', '🟠 Gasóleo Premium'),
        ('GLP', '⚪️ GLP'),
    ]
    
    for fuel_key, fuel_display in top_fuels:
        fuel_buttons.append([InlineKeyboardButton(
            fuel_display,
            callback_data=f"{ALERT_FUEL_SELECT}_{fuel_key}"
        )])
    
    # Add back button
    fuel_buttons.append([InlineKeyboardButton(B5, callback_data=f"{TOWN_PREFIX}{municipality_key}")])
    
    municipality_display = MUNICIPALITIES[municipality_key]['display']
    message = f"{M_ALERT_CREATE_START}\n\n📍 *Municipio:* {municipality_display}"
    
    await query.edit_message_text(
        text=message,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(fuel_buttons)
    )
    return ALERT_FUEL_SELECT

@error_handler
async def alert_fuel_selected(update: Update, context: CallbackContext):
    """Handle fuel type selection for alert."""
    query = update.callback_query
    await query.answer()
    
    # Extract fuel type from callback data
    fuel_type = query.data.replace(f'{ALERT_FUEL_SELECT}_', '')
    
    # Store fuel type for alert creation
    context.user_data['alert_fuel_type'] = fuel_type
    
    municipality_key = context.user_data.get('alert_municipality')
    if not municipality_key:
        await query.answer("Error: no se encontró el municipio.")
        return NIVELL1
    
    municipality_display = MUNICIPALITIES[municipality_key]['display']
    fuel_display = FUEL_TYPES[fuel_type]['display']
    
    # Get current minimum price for reference
    try:
        current_min = tenerife_data_manager.get_stations_by_fuel_ascending(fuel_type, limit=1)
        if not current_min.empty:
            fuel_column = FUEL_TYPES[fuel_type]['column'].lower()
            min_price = current_min.iloc[0][fuel_column]
            price_hint = f"\n💡 *Precio mínimo actual:* {min_price}€"
        else:
            price_hint = ""
    except:
        price_hint = ""
    
    message = f"{M_ALERT_PRICE_INPUT}\n\n📍 *Municipio:* {municipality_display}\n⛽ *Combustible:* {fuel_display}{price_hint}"
    
    # Create cancel button
    cancel_button = InlineKeyboardButton(B5, callback_data=f"{TOWN_PREFIX}{municipality_key}")
    
    await query.edit_message_text(
        text=message,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([[cancel_button]])
    )
    return ALERT_PRICE_INPUT

@error_handler
async def alert_price_input(update: Update, context: CallbackContext):
    """Handle price input for alert creation."""
    price_text = update.message.text.strip()
    
    # Validate price input
    try:
        price = float(price_text.replace(',', '.'))
        if price <= 0 or price > 10:
            raise ValueError("Price out of range")
    except ValueError:
        await update.message.reply_text(
            "❌ Precio inválido. Por favor, escribe un precio válido (ej: 1.50)",
            reply_markup=create_back_to_main_keyboard()
        )
        return ALERT_PRICE_INPUT
    
    # Get stored alert data
    municipality_key = context.user_data.get('alert_municipality')
    fuel_type = context.user_data.get('alert_fuel_type')
    
    if not municipality_key or not fuel_type:
        await update.message.reply_text(
            "❌ Error: datos de alerta incompletos. Inténtalo de nuevo.",
            reply_markup=create_back_to_main_keyboard()
        )
        return NIVELL1
    
    # Create the alert
    user = update.message.from_user
    municipality_display = MUNICIPALITIES[municipality_key]['display']
    
    success, result = tenerife_data_manager.create_price_alert(
        user_id=user.id,
        username=user.username,
        fuel_type=fuel_type,
        price_threshold=price,
        municipality=municipality_display
    )
    
    if success:
        if result == "updated":
            message = f"✅ *Alerta actualizada*\n\nTe notificaremos cuando *{FUEL_TYPES[fuel_type]['display']}* esté por debajo de *{price}€* en *{municipality_display}*."
        else:
            message = M_ALERT_CREATED.format(price=price, municipality=municipality_display)
    else:
        message = f"❌ Error al crear la alerta: {result}"
    
    # Create navigation buttons
    buttons = [
        [InlineKeyboardButton(B_ALERT_LIST, callback_data=ALERT_LIST)],
        [InlineKeyboardButton("🏠 Menú Principal", callback_data=str(INICI))]
    ]
    
    # Clean up stored data
    context.user_data.pop('alert_municipality', None)
    context.user_data.pop('alert_fuel_type', None)
    
    await update.message.reply_text(
        message,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    return NIVELL1

@error_handler
async def alert_list(update: Update, context: CallbackContext):
    """Show user's active alerts."""
    query = update.callback_query
    await query.answer()
    
    user = update.message.from_user if update.message else query.from_user
    alerts = tenerife_data_manager.get_user_alerts(user.id)
    
    if not alerts:
        message = M_ALERT_LIST_EMPTY
        buttons = [[InlineKeyboardButton("🏠 Menú Principal", callback_data=str(INICI))]]
    else:
        message = "📋 *Tus alertas activas:*\n\n"
        
        buttons = []
        for i, alert in enumerate(alerts, 1):
            fuel_display = FUEL_TYPES.get(alert['fuel_type'], {}).get('display', alert['fuel_type'])
            created_date = alert['created_at'].strftime('%d/%m/%Y')
            
            message += f"{i}. *{fuel_display}* ≤ {alert['price_threshold']}€\n"
            message += f"   📍 {alert['municipio']}\n"
            message += f"   📅 {created_date}\n\n"
            
            # Add delete button for each alert
            delete_callback = f"{ALERT_DELETE}_{alert['id']}"
            logger.info(f"Creating delete button with callback: {delete_callback}")
            delete_button = InlineKeyboardButton(
                f"🗑️ Eliminar #{i}",
                callback_data=delete_callback
            )
            buttons.append([delete_button])
        
        # Add navigation buttons
        buttons.append([InlineKeyboardButton("🏠 Menú Principal", callback_data=str(INICI))])
    
    await query.edit_message_text(
        text=message,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    return NIVELL1

@error_handler
async def alert_delete(update: Update, context: CallbackContext):
    """Delete a specific alert."""
    query = update.callback_query
    await query.answer()
    
    logger.info(f"Alert delete called with callback data: {query.data}")
    
    # Extract alert ID from callback data
    try:
        alert_id = int(query.data.split('_')[2])
        logger.info(f"Extracted alert ID: {alert_id}")
    except (IndexError, ValueError) as e:
        logger.error(f"Error parsing alert ID from {query.data}: {e}")
        await query.answer("❌ Error en los datos de la alerta", show_alert=True)
        return NIVELL1
    
    user = query.from_user
    success = tenerife_data_manager.delete_alert(user.id, alert_id)
    
    if success:
        await query.answer("✅ Alerta eliminada correctamente", show_alert=True)
        # Refresh the alert list
        await alert_list(update, context)
    else:
        await query.answer("❌ Error al eliminar la alerta", show_alert=True)
    
    return NIVELL1

@error_handler
async def global_navigation_handler(update: Update, context: CallbackContext):
    """Global handler for navigation buttons from alert messages or any orphaned callbacks."""
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    
    # Handle main menu navigation
    if callback_data == str(INICI):
        return await start_over(update, context)
    
    # Handle alerts navigation  
    elif callback_data == str(ALERTS):
        return await alert_list(update, context)
    
    # Handle charts navigation
    elif callback_data == str(CHARTS):
        return await charts_menu(update, context)
    
    # If it's an unknown callback, send user back to main menu
    else:
        await query.edit_message_text(
            text="🔄 Regresando al menú principal...",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🏠 Menú Principal", callback_data=str(INICI))]
            ])
        )
        return NIVELL1

@error_handler
async def inline_query_handler(update: Update, context: CallbackContext):
    """Handle inline queries for municipality search."""
    query = update.inline_query.query.strip().lower()
    
    # If no query, show all municipalities
    if not query:
        results = []
        # Sort municipalities by priority (most important first)
        sorted_municipalities = sorted(MUNICIPALITIES.items(), key=lambda x: x[1]['priority'])
        
        for muni_key, muni_info in sorted_municipalities:  # Show all municipalities sorted by priority
            # Get the actual station data for this municipality
            station_message = await get_cheapest_stations_message(muni_key, muni_info['display'])
            
            result = InlineQueryResultArticle(
                id=muni_key,
                title=f"🏘️ {muni_info['display']}",
                description="Ver las 5 estaciones más baratas",
                input_message_content=InputTextMessageContent(
                    message_text=station_message,
                    parse_mode=ParseMode.MARKDOWN,
                    disable_web_page_preview=True
                )
            )
            results.append(result)
    else:
        # Search municipalities matching the query
        results = []
        matches = []
        
        for muni_key, muni_info in MUNICIPALITIES.items():
            if query in muni_info['display'].lower():
                matches.append((muni_key, muni_info))
        
        # Sort by relevance (exact match first, then contains)
        matches.sort(key=lambda x: (
            0 if x[1]['display'].lower().startswith(query) else 1,
            len(x[1]['display'])
        ))
        
        for muni_key, muni_info in matches[:10]:  # Limit to 10 results
            # Get the actual station data for this municipality
            station_message = await get_cheapest_stations_message(muni_key, muni_info['display'])
            
            result = InlineQueryResultArticle(
                id=muni_key,
                title=f"🏘️ {muni_info['display']}",
                description="Ver las 5 estaciones más baratas",
                input_message_content=InputTextMessageContent(
                    message_text=station_message,
                    parse_mode=ParseMode.MARKDOWN,
                    disable_web_page_preview=True
                )
            )
            results.append(result)
    
    await update.inline_query.answer(results, cache_time=300)

async def get_cheapest_stations_message(municipality_key, municipality_display):
    """Get the message with the 5 cheapest stations for a municipality."""
    try:
        # Get all stations in this municipality
        stations_data, total_count = tenerife_data_manager.get_stations_by_municipality(
            municipality_key, offset=0, limit=100  # Get more to find cheapest
        )
        
        if stations_data.empty:
            return f"❌ No hay estaciones disponibles en {municipality_display}"
        
        # Filter stations with Gasolina 95 E5 prices and sort by price
        stations_with_fuel = stations_data[
            stations_data['precio_gasolina_95_e5'].notna() & 
            (stations_data['precio_gasolina_95_e5'] > 0)
        ].copy()
        
        if stations_with_fuel.empty:
            return f"❌ No hay estaciones con precios de Gasolina 95 E5 en {municipality_display}"
        
        # Sort by price and get top 5
        cheapest_stations = stations_with_fuel.sort_values(
            by='precio_gasolina_95_e5', ascending=True
        ).head(5)
        
        messages = [f"⛽ *5 más baratas en {municipality_display}*\n"]
        
        for i, (_, station) in enumerate(cheapest_stations.iterrows(), 1):
            station_msg = f"{i}. {format_station_message(
                station.to_dict(),
                ['precio_gasolina_95_e5', 'precio_gasoleo_a']
            )}"
            messages.append(station_msg)
        
        message = "\n\n".join(messages)
        return message
        
    except Exception as e:
        logger.error(f"Error getting cheapest stations for {municipality_display}: {e}")
        return f"❌ Error al buscar estaciones en {municipality_display}"

def get_conversation_handler():
    # Debug: Print the alert delete pattern
    alert_delete_pattern = f'^{ALERT_DELETE}_'
    logger.info(f"Alert delete pattern: {alert_delete_pattern}")
    
    conv_handler = ConversationHandler(
        name="tenerife_fuel_bot",
        entry_points=[CommandHandler('start', start)],
        states={
            NIVELL1: [
                CallbackQueryHandler(start_over, pattern=f'^{INICI}$'),
                CallbackQueryHandler(price_menu, pattern=f'^{PREU}$'),
                CallbackQueryHandler(fuel_type_menu, pattern=f'^{COMBUSTIBLE}$'),
                CallbackQueryHandler(municipality_menu, pattern=f'^{POBLE}$'),
                CallbackQueryHandler(info, pattern=f'^{INFO}$'),
                CallbackQueryHandler(location_search, pattern=f'^{LOCATION}$'),
                CallbackQueryHandler(charts_menu, pattern=f'^{CHARTS}$'),
                CallbackQueryHandler(alert_list, pattern=f'^{ALERTS}$'),
                CallbackQueryHandler(municipality_info, pattern=f'^{TOWN_PREFIX}'),
                CallbackQueryHandler(fuel_info, pattern=f'^{FUEL_PREFIX}'),
                CallbackQueryHandler(result_pagination_handler, pattern=f'^{RESULT_PREFIX}'),
                CallbackQueryHandler(fuel_page_handler, pattern='^fuelpage_'),
                CallbackQueryHandler(generate_chart, pattern=f'^{CHART_PREFIX}'),
                CallbackQueryHandler(alert_create_start, pattern=f'^{ALERT_PREFIX}CREATE_'),
                CallbackQueryHandler(alert_list, pattern=f'^{ALERT_LIST}$'),
                CallbackQueryHandler(alert_delete, pattern=alert_delete_pattern),
            ],
            NIVELL2: [
                CallbackQueryHandler(start_over, pattern=f'^{INICI}$'),
                CallbackQueryHandler(cheapest_stations, pattern=f'^{BARATES}$'),
                CallbackQueryHandler(most_expensive_stations, pattern=f'^{CARES}$'),
                CallbackQueryHandler(municipality_page_handler, pattern=f'^{PAGE_PREFIX}'),
                CallbackQueryHandler(municipality_info, pattern=f'^{TOWN_PREFIX}'),
                CallbackQueryHandler(fuel_info, pattern=f'^{FUEL_PREFIX}'),
                CallbackQueryHandler(price_menu, pattern=f'^{PREU}$'),
                CallbackQueryHandler(fuel_type_menu, pattern=f'^{COMBUSTIBLE}$'),
                CallbackQueryHandler(municipality_menu, pattern=f'^{POBLE}$'),
                CallbackQueryHandler(info, pattern=f'^{INFO}$'),
                CallbackQueryHandler(charts_menu, pattern=f'^{CHARTS}$'),
                CallbackQueryHandler(alert_list, pattern=f'^{ALERTS}$'),
                CallbackQueryHandler(fuel_page_handler, pattern='^fuelpage_'),
                CallbackQueryHandler(search_municipality_start, pattern=f'^{SEARCH_MUN}$'),
                CallbackQueryHandler(generate_chart, pattern=f'^{CHART_PREFIX}'),
                CallbackQueryHandler(alert_delete, pattern=alert_delete_pattern),
                MessageHandler(filters.LOCATION, handle_location),
            ],
            NIVELL3: [
                CallbackQueryHandler(start_over, pattern=f'^{INICI}$'),
                CallbackQueryHandler(info, pattern=f'^{INFO}$'),
            ],
            SEARCH_STATE: [
                CallbackQueryHandler(start_over, pattern=f'^{INICI}$'),
                CallbackQueryHandler(municipality_menu, pattern=f'^{POBLE}$'),
                CallbackQueryHandler(info, pattern=f'^{INFO}$'),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_search_input),
            ],
            ALERT_FUEL_SELECT: [
                CallbackQueryHandler(start_over, pattern=f'^{INICI}$'),
                CallbackQueryHandler(municipality_info, pattern=f'^{TOWN_PREFIX}'),
                CallbackQueryHandler(alert_fuel_selected, pattern=f'^{ALERT_FUEL_SELECT}_'),
                CallbackQueryHandler(info, pattern=f'^{INFO}$'),
            ],
            ALERT_PRICE_INPUT: [
                CallbackQueryHandler(start_over, pattern=f'^{INICI}$'),
                CallbackQueryHandler(municipality_info, pattern=f'^{TOWN_PREFIX}'),
                CallbackQueryHandler(info, pattern=f'^{INFO}$'),
                MessageHandler(filters.TEXT & ~filters.COMMAND, alert_price_input),
            ]
        },
        fallbacks=[CommandHandler('start', start)],
        persistent=True,
        allow_reentry=True
    )
    
    return conv_handler

def main():
    # Initialize data manager
    try:
        tenerife_data_manager.load_data_from_db()
        print("✅ Tenerife data manager initialized successfully")
    except Exception as e:
        print(f"⚠️ Could not load data from database: {e}")
        print("You may need to run data loading first")
    
    # Create persistence with explicit path and error handling
    persistence_file = "tenerife_bot_persistence.pkl"
    try:
        # Create persistence directory if it doesn't exist
        os.makedirs("data", exist_ok=True)
        persistence_file = os.path.join("data", "tenerife_bot_persistence.pkl")
        
        persistence = PicklePersistence(filepath=persistence_file)
        print(f"📁 Persistence file: {os.path.abspath(persistence_file)}")
    except Exception as e:
        print(f"⚠️ Could not create persistence: {e}")
        print("Running without persistence...")
        persistence = None
    
    # Create application with increased timeouts for network stability
    builder = Application.builder().token(secret.secret['token'])
    
    # Set timeouts to handle potential DNS resolution issues
    builder.connect_timeout(20)
    builder.read_timeout(20)

    if persistence:
        builder.persistence(persistence)
        print("✅ Bot created with persistence enabled")
    else:
        print("⚠️ Bot created WITHOUT persistence")

    application = builder.build()
    
    # IMPORTANT: Add global navigation handler FIRST (higher priority)
    # This catches navigation buttons from alert notifications and other sources
    application.add_handler(CallbackQueryHandler(
        global_navigation_handler, 
        pattern=f'^({INICI}|{ALERTS}|{CHARTS})$'
    ))
    
    # Add conversation handler SECOND
    application.add_handler(get_conversation_handler())
    
    # Add inline handlers
    application.add_handler(InlineQueryHandler(inline_query_handler))
    
    # Add command handlers
    application.add_handler(CommandHandler('status', status_command))
    application.add_handler(CommandHandler('id', get_id_command))
    
    # Admin commands
    application.add_handler(CommandHandler('admin_help', admin_help))
    application.add_handler(CommandHandler('admin_stats', admin_stats))
    application.add_handler(CommandHandler('admin_users', admin_users))
    application.add_handler(CommandHandler('admin_user', admin_user_info))
    application.add_handler(CommandHandler('admin_broadcast', admin_broadcast))
    application.add_handler(CommandHandler('admin_data_status', admin_data_status))
    application.add_handler(CommandHandler('admin_create_historical', admin_create_historical))
    application.add_handler(CommandHandler('admin_alerts', admin_alerts))
    
    # Broadcast confirmation handler
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, 
        handle_broadcast_confirmation
    ))
    
    # Add error handler
    async def error_callback(update: Update, context: CallbackContext):
        logger.error(f"Exception while handling an update: {context.error}", exc_info=context.error)
    
    application.add_error_handler(error_callback)
    
    print("🚀 Starting Tenerife Bot...")
    application.run_polling()

if __name__ == '__main__':
    main() 