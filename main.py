import asyncio
import logging
from fastapi import FastAPI
from contextlib import asynccontextmanager
from src.telegram_bot import run_telegram_bot
from src.agent import gradio_interface
import uvicorn
import gradio as gr
from src.database import engine, Base
from src.init_db import init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    logger.info("Initializing database...")
    init_db()
    logger.info("Starting Telegram bot...")
    telegram_task = asyncio.create_task(run_telegram_bot())
    yield
    logger.info("Shutting down Telegram bot...")
    telegram_task.cancel()
    try:
        await telegram_task
    except asyncio.CancelledError:
        logger.info("Telegram bot shut down successfully")

app = FastAPI(lifespan=lifespan)

# Mount Gradio app to FastAPI
app = gr.mount_gradio_app(app, gradio_interface, path="/")

# Your other FastAPI routes and setup code here

if __name__ == "__main__":
    logger.info("Starting FastAPI application...")
    uvicorn.run("main:app", host="0.0.0.0", port=5000, reload=True)