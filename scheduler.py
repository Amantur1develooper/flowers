
import os
import django
from apscheduler.schedulers.blocking import BlockingScheduler

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
django.setup()


from core.utils import send_daily_report

scheduler = BlockingScheduler()
scheduler.add_job(send_daily_report, 'cron', hour=11, minute=40)

if __name__ == "__main__":
    print("✅ Планировщик запущен...")
    scheduler.start()
