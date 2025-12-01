# ml/management/commands/train_model.py - VERSION SIMPLIFIÉE
from django.core.management.base import BaseCommand
from ml.ml_model import MLModel

class Command(BaseCommand):
    help = 'Entraîne le modèle Isolation Forest pour la détection d\'anomalies'
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🚀 Début de l\'entraînement du modèle ML...'))
        
        # Crée une instance et entraîne
        model_instance = MLModel()
        model_instance.train()
        
        self.stdout.write(self.style.SUCCESS('✅ Modèle entraîné et sauvegardé avec succès!'))
        
        # Test rapide
        self.stdout.write("\n🧪 Test rapide:")
        
        test_cases = [
            (65, 24, 70, "Normal"),
            (25, 24, 70, "Anomalie humidité"),
            (65, 36, 70, "Anomalie température"),
        ]
        
        for m, t, h, label in test_cases:
            is_anomaly, score = model_instance.predict(m, t, h)
            if is_anomaly:
                self.stdout.write(self.style.ERROR(f'   {label}: ANOMALIE (score: {score:.3f})'))
            else:
                self.stdout.write(self.style.SUCCESS(f'   {label}: Normal (score: {score:.3f})'))