"""
Détection d'anomalies agricoles
"""
import numpy as np
from django.utils import timezone
from monitoring.models import SensorReading

# Import du modèle ML
try:
    from .ml_model import ml_model
    ML_AVAILABLE = ml_model is not None and ml_model.model is not None
except (ImportError, AttributeError) as e:
    print(f"⚠️  Erreur import ML: {e}")
    ml_model = None
    ML_AVAILABLE = False

class AnomalyDetector:
    @staticmethod
    def get_latest_readings(plot_id):
        """Récupère les 10 dernières lectures pour chaque capteur"""
        readings = SensorReading.objects.filter(plot_id=plot_id).order_by('-timestamp')[:10]
        values = {'moisture': 60.0, 'temperature': 24.0, 'humidity': 65.0}
        for reading in readings:
            if reading.sensor_type in values and values[reading.sensor_type] == 60.0:
                values[reading.sensor_type] = float(reading.value)
        return values['moisture'], values['temperature'], values['humidity']

    @staticmethod
    def classify_anomaly(moisture, temperature, humidity):
        """Détermine le type d'anomalie"""
        if moisture < 35:
            return 'soil_moisture_low'
        elif moisture > 85:
            return 'soil_moisture_high'
        elif temperature < 10:
            return 'temperature_low'
        elif temperature > 35:
            return 'temperature_high'
        elif humidity < 30:
            return 'air_humidity_low'
        elif humidity > 90:
            return 'air_humidity_high'
        return 'unknown'

    @staticmethod
    def detect_for_plot(plot_id):
        """Détection principale pour une parcelle"""
        try:
            moisture, temp, humidity = AnomalyDetector.get_latest_readings(plot_id)
            return AnomalyDetector.detect_anomaly({
                'moisture': moisture,
                'temperature': temp,
                'humidity': humidity
            })
        except Exception as e:
            print(f"❌ Erreur détection parcelle: {e}")
            return {'is_anomaly': False, 'score': 0.0, 'ml_used': False, 'error': str(e)}

    @staticmethod
    def detect_anomaly(reading):
        """Détecte une anomalie pour une lecture donnée"""
        try:
            moisture = float(reading.get('moisture', 60.0))
            temperature = float(reading.get('temperature', 24.0))
            humidity = float(reading.get('humidity', 65.0))

            if ML_AVAILABLE and hasattr(ml_model, 'predict'):
                features = np.array([[moisture, temperature, humidity]])
                prediction = ml_model.model.predict(features)[0]
                score = ml_model.model.decision_function(features)[0]
                is_anomaly = prediction == -1
                anomaly_type = AnomalyDetector.classify_anomaly(moisture, temperature, humidity)
            else:
                # Fallback rules
                is_anomaly = (
                    moisture < 40 or moisture > 80 or
                    temperature < 15 or temperature > 35 or
                    humidity < 35 or humidity > 85
                )
                score = -0.8 if is_anomaly else 0.5
                anomaly_type = AnomalyDetector.classify_anomaly(moisture, temperature, humidity)

            return {
                'is_anomaly': is_anomaly,
                'score': float(score),
                'moisture': moisture,
                'temperature': temperature,
                'humidity_air': humidity,
                'anomaly_type': anomaly_type,
                'ml_used': ML_AVAILABLE
            }

        except Exception as e:
            print(f"❌ Erreur détection lecture: {e}")
            return {'is_anomaly': False, 'score': 0.0, 'ml_used': False, 'error': str(e)}

# Instance globale
detector = AnomalyDetector()
