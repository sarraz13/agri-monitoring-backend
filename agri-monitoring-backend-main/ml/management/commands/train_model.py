# ml/management/commands/train_model.py - IMPROVED VERSION
from django.core.management.base import BaseCommand
import numpy as np
from sklearn.ensemble import IsolationForest
import joblib
import os

class Command(BaseCommand):
    help = 'Train Isolation Forest model with realistic anomalies'
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🚀 Training IMPROVED ML model...'))
        
        # ==================== 1. CREATE REALISTIC DATASET ====================
        np.random.seed(42)
        
        # Normal data (80% of dataset)
        n_normal = 800
        X_normal = np.column_stack([
            np.random.normal(60, 5, n_normal),    # Moisture: centered at 60%
            np.random.normal(24, 3, n_normal),    # Temperature: centered at 24°C
            np.random.normal(65, 8, n_normal)     # Humidity: centered at 65%
        ])
        
        # ==================== 2. CREATE REAL ANOMALIES (20% of dataset) ====================
        n_anomaly = 200
        
        # Type 1: Low moisture (drought/irrigation failure)
        anomaly_low_moisture = np.column_stack([
            np.random.uniform(20, 40, n_anomaly//4),     # Moisture 20-40%
            np.random.normal(24, 3, n_anomaly//4),       # Normal temp
            np.random.normal(65, 8, n_anomaly//4)        # Normal humidity
        ])
        
        # Type 2: High temperature (heat stress)
        anomaly_high_temp = np.column_stack([
            np.random.normal(60, 5, n_anomaly//4),       # Normal moisture
            np.random.uniform(32, 40, n_anomaly//4),     # Temp 32-40°C
            np.random.normal(65, 8, n_anomaly//4)        # Normal humidity
        ])
        
        # Type 3: Low humidity (dry air)
        anomaly_low_humidity = np.column_stack([
            np.random.normal(60, 5, n_anomaly//4),       # Normal moisture
            np.random.normal(24, 3, n_anomaly//4),       # Normal temp
            np.random.uniform(20, 40, n_anomaly//4)      # Humidity 20-40%
        ])
        
        # Type 4: Multiple anomalies (worst case)
        anomaly_multiple = np.column_stack([
            np.random.uniform(20, 40, n_anomaly//4),     # Low moisture
            np.random.uniform(32, 40, n_anomaly//4),     # High temp
            np.random.uniform(20, 40, n_anomaly//4)      # Low humidity
        ])
        
        # Combine all anomalies
        X_anomaly = np.vstack([
            anomaly_low_moisture,
            anomaly_high_temp,
            anomaly_low_humidity,
            anomaly_multiple
        ])
        
        # ==================== 3. COMBINE AND SHUFFLE ====================
        X_train = np.vstack([X_normal, X_anomaly])
        np.random.shuffle(X_train)  # Important: shuffle the data
        
        self.stdout.write(self.style.SUCCESS(f'📊 Dataset created:'))
        self.stdout.write(f'   Total samples: {X_train.shape[0]}')
        self.stdout.write(f'   Normal samples: {n_normal}')
        self.stdout.write(f'   Anomaly samples: {n_anomaly}')
        self.stdout.write(f'   Feature dimensions: {X_train.shape[1]}')
        
        # ==================== 4. TRAIN MODEL ====================
        self.stdout.write(self.style.SUCCESS('🤖 Training Isolation Forest...'))
        
        # Set contamination to actual anomaly ratio (0.2 = 20%)
        model = IsolationForest(
            n_estimators=150,           # More trees for better accuracy
            contamination=0.2,          # ACTUAL anomaly ratio in training data
            max_samples='auto',
            bootstrap=False,
            n_jobs=-1,                  # Use all CPU cores
            random_state=42,
            verbose=0
        )
        
        model.fit(X_train)
        
        # ==================== 5. SAVE MODEL ====================
        os.makedirs('models', exist_ok=True)
        model_path = 'models/isolation_forest.pkl'
        joblib.dump(model, model_path)
        
        self.stdout.write(self.style.SUCCESS(f'✅ Model saved: {model_path}'))
        self.stdout.write(f'   Model parameters:')
        self.stdout.write(f'   - n_estimators: {model.n_estimators}')
        self.stdout.write(f'   - Features: {model.n_features_in_}')
        self.stdout.write(f'   - Contamination: {model.contamination}')
        
        # ==================== 6. COMPREHENSIVE TEST ====================
        self.stdout.write(self.style.SUCCESS('\n🧪 COMPREHENSIVE TEST:'))
        
        test_cases = [
            # Format: [moisture, temperature, humidity], description, expected
            ([65, 24, 70], "Normal conditions", "Normal"),
            ([55, 22, 60], "Normal (slightly low)", "Normal"),
            ([70, 26, 75], "Normal (slightly high)", "Normal"),
            ([25, 24, 70], "Water stress", "ANOMALY"),
            ([15, 24, 70], "Severe drought", "ANOMALY"),
            ([65, 35, 70], "Heat stress", "ANOMALY"),
            ([65, 40, 70], "Extreme heat", "ANOMALY"),
            ([65, 24, 25], "Dry air", "ANOMALY"),
            ([65, 24, 15], "Extremely dry", "ANOMALY"),
            ([25, 35, 25], "Multiple stresses", "ANOMALY"),
            ([80, 24, 70], "High moisture", "Normal"),  # Might be normal or anomaly
            ([65, 10, 70], "Cold stress", "ANOMALY"),
        ]
        
        correct = 0
        total = len(test_cases)
        
        for features, description, expected in test_cases:
            prediction = model.predict([features])[0]
            score = model.decision_function([features])[0]
            
            actual = "ANOMALY" if prediction == -1 else "Normal"
            match = "✓" if actual == expected else "✗"
            
            if match == "✓":
                correct += 1
            
            self.stdout.write(f'   {match} {description:25} → {actual:8} '
                            f'(score: {score:7.3f}) [Expected: {expected}]')
        
        accuracy = (correct / total) * 100
        self.stdout.write(self.style.SUCCESS(f'\n📈 Test Accuracy: {accuracy:.1f}% ({correct}/{total})'))
        
        # ==================== 7. THRESHOLD ANALYSIS ====================
        self.stdout.write(self.style.SUCCESS('\n📊 Threshold Analysis:'))
        
        # Generate decision scores for normal vs anomaly
        normal_scores = model.decision_function(X_normal[:50])  # Sample of normal
        anomaly_scores = model.decision_function(X_anomaly[:50])  # Sample of anomalies
        
        self.stdout.write(f'   Normal scores range:   {normal_scores.min():.3f} to {normal_scores.max():.3f}')
        self.stdout.write(f'   Anomaly scores range:  {anomaly_scores.min():.3f} to {anomaly_scores.max():.3f}')
        
        # Suggest a manual threshold (more negative = more anomalous)
        suggested_threshold = (normal_scores.min() + anomaly_scores.max()) / 2
        self.stdout.write(f'   Suggested threshold:   {suggested_threshold:.3f}')
        self.stdout.write(f'   (Scores < {suggested_threshold:.3f} = anomaly)')
        
        # ==================== 8. VALIDATE WITH YOUR CLASSIFICATION LOGIC ====================
        self.stdout.write(self.style.SUCCESS('\n🔗 Compatibility Check with Your Classification:'))
        
        # Import your classifier to ensure consistency
        try:
            from ml.inference import AnomalyDetector
            
            detector = AnomalyDetector()
            
            compatibility_tests = [
                ([25, 24, 70], "soil_moisture_low"),
                ([65, 38, 70], "temperature_high"),
                ([65, 24, 25], "humidity_low"),
                ([75, 24, 70], "normal"),
            ]
            
            self.stdout.write(f'   Comparing ML model with your classify_anomaly() logic:')
            
            for features, expected_type in compatibility_tests:
                # Your classification
                your_type = detector.classify_anomaly(*features)
                
                # ML prediction
                ml_pred = model.predict([features])[0]
                ml_type = "ANOMALY" if ml_pred == -1 else "normal"
                
                match = "✓" if (ml_type == "ANOMALY") == (your_type != "unknown") else "✗"
                
                self.stdout.write(f'   {match} [{features}] → Your: {your_type:20} | ML: {ml_type:8}')
                
        except ImportError:
            self.stdout.write(self.style.WARNING('   ⚠️ Could not import AnomalyDetector for compatibility check'))
        
        self.stdout.write(self.style.SUCCESS('\n🎉 Training complete! Model ready for use.'))
        self.stdout.write('\n💡 Next steps:')
        self.stdout.write('   1. Restart Django server to load new model')
        self.stdout.write('   2. Test with: python manage.py shell')
        self.stdout.write('   3. Run simulator to generate real data')