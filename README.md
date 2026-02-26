# Cars Recognizer API

REST API для распознавания марок и моделей автомобилей по фотографиям. Использует модель `google/vit-base-patch16-224` через Hugging Face Inference API (Stanford Cars dataset, 196 классов).

## Требования

- Python 3.9+
- Аккаунт на [Hugging Face](https://huggingface.co/) и API-токен

## Установка и запуск

1. **Клонировать репозиторий и перейти в директорию:**

```bash
git clone <url>
cd cars-recognizer
```

2. **Создать виртуальное окружение и активировать его:**

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/macOS
source venv/bin/activate
```

3. **Установить зависимости:**

```bash
pip install -r requirements.txt
```

4. **Настроить переменные окружения:**

```bash
cp .env.example .env
```

Открыть `.env` и вставить свой Hugging Face токен:

```
HF_API_TOKEN=hf_your_token_here
```

Токен можно получить на https://huggingface.co/settings/tokens

5. **Запустить сервер:**

```bash
uvicorn main:app --reload
```

Сервер будет доступен по адресу http://localhost:8000

## Документация API

После запуска сервера:

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

## Эндпоинты

### Загрузка изображений

| Метод | URL | Описание |
|-------|-----|----------|
| POST | `/upload/` | Загрузка одного изображения |
| POST | `/upload/batch` | Загрузка нескольких изображений |

Допустимые форматы: JPG, JPEG, PNG. Максимальный размер: 10 МБ.

### Распознавание

| Метод | URL | Описание |
|-------|-----|----------|
| POST | `/inference/{image_id}` | Распознать одно изображение |
| POST | `/inference/batch` | Распознать несколько изображений (передать список ID в теле запроса) |

### Управление файлами

| Метод | URL | Описание |
|-------|-----|----------|
| GET | `/files/` | Список всех файлов |
| GET | `/files/{image_id}` | Метаданные файла по ID |
| DELETE | `/files/{image_id}` | Удалить файл |
| POST | `/files/{image_id}/reprocess` | Сбросить результаты для повторной обработки |

### Визуализация

| Метод | URL | Описание |
|-------|-----|----------|
| GET | `/visualization/stats` | Статистика по файлам и предсказаниям |
| GET | `/visualization/export/csv` | Экспорт результатов в CSV |
| GET | `/visualization/report` | HTML-страница с отчётом |

## Пример использования

```bash
# Загрузить изображение
curl -X POST http://localhost:8000/upload/ -F "file=@car.jpg"

# Распознать (image_id из ответа загрузки)
curl -X POST http://localhost:8000/inference/1

# Посмотреть результаты
curl http://localhost:8000/files/1

# Экспорт в CSV
curl http://localhost:8000/visualization/export/csv -o results.csv
```

## Технологии

- **FastAPI** — веб-фреймворк
- **Pydantic** — валидация данных
- **aiohttp** — асинхронный HTTP-клиент
- **Hugging Face Inference API** — классификация изображений
