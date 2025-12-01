from django.apps import AppConfig

class MonitoringConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'monitoring'
    
    def ready(self):
        # Importe les signaux pour les activer
        import monitoring.signals
        print("✅ App 'monitoring' prête - Signaux d'anomalie activés")