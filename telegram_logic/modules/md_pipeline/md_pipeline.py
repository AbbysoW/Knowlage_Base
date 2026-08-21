import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor

import facts, relations, further_reading, summary
import designer
from kb_schemas import NoteDesigner, TranscriptionResult

logger = logging.getLogger(__name__)


async def prepare_md(user_id: int, data: TranscriptionResult) -> NoteDesigner:
    targets = {
        "facts": facts.FactsModel.process,
        "relations": relations.RelationModel.process,
        "further_reading": further_reading.FurtherReadingModel.process,
        "summary": summary.SummaryModel.process,
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
            except Exception as e:
                logger.exception("Поток '%s' упал", name)
                errors[name] = e
    results: dict = {name: fut.result() for name, fut in futures.items() if not fut.exception()}

    if errors:
        name, exc = next(iter(errors.items()))
        raise RuntimeError(f"Поток '{name}' завершился с ошибкой") from exc

    if len(results) != len(targets):
        logger.error("Не все потоки вернули результат: %d из %d", len(results), len(targets))
        return None

    try:
        md = await loop.run_in_executor(None, designer.MdDesignerModel.process, results)
    except Exception:
        logger.exception("designer.MdDesignerModel.process упал с ошибкой")
        raise

    if not md:
        logger.error("designer.MdDesignerModel.process вернул пустой результат")
        return None

    return md



    # 1.6 [LOW] Общий словарь results пишется из разных потоков без синхронизации

    # md_pipeline.py — каждый worker пишет results[key] = value из своего потока executor'а. Присваивание по ключу в CPython обычно атомарно благодаря GIL, но это неявная гарантия, на которую не стоит полагаться в архитектурном коде — лучше собирать результаты через future.result(), а не через shared mutable state.