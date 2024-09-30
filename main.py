import threading
from src.agent import iface
from src.telegram_bot import run_telegram_bot

def run_gradio():
    iface.launch()

if __name__ == "__main__":
    # Start Gradio interface in a separate thread
    gradio_thread = threading.Thread(target=run_gradio)
    gradio_thread.start()

    # Run Telegram bot in the main thread
    run_telegram_bot()