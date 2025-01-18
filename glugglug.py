from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.base import JobLookupError

TOKEN = 'YOUR_BOT_TOKEN'  # Your bot token here

# Constants
TARGET_WATER_INTAKE = 2000  # Daily water intake target in milliliters (adjust as needed)
ENCOURAGING_MESSAGES = [
    "Great job, keep going!",
    "You're doing awesome!",
    "Keep it up, you're almost there!",
    "Drink up, stay hydrated!",
    "Hydration is key! You're doing well!"
]

# Dictionary to store user's water intake
user_data = {}

# Initialize scheduler
scheduler = BackgroundScheduler()
scheduler.start()

# State for conversation handler
WATER_INPUT, SET_REMINDER = range(2)

# Start Command
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome to the Drinking Water Tracker Bot! Type /help to see available commands.")

# Help Command
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Use /track to input your daily water intake, /show to check your progress, and /setreminder to set reminders.")

# Track Command
async def track_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Prompt the user to input how much water they've drunk"""
    await update.message.reply_text("How much water did you drink today (in milliliters)?")

    return WATER_INPUT

# Track Water Input
async def water_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the user input for water intake"""
    try:
        water_drunk = int(update.message.text)
        user_id = update.message.from_user.id

        # Initialize user's data if not already
        if user_id not in user_data:
            user_data[user_id] = {'total': 0, 'target': TARGET_WATER_INTAKE}

        # Update the user's water intake
        user_data[user_id]['total'] += water_drunk

        # Get the current intake and target
        total_drunk = user_data[user_id]['total']
        target = user_data[user_id]['target']

        # Send encouraging message
        encouragement = ENCOURAGING_MESSAGES[total_drunk % len(ENCOURAGING_MESSAGES)]  # Cycle through messages

        # Check if the user has reached the target
        if total_drunk >= target:
            await update.message.reply_text(f"🎉 Congratulations! You've reached your daily water goal of {target}ml! Well done!")
            user_data[user_id]['total'] = 0  # Reset the water intake for the next day
        else:
            await update.message.reply_text(f"Nice! You've drunk {total_drunk}ml out of {target}ml today. {encouragement}")

        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("Please input a valid number (in milliliters). Try again.")
        return WATER_INPUT

# Show Water Intake Command
async def show_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display user's current progress"""
    user_id = update.message.from_user.id

    if user_id not in user_data or user_data[user_id]['total'] == 0:
        await update.message.reply_text("You haven't tracked your water intake yet! Use /track to start.")
        return

    total_drunk = user_data[user_id]['total']
    target = user_data[user_id]['target']
    await update.message.reply_text(f"Your current progress: {total_drunk}ml out of {target}ml today. Keep it up!")

# Set Reminder Command
async def setreminder_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set a reminder to drink water"""
    await update.message.reply_text("How often would you like to be reminded to drink water (in hours)?")
    return SET_REMINDER

# Handle Reminder Input
async def reminder_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        reminder_interval = int(update.message.text)
        user_id = update.message.from_user.id

        # Schedule a daily reminder
        scheduler.add_job(
            send_reminder,
            'interval',
            hours=reminder_interval,
            args=[user_id],
            id=f"reminder_{user_id}",
            replace_existing=True
        )

        await update.message.reply_text(f"Reminder set! I'll remind you every {reminder_interval} hours to drink water.")
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("Please enter a valid number for reminder interval (in hours).")
        return SET_REMINDER

# Send Reminder to Drink Water
async def send_reminder(user_id: int):
    """Send a reminder to drink water"""
    chat_id = user_id
    message = "⏰ Time to drink some water! Stay hydrated!"
    try:
        await context.bot.send_message(chat_id=chat_id, text=message)
    except JobLookupError:
        pass  # The job may have been removed, so we ignore the error

# Cancel Reminder Command
async def cancel_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel the reminder"""
    user_id = update.message.from_user.id
    try:
        scheduler.remove_job(f"reminder_{user_id}")
        await update.message.reply_text("Your reminder has been canceled.")
    except JobLookupError:
        await update.message.reply_text("You don't have any active reminders.")

    return ConversationHandler.END

# Conversation Handler Setup
conversation_handler = ConversationHandler(
    entry_points=[CommandHandler('track', track_command), CommandHandler('setreminder', setreminder_command)],
    states={
        WATER_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, water_input)],
        SET_REMINDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, reminder_input)],
    },
    fallbacks=[CommandHandler('cancel', cancel_reminder)]
)

# Main Function to Run the Bot
def main():
    """Start the bot"""
    app = Application.builder().token(TOKEN).build()

    # Add command handlers
    app.add_handler(CommandHandler('start', start_command))
    app.add_handler(CommandHandler('help', help_command))
    app.add_handler(CommandHandler('show', show_command))
    app.add_handler(conversation_handler)

    # Run the bot
    app.run_polling()

if __name__ == '__main__':
    main()
