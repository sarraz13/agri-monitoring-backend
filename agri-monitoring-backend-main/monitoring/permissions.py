from rest_framework import permissions
from .models import FarmProfile

#Defines who can access what in the API

class IsAdmin(permissions.BasePermission):
    """Allows access only to admin users or superusers."""
    def has_permission(self, request, view):
        # User must be authenticated AND be superuser
        return request.user.is_authenticated and (request.user.is_superuser)

class IsFarmer(permissions.BasePermission):
    """Allows access only to farmer users (non-staff)."""
    def has_permission(self, request, view):
        # User must be authenticated AND NOT be staff or superuser
        return request.user.is_authenticated and not (
            request.user.is_staff or 
            request.user.is_superuser
        )

class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Farmers can only access their own farms, Admins can access all.
    Logic:
    1. Admin users (staff/superuser) can do anything
    2. Farmers can only access their farms
    3. Ownership is checked by foreign key relationships
    """
    def has_permission(self, request, view):
        # Anyone can try, object-level permissions will handle the rest
        return request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        # Admin can do anything
        if request.user.is_staff or request.user.is_superuser:
            return True
        
        #Check ownership based on object type
        # For FarmProfile: check if user owns the farm
        if hasattr(obj, 'owner'):
            return obj.owner == request.user
        # For FieldPlot, check if farm user owns the farm
        if hasattr(obj, 'farm') and hasattr(obj.farm, 'owner'):
            return obj.farm.owner == request.user
        
        # For SensorReading/AnomalyEvent/AgentRecommendation, check through plot -> farm -> owner
        if hasattr(obj, 'plot') and hasattr(obj.plot, 'farm'):
            return obj.plot.farm.owner == request.user
        
        # For AgentRecommendation, check through anomaly -> plot -> farm -> owner
        if hasattr(obj, 'anomaly_event') and hasattr(obj.anomaly_event, 'plot'):
            return obj.anomaly_event.plot.farm.owner == request.user
        
        return False