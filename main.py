import os
import threading
from src.agent import iface
from src.telegram_bot import run_telegram_bot

def run_gradio():
    iface.launch(server_name="0.0.0.0", server_port=int(os.environ.get("PORT", 5000)))

if __name__ == "__main__":
    # Start Gradio interface in a separate thread
    gradio_thread = threading.Thread(target=run_gradio)
    gradio_thread.start()

    # Run Telegram bot in the main thread
    run_telegram_bot()

    # Keep the main thread alive
    gradio_thread.join()