import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor

import facts, relations, further_reading, summary
import designer
from kb_schemas import NoteDesigner, TranscriptionResult

logger = logging.getLogger(__name__)


async def prepare_md(user_id: int, data: TranscriptionResult) -> NoteDesigner:
    results: dict = {}

    targets = {
        "facts": facts.process,
        "relations": relations.process,
        "further_reading": further_reading.process,
        "summary": summary.process,
    }

    loop = asyncio.get_event_loop()

    with ThreadPoolExecutor(max_workers=len(targets)) as pool:
        futures = {
            name: loop.run_in_executor(pool, func, user_id, data, results)
            for name, func in targets.items()
        }

        errors = {}
        for name, fut in futures.items():
            try:
                await fut
            except Exception as e:
                logger.exception("Поток '%s' упал", name)
                errors[name] = e
                

    if errors:
        name, exc = next(iter(errors.items()))
        raise RuntimeError(f"Поток '{name}' завершился с ошибкой") from exc

    if len(results) != len(targets):
        logger.error("Не все потоки вернули результат: %d из %d", len(results), len(targets))
        return None

    try:
        md = await loop.run_in_executor(None, designer.process, results)
    except Exception:
        logger.exception("designer.process упал с ошибкой")
        raise

    if not md:
        logger.error("designer.process вернул пустой результат")
        return None

    return md