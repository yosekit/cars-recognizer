"""Клиент для Hugging Face Inference API."""

import asyncio
import hashlib
import logging
import os
from collections import OrderedDict

import aiohttp

from models.schemas import Prediction

logger = logging.getLogger(__name__)

default_model = "google/vit-base-patch16-224"

API_URL = f"https://router.huggingface.co/hf-inference/models/{os.getenv('HF_MODEL', default_model)}"
API_TOKEN = os.getenv("HF_API_TOKEN", "")
TIMEOUT_SECONDS = 30

# In-memory кеш результатов: ключ — SHA-256 хеш файла, значение — список предсказаний.
_CACHE_MAX_SIZE = 128
_cache: OrderedDict[str, list[Prediction]] = OrderedDict()


def _compute_file_hash(data: bytes) -> str:
    """Вычисляет SHA-256 хеш содержимого файла."""
    return hashlib.sha256(data).hexdigest()


def _get_cached(file_hash: str) -> list[Prediction] | None:
    """Возвращает кешированный результат или None."""
    if file_hash in _cache:
        _cache.move_to_end(file_hash)
        logger.info("Результат найден в кеше (hash=%s...)", file_hash[:12])
        return _cache[file_hash]
    return None


def _put_cache(file_hash: str, predictions: list[Prediction]) -> None:
    """Сохраняет результат в кеш с вытеснением старых записей."""
    _cache[file_hash] = predictions
    _cache.move_to_end(file_hash)
    if len(_cache) > _CACHE_MAX_SIZE:
        _cache.popitem(last=False)


def clear_cache() -> None:
    """Очищает кеш результатов."""
    _cache.clear()
    logger.info("Кеш результатов очищен")


async def classify_image(image_path: str) -> list[Prediction]:
    """Отправляет изображение в Hugging Face API для классификации.

    Результаты кешируются по хешу содержимого файла.

    Args:
        image_path: Путь к файлу изображения.

    Returns:
        Список из top-3 предсказаний, отсортированных по убыванию confidence.

    Raises:
        RuntimeError: При ошибке API.
    """
    if not API_TOKEN:
        raise RuntimeError("HF_API_TOKEN не задан. Установите переменную окружения.")

    with open(image_path, "rb") as f:
        data = f.read()

    # Проверяем кеш
    file_hash = _compute_file_hash(data)
    cached = _get_cached(file_hash)
    if cached is not None:
        return cached

    headers = {"Authorization": f"Bearer {API_TOKEN}"}
    timeout = aiohttp.ClientTimeout(total=TIMEOUT_SECONDS)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        try:
            async with session.post(API_URL, headers=headers, data=data) as response:
                if response.status == 401:
                    raise RuntimeError("Неверный HF_API_TOKEN.")
                if response.status == 503:
                    body = await response.json()
                    if "loading" in body.get("error", "").lower():
                        logger.info("Модель загружается, ждем 5 секунд...")
                        await asyncio.sleep(5)
                        return await classify_image(image_path)  # рекурсивный повтор
                    raise RuntimeError(f"Модель недоступна: {body.get('error')}")
                if response.status == 429:
                    raise RuntimeError("Превышен лимит запросов к API. Попробуйте позже.")
                if response.status != 200:
                    text = await response.text()
                    raise RuntimeError(f"Ошибка API (status={response.status}): {text}")

                result = await response.json()
                logger.info("Получен ответ от HF API: %d предсказаний", len(result))

        except aiohttp.ClientError as e:
            logger.error("Ошибка соединения с HF API: %s", str(e))
            raise RuntimeError(f"Ошибка соединения с API: {str(e)}")

    # Сортируем по score по убыванию и берём top-3
    sorted_result = sorted(result, key=lambda x: x["score"], reverse=True)
    top3 = sorted_result[:3]
    predictions = [
        Prediction(label=item["label"], confidence=round(item["score"], 4))
        for item in top3
    ]

    # Сохраняем в кеш
    _put_cache(file_hash, predictions)

    return predictions
