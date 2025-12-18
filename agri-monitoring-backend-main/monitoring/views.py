from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics, viewsets
from rest_framework.permissions import IsAuthenticated, AllowAny,BasePermission
from rest_framework.decorators import api_view, permission_classes, action
from django.db.models import Count, Q
from datetime import datetime
import traceback
from django.db import connection
from .ai_agent import ai_agent
from .models import (
    FarmProfile,
    FieldPlot,
    SensorReading,
    AnomalyEvent,
    AgentRecommendation,
)

from .serializers import (
    FarmProfileSerializer,
    FieldPlotSerializer,
    SensorReadingSerializer,
    AnomalyEventSerializer,
    AgentRecommendationSerializer,
)

# Import custom permissions
from .permissions import IsOwnerOrAdmin  # We'll create this file

# -------------------- User Info Endpoint -------------------- #

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_current_user(request):
    """
    GET /api/auth/user/
    Returns current user information including role
    """
    user = request.user
    
    return Response({
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'role': 'admin' if (user.is_staff or user.is_superuser) else 'farmer',
        'is_staff': user.is_staff,
        'is_superuser': user.is_superuser,
    })

# -------------------- Agent Recommendations ViewSet -------------------- #

# -------------------- Custom Permission -------------------- #
class AgentRecommendationPermission(BasePermission):
    """
    Handles permissions for AgentRecommendation:
    - Admins can do everything.
    - Owners of the plot can GET/POST/UPDATE their recommendations.
    - POST 'recommend' is allowed for any authenticated user (with ownership check in method).
    """
    def has_permission(self, request, view):
        # All actions require authentication
        if not request.user.is_authenticated:
            return False
        # recommend POST can be allowed for authenticated users
        return True

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.is_staff or user.is_superuser:
            return True
        # Owner can access only their plot's recommendations
        return obj.anomaly_event.plot.farm.owner == user


# -------------------- AgentRecommendation ViewSet -------------------- #
class AgentRecommendationViewSet(viewsets.ModelViewSet):
    queryset = AgentRecommendation.objects.all().select_related(
        'anomaly_event', 'anomaly_event__plot', 'anomaly_event__plot__farm'
    )
    serializer_class = AgentRecommendationSerializer
    permission_classes = [AgentRecommendationPermission]

    def get_queryset(self):
        user = self.request.user
        queryset = self.queryset

        if not (user.is_staff or user.is_superuser):
            queryset = queryset.filter(anomaly_event__plot__farm__owner=user)

        # Optional filters
        plot_id = self.request.query_params.get('plot_id')
        if plot_id:
            queryset = queryset.filter(anomaly_event__plot_id=plot_id)

        anomaly_id = self.request.query_params.get('anomaly')
        if anomaly_id:
            queryset = queryset.filter(anomaly_event_id=anomaly_id)

        return queryset

    @action(detail=True, methods=['post'])
    def recommend(self, request, pk=None):
        """
        POST /api/anomalies/{id}/recommend/
        Uses AI Agent to generate recommendation
        """
        try:
            anomaly = self.get_object()

            # Permission check
            if not (request.user.is_staff or request.user.is_superuser):
                if anomaly.plot.farm.owner != request.user:
                    return Response({'error': 'Not authorized'}, status=403)

            # Check if recommendation already exists
            existing_rec = AgentRecommendation.objects.filter(anomaly_event=anomaly).first()
            if existing_rec:
                serializer = AgentRecommendationSerializer(existing_rec)
                return Response(serializer.data)

            # Use AI Agent ONLY
            recommendation_data = ai_agent.generate_recommendation(anomaly)
            
            # Create the AgentRecommendation
            rec = AgentRecommendation.objects.create(
                anomaly_event=anomaly,
                recommended_action=recommendation_data['recommended_action'],
                explanation_text=recommendation_data['explanation_text'],
                confidence=recommendation_data['confidence']
            )

            serializer = AgentRecommendationSerializer(rec)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except AnomalyEvent.DoesNotExist:
            return Response({'error': 'Anomaly not found'}, status=404)
        except KeyError as e:
            return Response({'error': f'AI agent missing required field: {str(e)}'}, status=500)
        except Exception as e:
            return Response({'error': str(e)}, status=500)
    
# -------------------- Farms ViewSet -------------------- #

class FarmProfileViewSet(viewsets.ModelViewSet):
    queryset = FarmProfile.objects.all()
    serializer_class = FarmProfileSerializer
    permission_classes = [IsOwnerOrAdmin]
    
    def get_queryset(self):
        """Farmers see only their farms, Admins see all"""
        user = self.request.user
        
        if user.is_staff or user.is_superuser:
            return FarmProfile.objects.all()
        
        # Farmers only see their own farms
        return FarmProfile.objects.filter(owner=user)
    
    def perform_create(self, serializer):
        """Auto-set owner when creating farm"""
        serializer.save(owner=self.request.user)


# -------------------- Field Plots ViewSet -------------------- #

class FieldPlotViewSet(viewsets.ModelViewSet):
    queryset = FieldPlot.objects.all()
    serializer_class = FieldPlotSerializer
    permission_classes = [IsOwnerOrAdmin]

    def get_queryset(self):
        """Farmers see only plots from their farms, Admins see all"""
        user = self.request.user
        
        if user.is_staff or user.is_superuser:
            return FieldPlot.objects.all()
        
        # Farmers only see plots from their farms
        return FieldPlot.objects.filter(farm__owner=user)

    def list(self, request):
        """Retourne la liste des parcelles avec statuts et compteurs d'anomalies"""
        plots = self.get_queryset()  # Use filtered queryset
        
        plots_data = []
        for plot in plots:
            anomaly_count = AnomalyEvent.objects.filter(plot=plot).count()
            
            status_value = 'normal'
            if anomaly_count > 0:
                high_severity = AnomalyEvent.objects.filter(
                    plot=plot, 
                    severity='high'
                ).exists()
                status_value = 'alert' if high_severity else 'warning'
            
            plot_data = {
                'id': plot.id,
                'crop_variety': plot.crop_variety,
                'status': status_value,
                'anomaly_count': anomaly_count,
                'farm': plot.farm.id if plot.farm else None
            }
            plots_data.append(plot_data)
        
        return Response(plots_data)

    def retrieve(self, request, pk=None):
        """Retourne les détails d'une parcelle spécifique"""
        try:
            plot = self.get_queryset().get(pk=pk)  # Use filtered queryset
            anomaly_count = AnomalyEvent.objects.filter(plot=plot).count()
            
            status_value = 'normal'
            if anomaly_count > 0:
                high_severity = AnomalyEvent.objects.filter(
                    plot=plot, 
                    severity='high'
                ).exists()
                status_value = 'alert' if high_severity else 'warning'
            
            plot_data = {
                'id': plot.id,
                'crop_variety': plot.crop_variety,
                'status': status_value,
                'anomaly_count': anomaly_count,
                'farm': plot.farm.id if plot.farm else None
            }
            
            return Response(plot_data)
        except FieldPlot.DoesNotExist:
            return Response(
                {'error': 'Plot not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )


# -------------------- Sensor Readings ViewSet -------------------- #

class SensorReadingViewSet(viewsets.ModelViewSet):
    queryset = SensorReading.objects.all().order_by('-timestamp')
    serializer_class = SensorReadingSerializer
    permission_classes = [IsOwnerOrAdmin]

    def get_queryset(self):
        """Farmers see only readings from their farms, Admins see all"""
        user = self.request.user
        
        if user.is_staff or user.is_superuser:
            return SensorReading.objects.all().order_by('-timestamp')
        
        # Farmers only see readings from their farms
        return SensorReading.objects.filter(plot__farm__owner=user).order_by('-timestamp')

    def list(self, request):
        """Retourne les lectures de capteurs, optionnellement filtrées par parcelle"""
        field_plot_id = request.query_params.get('field_plot', None)
        
        # Start with filtered queryset
        readings = self.get_queryset()
        
        if field_plot_id:
            readings = readings.filter(plot_id=field_plot_id)
        
        # Limit to 100 most recent
        readings = readings[:100]
        
        readings_data = []
        for reading in readings:
            # FIXED: Safe access to plot relationship
            plot_id = None
            try:
                plot_id = reading.plot.id if hasattr(reading, 'plot') and reading.plot else None
            except:
                pass
            
            readings_data.append({
                'id': reading.id,
                'timestamp': reading.timestamp.isoformat(),
                'sensor_type': reading.sensor_type,
                'value': float(reading.value),
                'plot': plot_id  # Use safe access
            })
        
        return Response(readings_data)


# -------------------- Anomaly Events ViewSet -------------------- #

class AnomalyEventViewSet(viewsets.ModelViewSet):
    queryset = AnomalyEvent.objects.all().order_by('-timestamp')
    serializer_class = AnomalyEventSerializer
    permission_classes = [IsOwnerOrAdmin]

    def get_queryset(self):
        """Farmers see only anomalies from their farms, Admins see all"""
        user = self.request.user
        
        if user.is_staff or user.is_superuser:
            return AnomalyEvent.objects.all().order_by('-timestamp')
        
        # Farmers only see anomalies from their farms
        return AnomalyEvent.objects.filter(plot__farm__owner=user).order_by('-timestamp')

    def list(self, request):
        """Retourne les anomalies, optionnellement filtrées par parcelle"""
        field_plot_id = self.request.query_params.get('field_plot', None)
        
        # Start with filtered queryset
        anomalies = self.get_queryset()
        
        if field_plot_id:
            anomalies = anomalies.filter(plot_id=field_plot_id)
        
        anomalies_data = []
        for anomaly in anomalies:
            recommendation = None
            try:
                rec = AgentRecommendation.objects.filter(
                    anomaly_event_id=anomaly.id
                ).first()
                if rec:
                    recommendation = rec.recommended_action
            except:
                pass
            
            # FIXED: Safe access to plot and crop_variety
            field_plot_name = 'Unknown'
            plot_id = None  # ADD THIS
            try:
                if hasattr(anomaly, 'plot') and anomaly.plot:
                    # Try to get crop_variety, fall back to name, fall back to id
                    if hasattr(anomaly.plot, 'crop_variety') and anomaly.plot.crop_variety:
                        field_plot_name = anomaly.plot.crop_variety
                    elif hasattr(anomaly.plot, 'name') and anomaly.plot.name:
                        field_plot_name = anomaly.plot.name
                    else:
                        field_plot_name = f'Plot {anomaly.plot.id}'
                    
                    plot_id = anomaly.plot.id  # ADD THIS
            except:
                pass
            
            anomalies_data.append({
                'id': anomaly.id,
                'anomaly_type': anomaly.anomaly_type,
                'severity': anomaly.severity,
                'confidence_score': float(anomaly.model_confidence),
                'detected_at': anomaly.timestamp.isoformat(),
                'field_plot_name': field_plot_name,  # Use safe access
                'plot': plot_id,  # ADD THIS - plot ID for navigation
                'sensor_reading_id': None,
                'agent_recommendation': recommendation,
                'resolved': False
            })
        
        return Response(anomalies_data)

    def retrieve(self, request, pk=None):
        """Retourne les détails d'une anomalie spécifique"""
        try:
            anomaly = self.get_queryset().get(pk=pk)  # Use filtered queryset
            
            recommendation = None
            try:
                rec = AgentRecommendation.objects.filter(
                    anomaly_event_id=anomaly.id
                ).first()
                if rec:
                    recommendation = rec.recommended_action
            except:
                pass
            
            anomaly_data = {
                'id': anomaly.id,
                'anomaly_type': anomaly.anomaly_type,
                'severity': anomaly.severity,
                'confidence_score': float(anomaly.model_confidence),
                'detected_at': anomaly.timestamp.isoformat(),
                'field_plot_name': anomaly.plot.crop_variety if anomaly.plot else 'Unknown',
                'plot': anomaly.plot.id if anomaly.plot else None,  # ADD THIS
                'sensor_reading_id': None,
                'agent_recommendation': recommendation,
                'resolved': False
            }
            return Response(anomaly_data)
        except AnomalyEvent.DoesNotExist:
            return Response(
                {'error': 'Anomaly not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['post'])
    def recommend(self, request, pk=None):
        """
        POST /api/anomalies/{id}/recommend/
        Generates a recommendation for an anomaly using AI agent
        """
        try:
            anomaly = self.get_object()

            # Permission check
            if not (request.user.is_staff or request.user.is_superuser):
                if anomaly.plot.farm.owner != request.user:
                    return Response({'error': 'Not authorized'}, status=403)

            # Check if recommendation already exists
            existing_rec = AgentRecommendation.objects.filter(anomaly_event=anomaly).first()
            if existing_rec:
                serializer = AgentRecommendationSerializer(existing_rec)
                return Response(serializer.data)

            # Generate recommendation using AI agent ONLY
            recommendation_data = ai_agent.generate_recommendation(anomaly)
            
            # Create recommendation with data from AI agent
            rec = AgentRecommendation.objects.create(
                anomaly_event=anomaly,
                recommended_action=recommendation_data['recommended_action'],
                explanation_text=recommendation_data['explanation_text'],
                confidence=recommendation_data['confidence']
            )

            serializer = AgentRecommendationSerializer(rec)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except AnomalyEvent.DoesNotExist:
            return Response({'error': 'Anomaly not found'}, status=404)
        except KeyError as e:
            return Response({'error': f'AI agent missing required field: {str(e)}'}, status=500)
        except Exception as e:
            traceback.print_exc()
            return Response({'error': str(e)}, status=500)


# -------------------- Dashboard Stats -------------------- #

@api_view(['GET'])
@permission_classes([IsAuthenticated])  # CHANGED: Now requires authentication
def dashboard_stats(request):
    """
    GET /api/dashboard/stats/
    Retourne les statistiques du dashboard
    """
    user = request.user
    
    if user.is_staff or user.is_superuser:
        # Admin sees all stats
        total_farms = FarmProfile.objects.count()
        total_plots = FieldPlot.objects.count()
        total_anomalies = AnomalyEvent.objects.count()
        active_alerts = AnomalyEvent.objects.filter(severity__in=['high', 'medium']).count()
    else:
        # Farmer sees only their stats
        total_farms = FarmProfile.objects.filter(owner=user).count()
        total_plots = FieldPlot.objects.filter(farm__owner=user).count()
        total_anomalies = AnomalyEvent.objects.filter(plot__farm__owner=user).count()
        active_alerts = AnomalyEvent.objects.filter(
            plot__farm__owner=user,
            severity__in=['high', 'medium']
        ).count()
    
    return Response({
        'total_farms': total_farms,
        'total_plots': total_plots,
        'total_anomalies': total_anomalies,
        'active_alerts': active_alerts
    })


# -------------------- Legacy Views (Compatibilité) -------------------- #

class FarmProfileListView(generics.ListAPIView):
    queryset = FarmProfile.objects.all()
    serializer_class = FarmProfileSerializer
    permission_classes = [IsOwnerOrAdmin]  # CHANGED
    
    def get_queryset(self):
        user = self.request.user
        
        if user.is_staff or user.is_superuser:
            return FarmProfile.objects.all()
        
        return FarmProfile.objects.filter(owner=user)


class FieldPlotListView(generics.ListAPIView):
    serializer_class = FieldPlotSerializer
    permission_classes = [IsOwnerOrAdmin]  # CHANGED

    def get_queryset(self):
        user = self.request.user
        
        if user.is_staff or user.is_superuser:
            qs = FieldPlot.objects.all()
        else:
            qs = FieldPlot.objects.filter(farm__owner=user)
        
        farm_id = self.request.query_params.get("farm")
        if farm_id is not None:
            qs = qs.filter(farm_id=farm_id)
        return qs


class SensorReadingView(APIView):
    permission_classes = [IsOwnerOrAdmin]  # CHANGED
    
    def get(self, request):
        user = request.user
        plot_id = request.query_params.get("plot")
        
        if user.is_staff or user.is_superuser:
            queryset = SensorReading.objects.all().order_by("-timestamp")
        else:
            queryset = SensorReading.objects.filter(
                plot__farm__owner=user
            ).order_by("-timestamp")

        if plot_id is not None:
            queryset = queryset.filter(plot_id=plot_id)

        serializer = SensorReadingSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        # This should still work for simulator, but check permission
        serializer = SensorReadingSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        reading = serializer.save()

        return Response(
            SensorReadingSerializer(reading).data,
            status=status.HTTP_201_CREATED,
        )


class AnomalyEventListView(generics.ListAPIView):
    serializer_class = AnomalyEventSerializer
    permission_classes = [IsOwnerOrAdmin]  # CHANGED

    def get_queryset(self):
        user = self.request.user
        
        if user.is_staff or user.is_superuser:
            qs = AnomalyEvent.objects.all().order_by("-timestamp")
        else:
            qs = AnomalyEvent.objects.filter(
                plot__farm__owner=user
            ).order_by("-timestamp")
        
        plot_id = self.request.query_params.get("plot")
        if plot_id is not None:
            qs = qs.filter(plot_id=plot_id)
        return qs


class AgentRecommendationListView(generics.ListAPIView):
    serializer_class = AgentRecommendationSerializer
    permission_classes = [IsOwnerOrAdmin]  # CHANGED

    def get_queryset(self):
        user = self.request.user
        queryset = AgentRecommendation.objects.all()

        if not (user.is_staff or user.is_superuser):
            # Only recommendations belonging to user’s plots
            queryset = queryset.filter(
                anomaly_event__plot__farm__owner=user
            ).select_related('anomaly_event', 'anomaly_event__plot')

        # Optional: filter by plot_id
        plot_id = self.request.query_params.get('plot_id')
        if plot_id:
            queryset = queryset.filter(anomaly_event__plot_id=plot_id)

        # Optional: filter by anomaly_id
        anomaly_id = self.request.query_params.get('anomaly')
        if anomaly_id:
            queryset = queryset.filter(anomaly_event_id=anomaly_id)

        return queryset
