"""Эндпоинты для управления загруженными файлами."""

import logging
import os

from fastapi import APIRouter, HTTPException

from models.schemas import ImageMetadata
from services import metadata_store

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/files", tags=["Management"])


@router.get("/", response_model=list[ImageMetadata])
async def list_files() -> list[ImageMetadata]:
    """Получение списка всех загруженных файлов с метаданными."""
    return metadata_store.get_all()


@router.get("/{image_id}", response_model=ImageMetadata)
async def get_file(image_id: int) -> ImageMetadata:
    """Получение метаданных конкретного файла по ID.

    Args:
        image_id: ID изображения.
    """
    image = metadata_store.get_by_id(image_id)
    if not image:
        raise HTTPException(status_code=404, detail="Изображение не найдено.")
    return image


@router.delete("/{image_id}")
async def delete_file(image_id: int) -> dict:
    """Удаление файла и его метаданных.

    Args:
        image_id: ID изображения.
    """
    image = metadata_store.get_by_id(image_id)
    if not image:
        raise HTTPException(status_code=404, detail="Изображение не найдено.")

    # Удаляем файл с диска
    if os.path.exists(image.path):
        os.remove(image.path)
        logger.info("Удалён файл: %s", image.path)

    # Удаляем метаданные
    metadata_store.delete_by_id(image_id)
    return {"message": f"Файл '{image.filename}' удалён."}


@router.post("/{image_id}/reprocess", response_model=ImageMetadata)
async def reprocess_file(image_id: int) -> ImageMetadata:
    """Сброс результатов для повторной обработки.

    Args:
        image_id: ID изображения.
    """
    result = metadata_store.reset_results(image_id)
    if not result:
        raise HTTPException(status_code=404, detail="Изображение не найдено.")
    logger.info("Сброшены результаты для id=%d", image_id)
    return result
