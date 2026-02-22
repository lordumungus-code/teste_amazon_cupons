@echo off
echo 🚀 ATUALIZADOR DO SITE PROMOÇÕES AMAZON
echo ========================================
echo.

echo 1. Executando crawler local...
python crawler.py
if %errorlevel% neq 0 (
    echo ❌ Erro ao executar crawler!
    pause
    exit /b
)

echo.
echo 2. Verificando banco de dados...
sqlite3 produtos.db "SELECT COUNT(*) || ' produtos encontrados' FROM produtos;"

echo.
echo 3. Enviando para GitHub...
git add produtos.db crawler.py app.py templates/index.html
git commit -m "Atualiza banco de dados %date%"
git push origin main

echo.
echo 4. Pronto! Acesse:
echo    https://web-production-a202d.up.railway.app
echo    https://web-production-a202d.up.railway.app/debug

echo.
echo ✅ SITE ATUALIZADO COM SUCESSO!
pause