"""
Simulateur agricole avec authentification JWT
Envoyé de données aux API Django
"""
import requests
import random
import time
from datetime import timedelta
from django.utils import timezone

class AgriSimulator:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.token = None
        self.plots = [1, 2, 3]  # IDs des parcelles par défaut
        
    def login(self, username="sarra", password="sarour1234"):
        """Authentification JWT"""
        try:
            response = requests.post(
                f"{self.base_url}/api/auth/login/",
                json={"username": username, "password": password},
                timeout=5
            )
            
            if response.status_code == 200:
                self.token = response.json()['access']
                print(f"✅ Authentifié: {username}")
                return True
                
        except requests.exceptions.ConnectionError:
            print("❌ Impossible de se connecter au serveur")
        except Exception as e:
            print(f"❌ Erreur: {e}")
            
        return False
    
    def generate_sensor_value(self, sensor_type):
        """Génère une valeur réaliste selon le type de capteur"""
        ranges = {
            "moisture": (45, 75),      # Humidité sol normale
            "temperature": (18, 28),   # Température normale
            "humidity": (45, 75)       # Humidité air normale
        }
        min_val, max_val = ranges.get(sensor_type, (0, 100))
        return round(random.uniform(min_val, max_val), 2)
    
    def send_reading(self, plot_id, sensor_type, value=None):
        """Envoie une lecture unique"""
        if value is None:
            value = self.generate_sensor_value(sensor_type)
        
        data = {
            "plot": plot_id,
            "sensor_type": sensor_type,
            "value": value,
            "timestamp": timezone.now().isoformat(),
            "source": "agri_simulator"
        }
        
        headers = {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json'
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/api/sensor-readings/",
                json=data,
                headers=headers,
                timeout=5
            )
            return response.status_code in [200, 201]
        except Exception:
            return False
    
    def quick_test(self, count=3):
        """Test rapide"""
        if not self.login():
            return False
        
        print(f"\n🧪 Test ({count} lectures par parcelle)...")
        success = 0
        total = len(self.plots) * 3  # 3 capteurs par parcelle
        
        for plot_id in self.plots:
            for sensor in ["moisture", "temperature", "humidity"]:
                if self.send_reading(plot_id, sensor):
                    success += 1
                time.sleep(0.3)  # Petit délai
        
        print(f"✅ {success}/{total} lectures envoyées")
        return success > 0
    
    def run_simulation(self, duration_minutes=2):
        """Simulation continue"""
        if not self.login():
            return
        
        print(f"\n🚀 Simulation ({duration_minutes} minutes)...")
        end_time = timezone.now() + timedelta(minutes=duration_minutes)
        count = 0
        
        try:
            while timezone.now() < end_time:
                for plot_id in self.plots:
                    for sensor in ["moisture", "temperature", "humidity"]:
                        if self.send_reading(plot_id, sensor):
                            count += 1
                
                if count % 9 == 0:  # Log tous les cycles complets
                    print(f"   📊 {count} lectures...")
                
                time.sleep(10)  # Nouveau cycle toutes les 10s
                
        except KeyboardInterrupt:
            print("\n⏹️ Arrêt manuel")
        
        print(f"\n✅ Simulation terminée: {count} lectures")
        return count
    
    def inject_anomaly(self, plot_id=1, moisture=25, temp=32, humidity=35):
        """Injecte une anomalie spécifique (test ML)"""
        if not self.login():
            return False
        
        print(f"\n⚠️  Injection anomalie (Parcelle {plot_id})...")
        
        sensors = [
            ("moisture", moisture),
            ("temperature", temp),
            ("humidity", humidity)
        ]
        
        success = 0
        for sensor_type, value in sensors:
            if self.send_reading(plot_id, sensor_type, value):
                success += 1
            time.sleep(0.5)
        
        if success == 3:
            print(f"✅ Anomalie injectée: {moisture}% sol, {temp}°C, {humidity}% air")
        else:
            print("❌ Échec injection anomalie")
        
        return success == 3

def main():
    """Menu principal"""
    print("="*50)
    print("🌾 SIMULATEUR AGRI-MONITORING")
    print("="*50)
    
    simulator = AgriSimulator()
    
    print("\nOptions:")
    print("1. Test rapide (9 lectures)")
    print("2. Simulation continue (2 min)")
    print("3. Injecter anomalie test")
    print("4. Test connexion seulement")
    
    choice = input("\nChoix [1]: ").strip() or "1"
    
    if choice == "1":
        simulator.quick_test()
    elif choice == "2":
        simulator.run_simulation()
    elif choice == "3":
        simulator.inject_anomaly()
    elif choice == "4":
        simulator.login()
    else:
        print("❌ Option invalide")

if __name__ == "__main__":
    main()