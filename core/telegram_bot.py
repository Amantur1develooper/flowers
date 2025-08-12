import requests
from django.conf import settings
from .models import TelegramManager


def send_telegram_notification(message):
    """Отправка уведомления всем активным менеджерам"""
    if not settings.TELEGRAM_BOT_TOKEN:
        return False
    
    active_managers = TelegramManager.objects.filter(
        is_active=True,
        notify_orders=True
    )
    
    if not active_managers.exists():
        return False
    
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    success_count = 0

    for manager in active_managers:
        payload = {
            'chat_id': manager.chat_id,
            'text': message,
            'parse_mode': 'HTML'
        }
        
        try:
            response = requests.post(url, json=payload)
            if response.status_code == 200:
                success_count += 1
        except Exception as e:
            print(f"Error sending Telegram notification to {manager.chat_id}: {e}")
    
    return success_count > 0


def set_webhook():
    """Установка webhook для Telegram бота"""
    if not settings.TELEGRAM_BOT_TOKEN or not settings.WEBHOOK_URL:
        return False
    
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/setWebhook"
    payload = {
        'url': settings.WEBHOOK_URL,
        'allowed_updates': ['message']
    }
    
    try:
        response = requests.post(url, json=payload)
        return response.status_code == 200
    except Exception as e:
        print(f"Error setting webhook: {e}")
        return False