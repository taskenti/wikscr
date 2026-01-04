#!/bin/bash

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║                                                             ║"
echo "║   🍄 Sistema Detector de Tracks Micológicos 🍄            ║"
echo "║                                                             ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Verificar Python
echo -e "${BLUE}Verificando Python...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 no está instalado${NC}"
    echo "Instala Python 3.8 o superior desde https://www.python.org/"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
echo -e "${GREEN}✓ Python encontrado: ${PYTHON_VERSION}${NC}"
echo ""

# Crear entorno virtual si no existe
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}📦 Creando entorno virtual...${NC}"
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ Error al crear entorno virtual${NC}"
        exit 1
    fi
fi

# Activar entorno virtual
echo -e "${BLUE}Activando entorno virtual...${NC}"
source venv/bin/activate

# Verificar si requirements.txt existe
if [ ! -f "requirements.txt" ]; then
    echo -e "${RED}❌ No se encontró requirements.txt${NC}"
    exit 1
fi

# Instalar/actualizar dependencias
echo -e "${YELLOW}📦 Instalando dependencias...${NC}"
pip install -q --upgrade pip
pip install -q -r requirements.txt

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Error al instalar dependencias${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Dependencias instaladas${NC}"
echo ""

# Menú principal
echo "═══════════════════════════════════════════════════════════"
echo "  MENÚ PRINCIPAL"
echo "═══════════════════════════════════════════════════════════"
echo "1. Ejecutar flujo completo (Scraper + Analyzer + Detector)"
echo "2. Solo Scraper de Wikiloc"
echo "3. Solo Analizador"
echo "4. Solo Detector de tracks micológicos"
echo "5. Salir"
echo "═══════════════════════════════════════════════════════════"
read -p "Selecciona una opción [1-5]: " option

case $option in
    1)
        echo ""
        echo "🚀 Ejecutando flujo completo..."
        echo ""
        
        # Paso 1: Scraper
        echo -e "${BLUE}═══ PASO 1: Scraping de Wikiloc ═══${NC}"
        python3 wikiloc_scraper.py
        
        if [ $? -ne 0 ]; then
            echo -e "${RED}❌ Error en el scraper${NC}"
            exit 1
        fi
        
        echo ""
        
        # Paso 2: Analyzer
        echo -e "${BLUE}═══ PASO 2: Análisis de datos ═══${NC}"
        
        # Verificar si hay datos para analizar
        if [ ! -f "wikiloc_cache.db" ]; then
            echo -e "${YELLOW}⚠️  No hay base de datos. Saltando análisis.${NC}"
        else
            python3 wikiloc_analyzer.py <<EOF
5
EOF
        fi
        
        echo ""
        
        # Paso 3: Detector
        echo -e "${BLUE}═══ PASO 3: Detección de tracks micológicos ═══${NC}"
        
        if [ -d "gpx_files" ] && [ "$(ls -A gpx_files 2>/dev/null)" ]; then
            python3 mushroom_detector.py gpx_files/
        else
            echo -e "${YELLOW}⚠️  No hay archivos GPX. Descarga GPX primero.${NC}"
        fi
        ;;
        
    2)
        echo ""
        echo "🕷️  Ejecutando Scraper de Wikiloc..."
        python3 wikiloc_scraper.py
        ;;
        
    3)
        echo ""
        echo "📊 Ejecutando Analizador..."
        
        if [ ! -f "wikiloc_cache.db" ]; then
            echo -e "${RED}❌ No se encontró wikiloc_cache.db${NC}"
            echo "Ejecuta primero el scraper para recolectar datos"
            exit 1
        fi
        
        python3 wikiloc_analyzer.py
        ;;
        
    4)
        echo ""
        echo "🔍 Ejecutando Detector de tracks micológicos..."
        
        if [ ! -d "gpx_files" ] || [ ! "$(ls -A gpx_files 2>/dev/null)" ]; then
            echo -e "${RED}❌ No hay archivos GPX en gpx_files/${NC}"
            echo "Ejecuta primero el scraper y descarga los GPX"
            exit 1
        fi
        
        python3 mushroom_detector.py gpx_files/
        ;;
        
    5)
        echo ""
        echo "👋 Saliendo..."
        deactivate 2>/dev/null
        exit 0
        ;;
        
    *)
        echo -e "${RED}❌ Opción inválida${NC}"
        exit 1
        ;;
esac

echo ""
echo "═══════════════════════════════════════════════════════════"
echo -e "${GREEN}✅ Proceso completado!${NC}"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "📁 Archivos generados:"

if [ -f "wikiloc_cache.db" ]; then
    echo "   ✓ wikiloc_cache.db (base de datos)"
fi

if [ -f "tracks_found.json" ]; then
    echo "   ✓ tracks_found.json (tracks encontrados)"
fi

if [ -f "tracks_heatmap.html" ]; then
    echo "   ✓ tracks_heatmap.html (mapa interactivo)"
fi

if [ -d "gpx_files" ] && [ "$(ls -A gpx_files 2>/dev/null)" ]; then
    GPX_COUNT=$(ls -1 gpx_files/*.gpx 2>/dev/null | wc -l)
    echo "   ✓ gpx_files/ (${GPX_COUNT} archivos GPX)"
fi

if [ -f "analysis_report.json" ]; then
    echo "   ✓ analysis_report.json (reporte de análisis)"
fi

if [ -d "analysis_plots" ] && [ "$(ls -A analysis_plots 2>/dev/null)" ]; then
    PLOT_COUNT=$(ls -1 analysis_plots/*.png 2>/dev/null | wc -l)
    echo "   ✓ analysis_plots/ (${PLOT_COUNT} gráficos)"
fi

if [ -f "mushroom_analysis_results.json" ]; then
    echo "   ✓ mushroom_analysis_results.json (detección micológica)"
fi

if [ -f "wikiloc_scraper.log" ]; then
    echo "   ✓ wikiloc_scraper.log (log de operaciones)"
fi

echo ""
echo "🎉 ¡Gracias por usar el Sistema Detector de Tracks Micológicos!"
echo ""

# Desactivar entorno virtual
deactivate 2>/dev/null
