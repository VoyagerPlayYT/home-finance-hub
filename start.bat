@echo off
chcp 65001 > nul
title Home Finance Hub [Port 8020]
echo ========================================================
echo   HOME FINANCE & UTILITIES // BUDGET & METER HUB
echo ========================================================
echo [INFO] Проверка и установка зависимостей...
python -m pip install -r requirements.txt --quiet
echo [INFO] Запуск FastAPI веб-сервера на http://localhost:8020 ...
start http://localhost:8020
python -m uvicorn main:app --host 0.0.0.0 --port 8020
pause
