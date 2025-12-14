from django.apps import AppConfig

class MonitoringConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'monitoring'
    
    def ready(self):
        # Import signals to register them
        import monitoring.signals
        print("✅ Signals registered for automatic anomaly detection")