"""Эндпоинты для визуализации и экспорта результатов."""

import csv
import io
import logging
from collections import Counter

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse

from models.schemas import StatsResponse
from services import metadata_store

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/visualization", tags=["Visualization"])


@router.get("/stats", response_model=StatsResponse)
async def get_stats() -> StatsResponse:
    """Получение статистики по загруженным файлам."""
    all_files = metadata_store.get_all()
    total = len(all_files)
    processed = sum(1 for f in all_files if f.processed)
    unprocessed = total - processed

    # Подсчёт популярных марок (по top-1 предсказанию)
    brand_counter: Counter = Counter()
    for f in all_files:
        if f.results and len(f.results) > 0:
            brand_counter[f.results[0].label] += 1

    top_brands = [
        {"label": label, "count": count}
        for label, count in brand_counter.most_common(10)
    ]

    return StatsResponse(
        total_files=total,
        processed_files=processed,
        unprocessed_files=unprocessed,
        top_brands=top_brands,
    )


@router.get("/export/csv")
async def export_csv() -> StreamingResponse:
    """Экспорт результатов в CSV-файл."""
    all_files = metadata_store.get_all()
    processed_files = [f for f in all_files if f.processed and f.results]

    if not processed_files:
        raise HTTPException(
            status_code=404,
            detail="Нет обработанных файлов для экспорта.",
        )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["filename", "top_prediction", "confidence", "all_predictions"])

    for f in processed_files:
        top = f.results[0]
        all_preds = ", ".join(
            f"{r.label} ({r.confidence})" for r in f.results
        )
        writer.writerow([f.filename, top.label, top.confidence, all_preds])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=results.csv"},
    )


@router.get("/report", response_class=HTMLResponse)
async def visualization_page() -> HTMLResponse:
    """HTML-страница с визуализацией результатов."""
    all_files = metadata_store.get_all()
    total = len(all_files)
    processed = sum(1 for f in all_files if f.processed)

    # Формируем строки таблицы
    rows = ""
    for f in all_files:
        status = "Обработано" if f.processed else "Не обработано"
        if f.results and len(f.results) > 0:
            top_pred = f"{f.results[0].label} ({f.results[0].confidence})"
        else:
            top_pred = "—"
        rows += f"""
        <tr>
            <td>{f.id}</td>
            <td>{f.filename}</td>
            <td>{status}</td>
            <td>{top_pred}</td>
            <td>{f.size_bytes} Б</td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cars Recognizer — Отчёт</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }}
        h1 {{ color: #333; }}
        .stats {{ display: flex; gap: 20px; margin: 20px 0; }}
        .stat-card {{ background: white; padding: 20px; border-radius: 8px;
                      box-shadow: 0 2px 4px rgba(0,0,0,0.1); min-width: 150px; }}
        .stat-card h3 {{ margin: 0 0 8px; color: #666; font-size: 14px; }}
        .stat-card .value {{ font-size: 32px; font-weight: bold; color: #2196F3; }}
        table {{ width: 100%; border-collapse: collapse; background: white;
                 border-radius: 8px; overflow: hidden;
                 box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        th {{ background: #2196F3; color: white; padding: 12px; text-align: left; }}
        td {{ padding: 10px 12px; border-bottom: 1px solid #eee; }}
        tr:hover {{ background: #f0f7ff; }}
    </style>
</head>
<body>
    <h1>Cars Recognizer — Отчёт</h1>
    <div class="stats">
        <div class="stat-card">
            <h3>Всего файлов</h3>
            <div class="value">{total}</div>
        </div>
        <div class="stat-card">
            <h3>Обработано</h3>
            <div class="value">{processed}</div>
        </div>
        <div class="stat-card">
            <h3>Не обработано</h3>
            <div class="value">{total - processed}</div>
        </div>
    </div>
    <table>
        <thead>
            <tr>
                <th>ID</th>
                <th>Файл</th>
                <th>Статус</th>
                <th>Предсказание</th>
                <th>Размер</th>
            </tr>
        </thead>
        <tbody>
            {rows if rows else '<tr><td colspan="5" style="text-align:center;padding:20px;">Нет загруженных файлов</td></tr>'}
        </tbody>
    </table>
</body>
</html>"""
    return HTMLResponse(content=html)
