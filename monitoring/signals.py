# monitoring/signals.py
"""
Signaux pour la détection automatique d'anomalies
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta
import logging

from .models import SensorReading, AnomalyEvent
from ml.inference import detector

logger = logging.getLogger(__name__)

# Dictionnaire de mapping des scores vers sévérité
SEVERITY_MAP = {
    'high': (-1.0, -0.3),    # score <= -0.3
    'medium': (-0.3, -0.1),  # -0.3 < score <= -0.1
    'low': (-0.1, 0.0),      # -0.1 < score < 0
}

def get_severity_from_score(score):
    """Convertit un score d'anomalie en niveau de sévérité"""
    for severity, (min_score, max_score) in SEVERITY_MAP.items():
        if min_score <= score < max_score:
            return severity
    return 'low'  # default

def get_anomaly_type_from_features(moisture, temperature, humidity_air):
    """Détermine le type d'anomalie basé sur les valeurs"""
    anomalies = []
    
    if moisture < 35:
        anomalies.append('soil_moisture_low')
    elif moisture > 85:
        anomalies.append('soil_moisture_high')
    
    if temperature < 10:
        anomalies.append('temperature_low')
    elif temperature > 32:
        anomalies.append('temperature_high')
    
    if humidity_air < 30:
        anomalies.append('air_humidity_low')
    elif humidity_air > 90:
        anomalies.append('air_humidity_high')
    
    if not anomalies:
        return 'unknown'
    elif len(anomalies) == 1:
        return anomalies[0]
    else:
        return 'multiple_' + '_'.join(sorted(anomalies))

@receiver(post_save, sender=SensorReading)
def check_for_anomaly(sender, instance, created, **kwargs):
    """
    Vérifie les anomalies après chaque nouvelle lecture de capteur
    
    Logique:
    1. Se déclenche seulement pour les nouvelles lectures
    2. Vérifie les 3 types de capteurs principaux
    3. Utilise le détecteur ML pour évaluer
    4. Crée un AnomalyEvent si anomalie détectée
    """
    # Ne traite que les nouvelles lectures (pas les mises à jour)
    if not created:
        return
    
    # Seulement pour les capteurs principaux
    if instance.sensor_type not in ['moisture', 'temperature', 'humidity']:
        return
    
    logger.info(
        f"📡 Signal déclenché - Lecture #{instance.id}: "
        f"{instance.sensor_type}={instance.value} "
        f"(Parcelle #{instance.plot_id})"
    )
    
    try:
        # Attendre un peu pour permettre l'accumulation de données
        # (optionnel, mais utile pour avoir du contexte)
        plot_id = instance.plot.id
        
        # Utilise le détecteur pour cette parcelle
        result = detector.detect_for_plot(plot_id)
        
        logger.debug(
            f"🔍 Résultat détection parcelle {plot_id}: "
            f"anomalie={result['is_anomaly']}, score={result['score']:.3f}"
        )
        
        # Si anomalie détectée et score significatif
        if result['is_anomaly'] and result['score'] < -0.05:
            
            # Vérifie si une anomalie similaire existe déjà récemment
            # (pour éviter les doublons)
            time_threshold = timezone.now() - timedelta(minutes=30)
            recent_similar = AnomalyEvent.objects.filter(
                plot_id=plot_id,
                anomaly_type=result['anomaly_type'],
                timestamp__gte=time_threshold
            ).exists()
            
            if recent_similar:
                logger.info(
                    f"⚠️  Anomalie similaire déjà détectée récemment "
                    f"(parcelle {plot_id}, type: {result['anomaly_type']})"
                )
                return
            
            # Détermine le type d'anomalie
            anomaly_type = get_anomaly_type_from_features(
                result['moisture'],
                result['temperature'],
                result['humidity_air']
            )
            
            # Convertit le score en sévérité
            severity = get_severity_from_score(result['score'])
            
            # Crée l'événement d'anomalie
            anomaly = AnomalyEvent.objects.create(
                plot=instance.plot,
                anomaly_type=anomaly_type,
                severity=severity,
                model_confidence=abs(result['score'])
            )
            
            logger.warning(
                f"🚨 NOUVELLE ANOMALIE DÉTECTÉE! "
                f"ID: {anomaly.id}, "
                f"Parcelle: {plot_id}, "
                f"Type: {anomaly_type}, "
                f"Sévérité: {severity}, "
                f"Confiance: {abs(result['score']):.3f}, "
                f"Valeurs: H={result['moisture']:.1f}%, "
                f"T={result['temperature']:.1f}°C, "
                f"HA={result['humidity_air']:.1f}%"
            )
            
            # Pour debug: affiche aussi dans la console
            print(f"\n{'='*60}")
            print(f"🚨 ANOMALIE CRÉÉE AUTOMATIQUEMENT")
            print(f"{'='*60}")
            print(f"ID: {anomaly.id}")
            print(f"Parcelle: {plot_id} ({instance.plot.crop_variety})")
            print(f"Type: {anomaly_type}")
            print(f"Sévérité: {severity}")
            print(f"Confiance modèle: {abs(result['score']):.3f}")
            print(f"Détecté à: {anomaly.timestamp}")
            print(f"{'='*60}\n")
            
        elif not result['is_anomaly']:
            logger.debug(
                f"✅ Pas d'anomalie - Parcelle {plot_id}: "
                f"score={result['score']:.3f}"
            )
            
    except Exception as e:
        logger.error(
            f"❌ ERREUR dans le signal d'anomalie pour la lecture #{instance.id}: {e}",
            exc_info=True
        )
        # Pour debug
        print(f"❌ ERREUR signal: {e}")

# Signal supplémentaire: nettoyage périodique (optionnel)
@receiver(post_save, sender=SensorReading)
def cleanup_old_readings(sender, instance, created, **kwargs):
    """
    Nettoyage automatique des anciennes lectures
    (Garder seulement les 1000 dernières lectures par parcelle)
    """
    if not created:
        return
    
    # Exécuté seulement 1 fois sur 100 pour la performance
    import random
    if random.randint(1, 100) != 1:
        return
    
    try:
        from django.db.models import Count
        from datetime import timedelta
        
        # Garde seulement les lectures des 7 derniers jours
        # ou max 1000 lectures par parcelle
        time_limit = timezone.now() - timedelta(days=7)
        
        for plot in instance.plot.farm.plots.all():
            # Compte les lectures
            count = plot.sensor_readings.count()
            
            if count > 1000:
                # Trouve le timestamp de la 1000ème lecture
                thousandth = plot.sensor_readings.order_by('-timestamp')[999]
                old_readings = plot.sensor_readings.filter(
                    timestamp__lt=thousandth.timestamp
                )
                deleted_count, _ = old_readings.delete()
                
                logger.info(
                    f"Nettoyage automatique - Parcelle {plot.id}: "
                    f"supprimé {deleted_count} anciennes lectures"
                )
                
    except Exception as e:
        logger.error(f"❌ Erreur nettoyage: {e}")