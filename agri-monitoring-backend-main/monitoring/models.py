from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()# Get the currently active User model


class FarmProfile(models.Model):
    """
    Represents a fram owned by a user 
    Fields:
    - owner: User foreign key
    - location: CharField
    - size: FloatField (hectares)
    - crop_type: CharField
    """
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE, # Delete farm if owner is deleted
        related_name="farms", # User.farms gives all farms of a user
        verbose_name="Owner"
    )
    location = models.CharField(
        max_length=255,
        verbose_name="Location"
    )
    size = models.FloatField(
        help_text="Farm size in hectares",
        verbose_name="Size (ha)"
    )
    crop_type = models.CharField(
        max_length=100,
        verbose_name="Crop Type"
    )
    
    class Meta:
        verbose_name = "Farm Profile" # Human-readable name
        verbose_name_plural = "Farm Profiles" # Plural name
        ordering = ["owner_id", "location"] # Default ordering

    def __str__(self):
        return f"{self.crop_type} farm at {self.location} (id={self.id})"


class FieldPlot(models.Model):
    """
    Represents a specific plot within a farm.
    Fields:
        farm: ForeignKey to FarmProfile this plot belongs to
        crop_variety: Specific variety of crop in this plot
    """
    farm = models.ForeignKey(
        FarmProfile,
        on_delete=models.CASCADE,# Delete plot if farm is deleted
        related_name="plots", # FarmProfile.plots gives all plots in a farm
        verbose_name="Farm"
    )
    crop_variety = models.CharField(
        max_length=100,
        verbose_name="Crop Variety"
    )
    
    class Meta:
        verbose_name = "Field Plot"
        verbose_name_plural = "Field Plots"
        ordering = ["farm_id", "id"]
   
    def __str__(self):
        return f"Plot {self.id} - {self.crop_variety} (farm {self.farm_id})"


class SensorReading(models.Model):
    """
    Represents a single sensor reading from a plot.
    Fields:
        timestamp: When the reading was taken
        plot: Which plot this reading is from
        sensor_type: Type of sensor (moisture, temperature, humidity)
        value: Numeric reading value
        source: Where the data came from (simulator, real sensor, etc.)
    """
    SENSOR_TYPE_CHOICES = [
        ("moisture", "Soil Moisture"), # Database value: "moisture", Display: "Soil Moisture"
        ("temperature", "Air Temperature"),
        ("humidity", "Air Humidity"),
    ]

    timestamp = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Timestamp"
    )
    plot = models.ForeignKey(
        FieldPlot,
        on_delete=models.CASCADE, # Delete readings if plot is deleted
        related_name="sensor_readings", # FieldPlot.sensor_readings gives all readings
        verbose_name="Field Plot"
    )
    sensor_type = models.CharField(
        max_length=20,
        choices=SENSOR_TYPE_CHOICES, # Limits to predefined choices
        verbose_name="Sensor Type"
    )
    value = models.FloatField(
        verbose_name="Value"
    )
    source = models.CharField(
        max_length=50,
        default="simulator", # Default value : source is the simulator
        help_text="Source of the data",
        verbose_name="Data Source"
    )

    class Meta:
        verbose_name = "Sensor Reading"
        verbose_name_plural = "Sensor Readings"
        ordering = ["-timestamp"] # Most recent reading first

    def __str__(self):
        return f"{self.get_sensor_type_display()}={self.value} at {self.timestamp}"


class AnomalyEvent(models.Model):
    """
    Represents a detected anomaly in sensor data.
    Fields:
        timestamp: When the anomaly was detected
        plot: Which plot has the anomaly
        anomaly_type: Type of anomaly (soil_moisture_low, temperature_high, etc.)
        severity: How severe the anomaly is
        model_confidence: ML model's confidence in this detection (0-1)
    """
    # Choices for severity field
    SEVERITY_CHOICES = [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
    ]

    timestamp = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Detection Time"
    )
    plot = models.ForeignKey(
        FieldPlot,
        on_delete=models.CASCADE,
        related_name="anomalies", # FieldPlot.anomalies gives all anomalies for a plot
        verbose_name="Field Plot"
    )
    anomaly_type = models.CharField(
        max_length=100,
        verbose_name="Anomaly Type"
    )
    severity = models.CharField(
        max_length=10,
        choices=SEVERITY_CHOICES,
        verbose_name="Severity Level"
    )
    model_confidence = models.FloatField(
        help_text="Confidence score from ML model (0–1)",
        default=0.0,
        verbose_name="Model Confidence"
    )

    class Meta:
        verbose_name = "Anomaly Event"
        verbose_name_plural = "Anomaly Events"
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.anomaly_type} ({self.severity}) on plot {self.plot.id}"



class AgentRecommendation(models.Model):
    """
    Represents an AI-generated recommendation for an anomaly.
    Fields:
        timestamp: When recommendation was generated
        anomaly_event: Which anomaly this recommendation is for
        recommended_action: What action to take
        explanation_text: Why this action is recommended
        confidence: AI's confidence in this recommendation (0-1)
    """
    timestamp = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Generation Time"
    )
    anomaly_event = models.ForeignKey(
        AnomalyEvent,
        on_delete=models.CASCADE,
        related_name="recommendations", # AnomalyEvent.recommendations gives all recs
        verbose_name="Anomaly Event"
    )
    recommended_action = models.TextField(
        verbose_name="Recommended Action"
    )
    explanation_text = models.TextField(
        verbose_name="Explanation"
    )
    confidence = models.FloatField(
        help_text="AI confidence in recommendation (0–1)",
        default=0.8,
        verbose_name="Confidence Score"
    )

    class Meta:
        verbose_name = "Agent Recommendation"
        verbose_name_plural = "Agent Recommendations"
        ordering = ["-timestamp"]

    def __str__(self):
        return f"Recommendation for {self.anomaly_event.anomaly_type} (conf: {self.confidence})"