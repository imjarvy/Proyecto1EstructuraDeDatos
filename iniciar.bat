@echo off
title SkyBalance AVL — Iniciador
cd /d "%~dp0"

echo.
echo  ==========================================
echo   SkyBalance AVL - Sistema de Gestion Aerea
echo  ==========================================
echo.

REM Verificar que Python esta disponible
py --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python no encontrado. Asegurate de tener Python instalado y en el PATH.
    pause
    exit /b 1
)

REM Instalar dependencias si no estan instaladas
echo  [1/3] Verificando dependencias...
py -m pip install flask flask-cors --quiet
if errorlevel 1 (
    echo  [AVISO] No se pudieron instalar las dependencias automaticamente.
    echo          Ejecuta manualmente: pip install flask flask-cors
)

echo  [2/3] Iniciando servidor Flask en http://localhost:5000 ...
echo.

REM Arrancar Flask en segundo plano y abrir navegador
start "SkyBalance AVL - Servidor" cmd /k "cd /d ""%~dp0"" && py app.py"

REM Esperar 2 segundos a que Flask levante
timeout /t 2 /nobreak >nul

echo  [3/3] Abriendo navegador...
start "" http://localhost:5000

echo.
echo  Servidor corriendo en http://localhost:5000
echo  Cierra la ventana "SkyBalance AVL - Servidor" para detener la aplicacion.
echo.
pause