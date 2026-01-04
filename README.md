# 🍄 Sistema Detector de Tracks Micológicos

Sistema completo de web scraping, análisis y detección de rutas micológicas en Wikiloc.

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## 📋 Características

- **Scraper Multi-Estrategia**: 5 métodos diferentes para extraer tracks de Wikiloc
- **Detector Heurístico**: Análisis avanzado de patrones de movimiento
- **Analizador con IA**: Clustering automático y recomendaciones de zonas
- **Visualizaciones**: Mapas de calor, gráficos y dashboards interactivos
- **Base de Datos**: Sistema de caché con SQLite
- **Multi-plataforma**: Compatible con Windows, Linux y macOS

## 🚀 Instalación Rápida

### Requisitos previos
- Python 3.8 o superior
- pip (gestor de paquetes de Python)

### Pasos de instalación
```bash
# 1. Clonar o descargar el repositorio
cd mushroom-tracker-system

# 2. (Opcional pero recomendado) Crear entorno virtual
python -m venv venv

# En Linux/Mac:
source venv/bin/activate

# En Windows:
venv\Scripts\activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. (Opcional) Instalar ChromeDriver para Selenium
# Ubuntu/Debian:
sudo apt-get install chromium-chromedriver

# macOS:
brew install chromedriver

# Windows:
# Descargar de https://chromedriver.chromium.org/
# Y añadir al PATH del sistema
```

## 📖 Uso

### Modo Interactivo (Recomendado)
```bash
# Ejecutar el scraper
python wikiloc_scraper.py
```

El script te guiará paso a paso:
1. Seleccionar zona(s) caliente(s)
2. Elegir estrategias de scraping
3. Ver resultados en tiempo real

### Modo Automatizado

**Linux/Mac:**
```bash
chmod +x run.sh
./run.sh
```

**Windows:**
```cmd
run.bat
```

### Análisis de Resultados
```bash
# Analizar tracks scrapeados
python wikiloc_analyzer.py

# Detectar patrones micológicos en GPX
python mushroom_detector.py gpx_files/
```

## 🗺️ Zonas Calientes Predefinidas

El sistema incluye 7 zonas top de España:

1. **Picos de Europa** (León) - Radio: 15km
2. **Sierra de Guadarrama** (Madrid) - Radio: 20km
3. **Pirineos Catalanes** (Lleida) - Radio: 25km
4. **Montseny** (Barcelona) - Radio: 15km
5. **Sierra de Gredos** (Ávila) - Radio: 20km
6. **Selva de Irati** (Navarra) - Radio: 15km
7. **Comarca de la Vera** (Cáceres) - Radio: 15km

## ⚙️ Configuración

Edita `config.json` para personalizar:

### Añadir nuevas zonas calientes
```json
{
  "hot_zones": [
    {
      "name": "Mi Zona",
      "lat": 40.4168,
      "lon": -3.7038,
      "radius": 10,
      "province": "Madrid",
      "keywords": ["setas", "bosque", "monte"]
    }
  ]
}
```

### Ajustar parámetros del detector
```json
{
  "detector": {
    "max_mushroom_speed": 3.0,
    "min_duration_hours": 2,
    "weights": {
      "tortuosity": 0.20,
      "avg_speed": 0.15
    }
  }
}
```

### Configurar scraping
```json
{
  "scraping": {
    "use_selenium": false,
    "min_delay": 2,
    "max_delay": 5,
    "strategies": ["coordinates", "keywords", "api"]
  }
}
```

## 📊 Salidas Generadas

Después de ejecutar el sistema:

- `wikiloc_cache.db` - Base de datos SQLite con todos los tracks
- `tracks_found.json` - Lista de tracks encontrados en formato JSON
- `tracks_heatmap.html` - Mapa interactivo de zonas calientes
- `gpx_files/` - Carpeta con archivos GPX descargados
- `analysis_report.json` - Análisis completo con estadísticas
- `analysis_plots/` - Gráficos y visualizaciones PNG
- `mushroom_analysis_results.json` - Resultados de detección micológica
- `wikiloc_scraper.log` - Log de todas las operaciones

## 🔍 Estrategias de Scraping

El sistema utiliza 5 estrategias diferentes:

1. **Coordenadas**: Búsqueda directa por ubicación geográfica
2. **Keywords**: Búsqueda combinando palabras clave con ubicación
3. **API**: Intenta usar endpoints internos no documentados de Wikiloc
4. **Selenium**: Para contenido JavaScript dinámico (requiere ChromeDriver)
5. **Usuarios**: Scrapea perfiles de usuarios activos en la zona

## 📈 Métricas del Detector

El detector analiza múltiples factores:

- **Tortuosidad**: Índice de sinuosidad del recorrido
- **Velocidad**: Velocidad media y variabilidad
- **Paradas**: Número y duración de paradas
- **Cambios de dirección**: Frecuencia de cambios de rumbo
- **Temporada**: Si fue realizado en época de setas
- **Horario**: Si fue durante el día
- **Duración**: Si tiene duración apropiada (2-6h)
- **Altitud**: Variabilidad del terreno
- **Densidad espacial**: Puntos GPS por kilómetro

## 🎯 Ejemplos de Uso

### Ejemplo 1: Analizar zona específica
```bash
python wikiloc_scraper.py
# Selecciona opción 2 (Sierra de Guadarrama)
# Usa estrategias: coordinates,keywords
```

### Ejemplo 2: Buscar en todas las zonas
```bash
python wikiloc_scraper.py
# Escribe "todas" cuando te pregunte
```

### Ejemplo 3: Zona personalizada
```bash
python wikiloc_scraper.py
# Selecciona "personalizada"
# Introduce: Lat: 40.5, Lon: -3.8, Radio: 15
```

### Ejemplo 4: Analizar GPX local
```bash
# Si ya tienes archivos GPX descargados
python mushroom_detector.py mi_track.gpx

# O analizar una carpeta completa
python mushroom_detector.py mis_gpx/
```

## ⚠️ Avisos Legales

- ✅ Uso educacional y personal únicamente
- ✅ Respeta los términos de servicio de Wikiloc
- ✅ No hagas scraping masivo que sobrecargue servidores
- ✅ Usa delays apropiados (2-5 segundos entre requests)
- ✅ Respeta el archivo robots.txt
- ⚠️ Si Wikiloc ofrece una API oficial, úsala en su lugar

## 🐛 Solución de Problemas

### Error: ChromeDriver no encontrado
```bash
# Verifica la instalación
chromedriver --version

# En Linux, añade al PATH
export PATH=$PATH:/usr/lib/chromium-browser/

# En Windows, añade la carpeta de ChromeDriver al PATH del sistema
```

### Error: No se encuentran tracks

- Prueba con diferentes zonas
- Usa múltiples estrategias: `coordinates,keywords,api`
- Verifica tu conexión a Internet
- Aumenta el radio de búsqueda en config.json

### Error: Timeout en requests

- Aumenta los delays en `config.json`: `"min_delay": 5, "max_delay": 10`
- Verifica tu conexión a Internet
- Prueba en otro momento (menor carga del servidor)

### Error: Módulo no encontrado
```bash
# Reinstala las dependencias
pip install -r requirements.txt --upgrade

# O instala el módulo específico
pip install nombre_modulo
```

### Base de datos corrupta
```bash
# Elimina y vuelve a crear
rm wikiloc_cache.db
python wikiloc_scraper.py
```

## 🔧 Desarrollo

### Estructura del proyecto
```
mushroom-tracker-system/
├── mushroom_detector.py      # Detector de tracks micológicos
├── wikiloc_scraper.py         # Scraper multi-estrategia
├── wikiloc_analyzer.py        # Analizador con IA
├── config.json                # Configuración
├── requirements.txt           # Dependencias
├── README.md                  # Este archivo
├── run.sh                     # Script Linux/Mac
├── run.bat                    # Script Windows
├── LICENSE                    # Licencia MIT
└── .gitignore                # Git ignore
```

### Contribuir

Las contribuciones son bienvenidas:

1. Fork el proyecto
2. Crea tu rama de feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📝 Changelog

### v1.0.0 (2025-01-04)
- Release inicial
- 5 estrategias de scraping
- Detector heurístico completo
- Analizador con clustering
- Soporte multi-plataforma

## 📧 Contacto

Para preguntas, sugerencias o reportar bugs, abre un issue en el repositorio.

## 📄 Licencia

Este proyecto está bajo la Licencia MIT - ver el archivo [LICENSE](LICENSE) para más detalles.

---

**Desarrollado con ❤️ para la comunidad micológica**

*Disclaimer: Este proyecto no está afiliado con Wikiloc. Es una herramienta educacional para análisis de datos públicos.*
