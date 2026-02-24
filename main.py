"""Cars Recognizer — FastAPI приложение для распознавания марок автомобилей.

Использует Hugging Face Inference API с моделью google/vit-base-patch16-224
для классификации изображений автомобилей (Stanford Cars, 196 классов).
"""

import logging
import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

from routers import inference, management, upload, visualization

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Cars Recognizer API",
    description="API для распознавания марок и моделей автомобилей по фотографиям",
    version="1.0.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение роутеров
app.include_router(upload.router)
app.include_router(inference.router)
app.include_router(management.router)
app.include_router(visualization.router)


@app.get("/")
async def root() -> dict:
    """Корневой эндпоинт с информацией об API."""
    return {
        "name": "Cars Recognizer API",
        "version": "1.0.0",
        "docs": "/docs",
        "description": "Загрузите изображение автомобиля и получите предсказание марки и модели.",
    }


# Создание директории для загрузок при старте
upload_dir = os.getenv("UPLOAD_DIR", "uploads")
os.makedirs(upload_dir, exist_ok=True)
