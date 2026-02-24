"""Сервис валидации и предобработки изображений."""

import io
import logging
import os

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png"}
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "10"))
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024


def validate_file_extension(filename: str) -> bool:
    """Проверяет допустимость расширения файла.

    Args:
        filename: Имя загружаемого файла.

    Returns:
        True если расширение допустимо.
    """
    ext = os.path.splitext(filename)[1].lower()
    return ext in ALLOWED_EXTENSIONS


def validate_mime_type(content_type: str) -> bool:
    """Проверяет допустимость MIME-типа.

    Args:
        content_type: MIME-тип файла.

    Returns:
        True если тип допустим.
    """
    return content_type in ALLOWED_MIME_TYPES


def validate_file_size(data: bytes) -> bool:
    """Проверяет, что размер файла не превышает лимит.

    Args:
        data: Содержимое файла в байтах.

    Returns:
        True если размер в пределах лимита.
    """
    return len(data) <= MAX_FILE_SIZE_BYTES


def validate_image_integrity(data: bytes) -> bool:
    """Проверяет целостность изображения по магическим байтам.

    Args:
        data: Содержимое файла в байтах.

    Returns:
        True если файл является валидным изображением.
    """
    if len(data) < 4:
        return False
    # JPEG: FF D8 FF
    if data[:3] == b'\xff\xd8\xff':
        return True
    # PNG: 89 50 4E 47
    if data[:4] == b'\x89PNG':
        return True
    return False


def get_mime_type(filename: str) -> str:
    """Определяет MIME-тип по расширению файла.

    Args:
        filename: Имя файла.

    Returns:
        MIME-тип.
    """
    ext = os.path.splitext(filename)[1].lower()
    if ext in (".jpg", ".jpeg"):
        return "image/jpeg"
    if ext == ".png":
        return "image/png"
    return "application/octet-stream"
