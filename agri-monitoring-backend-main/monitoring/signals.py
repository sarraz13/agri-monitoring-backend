"""
Simple signals for automatic AI recommendations
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import AnomalyEvent, AgentRecommendation
from .ai_agent import ai_agent

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
            anomaly_event=recommendation_data['anomaly_event'],
            recommended_action=recommendation_data['recommended_action'],
            explanation_text=recommendation_data['explanation_text'],
            confidence=recommendation_data['confidence']
        )
        
        print(f"✅ AI Recommendation generated for anomaly {instance.id}")
        print(f"   Action: {recommendation_data['recommended_action'][:50]}...")
        
    except Exception as e:
        print(f"❌ Error generating AI recommendation: {e}")