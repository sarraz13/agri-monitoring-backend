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
        # id: auto-generated primary key
        # owner: user ID (foreign key)


class FieldPlotSerializer(serializers.ModelSerializer):
    class Meta:
        model = FieldPlot
        fields = [
            "id",
            "farm",
            "crop_variety",
        ]
        # farm: farm ID (foreign key)


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
        # plot: plot ID (foreign key)


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
        # plot: plot ID (foreign key)


class AgentRecommendationSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentRecommendation
        fields = '__all__'
        # Include all fields