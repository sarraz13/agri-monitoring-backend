# ml/inference.py - VERSION SIMPLE
from django.db.models import Avg
from datetime import datetime, timedelta
from monitoring.models import SensorReading

# Import local
try:
    from .ml_model import ml_model
except ImportError:
    # Fallback si ml_model n'existe pas
    ml_model = None

class AnomalyDetector:
    """Détecteur simplifié"""
    
    @staticmethod
    def get_plot_features(plot_id, hours_back=2):
        """Récupère les moyennes"""
        time_threshold = datetime.now() - timedelta(hours=hours_back)
        
        readings = SensorReading.objects.filter(
            plot_id=plot_id,
            timestamp__gte=time_threshold
        )
        
        if not readings.exists():
            return 60.0, 24.0, 65.0
        
        moisture = readings.filter(sensor_type='moisture').aggregate(Avg('value'))['value__avg'] or 60.0
        temp = readings.filter(sensor_type='temperature').aggregate(Avg('value'))['value__avg'] or 24.0
        humidity = readings.filter(sensor_type='humidity').aggregate(Avg('value'))['value__avg'] or 65.0
        
        return moisture, temp, humidity
    
    @staticmethod
    def detect_for_plot(plot_id):
        """Détection basique"""
        try:
            moisture, temp, humidity = AnomalyDetector.get_plot_features(plot_id)
            
            # Fallback simple si pas de modèle ML
            if ml_model is None:
                is_anomaly = (
                    moisture < 40 or moisture > 80 or
                    temp < 15 or temp > 35 or
                    humidity < 35 or humidity > 85
                )
                score = -0.5 if is_anomaly else 0.5
                anomaly_type = "water_stress" if moisture < 40 else "other"
            else:
                # Utilise le modèle ML si disponible
                is_anomaly, score = ml_model.predict(moisture, temp, humidity)
                anomaly_type = "detected"
            
            return {
                'is_anomaly': is_anomaly,
                'score': score,
                'moisture': moisture,
                'temperature': temp,
                'humidity_air': humidity,
                'anomaly_type': anomaly_type
            }
            
        except Exception as e:
            return {
                'is_anomaly': False,
                'score': 0.0,
                'error': str(e)
            }

# Instance globale
detector = AnomalyDetector()