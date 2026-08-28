import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from time import monotonic

from .facts import FactsModel
from .relations import RelationModel
from .further_reading import FurtherReadingModel
from .summary import SummaryModel
from .designer import MdDesignerModel 
from kb_schemas import NoteDesigner, TranscriptionResult


logger = logging.getLogger(__name__)


async def prepare_md(user_id: int, data: TranscriptionResult) -> NoteDesigner:
    started_at = monotonic()
    logger.info("Markdown pipeline started: user_id=%s, source_type=%s, text_length=%s", user_id, data.source_type, len(data.text))
    targets = {
        "facts": FactsModel.process,
        "relations": RelationModel.process,
        "further_reading": FurtherReadingModel.process,
        "summary": SummaryModel.process,
    }

    loop = asyncio.get_event_loop()

    with ThreadPoolExecutor(max_workers=len(targets)) as pool:
        futures = {
            name: loop.run_in_executor(pool, func, user_id, data)
            for name, func in targets.items()
        }

        errors = {}
        for name, fut in futures.items():
            try:
                await fut
                logger.debug("Markdown stage completed: user_id=%s, stage=%s", user_id, name)
            except Exception as e:
                logger.exception("Markdown stage failed: user_id=%s, stage=%s", user_id, name)
                errors[name] = e
    results: dict = {name: fut.result() for name, fut in futures.items() if not fut.exception()}

    if errors:
        name, exc = next(iter(errors.items()))
        logger.error("Markdown pipeline aborted: user_id=%s, failed_stage=%s", user_id, name)
        raise RuntimeError(f"Поток '{name}' завершился с ошибкой") from exc

    if len(results) != len(targets):
        logger.error("Markdown pipeline incomplete: user_id=%s, completed_stages=%s, expected_stages=%s", user_id, len(results), len(targets))
        return None

    try:
        md = await loop.run_in_executor(None, MdDesignerModel.process, results, data)
    except Exception:
        logger.exception("Note design failed: user_id=%s", user_id)
        raise

    if not md:
        logger.error("Note design returned empty result: user_id=%s", user_id)
        return None

    logger.info("Markdown pipeline completed: user_id=%s, duration_ms=%s", user_id, round((monotonic() - started_at) * 1000))
    return md



    # 1.6 [LOW] Общий словарь results пишется из разных потоков без синхронизации

    # md_pipeline.py — каждый worker пишет results[key] = value из своего потока executor'а. Присваивание по ключу в CPython обычно атомарно благодаря GIL, но это неявная гарантия, на которую не стоит полагаться в архитектурном коде — лучше собирать результаты через future.result(), а не через shared mutable state.