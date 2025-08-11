from django.utils import timezone

from .telegram_bot import send_telegram_notification
from .models import Customer 

def send_daily_report():
    """
    Генерация ежедневного уведомления и отправка в Telegram менеджерам.
    """
    today = timezone.localdate()
    
    customers_birthdays = Customer.objects.filter(spouse_birthday=today)
    lines = []

    for customer in customers_birthdays:
        lines.append(f"""
        {customer.spouse_name or "не указано"}
        'Телефон супруга/супруги' - {customer.spouse_phone or "не указано"}
        'Заметки' - {customer.notes or "нет заметок"}
        'Баллы' - {customer.point or "нет баллов"}

        \n
        """)

    message = (
        f"<b>Ежедневное уведомление — {today.strftime('%d.%m.%Y')}</b>\n"
        "Дни рождения супругов:\n" +
        "\n".join(lines)
    )

    send_telegram_notification(message)
