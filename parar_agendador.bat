@echo off
echo ========================================
echo    PARANDO AGENDADOR DO CRAWLER
echo ========================================
echo.

taskkill /f /im pythonw.exe 2>nul

if errorlevel 1 (
    echo [AVISO] Nenhum processo pythonw.exe encontrado
) else (
    echo [OK] Agendador parado com sucesso
)

echo.
pause