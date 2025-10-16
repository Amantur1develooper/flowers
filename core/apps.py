from django.apps import AppConfig
from apscheduler.schedulers.background import BackgroundScheduler
import os


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        run_main = os.environ.get('RUN_MAIN')
        if run_main == 'true' or run_main is None:
            from .utils import send_daily_report
            scheduler = BackgroundScheduler()
            scheduler.add_job(send_daily_report, 'cron', hour=8, minute=47)
            scheduler.start()

    # def ready(self):
    #     if os.environ.get('RUN_MAIN', None) != 'true':
    #         return 

    #     from .utils import send_daily_report
    #     scheduler = BackgroundScheduler()
    #     scheduler.add_job(send_daily_report, 'cron', hour=8, minute=30)  # Ежедневно в 9:00 утра
    #     scheduler.start()

