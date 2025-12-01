# ml/management/commands/train_model.py - VERSION SIMPLE
from django.core.management.base import BaseCommand
import numpy as np
from sklearn.ensemble import IsolationForest
import joblib
import os

class Command(BaseCommand):
    help = 'Train a simple Isolation Forest model'
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🚀 Training ML model...'))
        
        # Simple dataset
        np.random.seed(42)
        n_samples = 1000
        
        X = np.column_stack([
            np.random.normal(60, 5, n_samples),   # Moisture
            np.random.normal(24, 3, n_samples),   # Temperature
            np.random.normal(65, 8, n_samples)    # Humidity
        ])
        
        # Train
        model = IsolationForest(
            n_estimators=100,
            contamination=0.1,
            random_state=42
        )
        
        model.fit(X)
        
        # Save
        os.makedirs('models', exist_ok=True)
        model_path = 'models/isolation_forest.pkl'
        joblib.dump(model, model_path)
        
        self.stdout.write(self.style.SUCCESS(f'✅ Model saved: {model_path}'))
        
        # Quick test
        self.stdout.write("\n🧪 Quick test:")
        tests = [
            ([65, 24, 65], "Normal"),
            ([25, 24, 65], "Water stress"),
        ]
        
        for features, label in tests:
            pred = model.predict([features])[0]
            status = "ANOMALY" if pred == -1 else "Normal"
            self.stdout.write(f"   {label}: {status}")