# monitoring/urls.py - COMPLETE WITH ALL ENDPOINTS
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import (
    FarmProfileViewSet,
    FieldPlotViewSet,
    SensorReadingViewSet,
    AnomalyEventViewSet,
    AgentRecommendationViewSet,
    dashboard_stats,
    get_current_user,
    FarmProfileListView,
    FieldPlotListView,
    SensorReadingView,
    AnomalyEventListView,
    AgentRecommendationListView,
)

router = DefaultRouter()
router.register(r'farms', FarmProfileViewSet, basename='farm')
router.register(r'plots', FieldPlotViewSet, basename='plot')
router.register(r'sensor-readings', SensorReadingViewSet, basename='sensor-reading')
router.register(r'anomalies', AnomalyEventViewSet, basename='anomaly')
router.register(r'recommendations', AgentRecommendationViewSet, basename='recommendation')

urlpatterns = [
    # User info endpoint
    path('auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/user/', get_current_user, name='current_user'),
    
    # Dashboard stats
    path('dashboard/stats/', dashboard_stats, name='dashboard-stats'),
    
    # ViewSet routes
    path('', include(router.urls)),
]