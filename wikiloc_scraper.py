import requests
from bs4 import BeautifulSoup
import json
import time
import random
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import re
from urllib.parse import urlencode, quote
import sqlite3
from datetime import datetime, timedelta
import folium
from pathlib import Path
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import gpxpy
import gpxpy.gpx
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import hashlib

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('wikiloc_scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class HotZone:
    """Zona caliente para búsqueda"""
    name: str
    lat: float
    lon: float
    radius: float  # km
    province: str = ""
    country: str = "España"
    keywords: List[str] = None
    
    def __post_init__(self):
        if self.keywords is None:
            self.keywords = ["setas", "hongos", "mushroom", "bosque", "monte"]

@dataclass
class TrackInfo:
    """Información básica de un track"""
    track_id: str
    title: str
    url: str
    distance_km: float
    duration_hours: float
    difficulty: str
    activity_type: str
    date: Optional[datetime]
    author: str
    lat: float
    lon: float
    province: str
    downloads: int
    views: int
    description: str
    gpx_url: Optional[str] = None
    
class WikilocScraperAdvanced:
    """Scraper avanzado de Wikiloc con múltiples estrategias"""
    
    def __init__(self, use_selenium: bool = False, headless: bool = True):
        self.session = requests.Session()
        self.use_selenium = use_selenium
        self.driver = None
        self.headless = headless
        
        # Headers realistas para evitar detección
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        }
        self.session.headers.update(self.headers)
        
        # Base de datos local para caché
        self.db_path = "wikiloc_cache.db"
        self._init_database()
        
        # Delays para no ser detectado
        self.min_delay = 2
        self.max_delay = 5
        
    def _init_database(self):
        """Inicializa base de datos SQLite para caché"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tracks (
                track_id TEXT PRIMARY KEY,
                title TEXT,
                url TEXT,
                distance_km REAL,
                duration_hours REAL,
                difficulty TEXT,
                activity_type TEXT,
                date TEXT,
                author TEXT,
                lat REAL,
                lon REAL,
                province TEXT,
                downloads INTEGER,
                views INTEGER,
                description TEXT,
                gpx_url TEXT,
                scraped_at TEXT,
                gpx_content TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS hot_zones (
                zone_id TEXT PRIMARY KEY,
                name TEXT,
                lat REAL,
                lon REAL,
                radius REAL,
                last_scraped TEXT,
                track_count INTEGER
            )
        ''')
        
        conn.commit()
        conn.close()
        
    def _init_selenium(self):
        """Inicializa Selenium WebDriver"""
        if self.driver is None:
            options = Options()
            if self.headless:
                options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument(f'user-agent={self.headers["User-Agent"]}')
            options.add_argument('--disable-blink-features=AutomationControlled')
            
            self.driver = webdriver.Chrome(options=options)
            logger.info("Selenium WebDriver inicializado")
    
    def _random_delay(self):
        """Delay aleatorio para simular comportamiento humano"""
        time.sleep(random.uniform(self.min_delay, self.max_delay))
    
    def _get_zone_hash(self, zone: HotZone) -> str:
        """Genera hash único para una zona"""
        zone_str = f"{zone.lat}_{zone.lon}_{zone.radius}"
        return hashlib.md5(zone_str.encode()).hexdigest()
    
    # ESTRATEGIA 1: Búsqueda por coordenadas geográficas
    def search_by_coordinates(self, zone: HotZone) -> List[TrackInfo]:
        """Busca tracks cerca de coordenadas específicas"""
        logger.info(f"Buscando tracks en zona: {zone.name}")
        
        tracks = []
        
        # Construir URL de búsqueda por mapa
        base_url = "https://es.wikiloc.com/wikiloc/map.do"
        
        params = {
            'lat': zone.lat,
            'lon': zone.lon,
            'z': 12,
            'act': '5',
            'sw': f"{zone.lat - 0.1},{zone.lon - 0.1}",
            'ne': f"{zone.lat + 0.1},{zone.lon + 0.1}"
        }
        
        try:
            url = f"{base_url}?{urlencode(params)}"
            logger.info(f"URL: {url}")
            
            response = self.session.get(url, timeout=10)
            self._random_delay()
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    if 'trails' in data:
                        for trail in data['trails']:
                            track = self._parse_trail_json(trail, zone)
                            if track:
                                tracks.append(track)
                                logger.info(f"Track encontrado: {track.title}")
                except json.JSONDecodeError:
                    logger.warning("Respuesta no es JSON, intentando parsear HTML")
                    tracks = self._parse_html_tracks(response.text, zone)
            else:
                logger.warning(f"Status code: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error en búsqueda por coordenadas: {e}")
        
        return tracks
    
    # ESTRATEGIA 2: Búsqueda por texto + ubicación
    def search_by_keywords(self, zone: HotZone, keywords: List[str] = None) -> List[TrackInfo]:
        """Busca tracks usando palabras clave + ubicación"""
        if keywords is None:
            keywords = zone.keywords
        
        tracks = []
        
        for keyword in keywords:
            logger.info(f"Buscando con keyword: '{keyword}' en {zone.name}")
            
            search_url = "https://es.wikiloc.com/wikiloc/find.do"
            
            params = {
                'q': f"{keyword} {zone.province}",
                'lat': zone.lat,
                'lon': zone.lon,
                'd': zone.radius,
                'act': '',
            }
            
            try:
                response = self.session.get(search_url, params=params, timeout=10)
                self._random_delay()
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    trail_items = soup.find_all('div', class_='trail-card') or \
                                 soup.find_all('li', class_='trail-item') or \
                                 soup.find_all('div', class_='item')
                    
                    for item in trail_items:
                        track = self._parse_trail_html(item, zone)
                        if track and track not in tracks:
                            tracks.append(track)
                            logger.info(f"Track encontrado: {track.title}")
                    
                    logger.info(f"Encontrados {len(trail_items)} resultados para '{keyword}'")
                    
            except Exception as e:
                logger.error(f"Error buscando con keyword '{keyword}': {e}")
        
        return tracks
    
    # ESTRATEGIA 3: Selenium para contenido dinámico
    def search_with_selenium(self, zone: HotZone) -> List[TrackInfo]:
        """Usa Selenium para contenido cargado con JavaScript"""
        self._init_selenium()
        tracks = []
        
        try:
            url = f"https://es.wikiloc.com/wikiloc/explore.do?lat={zone.lat}&lon={zone.lon}"
            logger.info(f"Cargando con Selenium: {url}")
            
            self.driver.get(url)
            
            wait = WebDriverWait(self.driver, 10)
            wait.until(EC.presence_of_element_located((By.CLASS_NAME, "trail-card")))
            
            for _ in range(3):
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
            
            html = self.driver.page_source
            soup = BeautifulSoup(html, 'html.parser')
            
            trail_cards = soup.find_all('div', class_='trail-card')
            for card in trail_cards:
                track = self._parse_trail_html(card, zone)
                if track:
                    tracks.append(track)
                    
            logger.info(f"Encontrados {len(tracks)} tracks con Selenium")
            
        except Exception as e:
            logger.error(f"Error con Selenium: {e}")
        
        return tracks
    
    # ESTRATEGIA 4: API no documentada
    def search_api_endpoint(self, zone: HotZone) -> List[TrackInfo]:
        """Intenta usar endpoints de API internos"""
        tracks = []
        
        api_endpoints = [
            f"https://es.wikiloc.com/wikiloc/trails.json?sw={zone.lat-0.1},{zone.lon-0.1}&ne={zone.lat+0.1},{zone.lon+0.1}",
            f"https://es.wikiloc.com/wikiloc/nearby.json?lat={zone.lat}&lon={zone.lon}&d={zone.radius}",
        ]
        
        for endpoint in api_endpoints:
            try:
                logger.info(f"Probando endpoint: {endpoint}")
                response = self.session.get(endpoint, timeout=10)
                self._random_delay()
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        logger.info(f"Respuesta JSON recibida: {len(str(data))} caracteres")
                        
                        if isinstance(data, list):
                            for item in data:
                                track = self._parse_trail_json(item, zone)
                                if track:
                                    tracks.append(track)
                        elif isinstance(data, dict) and 'trails' in data:
                            for item in data['trails']:
                                track = self._parse_trail_json(item, zone)
                                if track:
                                    tracks.append(track)
                                    
                    except json.JSONDecodeError:
                        logger.warning("Respuesta no es JSON válido")
                        
            except Exception as e:
                logger.error(f"Error en endpoint {endpoint}: {e}")
        
        return tracks
    
    # ESTRATEGIA 5: Scraping de perfiles de usuarios activos
    def search_by_active_users(self, zone: HotZone) -> List[TrackInfo]:
        """Busca tracks de usuarios activos en la zona"""
        tracks = []
        
        users_url = f"https://es.wikiloc.com/wikiloc/users.do?lat={zone.lat}&lon={zone.lon}&d={zone.radius}"
        
        try:
            response = self.session.get(users_url, timeout=10)
            self._random_delay()
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                user_links = soup.find_all('a', href=re.compile(r'/wikiloc/user\.do\?id='))
                
                for user_link in user_links[:5]:
                    user_url = "https://es.wikiloc.com" + user_link.get('href')
                    logger.info(f"Scrapeando usuario: {user_url}")
                    
                    user_tracks = self._scrape_user_tracks(user_url, zone)
                    tracks.extend(user_tracks)
                    self._random_delay()
                    
        except Exception as e:
            logger.error(f"Error buscando usuarios: {e}")
        
        return tracks
    
    def _scrape_user_tracks(self, user_url: str, zone: HotZone) -> List[TrackInfo]:
        """Scrapea tracks de un usuario específico"""
        tracks = []
        
        try:
            response = self.session.get(user_url, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                trail_items = soup.find_all('div', class_='trail-card')
                
                for item in trail_items:
                    track = self._parse_trail_html(item, zone)
                    if track:
                        from geopy.distance import geodesic
                        dist = geodesic((zone.lat, zone.lon), (track.lat, track.lon)).km
                        if dist <= zone.radius:
                            tracks.append(track)
                            
        except Exception as e:
            logger.error(f"Error scrapeando usuario: {e}")
        
        return tracks
    
    def _parse_trail_json(self, data: Dict, zone: HotZone) -> Optional[TrackInfo]:
        """Parsea datos JSON de un trail"""
        try:
            track_id = str(data.get('id', ''))
            
            return TrackInfo(
                track_id=track_id,
                title=data.get('name', ''),
                url=f"https://es.wikiloc.com/wikiloc/view.do?id={track_id}",
                distance_km=float(data.get('distance', 0)) / 1000,
                duration_hours=float(data.get('duration', 0)) / 3600,
                difficulty=data.get('difficulty', ''),
                activity_type=data.get('activity', ''),
                date=None,
                author=data.get('user', {}).get('name', ''),
                lat=float(data.get('lat', zone.lat)),
                lon=float(data.get('lon', zone.lon)),
                province=zone.province,
                downloads=int(data.get('downloads', 0)),
                views=int(data.get('views', 0)),
                description=data.get('description', ''),
                gpx_url=data.get('gpx_url', '')
            )
        except Exception as e:
            logger.error(f"Error parseando JSON: {e}")
            return None
    
    def _parse_trail_html(self, element, zone: HotZone) -> Optional[TrackInfo]:
        """Parsea elemento HTML de un trail"""
        try:
            title_elem = element.find('a', class_='trail-title') or element.find('h3')
            if not title_elem:
                return None
            
            title = title_elem.get_text(strip=True)
            url = title_elem.get('href', '')
            if url and not url.startswith('http'):
                url = f"https://es.wikiloc.com{url}"
            
            track_id_match = re.search(r'id=(\d+)', url)
            track_id = track_id_match.group(1) if track_id_match else ''
            
            distance_elem = element.find(string=re.compile(r'\d+[\.,]\d+\s*km'))
            distance_km = 0.0
            if distance_elem:
                dist_match = re.search(r'(\d+[\.,]\d+)', distance_elem)
                if dist_match:
                    distance_km = float(dist_match.group(1).replace(',', '.'))
            
            return TrackInfo(
                track_id=track_id,
                title=title,
                url=url,
                distance_km=distance_km,
                duration_hours=0.0,
                difficulty='',
                activity_type='',
                date=None,
                author='',
                lat=zone.lat,
                lon=zone.lon,
                province=zone.province,
                downloads=0,
                views=0,
                description=''
            )
            
        except Exception as e:
            logger.error(f"Error parseando HTML: {e}")
            return None
    
    def _parse_html_tracks(self, html: str, zone: HotZone) -> List[TrackInfo]:
        """Parsea tracks de HTML general"""
        tracks = []
        soup = BeautifulSoup(html, 'html.parser')
        
        trail_elements = (
            soup.find_all('div', class_='trail-card') +
            soup.find_all('li', class_='trail-item') +
            soup.find_all('div', class_='item')
        )
        
        for elem in trail_elements:
            track = self._parse_trail_html(elem, zone)
            if track:
                tracks.append(track)
        
        return tracks
    
    def download_gpx(self, track: TrackInfo) -> Optional[str]:
        """Descarga el archivo GPX de un track"""
        if not track.gpx_url:
            track.gpx_url = f"https://es.wikiloc.com/wikiloc/download.do?id={track.track_id}"
        
        try:
            logger.info(f"Descargando GPX: {track.title}")
            response = self.session.get(track.gpx_url, timeout=15)
            self._random_delay()
            
            if response.status_code == 200:
                try:
                    gpxpy.parse(response.text)
                    return response.text
                except:
                    logger.warning(f"El contenido descargado no es un GPX válido")
                    return None
            else:
                logger.warning(f"No se pudo descargar GPX: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error descargando GPX: {e}")
            return None
    
    def save_track_to_db(self, track: TrackInfo, gpx_content: Optional[str] = None):
        """Guarda track en base de datos"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO tracks VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            track.track_id, track.title, track.url, track.distance_km,
            track.duration_hours, track.difficulty, track.activity_type,
            str(track.date) if track.date else None, track.author,
            track.lat, track.lon, track.province, track.downloads,
            track.views, track.description, track.gpx_url,
            datetime.now().isoformat(), gpx_content
        ))
        
        conn.commit()
        conn.close()
    
    def scrape_hot_zone(self, zone: HotZone, strategies: List[str] = None) -> List[TrackInfo]:
        """Scrapea una zona usando múltiples estrategias"""
        if strategies is None:
            strategies = ['coordinates', 'keywords', 'api']
        
        all_tracks = []
        seen_ids = set()
        
        logger.info(f"=== Iniciando scraping de zona: {zone.name} ===")
        
        for strategy in strategies:
            logger.info(f"Ejecutando estrategia: {strategy}")
            
            tracks = []
            if strategy == 'coordinates':
                tracks = self.search_by_coordinates(zone)
            elif strategy == 'keywords':
                tracks = self.search_by_keywords(zone)
            elif strategy == 'selenium' and self.use_selenium:
                tracks = self.search_with_selenium(zone)
            elif strategy == 'api':
                tracks = self.search_api_endpoint(zone)
            elif strategy == 'users':
                tracks = self.search_by_active_users(zone)
            
            for track in tracks:
                if track.track_id not in seen_ids:
                    all_tracks.append(track)
                    seen_ids.add(track.track_id)
                    self.save_track_to_db(track)
            
            logger.info(f"Estrategia '{strategy}': {len(tracks)} tracks encontrados")
        
        logger.info(f"=== Total tracks únicos: {len(all_tracks)} ===")
        return all_tracks
    
    def download_all_gpx(self, tracks: List[TrackInfo], output_dir: str = "gpx_files"):
        """Descarga todos los GPX de los tracks"""
        Path(output_dir).mkdir(exist_ok=True)
        
        successful = 0
        failed = 0
        
        for i, track in enumerate(tracks, 1):
            logger.info(f"[{i}/{len(tracks)}] Descargando: {track.title}")
            
            gpx_content = self.download_gpx(track)
            
            if gpx_content:
                filename = f"{track.track_id}_{track.title[:50]}.gpx"
                filename = re.sub(r'[^\w\s-]', '', filename)
                filepath = Path(output_dir) / filename
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(gpx_content)
                
                self.save_track_to_db(track, gpx_content)
                
                successful += 1
                logger.info(f"✓ Guardado: {filepath}")
            else:
                failed += 1
                logger.warning(f"✗ Fallo al descargar: {track.title}")
        
        logger.info(f"\n=== Resumen de descargas ===")
        logger.info(f"Exitosas: {successful}")
        logger.info(f"Fallidas: {failed}")
    
    def create_heatmap(self, tracks: List[TrackInfo], output_file: str = "heatmap.html"):
        """Crea mapa de calor con los tracks encontrados"""
        if not tracks:
            logger.warning("No hay tracks para crear mapa")
            return
        
        center_lat = sum(t.lat for t in tracks) / len(tracks)
        center_lon = sum(t.lon for t in tracks) / len(tracks)
        
        m = folium.Map(location=[center_lat, center_lon], zoom_start=10)
        
        for track in tracks:
            folium.CircleMarker(
                location=[track.lat, track.lon],
                radius=5,
                popup=f"<b>{track.title}</b><br>{track.distance_km} km<br><a href='{track.url}' target='_blank'>Ver en Wikiloc</a>",
                color='red',
                fill=True,
                fillColor='red'
            ).add_to(m)
        
        m.save(output_file)
        logger.info(f"Mapa guardado en: {output_file}")
    
    def cleanup(self):
        """Limpia recursos"""
        if self.driver:
            self.driver.quit()
            logger.info("Selenium WebDriver cerrado")

# ZONAS CALIENTES PREDEFINIDAS - ESPAÑA
SPANISH_HOT_ZONES = [
    HotZone("Picos de Europa", 43.1965, -4.8152, 15, "León", "España", 
            ["setas", "montaña", "bosque", "picos europa"]),
    HotZone("Sierra de Guadarrama", 40.7736, -4.0117, 20, "Madrid", "España",
            ["setas", "guadarrama", "hayedo", "pinar"]),
    HotZone("Pirineos Catalanes", 42.3453, 1.7318, 25, "Lleida", "España",
            ["bolets", "pirineu", "muntanya"]),
    HotZone("Montseny", 41.7667, 2.4333, 15, "Barcelona", "España",
            ["bolets", "montseny", "fageda"]),
    HotZone("Sierra de Gredos", 40.2969, -5.2219, 20, "Ávila", "España",
            ["setas", "gredos", "castaño"]),
    HotZone("Selva de Irati", 42.9833, -1.1667, 15, "Navarra", "España",
            ["setas", "irati", "haya", "hayedo"]),
    HotZone("Comarca de la Vera", 40.1167, -5.4667, 15, "Cáceres", "España",
            ["setas", "vera", "castaño", "roble"]),
]

def main():
    """Función principal de ejemplo"""
    print("🍄 Wikiloc Advanced Scraper - Zonas Calientes de Setas 🍄\n")
    
    use_selenium = input("¿Usar Selenium? (más completo pero más lento) [s/N]: ").lower() == 's'
    
    scraper = WikilocScraperAdvanced(use_selenium=use_selenium)
    
    print("\n📍 Zonas calientes disponibles:")
    for i, zone in enumerate(SPANISH_HOT_ZONES, 1):
        print(f"{i}. {zone.name} ({zone.province}) - Radio: {zone.radius}km")
    
    selection = input("\nSelecciona zona(s) [1-7, 'todas', o 'personalizada']: ").strip()
    
    zones_to_scrape = []
    
    if selection.lower() == 'todas':
        zones_to_scrape = SPANISH_HOT_ZONES
    elif selection.lower() == 'personalizada':
        name = input("Nombre de la zona: ")
        lat = float(input("Latitud: "))
        lon = float(input("Longitud: "))
        radius = float(input("Radio (km): "))
        province = input("Provincia: ")
        keywords = input("Keywords (separadas por coma): ").split(',')
        
        zones_to_scrape = [HotZone(name, lat, lon, radius, province, "España", 
                                   [k.strip() for k in keywords])]
    else:
        try:
            indices = [int(x.strip()) - 1 for x in selection.split(',')]
            zones_to_scrape = [SPANISH_HOT_ZONES[i] for i in indices if 0 <= i < len(SPANISH_HOT_ZONES)]
        except:
            print("Selección inválida, usando primera zona")
            zones_to_scrape = [SPANISH_HOT_ZONES[0]]
    
    print("\n🎯 Estrategias disponibles:")
    print("1. coordinates - Búsqueda por coordenadas geográficas")
    print("2. keywords - Búsqueda por palabras clave")
    print("3. api - Endpoints de API internos")
    print("4. selenium - Contenido dinámico (requiere Selenium)")
    print("5. users - Scraping de usuarios activos")
    
    strategy_input = input("\nEstrategias a usar (separadas por coma) [coordinates,keywords,api]: ").strip()
    strategies = [s.strip() for s in strategy_input.split(',')] if strategy_input else ['coordinates', 'keywords', 'api']
    
    all_tracks = []
    
    for zone in zones_to_scrape:
        print(f"\n{'='*60}")
        print(f"🔍 Scrapeando zona: {zone.name}")
        print(f"{'='*60}")
        
        tracks = scraper.scrape_hot_zone(zone, strategies)
        all_tracks.extend(tracks)
        
        print(f"\n✅ Encontrados {len(tracks)} tracks en {zone.name}")
    
    print(f"\n{'='*60}")
    print(f"📊 RESUMEN TOTAL")
    print(f"{'='*60}")
    print(f"Total de tracks únicos encontrados: {len(all_tracks)}")
    
    if all_tracks:
        export_json = input("\n¿Exportar resultados a JSON? [S/n]: ").lower() != 'n'
        if export_json:
            with open('tracks_found.json', 'w', encoding='utf-8') as f:
                json.dump([{
                    'track_id': t.track_id,
                    'title': t.title,
                    'url': t.url,
                    'distance_km': t.distance_km,
                    'province': t.province,
                    'lat': t.lat,
                    'lon': t.lon
                } for t in all_tracks], f, indent=2, ensure_ascii=False)
            print("✓ Exportado a tracks_found.json")
        
        create_map = input("¿Crear mapa de calor? [S/n]: ").lower() != 'n'
        if create_map:
            scraper.create_heatmap(all_tracks, "tracks_heatmap.html")
            print("✓ Mapa creado: tracks_heatmap.html")
        
        download = input("\n¿Descargar archivos GPX? [s/N]: ").lower() == 's'
      print("\n⬇️  Iniciando descarga de GPX...")
        scraper.download_all_gpx(all_tracks)
        print("✓ Descarga completada")

scraper.cleanup()

print("\n🎉 ¡Proceso completado!")
print(f"📁 Archivos generados:")
print(f"   - wikiloc_cache.db (base de datos)")
print(f"   - tracks_found.json (resultados)")
print(f"   - tracks_heatmap.html (mapa)")
print(f"   - gpx_files/ (archivos GPX)")
print(f"   - wikiloc_scraper.log (log)")
        if download:
