# ml/inference.py - COMPLETE FIXED VERSION
"""
Détection d'anomalies agricoles - FIXED VERSION
"""
import numpy as np
from django.utils import timezone
from datetime import timedelta
from monitoring.models import SensorReading

# Import du modèle ML
try:
    from .ml_model import ml_model
    ML_AVAILABLE = ml_model is not None and ml_model.model is not None
    if ML_AVAILABLE:
        print(f"✅ ML Model loaded with {ml_model.model.n_features_in_} features")
except (ImportError, AttributeError) as e:
    print(f"⚠️  Erreur import ML: {e}")
    ml_model = None
    ML_AVAILABLE = False

class AnomalyDetector:
    @staticmethod
    def get_latest_reading_for_sensor(plot_id, sensor_type, default_value):
        """Get the single most recent reading for a specific sensor type"""
        try:
            reading = SensorReading.objects.filter(
                plot_id=plot_id,
                sensor_type=sensor_type
            ).order_by('-timestamp').first()
            
            if reading:
                return float(reading.value)
            else:
                return default_value
        except Exception as e:
            print(f"⚠️ Error getting {sensor_type} reading: {e}")
            return default_value
    
    @staticmethod
    def get_latest_readings(plot_id):
        """Get the most recent value for EACH sensor type"""
        # Get latest moisture
        moisture_reading = SensorReading.objects.filter(
            plot_id=plot_id, 
            sensor_type='moisture'
        ).order_by('-timestamp').first()
        
        # Get latest temperature  
        temp_reading = SensorReading.objects.filter(
            plot_id=plot_id,
            sensor_type='temperature'
        ).order_by('-timestamp').first()
        
        # Get latest humidity
        humidity_reading = SensorReading.objects.filter(
            plot_id=plot_id,
            sensor_type='humidity'
        ).order_by('-timestamp').first()
        
        moisture = float(moisture_reading.value) if moisture_reading else 60.0
        temperature = float(temp_reading.value) if temp_reading else 24.0
        humidity = float(humidity_reading.value) if humidity_reading else 65.0
        
        print(f"📊 Latest INDIVIDUAL readings - M: {moisture}, T: {temperature}, H: {humidity}")
        return moisture, temperature, humidity
    
    @staticmethod
    def classify_anomaly(moisture, temperature, humidity):
        """Détermine le type d'anomalie - Check temperature first"""
        # Check temperature extremes first (often more urgent)
        if temperature < 10:
            return 'temperature_low'
        elif temperature > 35:
            return 'temperature_high'
        
        # Then check moisture
        if moisture < 30:
            return 'soil_moisture_low'
        elif moisture > 85:
            return 'soil_moisture_high'
        
        # Then humidity
        if humidity < 30:
            return 'humidity_low'
        elif humidity > 90:
            return 'humidity_high'
        
        # Check combinations
        if temperature > 32 and humidity > 80:
            return 'temperature_high_heat_stress'
        elif moisture < 40 and temperature > 28:
            return 'drought_stress'
        elif moisture > 80 and humidity > 85:
            return 'waterlogging_risk'
        
        return 'normal'
        
    @staticmethod
    def detect_for_plot(plot_id):
        """Détection principale pour une parcelle - FIXED"""
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
        """Détecte une anomalie pour une lecture donnée - COMPLETELY FIXED"""
        try:
            # Get the values - these should be the LATEST values
            moisture = float(reading.get('moisture', 60.0))
            temperature = float(reading.get('temperature', 24.0))
            humidity = float(reading.get('humidity', 65.0))
            
            print(f"🔍 ML Detection - ACTUAL VALUES - Moisture: {moisture}, Temp: {temperature}, Humidity: {humidity}")
            
            # First, classify based on the ACTUAL values
            anomaly_type = AnomalyDetector.classify_anomaly(moisture, temperature, humidity)
            
            # Check if it's an anomaly based on classification
            is_classified_anomaly = anomaly_type != 'unknown'
            
            # Use ML model if available
            if ML_AVAILABLE and hasattr(ml_model, 'model'):
                try:
                    features = np.array([[moisture, temperature, humidity]])
                    prediction = ml_model.model.predict(features)[0]
                    score = ml_model.model.decision_function(features)[0]
                    is_ml_anomaly = (prediction == -1)
                    
                    print(f"🤖 ML says: {'ANOMALY' if is_ml_anomaly else 'Normal'} (score: {score:.3f})")
                    
                    # If classification says anomaly but ML doesn't, trust classification for certain types
                    if is_classified_anomaly and not is_ml_anomaly:
                        # For extreme values, trust classification over ML
                        if (moisture < 30 or moisture > 85 or 
                            temperature < 10 or temperature > 35 or 
                            humidity < 30 or humidity > 90):
                            print(f"⚠️ Extreme value detected, overriding ML")
                            is_anomaly = True
                            score = -0.9  # High confidence for extremes
                        else:
                            is_anomaly = False
                            score = 0.5
                    else:
                        is_anomaly = is_ml_anomaly
                    
                    return {
                        'is_anomaly': is_anomaly,
                        'score': float(score),
                        'moisture': moisture,
                        'temperature': temperature,
                        'humidity': humidity,
                        'anomaly_type': anomaly_type if is_anomaly else 'normal',
                        'ml_used': True
                    }
                    
                except Exception as e:
                    print(f"⚠️ ML prediction error: {e}")
            
            # Fallback: Use classification + rule-based
            is_anomaly = is_classified_anomaly
            
            # Calculate a simple score
            score = -0.8 if is_anomaly else 0.5
            
            print(f"📊 Rule-based: {'ANOMALY' if is_anomaly else 'Normal'} ({anomaly_type})")
            
            return {
                'is_anomaly': is_anomaly,
                'score': score,
                'moisture': moisture,
                'temperature': temperature,
                'humidity': humidity,
                'anomaly_type': anomaly_type if is_anomaly else 'normal',
                'ml_used': False
            }
            
        except Exception as e:
            print(f"❌ Error in detect_anomaly: {e}")
            import traceback
            traceback.print_exc()
            return {'is_anomaly': False, 'score': 0.0, 'ml_used': False, 'error': str(e)}

# Instance globale
detector = AnomalyDetector()