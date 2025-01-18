from typing import Final
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler

TOKEN: Final = '7815381432:AAFbTCQV6ytHVwDG4auEQ77_cVUtV9wdOB0'
BOT_USERNAME: Final = '@glugglugbot'

# Constants
TASK_NAME, TASK_DUE_DATE, WATER_INPUT, REMINDER_DAYS = range(4)

# Dictionary to store user data
user_data = {}
scheduler = BackgroundScheduler()
scheduler.start()

# Command to display instructions
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    instructions = (
        "Welcome to your Water Tracker bot! Here are the commands you can use:\n\n"
        "/track - Log your water intake\n"
        "/status - Check your daily water progress\n"
        "/reminder - Set a reminder to drink water\n"
        "/help - Get instructions on how to use the bot"
    )
    await update.message.reply_text(instructions)

# Command to display help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    instructions = (
        "This bot helps you track your water intake. Here's how it works:\n\n"
        "/track - Log the amount of water you drink\n"
        "/status - See how much water you've drunk out of your goal for the day\n"
        "/reminder - Set a reminder to drink water"
    )
    await update.message.reply_text(instructions)

# Water input
async def track_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('How much water did you drink today? Please input the amount in milliliters.')
    return WATER_INPUT

async def water_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    water_amount = update.message.text.strip()

    try:
        water_amount = int(water_amount)
        user_id = update.message.from_user.id
        user_data[user_id] = user_data.get(user_id, {'daily_goal': 2000, 'water_drank': 0})
        user_data[user_id]['water_drank'] += water_amount

        remaining = user_data[user_id]['daily_goal'] - user_data[user_id]['water_drank']

        if remaining <= 0:
            await update.message.reply_text("🎉 Congratulations, you've met your daily water goal! Well done!")
        else:
            await update.message.reply_text(f"Great job! You've drunk {water_amount}ml. Keep going! "
                                           f"You still need {remaining}ml to meet your daily goal.")

        return ConversationHandler.END

    except ValueError:
        await update.message.reply_text("Please input a valid number of milliliters.")
        return WATER_INPUT

# Set reminder to drink water
async def set_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("How many hours before you want to be reminded to drink water? (e.g., 2 hours before).")
    return REMINDER_DAYS

async def reminder_days(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        reminder_hours = int(update.message.text)
        user_id = update.message.from_user.id
        reminder_time = datetime.now() + timedelta(hours=reminder_hours)

        # Schedule the reminder job
        job_id = f"reminder_{user_id}"
        scheduler.add_job(send_reminder, 'date', run_date=reminder_time, args=[user_id], id=job_id, replace_existing=True)

        await update.message.reply_text(f"Reminder set for {reminder_hours} hours before your next water intake!")

        return ConversationHandler.END

    except ValueError:
        await update.message.reply_text("Please input a valid number of hours.")
        return REMINDER_DAYS

# Send reminder to user
async def send_reminder(user_id: int):
    chat_id = user_id
    message = "⏰ Time to drink some water! Stay hydrated!"
    await context.bot.send_message(chat_id=chat_id, text=message)

# Command to show the current progress
async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_info = user_data.get(user_id, {'daily_goal': 2000, 'water_drank': 0})

    remaining = user_info['daily_goal'] - user_info['water_drank']

    if remaining > 0:
        await update.message.reply_text(f"You've drunk {user_info['water_drank']}ml out of your daily goal of {user_info['daily_goal']}ml. Keep it up! You need {remaining}ml more!")
    else:
        await update.message.reply_text("🎉 You've reached your daily goal! Great job!")

# Conversation flow
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel the current conversation."""
    await update.message.reply_text("Okay, the current task setup has been canceled!")
    return ConversationHandler.END

# Main function to set up handlers and run the bot
if __name__ == '__main__':
    print('Starting bot...')
    app = Application.builder().token(TOKEN).build()

    # Add handlers
    app.add_handler(CommandHandler('start', start_command))
    app.add_handler(CommandHandler('help', help_command))
    app.add_handler(CommandHandler('track', track_command))
    app.add_handler(CommandHandler('status', status_command))
    app.add_handler(CommandHandler('reminder', set_reminder))

    # Define conversation handler
    conversation_handler = ConversationHandler(
        entry_points=[CommandHandler('track', track_command), CommandHandler('reminder', set_reminder)],
        states={
            WATER_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, water_input)],
            REMINDER_DAYS: [MessageHandler(filters.TEXT & ~filters.COMMAND, reminder_days)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    # Add conversation handler to the application
    app.add_handler(conversation_handler)

    # Polling
    print('Polling bot...')
    app.run_polling(poll_interval=3)
