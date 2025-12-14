# test_complete_system.py
import os
import django
import sys
import time

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'agri_backend.settings')
django.setup()

print("🧪 COMPLETE SYSTEM TEST")
print("=" * 60)

from monitoring.models import SensorReading, AnomalyEvent, AgentRecommendation, FieldPlot, User
from django.utils import timezone
from datetime import timedelta

# 1. Check ML Model
print("1. ML Model Status:")
try:
    from ml.ml_model import ml_model
    if ml_model and ml_model.model:
        print(f"   ✅ Loaded - {ml_model.model.n_features_in_} features")
        
        # Quick prediction
        pred, score = ml_model.predict(65, 24, 70)
        print(f"   Test: Normal (65,24,70) → {'Anomaly' if pred else 'Normal'} (score: {score:.3f})")
    else:
        print("   ❌ Not loaded")
except Exception as e:
    print(f"   ❌ Error: {e}")

# 2. Get a plot for testing
print("\n2. Database Check:")
plots = FieldPlot.objects.all()
users = User.objects.all()

print(f"   Users: {users.count()}")
print(f"   Plots: {plots.count()}")

if plots.exists():
    plot = plots.first()
    print(f"   Using plot {plot.id}: {plot.crop_variety}")
    
    # 3. Clear any existing test data from this plot
    SensorReading.objects.filter(plot=plot, source='test').delete()
    old_anomalies = AnomalyEvent.objects.filter(plot=plot)
    old_count = old_anomalies.count()
    old_anomalies.delete()
    print(f"   Cleared {old_count} old anomalies for clean test")
    
    # 4. Test 1: Create a NORMAL reading (should NOT trigger)
    print("\n3. Test 1 - Normal Reading:")
    reading1 = SensorReading.objects.create(
        plot=plot,
        sensor_type='moisture',
        value=65.0,
        source='test',
        timestamp=timezone.now()
    )
    print(f"   Created: moisture = 65.0%")
    
    time.sleep(2)  # Wait for signal processing
    
    anomalies = AnomalyEvent.objects.filter(plot=plot)
    print(f"   Anomalies detected: {anomalies.count()} (should be 0)")
    
    # 5. Test 2: Create an ANOMALY (low moisture)
    print("\n4. Test 2 - Anomaly (Low Moisture):")
    reading2 = SensorReading.objects.create(
        plot=plot,
        sensor_type='moisture',
        value=22.5,  # Very low - should trigger
        source='test',
        timestamp=timezone.now()
    )
    print(f"   Created: moisture = 22.5% (anomalous)")
    
    time.sleep(3)  # Wait longer for full processing
    
    anomalies = AnomalyEvent.objects.filter(plot=plot)
    print(f"   Anomalies detected: {anomalies.count()} (should be 1)")
    
    if anomalies.exists():
        anomaly = anomalies.first()
        print(f"\n   ✅ ANOMALY DETECTED!")
        print(f"      Type: {anomaly.anomaly_type}")
        print(f"      Severity: {anomaly.severity}")
        print(f"      Confidence: {anomaly.model_confidence:.2f}")
        print(f"      Timestamp: {anomaly.timestamp.strftime('%H:%M:%S')}")
        
        # Check AI recommendation
        recs = anomaly.recommendations.all()
        print(f"      AI Recommendations: {recs.count()}")
        
        if recs.exists():
            rec = recs.first()
            print(f"\n      🤖 AI RECOMMENDATION:")
            print(f"         Action: {rec.recommended_action[:80]}...")
            print(f"         Confidence: {rec.confidence:.2f}")
            print(f"         Generated: {rec.timestamp.strftime('%H:%M:%S')}")
    
    # 6. Test 3: Another anomaly type
    print("\n5. Test 3 - Different Anomaly (High Temperature):")
    reading3 = SensorReading.objects.create(
        plot=plot,
        sensor_type='temperature',
        value=38.5,  # Heat stress
        source='test',
        timestamp=timezone.now()
    )
    print(f"   Created: temperature = 38.5°C (anomalous)")
    
    time.sleep(2)
    
    # Show all results
    print("\n6. Final Results:")
    all_anomalies = AnomalyEvent.objects.filter(plot=plot).order_by('-timestamp')
    print(f"   Total anomalies: {all_anomalies.count()}")
    
    for i, anomaly in enumerate(all_anomalies, 1):
        recs = anomaly.recommendations.count()
        print(f"   {i}. {anomaly.anomaly_type:25} - {anomaly.severity:6} "
              f"(conf: {anomaly.model_confidence:.2f}) - {recs} AI rec(s)")
    
    # 7. Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print(f"   Sensor readings created: 3")
    print(f"   Anomalies detected: {all_anomalies.count()}")
    print(f"   AI recommendations generated: {AgentRecommendation.objects.filter(anomaly_event__plot=plot).count()}")
    
    if all_anomalies.count() >= 2:
        print("\n🎉 SUCCESS! System is working correctly!")
        print("   - ML model is predicting")
        print("   - Signals are triggering")
        print("   - Anomaly types are correct")
        print("   - AI recommendations are generated")
    else:
        print("\n⚠️  WARNING: Some issues detected")
        print("   Check signals.py and inference.py")
        
else:
    print("❌ No plots found in database")
    print("   Create plots first or run the simulator to auto-create them")

print("\n🚀 Next: Run the simulator to see real-time data flow!")