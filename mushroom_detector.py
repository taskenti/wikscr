import gpxpy
import numpy as np
import pandas as pd
from datetime import datetime, time
from geopy.distance import geodesic
from typing import List, Tuple, Dict, Optional
import math
from dataclasses import dataclass
import plotly.graph_objects as go
import plotly.express as px
from pathlib import Path
import json

@dataclass
class TrackMetrics:
    """Métricas calculadas para un track GPX"""
    total_distance: float
    straight_line_distance: float
    tortuosity_index: float
    avg_speed: float
    speed_std: float
    direction_changes_per_km: float
    stop_count: int
    total_duration: float
    avg_altitude: float
    altitude_variability: float
    season_score: float
    time_score: float
    duration_score: float
    spatial_density: float

class MushroomTrackDetector:
    """Detector de tracks micológicos basado en reglas heurísticas"""
    
    def __init__(self, config: Optional[Dict] = None):
        """Inicializa el detector con configuración"""
        self.config = config or self._default_config()
        
    def _default_config(self) -> Dict:
        """Configuración por defecto"""
        return {
            # Velocidades (km/h)
            'max_mushroom_speed': 3.0,
            'stop_speed_threshold': 0.5,
            'min_stop_duration': 60,
            
            # Ángulos
            'direction_change_threshold': 30,
            
            # Temporada
            'spring_months': [3, 4, 5],
            'autumn_months': [9, 10, 11],
            
            # Horarios
            'day_start': time(8, 0),
            'day_end': time(20, 0),
            
            # Duración
            'min_duration': 2 * 3600,
            'max_duration': 6 * 3600,
            
            # Ponderaciones
            'weights': {
                'tortuosity': 0.20,
                'avg_speed': 0.15,
                'direction_changes': 0.15,
                'stops': 0.10,
                'season': 0.10,
                'daytime': 0.10,
                'duration': 0.10,
                'altitude_variability': 0.05,
                'spatial_density': 0.05
            }
        }
    
    def parse_gpx(self, gpx_file: str) -> pd.DataFrame:
        """Parsea archivo GPX a DataFrame"""
        with open(gpx_file, 'r') as f:
            gpx = gpxpy.parse(f)
        
        points = []
        for track in gpx.tracks:
            for segment in track.segments:
                for point in segment.points:
                    points.append({
                        'latitude': point.latitude,
                        'longitude': point.longitude,
                        'elevation': point.elevation or 0,
                        'time': point.time,
                        'speed': point.speed or 0 if hasattr(point, 'speed') else 0
                    })
        
        df = pd.DataFrame(points)
        df['time'] = pd.to_datetime(df['time'])
        df = df.sort_values('time').reset_index(drop=True)
        
        return df
    
    def calculate_metrics(self, df: pd.DataFrame) -> TrackMetrics:
        """Calcula todas las métricas del track"""
        distances = []
        for i in range(len(df) - 1):
            point1 = (df.iloc[i]['latitude'], df.iloc[i]['longitude'])
            point2 = (df.iloc[i+1]['latitude'], df.iloc[i+1]['longitude'])
            distances.append(geodesic(point1, point2).kilometers)
        
        total_distance = sum(distances)
        
        start_point = (df.iloc[0]['latitude'], df.iloc[0]['longitude'])
        end_point = (df.iloc[-1]['latitude'], df.iloc[-1]['longitude'])
        straight_line_distance = geodesic(start_point, end_point).kilometers
        
        tortuosity_index = total_distance / straight_line_distance if straight_line_distance > 0 else 1
        
        df['time_diff'] = df['time'].diff().dt.total_seconds()
        df['distance_diff'] = distances + [0]
        df['speed_kmh'] = df.apply(
            lambda row: (row['distance_diff'] / (row['time_diff'] / 3600)) if row['time_diff'] > 0 else 0,
            axis=1
        )
        avg_speed = df['speed_kmh'].mean()
        speed_std = df['speed_kmh'].std()
        
        direction_changes = 0
        for i in range(1, len(df) - 1):
            if distances[i] > 0 and distances[i-1] > 0:
                bearing1 = self._calculate_bearing(
                    df.iloc[i-1]['latitude'], df.iloc[i-1]['longitude'],
                    df.iloc[i]['latitude'], df.iloc[i]['longitude']
                )
                bearing2 = self._calculate_bearing(
                    df.iloc[i]['latitude'], df.iloc[i]['longitude'],
                    df.iloc[i+1]['latitude'], df.iloc[i+1]['longitude']
                )
                angle_change = abs((bearing2 - bearing1 + 180) % 360 - 180)
                if angle_change > self.config['direction_change_threshold']:
                    direction_changes += 1
        
        direction_changes_per_km = direction_changes / total_distance if total_distance > 0 else 0
        
        stop_count = 0
        stop_duration = 0
        in_stop = False
        
        for i in range(len(df)):
            if df.iloc[i]['speed_kmh'] < self.config['stop_speed_threshold']:
                if not in_stop:
                    in_stop = True
                    stop_start = df.iloc[i]['time']
                stop_duration += df.iloc[i]['time_diff'] if i > 0 else 0
            else:
                if in_stop and stop_duration >= self.config['min_stop_duration']:
                    stop_count += 1
                in_stop = False
                stop_duration = 0
        
        total_duration = (df.iloc[-1]['time'] - df.iloc[0]['time']).total_seconds()
        
        avg_altitude = df['elevation'].mean()
        altitude_variability = df['elevation'].std()
        
        month = df.iloc[0]['time'].month
        season_score = 1.0 if month in self.config['spring_months'] + self.config['autumn_months'] else 0.0
        
        daytime_points = df[df['time'].dt.time.between(
            self.config['day_start'], self.config['day_end']
        )].shape[0]
        time_score = daytime_points / len(df) if len(df) > 0 else 0
        
        if self.config['min_duration'] <= total_duration <= self.config['max_duration']:
            duration_score = 1.0
        elif total_duration < self.config['min_duration']:
            duration_score = total_duration / self.config['min_duration']
        else:
            duration_score = max(0, 1 - (total_duration - self.config['max_duration']) / (self.config['max_duration'] * 2))
        
        spatial_density = len(df) / total_distance if total_distance > 0 else 0
        
        return TrackMetrics(
            total_distance=total_distance,
            straight_line_distance=straight_line_distance,
            tortuosity_index=tortuosity_index,
            avg_speed=avg_speed,
            speed_std=speed_std,
            direction_changes_per_km=direction_changes_per_km,
            stop_count=stop_count,
            total_duration=total_duration,
            avg_altitude=avg_altitude,
            altitude_variability=altitude_variability,
            season_score=season_score,
            time_score=time_score,
            duration_score=duration_score,
            spatial_density=spatial_density
        )
    
    def _calculate_bearing(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calcula el rumbo entre dos puntos"""
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        
        dlon = lon2 - lon1
        x = math.sin(dlon) * math.cos(lat2)
        y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
        
        initial_bearing = math.atan2(x, y)
        initial_bearing = math.degrees(initial_bearing)
        compass_bearing = (initial_bearing + 360) % 360
        
        return compass_bearing
    
    def calculate_mushroom_score(self, metrics: TrackMetrics) -> Tuple[float, Dict[str, float]]:
        """Calcula el score micológico total y scores individuales"""
        scores = {}
        
        scores['tortuosity'] = min(metrics.tortuosity_index / 3, 1.0)
        
        if metrics.avg_speed <= self.config['max_mushroom_speed']:
            scores['avg_speed'] = 1.0
        else:
            scores['avg_speed'] = max(0, 1 - (metrics.avg_speed - self.config['max_mushroom_speed']) / self.config['max_mushroom_speed'])
        
        scores['direction_changes'] = min(metrics.direction_changes_per_km / 10, 1.0)
        scores['stops'] = min(metrics.stop_count / 10, 1.0)
        scores['season'] = metrics.season_score
        scores['daytime'] = metrics.time_score
        scores['duration'] = metrics.duration_score
        scores['altitude_variability'] = min(metrics.altitude_variability / 50, 1.0)
        scores['spatial_density'] = min(metrics.spatial_density / 100, 1.0)
        
        total_score = sum(scores[metric] * self.config['weights'][metric] 
                         for metric in self.config['weights'])
        
        return total_score * 100, scores
    
    def analyze_gpx(self, gpx_file: str) -> Dict:
        """Analiza un archivo GPX y devuelve todos los resultados"""
        df = self.parse_gpx(gpx_file)
        metrics = self.calculate_metrics(df)
        total_score, component_scores = self.calculate_mushroom_score(metrics)
        
        return {
            'filename': Path(gpx_file).name,
            'total_score': round(total_score, 2),
            'component_scores': {k: round(v * 100, 2) for k, v in component_scores.items()},
            'metrics': {
                'total_distance_km': round(metrics.total_distance, 2),
                'straight_line_distance_km': round(metrics.straight_line_distance, 2),
                'tortuosity_index': round(metrics.tortuosity_index, 2),
                'avg_speed_kmh': round(metrics.avg_speed, 2),
                'direction_changes_per_km': round(metrics.direction_changes_per_km, 2),
                'stop_count': metrics.stop_count,
                'total_duration_hours': round(metrics.total_duration / 3600, 2),
                'spatial_density': round(metrics.spatial_density, 2)
            },
            'interpretation': self._interpret_score(total_score)
        }
    
    def _interpret_score(self, score: float) -> str:
        """Interpreta el score total"""
        if score >= 80:
            return "ALTA probabilidad de track micológico"
        elif score >= 60:
            return "MEDIA probabilidad de track micológico"
        elif score >= 40:
            return "BAJA probabilidad de track micológico"
        else:
            return "Probablemente NO es un track micológico"

def main():
    import sys
    
    if len(sys.argv) < 2:
        print("Uso: python mushroom_detector.py <archivo.gpx> [<archivo2.gpx> ...]")
        print("O: python mushroom_detector.py <directorio_con_gpx>")
        return
    
    detector = MushroomTrackDetector()
    
    path = Path(sys.argv[1])
    
    if path.is_dir():
        gpx_files = list(path.glob("**/*.gpx"))
    else:
        gpx_files = [Path(arg) for arg in sys.argv[1:]]
    
    print(f"Analizando {len(gpx_files)} archivos GPX...\n")
    
    results = []
    for gpx_file in gpx_files:
        try:
            print(f"Procesando: {gpx_file.name}")
            analysis = detector.analyze_gpx(str(gpx_file))
            results.append(analysis)
            
            print(f"  Score: {analysis['total_score']}")
            print(f"  {analysis['interpretation']}\n")
        except Exception as e:
            print(f"  Error: {e}\n")
    
    with open('mushroom_analysis_results.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"Resultados guardados en: mushroom_analysis_results.json")

if __name__ == "__main__":
    main()
