import asyncio
import os
import logging
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message
from dotenv import load_dotenv
from logger import setup_logging

from router import new_data, task_queue
from modules.md_pipeline.relations.db_search_client import close_http_client as close_search_client
from modules.to_db.db_client import close_http_client as close_db_client
from config import settings


load_dotenv()
setup_logging(service="telegram", format=settings.log.format, stream_level=settings.log.level)
logger = logging.getLogger(__name__)


token = settings.telegram_api_token
bot = Bot(token=token)
dp = Dispatcher()


@dp.message(F.text, ~F.text.startswith('/'))
async def catch_message(message: Message):
    status = new_data(message.from_user.id, message.text, 'text', datetime.now().isoformat())
    if status:
        logger.info("Message accepted: user_id=%s, data_type=text, text_length=%s", message.from_user.id, len(message.text))
        await message.reply("Text received!")
    else:
        logger.warning("Message rejected: user_id=%s, data_type=text", message.from_user.id)
        await message.reply("Failed to receive the text.\nTry again later!")


# @dp.message(F.voice | F.audio)
# async def catch_audio(message: Message):
#     # Get file ID for voice or standard audio
#     file_id = message.voice.file_id if message.voice else message.audio.file_id
#     # Retrieve file info from Telegram servers
#     file_info = await bot.get_file(file_id)
#     await message.reply("Audio caught successfully!")


# @dp.message(F.photo)
# async def catch_image(message: Message):
#     # Get file ID for the image
#     file_id = message.photo[-1].file_id  # Get the largest image
#     # Retrieve file info from Telegram servers
#     file_info = await bot.get_file(file_id)
#     await message.reply("Photo caught successfully!")


# @dp.message(F.video)
# async def catch_video(message: Message):
#     # Get file ID for the video
#     file_id = message.video.file_id
#     # Retrieve file info from Telegram servers
#     file_info = await bot.get_file(file_id)
#     await message.reply("Video caught successfully!")


# Start
@dp.message(CommandStart())
async def start(message: Message):
    logger.info("User started bot: user_id=%s", message.from_user.id)
    await message.reply("Welcome to the bot!")


async def run_bot():
    logger.info("Telegram service starting: workers=%s", task_queue._worker_count)
    task_queue.start()
    try:
        await dp.start_polling(bot)
    finally:
        await task_queue.stop()
        await close_search_client()
        await close_db_client()
        await bot.session.close()
        logger.info("Telegram service stopped")


if __name__ == "__main__":
    asyncio.run(run_bot())