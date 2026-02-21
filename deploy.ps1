# deploy_simples.ps1 - Versão sem emojis
Write-Host "Iniciando deploy..." -ForegroundColor Green

# Inicializa git
Write-Host "Inicializando git..." -ForegroundColor Yellow
git init

# Adiciona todos os arquivos
Write-Host "Adicionando arquivos..." -ForegroundColor Yellow
git add .

# Primeiro commit
Write-Host "Criando commit..." -ForegroundColor Yellow
git commit -m "Deploy inicial"

# Cria branch main
Write-Host "Criando branch main..." -ForegroundColor Yellow
git branch -M main

# Remove remote antigo se existir
Write-Host "Configurando remote..." -ForegroundColor Yellow
git remote remove origin 2>$null

# Adiciona remote NOVO
git remote add origin https://github.com/lordumungus-code/teste_amazon_cupons.git

# Tenta push
Write-Host "Enviando para o GitHub..." -ForegroundColor Yellow
git push -u origin main

# Mensagem de sucesso
Write-Host "Pronto! Verifique em: https://github.com/lordumungus-code/teste_amazon_cupons" -ForegroundColor Green

# Pausa
Read-Host "Pressione Enter para sair"