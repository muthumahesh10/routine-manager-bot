import os
import asyncio
import io
from datetime import datetime, date, timedelta
import pandas as pd
from celery import Celery
from celery.schedules import crontab
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup

from database import SessionLocal
import models

# Connect to Redis container
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery("tasks", broker=REDIS_URL)

# Set the timezone to India (Chennai) so the alarms match your clock perfectly
celery_app.conf.timezone = 'Asia/Kolkata'

# ==========================================
# PASTE YOUR TOKEN FROM BOTFATHER HERE
# (It needs to be here as well to send background alerts)
# ==========================================
TOKEN = os.getenv("TELEGRAM_TOKEN")


# ==========================================
# TELEGRAM SEND HELPERS
# ==========================================
def sync_send_message(chat_id: str, text: str, reply_markup=None):
    """Sends a Telegram message synchronously so Celery can use it."""

    async def _send():
        bot = Bot(token=TOKEN)
        await bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown", reply_markup=reply_markup)

    asyncio.run(_send())


def sync_send_document(chat_id: str, document_bytes: io.BytesIO, filename: str, caption: str):
    """Sends an Excel file synchronously so Celery can use it."""

    async def _send():
        bot = Bot(token=TOKEN)
        await bot.send_document(chat_id=chat_id, document=document_bytes, filename=filename, caption=caption)

    asyncio.run(_send())


# ==========================================
# TASK 1: MINUTE-BY-MINUTE ALARMS
# ==========================================
@celery_app.task
def check_routine_reminders():
    """Checks the database every minute to see if a task is scheduled for right now."""
    db = SessionLocal()
    try:
        now = datetime.now()
        current_time_str = now.strftime("%H:%M")
        today_date = now.date()

        # Determine what type of day it is
        is_weekend = today_date.weekday() >= 5
        is_1st = today_date.day == 1
        is_6th = today_date.day == 6

        filters = [models.FrequencyEnum.daily]
        if is_weekend:
            filters.append(models.FrequencyEnum.weekend)
        else:
            filters.append(models.FrequencyEnum.weekday)

        if is_1st: filters.append(models.FrequencyEnum.monthly_1st)
        if is_6th: filters.append(models.FrequencyEnum.monthly_6th)

        # Find all templates that apply today
        tasks_for_today = db.query(models.TaskTemplate).filter(
            models.TaskTemplate.frequency.in_(filters)
        ).all()

        for task in tasks_for_today:
            # If the task time exactly matches the current clock time!
            if task.start_time and task.start_time.strftime("%H:%M") == current_time_str:

                # Ensure a log exists for today so we have an ID for the button
                log = db.query(models.DailyLog).filter(
                    models.DailyLog.task_id == task.id, models.DailyLog.date == today_date
                ).first()

                if not log:
                    log = models.DailyLog(user_id=task.user_id, task_id=task.id, date=today_date,
                                          status=models.StatusEnum.pending)
                    db.add(log)
                    db.commit()

                # Get the user to find their Telegram Chat ID
                user = db.query(models.User).filter(models.User.id == task.user_id).first()
                if user and log.status == models.StatusEnum.pending:
                    # Create an interactive "Mark Done" button inside the alert!
                    btn_text = f"✅ Mark '{task.task_name}' as Done"
                    keyboard = [[InlineKeyboardButton(btn_text, callback_data=f"toggle_{log.id}")]]
                    reply_markup = InlineKeyboardMarkup(keyboard)

                    message = f"🔔 *Reminder:* It is time to *{task.task_name}*!\n\nTap the button below when you are finished."
                    sync_send_message(chat_id=user.phone_number, text=message, reply_markup=reply_markup)

    finally:
        db.close()


# ==========================================
# TASK 2: END OF DAY REVIEW
# ==========================================
@celery_app.task
def send_end_of_day_review():
    """Runs at 9:30 PM to ask the user to rewind their day."""
    db = SessionLocal()
    try:
        today_date = datetime.now().date()
        users = db.query(models.User).all()

        for user in users:
            # Check today's performance
            logs = db.query(models.DailyLog).join(models.TaskTemplate).filter(
                models.DailyLog.user_id == user.id,
                models.DailyLog.date == today_date
            ).all()

            completed = sum(1 for log in logs if log.status == models.StatusEnum.completed)
            total = len(logs)

            msg = "🌙 *End of Day Review*\n\n"
            msg += "It's time to set your sleep alarm, rewind your day, and prepare for tomorrow!\n\n"
            msg += f"📊 *Today's Score:* You completed {completed} out of {total} tasks.\n\n"
            msg += "Type /today to do a final check of your checklist before bed. Goodnight!"

            sync_send_message(chat_id=user.phone_number, text=msg)
    finally:
        db.close()


# ==========================================
# TASK 2.5: DAILY JOURNAL PROMPT
# ==========================================
@celery_app.task
def send_journal_prompt():
    """Runs at 9:31 PM to ask the user for their daily journal."""
    db = SessionLocal()
    try:
        users = db.query(models.User).all()
        for user in users:
            msg = (
                "📖 *Daily Journal*\n\n"
                "How was your day today? Did you learn anything new? "
                "Just type your thoughts below and send it to me. "
                "I will save it to your database!"
            )
            # ForceReply makes the keyboard pop up automatically on the user's phone!
            from telegram import ForceReply
            reply_markup = ForceReply(selective=True)
            sync_send_message(chat_id=user.phone_number, text=msg, reply_markup=reply_markup)
    finally:
        db.close()


# ==========================================
# TASK 3: AUTOMATIC MONTHLY EXCEL REPORT
# ==========================================
@celery_app.task
def generate_monthly_report():
    """Runs at 11:50 PM. Only generates the report if tomorrow is the 1st of the month."""
    tomorrow = datetime.now().date() + timedelta(days=1)

    # If tomorrow is not the 1st, stop here.
    if tomorrow.day != 1:
        return

    db = SessionLocal()
    try:
        users = db.query(models.User).all()
        current_month_str = datetime.now().strftime('%B %Y')

        for user in users:
            # Fetch all logs for this user
            logs = db.query(models.DailyLog, models.TaskTemplate).join(
                models.TaskTemplate, models.DailyLog.task_id == models.TaskTemplate.id
            ).filter(models.DailyLog.user_id == user.id).all()

            if not logs:
                continue

            # Build Pandas Dataframe
            data = []
            for log, task in logs:
                data.append({
                    "Date": log.date.strftime("%Y-%m-%d"),
                    "Time": task.start_time.strftime("%H:%M") if task.start_time else "",
                    "Task": task.task_name,
                    "Frequency": task.frequency.value,
                    "Status": log.status.value.upper()
                })

            df = pd.DataFrame(data)

            # Save to Excel Bytes
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name="Monthly Report")
            output.seek(0)

            filename = f"Routine_Report_{current_month_str}.xlsx"
            caption = f"📈 *Monthly Wrap-Up!* Here is your complete performance report for {current_month_str}."

            sync_send_document(chat_id=user.phone_number, document_bytes=output, filename=filename, caption=caption)
    finally:
        db.close()


# ==========================================
# CELERY BEAT SCHEDULE
# ==========================================
celery_app.conf.beat_schedule = {
    'minute-by-minute-alerts': {
        'task': 'tasks.check_routine_reminders',
        'schedule': crontab(minute='*'),  # Trigger every single minute!
    },
    'nightly-bedtime-review': {
        'task': 'tasks.send_end_of_day_review',
        'schedule': crontab(hour=21, minute=30),  # 9:30 PM Everyday
    },
    'daily-journal-prompt': {
        'task': 'tasks.send_journal_prompt',
        'schedule': crontab(hour=21, minute=31),  # 9:31 PM Everyday
    },
    'monthly-excel-report': {
        'task': 'tasks.generate_monthly_report',
        'schedule': crontab(hour=23, minute=50),  # 11:50 PM Everyday (logic filters for last day)
    }
}