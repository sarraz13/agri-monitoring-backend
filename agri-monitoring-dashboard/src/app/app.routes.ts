import { Routes } from '@angular/router';
import { LoginComponent } from './components/login/login.component';
import { DashboardComponent } from './components/dashboard/dashboard.component';
import { AlertsComponent } from './components/alerts/alerts.component';
import { PlotDetailsComponent } from './components/plot-details/plot-details.component';

export const routes: Routes = [
  { path: '', redirectTo: '/login', pathMatch: 'full' },
  { path: 'login', component: LoginComponent },
  { path: 'dashboard', component: DashboardComponent },
  { path: 'alerts', component: AlertsComponent },
  { path: 'plot-details/:id', component: PlotDetailsComponent },
  { path: '**', redirectTo: '/login' }
];