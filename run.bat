@echo off
chcp 65001 > nul
cls

echo ╔═══════════════════════════════════════════════════════════╗
echo ║                                                             ║
echo ║   🍄 Sistema Detector de Tracks Micológicos 🍄            ║
echo ║                                                             ║
echo ╚═══════════════════════════════════════════════════════════╝
echo.

REM Verificar Python
echo Verificando Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python no está instalado
    echo Instala Python 3.8 o superior desde https://www.python.org/
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo ✓ Python encontrado: %PYTHON_VERSION%
echo.

REM Crear entorno virtual si no existe
if not exist "venv" (
    echo 📦 Creando entorno virtual...
    python -m venv venv
    if errorlevel 1 (
        echo ❌ Error al crear entorno virtual
        pause
        exit /b 1
    )
)

REM Activar entorno virtual
echo Activando entorno virtual...
call venv\Scripts\activate.bat

REM Verificar requirements.txt
if not exist "requirements.txt" (
    echo ❌ No se encontró requirements.txt
    pause
    exit /b 1
)

REM Instalar/actualizar dependencias
echo 📦 Instalando dependencias...
python -m pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet

if errorlevel 1 (
    echo ❌ Error al instalar dependencias
    pause
    exit /b 1
)

echo ✓ Dependencias instaladas
echo.

REM Menú principal
echo ═══════════════════════════════════════════════════════════
echo   MENÚ PRINCIPAL
echo ═══════════════════════════════════════════════════════════
echo 1. Ejecutar flujo completo (Scraper + Analyzer + Detector)
echo 2. Solo Scraper de Wikiloc
echo 3. Solo Analizador
echo 4. Solo Detector de tracks micológicos
echo 5. Salir
echo ═══════════════════════════════════════════════════════════
set /p option="Selecciona una opción [1-5]: "

if "%option%"=="1" goto full_flow
if "%option%"=="2" goto scraper_only
if "%option%"=="3" goto analyzer_only
if "%option%"=="4" goto detector_only
if "%option%"=="5" goto exit_script
goto invalid_option

:full_flow
echo.
echo 🚀 Ejecutando flujo completo...
echo.

REM Paso 1: Scraper
echo ═══ PASO 1: Scraping de Wikiloc ═══
python wikiloc_scraper.py

if errorlevel 1 (
    echo ❌ Error en el scraper
    pause
    exit /b 1
)

echo.

REM Paso 2: Analyzer
echo ═══ PASO 2: Análisis de datos ═══

if not exist "wikiloc_cache.db" (
    echo ⚠️  No hay base de datos. Saltando análisis.
) else (
    echo 5 | python wikiloc_analyzer.py
)

echo.

REM Paso 3: Detector
echo ═══ PASO 3: Detección de tracks micológicos ═══

if exist "gpx_files" (
    dir /b gpx_files\*.gpx >nul 2>&1
    if not errorlevel 1 (
        python mushroom_detector.py gpx_files\
    ) else (
        echo ⚠️  No hay archivos GPX. Descarga GPX primero.
    )
) else (
    echo ⚠️  No hay carpeta gpx_files. Descarga GPX primero.
)

goto end_script

:scraper_only
echo.
echo 🕷️  Ejecutando Scraper de Wikiloc...
python wikiloc_scraper.py
goto end_script

:analyzer_only
echo.
echo 📊 Ejecutando Analizador...

if not exist "wikiloc_cache.db" (
    echo ❌ No se encontró wikiloc_cache.db
    echo Ejecuta primero el scraper para recolectar datos
    pause
    exit /b 1
)

python wikiloc_analyzer.py
goto end_script

:detector_only
echo.
echo 🔍 Ejecutando Detector de tracks micológicos...

if not exist "gpx_files" (
    echo ❌ No hay carpeta gpx_files
    echo Ejecuta primero el scraper y descarga los GPX
    pause
    exit /b 1
)

dir /b gpx_files\*.gpx >nul 2>&1
if errorlevel 1 (
    echo ❌ No hay archivos GPX en gpx_files\
    echo Ejecuta primero el scraper y descarga los GPX
    pause
    exit /b 1
)

python mushroom_detector.py gpx_files\
goto end_script

:invalid_option
echo ❌ Opción inválida
pause
exit /b 1

:exit_script
echo.
echo 👋 Saliendo...
call venv\Scripts\deactivate.bat 2>nul
exit /b 0

:end_script
echo.
echo ═══════════════════════════════════════════════════════════
echo ✅ Proceso completado!
echo ═══════════════════════════════════════════════════════════
echo.
echo 📁 Archivos generados:

if exist "wikiloc_cache.db" echo    ✓ wikiloc_cache.db (base de datos)
if exist "tracks_found.json" echo    ✓ tracks_found.json (tracks encontrados)
if exist "tracks_heatmap.html" echo    ✓ tracks_heatmap.html (mapa interactivo)

if exist "gpx_files" (
    for /f %%a in ('dir /b gpx_files\*.gpx 2^>nul ^| find /c /v ""') do set GPX_COUNT=%%a
    if defined GPX_COUNT echo    ✓ gpx_files\ (!GPX_COUNT! archivos GPX)
)

if exist "analysis_report.json" echo    ✓ analysis_report.json (reporte de análisis)

if exist "analysis_plots" (
    for /f %%a in ('dir /b analysis_plots\*.png 2^>nul ^| find /c /v ""') do set PLOT_COUNT=%%a
    if defined PLOT_COUNT echo    ✓ analysis_plots\ (!PLOT_COUNT! gráficos)
)

if exist "mushroom_analysis_results.json" echo    ✓ mushroom_analysis_results.json (detección micológica)
if exist "wikiloc_scraper.log" echo    ✓ wikiloc_scraper.log (log de operaciones)

echo.
echo 🎉 ¡Gracias por usar el Sistema Detector de Tracks Micológicos!
echo.

REM Desactivar entorno virtual
call venv\Scripts\deactivate.bat 2>nul

pause
