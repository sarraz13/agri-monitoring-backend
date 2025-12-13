import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable } from 'rxjs';

// ------------------- TYPES ------------------- //
export interface DashboardStats {
  total_farms: number;
  total_plots: number;
  total_anomalies: number;
  active_alerts: number;
}

export interface FieldPlot {
  id: number;
  crop_variety: string;
  status: 'normal' | 'warning' | 'alert';
  anomaly_count: number;
  farm: number;
  name?: string;
}

export interface SensorReading {
  id: number;
  timestamp: string;
  plot: number;
  sensor_type: 'temperature' | 'humidity' | 'soil_moisture';
  value: number;
}

export interface Anomaly {
  id: number;
  anomaly_type: string;
  severity: 'low' | 'medium' | 'high';
  confidence_score: number;
  detected_at: string;
  field_plot_name: string;
  agent_recommendation?: string | null;
  loadingRecommendation?: boolean;
  resolved: boolean;
}

export interface Recommendation {
  id?: number;
  anomaly_event?: { id: number };
  recommended_action?: string;  // This matches your backend
  explanation_text?: string;    // Add this to match backend
  confidence?: number;          
}

// ------------------- SERVICE ------------------- //
@Injectable({
  providedIn: 'root'
})
export class ApiService {
  private apiUrl = 'http://localhost:8000/api';

  constructor(private http: HttpClient) {}

  private getHeaders(): HttpHeaders {
    const token = localStorage.getItem('access_token');
    return new HttpHeaders({
      'Content-Type': 'application/json',
      Authorization: token ? `Bearer ${token}` : ''
    });
  }

  // ------------------- AUTH ------------------- //
  login(username: string, password: string): Observable<{ access: string }> {
    return this.http.post<{ access: string }>(`${this.apiUrl}/token/`, { username, password });
  }

  register(userData: Record<string, any>): Observable<any> {
    return this.http.post(`${this.apiUrl}/register/`, userData);
  }

  logout(): void {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
  }

  isAuthenticated(): boolean {
    return !!localStorage.getItem('access_token');
  }

  // ------------------- DASHBOARD ------------------- //
  getDashboardStats(): Observable<DashboardStats> {
    return this.http.get<DashboardStats>(`${this.apiUrl}/dashboard/stats/`, { headers: this.getHeaders() });
  }

  // ------------------- FARMS ------------------- //
  getFarms(): Observable<FieldPlot[]> {
    return this.http.get<FieldPlot[]>(`${this.apiUrl}/farms/`, { headers: this.getHeaders() });
  }

  getFarmById(id: number): Observable<FieldPlot> {
    return this.http.get<FieldPlot>(`${this.apiUrl}/farms/${id}/`, { headers: this.getHeaders() });
  }

  createFarm(farmData: Partial<FieldPlot>): Observable<FieldPlot> {
    return this.http.post<FieldPlot>(`${this.apiUrl}/farms/`, farmData, { headers: this.getHeaders() });
  }

  updateFarm(id: number, farmData: Partial<FieldPlot>): Observable<FieldPlot> {
    return this.http.put<FieldPlot>(`${this.apiUrl}/farms/${id}/`, farmData, { headers: this.getHeaders() });
  }

  deleteFarm(id: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/farms/${id}/`, { headers: this.getHeaders() });
  }

  // ------------------- PLOTS ------------------- //
  getPlots(): Observable<FieldPlot[]> {
    return this.http.get<FieldPlot[]>(`${this.apiUrl}/plots/`, { headers: this.getHeaders() });
  }

  getPlotById(id: number): Observable<FieldPlot> {
    return this.http.get<FieldPlot>(`${this.apiUrl}/plots/${id}/`, { headers: this.getHeaders() });
  }

  getPlotsByFarm(farmId: number): Observable<FieldPlot[]> {
    return this.http.get<FieldPlot[]>(`${this.apiUrl}/plots/?farm=${farmId}`, { headers: this.getHeaders() });
  }

  createPlot(plotData: Partial<FieldPlot>): Observable<FieldPlot> {
    return this.http.post<FieldPlot>(`${this.apiUrl}/plots/`, plotData, { headers: this.getHeaders() });
  }

  updatePlot(id: number, plotData: Partial<FieldPlot>): Observable<FieldPlot> {
    return this.http.put<FieldPlot>(`${this.apiUrl}/plots/${id}/`, plotData, { headers: this.getHeaders() });
  }

  deletePlot(id: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/plots/${id}/`, { headers: this.getHeaders() });
  }

  // ------------------- SENSOR READINGS ------------------- //
  getSensorReadings(): Observable<SensorReading[]> {
    return this.http.get<SensorReading[]>(`${this.apiUrl}/sensor-readings/`, { headers: this.getHeaders() });
  }

  getSensorReadingsByPlot(plotId: number): Observable<SensorReading[]> {
    return this.http.get<SensorReading[]>(`${this.apiUrl}/sensor-readings/?field_plot=${plotId}`, { headers: this.getHeaders() });
  }

  createSensorReading(readingData: Partial<SensorReading>): Observable<SensorReading> {
    return this.http.post<SensorReading>(`${this.apiUrl}/sensor-readings/`, readingData, { headers: this.getHeaders() });
  }

  // ------------------- ANOMALIES ------------------- //
  getAnomalies(): Observable<Anomaly[]> {
    return this.http.get<Anomaly[]>(`${this.apiUrl}/anomalies/`, { headers: this.getHeaders() });
  }

  getAnomaliesByPlot(plotId: number): Observable<Anomaly[]> {
    return this.http.get<Anomaly[]>(`${this.apiUrl}/anomalies/?field_plot=${plotId}`, { headers: this.getHeaders() });
  }

  generateRecommendation(anomalyId: number): Observable<Recommendation> {
    return this.http.post<Recommendation>(`${this.apiUrl}/anomalies/${anomalyId}/recommend/`, {}, { headers: this.getHeaders() });
  }

  regenerateRecommendation(anomalyId: number): Observable<Recommendation> {
    return this.http.post<Recommendation>(`${this.apiUrl}/anomalies/${anomalyId}/recommend/`, { force_regenerate: true }, { headers: this.getHeaders() });
  }

  resolveAnomaly(anomalyId: number): Observable<void> {
    return this.http.post<void>(`${this.apiUrl}/anomalies/${anomalyId}/resolve/`, {}, { headers: this.getHeaders() });
  }

  // ------------------- RECOMMENDATIONS ------------------- //
  getRecommendationsByAnomaly(anomalyId: number): Observable<Recommendation[]> {
    return this.http.get<Recommendation[]>(`${this.apiUrl}/recommendations/?anomaly=${anomalyId}`, { headers: this.getHeaders() });
  }

  applyRecommendation(recommendationId: number): Observable<void> {
    return this.http.post<void>(`${this.apiUrl}/recommendations/${recommendationId}/apply/`, {}, { headers: this.getHeaders() });
  }
}
