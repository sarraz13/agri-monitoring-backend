import os
import django
import sys

# Configure Django FIRST
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'agri_backend.settings')
django.setup()  # ← DOIT ÊTRE AVANT les imports !

# MAINTENANT importe les models
from monitoring.models import SensorReading, AnomalyEvent, FieldPlot, FarmProfile
from django.contrib.auth.models import User

def cleanup_database():
    """Nettoie la base de données des données de test"""
    print("🧹 Nettoyage base de données...")
    print("-" * 50)
    
    # 1. Compte avant
    before_readings = SensorReading.objects.count()
    before_anomalies = AnomalyEvent.objects.count()
    before_users = User.objects.filter(username='demo_user').count()
    
    print(f"📊 AVANT:")
    print(f"  Lectures: {before_readings}")
    print(f"  Anomalies: {before_anomalies}")
    print(f"  Users demo: {before_users}")
    
    # 2. Supprime les données de test
    # Lectures avec sources de test
    test_sources = ['simulator', 'demo', 'test', 'anomaly', 'auto_test']
    
    deleted_count = 0
    for source in test_sources:
        deleted = SensorReading.objects.filter(source__icontains=source).delete()
        deleted_count += deleted[0]
    
    print(f"\n✅ {deleted_count} lectures de test supprimées")
    
    # 3. Supprime TOUTES les anomalies (elles sont toutes de test)
    deleted_anomalies = AnomalyEvent.objects.all().delete()
    print(f"✅ {deleted_anomalies[0]} anomalies supprimées")
    
    # 4. Supprime utilisateur demo (optionnel)
    deleted_users = User.objects.filter(username='demo_user').delete()
    if deleted_users[0] > 0:
        print(f"✅ {deleted_users[0]} utilisateur(s) demo supprimé(s)")
    
    # 5. Compte après
    print(f"\n📊 APRÈS:")
    print(f"  Lectures: {SensorReading.objects.count()}")
    print(f"  Anomalies: {AnomalyEvent.objects.count()}")
    
    # 6. Vérifie les fermes/parcelles de test
    demo_farms = FarmProfile.objects.filter(location__icontains='Demo')
    if demo_farms.exists():
        print(f"\n⚠️  {demo_farms.count()} ferme(s) demo trouvée(s)")
        print("   (Gardées pour la structure, pas de données)")
    
    print("\n🎉 Nettoyage terminé !")
    print("La base est prête pour une nouvelle démo propre.")

if __name__ == "__main__":
    cleanup_database()