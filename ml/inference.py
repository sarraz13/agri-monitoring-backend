"""
Détection d'anomalies agricoles
"""
import numpy as np
from datetime import timedelta
from django.utils import timezone
from django.db.models import Avg

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
        """Récupère les 3 dernières lectures de chaque capteur"""
        readings = SensorReading.objects.filter(
            plot_id=plot_id
        ).order_by('-timestamp')[:10]  # 10 dernières
        
        # Initialise avec valeurs par défaut
        values = {
            'moisture': 60.0,
            'temperature': 24.0,
            'humidity': 65.0
        }
        
        # Prend la dernière de chaque type
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
        """Détection principale"""
        try:
            # 1. Récupère les dernières valeurs
            moisture, temp, humidity = AnomalyDetector.get_latest_readings(plot_id)
            
            print(f"🔍 Détection - Parcelle {plot_id}:")
            print(f"   Humidité sol: {moisture}%")
            print(f"   Température: {temp}°C")
            print(f"   Humidité air: {humidity}%")
            
            # 2. Utilise le modèle ML si disponible
            if ML_AVAILABLE and hasattr(ml_model, 'predict'):
                print("   🤖 Utilisation modèle ML...")
                
                # Prépare les features
                features = np.array([[moisture, temp, humidity]])
                
                # Prédiction
                prediction = ml_model.model.predict(features)[0]
                
                # Score (decision_function pour Isolation Forest)
                score = ml_model.model.decision_function(features)[0]
                
                is_anomaly = prediction == -1
                anomaly_type = AnomalyDetector.classify_anomaly(moisture, temp, humidity)
                
                print(f"   Résultat ML: {'ANOMALIE' if is_anomaly else 'Normal'}")
                print(f"   Score: {score:.3f}")
                print(f"   Type: {anomaly_type}")
                
            else:
                # 3. Fallback: règles simples
                print("   ⚠️  Utilisation règles de fallback...")
                
                is_anomaly = (
                    moisture < 40 or moisture > 80 or
                    temp < 15 or temp > 35 or
                    humidity < 35 or humidity > 85
                )
                
                # Score simulé basé sur les écarts
                score = -0.8 if is_anomaly else 0.5
                anomaly_type = AnomalyDetector.classify_anomaly(moisture, temp, humidity)
                
                print(f"   Résultat fallback: {'ANOMALIE' if is_anomaly else 'Normal'}")
                print(f"   Type: {anomaly_type}")
            
            # 4. Retourne le résultat
            return {
                'is_anomaly': is_anomaly,
                'score': float(score),
                'moisture': float(moisture),
                'temperature': float(temp),
                'humidity_air': float(humidity),
                'anomaly_type': anomaly_type,
                'ml_used': ML_AVAILABLE
            }
            
        except Exception as e:
            print(f"❌ Erreur détection: {e}")
            import traceback
            traceback.print_exc()
            
            return {
                'is_anomaly': False,
                'score': 0.0,
                'error': str(e),
                'ml_used': False
            }

# Instance globale
detector = AnomalyDetector()