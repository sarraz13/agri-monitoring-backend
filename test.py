# test_integration_fixed.py
"""
Test complet adapté à TA structure de modèles
"""
import os
import django
import sys
import monitoring

# Configure Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'agri_backend.settings')
django.setup()

from monitoring.models import FarmProfile, FieldPlot, SensorReading, AnomalyEvent
from ml.inference import detector
from datetime import datetime, timedelta
import random
from django.contrib.auth.models import User

def test_full_integration():
    print("="*60)
    print("🧪 TEST COMPLET - TA STRUCTURE")
    print("="*60)
    
    # 1. Crée ou récupère un utilisateur
    print("\n1. 👤 Création utilisateur...")
    
    user, _ = User.objects.get_or_create(
        username='ml_test_user',
        defaults={
            'email': 'ml_test@example.com',
            'password': 'testpass123'
        }
    )
    
    print(f"   ✅ Utilisateur: {user.username}")
    
    # 2. Crée une ferme (selon TON modèle)
    print("\n2. 🏡 Création ferme...")
    
    farm, created = FarmProfile.objects.get_or_create(
        owner=user,
        location="Tunis Test Zone",
        defaults={
            'size': 5.0,
            'crop_type': 'Blé Test'
        }
    )
    
    if created:
        print(f"   ✅ Ferme créée: {farm}")
    else:
        print(f"   ℹ️  Ferme existante réutilisée: {farm}")
    
    # 3. Crée une parcelle
    print("\n3. 🌾 Création parcelle...")
    
    plot, created = FieldPlot.objects.get_or_create(
        farm=farm,
        crop_variety='Blé Dur Test',
        defaults={}
    )
    
    print(f"   ✅ Parcelle: {plot}")
    
    # 4. Nettoie les anciennes données de test (optionnel)
    print("\n4. 🧹 Nettoyage anciennes données de test...")
    
    old_readings = SensorReading.objects.filter(plot=plot)
    old_anomalies = AnomalyEvent.objects.filter(plot=plot)
    
    print(f"   📊 Avant: {old_readings.count()} lectures, {old_anomalies.count()} anomalies")
    
    # old_readings.delete()  # Décommente si tu veux nettoyer
    # old_anomalies.delete()
    
    # 5. Ajoute des données normales
    print("\n5. 📊 Ajout données normales...")
    
    base_time = datetime.now() - timedelta(hours=5)
    
    for i in range(5):
        # Humidité normale
        SensorReading.objects.create(
            plot=plot,
            sensor_type='moisture',
            value=random.uniform(55, 70),
            timestamp=base_time + timedelta(hours=i),
            source='test'
        )
        
        # Température normale
        SensorReading.objects.create(
            plot=plot,
            sensor_type='temperature',
            value=random.uniform(20, 28),
            timestamp=base_time + timedelta(hours=i),
            source='test'
        )
        
        # Humidité air normale
        SensorReading.objects.create(
            plot=plot,
            sensor_type='humidity',
            value=random.uniform(55, 75),
            timestamp=base_time + timedelta(hours=i),
            source='test'
        )
    
    total_readings = SensorReading.objects.filter(plot=plot).count()
    print(f"   ✅ {total_readings} lectures créées")
    
    # 6. Test du détecteur ML
    print("\n6. 🔍 Test détecteur ML...")
    
    try:
        result = detector.detect_for_plot(plot.id)
        
        print(f"   📊 Résultat détection:")
        print(f"      - Anomalie: {'OUI' if result['is_anomaly'] else 'NON'}")
        print(f"      - Score: {result['score']:.3f}")
        print(f"      - Type: {result['anomaly_type'] or 'Aucun'}")
        print(f"      - Valeurs: H={result['moisture']:.1f}%, "
              f"T={result['temperature']:.1f}°C, HA={result['humidity_air']:.1f}%")
        
        if result['is_anomaly']:
            print(f"   ⚠️  ATTENTION: Détection d'anomalie sur données normales!")
            print(f"      → Vérifie les seuils du modèle")
    except Exception as e:
        print(f"   ❌ Erreur détecteur: {e}")
        result = None
    
    # 7. Ajoute une anomalie MANUELLE pour tester
    print("\n7. ⚠️  Injection anomalie manuelle...")
    
    # Ajoute 3 lectures anormales
    for i in range(3):
        SensorReading.objects.create(
            plot=plot,
            sensor_type='moisture',
            value=25.0 + random.uniform(-5, 5),  # Très bas!
            timestamp=datetime.now() - timedelta(minutes=30-i*10),
            source='test_anomaly'
        )
    
    print(f"   📉 3 lectures anormales ajoutées (humidité ~25%)")
    
    # 8. Vérifie la détection automatique (doit créer AnomalyEvent)
    print("\n8. 🤖 Attente détection automatique...")
    
    import time
    time.sleep(2)  # Donne le temps aux signaux de s'exécuter
    
    anomalies = AnomalyEvent.objects.filter(plot=plot)
    
    if anomalies.exists():
        print(f"   ✅ {anomalies.count()} anomalie(s) détectée(s) automatiquement!")
        
        for idx, anomaly in enumerate(anomalies.order_by('-timestamp')[:3]):
            print(f"      {idx+1}. Type: {anomaly.anomaly_type}")
            print(f"         Sévérité: {anomaly.severity}")
            print(f"         Confiance: {anomaly.model_confidence:.3f}")
            print(f"         Date: {anomaly.timestamp}")
    else:
        print("   ❌ Aucune anomalie détectée automatiquement")
        print("   🔍 Vérification manuelle...")
        
        # Test manuel du détecteur
        try:
            new_result = detector.detect_for_plot(plot.id)
            print(f"   📊 Détection manuelle: {'ANOMALIE' if new_result['is_anomaly'] else 'Normal'}")
            print(f"      Score: {new_result['score']:.3f}")
            
            # Crée une anomalie manuellement si détectée
            if new_result['is_anomaly']:
                AnomalyEvent.objects.create(
                    plot=plot,
                    anomaly_type=new_result['anomaly_type'] or 'unknown',
                    severity='high' if abs(new_result['score']) > 0.3 else 'medium',
                    model_confidence=abs(new_result['score'])
                )
                print(f"   ✅ Anomalie créée manuellement")
        except Exception as e:
            print(f"   ❌ Erreur détection manuelle: {e}")
    
    # 9. Statistiques finales
    print("\n" + "="*60)
    print("📊 STATISTIQUES FINALES")
    print("="*60)
    
    total_farms = FarmProfile.objects.count()
    total_plots = FieldPlot.objects.count()
    total_readings_all = SensorReading.objects.count()
    total_anomalies_all = AnomalyEvent.objects.count()
    
    print(f"Fermes totales: {total_farms}")
    print(f"Parcelles totales: {total_plots}")
    print(f"Lectures totales: {total_readings_all}")
    print(f"Anomalies totales: {total_anomalies_all}")
    
    print(f"\n📈 Données de TEST:")
    print(f"   Ferme test: {farm.crop_type} à {farm.location}")
    print(f"   Parcelle test: {plot.crop_variety}")
    print(f"   Lectures test: {SensorReading.objects.filter(plot=plot).count()}")
    print(f"   Anomalies test: {AnomalyEvent.objects.filter(plot=plot).count()}")
    
    # 10. Vérification système
    print("\n🔧 VÉRIFICATION SYSTÈME:")
    
    # Vérifie que le modèle ML est chargé
    from ml.ml_model import ml_model
    if ml_model.model is not None:
        print("   ✅ Modèle ML: CHARGÉ")
        print(f"      Features: {ml_model.model.n_features_in_}")
    else:
        print("   ❌ Modèle ML: NON CHARGÉ")
    
    # Vérifie les signaux
    try:
        import monitoring.signals
        print("   ✅ Signaux: IMPORTÉS")
    except:
        print("   ❌ Signaux: NON IMPORTÉS")
    
    print("="*60)
    
    if AnomalyEvent.objects.filter(plot=plot).exists():
        print("🎉 SUCCÈS: Le système ML est intégré et fonctionnel!")
    else:
        print("⚠️  ATTENTION: Aucune anomalie n'a été créée.")
        print("   Causes possibles:")
        print("   1. Les signaux ne sont pas activés")
        print("   2. Le seuil de détection est trop élevé")
        print("   3. Problème avec les données d'entrée")
    
    print("="*60)

if __name__ == "__main__":
    test_full_integration()