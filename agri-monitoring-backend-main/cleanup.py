# cleanup_normal.py
import os
import sys
import django

# ==================== SETUP DJANGO ====================
# Fix the path issue
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_dir)

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'agri_backend.settings')

try:
    django.setup()
    print("✅ Django configured successfully")
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)

# ==================== NOW IMPORT MODELS ====================
from monitoring.models import AnomalyEvent, AgentRecommendation

# ==================== DELETE NORMAL ANOMALIES ====================
print("🔍 Looking for anomalies with type 'normal'...")

# Find all anomalies with type 'normal'
normal_anomalies = AnomalyEvent.objects.filter(anomaly_type='normal')
count = normal_anomalies.count()

if count == 0:
    print("✅ No 'normal' anomalies found. Nothing to delete.")
    sys.exit(0)

print(f"📊 Found {count} anomalies with type 'normal'")

# Show a few examples
print("\n📝 Sample of 'normal' anomalies to delete:")
for anomaly in normal_anomalies[:3]:  # Show first 3
    print(f"  ID {anomaly.id}: Plot {anomaly.plot_id}, {anomaly.timestamp}")

# Count associated recommendations
recommendation_count = AgentRecommendation.objects.filter(
    anomaly_event__in=normal_anomalies
).count()

print(f"\n📝 Also found {recommendation_count} associated recommendations")

# Ask for confirmation
print("\n⚠️  WARNING: This will permanently delete data!")
response = input(f"Delete {count} 'normal' anomalies? (yes/no): ")

if response.lower() == 'yes':
    # Delete them (cascades to recommendations automatically)
    deleted = normal_anomalies.delete()
    
    print(f"\n✅ DELETED {count} 'normal' anomalies")
    print(f"✅ Also deleted {recommendation_count} recommendations")
    
    # Verify deletion
    remaining = AnomalyEvent.objects.filter(anomaly_type='normal').count()
    print(f"\n📊 Verification: {remaining} 'normal' anomalies remaining")
    
else:
    print("\n❌ Cancelled. No data was deleted.")

print("\n✅ Done!")