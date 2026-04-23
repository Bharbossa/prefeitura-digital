@echo off
echo.
echo ==========================================
echo   INICIANDO DEPLOY - COLONIA DIGITAL
echo ==========================================
echo.
echo 1. Limpando arquivos temporarios...
if exist backend\gen_hash.py del backend\gen_hash.py
if exist backend\gen_hash.py del backend\gen_hash.py
echo.
echo 2. Adicionando arquivos ao Git...
git add .
echo.
echo 3. Criando Commit...
git commit -m "Fix critico: remove channel_binding da DATABASE_URL e corrige trocas de senha"
echo.
echo 4. Enviando para o Render (Push)...
git push
echo.
echo ==========================================
echo   DEPLOY ENVIADO! 
echo.
echo   IMPORTANTE: O Render leva cerca de 2-3 
echo   minutos para atualizar o site.
echo.
echo   Aguarde a versao mudar para '2.0.0' em:
echo   https://prefeitura-digital.onrender.com/api/health
echo ==========================================
pause
