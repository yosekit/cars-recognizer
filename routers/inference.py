"""Эндпоинты для распознавания изображений."""

import logging

from fastapi import APIRouter, HTTPException

from models.schemas import InferenceResponse
from services import hf_client, metadata_store

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/inference", tags=["Inference"])


@router.post("/{image_id}", response_model=InferenceResponse)
async def recognize_single(image_id: int) -> InferenceResponse:
    """Распознавание одного изображения по ID.

    Args:
        image_id: ID изображения в хранилище.

    Returns:
        Результат распознавания с top-3 предсказаниями.
    """
    image = metadata_store.get_by_id(image_id)
    if not image:
        raise HTTPException(status_code=404, detail="Изображение не найдено.")

    try:
        predictions = await hf_client.classify_image(image.path)
    except RuntimeError as e:
        logger.error("Ошибка распознавания id=%d: %s", image_id, str(e))
        raise HTTPException(status_code=502, detail=str(e))

    metadata_store.update_results(image_id, predictions)
    logger.info("Распознано изображение id=%d: %s", image_id, predictions[0].label)

    return InferenceResponse(
        id=image.id,
        filename=image.filename,
        predictions=predictions,
    )


@router.post("/batch", response_model=list[InferenceResponse])
async def recognize_batch(image_ids: list[int]) -> list[InferenceResponse]:
    """Пакетное распознавание нескольких изображений.

    Args:
        image_ids: Список ID изображений.

    Returns:
        Список результатов распознавания.
    """
    results: list[InferenceResponse] = []

    for image_id in image_ids:
        image = metadata_store.get_by_id(image_id)
        if not image:
            logger.warning("Изображение id=%d не найдено, пропущено", image_id)
            continue

        try:
            predictions = await hf_client.classify_image(image.path)
        except RuntimeError as e:
            logger.error("Ошибка распознавания id=%d: %s", image_id, str(e))
            continue

        metadata_store.update_results(image_id, predictions)

        results.append(InferenceResponse(
            id=image.id,
            filename=image.filename,
            predictions=predictions,
        ))

    if not results:
        raise HTTPException(
            status_code=400,
            detail="Ни одно изображение не было успешно обработано.",
        )

    logger.info("Пакетное распознавание: обработано %d из %d", len(results), len(image_ids))
    return results
