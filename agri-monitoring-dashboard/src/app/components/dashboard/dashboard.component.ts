import { Component, OnInit, OnDestroy, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { ApiService } from '../../services/api.service';
import { Chart, registerables, ChartConfiguration } from 'chart.js';
import { forkJoin, timer, Subscription } from 'rxjs';
import { take } from 'rxjs/operators';

Chart.register(...registerables);

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './dashboard.component.html',
  styleUrls: ['./dashboard.component.css']
})
export class DashboardComponent implements OnInit, OnDestroy {
  stats: any = { total_farms: 0, total_plots: 0, total_anomalies: 0, active_alerts: 0 };
  plots: any[] = [];
  recentAnomalies: any[] = [];
  sensorReadings: any[] = [];

  activeChart: string = 'moisture';
  currentChart: Chart | null = null;
  refreshCountdown: number = 0;
  private refreshSubscription?: Subscription;

  constructor(
    private router: Router,
    private apiService: ApiService,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    this.loadDashboardData();
    // Auto-refresh every 30 seconds
    this.refreshSubscription = timer(30000, 30000).subscribe(() => {
      this.refreshCountdown = 5;
      const countdown = setInterval(() => {
        this.refreshCountdown--;
        if (this.refreshCountdown <= 0) {
          clearInterval(countdown);
          this.loadDashboardData();
        }
      }, 1000);
    });
  }

  ngOnDestroy(): void {
    if (this.refreshSubscription) {
      this.refreshSubscription.unsubscribe();
    }
    this.destroyCurrentChart();
  }

  loadDashboardData(): void {
    // Add this to your loadDashboardData method
  console.log('Sensor readings structure:', this.sensorReadings);
  console.log('Temperature readings:', this.sensorReadings.filter(r => r.sensor_type === 'temperature'));
    forkJoin({
      stats: this.apiService.getDashboardStats(),
      plots: this.apiService.getPlots(),
      anomalies: this.apiService.getAnomalies(),
      readings: this.apiService.getSensorReadings()
    }).pipe(take(1)).subscribe({
      next: (res) => {
        this.stats = res.stats;
        this.plots = res.plots;
        this.sensorReadings = res.readings.slice(0, 50); // Limit to 50 most recent
        
        // Get top 10 most recent anomalies
        this.recentAnomalies = res.anomalies
          .slice(0, 10)
          .map((a: any) => ({
            ...a,
            // Your API returns agent_recommendation as string, not object
            agent_recommendation: a.agent_recommendation || null
          }));

        if (this.sensorReadings.length > 0) {
          setTimeout(() => this.createChart(), 100);
        }
        
        this.cdr.detectChanges();
      },
      error: (err) => {
        console.error('Dashboard loading error:', err);
        if (err.status === 401) {
          this.logout();
        }
      }
    });
  }

  setActiveChart(chartType: string): void {
    this.activeChart = chartType;
    this.createChart();
  }

  createChart(): void {
    this.destroyCurrentChart();
    
    if (!this.sensorReadings.length) {
      console.log('No sensor readings available');
      return;
    }

    // Filter readings for the selected chart type
    const filteredReadings = this.sensorReadings
      .filter((r: any) => r.sensor_type === this.activeChart)
      .slice(-20); // Get last 20 readings

    console.log(`${this.activeChart} readings:`, filteredReadings.length);

    if (filteredReadings.length === 0) {
      console.log(`No ${this.activeChart} data available`);
      // Show empty state
      this.showEmptyChartState();
      return;
    }

    // Sort by timestamp
    filteredReadings.sort((a: any, b: any) => 
      new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
    );

    const labels = filteredReadings.map((r: any) =>
      new Date(r.timestamp).toLocaleTimeString('fr-FR', { 
        hour: '2-digit', 
        minute: '2-digit' 
      })
    );

    const data = filteredReadings.map((r: any) => r.value);

    const chartConfig = this.getChartConfig(this.activeChart, labels, data);
    
    const canvasId = this.activeChart + 'Chart';
    const ctx = document.getElementById(canvasId) as HTMLCanvasElement;
    
    if (!ctx) {
      console.error(`Canvas element #${canvasId} not found`);
      return;
    }

    this.currentChart = new Chart(ctx, chartConfig);
  }

  private showEmptyChartState(): void {
    const chartContainer = document.querySelector('.chart-container');
    if (chartContainer) {
      chartContainer.innerHTML = `
        <div class="no-data-message">
          <div class="no-data-icon">📊</div>
          <div class="no-data-text">No ${this.activeChart} data available</div>
          <div class="no-data-hint">Try selecting a different plot or check sensor status</div>
        </div>
      `;
    }
  }

  private getChartConfig(type: string, labels: string[], data: number[]): ChartConfiguration<'line'> {
    const configs: any = {
      moisture: { label: 'Soil Moisture (%)', color: '#3b82f6', unit: '%' },
      temperature: { label: 'Temperature (°C)', color: '#ef4444', unit: '°C' },
      humidity: { label: 'Humidity (%)', color: '#10b981', unit: '%' }
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
          borderWidth: 2
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          y: {
            beginAtZero: type !== 'temperature', // Only start at 0 for moisture/humidity
            grid: { color: 'rgba(0,0,0,0.05)' },
            ticks: { callback: (value) => `${value}${config.unit}` }
          },
          x: {
            grid: { color: 'rgba(0,0,0,0.05)' }
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

  formatDate(dateString: string): string {
    if (!dateString) return '--';
    const date = new Date(dateString);
    return date.toLocaleDateString('fr-FR', { 
      day: '2-digit', 
      month: '2-digit',
      hour: '2-digit', 
      minute: '2-digit' 
    });
  }

  trackByAnomalyId(index: number, anomaly: any): number {
    return anomaly.id;
  }

  viewPlotDetails(plotId: number): void {
    this.router.navigate(['/plot-details', plotId]);
  }

  generateRecommendation(anomalyId: number): void {
    this.apiService.generateRecommendation(anomalyId).subscribe({
      next: (response) => {
        console.log('Recommendation generated:', response);
        // Find and update the anomaly in the list
        const index = this.recentAnomalies.findIndex(a => a.id === anomalyId);
        if (index !== -1) {
          this.recentAnomalies[index].agent_recommendation = response.recommended_action;
          this.cdr.detectChanges();
        }
      },
      error: (err) => {
        console.error('Failed to generate recommendation:', err);
        alert('Could not generate recommendation. Please try again.');
      }
    });
  }

  logout(): void {
    localStorage.removeItem('access_token');
    this.router.navigate(['/login']);
  }

  showAlerts(): void {
    this.router.navigate(['/alerts']);
  }
}