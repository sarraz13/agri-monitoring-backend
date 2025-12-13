from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.postgres.fields import JSONField
from django.core.serializers.json import DjangoJSONEncoder

User = get_user_model()

# -------------------- Core Models -------------------- #

class FarmProfile(models.Model):
    """
    Core Django Model: FarmProfile
    - owner: User foreign key
    - location: CharField
    - size: FloatField (hectares)
    - crop_type: CharField
    """
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="farms",
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
        verbose_name = "Farm Profile"
        verbose_name_plural = "Farm Profiles"
        ordering = ["owner_id", "location"]

    def __str__(self):
        return f"{self.crop_type} farm at {self.location} (id={self.id})"


class FieldPlot(models.Model):
    """
    Core Django Model: FieldPlot
    - farm: FarmProfile foreign key
    - crop_variety: CharField
    """
    farm = models.ForeignKey(
        FarmProfile,
        on_delete=models.CASCADE,
        related_name="plots",
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
    Core Django Model: SensorReading
    - timestamp: DateTimeField
    - plot: FieldPlot foreign key
    - sensor_type: choices (moisture, temperature, humidity)
    - value: FloatField
    - source: CharField (simulator)
    """
    SENSOR_TYPE_CHOICES = [
        ("moisture", "Soil Moisture"),
        ("temperature", "Air Temperature"),
        ("humidity", "Air Humidity"),
    ]

    timestamp = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Timestamp"
    )
    plot = models.ForeignKey(
        FieldPlot,
        on_delete=models.CASCADE,
        related_name="sensor_readings",
        verbose_name="Field Plot"
    )
    sensor_type = models.CharField(
        max_length=20,
        choices=SENSOR_TYPE_CHOICES,
        verbose_name="Sensor Type"
    )
    value = models.FloatField(
        verbose_name="Value"
    )
    source = models.CharField(
        max_length=50,
        default="simulator",
        help_text="Source of the data",
        verbose_name="Data Source"
    )

    class Meta:
        verbose_name = "Sensor Reading"
        verbose_name_plural = "Sensor Readings"
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.get_sensor_type_display()}={self.value} at {self.timestamp}"


class AnomalyEvent(models.Model):
    """
    Core Django Model: AnomalyEvent
    - timestamp: DateTimeField (auto_now_add)
    - plot: FieldPlot foreign key
    - anomaly_type: CharField
    - severity: choices (low, medium, high)
    - model_confidence: FloatField (0-1)
    """
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
        related_name="anomalies",
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


# -------------------- AI Agent Model -------------------- #

class AgentRecommendation(models.Model):
    """
    Academic Model: AgentRecommendation
    - timestamp: DateTimeField (auto_now_add)
    - anomaly_event: AnomalyEvent foreign key
    - recommended_action: TextField
    - explanation_text: TextField
    - confidence: FloatField (0-1)
    """
    timestamp = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Generation Time"
    )
    anomaly_event = models.ForeignKey(
        AnomalyEvent,
        on_delete=models.CASCADE,
        related_name="recommendations",
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