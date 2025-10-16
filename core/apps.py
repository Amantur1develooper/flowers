from django.apps import AppConfig
from apscheduler.schedulers.background import BackgroundScheduler
import os

class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    scheduler_started = False  # Флаг, чтобы не запускать дважды

    def ready(self):
        if CoreConfig.scheduler_started:
            return  # чтобы не было двойного запуска при автоперезапуске runserver

        if os.environ.get('RUN_MAIN') != 'true':
            return

        from core.utils import send_daily_report

        scheduler = BackgroundScheduler()
        scheduler.add_job(send_daily_report, 'cron', hour=11, minute=27)
        scheduler.start()

        CoreConfig.scheduler_started = True
        print("✅ Планировщик APScheduler запущен автоматически")
