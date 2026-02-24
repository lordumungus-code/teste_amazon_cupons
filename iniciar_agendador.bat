@echo off
title Agendador Crawler Amazon
color 0A
echo ========================================
echo    INICIANDO AGENDADOR DO CRAWLER
echo ========================================
echo.

cd /d %~dp0

:: Verifica Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Python nao encontrado!
    pause
    exit /b 1
)

:: Verifica schedule
python -c "import schedule" >nul 2>&1
if errorlevel 1 (
    echo [AVISO] Instalando schedule...
    pip install schedule
)

echo [OK] Ambiente verificado
echo.

:: Inicia o agendador em uma nova janela
start "Agendador Crawler" /MIN cmd /c python agendador.py

echo [OK] Agendador iniciado em segundo plano!
echo.
echo Para ver os logs em tempo real:
echo   type %~dp0crawler_agendado.log
echo.
echo Para parar:
echo   taskkill /f /im python.exe
echo.
pause