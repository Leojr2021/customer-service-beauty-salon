import os
import threading
from src.agent import iface
from src.telegram_bot import run_telegram_bot
from telegram.ext import Application
import asyncio
from telegram.error import NetworkError, Conflict

def run_gradio():
    iface.launch(server_name="0.0.0.0", server_port=int(os.environ.get("PORT", 5000)))

async def run_bot():
    application = Application.builder().token(os.getenv("TELEGRAM_BOT_TOKEN")).build()
    
    while True:
        try:
            await application.initialize()
            await application.start()
            await application.bot.delete_webhook()  # Add this line to reset the webhook
            await run_telegram_bot(application)
            await application.stop()
        except NetworkError:
            print("Network error occurred. Retrying in 10 seconds...")
            await asyncio.sleep(10)
        except Conflict:
            print("Conflict error occurred. Resetting webhook and retrying in 10 seconds...")
            await application.bot.delete_webhook()
            await asyncio.sleep(10)
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            break

async def main():
    # Start Gradio interface in a separate thread
    gradio_thread = threading.Thread(target=run_gradio)
    gradio_thread.start()

    # Run Telegram bot in the main thread
    await run_bot()

    # Keep the main thread alive
    gradio_thread.join()

if __name__ == "__main__":
    asyncio.run(main())