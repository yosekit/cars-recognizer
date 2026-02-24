"""Клиент для Hugging Face Inference API."""

import logging
import os

import aiohttp

from models.schemas import Prediction

logger = logging.getLogger(__name__)

API_URL = "https://api-inference.huggingface.co/models/google/vit-base-patch16-224"
API_TOKEN = os.getenv("HF_API_TOKEN", "")
TIMEOUT_SECONDS = 30


async def classify_image(image_path: str) -> list[Prediction]:
    """Отправляет изображение в Hugging Face API для классификации.

    Args:
        image_path: Путь к файлу изображения.

    Returns:
        Список из top-3 предсказаний.

    Raises:
        RuntimeError: При ошибке API.
    """
    if not API_TOKEN:
        raise RuntimeError("HF_API_TOKEN не задан. Установите переменную окружения.")

    headers = {"Authorization": f"Bearer {API_TOKEN}"}

    with open(image_path, "rb") as f:
        data = f.read()

    timeout = aiohttp.ClientTimeout(total=TIMEOUT_SECONDS)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        try:
            async with session.post(API_URL, headers=headers, data=data) as response:
                if response.status == 401:
                    raise RuntimeError("Неверный HF_API_TOKEN.")
                if response.status == 503:
                    body = await response.json()
                    msg = body.get("error", "Модель загружается, попробуйте позже.")
                    raise RuntimeError(f"Модель недоступна: {msg}")
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

    # Берём top-3 предсказания
    top3 = result[:3]
    predictions = [
        Prediction(label=item["label"], confidence=round(item["score"], 4))
        for item in top3
    ]
    return predictions
