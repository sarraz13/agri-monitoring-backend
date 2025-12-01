"""
Simulateur avec credentials corrects
"""
import requests
import random
import time
from datetime import datetime, timedelta

class CorrectSimulator:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.token = None
        
    def login(self):
        """Essayez plusieurs combinaisons"""
        credentials = [
            ("sarra", "sarour1234"),
            ("admin", "admin123"),
            ("admin", "password"),
            ("test", "test123")
        ]
        
        for username, password in credentials:
            print(f"🔐 Essai avec {username}...")
            
            try:
                response = requests.post(
                    f"{self.base_url}/api/auth/login/",
                    json={"username": username, "password": password},
                    timeout=5
                )
                
                if response.status_code == 200:
                    self.token = response.json()['access']
                    print(f"✅ Connecté en tant que {username}")
                    return True
                else:
                    print(f"   ❌ {response.status_code}")
                    
            except Exception as e:
                print(f"   ❌ Erreur: {e}")
        
        print("\n❌ Aucun login n'a fonctionné.")
        print("\n🎯 Créez un superuser:")
        print("   python manage.py createsuperuser")
        print("   → Username: admin")
        print("   → Password: admin123")
        return False
    
    def quick_test(self):
        """Test rapide"""
        print("\n🧪 Test rapide...")
        
        # 1. Test de connexion
        if not self.login():
            return
        
        # 2. Test envoi de données
        headers = {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json'
        }
        
        # Génère des données de test
        for i in range(3):
            data = {
                "timestamp": datetime.now().isoformat(),
                "plot": i + 1,  # Parcelle 1, 2, 3
                "sensor_type": "moisture",
                "value": round(random.uniform(45, 75), 2),
                "source": "quick_test"
            }
            
            try:
                response = requests.post(
                    f"{self.base_url}/api/sensor-readings/",
                    json=data,
                    headers=headers,
                    timeout=5
                )
                
                if response.status_code in [200, 201]:
                    print(f"✅ Parcelle {i+1}: {data['value']}%")
                else:
                    print(f"❌ Erreur {response.status_code}: {response.text[:50]}")
                    
            except Exception as e:
                print(f"❌ Exception: {e}")
            
            time.sleep(1)
        
        print("\n✅ Test terminé!")
    
    def run_simulation(self):
        """Simulation simple"""
        print("\n🚀 Simulation simple (2 minutes)...")
        
        if not self.login():
            return
        
        headers = {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json'
        }
        
        end_time = datetime.now() + timedelta(minutes=2)
        count = 0
        
        try:
            while datetime.now() < end_time:
                for plot_id in [1, 2, 3]:
                    for sensor_type in ["moisture", "temperature", "humidity"]:
                        # Valeurs réalistes
                        if sensor_type == "moisture":
                            value = random.uniform(45, 75)
                        elif sensor_type == "temperature":
                            value = random.uniform(18, 28)
                        else:  # humidity
                            value = random.uniform(45, 75)
                        
                        data = {
                            "timestamp": datetime.now().isoformat(),
                            "plot": plot_id,
                            "sensor_type": sensor_type,
                            "value": round(value, 2),
                            "source": "simple_sim"
                        }
                        
                        response = requests.post(
                            f"{self.base_url}/api/sensor-readings/",
                            json=data,
                            headers=headers,
                            timeout=5
                        )
                        
                        if response.status_code in [200, 201]:
                            count += 1
                            if count % 5 == 0:  # Log toutes les 5 lectures
                                print(f"📊 {count} lectures envoyées...")
                
                time.sleep(10)  # Toutes les 10 secondes
                
        except KeyboardInterrupt:
            print("\n⏹️  Arrêté")
        
        print(f"\n✅ {count} lectures envoyées au total!")

def main():
    print("="*60)
    print("🌾 SIMULATEUR AGRICOLE - CREDENTIALS CORRECTS")
    print("="*60)
    
    url = "http://localhost:8000"
    
    print(f"\n🔗 URL: {url}")
    print("📋 Essai des combinaisons:")
    print("   1. sarra / sarour1234")
    print("   2. admin / admin123")
    print("   3. admin / password")
    print("   4. test / test123")
    
    simulator = CorrectSimulator(url)
    
    print("\n1. 🧪 Test rapide (3 lectures)")
    print("2. 🚀 Simulation (2 minutes)")
    print("3. 🔐 Test login seulement")
    
    choice = input("\nChoix [1]: ").strip() or "1"
    
    if choice == "1":
        simulator.quick_test()
    elif choice == "2":
        simulator.run_simulation()
    elif choice == "3":
        simulator.login()
    else:
        print("❌ Choix invalide")
    
    print("\n" + "="*60)
    print("🔧 SI RIEN NE MARCHE:")
    print("="*60)
    print("1. Créez un superuser:")
    print("   python manage.py createsuperuser")
    print("   → Username: testuser")
    print("   → Password: testpass123")
    
    print("\n2. Testez manuellement:")
    print("   curl -X POST http://localhost:8000/api/auth/login/ \\")
    print("        -H \"Content-Type: application/json\" \\")
    print("        -d '{\"username\":\"testuser\",\"password\":\"testpass123\"}'")

if __name__ == "__main__":
    main()