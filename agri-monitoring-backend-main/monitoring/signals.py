# monitoring/signals.py - FIXED
"""
Simple signals for automatic AI recommendations - FIXED VERSION
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from .models import SensorReading, AnomalyEvent, AgentRecommendation
from ml.inference import AnomalyDetector
from .ai_agent import ai_agent

@receiver(post_save, sender=SensorReading)
def detect_anomaly_on_sensor_reading(sender, instance, created, **kwargs):
    """
    Automatically run ML anomaly detection when new sensor reading arrives
    """
    if not created:
        return  # Only for new readings
    
    print(f"📡 New sensor reading: Plot {instance.plot_id}, Type: {instance.sensor_type}, Value: {instance.value}")
    
    # Wait a moment to ensure the reading is saved
    import time
    time.sleep(0.1)
    
    try:
        # Use detect_for_plot which gets the LATEST readings properly
        detector = AnomalyDetector()
        result = detector.detect_for_plot(instance.plot_id)
        
        if result.get('is_anomaly', False):
            anomaly_type = result.get('anomaly_type', 'unknown')
            
            # Don't create duplicate anomalies for the same type within 5 minutes
            recent_duplicate = AnomalyEvent.objects.filter(
                plot=instance.plot,
                anomaly_type=anomaly_type,  # Must be EXACT match
                timestamp__gte=timezone.now() - timezone.timedelta(minutes=1)  # Only 1 minute
            ).exists()
            
            if recent_duplicate:
                print(f"⚠️ Similar anomaly recently detected, skipping duplicate")
                return
            
            # Determine severity
            score = result.get('score', 0.0)  # ML anomaly score (negative for anomalies)
            confidence = abs(score)
            if score < -0.15:    # HIGH (was -0.2)
                severity = 'high'
            elif score < -0.08:  # MEDIUM (was -0.1)
                severity = 'medium'
            elif score < -0.03:  # LOW (was -0.05)
                severity = 'low'
            else:
                severity = 'low'

            
            # Create AnomalyEvent
            anomaly_event = AnomalyEvent.objects.create(
                plot=instance.plot,
                anomaly_type=anomaly_type,
                severity=severity,
                model_confidence=confidence
            )
            
            print(f"🚨 Anomaly detected: {anomaly_type} (severity: {severity}, confidence: {confidence:.2f})")
            
        else:
            print(f"✅ Reading normal - no anomaly detected")
            
    except Exception as e:
        print(f"❌ Error in anomaly detection: {e}")
        import traceback
        traceback.print_exc()

@receiver(post_save, sender=AnomalyEvent)
def generate_ai_recommendation_on_anomaly(sender, instance, created, **kwargs):
    """
    Automatically generate AI recommendation when anomaly is created
    """
    if not created:
        return  # Only for new anomalies
    
    print(f"🧠 AI Agent: Analyzing anomaly {instance.id} ({instance.anomaly_type})")
    
    # Check if recommendation already exists
    if AgentRecommendation.objects.filter(anomaly_event=instance).exists():
        print(f"⚠️ Recommendation already exists for anomaly {instance.id}")
        return
    
    try:
        # Generate recommendation using AI Agent
        recommendation_data = ai_agent.generate_recommendation(instance)
        
        # Create the recommendation
        AgentRecommendation.objects.create(
            anomaly_event=instance,
            recommended_action=recommendation_data['recommended_action'],
            explanation_text=recommendation_data['explanation_text'],
            confidence=recommendation_data['confidence']
        )
        
        print(f"✅ AI Recommendation generated for anomaly {instance.id}")
        print(f"   Action: {recommendation_data['recommended_action'][:50]}...")
        
    except Exception as e:
        print(f"❌ Error generating AI recommendation: {e}")
        import traceback
        traceback.print_exc()