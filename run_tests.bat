@echo off
echo ===================================================
echo  Enterprise Python Cloud Studio - Automated Tests
echo ===================================================
echo Running 18 automated acceptance tests...
echo.
python -m pytest tests/integration/ -v
echo.
pause
