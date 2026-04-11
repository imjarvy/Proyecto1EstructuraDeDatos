@echo off
chcp 65001 >nul
title SkyBalance AVL — Iniciador
cd /d "%~dp0"

echo.
echo  ==========================================
echo   SkyBalance AVL - Sistema de Gestion Aerea
echo  ==========================================
echo.

REM Verificar que Python está disponible
py --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python no encontrado. Asegurate de tener Python instalado y en el PATH.
    pause
    exit /b 1
)

REM Verificar que las dependencias están instaladas
echo  [1/3] Verificando dependencias...
py -c "import flask, flask_cors" >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Dependencias no encontradas.
    echo.
    echo  Por favor, ejecuta el siguiente comando en la terminal:
    echo  pip install -r requirements.txt
    echo.
    echo  Lee los manuales para instrucciones detalladas.
    echo.
    pause
    exit /b 1
)
echo  ✓ Dependencias verificadas

echo.
echo  [2/3] Iniciando servidor Flask en http://localhost:5000 ...
echo.

REM Arrancar Flask en un nuevo CMD
start "SkyBalance AVL - Servidor" cmd /k "chcp 65001 >nul && cd /d ""%~dp0"" && py app.py"

REM Esperar 3 segundos a que Flask levante completamente
timeout /t 3 /nobreak >nul

echo  ✓ Servidor corriendo en http://localhost:5000

echo.
echo  [3/3] Abriendo navegador...

REM Abrir en Chrome/Edge si está disponible, sino en navegador predeterminado
where chrome >nul 2>&1 && (
    start chrome http://localhost:5000
) || where msedge >nul 2>&1 && (
    start msedge http://localhost:5000
) || (
    start http://localhost:5000
)

echo.
echo  ✓ Si el navegador no abre, ve a http://localhost:5000 manualmente
echo  ✓ Cierra la ventana "SkyBalance AVL - Servidor" para detener
echo.
pause
