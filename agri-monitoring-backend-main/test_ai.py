"""
Test complet de l'agent IA Agri-Monitoring
Teste l'agent existant dans monitoring/ai_agent.py
"""
import os
import sys
import django
from datetime import datetime

# Configuration Django
project_path = r'C:\Users\semyz\agri-monitoring-backend\agri-monitoring-backend-main'
sys.path.append(project_path)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'agri_backend.settings')

try:
    django.setup()
    print("✅ Django setup successful")
except Exception as e:
    print(f"❌ Django setup failed: {e}")
    sys.exit(1)

def get_ai_agent():
    from monitoring.ai_agent import ai_agent, AgricultureAI
    # Ensure ai_agent is initialized properly
    if ai_agent is None or not isinstance(ai_agent, AgricultureAI):
        print("⚠️ ai_agent not initialized. Creating new AgricultureAI instance...")
        ai_agent_instance = AgricultureAI()
        return ai_agent_instance
    return ai_agent  # <- return the existing instance, not the class


def test_ai_agent_direct():
    """Test direct analysis on mock anomalies"""
    print("\n" + "="*60)
    print("🤖 TEST AI AGENT DIRECT")
    print("="*60)
    
    ai_agent_instance = get_ai_agent()
    
    test_anomalies = [
        {'type': 'soil_moisture_low', 'severity': 'high', 'confidence': 0.9},
        {'type': 'temperature_high', 'severity': 'medium', 'confidence': 0.85},
        {'type': 'humidity_high', 'severity': 'low', 'confidence': 0.8},
        {'type': 'unknown_anomaly', 'severity': 'medium', 'confidence': 0.7}
    ]
    
    for i, anomaly_data in enumerate(test_anomalies, 1):
        class MockAnomaly:
            def __init__(self, data, id_):
                self.id = id_  # Add an id attribute
                self.anomaly_type = data['type']
                self.severity = data['severity']
                self.confidence = data['confidence']
                self.plot = type('obj', (object,), {'id': id_})()
                self.timestamp = getattr(data, 'timestamp', datetime.now())
        
        mock_anomaly = MockAnomaly(anomaly_data,i)
        
        mock_sensor_data = [
            {'sensor_type': 'moisture', 'value': 65.0},
            {'sensor_type': 'temperature', 'value': 24.0},
            {'sensor_type': 'humidity', 'value': 55.0},
        ]
        
        if hasattr(ai_agent_instance, 'analyze_anomaly'):
            result = ai_agent_instance.analyze_anomaly(mock_anomaly, mock_sensor_data)
        else:
            result = ai_agent_instance.generate_recommendation(mock_anomaly)
        
        print(f"\n   Test {i}: {anomaly_data['type']} ({anomaly_data['severity']})")
        print(f"   • Action: {result.get('recommended_action', '')[:80]}...")
        print(f"   • Confidence: {result.get('confidence', 0):.2f}")



def main():
    print("="*60)
    print("🧪 AGRI-MONITORING AI TEST SUITE")
    print("="*60)
    
    print("\nOptions:")
    print("1. Test AI Agent Directly")
    print("2. Exit")
    
    while True:
        choice = input("\nYour choice [1]: ").strip() or "1"
        
        if choice == "1":
            test_ai_agent_direct()
        elif choice == "2":
            print("\n👋 Goodbye!")
            break
        else:
            print("❌ Invalid choice")

if __name__ == "__main__":
    main()
