import { Component, OnInit, OnDestroy, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { ApiService } from '../../services/api.service';
import { AuthService } from '../../services/auth.service';
import { Subscription, timer, forkJoin, of } from 'rxjs';
import { catchError, finalize } from 'rxjs/operators';

@Component({
  selector: 'app-alerts',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './alerts.component.html',
  styleUrls: ['./alerts.component.css']
})
export class AlertsComponent implements OnInit, OnDestroy {
  anomalies: any[] = [];
  selectedFilter: 'all' | 'high' | 'medium' | 'low' = 'all';
  refreshCountdown = 30;
  isLoading = true;
  errorMessage = '';
  
  private refreshSub?: Subscription;
  private processingAnomalies = new Set<number>();

  constructor(
    private apiService: ApiService,
    private router: Router,
    private cdr: ChangeDetectorRef,
    private authService: AuthService
  ) {}

  ngOnInit() {
    this.loadAnomalies();
    this.startAutoRefresh();
  }

  ngOnDestroy() {
    this.refreshSub?.unsubscribe();
    this.processingAnomalies.clear();
  }

  // ==================== DATA LOADING ====================
  
  loadAnomalies() {
    this.isLoading = true;
    this.errorMessage = '';
    
    this.apiService.getAnomalies().subscribe({
      next: (anomalies: any[]) => {
        // Initialize anomalies with recommendation state
        this.anomalies = anomalies.map(anomaly => ({
          ...anomaly,
          loadingRecommendation: false,
          agent_recommendation: null // Start null - will be loaded separately
        }));
        
        // Load existing recommendations for all anomalies
        this.loadExistingRecommendationsForAll();
        
        this.isLoading = false;
        this.cdr.detectChanges();
      },
      error: (err) => {
        console.error('Error loading anomalies:', err);
        this.errorMessage = 'Failed to load alerts. Please try again.';
        this.isLoading = false;
        this.cdr.detectChanges();
      }
    });
  }

  loadExistingRecommendationsForAll(): void {
    if (this.anomalies.length === 0) return;
    
    // Create parallel requests for each anomaly
    const recommendationRequests = this.anomalies.map(anomaly => 
      this.apiService.getRecommendationsByAnomaly(anomaly.id).pipe(
        catchError(() => of([])) // Empty array if no recommendation exists
      )
    );

    forkJoin(recommendationRequests).subscribe({
      next: (allRecommendations: any[][]) => {
        allRecommendations.forEach((recommendations, index) => {
          if (recommendations && recommendations.length > 0) {
            const recommendation = recommendations[0];
            this.anomalies[index].agent_recommendation = this.formatRecommendation(recommendation);
          }
        });
        this.cdr.detectChanges();
      },
      error: (err) => {
        console.log('Some recommendations failed to load:', err);
        // Continue anyway - not critical
      }
    });
  }

  // ==================== RECOMMENDATION WORKFLOW ====================
  
  generateRecommendation(anomaly: any): void {
    if (!anomaly || anomaly.loadingRecommendation || this.processingAnomalies.has(anomaly.id)) {
      return;
    }
    
    console.log('Generating AI recommendation for anomaly:', anomaly.id);
    
    // Set loading state
    anomaly.loadingRecommendation = true;
    this.processingAnomalies.add(anomaly.id);
    this.cdr.detectChanges();
    
    // Call API to generate recommendation
    this.apiService.generateRecommendation(anomaly.id).subscribe({
      next: (response: any) => {
        console.log('AI Agent response:', response);
        
        // Format and store the recommendation
        anomaly.agent_recommendation = this.formatRecommendation(response);
        anomaly.loadingRecommendation = false;
        this.processingAnomalies.delete(anomaly.id);
        
        this.cdr.detectChanges();
        console.log('Recommendation generated successfully');
      },
      error: (error) => {
        console.error('Error generating recommendation:', error);
        
        // Fallback to mock recommendation
        anomaly.agent_recommendation = this.getMockRecommendation(anomaly);
        anomaly.loadingRecommendation = false;
        this.processingAnomalies.delete(anomaly.id);
        
        this.cdr.detectChanges();
      }
    });
  }

  regenerateRecommendation(anomaly: any): void {
    // Clear existing recommendation and generate new one
    anomaly.agent_recommendation = null;
    this.generateRecommendation(anomaly);
  }

  // ==================== HELPER METHODS ====================
  
  private formatRecommendation(response: any): any {
    // Handle different API response formats consistently
    if (response && response.recommended_action) {
      return {
        recommended_action: response.recommended_action,
        explanation_text: response.explanation_text || 'AI-generated recommendation',
        confidence: response.confidence || 0.8,
        timestamp: new Date().toISOString()
      };
    } else if (response && response.recommendation) {
      return {
        recommended_action: response.recommendation,
        explanation_text: response.explanation || 'Generated by AI agent',
        confidence: response.confidence || 0.7,
        timestamp: new Date().toISOString()
      };
    } else if (response && response.action) {
      return {
        recommended_action: response.action,
        explanation_text: response.explanation || 'AI analysis completed',
        confidence: response.confidence || 0.75,
        timestamp: new Date().toISOString()
      };
    }
    
    // Default fallback
    return {
      recommended_action: 'Monitor anomaly and adjust farming practices',
      explanation_text: 'Temperature/moisture imbalance detected',
      confidence: 0.75,
      timestamp: new Date().toISOString()
    };
  }

  private getMockRecommendation(anomaly: any): any {
    // Consistent mock recommendations based on anomaly type
    const type = anomaly.anomaly_type?.toLowerCase() || '';
    const severity = anomaly.severity || 'medium';
    
    const mockRecommendations = [
      {
        condition: type.includes('moisture') && type.includes('low'),
        action: 'Increase irrigation by 20-30% for the next 48 hours',
        explanation: 'Soil moisture below optimal range. Plants showing early signs of water stress.',
        confidence: 0.85
      },
      {
        condition: type.includes('moisture') && type.includes('high'),
        action: 'Stop irrigation immediately and improve drainage systems',
        explanation: 'Excess soil moisture detected. Risk of root rot and fungal diseases.',
        confidence: 0.82
      },
      {
        condition: type.includes('temperature') && type.includes('high'),
        action: 'Deploy shade nets and increase irrigation frequency',
        explanation: 'High temperature stress detected. Crops at risk of heat damage.',
        confidence: 0.8
      },
      {
        condition: type.includes('temperature') && type.includes('low'),
        action: 'Activate frost protection and reduce irrigation',
        explanation: 'Low temperature alert. Protect sensitive crops from frost damage.',
        confidence: 0.78
      },
      {
        condition: type.includes('humidity') && type.includes('high'),
        action: 'Improve ventilation and monitor for fungal diseases',
        explanation: 'High humidity promotes fungal growth and reduces transpiration.',
        confidence: 0.75
      }
    ];
    
    // Find matching recommendation
    const matchedRec = mockRecommendations.find(rec => rec.condition);
    
    if (matchedRec) {
      return {
        recommended_action: matchedRec.action,
        explanation_text: matchedRec.explanation,
        confidence: matchedRec.confidence,
        timestamp: new Date().toISOString(),
        source: 'ai_agent_mock'
      };
    }
    
    // Default recommendation based on severity
    const defaultActions = {
      high: {
        action: 'Immediate field inspection required. Consider emergency measures.',
        explanation: 'Critical anomaly detected. High impact on crop health.',
        confidence: 0.9
      },
      medium: {
        action: 'Schedule inspection within 24 hours and adjust practices.',
        explanation: 'Moderate risk anomaly. Monitor closely.',
        confidence: 0.75
      },
      low: {
        action: 'Monitor trend and adjust during next regular maintenance.',
        explanation: 'Minor anomaly. Low immediate risk.',
        confidence: 0.65
      }
    };
    
    const defaultRec = defaultActions[severity as keyof typeof defaultActions] || defaultActions.medium;
    
    return {
      recommended_action: defaultRec.action,
      explanation_text: defaultRec.explanation,
      confidence: defaultRec.confidence,
      timestamp: new Date().toISOString(),
      source: 'ai_agent_mock'
    };
  }

  // ==================== TEMPLATE HELPERS ====================
  
  getRecommendationAction(anomaly: any): string {
    if (!anomaly?.agent_recommendation) return '';
    return anomaly.agent_recommendation.recommended_action || 
           anomaly.agent_recommendation.action || 
           'No recommendation available';
  }

  getRecommendationExplanation(anomaly: any): string {
    if (!anomaly?.agent_recommendation) return '';
    return anomaly.agent_recommendation.explanation_text || 
           anomaly.agent_recommendation.explanation || 
           '';
  }

  getRecommendationConfidence(anomaly: any): number {
    if (!anomaly?.agent_recommendation) return 0;
    return anomaly.agent_recommendation.confidence || 0;
  }

  getConfidenceLevel(anomaly: any): string {
    const confidence = this.getRecommendationConfidence(anomaly);
    if (confidence >= 0.8) return 'high';
    if (confidence >= 0.6) return 'medium';
    return 'low';
  }

  isRecommendationNew(anomaly: any): boolean {
    if (!anomaly?.agent_recommendation?.timestamp) return false;
    
    const recDate = new Date(anomaly.agent_recommendation.timestamp);
    const now = new Date();
    const hoursDiff = (now.getTime() - recDate.getTime()) / (1000 * 60 * 60);
    
    return hoursDiff < 24; // New if less than 24 hours old
  }

  // ==================== FILTERING & UI ====================
  
  startAutoRefresh(): void {
    this.refreshSub = timer(0, 1000).subscribe(() => {
      this.refreshCountdown--;
      if (this.refreshCountdown <= 0) {
        this.loadAnomalies();
        this.refreshCountdown = 30;
      }
    });
  }

  filterBy(severity: 'all' | 'high' | 'medium' | 'low'): void {
    this.selectedFilter = severity;
  }

  getFilteredAnomalies(): any[] {
    if (this.selectedFilter === 'all') {
      return this.anomalies;
    }
    return this.anomalies.filter(a => a.severity === this.selectedFilter);
  }

  formatDate(dateString: string): string {
    if (!dateString) return '--';
    return new Date(dateString).toLocaleString('fr-FR', { 
      day: '2-digit', 
      month: '2-digit',
      hour: '2-digit', 
      minute: '2-digit' 
    });
  }

  viewPlotDetails(anomaly: any): void {
    console.log('DEBUG: Anomaly object:', anomaly);
    
    // Get plot ID from the anomaly
    const plotId = anomaly.plot || anomaly.plotId || anomaly.plot_id;
    
    if (!plotId || isNaN(plotId)) {
      console.error('No valid plot ID found in anomaly:', anomaly);
      alert('Cannot view plot: Plot information is missing');
      return;
    }
    
    console.log('Navigating to plot:', plotId);
    this.router.navigate(['/plot-details', plotId]);
  }

  logout(): void {
    this.authService.logout();
    this.router.navigate(['/login']);
  }

  goBack(): void {
    this.router.navigate(['/dashboard']);
  }

  getSeverityLabel(severity: string): string {
    const labels: Record<string, string> = {
      'high': 'Critical',
      'medium': 'Warning',
      'low': 'Low'
    };
    return labels[severity] || severity;
  }

  getCriticalCount(): number {
    return this.anomalies.filter(a => a.severity === 'high').length;
  }

  getWarningCount(): number {
    return this.anomalies.filter(a => a.severity === 'medium').length;
  }

  getInfoCount(): number {
    return this.anomalies.filter(a => a.severity === 'low').length;
  }

  getCountBySeverity(severity: string): number {
    return this.anomalies.filter(a => a.severity === severity).length;
  }

  // ==================== TRACKING ====================
  
  trackByAnomalyId(index: number, anomaly: any): number {
    return anomaly.id;
  }

  trackByIndex(index: number): number {
    return index;
  }
}