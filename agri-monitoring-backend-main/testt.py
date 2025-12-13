"""
AGRI-MONITORING FULL SYSTEM TEST
Tests all components: ML, AI Agent, API, Dashboard, Simulator
"""
import os
import sys
import django
import requests
import json
import random
import time
from datetime import datetime, timedelta

# Django setup
PROJECT_PATH = r'C:\Users\semyz\agri-monitoring-backend\agri-monitoring-backend-main'
sys.path.append(PROJECT_PATH)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'agri_backend.settings')

try:
    django.setup()
    print("✅ Django setup successful")
except Exception as e:
    print(f"❌ Django setup failed: {e}")
    sys.exit(1)

from django.contrib.auth.models import User
from django.utils import timezone
from monitoring.models import FarmProfile, FieldPlot, SensorReading, AnomalyEvent, AgentRecommendation

class FullSystemTester:
    def __init__(self):
        self.base_url = "http://127.0.0.1:8000"
        self.token = None
        self.test_user = None
        self.test_farm = None
        self.test_plot = None

    # ------------------- Utility -------------------
    def print_section(self, title):
        print(f"\n{'='*70}\n🔬 {title}\n{'='*70}")

    # ------------------- Setup -------------------
    def setup_test_environment(self):
        self.print_section("SETTING UP TEST ENVIRONMENT")

        # Create test user
        self.test_user, created = User.objects.get_or_create(
            username="full_system_test",
            defaults={'email': 'fulltest@example.com'}
        )
        if created:
            self.test_user.set_password("test123")
            self.test_user.save()
        print(f"👤 Test user: {self.test_user.username}")

        # Create test farm
        self.test_farm, _ = FarmProfile.objects.get_or_create(
            owner=self.test_user,
            location="Full System Test Farm",
            defaults={'size': 25.0, 'crop_type': "Mixed Test Crops"}
        )
        print(f"🏭 Test farm: {self.test_farm.id} - {self.test_farm.location}")

        # Create test plot
        self.test_plot, _ = FieldPlot.objects.get_or_create(
            farm=self.test_farm,
            crop_variety="Full System Test Plot"
        )
        print(f"🌾 Test plot: {self.test_plot.id} - {self.test_plot.crop_variety}")

        # Get API token
        self.get_auth_token()
        return True

    def get_auth_token(self):
        try:
            response = requests.post(
                f"{self.base_url}/api/auth/login/",
                json={"username": "sarra", "password": "sarour1234"},
                timeout=5
            )
            if response.status_code == 200:
                self.token = response.json()['access']
                print(f"🔑 Token obtained: {self.token[:50]}...")
                return True
        except Exception as e:
            print(f"⚠️ Could not get token: {e}")
        self.token = None
        return False

    # ------------------- ML Model -------------------
    def test_ml_model(self):
        self.print_section("TESTING ML MODEL")
        try:
            from ml.ml_model import ml_model
            from ml.inference import detector

            if not ml_model.model:
                print("❌ ML Model not loaded")
                return False
            print(f"✅ ML Model loaded: {type(ml_model.model).__name__}")

            # Test sample readings
            test_readings = [
                {'moisture': 65.5, 'temperature': 24.3, 'humidity': 58.2},
                {'moisture': 25.7, 'temperature': 32.1, 'humidity': 35.4},  # anomaly
                {'moisture': 85.3, 'temperature': 18.2, 'humidity': 92.1},  # anomaly
            ]
            for i, reading in enumerate(test_readings, 1):
                result = detector.detect_anomaly(reading)
                status = 'ANOMALY' if result['is_anomaly'] else 'NORMAL'
                print(f"  Test {i}: {status}, Score: {result.get('score', 0):.3f}, Type: {result.get('anomaly_type', 'unknown')}")

            # Plot-level detection
            plot_result = detector.detect_for_plot(self.test_plot.id)
            print(f"  Plot {self.test_plot.id} Anomaly: {'YES' if plot_result['is_anomaly'] else 'NO'}, Confidence: {plot_result.get('score',0):.3f}")
            return True

        except Exception as e:
            print(f"❌ ML test error: {e}")
            return False

    # ------------------- AI Agent -------------------
    def test_ai_agent(self):
        self.print_section("TESTING AI AGENT")
        try:
            from monitoring.ai_agent import AgricultureAI

            print(f"✅ AI Agent loaded: {AgricultureAI.__class__.__name__}, Rules: {len(AgricultureAI.knowledge_base)}")

            # Test mock anomalies
            test_anomalies = [
                {'type': 'soil_moisture_low', 'severity': 'high'},
                {'type': 'temperature_high', 'severity': 'medium'},
                {'type': 'unknown_type', 'severity': 'low'}
            ]
            for data in test_anomalies:
                class MockAnomaly:
                    def __init__(self, d): self.anomaly_type=d['type']; self.severity=d['severity']; self.confidence=0.85; self.plot=self.plot
                result = AgricultureAI.analyze_anomaly(MockAnomaly(data))
                print(f"  {data['type']} → Action: {result['recommended_action'][:60]}..., Confidence: {result['confidence']:.2f}")

            # Real anomaly test
            anomaly = AnomalyEvent.objects.create(plot=self.test_plot, anomaly_type="soil_moisture_low", severity="high", model_confidence=0.92)
            recommendation = AgricultureAI.generate_recommendation(anomaly)
            print(f"✅ Real recommendation generated, Length: {len(recommendation['recommended_action'])}, Confidence: {recommendation['confidence']:.2f}")
            AgentRecommendation.objects.filter(anomaly_event=anomaly).delete()
            anomaly.delete()
            return True
        except Exception as e:
            print(f"❌ AI Agent test error: {e}")
            return False

    # ------------------- Simulator -------------------
    def test_simulator(self):
        self.print_section("TESTING SIMULATOR")
        try:
            sys.path.append(os.path.join(PROJECT_PATH, 'simulator'))
            from simulator.simulator import AgriSimulator

            simulator = AgriSimulator(base_url=self.base_url)
            if not simulator.login():
                print("❌ Simulator login failed")
                return False
            print("✅ Simulator login successful")

            # Send sample readings
            for i in range(3):
                reading_data = {
                    "plot_id": self.test_plot.id,
                    "sensor_type": "temperature",
                    "value": 25.5 + i
                }
                simulator.send_reading(reading_data)
                time.sleep(0.5)
            print("📊 Sample readings sent")

            # Quick simulator test
            if simulator.quick_test(count=2):
                print("✅ Simulator quick test passed")
            return True
        except Exception as e:
            print(f"❌ Simulator test error: {e}")
            return False

    # ------------------- API Endpoints -------------------
    def test_api_endpoints(self):
        self.print_section("TESTING API ENDPOINTS")
        if not self.token: return False

        headers = {'Authorization': f'Bearer {self.token}'}
        endpoints = [
            ("/api/farms/", "GET"), ("/api/plots/", "GET"),
            ("/api/sensor-readings/", "GET"), ("/api/anomalies/", "GET"),
            ("/api/recommendations/", "GET"), ("/api/dashboard/stats/", "GET")
        ]
        all_success = True
        for ep, method in endpoints:
            try:
                resp = requests.get(f"{self.base_url}{ep}", headers=headers, timeout=5)
                status = "✅" if resp.status_code == 200 else "❌"
                print(f"  {status} {ep}: {resp.status_code}")
                if resp.status_code != 200: all_success = False
            except Exception as e:
                print(f"  ❌ {ep} error: {e}")
                all_success = False

        # Test anomaly recommendation
        anomaly = AnomalyEvent.objects.create(plot=self.test_plot, anomaly_type="temperature_high", severity="medium", model_confidence=0.87)
        try:
            resp = requests.post(f"{self.base_url}/api/anomalies/{anomaly.id}/recommend/", headers=headers, timeout=10)
            if resp.status_code == 200:
                print(f"✅ Recommendation generated")
            else:
                print(f"❌ Recommendation failed: {resp.status_code}")
                all_success = False
        finally:
            anomaly.delete()
        return all_success

    # ------------------- Dashboard Data -------------------
    def test_dashboard_data(self):
        self.print_section("TESTING DASHBOARD DATA")
        now = timezone.now()
        # Sensor readings
        for i in range(20):
            ts = now - timedelta(hours=i)
            SensorReading.objects.create(plot=self.test_plot, sensor_type="moisture", value=55+random.uniform(-15,15), timestamp=ts, source="dashboard_test")
            SensorReading.objects.create(plot=self.test_plot, sensor_type="temperature", value=24+random.uniform(-5,5), timestamp=ts, source="dashboard_test")

        # Anomalies
        for _ in range(3):
            AnomalyEvent.objects.create(plot=self.test_plot, anomaly_type=random.choice(['soil_moisture_low','temperature_high','humidity_high']),
                                        severity=random.choice(['low','medium','high']), model_confidence=random.uniform(0.7,0.95), timestamp=now)

        stats = {
            "Total readings": SensorReading.objects.filter(plot=self.test_plot).count(),
            "Anomalies": AnomalyEvent.objects.filter(plot=self.test_plot).count(),
            "Recommendations": AgentRecommendation.objects.filter(anomaly_event__plot=self.test_plot).count()
        }
        print("📈 Dashboard stats:", stats)
        return True

    # ------------------- Angular Compatibility -------------------
    def test_angular_compatibility(self):
        self.print_section("TESTING ANGULAR COMPATIBILITY")
        if not self.token: return False
        headers = {'Authorization': f'Bearer {self.token}'}
        endpoints = [("/api/plots/", "Plots"), ("/api/anomalies/", "Anomalies"), (f"/api/sensor-readings/?field_plot={self.test_plot.id}", "Sensor data")]
        for ep, name in endpoints:
            try:
                resp = requests.get(f"{self.base_url}{ep}", headers=headers, timeout=5)
                if resp.status_code == 200:
                    data = resp.json()
                    print(f"✅ {name}: {type(data).__name__}, Sample keys: {list(data[0].keys())[:5] if data else 'N/A'}")
                else:
                    print(f"❌ {name}: {resp.status_code}")
            except Exception as e:
                print(f"❌ {name} error: {e}")
        return True

    # ------------------- Run Complete Test -------------------
    def run_complete_test(self):
        self.print_section("RUNNING FULL SYSTEM TEST")
        self.setup_test_environment()
        tests = [
            ("ML Model", self.test_ml_model),
            ("AI Agent", self.test_ai_agent),
            ("Simulator", self.test_simulator),
            ("API Endpoints", self.test_api_endpoints),
            ("Dashboard Data", self.test_dashboard_data),
            ("Angular Compatibility", self.test_angular_compatibility)
        ]
        results = []
        for name, func in tests:
            print(f"\n▶️  Running: {name}")
            success = func()
            results.append((name, success))
            print(f"   {'✅ PASS' if success else '❌ FAIL'}")

        # Summary
        passed = sum(1 for _, s in results if s)
        print(f"\n📊 Summary: {passed}/{len(tests)} tests passed")
        self.cleanup_test_data()
        return passed == len(tests)

        # ------------------- Plot 5 Anomaly Detection -------------------
    def test_plot_5_anomaly_detection(self):
        """Detect anomalies from actual sensor data for plot_id 5"""
        self.print_section("DETECTING ANOMALIES FROM ACTUAL SENSOR DATA - PLOT ID 5")
        
        try:
            from ml.inference import detector
            
            # Check if plot 5 exists in the database
            try:
                plot_5 = FieldPlot.objects.get(id=5)
                print(f"🌾 Found plot 5: {plot_5.crop_variety}")
                print(f"   Farm: {plot_5.farm.location}")
            except FieldPlot.DoesNotExist:
                print(f"❌ Plot 5 does not exist in the database")
                print(f"   Creating a test plot...")
                
                # Get or create a farm for plot 5
                farm, _ = FarmProfile.objects.get_or_create(
                    location="Plot 5 Test Farm",
                    defaults={'size': 10.0, 'crop_type': "Mixed Crops"}
                )
                
                plot_5 = FieldPlot.objects.create(
                    id=5,
                    farm=farm,
                    crop_variety="Test Plot 5",
                    size=2.5,
                    planting_date=timezone.now() - timedelta(days=90)
                )
                print(f"✅ Created plot 5 for testing")
            
            # Get ACTUAL sensor readings for plot 5 from the database
            print(f"\n📊 Checking ACTUAL sensor data for plot 5...")
            
            # Count all readings for plot 5
            total_readings = SensorReading.objects.filter(plot=plot_5).count()
            print(f"   Total sensor readings in database: {total_readings}")
            
            if total_readings == 0:
                print(f"⚠️  No sensor readings found for plot 5")
                print(f"   Please run the simulator or add real sensor data first")
                return False
            
            # Get readings by sensor type
            sensor_types = SensorReading.objects.filter(plot=plot_5).values_list('sensor_type', flat=True).distinct()
            print(f"   Sensor types found: {list(sensor_types)}")
            
            # Show latest readings
            latest_readings = SensorReading.objects.filter(plot=plot_5).order_by('-timestamp')[:3]
            print(f"\n   Latest readings for plot 5:")
            for reading in latest_readings:
                print(f"   - {reading.timestamp}: {reading.sensor_type} = {reading.value:.2f}")
            
            # Get statistics
            moisture_readings = SensorReading.objects.filter(plot=plot_5, sensor_type='moisture')
            temp_readings = SensorReading.objects.filter(plot=plot_5, sensor_type='temperature')
            
            if moisture_readings.exists():
                avg_moisture = sum(r.value for r in moisture_readings) / moisture_readings.count()
                print(f"\n   Moisture stats: Avg = {avg_moisture:.2f}, Count = {moisture_readings.count()}")
            
            if temp_readings.exists():
                avg_temp = sum(r.value for r in temp_readings) / temp_readings.count()
                print(f"   Temperature stats: Avg = {avg_temp:.2f}, Count = {temp_readings.count()}")
            
            # Run anomaly detection on ACTUAL data
            print(f"\n🔍 Running anomaly detection on ACTUAL sensor data for plot 5...")
            plot_result = detector.detect_for_plot(5)
            
            print(f"\n📈 ANOMALY DETECTION RESULTS FOR PLOT 5:")
            print(f"   {'='*40}")
            
            if plot_result.get('error'):
                print(f"❌ Error: {plot_result['error']}")
                return False
            
            print(f"   - Anomaly Detected: {'🔴 YES' if plot_result['is_anomaly'] else '🟢 NO'}")
            print(f"   - Confidence Score: {plot_result.get('score', 0):.3f}")
            print(f"   - Anomaly Type: {plot_result.get('anomaly_type', 'unknown')}")
            print(f"   - Severity: {plot_result.get('severity', 'unknown')}")
            
            # Inside test_plot_5_anomaly_detection method, after anomaly detection:

            if plot_result['is_anomaly']:
                print(f"\n⚠️  ANOMALY DETAILS:")
                print(f"   - Details: {plot_result.get('details', 'No details available')}")
                
                # Create new anomaly event from ACTUAL data
                anomaly_event = AnomalyEvent.objects.create(
                    plot=plot_5,
                    anomaly_type=plot_result.get('anomaly_type', 'unknown'),
                    severity=plot_result.get('severity', 'medium'),
                    model_confidence=plot_result.get('score', 0.8),
                    timestamp=timezone.now()
                )
                print(f"\n📝 Created new anomaly event #{anomaly_event.id}")
                
            # Show historical anomalies for plot 5
            print(f"\n📋 HISTORICAL ANOMALIES FOR PLOT 5:")
            historical_anomalies = AnomalyEvent.objects.filter(plot=plot_5).order_by('-timestamp')[:5]
            
            if historical_anomalies.exists():
                for anomaly in historical_anomalies:
                    status = "🟢" if anomaly.resolved else "🔴"
                    print(f"   {status} {anomaly.timestamp}: {anomaly.anomaly_type} ({anomaly.severity})")
            else:
                print(f"   No historical anomalies found")
            
            # Test API endpoint with actual data
            if self.token:
                print(f"\n📡 Testing API endpoints with actual plot 5 data...")
                headers = {'Authorization': f'Bearer {self.token}'}
                
                # Get plot 5 sensor data via API
                resp = requests.get(
                    f"{self.base_url}/api/sensor-readings/?field_plot=5",
                    headers=headers,
                    timeout=5
                )
                if resp.status_code == 200:
                    api_data = resp.json()
                    print(f"✅ API - Plot 5 sensor readings: {len(api_data)} records")
                
                # Get plot 5 anomalies via API
                resp = requests.get(
                    f"{self.base_url}/api/anomalies/?plot_id=5",
                    headers=headers,
                    timeout=5
                )
                if resp.status_code == 200:
                    api_anomalies = resp.json()
                    print(f"✅ API - Plot 5 anomalies: {len(api_anomalies)} records")
            
            return True
            
        except Exception as e:
            print(f"❌ Error detecting anomalies for plot 5: {e}")
            import traceback
            traceback.print_exc()
            return False


    # ------------------- Cleanup -------------------
    def cleanup_test_data(self):
        self.print_section("CLEANING UP TEST DATA")
        SensorReading.objects.filter(plot=self.test_plot, source__in=["dashboard_test"]).delete()
        AnomalyEvent.objects.filter(plot=self.test_plot).delete()
        AgentRecommendation.objects.filter(anomaly_event__plot=self.test_plot).delete()
        self.test_plot.delete()
        self.test_farm.delete()
        self.test_user.delete()
        print("✅ Test data cleaned")

# ------------------- Main -------------------
if __name__ == "__main__":
    print("="*70)
    print("🤖 AGRI-MONITORING FULL SYSTEM TESTER")
    print("="*70)

    tester = FullSystemTester()
    print("\nOptions:\n1. Complete system test\n2. Quick API test\n3. Plot 5 anomaly detection\n4. Exit")
    choice = input("Your choice [1]: ").strip() or "1"

    if choice == "1":
        tester.run_complete_test()
    elif choice == "2":
        tester.get_auth_token()
        if tester.token:
            headers = {'Authorization': f'Bearer {tester.token}'}
            resp = requests.get(f"{tester.base_url}/api/dashboard/stats/", headers=headers, timeout=5)
            print(resp.json() if resp.status_code==200 else "❌ API failed")
    elif choice == "3":
        # Directly test plot 5 anomaly detection
        tester.setup_test_environment()
        tester.test_plot_5_anomaly_detection()
    
    print("\n👋 Test completed!")