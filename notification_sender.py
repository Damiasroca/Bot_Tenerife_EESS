#!/usr/bin/env python3
"""
Price Alert Notification Sender for Tenerife Bot
This script checks for price alerts and sends actual Telegram notifications.
Run this periodically (e.g., every 10 minutes) to monitor and send alerts.
"""

import asyncio
from telegram import Bot, InlineKeyboardMarkup, InlineKeyboardButton
from data_manager_tenerife import tenerife_data_manager
from constants_tenerife import FUEL_TYPES, INICI, ALERTS
import secret
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_alert_navigation_keyboard():
    """Create navigation keyboard for alert messages."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏠 Menú Principal", callback_data=str(INICI))],
        [InlineKeyboardButton("📋 Mis Alertas", callback_data=str(ALERTS))]
    ])

async def send_price_notifications():
    """Check for price alerts and send Telegram notifications."""
    print("🔔 Checking for price alerts...")
    
    try:
        # Initialize bot
        bot = Bot(token=secret.secret['token'])
        
        # Get notifications that need to be sent
        notifications = tenerife_data_manager.check_price_alerts()
        
        if not notifications:
            print("✅ No price alerts triggered at this time.")
            return
        
        print(f"🚨 Found {len(notifications)} price alerts to send!")
        
        sent_count = 0
        error_count = 0
        
        for notification in notifications:
            try:
                # Format the alert message
                fuel_display = FUEL_TYPES.get(notification['fuel_type'], {}).get('display', notification['fuel_type'])
                
                alert_message = f"🚨 **¡ALERTA DE PRECIO!**\n\n"
                alert_message += f"⛽ **{fuel_display}:** {notification['current_price']}€\n"
                alert_message += f"💰 **Tu límite:** ≤ {notification['threshold']}€\n"
                alert_message += f"📍 **Ubicación:** {notification['municipality']}\n\n"
                alert_message += f"🏪 **Estación:** {notification['station_name']}\n"
                if notification['station_address']:
                    alert_message += f"📍 {notification['station_address']}\n\n"
                alert_message += f"💡 ¡Precio por debajo de tu alerta!"
                
                # Send the notification with navigation buttons
                await bot.send_message(
                    chat_id=notification['user_id'],
                    text=alert_message,
                    parse_mode='Markdown',
                    reply_markup=create_alert_navigation_keyboard()
                )
                
                sent_count += 1
                print(f"   ✅ Sent alert to user {notification['user_id']} - {fuel_display}: {notification['current_price']}€")
                
                # Small delay to avoid rate limiting
                await asyncio.sleep(0.1)
                
            except Exception as e:
                error_count += 1
                logger.error(f"Failed to send alert to user {notification['user_id']}: {e}")
        
        print(f"\n📊 **Notification Summary:**")
        print(f"   ✅ Sent: {sent_count} alerts")
        print(f"   ❌ Failed: {error_count} alerts")
        print(f"   📱 Total processed: {len(notifications)} alerts")
        
    except Exception as e:
        logger.error(f"Error in notification system: {e}")
        print(f"❌ Notification system error: {e}")

async def test_single_notification():
    """Send a test notification to verify the system works."""
    print("🧪 Sending test notification...")
    
    try:
        bot = Bot(token=secret.secret['token'])
        
        # Get your user ID (replace with your actual Telegram ID)
        test_user_id = 306657494  # Your user ID from the test
        
        test_message = f"🧪 **Prueba del Sistema de Alertas**\n\n"
        test_message += f"✅ El sistema de notificaciones funciona correctamente.\n"
        test_message += f"🔔 Recibirás alertas cuando los precios bajen de tus límites.\n\n"
        test_message += f"💡 Para crear alertas reales, usa el bot normalmente."
        
        # Send test message with navigation buttons
        await bot.send_message(
            chat_id=test_user_id,
            text=test_message,
            parse_mode='Markdown',
            reply_markup=create_alert_navigation_keyboard()
        )
        
        print(f"✅ Test notification sent to user {test_user_id}")
        
    except Exception as e:
        logger.error(f"Failed to send test notification: {e}")
        print(f"❌ Test notification failed: {e}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        # Run test notification
        asyncio.run(test_single_notification())
    else:
        # Run real notification check
        asyncio.run(send_price_notifications()) 