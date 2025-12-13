from rest_framework import serializers
from .models import (
    FarmProfile,
    FieldPlot,
    SensorReading,
    AnomalyEvent,
    AgentRecommendation,
)


class FarmProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = FarmProfile
        fields = [
            "id",
            "owner",
            "location",
            "size",
            "crop_type",
        ]


class FieldPlotSerializer(serializers.ModelSerializer):
    class Meta:
        model = FieldPlot
        fields = [
            "id",
            "farm",
            "crop_variety",
        ]


class SensorReadingSerializer(serializers.ModelSerializer):
    class Meta:
        model = SensorReading
        fields = [
            "id",
            "timestamp",
            "plot",
            "sensor_type",
            "value",
            "source",
        ]


class AnomalyEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnomalyEvent
        fields = [
            "id",
            "timestamp",
            "plot",
            "anomaly_type",
            "severity",
            "model_confidence",
        ]


class AgentRecommendationSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentRecommendation
        fields = '__all__'