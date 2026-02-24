"""Эндпоинты для загрузки изображений."""

import logging
import os
import shutil

from fastapi import APIRouter, File, HTTPException, UploadFile

from models.schemas import ImageMetadata, UploadResponse
from services import image_processor, metadata_store

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/upload", tags=["Upload"])

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")


def _ensure_upload_dir() -> None:
    """Создаёт директорию для загрузок если не существует."""
    os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/", response_model=UploadResponse)
async def upload_single(file: UploadFile = File(...)) -> UploadResponse:
    """Загрузка одного изображения.

    Args:
        file: Загружаемый файл.

    Returns:
        Информация о загруженном файле.
    """
    _ensure_upload_dir()

    if not file.filename:
        raise HTTPException(status_code=400, detail="Имя файла отсутствует.")

    if not image_processor.validate_file_extension(file.filename):
        raise HTTPException(
            status_code=400,
            detail="Недопустимый формат файла. Допустимы: jpg, jpeg, png.",
        )

    data = await file.read()

    if not image_processor.validate_file_size(data):
        raise HTTPException(
            status_code=400,
            detail=f"Файл слишком большой. Максимум: {image_processor.MAX_FILE_SIZE_MB} МБ.",
        )

    if not image_processor.validate_image_integrity(data):
        raise HTTPException(
            status_code=400,
            detail="Файл повреждён или не является изображением.",
        )

    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as f:
        f.write(data)

    mime_type = image_processor.get_mime_type(file.filename)
    metadata = metadata_store.add_image(
        filename=file.filename,
        path=file_path,
        mime_type=mime_type,
        size_bytes=len(data),
    )

    logger.info("Загружен файл: %s (%d байт)", file.filename, len(data))
    return UploadResponse(message="Файл успешно загружен.", files=[metadata])


@router.post("/batch", response_model=UploadResponse)
async def upload_batch(files: list[UploadFile] = File(...)) -> UploadResponse:
    """Загрузка нескольких изображений.

    Args:
        files: Список загружаемых файлов.

    Returns:
        Информация о загруженных файлах.
    """
    _ensure_upload_dir()

    uploaded: list[ImageMetadata] = []
    errors: list[str] = []

    for file in files:
        if not file.filename:
            errors.append("Пропущен файл без имени.")
            continue

        if not image_processor.validate_file_extension(file.filename):
            errors.append(f"{file.filename}: недопустимый формат.")
            continue

        data = await file.read()

        if not image_processor.validate_file_size(data):
            errors.append(f"{file.filename}: превышен лимит размера.")
            continue

        if not image_processor.validate_image_integrity(data):
            errors.append(f"{file.filename}: файл повреждён.")
            continue

        file_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(file_path, "wb") as f:
            f.write(data)

        mime_type = image_processor.get_mime_type(file.filename)
        metadata = metadata_store.add_image(
            filename=file.filename,
            path=file_path,
            mime_type=mime_type,
            size_bytes=len(data),
        )
        uploaded.append(metadata)

    if not uploaded and errors:
        raise HTTPException(status_code=400, detail="; ".join(errors))

    msg = f"Загружено файлов: {len(uploaded)}."
    if errors:
        msg += f" Ошибки: {'; '.join(errors)}"

    logger.info("Пакетная загрузка: %d файлов, %d ошибок", len(uploaded), len(errors))
    return UploadResponse(message=msg, files=uploaded)
