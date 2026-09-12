import argparse
import asyncio
import logging
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from logger import setup_logging

from router import new_data, task_queue
from modules.md_pipeline.relations.db_search_client import close_http_client as close_search_client
from modules.to_db.db_client import close_http_client as close_db_client
from config import settings


load_dotenv()
setup_logging(service="cli", format=settings.log.format, stream_level=settings.log.level)
logger = logging.getLogger(__name__)


DEFAULT_USER_ID = 8691426314


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="CLI-версия входной точки приложения (замена Telegram-бота)."
    )

    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument(
        "--text",
        type=str,
        help="Произвольный текст, переданный прямо из консоли.",
    )
    source_group.add_argument(
        "--file",
        type=str,
        help="Путь к .txt файлу, содержимое которого будет обработано.",
    )

    parser.add_argument(
        "--user-id",
        type=int,
        default=DEFAULT_USER_ID,
        help=f"ID пользователя (по умолчанию: {DEFAULT_USER_ID}).",
    )

    return parser.parse_args()


def read_text_source(args: argparse.Namespace) -> str:
    if args.text is not None:
        return args.text

    file_path = Path(args.file)
    if not file_path.is_file():
        raise FileNotFoundError(f"Файл не найден: {file_path}")

    return file_path.read_text(encoding="utf-8")


async def catch_message(user_id: int, text_content: str) -> None:
    status = new_data(user_id, text_content, 'text', datetime.now().isoformat())
    if status:
        logger.info(
            "Message accepted: user_id=%s, data_type=text, text_length=%s",
            user_id, len(text_content)
        )
        print("Text received!")
    else:
        logger.warning("Message rejected: user_id=%s, data_type=text", user_id)
        print("Failed to receive the text.\nTry again later!")


async def run_cli():
    args = parse_args()

    try:
        text_content = read_text_source(args)
    except (FileNotFoundError, OSError, UnicodeDecodeError) as e:
        logger.error("Не удалось прочитать источник текста: %s", e)
        print(f"Failed to read input: {e}")
        return

    logger.info("CLI service starting: workers=%s", task_queue._worker_count)
    task_queue.start()
    try:
        await catch_message(args.user_id, text_content)
    finally:
        await task_queue.stop()
        await close_search_client()
        await close_db_client()
        logger.info("CLI service stopped")


if __name__ == "__main__":
    asyncio.run(run_cli())