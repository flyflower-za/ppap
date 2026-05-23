"""
Celery Beat configuration for scheduled tasks.
"""
from celery.schedules import crontab
from app.tasks.celery_app import celery_app

# Celery Beat schedule configuration
celery_app.conf.beat_schedule = {
    # Daily summary report - runs every day at 8:00 AM
    'daily-summary-report': {
        'task': 'app.tasks.scheduler_tasks.send_daily_summary_report',
        'schedule': crontab(hour=8, minute=0),
    },
}
