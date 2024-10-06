import asyncio
from fastapi import FastAPI
from contextlib import asynccontextmanager
from src.telegram_bot import run_telegram_bot
from src.agent import gradio_interface
import uvicorn
import gradio as gr

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Run the Telegram bot
    telegram_task = asyncio.create_task(run_telegram_bot())
    yield
    # Shutdown: Cancel the Telegram bot task
    telegram_task.cancel()
    try:
        await telegram_task
    except asyncio.CancelledError:
        pass

app = FastAPI(lifespan=lifespan)

# Mount Gradio app to FastAPI
app = gr.mount_gradio_app(app, gradio_interface, path="/")

# Your other FastAPI routes and setup code here

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=5000, reload=True)