from django.core.management.base import BaseCommand # Django command framework
import numpy as np
from sklearn.ensemble import IsolationForest # ML algorithm
import joblib # Save/load models
import os  # File operations (pkl)

"""
ML MODEL TRAINING SCRIPT
Django management command to train the Isolation Forest anomaly detection model.
Run with: python manage.py train_model
"""

class Command(BaseCommand):
    """
    Custom Django management command for training ML models.
    Inherits from BaseCommand to integrate with Django's command system.
    """
    help = 'Train Isolation Forest model with realistic anomalies' #description taa l commande
    
    def handle(self, *args, **options): #Main method called when command is executed.
        self.stdout.write(self.style.SUCCESS('Training ML model:'))
        
        # 1.dataset synthetic li bch netrainiw bih el model (mch mel readings taa db)
        np.random.seed(42)# Set random seed for reproducibility
        # Normal data (80% of dataset)
        n_normal = 800
        X_normal = np.column_stack([
            np.random.normal(60, 5, n_normal),    # Moisture: centered at 60% ±5%
            np.random.normal(24, 3, n_normal),    # Temperature: centered at 24°C ±3°
            np.random.normal(65, 8, n_normal)     # Humidity: centered at 65% ±8%
        ])
        
        #2. creation d'anomalies  (20% mel dataset)
        n_anomaly = 200
        
        # Type 1: Low moisture (drought/irrigation failure)
        anomaly_low_moisture = np.column_stack([
            np.random.uniform(20, 40, n_anomaly//4),     # Moisture 20-40% (lowww)
            np.random.normal(24, 3, n_anomaly//4),       # Normal temp
            np.random.normal(65, 8, n_anomaly//4)        # Normal humidity
        ])
        
        # Type 2: High temperature (heat stress)
        anomaly_high_temp = np.column_stack([
            np.random.normal(60, 5, n_anomaly//4),       # Normal moisture
            np.random.uniform(32, 40, n_anomaly//4),     # Temp 32-40°C (too high)
            np.random.normal(65, 8, n_anomaly//4)        # Normal humidity
        ])
        
        # Type 3: Low humidity (dry air)
        anomaly_low_humidity = np.column_stack([
            np.random.normal(60, 5, n_anomaly//4),       # Normal moisture
            np.random.normal(24, 3, n_anomaly//4),       # Normal temp
            np.random.uniform(20, 40, n_anomaly//4)      # Humidity 20-40% (too low)
        ])
        
        # Type 4: Multiple anomalies (worst case : el parameters lkol khaybin)
        anomaly_multiple = np.column_stack([
            np.random.uniform(20, 40, n_anomaly//4),     # Low moisture
            np.random.uniform(32, 40, n_anomaly//4),     # High temp
            np.random.uniform(20, 40, n_anomaly//4)      # Low humidity
        ])
        
        # Combine all anomalies fi dataset wehed esmou X_anomaly
        X_anomaly = np.vstack([ # Stack vertically (add rows)
            anomaly_low_moisture,
            anomaly_high_temp,
            anomaly_low_humidity,
            anomaly_multiple
        ])
        
        #3. combiner el normal data wel anomalies fi dataset wehed w khalathom
        X_train = np.vstack([X_normal, X_anomaly]) #800 normal w 200 anomalies => 1000 samples 
        np.random.shuffle(X_train)  # Important: shuffle the data
        
        self.stdout.write(self.style.SUCCESS(f'Dataset created:'))
        self.stdout.write(f'   Total samples: {X_train.shape[0]}') #(1000,3) 1000 rows w 3 colonnes taa l features (mois,temp,hum)
        self.stdout.write(f'   Normal samples: {n_normal}')
        self.stdout.write(f'   Anomaly samples: {n_anomaly}')
        self.stdout.write(f'   Feature dimensions: {X_train.shape[1]}') #3 features
        
        #4.train model
        self.stdout.write(self.style.SUCCESS('Training Isolation Forest:'))
        
        # Isolation Forest parameters explained:
        # n_estimators=150: Number of trees (more = more accurate but slower)
        # contamination=0.2: Expected proportion of anomalies in data (20%)
        # max_samples='auto': Number of samples to draw for each tree
        # bootstrap=False: Don't sample with replacement
        # n_jobs=-1: Use all CPU cores
        # random_state=42: For reproducibility
        model = IsolationForest(
            n_estimators=150,           # More trees for better accuracy
            contamination=0.2,          # matches el anomaly ratio li aamelneh (20% anomalies)
            max_samples='auto',
            bootstrap=False,
            n_jobs=-1,                  # Use all CPU cores
            random_state=42,
            verbose=0
        )
        
        model.fit(X_train)# Train the model
        
        #5. save model 
        os.makedirs('models', exist_ok=True) # Create directory if doesn't exist
        model_path = 'models/isolation_forest.pkl'
        joblib.dump(model, model_path) #save model to file
        
        self.stdout.write(self.style.SUCCESS(f'Model saved: {model_path}'))
        self.stdout.write(f'   Model parameters:')
        self.stdout.write(f'   - n_estimators: {model.n_estimators}')
        self.stdout.write(f'   - Features: {model.n_features_in_}') #3
        self.stdout.write(f'   - Contamination: {model.contamination}')
        
        #6. test du modele
        self.stdout.write(self.style.SUCCESS('\nCOMPREHENSIVE TEST:'))
        
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
            prediction = model.predict([features])[0]  # -1 = anomaly, 1 = normal
            score = model.decision_function([features])[0] # Lower = more anomalous
            
            actual = "ANOMALY" if prediction == -1 else "Normal"
            match = "✓" if actual == expected else "✗"
            
            if match == "✓":
                correct += 1
            
            self.stdout.write(f'   {match} {description:25} → {actual:8} '
                            f'(score: {score:7.3f}) [Expected: {expected}]')
        
        accuracy = (correct / total) * 100
        self.stdout.write(self.style.SUCCESS(f'\nTest Accuracy: {accuracy:.1f}% ({correct}/{total})'))
        
        #7.Threshhold analysis
        self.stdout.write(self.style.SUCCESS('\nThreshold Analysis:'))
        
        # Generate decision scores for normal vs anomaly samples
        normal_scores = model.decision_function(X_normal[:50])  # First 50 normal samples
        anomaly_scores = model.decision_function(X_anomaly[:50])  # First 50 anomaly samples
        
        self.stdout.write(f'   Normal scores range:   {normal_scores.min():.3f} to {normal_scores.max():.3f}')
        self.stdout.write(f'   Anomaly scores range:  {anomaly_scores.min():.3f} to {anomaly_scores.max():.3f}')
        
        # Suggest a manual threshold (more negative = more anomalous)
        suggested_threshold = (normal_scores.min() + anomaly_scores.max()) / 2
        self.stdout.write(f'   Suggested threshold:   {suggested_threshold:.3f}')
        self.stdout.write(f'   (Scores < {suggested_threshold:.3f} = anomaly)')
        
        # 8. VALIDATE WITH YOUR CLASSIFICATION LOGIC
        self.stdout.write(self.style.SUCCESS('\nCompatibility Check with Your Classification:'))
        
        # Import your classifier to ensure consistency
        try:
            from ml.inference import AnomalyDetector
            detector = AnomalyDetector() # Rule-based detector
            compatibility_tests = [
                ([25, 24, 70], "soil_moisture_low"),
                ([65, 38, 70], "temperature_high"),
                ([65, 24, 25], "humidity_low"),
                ([75, 24, 70], "normal"),
            ]
            
            self.stdout.write(f'   Comparing ML model with your classify_anomaly() logic:')
            for features, expected_type in compatibility_tests:
                # Your rule-based classification
                your_type = detector.classify_anomaly(*features)
                
                # ML prediction
                ml_pred = model.predict([features])[0]
                ml_type = "ANOMALY" if ml_pred == -1 else "normal"
                # Check if both agree on anomaly/normal (not necessarily same type)
                match = "✓" if (ml_type == "ANOMALY") == (your_type != "unknown") else "✗"
                
                self.stdout.write(f'   {match} [{features}] → Your: {your_type:20} | ML: {ml_type:8}')
                
        except ImportError:
            self.stdout.write(self.style.WARNING(' Could not import AnomalyDetector for compatibility check'))
        
        self.stdout.write(self.style.SUCCESS('\nTraining complete! Model ready for use.'))
        self.stdout.write('\nNext steps:')
        self.stdout.write('   1. Restart Django server to load new model')
        self.stdout.write('   2. Test with: python manage.py shell')
        self.stdout.write('   3. Run simulator to generate real data')