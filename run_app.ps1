Write-Host "========================================================" -ForegroundColor Cyan
Write-Host " Enterprise Python Cloud Studio - Starting Local Server " -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Web Dashboard URL:  " -NoNewline
Write-Host "http://localhost:8765/" -ForegroundColor Green
Write-Host "Swagger API Docs:   " -NoNewline
Write-Host "http://localhost:8765/docs" -ForegroundColor Yellow
Write-Host ""
Write-Host "Press Ctrl+C to stop the server." -ForegroundColor DarkGray
Write-Host ""

python -m uvicorn services.api.main:app --host 127.0.0.1 --port 8765 --reload

