# BACKLOG

Аудит кодовой базы против ТЗ (статический, код не запускался). Где вывод зависит от версий библиотек (Chroma, httpx, torch) — помечено «проверить».

**Оценка трудоёмкости:** `S` — до 2 ч · `M` — полдня–день · `L` — несколько дней.

**Приоритеты:** 🔥 Горит — без этого не запускается или теряет данные · ⚠️ Важно — надёжность, UX и ядро ТЗ · 🧭 Потом — расширения и масштаб.

---

## Статус

**Работает (только текстовый путь):** Telegram-бот (aiogram) → `TaskQueue` (3 воркера, в памяти) → `prepare_md` (4 параллельные LLM-стадии: facts / relations / further_reading / summary) → `MdDesignerModel` → `Split` (LLM-чанкинг + эмбеддинги) → сервис `database` (FastAPI): сага с WAL — `.md` с YAML-frontmatter → SQLite-метаданные → Chroma. Есть per-user lock, retry на `RateLimitError`, подробное логирование, dev/prod compose, общий пакет `kb_schemas`.

**Не реализовано:** голос / PDF / изображения / видео / ссылки, Attachment Store, Git-vault, категория по confidence и `_inbox/_unsorted`, реструктуризатор, MOC, RAG-поиск, read/update, тесты. Корневые `README.md`, `main.py`, `pyproject.toml`, `Dockerfile` пустые.

**Скан на маркеры:** литералов `TODO` / `FIXME` / `NotImplementedError` нет.
- Заглушки `pass`: `FileStore.read/update`, `SqliteStore.read/update`, ветка `except ValueError` в `router.process_data`.
- Мёртвый код: после `return # пока не надо` в `recover_pending_transactions`; закомментированные хендлеры audio/photo/video в `bot.py` и `transcriber_registry` в `router.py`.
- Неиспользуемое: импорты `apscheduler` (×2), `WeakValueDictionary`, `dataclass`, `os`; модель `Note` в `kb_schemas`; `VectorStore.delete_list`.
- Забытая заметка «1.6 [LOW]» в конце `md_pipeline.py` — проблема уже решена (результаты собираются через `fut.result()`), комментарий удалить.

---

## 🔥 Горит

### Блокеры запуска

- [ ] **`S`** `docker-compose.yml`: блок `volumes:` стоит с отступом внутри `services:` — вынести на верхний уровень, иначе compose невалиден.
- [ ] **`S`** Пути томов не совпадают с путями приложения: тома смонтированы в `/data/files`, `/data/metadata`, `/data/vectors`, `/var/data/wal`, а приложение пишет в относительные `data/...` и `var/data/wal` (то есть в `/app/...`) — данные пропадут при пересоздании контейнера. Задать абсолютные пути через env (`DB__FILE_STORE__PATH=/data/files` и т.д.) или смонтировать тома в `/app/data/...`.
- [ ] **`S`** Образы не собираются / падают на старте:
  - `packages/logger` не копируется и не ставится ни в одном Dockerfile, но импортируется в `bot.py`, `commands.py`, `server.py`;
  - `tenacity` (`llm_client.py`) отсутствует в `requirements.txt`;
  - `apscheduler` и `sqlalchemy` (импорты в `router.py`) отсутствуют — добавить или удалить импорты.
- [ ] **`S`** `setup_logging(service=None)` падает: `Path('logs') / service` выполняется до проверки `if service`. Заодно: логи пишутся внутрь контейнера без тома.
- [ ] **`S`** Образ telegram_logic: CPU-сборка torch (`--extra-index-url https://download.pytorch.org/whl/cpu`); модель эмбеддингов скачивать при сборке или монтировать `HF_HOME` как том (иначе качается при каждом пересоздании контейнера).

### Обработка исключений

- [ ] **`M`** `md_pipeline.prepare_md`: `with ThreadPoolExecutor(...)` внутри `async`-функции — при выходе `shutdown(wait=True)`; зависший после таймаута поток **блокирует весь event loop**. Заменить на `asyncio.to_thread` + `asyncio.gather(..., return_exceptions=True)` либо `pool.shutdown(wait=False, cancel_futures=True)`. Заодно `get_event_loop()` → `get_running_loop()`.
- [ ] **`M`** Политика по стадиям пайплайна: сейчас ошибка любой из 4 стадий убивает всю заметку. Сделать summary и designer обязательными, facts / relations / further_reading — опциональными (деградация до `[]` с пометкой «стадия пропущена»).
- [ ] **`S`** `prepare_md`: два `return None` (неполные результаты, пустой designer) приводят к `AttributeError` в `router.process_data` (`md.formatter.title`) и `ToDB`. Заменить на типизированный `PipelineError`.
- [ ] **`M`** `llm_client.py`:
  - `@retry` без `reraise=True` — наверх уходит `tenacity.RetryError` вместо `RateLimitError`;
  - ретраится только `RateLimitError` — добавить `APIConnectionError`, `APITimeoutError`, 5xx; ошибки 401/402/400 считать permanent и алертить админа (кончился баланс);
  - у `OpenAI(...)` не заданы `timeout` и `max_retries` (по умолчанию 600 с и 2 повтора) — это ломает таймауты стадий (90–120 с); поставить `timeout≈60` и согласовать с tenacity;
  - нет проверки `content is None`, пустой строки, `finish_reason == "length"`; без `max_tokens` длинный JSON обрезается и `model_validate_json` падает — нужен явный `max_tokens` и одна попытка «починки»;
  - имя модели и `base_url` захардкожены — вынести в `settings`.
- [ ] **`M`** `relations.py`: `ProcessPoolExecutor(max_workers=1)` создаётся **на каждый вызов**, каждый новый процесс заново грузит SentenceTransformer — при таймауте 30 с это почти всегда `[]`. Считать эмбеддинг в главном процессе через `asyncio.to_thread` (проверить: fork после инициализации потоков и torch может дедлочить).
- [ ] **`M`** `relations.py` + `db_search_client.py`: `asyncio.run()` внутри потока создаёт новый loop на каждый вызов, а `httpx.AsyncClient` живёт на уровне модуля — переиспользование keep-alive соединений из другого loop даёт `Event loop is closed` (проверить); ошибку глотает `except Exception` → `None` → relations пустые. Вызывать `_fetch_articles` напрямую из основного loop.
- [ ] **`S`** `relations.py`: постфильтр — оставлять только `target_note_path` из списка кандидатов (LLM может выдумать путь); дедуплицировать кандидатов по `path` (`read_nearest` возвращает чанки).
- [ ] **`M`** `db_client.post_new_article`: все ошибки превращаются в `None`, вызывающий не отличает таймаут / 4xx / 5xx. Нужны типизированные исключения, ретрай на connect-ошибки и 5xx, **idempotency key** (например, hash заметки): read-timeout (10 с) возможен при том, что сервер уже закоммитил, и повтор даёт `FileExistsError`.
- [ ] **`S`** `router.transcribe`: `except KeyError` ловит и `KeyError` **внутри** будущих транскриберов, маскируя под «unsupported data_type». Проверять `data_type in registry` до вызова.
- [ ] **`M`** `task_queue.py`: `stop()` делает `queue.join()` без таймаута (зависшая задача → shutdown висит до SIGKILL); нет таймаута на задачу (`asyncio.wait_for(handler, job_timeout)`), нет retry и dead-letter.
- [ ] **`M`** `bot.py`: нет `@dp.errors()` и глобального обработчика; `message.from_user` может быть `None` (анонимный админ, канал); сами `message.reply()` могут падать (`TelegramRetryAfter`, бот заблокирован) — обёртка `safe_send`.
- [ ] **`M`** `logic.Transaction._rollback`: при падении одной компенсации делает `raise` и **не откатывает оставшиеся шаги** — продолжать цикл и собирать ошибки.
- [ ] **`S`** `logic.Transaction.run`: `failed_name = self.steps[len(completed)].name` неверно, если исключение случилось после `completed.append(...)` (например, `_write_wal` на диске без места); для последнего шага — `IndexError` внутри `except`, откат не запустится. Хранить `current_step` отдельно.
- [ ] **`M`** `logic.recover_pending_transactions` — no-op (`return # пока не надо`): WAL пишется, но не читается. Реализовать: для `pending` компенсировать `completed`, для `rollback_failed` — алерт админу.
- [ ] **`S`** `_write_wal_sync` не атомарна: `write_text` может оставить битый файл — писать во временный файл и `os.replace`.
- [ ] **`M`** `database/server.py`: любая ошибка → 500 «Failed to create article». Нужны коды: 409 дубликат, 422 невалидный payload, 500 с `failed_step` для `TransactionError`, единый формат тела `{status: "error", code: ...}`. Добавить `@app.exception_handler(Exception)` и `/health`. Заменить `from fastapi.concurrency import asynccontextmanager` на `from contextlib import asynccontextmanager`.
- [ ] **`S`** `split_model.py`: если LLM вернул `chunks == []`, заметка сохранится без векторов и без ошибки. Нужен fallback (детерминированный сплит или один чанк).
- [ ] **`S`** Чтение промптов: `open(..., "r")` без `encoding="utf-8"` (на Windows читает русские промпты в cp1251), ловится только `FileNotFoundError`. Кэшировать промпты один раз при импорте.

### Потеря данных и безопасность

- [ ] **`S`** `VectorStore._gen_id` = `int(time()*1000)` в цикле — чанки в одну миллисекунду получают одинаковые ID (тихо игнорируются или `DuplicateIDError` — проверить по версии Chroma). Использовать `f"{path}#{i}"` и один batch-`add`/`upsert`.
- [ ] **`M`** Коллизии `file_name`: имя генерирует LLM, `open("x")` падает с `FileExistsError`, заметка теряется (пользователь уже получил «Text received!»). Нужна стратегия суффикса/хэша.
- [ ] **`S`** Компенсация `SqliteStore.delete` удаляет по `(user_id, title, category)` — при откате может стереть метаданные другой заметки с тем же заголовком. Удалять по `id` из `step.result`.
- [ ] **`S`** Path traversal от LLM: `primary_category` и `file_name` идут в `Path` без санитизации (`../..` или абсолютный путь выведут запись за пределы vault; вход контролирует пользователь через промпт). Нормализовать `\` → `/` (промпт designer сам разрешает `\`), проверять `resolve().is_relative_to(base)`.
- [ ] **`S`** YAML в `FileStore._format_yaml`: `title: "%s"` ломается при кавычке в заголовке, сущности вроде `C#` или с `:` ломают списки. Экранировать через `json.dumps`.
- [ ] **`S`** Сервис `database` опубликован наружу (`5432:5432`) без авторизации — убрать публикацию порта или добавить API-ключ.
- [ ] **`S`** У бота нет allow-list: любой нашедший бота тратит токены DeepSeek. Добавить список разрешённых `user_id`.

### Уведомления пользователей

Сейчас пользователь видит только «Text received!» / «Failed to receive…» (очередь переполнена). Всё остальное — только в логах.

- [ ] **`M`** Абстракция `Notifier` (`BotNotifier` через `send_message` / `edit_message_text`, `CliNotifier` для `commands.py`).
- [ ] **`S`** Расширить `Job` полями `chat_id`, `message_id`; завести `job_id` и добавить во все логи для корреляции.
- [ ] **`M`** Иерархия ошибок `UserFacingError(user_message)` / `RetryableError` / `PermanentError`; тексты — в одном `messages.py` (ответы бота сейчас на английском, промпты на русском).
- [ ] **`S`** Хук `on_job_failed` в `TaskQueue._worker_loop`: сейчас `process_data` делает `raise`, воркер пишет только в лог.
- [ ] **`S`** `router.process_data`: заполнить заглушку в `except ValueError` («send user error message») — сейчас `pass`.
- [ ] **`S`** Catch-all `@dp.message()` в `bot.py`: голос / фото / видео / документ / стикер / команды кроме `/start` сейчас получают **полную тишину**. Ответ: «Этот тип пока не поддерживается».
- [ ] **`S`** Валидация входа в `transcribe`: пустой и слишком длинный текст → понятное сообщение.
- [ ] **`S`** Итоговое сообщение об успехе: «✅ Сохранено: *title* → `category/file`».
- [ ] **`M`** Прогресс: правка того же сообщения по стадиям («Транскрибирую… / Анализирую… / Сохраняю…»).
- [ ] **`M`** Частичный успех: при таймауте опциональных стадий — «Сохранено без связей / без источников».
- [ ] **`S`** Сбой `send_to_db` → «Заметка обработана, но не сохранена, повторю позже».
- [ ] **`S`** `rollback_failed` / `logger.critical` дублировать в админ-чат (`ADMIN_CHAT_ID`).

---

## ⚠️ Важно

### Транскрибер файлов

Сейчас `transcriber_registry` содержит только `'text'`. Хендлеры бота для voice / photo / video закомментированы и ничего не качают; ссылки не распознаются (URL уходит в LLM как обычная строка, и модель выдумывает содержимое). Порядок ниже — по логике внедрения.

- [ ] **`M`** Контракт транскрибера:
  - типизированный `IncomingItem(kind, payload/path, mime, file_name, size, file_id, chat_id, message_id)` вместо `Job.data: Any` — передавать путь, не байты, чтобы задачу можно было сериализовать;
  - `Transcriber` (Protocol) с `async transcribe(item) -> TranscriptionResult`;
  - блокирующие STT / OCR / yt-dlp вызывать через `asyncio.to_thread` или subprocess;
  - лимиты в `config.py`: размер, длительность, страницы, таймаут;
  - заполнять уже существующие поля `source_ref`, `duration_sec`, `confidence`.
- [ ] **`S`** Текст: валидация + map-reduce для длинных текстов (час видео ≈ 50–60K токенов, а все 4 стадии шлют полный текст в каждый вызов).
- [ ] **`M`** Хендлеры бота для voice / audio / photo / document / video / video_note. Скачивание — в воркере через `bot.download`, в задаче хранить `file_id`. **Cloud Bot API отдаёт файлы только до 20 МБ** — для больших нужен локальный Bot API server, иначе отклонять с понятным сообщением.
- [ ] **`L`** Ссылки: определение URL по `message.entities` и роутинг:
  - YouTube / TikTok → видео-пайплайн; ссылка на PDF → PDF-пайплайн; картинка → OCR;
  - иначе `httpx` + `trafilatura` (лимит размера, редиректы, таймаут); при 403 / paywall — понятная ошибка;
  - **обязательна SSRF-защита**: блокировать localhost, приватные диапазоны и metadata-адреса, иначе пользователь заставит бота ходить в `http://database:5432`.
- [ ] **`L`** PDF: текстовый слой через PyMuPDF (`pymupdf4llm`); если текста мало (скан) — растеризация страниц + OCR; отдельно обработать пароль, лимит страниц и таблицы.
- [ ] **`M`** Изображения: OCR (Tesseract rus+eng) с предобработкой (EXIF-поворот, ресайз); для фото без текста нужен vision-LLM (проверить, принимает ли текущая модель изображения, иначе понадобится отдельный провайдер); альбомы группировать по `media_group_id`.
- [ ] **`L`** Голос / аудио: Telegram отдаёт OGG/Opus → нужен ffmpeg. STT ещё не выбран (локальный faster-whisper или API; у API обычно лимит ≈25 МБ → нарезка; DeepSeek STT не даёт). Задавать язык, писать `confidence` и `duration_sec`.
- [ ] **`L`** Видео: `yt-dlp` — сначала субтитры, при отсутствии аудио + STT; лимит длительности; таймаут через `asyncio.create_subprocess_exec`; очистка временных файлов; в `source_ref` писать URL (по ТЗ видео целиком не хранится). Учесть обновления yt-dlp и cookies для антибот-защиты. Присланный файл `F.video` / `video_note` → ffmpeg → аудио → STT.
- [ ] **`M`** Attachment Store (ТЗ 2.3): `attachments/{sha256[:2]}/{sha256}.{ext}` + таблица `(sha256, mime, size, user_id, source_ref)`; дедуп по хэшу; хранить вне git.
- [ ] **`S`** Dockerfile: `ffmpeg`, `tesseract-ocr`, `tesseract-ocr-rus`; pip: `yt-dlp`, `pymupdf`, `trafilatura`, `pytesseract`, `Pillow`, STT-библиотека.
- [ ] **`S`** Frontmatter (`FileStore._format_yaml`): добавить `source_ref` и `confidence`.
- [ ] **`M`** Тесты транскриберов на фикстурах для каждого формата.

### Ядро ТЗ

- [ ] **`M`** Детерминированные поля вместо LLM-копирования: `created_at`, `source_type`, `facts`, `relations` проставлять в коде после ответа designer. Сейчас LLM должен воспроизвести их дословно, а ТЗ требует, чтобы verbatim-факты не искажались. Плюс проверка, что `fact.content` реально встречается в исходнике.
- [ ] **`S`** `md_designer`: списки форматируются через `%s` (Python-repr `Fact(content=...)`) — передавать `model_dump_json`.
- [ ] **`S`** Порядок сообщений в `llm_client`: system добавляется **после** user — поставить первым (стандарт, лучше следование инструкциям, общий префикс для кэша DeepSeek).
- [ ] **`M`** ТЗ 2.5: чанкинг по секциям. Заменить LLM-чанкер (возвращает всю заметку заново — двойной расход токенов, риск усечения и перефразирования) детерминированным сплитом по `##` / `###` с ограничением по токенам; эмбеддинги считать батчем (`encode(list)`), добавлять заголовок заметки в текст чанка.
- [ ] **`S`** Усечение эмбеддингов: у `paraphrase-multilingual-MiniLM-L12-v2` по умолчанию `max_seq_length=128` (проверить), а чанки по промпту 150–400 слов — вектор описывает только начало чанка. Уменьшить чанки или сменить модель.
- [ ] **`M`** ТЗ 2.6: категория по confidence (`primary_category = argmax(confidence)`), низкая уверенность → `_inbox/_unsorted/`. Сейчас категорию свободно выдумывает LLM и не знает существующего дерева (будет «AI/ML» против «AI/MachineLearning»).
- [ ] **`S`** ТЗ 2.4: «embedding-ссылка» и поля `source_ref`, `id` в frontmatter.
- [ ] **`M`** ТЗ 2.7: расширить SQLite-индекс — `path/file_name`, `updated_at`, уникальность `(user_id, path)`, таблица рёбер для типизированных связей, миграции (`PRAGMA user_version`), read-API.
- [ ] **`M`** WAL: `payload.model_dump()` пишет **все эмбеддинги и весь текст** при каждом обновлении статуса (4 раза на транзакцию) — хранить только идентификаторы и пути.
- [ ] **`M`** CRUD: `read` / `update` (заглушки) в `FileStore` и `SqliteStore`, `update` в `VectorStore`, эндпоинты delete / update, команда бота `/undo`.
- [ ] **`M`** Persistent-очередь: хранить задачи в SQLite-таблице `jobs(status, attempts, error, ...)` — всё принятое («Text received!») сейчас теряется при рестарте; это же даст статусы для уведомлений.
- [ ] **`M`** Ограничить параллелизм: 3 воркера × 4 потока = до 12 параллельных LLM-вызовов и до 3 копий модели в RAM. Общий semaphore на LLM + одна копия модели эмбеддингов.
- [ ] **`M`** Тесты: unit для `Transaction` / `FileStore` / `Formatter`, интеграционный прогон пайплайна с замоканным LLM.

---

## 🧭 Потом

- [ ] **`L`** ТЗ 2.10: Git-vault — одна очередь записи, атомарный коммит на батч, синхронизация. Отдельно предусмотреть реиндекс при правках пользователя в Obsidian.
- [ ] **`L`** ТЗ 2.6: MOC / хаб-заметки, Obsidian Bases.
- [ ] **`L`** Реструктуризатор: планировщик (apscheduler или отдельный контейнер), кластеризация по эмбеддингам, предложения в боте с подтверждением, перемещение заметок. Учесть каскад: путь меняется в SQL, в Chroma metadata и в wikilinks других заметок.
- [ ] **`M`** ТЗ 2.7: derived-граф из wikilinks + frontmatter.
- [ ] **`L`** ТЗ 2.8: RAG / поисковый эндпоинт (metadata-фильтр + вектор), команды `/ask`, `/search`.
- [ ] **`M`** Масштаб 10⁵–10⁶ заметок: batch-вставки в Chroma, версия эмбеддинг-модели в метаданных коллекции для будущего переиндекса.
- [ ] **`S`** Root `README.md`, `pyproject.toml`, ruff / mypy. Учесть: `.github` в `.gitignore` — CI-конфиги не попадут в репозиторий.

### Уборка кода

- [ ] **`S`** `datetime.now()` → `message.date` (UTC), сейчас наивное серверное время.
- [ ] **`S`** Опечатки `neerest` в роутах и именах функций — исправить, пока клиент один.
- [ ] **`S`** `QUERY` как HTTP-метод нестандартен — заменить на POST.
- [ ] **`S`** `commands.py`: убрать захардкоженный реальный `DEFAULT_USER_ID`.
- [ ] **`S`** `EmbeddingModel.__main__` вызывает `.shape` на `list`.
- [ ] **`S`** Опечатки в промптах: «ТБОРА» (relations), «Основовная» (designer).
- [ ] **`S`** Промпт relations просит вернуть `[]`, а формат ответа — объект `{relations: []}`; согласовать.
- [ ] **`S`** Логи без ротации, файл на каждый запуск — добавить `RotatingFileHandler`.
- [ ] **`S`** Удалить мёртвый код и неиспользуемые импорты (см. раздел «Статус»).