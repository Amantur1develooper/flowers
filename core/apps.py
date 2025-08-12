from django.apps import AppConfig
from apscheduler.schedulers.background import BackgroundScheduler


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        from .utils import send_daily_report
        scheduler = BackgroundScheduler()
        scheduler.add_job(send_daily_report, 'cron', hour=13, minute=19) 
        scheduler.start()

