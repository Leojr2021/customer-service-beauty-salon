import os
import asyncio
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from src.agent import chat_with_ai

load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG
)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info(f"Received /start command from user {update.effective_user.id}")
    await update.message.reply_text('Welcome to Zen Beauty Salon Assistant! How may I assist you today?')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info(f"Received message from user {update.effective_user.id}: {update.message.text}")
    try:
        user_message = update.message.text
        chat_history = context.user_data.get('chat_history', [])
        
        # Run chat_with_ai in a separate thread to avoid blocking
        ai_response = await asyncio.to_thread(chat_with_ai, user_message, chat_history)
        
        logger.info(f"Sending response to user {update.effective_user.id}: {ai_response}")
        await update.message.reply_text(ai_response)
        
        # Update chat history
        if 'chat_history' not in context.user_data:
            context.user_data['chat_history'] = []
        context.user_data['chat_history'].append((user_message, ai_response))
        
        # Limit chat history to last 10 messages
        context.user_data['chat_history'] = context.user_data['chat_history'][-10:]
    except Exception as e:
        logger.error(f"Error processing message for user {update.effective_user.id}: {str(e)}")
        await update.message.reply_text("I apologize, but I encountered an error while processing your message. Please try again later.")

async def run_telegram_bot():
    logger.info("Initializing Telegram bot...")
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Starting Telegram bot polling...")
    await application.initialize()
    await application.start()
    await application.updater.start_polling(allowed_updates=Update.ALL_TYPES)
    
    # Run the bot until the application is stopped
    logger.info("Bot is running. Press Ctrl-C to stop.")
    stop_signal = asyncio.Event()
    await stop_signal.wait()

if __name__ == '__main__':
    try:
        asyncio.run(run_telegram_bot())
    except KeyboardInterrupt:
        logger.info("Bot stopped manually")
    except Exception as e:
        logger.exception(f"Error occurred: {e}")