# ml/inference.py
"""
Interface de détection d'anomalies pour Django
"""
from .ml_model import ml_model
import numpy as np
from django.db.models import Avg
from monitoring.models import SensorReading
from datetime import datetime, timedelta

class AnomalyDetector:
    """Détecteur d'anomalies pour les parcelles"""
    
    @staticmethod
    def get_plot_features(plot_id, hours_back=2):
        """
        Récupère les moyennes des features d'une parcelle
        
        Returns:
            (moisture_avg, temp_avg, humidity_avg)
        """
        time_threshold = datetime.now() - timedelta(hours=hours_back)
        
        # Récupère les lectures récentes
        readings = SensorReading.objects.filter(
            plot_id=plot_id,
            timestamp__gte=time_threshold
        )
        
        if not readings.exists():
            return 60.0, 24.0, 65.0  # Valeurs par défaut
        
        # Calcule les moyennes par type de capteur
        moisture_readings = readings.filter(sensor_type='moisture')
        temp_readings = readings.filter(sensor_type='temperature')
        humidity_readings = readings.filter(sensor_type='humidity')
        
        moisture_avg = moisture_readings.aggregate(Avg('value'))['value__avg'] or 60.0
        temp_avg = temp_readings.aggregate(Avg('value'))['value__avg'] or 24.0
        humidity_avg = humidity_readings.aggregate(Avg('value'))['value__avg'] or 65.0
        
        return moisture_avg, temp_avg, humidity_avg
    
    @staticmethod
    def detect_for_plot(plot_id):
        """
        Détecte une anomalie pour une parcelle spécifique
        
        Returns:
            {
                'is_anomaly': bool,
                'score': float,
                'moisture': float,
                'temperature': float,
                'humidity_air': float,
                'anomaly_type': str or None
            }
        """
        # 1. Récupère les features
        moisture, temp, humidity = AnomalyDetector.get_plot_features(plot_id)
        
        # 2. Prédiction ML
        is_anomaly, score = ml_model.predict(moisture, temp, humidity)
        
        # 3. Détermine le type d'anomalie
        anomaly_type = None
        if is_anomaly:
            if moisture < 40:
                anomaly_type = 'moisture_low'
            elif moisture > 80:
                anomaly_type = 'moisture_high'
            elif temp < 15:
                anomaly_type = 'temperature_low'
            elif temp > 32:
                anomaly_type = 'temperature_high'
            elif humidity < 35:
                anomaly_type = 'humidity_low'
            elif humidity > 85:
                anomaly_type = 'humidity_high'
            else:
                anomaly_type = 'unknown'
        
        return {
            'is_anomaly': is_anomaly,
            'score': score,
            'moisture': moisture,
            'temperature': temp,
            'humidity_air': humidity,
            'anomaly_type': anomaly_type
        }
    
    @staticmethod
    def check_all_plots():
        """Vérifie toutes les parcelles pour anomalies"""
        from monitoring.models import FieldPlot
        
        plots = FieldPlot.objects.all()
        results = []
        
        for plot in plots:
            result = AnomalyDetector.detect_for_plot(plot.id)
            result['plot_id'] = plot.id
            result['plot_name'] = plot.plot_name
            results.append(result)
        
        return results

# Instance globale
detector = AnomalyDetector()