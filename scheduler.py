# scheduler.py
import os
import django
from apscheduler.schedulers.blocking import BlockingScheduler

# 1. Указываем настройки Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')  # <-- замени project на имя твоего проекта
django.setup()  # 2. Инициализируем Django

# 3. Импортируем после настройки окружения!
from core.utils import send_daily_report

scheduler = BlockingScheduler(timezone="Asia/Bishkek")
scheduler.add_job(send_daily_report, 'cron', hour=10, minute=30)  # Уведомление в 8:30
print("✅ Планировщик запущен...")
scheduler.start()
