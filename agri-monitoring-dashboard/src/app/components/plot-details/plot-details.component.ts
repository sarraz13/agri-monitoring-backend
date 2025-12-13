import { Component, OnInit, OnDestroy, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { ApiService } from '../../services/api.service';
import { Chart, registerables, ChartConfiguration } from 'chart.js';
import { forkJoin } from 'rxjs';

Chart.register(...registerables);

@Component({
  selector: 'app-plot-details',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './plot-details.component.html',
  styleUrls: ['./plot-details.component.css']
})
export class PlotDetailsComponent implements OnInit, OnDestroy {
  plotId: number = 0;
  plot: any = null;
  sensorReadings: any[] = [];
  anomalies: any[] = [];
  selectedAnomaly: any = null;
  loading = true;
  error: string = '';

  activeChart: string = 'moisture';
  currentChart: Chart | null = null;

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private apiService: ApiService,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    this.route.params.subscribe(params => {
      this.plotId = Number(params['id']);
      if (!this.plotId || isNaN(this.plotId)) {
        this.error = 'Invalid plot ID';
        this.loading = false;
        return;
      }
      this.resetComponent();
      this.loadPlotData();
    });
  }

  ngOnDestroy(): void {
    this.destroyCurrentChart();
  }

  private resetComponent(): void {
    this.plot = null;
    this.sensorReadings = [];
    this.anomalies = [];
    this.selectedAnomaly = null;
    this.loading = true;
    this.error = '';
    this.destroyCurrentChart();
  }

  loadPlotData(): void {
    this.loading = true;
    this.error = '';
    
    forkJoin({
      plot: this.apiService.getPlotById(this.plotId),
      sensors: this.apiService.getSensorReadingsByPlot(this.plotId),
      anomalies: this.apiService.getAnomaliesByPlot(this.plotId)
    }).subscribe({
      next: (results) => {
        this.plot = results.plot;
        this.sensorReadings = results.sensors;
        this.anomalies = results.anomalies;

        // Load existing recommendations for each anomaly
        this.anomalies.forEach(anomaly => {
          if (anomaly.id) {
            this.loadExistingRecommendation(anomaly.id);
          }
        });

        // Select first anomaly by default
        if (this.anomalies.length > 0) {
          this.selectAnomaly(this.anomalies[0]);
        }

        // Create chart if we have data
        if (this.sensorReadings.length > 0) {
          setTimeout(() => this.createChart(), 100);
        }

        this.loading = false;
        this.cdr.detectChanges();
      },
      error: (err) => {
        console.error('Error loading plot data:', err);
        this.error = 'Error loading plot data. Please try again.';
        this.loading = false;
        this.cdr.detectChanges();
      }
    });
  }

  loadExistingRecommendation(anomalyId: number): void {
    this.apiService.getRecommendationsByAnomaly(anomalyId).subscribe({
      next: (recommendations: any[]) => {
        if (recommendations && recommendations.length > 0) {
          const recommendation = recommendations[0];
          const anomalyIndex = this.anomalies.findIndex(a => a.id === anomalyId);
          if (anomalyIndex !== -1) {
            this.anomalies[anomalyIndex].agent_recommendation = {
              recommended_action: recommendation.recommended_action || recommendation.action,
              explanation_text: recommendation.explanation_text || recommendation.explanation,
              confidence: recommendation.confidence || 0.8
            };
            
            // Update selected anomaly if it's the current one
            if (this.selectedAnomaly && this.selectedAnomaly.id === anomalyId) {
              this.selectedAnomaly.agent_recommendation = this.anomalies[anomalyIndex].agent_recommendation;
            }
            
            this.cdr.detectChanges();
          }
        }
      },
      error: (err) => {
        console.log('No existing recommendation found for anomaly:', anomalyId);
      }
    });
  }

  setActiveChart(chartType: string): void {
    if (this.activeChart === chartType) return;
    
    this.activeChart = chartType;
    this.createChart();
  }

  createChart(): void {
    this.destroyCurrentChart();
    if (!this.sensorReadings.length) return;

    // Filter readings for selected chart type
    const filteredReadings = this.sensorReadings
      .filter(r => r.sensor_type === this.activeChart)
      .slice(-20); // Last 20 readings

    if (filteredReadings.length === 0) {
      console.log(`No ${this.activeChart} data available`);
      return;
    }

    // Sort by timestamp
    filteredReadings.sort((a, b) => 
      new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
    );

    const labels = filteredReadings.map(r =>
      new Date(r.timestamp).toLocaleTimeString('fr-FR', { 
        hour: '2-digit', 
        minute: '2-digit' 
      })
    );

    const data = filteredReadings.map(r => r.value);

    const chartConfig = this.getChartConfig(this.activeChart, labels, data);
    
    const ctx = document.getElementById('activeChart') as HTMLCanvasElement;
    if (!ctx) return;

    this.currentChart = new Chart(ctx, chartConfig);
  }

  private getChartConfig(type: string, labels: string[], data: number[]): ChartConfiguration<'line'> {
    const configs: any = {
      moisture: {
        label: 'Soil Moisture (%)',
        color: '#3b82f6',
        min: 0,
        max: 100,
        unit: '%'
      },
      temperature: {
        label: 'Temperature (°C)',
        color: '#ef4444',
        min: null,
        max: null,
        unit: '°C'
      },
      humidity: {
        label: 'Humidity (%)',
        color: '#10b981',
        min: 0,
        max: 100,
        unit: '%'
      }
    };

    const config = configs[type] || configs.moisture;

    return {
      type: 'line',
      data: {
        labels,
        datasets: [{
          label: config.label,
          data,
          borderColor: config.color,
          backgroundColor: config.color + '20',
          tension: 0.3,
          fill: true,
          borderWidth: 2,
          pointBackgroundColor: config.color,
          pointBorderColor: '#fff',
          pointBorderWidth: 2,
          pointRadius: 3
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            mode: 'index',
            intersect: false,
            callbacks: {
              label: (context) => `${context.parsed.y}${config.unit}`
            }
          }
        },
        scales: {
          y: {
            beginAtZero: config.min !== null,
            suggestedMin: config.min,
            suggestedMax: config.max,
            grid: { color: 'rgba(0,0,0,0.05)' },
            ticks: {
              callback: (value) => `${value}${config.unit}`
            }
          },
          x: {
            grid: { color: 'rgba(0,0,0,0.05)' },
            ticks: { 
              maxRotation: 0,
              autoSkip: true,
              maxTicksLimit: 6
            }
          }
        }
      }
    };
  }

  destroyCurrentChart(): void {
    if (this.currentChart) {
      this.currentChart.destroy();
      this.currentChart = null;
    }
  }

  selectAnomaly(anomaly: any): void {
    this.selectedAnomaly = { ...anomaly };
    this.cdr.detectChanges();
  }

  generateRecommendation(): void {
    if (!this.selectedAnomaly || this.selectedAnomaly.loadingRecommendation) return;
    
    console.log('Generating recommendation for anomaly:', this.selectedAnomaly.id);
    
    this.selectedAnomaly.loadingRecommendation = true;
    this.cdr.detectChanges();
    
    this.apiService.generateRecommendation(this.selectedAnomaly.id).subscribe({
      next: (response: any) => {
        console.log('Recommendation API response:', response);
        
        // Handle different response formats
        let recommendation;
        
        if (response && response.recommended_action) {
          // Format 1: Direct recommended_action
          recommendation = {
            recommended_action: response.recommended_action,
            explanation_text: response.explanation_text || 'AI-generated recommendation',
            confidence: response.confidence || 0.8
          };
        } else if (response && response.recommendation) {
          // Format 2: Has recommendation field
          recommendation = {
            recommended_action: response.recommendation,
            explanation_text: 'Generated by AI agent',
            confidence: 0.7
          };
        } else {
          // Format 3: Fallback
          recommendation = {
            recommended_action: 'Monitor anomaly and adjust irrigation',
            explanation_text: 'Temperature/moisture imbalance detected',
            confidence: 0.75
          };
        }
        
        // Update the anomaly
        this.selectedAnomaly.agent_recommendation = recommendation;
        this.selectedAnomaly.loadingRecommendation = false;
        
        // Update in anomalies list too
        const anomalyIndex = this.anomalies.findIndex(a => a.id === this.selectedAnomaly.id);
        if (anomalyIndex !== -1) {
          this.anomalies[anomalyIndex].agent_recommendation = recommendation;
        }
        
        this.cdr.detectChanges();
        console.log('Recommendation set successfully');
      },
      error: (error) => {
        console.error('Error generating recommendation:', error);
        
        // Fallback mock recommendation
        const mockRecommendations = [
          { action: 'Increase irrigation by 20% for 2 days', explanation: 'Low soil moisture detected', confidence: 0.8 },
          { action: 'Reduce irrigation and check drainage', explanation: 'Excess soil moisture', confidence: 0.75 },
          { action: 'Install temporary shade', explanation: 'High temperature stress', confidence: 0.7 },
          { action: 'Monitor for frost protection', explanation: 'Low temperature alert', confidence: 0.65 }
        ];
        
        const mockRec = mockRecommendations[Math.floor(Math.random() * mockRecommendations.length)];
        
        this.selectedAnomaly.agent_recommendation = {
          recommended_action: mockRec.action,
          explanation_text: mockRec.explanation,
          confidence: mockRec.confidence
        };
        
        this.selectedAnomaly.loadingRecommendation = false;
        this.cdr.detectChanges();
      }
    });
  }

  getRecommendationAction(): string {
    if (!this.selectedAnomaly?.agent_recommendation) {
      return 'No recommendation available';
    }
    
    const rec = this.selectedAnomaly.agent_recommendation;
    return rec.recommended_action || rec.action || 'No action specified';
  }

  getRecommendationExplanation(): string {
    if (!this.selectedAnomaly?.agent_recommendation) return '';
    
    const rec = this.selectedAnomaly.agent_recommendation;
    return rec.explanation_text || rec.explanation || '';
  }

  getRecommendationConfidence(): string {
    if (!this.selectedAnomaly?.agent_recommendation?.confidence) return '';
    
    return (this.selectedAnomaly.agent_recommendation.confidence * 100).toFixed(0);
  }

  getCurrentValue(type: string): string {
    if (!this.sensorReadings.length) return '--';
    
    const latestReading = [...this.sensorReadings]
      .filter(r => r.sensor_type === type)
      .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())[0];
    
    return latestReading ? latestReading.value.toFixed(1) : '--';
  }

  getAverage(type: string): string {
    if (!this.sensorReadings.length) return '--';
    
    const values = this.sensorReadings
      .filter(r => r.sensor_type === type)
      .map(r => r.value);
    
    if (values.length === 0) return '--';
    
    const sum = values.reduce((a, b) => a + b, 0);
    return (sum / values.length).toFixed(1);
  }

  getStatusText(status: string): string {
    const statusMap: Record<string, string> = {
      'normal': 'Normal',
      'warning': 'Warning',
      'alert': 'Alert',
      'critical': 'Critical'
    };
    return statusMap[status] || 'Normal';
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

  goBack(): void {
    this.router.navigate(['/dashboard']);
  }

  logout(): void {
    localStorage.removeItem('access_token');
    this.router.navigate(['/login']);
  }

  trackByAnomalyId(index: number, anomaly: any): number {
    return anomaly.id;
  }
}