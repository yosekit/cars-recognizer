"""Сервис для работы с JSON-хранилищем метаданных изображений."""

import json
import logging
import os
from datetime import datetime
from typing import Optional

from models.schemas import ImageMetadata, Prediction

logger = logging.getLogger(__name__)

METADATA_FILE = os.getenv("METADATA_FILE", "metadata.json")


def _load_metadata() -> list[dict]:
    """Загружает метаданные из JSON-файла."""
    if not os.path.exists(METADATA_FILE):
        return []
    try:
        with open(METADATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        logger.error("Ошибка чтения файла метаданных")
        return []


def _save_metadata(data: list[dict]) -> None:
    """Сохраняет метаданные в JSON-файл."""
    with open(METADATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)


def get_next_id() -> int:
    """Возвращает следующий доступный ID."""
    data = _load_metadata()
    if not data:
        return 1
    return max(item["id"] for item in data) + 1


def add_image(filename: str, path: str, mime_type: str, size_bytes: int) -> ImageMetadata:
    """Добавляет запись о новом изображении.

    Args:
        filename: Имя файла.
        path: Путь к файлу.
        mime_type: MIME-тип файла.
        size_bytes: Размер файла в байтах.

    Returns:
        Метаданные добавленного изображения.
    """
    data = _load_metadata()
    new_id = get_next_id()
    record = {
        "id": new_id,
        "filename": filename,
        "path": path,
        "upload_date": datetime.now().isoformat(),
        "processed": False,
        "results": None,
        "mime_type": mime_type,
        "size_bytes": size_bytes,
    }
    data.append(record)
    _save_metadata(data)
    logger.info("Добавлено изображение: %s (id=%d)", filename, new_id)
    return ImageMetadata(**record)


def get_all() -> list[ImageMetadata]:
    """Возвращает все записи метаданных."""
    data = _load_metadata()
    return [ImageMetadata(**item) for item in data]


def get_by_id(image_id: int) -> Optional[ImageMetadata]:
    """Возвращает метаданные по ID."""
    data = _load_metadata()
    for item in data:
        if item["id"] == image_id:
            return ImageMetadata(**item)
    return None


def update_results(image_id: int, results: list[Prediction]) -> Optional[ImageMetadata]:
    """Обновляет результаты распознавания для изображения.

    Args:
        image_id: ID изображения.
        results: Список предсказаний.

    Returns:
        Обновлённые метаданные или None если не найдено.
    """
    data = _load_metadata()
    for item in data:
        if item["id"] == image_id:
            item["processed"] = True
            item["results"] = [r.model_dump() for r in results]
            _save_metadata(data)
            logger.info("Обновлены результаты для id=%d", image_id)
            return ImageMetadata(**item)
    return None


def delete_by_id(image_id: int) -> bool:
    """Удаляет запись по ID.

    Returns:
        True если запись была удалена, False если не найдена.
    """
    data = _load_metadata()
    new_data = [item for item in data if item["id"] != image_id]
    if len(new_data) == len(data):
        return False
    _save_metadata(new_data)
    logger.info("Удалена запись id=%d", image_id)
    return True


def reset_results(image_id: int) -> Optional[ImageMetadata]:
    """Сбрасывает результаты распознавания (для повторной обработки)."""
    data = _load_metadata()
    for item in data:
        if item["id"] == image_id:
            item["processed"] = False
            item["results"] = None
            _save_metadata(data)
            return ImageMetadata(**item)
    return None
