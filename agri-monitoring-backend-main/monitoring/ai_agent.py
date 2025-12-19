"""
AI AGENT - RECOMMENDATION ENGINE
Generates agricultural recommendations based on detected anomalies.
Rule-based system following project requirements.
"""
from datetime import datetime
from monitoring.models import AnomalyEvent

class AgricultureAI:
    """
    AI Agent that analyzes anomalies and generates recommendations.
    Design principles:
    - Deterministic rule-based system
    - Template-based explanations
    - Uses model confidence scores
    """
    
    def __init__(self):
        ''' 
         Knowledge base: Maps anomaly types to recommended actions
         Each entry contains:
         - recommended_action: Single best action to take
         - explanation_template: Why this action is recommended
         - base_confidence: Default confidence for this rule
         - priority: How urgent this anomaly is'''
        self.knowledge_base = {
            'soil_moisture_low': {
                'recommended_action': "Increase irrigation frequency by 30% for the next 3 days and check for leaks.",
                'explanation_template': "Soil moisture below optimal range (30-70%). Sudden drop detected indicating possible irrigation failure.",
                'base_confidence': 0.85,
                'priority': 'high'
            },
            'soil_moisture_high': {
                'recommended_action': "Reduce irrigation, check drainage system, and aerate soil to prevent root rot.",
                'explanation_template': "Soil moisture above optimal range. Risk of waterlogging and fungal diseases.",
                'base_confidence': 0.80,
                'priority': 'medium'
            },
            'temperature_low': {
                'recommended_action': "Install thermal covers for sensitive crops and monitor for frost damage overnight.",
                'explanation_template': "Temperature below crop-specific optimal range. Risk of growth inhibition and frost damage.",
                'base_confidence': 0.75,
                'priority': 'medium'
            },
            'temperature_high': {
                'recommended_action': "Increase shade coverage and adjust irrigation to early morning/late evening to reduce heat stress.",
                'explanation_template': "Temperature above optimal range. Sustained high temperature detected (>5°C above normal).",
                'base_confidence': 0.82,
                'priority': 'high'
            },
            'humidity_high': {
                'recommended_action': "Improve ventilation, reduce irrigation frequency, and monitor for fungal diseases.",
                'explanation_template': "High humidity promotes fungal growth and reduces transpiration efficiency.",
                'base_confidence': 0.78,
                'priority': 'medium'
            },
            'humidity_low': {
                'recommended_action': "Increase misting frequency and monitor plant hydration to prevent drying.",
                'explanation_template': "Low humidity detected (<30%). Risk of excessive transpiration and plant dehydration.",
                'base_confidence': 0.76,
                'priority': 'low'
            },
            'sensor_failure': {
                'recommended_action': "Inspect sensor hardware, check connections, and verify data transmission.",
                'explanation_template': "Sensor failure or communication disruption detected. Data may be unreliable.",
                'base_confidence': 0.90,
                'priority': 'critical'
            },
            'drift_detected': {
                'recommended_action': "Calibrate sensors and verify readings against manual measurements.",
                'explanation_template': "Gradual sensor drift detected (>20% shift over 48h). Data accuracy compromised.",
                'base_confidence': 0.88,
                'priority': 'medium'
            },
            'temperature_high_heat_stress': {
                'recommended_action': "Implement evaporative cooling, increase irrigation during peak heat, and use shade nets.",
                'explanation_template': "Heat stress conditions detected. Temperature sustained above 32°C.",
                'base_confidence': 0.85,
                'priority': 'high'
            }
        }
    
    def generate_recommendation(self, anomaly_event):
        """
        Generate recommendation for an anomaly event.
        Returns dict with fields matching AgentRecommendation model:
        - recommended_action (TextField)
        - explanation_text (TextField)
        - confidence (FloatField)
        """
        try:
            anomaly_type = anomaly_event.anomaly_type
            severity = anomaly_event.severity
            
            # Check if we have a rule for this anomaly type
            if anomaly_type not in self.knowledge_base:
                # Default recommendation for unknown anomaly types
                return self._generate_default_recommendation(anomaly_event)
            
            rule = self.knowledge_base[anomaly_type]
            # Build the recommended action (deterministic - not random)
            recommended_action = rule['recommended_action']
            # Build explanation following the template format
            explanation_text = self._build_template_explanation(anomaly_event, rule)
            # Calculate confidence: combine model confidence with rule base confidence
            confidence = self._calculate_confidence(anomaly_event.model_confidence, rule['base_confidence'], severity)
            
            # Return the fields that exist in AgentRecommendation model
            return {
                'recommended_action': recommended_action,
                'explanation_text': explanation_text,
                'confidence': confidence
            }
            
        except Exception as e:
            # Fallback in case of any error
            return self._generate_default_recommendation(anomaly_event)
    
    def _build_template_explanation(self, anomaly_event, rule):
        """
        Build explanation following the exact template from project requirements.
        Format: "On {timestamp} at {time}, sensor readings detected an **{anomaly_type}** 
        (model confidence {score}). {Sensor trend}. Agent recommends {action}. 
        Confidence: {level}."
        """
        # Format timestamp
        timestamp_str = anomaly_event.timestamp.strftime("%Y-%m-%d at %H:%M")
        
        # Get model confidence (from anomaly detection ML model)
        model_confidence = anomaly_event.model_confidence
        
        # Get plot information for context
        plot_name = "the plot" #fallback
        if hasattr(anomaly_event, 'plot') and anomaly_event.plot:
            if hasattr(anomaly_event.plot, 'crop_variety') and anomaly_event.plot.crop_variety:
                plot_name = anomaly_event.plot.crop_variety
        
        # Determine confidence level based on severity
        confidence_level = self._get_confidence_level(anomaly_event.severity)
        
        # Build the template explanation
        explanation = (
            f"On {timestamp_str}, sensor readings detected an **{anomaly_event.anomaly_type}** "
            f"on {plot_name} (model confidence: {model_confidence:.2f}). "
            f"{rule['explanation_template']} "
            f"Agent recommends: {rule['recommended_action']} "
            f"Confidence: {confidence_level}."
        )
        
        return explanation
    
    def _calculate_confidence(self, model_confidence, rule_confidence, severity):
        """
        Calculate overall confidence score (0-1)
        Combines ML model confidence with rule base confidence
        Adjusts based on anomaly severity
        """

        # Weight: 60% from ML model, 40% from rule base
        base_score = (model_confidence * 0.6) + (rule_confidence * 0.4)
        # Adjust based on severity (higher severity = higher confidence adjustment)
        severity_multiplier = {
            'low': 0.9,
            'medium': 1.0,
            'high': 1.1,
            'critical': 1.2
        }.get(severity, 1.0)
        
        confidence = base_score * severity_multiplier
        
        # Ensure within 0-1 range
        return min(max(confidence, 0.0), 1.0)
    
    def _get_confidence_level(self, severity):
        #Convert confidence score to human-readable level
        return {
            'low': 'low',
            'medium': 'medium',
            'high': 'high',
            'critical': 'very high'
        }.get(severity, 'medium')
    
    def _generate_default_recommendation(self, anomaly_event):
        """Generate default recommendation for unknown anomaly types"""
        timestamp_str = anomaly_event.timestamp.strftime("%Y-%m-%d at %H:%M")
        
        explanation = (
            f"On {timestamp_str}, sensor readings detected an **{anomaly_event.anomaly_type}** "
            f"(model confidence: {anomaly_event.model_confidence:.2f}). "
            f"Uncommon anomaly type detected. Agent recommends monitoring the plot closely "
            f"and conducting manual inspection to verify conditions. "
            f"Confidence: medium."
        )
        
        return {
            'recommended_action': "Monitor the plot closely and conduct manual inspection to verify conditions.",
            'explanation_text': explanation,
            'confidence': 0.5  # Default medium confidence
        }
    
    def analyze_anomaly(self, anomaly_event, sensor_data=None):
        """
        Legacy method for backward compatibility
        Returns analysis with only the fields needed for your views
        """
        recommendation = self.generate_recommendation(anomaly_event)
        
        return {
            'anomaly_id': anomaly_event.id,
            'recommended_action': recommendation['recommended_action'],
            'explanation_text': recommendation['explanation_text'],
            'confidence': recommendation['confidence']
        }


# Global instance for easy import
ai_agent = AgricultureAI()