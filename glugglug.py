from typing import Final
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from datetime import datetime, timedelta, time
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.base import JobLookupError
from dotenv import load_dotenv
import os

# Load environment variables from the .env file
load_dotenv()

# Retrieve the bot token from environment variables
TOKEN = os.getenv("BOT_TOKEN")

# Ensure the token is successfully loaded
if TOKEN is None:
    raise ValueError("Bot token not found. Please set the BOT_TOKEN in the .env file.")

BOT_USERNAME: Final = "@glugglugbot"

# Constants
TARGET_WATER_INTAKE = 2000  # Daily water intake target in milliliters (adjust as needed)
WAKE_UP_TIME = time(6, 0)   # Waking up at 8:00 AM
SLEEP_TIME = time(23, 0)    # Going to bed at 11:00 PM
ENCOURAGING_MESSAGES = [
    "Great job, keep going!",
    "You're doing awesome!",
    "Keep it up, you're almost there!",
    "Drink up, stay hydrated!",
    "Hydration is key! You're doing well!"
    "Half full water bottle drink up!"
]

# Dictionary to store user's water intake and reminder settings
user_data = {}

# Initialize scheduler
scheduler = BackgroundScheduler()
scheduler.start()

# State for conversation handler
WATER_INPUT, SET_REMINDER = range(2)

# Utility Function: Calculate target water intake at a given time
def calculate_target_water(current_time: datetime) -> int:
    """Calculate the target water intake based on the current time."""
    start = datetime.combine(current_time.date(), WAKE_UP_TIME)
    end = datetime.combine(current_time.date(), SLEEP_TIME)

    # Total waking duration in seconds
    total_duration = (end - start).total_seconds()

    # Elapsed time since waking up in seconds
    elapsed_time = (current_time - start).total_seconds()

    # Avoid negative values before waking up
    if elapsed_time < 0:
        elapsed_time = 0

    # Calculate proportional water intake
    target = int((elapsed_time / total_duration) * TARGET_WATER_INTAKE)
    return target

# Start Command
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome to the Drinking Water Tracker Bot!" + "\n" + "Use /track to input your daily water intake, /show to check your progress, and /setreminder to set reminders.")

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

        # Schedule a personalized reminder
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
    """Send a personalized reminder to drink water"""
    chat_id = user_id
    current_time = datetime.now()
    target_by_now = calculate_target_water(current_time)
    how_much_drank = water_input(WATER_INPUT)
    message = f"⏰ It's {current_time.strftime('%H:%M')}! By now, you should have drunk approximately {target_by_now}ml of water. You have drank {how_much_drank}ml. Stay hydrated!"
    try:
        # Assuming `context` is globally accessible or passed explicitly
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
    app.add_handler(CommandHandler('show', show_command))
    app.add_handler(conversation_handler)

    # Run the bot
    print("Polling...")
    app.run_polling(poll_interval=3)

if __name__ == '__main__':
    main()
