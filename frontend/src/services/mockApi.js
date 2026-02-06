/**
 * Mock API Service
 * Provides mock data for frontend-only mode (no backend required)
 */

// Mock trajectory data for visualization
const mockTrajectoryData = [
    { track_id: 1, timestamp: "2023-11-25T06:00:00", centroid_lat: 12.5, centroid_lon: 85.2, mean_bt: 215.3, min_bt: 198.5, area_km2: 45000, is_predicted: false },
    { track_id: 1, timestamp: "2023-11-25T09:00:00", centroid_lat: 12.8, centroid_lon: 84.8, mean_bt: 212.1, min_bt: 195.2, area_km2: 52000, is_predicted: false },
    { track_id: 1, timestamp: "2023-11-25T12:00:00", centroid_lat: 13.2, centroid_lon: 84.4, mean_bt: 208.7, min_bt: 192.1, area_km2: 58000, is_predicted: false },
    { track_id: 1, timestamp: "2023-11-25T15:00:00", centroid_lat: 13.8, centroid_lon: 84.0, mean_bt: 205.3, min_bt: 189.8, area_km2: 65000, is_predicted: false },
    { track_id: 1, timestamp: "2023-11-25T18:00:00", centroid_lat: 14.5, centroid_lon: 83.5, mean_bt: 202.1, min_bt: 186.5, area_km2: 72000, is_predicted: false },
    { track_id: 1, timestamp: "2023-11-25T21:00:00", centroid_lat: 15.2, centroid_lon: 83.0, mean_bt: 199.8, min_bt: 184.2, area_km2: 78000, is_predicted: true },
    { track_id: 1, timestamp: "2023-11-26T00:00:00", centroid_lat: 15.9, centroid_lon: 82.4, mean_bt: 197.5, min_bt: 182.0, area_km2: 85000, is_predicted: true },
];

// Mock analysis metadata
const mockMetadata = {
    total_frames: 7,
    total_tracks: 1,
    mean_bt: 205.8,
    min_bt: 182.0,
    max_bt: 215.3,
    total_area: 455000,
};

// Mock exports
const mockExports = [
    { id: 'netcdf', name: 'tcc_trajectory_demo.nc', type: 'NetCDF', status: 'ready', description: 'CF-compliant trajectory data' },
    { id: 'csv', name: 'tcc_trajectory_demo.csv', type: 'CSV', status: 'ready', description: 'Spreadsheet-compatible data' },
    { id: 'json', name: 'tcc_analysis_demo.json', type: 'JSON', status: 'ready', description: 'Full analysis data' },
];

// Simulated user for demo
const mockUser = {
    id: 1,
    username: 'demo_user',
    email: 'demo@cloudsense.ai',
};

// Mock API client
const mockApi = {
    // Auth - auto-success in demo mode
    isAuthenticated: () => {
        return localStorage.getItem('demo_mode') === 'true';
    },

    login: async (email, password) => {
        // Simulate network delay
        await new Promise(resolve => setTimeout(resolve, 500));
        localStorage.setItem('demo_mode', 'true');
        localStorage.setItem('demo_user', JSON.stringify(mockUser));
        return { success: true, user: mockUser };
    },

    logout: () => {
        localStorage.removeItem('demo_mode');
        localStorage.removeItem('demo_user');
    },

    getUser: () => {
        const user = localStorage.getItem('demo_user');
        return user ? JSON.parse(user) : null;
    },

    // Analysis data
    getTrajectory: async (analysisId) => {
        await new Promise(resolve => setTimeout(resolve, 300));
        return mockTrajectoryData;
    },

    getMetadata: async (analysisId) => {
        await new Promise(resolve => setTimeout(resolve, 200));
        return mockMetadata;
    },

    // Upload - simulates processing
    uploadFile: async (file, onProgress) => {
        // Simulate upload progress
        for (let i = 0; i <= 100; i += 10) {
            await new Promise(resolve => setTimeout(resolve, 100));
            if (onProgress) onProgress(i);
        }

        const analysisId = 'demo-' + Date.now();
        localStorage.setItem('current_analysis_id', analysisId);

        return {
            analysis_id: analysisId,
            status: 'complete',
            message: `Processed ${file.name} (Demo Mode)`,
            total_frames: 7,
        };
    },

    // Exports
    getExports: async () => {
        await new Promise(resolve => setTimeout(resolve, 200));
        return mockExports;
    },

    generateReport: async (analysisId) => {
        await new Promise(resolve => setTimeout(resolve, 1000));
        return {
            status: 'complete',
            download_urls: {
                netcdf: '#demo-download',
                csv: '#demo-download',
                json: '#demo-download',
                predictions: '#demo-download',
            },
            report: { metadata: mockMetadata },
        };
    },

    // Token compatibility
    getAuthToken: () => {
        return localStorage.getItem('demo_mode') === 'true' ? 'demo-token' : null;
    },
};

export default mockApi;
