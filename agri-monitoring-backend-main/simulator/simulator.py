"""
AGRICULTURAL MONITORING SIMULATOR

Purpose: Generates realistic sensor data and sends it to your Django API
Key features:
- Simulates diurnal cycles (day/night temperature changes)
- Creates realistic anomalies for testing
- Sends data via HTTP to your running Django server
- Can run in background or interactively
"""
from __future__ import annotations # For type hints
import os
import sys
import django
import requests # HTTP library for API calls
import random
import time
import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import argparse # For command-line arguments
import threading # For running simulation in background
from dataclasses import dataclass # For structured data
from enum import Enum # For predefined choices

# Optional: configure Django settings if you're running inside project
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'agri_backend.settings')

try:
    django.setup()
    from django.utils import timezone
    DJANGO_CONFIGURED = True
except Exception:
    DJANGO_CONFIGURED = False
    timezone = type('tzproxy', (), {'now': staticmethod(lambda: datetime.now())})


#Enums & dataclasses 
class SensorType(Enum):
    """Types of sensors the simulator can generate data for."""
    MOISTURE = "moisture" #soil moisture sensor
    TEMPERATURE = "temperature" #air temp sensor
    HUMIDITY = "humidity" #air humidity sensor

class AnomalyType(Enum):
    """Types of anomalies the simulator can inject."""
    NONE = "none"              # No anomaly
    SUDDEN_DROP = "sudden_drop"  # Sudden decrease in value
    SPIKE = "spike"            # Sudden increase in value
    DRIFT = "drift"            # Gradual change over time
    STUCK = "stuck"            # Sensor stuck at one value
    NOISY = "noisy"            # Random noise added

@dataclass
class PlotConfig:
    """Configuration for each simulated field plot."""
    id: int # Human-readable name
    name: str  # Human-readable name
    crop_type: str = "wheat" # Type of crop
    irrigation_interval_hours: int = 18 # How often plot gets watered
    last_irrigation: Optional[datetime] = None  # Last watering time
    anomaly: AnomalyType = AnomalyType.NONE # Current anomaly
    anomaly_start: Optional[datetime] = None # When anomaly started
    anomaly_params: Dict = None # Parameters for the anomaly

    def __post_init__(self):
        """Initialize default values after creation."""
        if self.anomaly_params is None:
            self.anomaly_params = {}
        if self.last_irrigation is None:
            # Start with irrigation 6 hours ago
            self.last_irrigation = datetime.now() - timedelta(hours=6)

@dataclass
class SensorReading:
    """Represents a single sensor reading to send to API."""
    plot_id: int
    sensor_type: SensorType
    value: float
    timestamp: datetime
    is_anomaly: bool = False
    anomaly_type: str = "none"

# Main simulator class
class AgriSimulator:
    """
    Main simulator class that generates and sends agricultural sensor data.
    
    How it works:
    1. Connects to your Django API (bel authentication)
    2. Creates/looks up field plots
    3. Generates realistic sensor values with daily cycles
    4. Can inject anomalies for testing
    5. Sends data to API at configurable intervals
    """
    def __init__(self, base_url: str = "http://localhost:8000", frequency_minutes: int = 10):
        """
        Initialize simulator.
        
        Args:
            base_url: URL of your Django API
            frequency_minutes: How often to send data (in minutes)
        """
        self.base_url = base_url.rstrip("/") # Remove trailing slash
        self.frequency_seconds = max(10, frequency_minutes * 60)  # minimum 10s
        self.token: Optional[str] = None # JWT token for authentication
        self.plots: List[PlotConfig] = [] # List of simulated plots
        self.simulation_running = False # Control flag
        self.thread: Optional[threading.Thread] = None # Background thread

        # State tracking for realistic simulations
        self.simulation_state: Dict[str, float] = {}
        self.state_lock = threading.Lock()# For thread safety

        # HTTP session reused for better perf
        self.session = requests.Session()

        # realistic parameter ranges for agricultural data
        self.params = {
            "moisture": {
                "base_range": (40.0, 80.0), # Normal soil moisture %
                "daily_decrease_per_hour": 0.8, # How fast soil dries per hour
                "irrigation_increase": 25.0, # How much watering helps
                "night_recovery_per_hour": 0.2, # Minor recovery at night
            },
            "temperature": {
                "base_range": (15.0, 30.0), # Normal temperature range °C
                "daily_amplitude": 8.0, # Day-night difference
                "peak_hour": 14.0, # Hottest time of day (2 PM)
            },
            "humidity": {
                "base_range": (40.0, 80.0),  # Normal humidity %
                "temp_inverse_factor": -0.7, # Hotter = less humid
                "daily_amplitude": 15.0, # Day-night variation
            }
        }

    #authentification and plot management
    def login(self, username: str = None, password: str = None) -> bool:
        """Authenticate and prepare session headers. Accepts token in various shapes."""
        import os
        from dotenv import load_dotenv
        load_dotenv()
        # Load environment variables
        load_dotenv()
        
        # Get credentials from environment or use defaults
        username = username or os.getenv('SIMULATOR_USERNAME', 'simulator')
        password = password or os.getenv('SIMULATOR_PASSWORD', 'simulator_pass')
        try:
            # Send login request to Django's JWT endpoint
            r = self.session.post(
                f"{self.base_url}/api/auth/login/",
                json={"username": username, "password": password},
                timeout=6
            )
            if r.status_code == 200:
                body = r.json()
                # Extract token (Django Simple JWT uses 'access' key)
                self.token = body.get("access") or body.get("token") or body.get("access_token") or body.get("auth_token")
                if self.token:
                    # Add token to all future requests
                    self.session.headers.update({"Authorization": f"Bearer {self.token}"})
                print(f" Authenticated as {username}")
                self.load_or_create_plots()
                return True
            else:
                print(f" Login failed ({r.status_code}): {r.text[:200]}")
        except requests.exceptions.ConnectionError:
            print(f" Cannot connect to {self.base_url}")
        except Exception as e:
            print(f" Login error: {e}")
        return False

    def load_or_create_plots(self):
        """Try to load existing plots from API, or create default ones."""
        try:
            # Try to get plots from API
            r = self.session.get(f"{self.base_url}/api/plots/", timeout=6)
            if r.status_code == 200:
                plots = r.json()
                if plots:
                    for p in plots:
                        self.plots.append(PlotConfig(
                            id=p["id"],
                            name=p.get("name", f"Plot {p['id']}"),
                            crop_type=p.get("crop_type", "wheat")
                        ))
                    print(f" Loaded {len(self.plots)} plots from API")
                    return
        except Exception:
            pass # If API fails, create defaults

        # fallback: create default plots
        defaults = [
            {"name": "Demo North", "crop_type": "wheat", "area": 2.5},
            {"name": "Demo South", "crop_type": "corn", "area": 3.0},
            {"name": "Demo East", "crop_type": "vegetables", "area": 1.5},
        ]
        created = 0
        for data in defaults:
            try:
                r = self.session.post(f"{self.base_url}/api/plots/", json=data, timeout=6)
                if r.status_code in (200, 201):
                    p = r.json()
                    self.plots.append(PlotConfig(id=p["id"], name=p.get("name", data["name"]), crop_type=p.get("crop_type", data["crop_type"])))
                    created += 1
            except Exception:
                continue

        if created:
            print(f" Created {created} default plots")
        else:
            # Use fake plot IDs for testing
            print(" Running in demo mode with in-memory plots")
            self.plots = [
                PlotConfig(id=1, name="Demo Plot 1", crop_type="wheat"),
                PlotConfig(id=2, name="Demo Plot 2", crop_type="corn"),
                PlotConfig(id=3, name="Demo Plot 3", crop_type="vegetables"),
            ]

    #data generation
    def calculate_time_factors(self, current_time: datetime) -> Tuple[float, float, float]:
        """
        Calculate time-based factors that affect sensor readings.
        
        Returns:
            tuple: (diurnal_factor, seasonal_factor, weather_factor)
            - diurnal: 0-1 based on time of day (0=night, 1=peak heat)
            - seasonal: 0.7-1.0 based on time of year
            - weather: 0.95-1.05 random daily variation
        """
        hour = current_time.hour + current_time.minute / 60.0
        # Diurnal factor: sinusoidal curve peaking at 2 PM
        peak = self.params["temperature"]["peak_hour"]
        diurnal = 0.5 * (1 + math.cos((hour - peak) * 2 * math.pi / 24.0))  # cosine centered on peak
        # normalize into 0..1
        diurnal = max(0.0, min(1.0, diurnal))
        # Seasonal factor: sinusoid over year
        day_of_year = current_time.timetuple().tm_yday
        seasonal = 0.7 + 0.3 * math.sin(2 * math.pi * day_of_year / 365.0)
        # Weather factor: random but consistent for a given hour
        weather_key = current_time.strftime("%Y%m%d%H")
        random.seed(hash(weather_key) % 100000) # Deterministic per hour
        weather_factor = 0.95 + random.random() * 0.1
        return diurnal, seasonal, weather_factor

    def generate_moisture(self, plot: PlotConfig, current_time: datetime, diurnal_factor: float) -> Tuple[float, bool]:
        """
        Generate realistic soil moisture values.
        
        Features:
        - Slowly decreases between irrigations
        - Jumps up after irrigation
        - Slight recovery at night
        """
        p = self.params["moisture"]
        base_min, base_max = p["base_range"]

        # Check if irrigation is due
        hours_since_irrigation = (current_time - plot.last_irrigation).total_seconds() / 3600.0
        irrigation_due = hours_since_irrigation >= plot.irrigation_interval_hours

         # Thread-safe state management
        with self.state_lock:
            state_key = f"moisture_{plot.id}"
            if state_key not in self.simulation_state:
                # Initialize with random value in normal range
                self.simulation_state[state_key] = random.uniform(base_min + 5, base_max - 5)
            current_moisture = self.simulation_state[state_key]

            if irrigation_due:
                # Irrigation event: moisture increases
                new_moisture = min(100.0, current_moisture + p["irrigation_increase"])
                plot.last_irrigation = current_time
                is_irrigation = True
            else:
                 # Normal drying/recovery cycle
                hour = current_time.hour
                if 20 <= hour or hour < 6:
                    # Night: slight recovery
                    change = p["night_recovery_per_hour"] * (1.0 - diurnal_factor)  # small positive
                else:
                    # Day: drying
                    change = -p["daily_decrease_per_hour"] * (0.3 + 0.7 * diurnal_factor)
                new_moisture = current_moisture + change
                # Allow moisture to go below nominal base_min when drought/anomaly occurs
                # clamp to a sensible absolute range [0, 100]
                new_moisture = max(0.0, min(100.0, new_moisture))
                is_irrigation = False

            # save state for next iteration
            self.simulation_state[state_key] = new_moisture

        # Apply any active anomalies
        value, anomaly_type = self.apply_anomaly(plot, SensorType.MOISTURE, new_moisture, current_time)
        return round(value, 1), is_irrigation

    def generate_temperature(self, plot: PlotConfig, current_time: datetime, diurnal_factor: float, seasonal_factor: float, weather_factor: float) -> float:
        """
        Generate realistic air temperature with daily and seasonal cycles.
        """
        p = self.params["temperature"]
        base_min, base_max = p["base_range"]

        # base temp influenced by seasonal factor
        base_temp = base_min + (base_max - base_min) * seasonal_factor * 0.6
        
        # sinusoidal diurnal variation (daily)
        peak = p["peak_hour"]
        angle = 2 * math.pi * (current_time.hour + current_time.minute / 60.0 - peak) / 24.0
        diurnal_variation = p["daily_amplitude"] * math.cos(angle)
        
        # Small random variation
        random_variation = (random.random() - 0.5) * 2.5
        # Combine all factors
        value = (base_temp + diurnal_variation + random_variation) * weather_factor
        # Apply anomalies if any
        value, _ = self.apply_anomaly(plot, SensorType.TEMPERATURE, value, current_time)
        return round(value, 1)

    def generate_humidity(self, plot: PlotConfig, temperature: float, diurnal_factor: float) -> float:
        """
        Generate air humidity (inversely related to temperature).
        """
        p = self.params["humidity"]
        base_min, base_max = p["base_range"]
        # Base humidity: higher when cooler
        base_humidity = 70.0 + p["temp_inverse_factor"] * (temperature - 22.0)
        
        # Daily variation (lower during day)
        diurnal_variation = p["daily_amplitude"] * (0.5 - diurnal_factor)
        random_variation = (random.random() - 0.5) * 6.0
        value = base_humidity + diurnal_variation + random_variation
        value = max(0.0, min(100.0, value))
        value, _ = self.apply_anomaly(plot, SensorType.HUMIDITY, value, datetime.now())
        return round(value, 1)

    def apply_anomaly(self, plot: PlotConfig, sensor_type: SensorType, base_value: float, current_time: datetime) -> Tuple[float, str]:
        """
        Apply configured anomaly to sensor value.
        
        Anomalies have configurable durations (in minutes).
        """
        if plot.anomaly == AnomalyType.NONE:
            return base_value, "none"

        # Check if anomaly has expired
        duration_min = plot.anomaly_params.get("duration_minutes")
        if plot.anomaly_start and duration_min is not None:
            elapsed = (current_time - plot.anomaly_start).total_seconds() / 60.0
            if elapsed > duration_min:
                # Anomaly expired
                plot.anomaly = AnomalyType.NONE
                plot.anomaly_start = None
                plot.anomaly_params = {}
                return base_value, "none"


        # Apply anomaly based on type (anomaly_key)
        a = plot.anomaly
        anomaly_key = a.value

        if a == AnomalyType.SUDDEN_DROP:
            if sensor_type == SensorType.MOISTURE:
                return max(0.0, base_value * 0.35), anomaly_key # 65% drop
            if sensor_type == SensorType.HUMIDITY:
                return max(0.0, base_value * 0.7), anomaly_key # 30% drop

        if a == AnomalyType.SPIKE:
            factor = float(plot.anomaly_params.get("spike_factor", 1.8))
            return base_value * factor, anomaly_key

        if a == AnomalyType.DRIFT:
            if plot.anomaly_start:
                # Gradual change over time
                hours_active = (current_time - plot.anomaly_start).total_seconds() / 3600.0
                rate = float(plot.anomaly_params.get("drift_rate", 0.5))
                if sensor_type == SensorType.MOISTURE:
                    return max(0.0, base_value - hours_active * rate), anomaly_key
                if sensor_type == SensorType.TEMPERATURE:
                    return base_value + hours_active * rate, anomaly_key

        if a == AnomalyType.STUCK:
            # Sensor stuck at fixed value
            stuck_value = float(plot.anomaly_params.get("stuck_value", base_value))
            return stuck_value, anomaly_key

        if a == AnomalyType.NOISY:
            # Add random noise
            noise_level = float(plot.anomaly_params.get("noise_level", 8.0))
            noise = (random.random() - 0.5) * 2 * noise_level
            return base_value + noise, anomaly_key

        return base_value, anomaly_key

    

    #API Communication
    def send_reading(self, reading: SensorReading) -> bool:
        """
        Sends a reading to the API.
        - Uses reading.timestamp (no overwrite)
        - Sends both compact sensor_type and explicit fields for compatibility
        """
        
        # Format timestamp
        ts_iso = reading.timestamp.isoformat()
        #Build API payload
        payload = {
            "plot": reading.plot_id,
            "sensor_type": reading.sensor_type.value,
            "value": reading.value,
            "timestamp": ts_iso,
            "source": "advanced_simulator",
            "metadata": {
                "is_anomaly": bool(reading.is_anomaly),
                "anomaly_type": reading.anomaly_type
            }
        }

        # Add explicit field names for different sensor types
        if reading.sensor_type == SensorType.MOISTURE:
            payload["soil_moisture"] = reading.value
        elif reading.sensor_type == SensorType.TEMPERATURE:
            payload["air_temperature"] = reading.value
        elif reading.sensor_type == SensorType.HUMIDITY:
            payload["ambient_humidity"] = reading.value

        try:
            # Send to API
            r = self.session.post(f"{self.base_url}/api/sensor-readings/", json=payload, timeout=6)
            if r.status_code in (200, 201):
                print(f"→ Sent reading | plot={reading.plot_id} | {reading.sensor_type.value}={reading.value} | ts={ts_iso} | anomaly={reading.anomaly_type}")
                return True
            else:
                print(f" Failed send ({r.status_code}) | plot={reading.plot_id} | sensor={reading.sensor_type.value} | {r.text[:160]}")
                return False
        except requests.exceptions.ConnectionError:
            print(" Cannot reach API server")
            return False
        except Exception as e:
            print(f" Send error: {e}")
            return False

    #Simulation loop
    def generate_readings_for_plot(self, plot: PlotConfig, current_time: datetime) -> List[SensorReading]:
        """Generate all three sensor readings for a plot."""
        diurnal, seasonal, weather = self.calculate_time_factors(current_time)
        moisture, irrig = self.generate_moisture(plot, current_time, diurnal)

        if irrig:
            print(f"    Irrigation triggered for plot {plot.id} ({plot.name}) at {current_time.isoformat()}")
        temp = self.generate_temperature(plot, current_time, diurnal, seasonal, weather)
        humidity = self.generate_humidity(plot, temp, diurnal)

        # Create reading objects for all three sensors
        readings = [
            SensorReading(plot_id=plot.id, sensor_type=SensorType.MOISTURE, value=round(moisture, 1), timestamp=current_time, is_anomaly=(plot.anomaly != AnomalyType.NONE), anomaly_type=(plot.anomaly.value if plot.anomaly != AnomalyType.NONE else "none")),
            SensorReading(plot_id=plot.id, sensor_type=SensorType.TEMPERATURE, value=temp, timestamp=current_time, is_anomaly=(plot.anomaly != AnomalyType.NONE), anomaly_type=(plot.anomaly.value if plot.anomaly != AnomalyType.NONE else "none")),
            SensorReading(plot_id=plot.id, sensor_type=SensorType.HUMIDITY, value=round(humidity, 1), timestamp=current_time, is_anomaly=(plot.anomaly != AnomalyType.NONE), anomaly_type=(plot.anomaly.value if plot.anomaly != AnomalyType.NONE else "none")),
        ]
        return readings


    def simulation_loop(self, duration_minutes: Optional[int] = None):
        """Main simulation loop - runs in background thread."""
        print(f"\nStarting simulation — freq={self.frequency_seconds/60:.2f}min — plots={len(self.plots)}")
        start = datetime.now()
        end = start + timedelta(minutes=duration_minutes) if duration_minutes else None
        cycle = 0
        sent = 0

        try:
            while self.simulation_running:
                now = datetime.now()
                if end and now >= end:
                    break
                cycle += 1
                print(f"\n Cycle {cycle} @ {now.isoformat()}")

                # Generate readings for all plots
                all_readings: List[SensorReading] = []
                for plot in list(self.plots):
                    all_readings.extend(self.generate_readings_for_plot(plot, now))

                # Send all readings 
                for r in all_readings:
                    if self.send_reading(r):
                        sent += 1

                print(f"    Cycle complete — readings sent this cycle: {len(all_readings)} — total_sent: {sent}")
                
                # Sleep until next cycle
                time.sleep(self.frequency_seconds)
        except KeyboardInterrupt:
            print("\n Simulation interrupted by user")
        finally:
            self.simulation_running = False
            elapsed_mins = (datetime.now() - start).total_seconds() / 60.0
            print(f"\n Simulation finished — cycles={cycle} — elapsed={elapsed_mins:.1f} min — total_sent={sent}")

    
    #interface
    def start_simulation(self, duration_minutes: Optional[int] = None):
        """Start simulation in background thread."""
        if not self.login():
            return False
        if self.simulation_running:
            print(" Simulation already running")
            return False
        self.simulation_running = True
        self.thread = threading.Thread(target=self.simulation_loop, args=(duration_minutes,), daemon=True) # Thread dies when main program exits
        self.thread.start()
        print(" Simulation started in background")
        return True

    def stop_simulation(self):
        self.simulation_running = False
        if self.thread:
            self.thread.join(timeout=5)
        print(" Simulation stopped")

    def inject_anomaly(self, plot_id: int, anomaly_type: AnomalyType, duration_minutes: int = 60, **params):
        """
        Inject an anomaly into a plot for testing.
        
        Example:
            sim.inject_anomaly(1, AnomalyType.SUDDEN_DROP, duration_minutes=90)
        """
        plot = next((p for p in self.plots if p.id == plot_id), None)
        if not plot:
            print(f" Plot {plot_id} not found")
            return False
        plot.anomaly = anomaly_type
        plot.anomaly_start = datetime.now()
        plot.anomaly_params = dict(params)
        # store duration explicitly
        plot.anomaly_params.setdefault("duration_minutes", duration_minutes)
        print(f" Injected anomaly {anomaly_type.value} on plot {plot.id} for {duration_minutes} minutes — params={params}")
        return True



#Command Line Interface CLI
def main():
    parser = argparse.ArgumentParser(description="Advanced Agri-Monitoring Simulator (cleaned)")
    parser.add_argument("--frequency", type=int, default=10, help="frequency in minutes (default 10)")
    parser.add_argument("--duration", type=int, help="duration in minutes (optional)")
    parser.add_argument("--scenario", type=str, help="run predefined scenario (optional)")
    args = parser.parse_args()

    sim = AgriSimulator(frequency_minutes=args.frequency)

    if args.scenario:
        # Predefined scenario mode
        if not sim.login():
            return
        sim.start_simulation(duration_minutes=args.duration or 30)
        # Example simple scenario runner — you can extend this:
        if args.scenario == "irrigation_failure":
            sim.inject_anomaly(plot_id=1, anomaly_type=AnomalyType.SUDDEN_DROP, duration_minutes=90)
        elif args.scenario == "sensor_drift":
            sim.inject_anomaly(plot_id=2, anomaly_type=AnomalyType.DRIFT, duration_minutes=240, stuck_value=25.0)
        elif args.scenario == "stuck":
            sim.inject_anomaly(plot_id=2, anomaly_type=AnomalyType.STUCK, duration_minutes=240, drift_rate=0.4)
        elif args.scenario == "heat_wave":
            sim.inject_anomaly(plot_id=4, anomaly_type=AnomalyType.SPIKE, duration_minutes=300, spike_factor=1.8)
        elif args.scenario == "cold_snap":
            sim.inject_anomaly(plot_id=4, anomaly_type=AnomalyType.SUDDEN_DROP, duration_minutes=180)
            sim.inject_anomaly(plot_id=5, anomaly_type=AnomalyType.SPIKE, duration_minutes=180, spike_factor=0.6)
        try:
            while sim.simulation_running:
                time.sleep(1)
        except KeyboardInterrupt:
            sim.stop_simulation()
        return

    # interactive mode
    print("\nOptions:\n1) run simulation\n2) short test (fast cycles)\n3) inject anomaly\n4) list plots\n")
    choice = input("Choice [1]: ").strip() or "1"

    if not sim.login():
        return

    if choice == "1":
        dur = input("Duration in minutes (empty = run indefinitely): ").strip()
        dur_val = int(dur) if dur else None
        sim.start_simulation(duration_minutes=dur_val)
        try:
            while sim.simulation_running:
                time.sleep(1)
        except KeyboardInterrupt:
            sim.stop_simulation()

    elif choice == "2":
        sim.frequency_seconds = 5
        sim.start_simulation(duration_minutes=1)
        try:
            while sim.simulation_running:
                time.sleep(1)
        except KeyboardInterrupt:
            sim.stop_simulation()

    elif choice == "3":
        print("Available plots:")
        for p in sim.plots:
            print(f"  {p.id}: {p.name}")
        pid = int(input("Plot id: ").strip())
        print("Available anomalies:", ", ".join([a.value for a in AnomalyType]))
        at = input("Anomaly type: ").strip()
        try:
            aenum = AnomalyType(at)
        except ValueError:
            print("Invalid anomaly")
            return
        dur = int(input("Duration minutes (default 60): ").strip() or "60")
        params = {}
        # optional params entry (simple)
        extra = input("Extra params as key=value separated by commas (or empty): ").strip()
        if extra:
            for kv in extra.split(","):
                if "=" in kv:
                    k, v = kv.split("=", 1)
                    try:
                        params[k.strip()] = float(v) if "." in v or v.isdigit() else v.strip()
                    except Exception:
                        params[k.strip()] = v.strip()
        sim.inject_anomaly(pid, aenum, duration_minutes=dur, **params)
        # run a short simulation to see effect
        sim.start_simulation(duration_minutes=5)
        try:
            while sim.simulation_running:
                time.sleep(1)
        except KeyboardInterrupt:
            sim.stop_simulation()

    elif choice == "4":
        for p in sim.plots:
            print(f"  {p.id}: {p.name} ({p.crop_type}) anomaly={p.anomaly.value}")

if __name__ == "__main__":
    main()
