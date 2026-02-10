/**
 * API Client - Demo Mode (Frontend Only)
 * Works without backend - uses mock data
 */

// Demo mode - no backend required
const DEMO_MODE = false;

// Mock user for demo
const mockUser = {
  id: 1,
  username: 'demo_user',
  email: 'demo@cloudsense.ai',
};

// Mock trajectory data
const mockTrajectoryData = [
  { track_id: 1, timestamp: "2023-11-25T06:00:00", centroid_lat: 12.5, centroid_lon: 85.2, mean_bt: 215.3, min_bt: 198.5, area_km2: 45000, is_predicted: false },
  { track_id: 1, timestamp: "2023-11-25T09:00:00", centroid_lat: 12.8, centroid_lon: 84.8, mean_bt: 212.1, min_bt: 195.2, area_km2: 52000, is_predicted: false },
  { track_id: 1, timestamp: "2023-11-25T12:00:00", centroid_lat: 13.2, centroid_lon: 84.4, mean_bt: 208.7, min_bt: 192.1, area_km2: 58000, is_predicted: false },
  { track_id: 1, timestamp: "2023-11-25T15:00:00", centroid_lat: 13.8, centroid_lon: 84.0, mean_bt: 205.3, min_bt: 189.8, area_km2: 65000, is_predicted: false },
  { track_id: 1, timestamp: "2023-11-25T18:00:00", centroid_lat: 14.5, centroid_lon: 83.5, mean_bt: 202.1, min_bt: 186.5, area_km2: 72000, is_predicted: false },
  { track_id: 1, timestamp: "2023-11-25T21:00:00", centroid_lat: 15.2, centroid_lon: 83.0, mean_bt: 199.8, min_bt: 184.2, area_km2: 78000, is_predicted: true },
  { track_id: 1, timestamp: "2023-11-26T00:00:00", centroid_lat: 15.9, centroid_lon: 82.4, mean_bt: 197.5, min_bt: 182.0, area_km2: 85000, is_predicted: true },
  { track_id: 2, timestamp: "2023-11-25T09:00:00", centroid_lat: 10.2, centroid_lon: 88.5, mean_bt: 218.2, min_bt: 205.1, area_km2: 35000, is_predicted: false },
  { track_id: 2, timestamp: "2023-11-25T12:00:00", centroid_lat: 10.8, centroid_lon: 88.0, mean_bt: 215.5, min_bt: 201.3, area_km2: 42000, is_predicted: false },
  { track_id: 2, timestamp: "2023-11-25T15:00:00", centroid_lat: 11.3, centroid_lon: 87.5, mean_bt: 212.8, min_bt: 198.0, area_km2: 48000, is_predicted: false },
];

const apiClient = {
  // API Base URL
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',

  // Signup
  async signup(username, email, password) {
    if (DEMO_MODE) {
      await new Promise(r => setTimeout(r, 500));
      const user = { ...mockUser, username, email };
      localStorage.setItem('authToken', 'demo-token-' + Date.now());
      localStorage.setItem('user', JSON.stringify(user));
      return { access_token: 'demo-token', user };
    }

    const response = await fetch(`${this.baseURL}/api/auth/signup`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, email, password }),
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || 'Signup failed');
    }

    localStorage.setItem('authToken', data.access_token);
    localStorage.setItem('user', JSON.stringify(data.user));
    return data;
  },

  // Login
  async login(email, password) {
    if (DEMO_MODE) {
      await new Promise(r => setTimeout(r, 500));
      const user = { ...mockUser, email };
      localStorage.setItem('authToken', 'demo-token-' + Date.now());
      localStorage.setItem('user', JSON.stringify(user));
      return { access_token: 'demo-token', user };
    }

    const response = await fetch(`${this.baseURL}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || 'Login failed');
    }

    localStorage.setItem('authToken', data.access_token);
    localStorage.setItem('user', JSON.stringify(data.user));
    return data;
  },

  async verifyToken(token) {
    if (DEMO_MODE) {
      return { valid: true, user: this.getUser() };
    }

    try {
      const response = await fetch(`${this.baseURL}/api/auth/verify`, {
        headers: { 'Authorization': `Bearer ${token}` },
      });
      if (response.ok) {
        return { valid: true, user: await response.json() };
      }
      return { valid: false };
    } catch {
      return { valid: false };
    }
  },

  // Get trajectory data for analysis
  async getTrajectory(analysisId) {
    if (DEMO_MODE) {
      await new Promise(r => setTimeout(r, 300));
      return mockTrajectoryData;
    }

    const response = await fetch(`${this.baseURL}/api/analysis/clusters`, {
      headers: { 'Authorization': `Bearer ${this.getToken()}` },
    });
    return response.ok ? await response.json() : [];
  },

  // Upload file
  async uploadFile(file, onProgress) {
    if (DEMO_MODE) {
      for (let i = 0; i <= 100; i += 20) {
        await new Promise(r => setTimeout(r, 200));
        if (onProgress) onProgress(i);
      }
      return { analysis_id: 'demo-' + Date.now(), status: 'complete' };
    }

    const formData = new FormData();
    formData.append('file', file);
    const response = await fetch(`${this.baseURL}/api/upload`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${this.getToken()}` },
      body: formData,
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || 'Upload failed');
    return data;
  },

  // Generate report
  async generateReport(analysisId) {
    if (DEMO_MODE) {
      await new Promise(r => setTimeout(r, 1000));
      return { status: 'complete' };
    }

    const response = await fetch(`${this.baseURL}/api/exports`, {
      headers: { 'Authorization': `Bearer ${this.getToken()}` },
    });
    return response.ok ? await response.json() : {};
  },

  setAuthToken(token) {
    if (token) {
      localStorage.setItem('authToken', token);
    } else {
      localStorage.removeItem('authToken');
    }
  },

  getAuthToken() {
    return localStorage.getItem('authToken');
  },

  // Alias for getAuthToken (for compatibility)
  getToken() {
    return this.getAuthToken();
  },

  setUser(user) {
    if (user) {
      localStorage.setItem('user', JSON.stringify(user));
    } else {
      localStorage.removeItem('user');
    }
  },

  getUser() {
    const user = localStorage.getItem('user');
    return user ? JSON.parse(user) : null;
  },

  logout() {
    this.setAuthToken(null);
    this.setUser(null);
  },

  isAuthenticated() {
    return !!this.getAuthToken();
  },
};

export default apiClient;
