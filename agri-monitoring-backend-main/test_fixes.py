# test_fix_verification.py
import os
import django
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'agri_backend.settings')
django.setup()

from monitoring.models import SensorReading, FieldPlot, FarmProfile, User, AnomalyEvent
from django.utils import timezone
import time

print("🧪 Testing the FIXED anomaly detection system...")
print("=" * 60)

# Get a plot
plot = FieldPlot.objects.first()
if not plot:
    # Create one
    user, _ = User.objects.get_or_create(username='test_user')
    farm, _ = FarmProfile.objects.get_or_create(
        owner=user,
        defaults={'location': 'Test', 'size': 10, 'crop_type': 'Wheat'}
    )
    plot, _ = FieldPlot.objects.get_or_create(
        farm=farm,
        defaults={'crop_variety': 'Test Wheat'}
    )

print(f"📊 Using plot {plot.id}")

# Clear any existing data for clean test
SensorReading.objects.filter(plot=plot).delete()
AnomalyEvent.objects.filter(plot=plot).delete()

# Test 1: Create a LOW moisture reading (should trigger)
print("\n1️⃣ Testing LOW moisture (25.0):")
reading1 = SensorReading.objects.create(
    plot=plot,
    sensor_type='moisture',
    value=25.0,
    source='test'
)
time.sleep(1)  # Let signal process

anomalies = AnomalyEvent.objects.filter(plot=plot)
print(f"   Anomalies found: {anomalies.count()}")
for a in anomalies:
    print(f"   - {a.anomaly_type} (severity: {a.severity})")

# Test 2: Create a HIGH temperature reading
print("\n2️⃣ Testing HIGH temperature (38.0):")
reading2 = SensorReading.objects.create(
    plot=plot,
    sensor_type='temperature',
    value=38.0,
    source='test'
)
time.sleep(1)

anomalies = AnomalyEvent.objects.filter(plot=plot)
print(f"   Total anomalies: {anomalies.count()}")
for a in anomalies:
    print(f"   - {a.anomaly_type}")

# Test 3: Create a LOW humidity reading
print("\n3️⃣ Testing LOW humidity (20.0):")
reading3 = SensorReading.objects.create(
    plot=plot,
    sensor_type='humidity',
    value=20.0,
    source='test'
)
time.sleep(1)

anomalies = AnomalyEvent.objects.filter(plot=plot)
print(f"   Total anomalies: {anomalies.count()}")
print("   All anomalies:")
for a in anomalies:
    print(f"   - {a.anomaly_type} at {a.timestamp.strftime('%H:%M:%S')}")

# Test 4: Normal reading (should NOT trigger)
print("\n4️⃣ Testing NORMAL reading (65.0):")
reading4 = SensorReading.objects.create(
    plot=plot,
    sensor_type='moisture',
    value=65.0,
    source='test'
)
time.sleep(1)

print("   No new anomalies should be created for normal reading")

print("\n" + "=" * 60)
print("✅ Test complete!")
print(f"📈 Total anomalies created: {AnomalyEvent.objects.filter(plot=plot).count()}")
print(f"💡 Total AI recommendations: {sum(a.recommendations.count() for a in AnomalyEvent.objects.filter(plot=plot))}")