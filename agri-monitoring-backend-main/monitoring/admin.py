from django.contrib import admin
from .models import (
    FarmProfile,
    FieldPlot,
    SensorReading,
    AnomalyEvent,
    AgentRecommendation
)

admin.site.register(FarmProfile)
admin.site.register(FieldPlot)
admin.site.register(SensorReading)
admin.site.register(AnomalyEvent)
admin.site.register(AgentRecommendation)
