import numpy as np
from sklearn.ensemble import IsolationForest
import joblib
import os

class MLModel:
    def __init__(self, model_path=None):
        if model_path is None:
            # Go up from ml/ to project root, then to models/
            BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.model_path = os.path.join(BASE_DIR, 'models', 'isolation_forest.pkl')
        else:
            self.model_path = model_path
        self.model = None
        self.load_model()

    def load_model(self):
        """Charge le modèle depuis le fichier"""
        try:
            if os.path.exists(self.model_path):
                self.model = joblib.load(self.model_path)
            else:
                print("⚠️  Modèle non trouvé. Entraînez avec: python manage.py train_model")
                self.model = None
        except Exception as e:
            print(f"❌ Erreur chargement modèle: {e}")
            self.model = None
    
    def train(self, save_path='isolation_forest.pkl'):
        print("🧠 Entraînement du modèle ML (3 features)...")
        np.random.seed(42)
        # 1. Données normales
        n_normal = 800
        X_normal = np.column_stack([
            np.random.normal(60, 5, n_normal),    # Humidité sol
            np.random.normal(24, 3, n_normal),    # Température
            np.random.normal(65, 8, n_normal)     # Humidité air
        ])
        # 2. Données anormales
        n_anomaly = 200
        X_anomaly = np.column_stack([
            np.random.uniform(20, 40, n_anomaly),    # Humidité basse
            np.random.uniform(32, 40, n_anomaly),    # Température haute
            np.random.uniform(20, 40, n_anomaly)     # Humidité air basse
        ])
        # 3. Combine
        X_train = np.vstack([X_normal, X_anomaly])
        np.random.shuffle(X_train)
        print(f"📊 Dataset: {X_train.shape[0]} échantillons")
        print(f"   Normales: {n_normal}, Anomalies: {n_anomaly}")
        # 4. Entraînement
        self.model = IsolationForest(
            n_estimators=100,
            contamination=0.2,
            random_state=42,
            n_jobs=-1
        )
        print("⏳ Entraînement...")
        self.model.fit(X_train)
        # 5. Sauvegarde
        os.makedirs(os.path.dirname(save_path) or '.', exist_ok=True)
        joblib.dump(self.model, save_path)
        print(f"✅ Modèle sauvegardé: {save_path}")
        print(f"   Features attendues: {self.model.n_features_in_}")
        # 6. Validation
        self._validate_model()
        return self.model
    
    def _validate_model(self):
        """Teste le modèle avec des cas connus"""
        if self.model is None:
            print("❌ Modèle non disponible pour validation")
            return
            
        test_cases = [
            ([65, 24, 70], "Normal"),
            ([25, 24, 70], "Anomalie humidité basse"),
            ([85, 24, 70], "Anomalie humidité haute"),
            ([65, 10, 70], "Anomalie température basse"),
            ([65, 36, 70], "Anomalie température haute"),
            ([65, 24, 25], "Anomalie humidité air basse"),
            ([25, 36, 25], "Anomalie multiple"),
        ]
        
        print("\n🧪 Validation du modèle:")
        for features, label in test_cases:
            try:
                pred = self.model.predict([features])[0]
                score = self.model.decision_function([features])[0]
                status = "ANOMALIE" if pred == -1 else "Normal"
                print(f"   {label:30} → {status:10} (score: {score:7.3f})")
            except Exception as e:
                print(f"   {label:30} → ERREUR: {e}")
    
    def predict(self, moisture, temperature, humidity_air):
        if self.model is None:
            # Fallback: seuils simples
            is_anomaly = (
                moisture < 35 or moisture > 85 or
                temperature < 10 or temperature > 35 or
                humidity_air < 30 or humidity_air > 90
            )
            return is_anomaly, -0.5 if is_anomaly else 0.5
        
        features = np.array([[moisture, temperature, humidity_air]])
        
        try:
            prediction = self.model.predict(features)[0]
            score = self.model.decision_function(features)[0]
            return (prediction == -1), float(score)
        except Exception as e:
            print(f"⚠️  Erreur prédiction: {e}")
            return False, 0.0

# Instance globale
ml_model = MLModel()