@echo off
title FOOD CALENDAR
setlocal ENABLEDELAYEDEXPANSION

echo =====================================
echo   FOOD CALENDAR
echo =====================================
echo.

:: --------------------------------------------------
:: 1. Ir al directorio raiz del proyecto
:: --------------------------------------------------
cd /d "%~dp0"

:: --------------------------------------------------
:: 2. Comprobar Python
:: --------------------------------------------------
where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python no esta instalado o no esta en el PATH.
    echo Instala Python 3.12.1 desde:
    echo https://www.python.org/downloads/release/python-3121/
    pause
    exit /b 1
)

:: --------------------------------------------------
:: 3. Crear entorno virtual si no existe
:: --------------------------------------------------
if not exist ".venv" (
    echo [INFO] Creando entorno virtual...
    python -m venv .venv
    if errorlevel 1 (
        echo [ERROR] No se pudo crear el entorno virtual.
        pause
        exit /b 1
    )
) else (
    echo [INFO] Entorno virtual detectado.
)

:: --------------------------------------------------
:: 4. Activar entorno virtual
:: --------------------------------------------------
call ".venv\Scripts\activate.bat"

:: --------------------------------------------------
:: 5. Actualizar pip (silencioso pero seguro)
:: --------------------------------------------------
python -m pip install --upgrade pip >nul

:: --------------------------------------------------
:: 6. Instalar dependencias si es necesario
:: --------------------------------------------------
if exist "requirements.txt" (
    echo [INFO] Instalando dependencias...
    pip install -r requirements.txt
) else (
    echo [ERROR] No se encontro requirements.txt
    pause
    exit /b 1
)

:: --------------------------------------------------
:: 7. Definir PYTHONPATH (solo para esta sesion)
:: --------------------------------------------------
set PYTHONPATH=%CD%

:: --------------------------------------------------
:: 8. Lanzar la aplicacion
:: --------------------------------------------------
echo.
echo [INFO] Lanzando aplicacion...
echo [INFO] Cierra esta ventana para detenerla
echo.

streamlit run app.py

pause
