from django.utils import timezone
from django.db.models import Q

from .telegram_bot import send_telegram_notification
from .models import Customer 


def send_daily_report():
    """
    Генерация ежедневного уведомления и отправка в Telegram менеджерам.
    """
    today = timezone.localdate()

    customers_birthdays = Customer.objects.filter(
        Q(spouse_birthday=today) | Q(birthday=today)
    )
    lines = []

    for customer in customers_birthdays:
        lines.append(f"""
Имя клиента - {customer.full_name or "не указано"}
Телефон клиента - {customer.phone or "не указано"}
Дата рождения клиента - {customer.birthday.strftime('%d.%m.%Y') if customer.birthday else "не указана"}
Дата рождения супруга/супруги - {customer.spouse_birthday.strftime('%d.%m.%Y') if customer.spouse_birthday else "не указана"}
Имя супруга/супруги (жена или муж) - {customer.spouse_name or "не указано"}
Телефон супруга/супруги - {customer.spouse_phone or "не указано"}
Любимые цветы - {customer.favorite_flowers or "не указаны"} 
Заметки - {customer.notes or "нет заметок"}
Баллы - {customer.point or "нет баллов"}
        """)

    message = (
        f"<b>Ежедневное уведомление — {today.strftime('%d.%m.%Y')}</b>\n"
        "Дни рождения:\n" +
        "\n".join(lines) or "Нет дней рождения сегодня."
    )
      
    send_telegram_notification(message)
