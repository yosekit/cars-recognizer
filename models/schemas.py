"""Pydantic-модели для запросов и ответов API."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class Prediction(BaseModel):
    """Одно предсказание модели."""
    label: str
    confidence: float


class ImageMetadata(BaseModel):
    """Метаданные загруженного изображения."""
    id: int
    filename: str
    path: str
    upload_date: datetime
    processed: bool = False
    results: Optional[list[Prediction]] = None
    mime_type: str
    size_bytes: int


class UploadResponse(BaseModel):
    """Ответ на загрузку файла."""
    message: str
    files: list[ImageMetadata]


class InferenceResponse(BaseModel):
    """Ответ на запрос распознавания."""
    id: int
    filename: str
    predictions: list[Prediction]


class StatsResponse(BaseModel):
    """Статистика по загруженным файлам."""
    total_files: int
    processed_files: int
    unprocessed_files: int
    top_brands: list[dict]


class ErrorResponse(BaseModel):
    """Ответ с ошибкой."""
    detail: str
