@echo off
echo ========================================================
echo  Enterprise Python Cloud Studio - Starting Local Server
echo ========================================================
echo.
echo Application will be available at: http://localhost:8000/
echo Swagger API docs available at:    http://localhost:8000/docs
echo.
echo Press Ctrl+C in this terminal window to stop the server.
echo.
python -m uvicorn services.api.main:app --host 127.0.0.1 --port 8000 --reload
pause
