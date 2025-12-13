// auth.service.ts - FIXED VERSION
import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Router } from '@angular/router';
import { BehaviorSubject, Observable, throwError } from 'rxjs';
import { tap, catchError, switchMap } from 'rxjs/operators';

export interface User {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  role: string;
  is_staff: boolean;
  is_superuser: boolean;
}

export interface LoginResponse {
  access: string;
  refresh: string;
}

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private apiUrl = 'http://localhost:8000/api/auth'; // include 'auth'
  private tokenKey = 'access_token';
  private refreshKey = 'refresh_token';
  private userKey = 'user_data';
  
  public isLoggedIn$ = new BehaviorSubject<boolean>(false);
  public userRole$ = new BehaviorSubject<string>('');
  public currentUser$ = new BehaviorSubject<User | null>(null);

  constructor(
    private http: HttpClient,
    private router: Router
  ) {
    this.checkTokenValidity();
  }


  login(username: string, password: string): Observable<any> {
    return this.http.post<LoginResponse>(`${this.apiUrl}/login/`, {
      username,
      password
    }).pipe(
      switchMap((tokenResponse: any) => {
        const accessToken = tokenResponse.access;
        const refreshToken = tokenResponse.refresh;
        localStorage.setItem(this.tokenKey, accessToken);
        localStorage.setItem(this.refreshKey, refreshToken);

        return this.http.get<User>(`${this.apiUrl}/user/`, {
          headers: new HttpHeaders({
            'Authorization': `Bearer ${accessToken}`
          })
        }).pipe(
          tap((userInfo: User) => {
            const role = userInfo.is_staff || userInfo.is_superuser ? 'admin' : 'farmer';
            const userData: User = { ...userInfo, role };
            localStorage.setItem(this.userKey, JSON.stringify(userData));
            this.isLoggedIn$.next(true);
            this.userRole$.next(userData.role);
            this.currentUser$.next(userData);
            this.router.navigate(['/dashboard']);
          })
        );
      }),
      catchError(error => throwError(() => error))
    );
  }

  refreshToken(): Observable<any> {
    const refreshToken = localStorage.getItem(this.refreshKey);
    if (!refreshToken) {
      this.logout();
      return throwError(() => new Error('No refresh token'));
    }

    return this.http.post(`${this.apiUrl}/refresh/`, { refresh: refreshToken }).pipe(
      tap((response: any) => {
        localStorage.setItem(this.tokenKey, response.access);
        console.log('Token refreshed');
      }),
      catchError(error => {
        console.error('Token refresh failed:', error);
        this.logout();
        return throwError(() => error);
      })
    );
  }


  // Register method - Remove for now if not implemented
  register(userData: any): Observable<any> {
    return this.http.post(`${this.apiUrl}/register/`, userData).pipe(
      tap(response => {
        console.log('Registration successful:', response);
      }),
      catchError(error => {
        console.error('Registration error:', error);
        return throwError(() => error);
      })
    );
  }

  // Logout method
  logout(): void {
    localStorage.removeItem(this.tokenKey);
    localStorage.removeItem(this.refreshKey);
    localStorage.removeItem(this.userKey);
    
    this.isLoggedIn$.next(false);
    this.userRole$.next('');
    this.currentUser$.next(null);
    
    this.router.navigate(['/login']);
  }

  // Get current user info
  getCurrentUser(): User | null {
    const userData = localStorage.getItem(this.userKey);
    return userData ? JSON.parse(userData) : null;
  }

  // Get user role
  getUserRole(): string {
    const user = this.getCurrentUser();
    return user?.role || '';
  }

  // Check if user is admin
  isAdmin(): boolean {
    const user = this.getCurrentUser();
    return user?.is_staff === true || user?.is_superuser === true;
  }

  // Check if user is farmer
  isFarmer(): boolean {
    const user = this.getCurrentUser();
    return user?.is_staff === false && user?.is_superuser === false;
  }

  // Get token
  getToken(): string | null {
    return localStorage.getItem(this.tokenKey);
  }

  // Get headers with auth token
  getAuthHeaders(): HttpHeaders {
    const token = this.getToken();
    return new HttpHeaders({
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    });
  }


  // Check if token exists and is valid
  isTokenValid(): boolean {
    const token = this.getToken();
    if (!token) return false;
    
    // Simple check - you could add JWT expiration check here
    return true;
  }

  // Check token on init
  private checkTokenValidity(): void {
    if (this.isTokenValid()) {
      const user = this.getCurrentUser();
      if (user) {
        this.isLoggedIn$.next(true);
        this.userRole$.next(user.role);
        this.currentUser$.next(user);
      }
    }
  }

  // Get updated user profile from API
  refreshUserProfile(): Observable<User> {
    return this.http.get<User>(`${this.apiUrl}/auth/user/`, {
      headers: this.getAuthHeaders()
    }).pipe(
      tap(userInfo => {
        // Update with correct role
        const role = userInfo.is_staff || userInfo.is_superuser ? 'admin' : 'farmer';
        const updatedUser: User = {
          ...userInfo,
          role: role
        };
        
        localStorage.setItem(this.userKey, JSON.stringify(updatedUser));
        this.currentUser$.next(updatedUser);
      }),
      catchError(error => {
        console.error('Failed to get user profile:', error);
        return throwError(() => error);
      })
    );
  }

  // Simple check for headers in API calls
  getHeaders(): HttpHeaders {
    const token = this.getToken();
    if (token) {
      return new HttpHeaders({
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      });
    }
    return new HttpHeaders({
      'Content-Type': 'application/json'
    });
  }
}