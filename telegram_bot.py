import asyncio
import logging
from datetime import datetime, date
import io
import pandas as pd
import os

from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

from database import SessionLocal, engine
import models
from routines_config import DEFAULT_ROUTINES

# Create the database tables before starting the bot!
models.Base.metadata.create_all(bind=engine)

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
# Hide the constant "HTTP Request" polling logs
logging.getLogger("httpx").setLevel(logging.WARNING)

# ==========================================
# PASTE YOUR TOKEN FROM BOTFATHER HERE
# ==========================================
TOKEN = os.getenv("TELEGRAM_TOKEN")


# ==========================================
# 1. AUTHENTICATION & HELP
# ==========================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Responds to /start command and saves user to database"""
    user_name = update.effective_user.first_name
    chat_id = str(update.effective_chat.id)

    db = SessionLocal()
    try:
        user = db.query(models.User).filter(models.User.phone_number == chat_id).first()
        if not user:
            new_user = models.User(name=user_name, phone_number=chat_id, password_hash="telegram_secure")
            db.add(new_user)
            db.commit()
            message = f"👋 Welcome {user_name}! Your Routine Manager is ready.\n\nType /setup_my_routine to load your custom schedule, or type /help to see how to use me!"
        else:
            message = f"👋 Welcome back, {user_name}!\n\nUse /today to see your checklist, or /help to see all commands."
        await update.message.reply_text(message)
    except Exception as e:
        logging.error(f"DB Error: {e}")
        await update.message.reply_text("Database connection error.")
    finally:
        db.close()


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays the user manual for the bot."""
    help_text = (
        "🤖 *Routine Manager - User Manual*\n\n"
        "Here is how to interact with me:\n\n"
        "📅 *Daily Use*\n"
        "• `/today` - View and check off today's tasks.\n"
        "• `/report` - Instantly generate your Excel performance report.\n\n"
        "⚙️ *Task Management*\n"
        "• `/list` - View all your active tasks and their times.\n"
        "• `/add <Task Name> <HH:MM>` - Create a new daily task.\n"
        "  _Example:_ `/add Read a book 19:30`\n"
        "• `/edit <Task Name> <HH:MM>` - Change the time of an existing task.\n"
        "  _Example:_ `/edit Workout 07:00`\n"
        "• `/delete <Task Name>` - Remove a task permanently.\n"
        "  _Example:_ `/delete Wash dress`\n\n"
        "🚀 *System Setup*\n"
        "• `/setup_my_routine` - Resets your schedule back to the default configuration.\n"
        "• `/help` - Show this exact menu again."
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")


# ==========================================
# 2. LOAD CUSTOM ROUTINE (ONE-TIME SETUP)
# ==========================================
async def setup_my_routine(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Automatically loads the user's specific complex routine from routines_config.py"""
    chat_id = str(update.effective_chat.id)
    db = SessionLocal()

    try:
        user = db.query(models.User).filter(models.User.phone_number == chat_id).first()
        if not user:
            await update.message.reply_text("Please type /start first!")
            return

        # Clear existing templates to avoid duplicates during setup
        db.query(models.TaskTemplate).filter(models.TaskTemplate.user_id == user.id).delete()

        # Load from our new config file!
        for r in DEFAULT_ROUTINES:
            new_task = models.TaskTemplate(
                user_id=user.id,
                task_name=r["name"],
                start_time=datetime.strptime(r["time"], "%H:%M").time(),
                frequency=r["freq"]
            )
            db.add(new_task)

        db.commit()
        await update.message.reply_text(
            "✅ Your complete schedule has been successfully loaded into the database!\n\nType /today to see your interactive checklist.")
    except Exception as e:
        logging.error(f"Setup Error: {e}")
        await update.message.reply_text("Failed to setup routine.")
    finally:
        db.close()


# ==========================================
# 3. TASK MANAGEMENT (/edit, /add, /delete, /list)
# ==========================================
async def list_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lists all active routines so the user can see them."""
    chat_id = str(update.effective_chat.id)
    db = SessionLocal()

    try:
        user = db.query(models.User).filter(models.User.phone_number == chat_id).first()
        tasks = db.query(models.TaskTemplate).filter(models.TaskTemplate.user_id == user.id).order_by(
            models.TaskTemplate.start_time).all()

        if not tasks:
            await update.message.reply_text("You have no tasks! Use /setup_my_routine or /add to create some.")
            return

        msg = "📋 *All Your Active Tasks:*\n\n"
        for t in tasks:
            time_str = t.start_time.strftime("%H:%M") if t.start_time else "Anytime"
            msg += f"• *{t.task_name}* at {time_str} ({t.frequency.value})\n"

        msg += "\n💡 *Need help?* Type `/help` for instructions."
        await update.message.reply_text(msg, parse_mode="Markdown")
    finally:
        db.close()


async def edit_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Changes the time of an existing task."""
    chat_id = str(update.effective_chat.id)

    try:
        if len(context.args) < 2:
            raise ValueError("Not enough arguments")

        time_str = context.args[-1]
        task_name_query = " ".join(context.args[:-1])
        parsed_time = datetime.strptime(time_str, "%H:%M").time()
    except (IndexError, ValueError):
        await update.message.reply_text("⚠️ *Usage:* `/edit <Task Name> <HH:MM>`\n*Example:* `/edit Workout 07:00`",
                                        parse_mode="Markdown")
        return

    db = SessionLocal()
    try:
        user = db.query(models.User).filter(models.User.phone_number == chat_id).first()

        # Search for a task that contains the query string (case insensitive)
        task = db.query(models.TaskTemplate).filter(
            models.TaskTemplate.user_id == user.id,
            models.TaskTemplate.task_name.ilike(f"%{task_name_query}%")
        ).first()

        if not task:
            await update.message.reply_text(
                f"❌ Could not find a task matching '{task_name_query}'. Use /list to see exact names.")
            return

        old_time = task.start_time.strftime("%H:%M")
        task.start_time = parsed_time
        db.commit()

        await update.message.reply_text(
            f"✅ *Task Updated!*\n\n'{task.task_name}' has been moved from {old_time} to {time_str}.",
            parse_mode="Markdown")
    finally:
        db.close()


async def add_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Adds a brand new daily task."""
    chat_id = str(update.effective_chat.id)

    try:
        if len(context.args) < 2:
            raise ValueError("Not enough arguments")
        time_str = context.args[-1]
        task_name = " ".join(context.args[:-1])
        parsed_time = datetime.strptime(time_str, "%H:%M").time()
    except:
        await update.message.reply_text("⚠️ *Usage:* `/add <Task Name> <HH:MM>`\n*Example:* `/add Call Mom 19:00`",
                                        parse_mode="Markdown")
        return

    db = SessionLocal()
    try:
        user = db.query(models.User).filter(models.User.phone_number == chat_id).first()
        new_task = models.TaskTemplate(
            user_id=user.id, task_name=task_name, start_time=parsed_time, frequency=models.FrequencyEnum.daily
        )
        db.add(new_task)
        db.commit()
        await update.message.reply_text(f"✅ *New Task Added!*\n\n'{task_name}' is scheduled for {time_str} daily.",
                                        parse_mode="Markdown")
    finally:
        db.close()


async def delete_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Deletes an existing task."""
    chat_id = str(update.effective_chat.id)
    task_name_query = " ".join(context.args)

    if not task_name_query:
        await update.message.reply_text("⚠️ *Usage:* `/delete <Task Name>`")
        return

    db = SessionLocal()
    try:
        user = db.query(models.User).filter(models.User.phone_number == chat_id).first()
        task = db.query(models.TaskTemplate).filter(
            models.TaskTemplate.user_id == user.id, models.TaskTemplate.task_name.ilike(f"%{task_name_query}%")
        ).first()

        if not task:
            await update.message.reply_text(f"❌ Could not find task '{task_name_query}'.")
            return

        task_name = task.task_name
        db.delete(task)
        db.commit()
        await update.message.reply_text(f"🗑️ *Task Deleted:* '{task_name}' has been removed from your routine.",
                                        parse_mode="Markdown")
    finally:
        db.close()


# ==========================================
# 4. INTERACTIVE CHECKLIST (/today)
# ==========================================
async def today_checklist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generates today's checklist with inline interactive checkboxes."""
    chat_id = str(update.effective_chat.id)
    today_date = date.today()
    day_name = today_date.strftime("%A")  # e.g., "Monday"
    formatted_date = today_date.strftime("%d %B %Y")

    db = SessionLocal()
    try:
        user = db.query(models.User).filter(models.User.phone_number == chat_id).first()
        if not user:
            await update.message.reply_text("Please type /start first!")
            return

        # Determine which tasks apply today based on frequency
        is_weekend = today_date.weekday() >= 5  # 5=Sat, 6=Sun
        is_1st = today_date.day == 1
        is_6th = today_date.day == 6

        filters = []
        if is_weekend:
            filters.append(models.FrequencyEnum.weekend)
        else:
            filters.append(models.FrequencyEnum.weekday)

        if is_1st: filters.append(models.FrequencyEnum.monthly_1st)
        if is_6th: filters.append(models.FrequencyEnum.monthly_6th)
        filters.append(models.FrequencyEnum.daily)  # Always include daily if any

        # Fetch relevant templates
        templates = db.query(models.TaskTemplate).filter(
            models.TaskTemplate.user_id == user.id,
            models.TaskTemplate.frequency.in_(filters)
        ).order_by(models.TaskTemplate.start_time).all()

        if not templates:
            await update.message.reply_text("No tasks scheduled for today. Enjoy your day!")
            return

        # Ensure DailyLogs exist for today
        for t in templates:
            existing_log = db.query(models.DailyLog).filter(
                models.DailyLog.task_id == t.id,
                models.DailyLog.date == today_date
            ).first()
            if not existing_log:
                new_log = models.DailyLog(user_id=user.id, task_id=t.id, date=today_date,
                                          status=models.StatusEnum.pending)
                db.add(new_log)
        db.commit()

        # Fetch Today's Logs to build UI
        todays_logs = db.query(models.DailyLog).join(models.TaskTemplate).filter(
            models.DailyLog.user_id == user.id,
            models.DailyLog.date == today_date
        ).order_by(models.TaskTemplate.start_time).all()

        # Build Interactive Keyboard (Wide buttons)
        keyboard = []
        for log in todays_logs:
            task_time = log.task.start_time.strftime("%H:%M") if log.task.start_time else ""
            status_emoji = "✅" if log.status == models.StatusEnum.completed else "⬜️"
            btn_text = f"{status_emoji} {task_time} - {log.task.task_name}"
            # Callback data stores the Log ID
            keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"toggle_{log.id}")])

        reply_markup = InlineKeyboardMarkup(keyboard)
        header = f"📅 *{day_name}, {formatted_date}*\nHere is your checklist for today. Tap to check/uncheck:\n"

        await update.message.reply_text(header, reply_markup=reply_markup, parse_mode="Markdown")

    finally:
        db.close()


# ==========================================
# 5. BUTTON CLICK HANDLER (Toggling Done/Pending)
# ==========================================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Catches inline keyboard clicks to mark tasks as Done."""
    query = update.callback_query
    await query.answer()  # Acknowledge click

    data = query.data
    if data.startswith("toggle_"):
        log_id = int(data.split("_")[1])

        db = SessionLocal()
        try:
            log = db.query(models.DailyLog).filter(models.DailyLog.id == log_id).first()
            if log:
                # Toggle Status
                if log.status == models.StatusEnum.completed:
                    log.status = models.StatusEnum.pending
                else:
                    log.status = models.StatusEnum.completed
                db.commit()

                # Rebuild keyboard with updated status
                todays_logs = db.query(models.DailyLog).join(models.TaskTemplate).filter(
                    models.DailyLog.user_id == log.user_id,
                    models.DailyLog.date == log.date
                ).order_by(models.TaskTemplate.start_time).all()

                keyboard = []
                for l in todays_logs:
                    task_time = l.task.start_time.strftime("%H:%M") if l.task.start_time else ""
                    status_emoji = "✅" if l.status == models.StatusEnum.completed else "⬜️"
                    keyboard.append([InlineKeyboardButton(f"{status_emoji} {task_time} - {l.task.task_name}",
                                                          callback_data=f"toggle_{l.id}")])

                header = f"📅 *{log.date.strftime('%A')}, {log.date.strftime('%d %B %Y')}*\nHere is your checklist for today. Tap to check/uncheck:\n"
                await query.edit_message_text(text=header, reply_markup=InlineKeyboardMarkup(keyboard),
                                              parse_mode="Markdown")
        finally:
            db.close()


# ==========================================
# 6. GENERATE EXCEL REPORT (/report)
# ==========================================
async def generate_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generates an Excel tabular report and sends it to the user."""
    chat_id = str(update.effective_chat.id)
    await update.message.reply_text("📊 Generating your Excel report, please wait...")

    db = SessionLocal()
    try:
        user = db.query(models.User).filter(models.User.phone_number == chat_id).first()

        # Fetch all logs for this user joined with task details
        logs = db.query(models.DailyLog, models.TaskTemplate).join(
            models.TaskTemplate, models.DailyLog.task_id == models.TaskTemplate.id
        ).filter(models.DailyLog.user_id == user.id).all()

        if not logs:
            await update.message.reply_text("No data found to generate a report.")
            return

        # Prepare Data for Pandas
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

        # Save to virtual Excel file in memory
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name="Routine Report")
        output.seek(0)

        # Send the file via Telegram
        filename = f"Routine_Report_{date.today().strftime('%B_%Y')}.xlsx"
        await update.message.reply_document(document=output, filename=filename,
                                            caption="📈 Here is your routine performance report!")

    except Exception as e:
        logging.error(f"Report Error: {e}")
        await update.message.reply_text("Failed to generate report.")
    finally:
        db.close()


# ==========================================
# RUNNING THE BOT
# ==========================================
if __name__ == '__main__':
    print("🚀 Telegram Bot is running...")
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))  # Added Help Command!
    app.add_handler(CommandHandler("menu", help_command))  # Added Menu Alias!
    app.add_handler(CommandHandler("setup_my_routine", setup_my_routine))
    app.add_handler(CommandHandler("list", list_tasks))
    app.add_handler(CommandHandler("edit", edit_task))
    app.add_handler(CommandHandler("add", add_task))
    app.add_handler(CommandHandler("delete", delete_task))
    app.add_handler(CommandHandler("today", today_checklist))
    app.add_handler(CommandHandler("report", generate_report))

    # Handler for inline button clicks
    app.add_handler(CallbackQueryHandler(button_handler))

    app.run_polling()