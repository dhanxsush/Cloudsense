"""
NetCDF Generator for CloudSense
CF-1.8 Compliant Export
"""

import sqlite3
import numpy as np
import netCDF4 as nc
from datetime import datetime


class NetCDFGenerator:
    """Generate CF-1.8 compliant NetCDF files from analysis results."""
    
    def generate(self, analysis_id, database_path, output_path):
        """
        Generate NetCDF file from database.
        
        Args:
            analysis_id: UUID of analysis
            database_path: Path to SQLite database
            output_path: Output NetCDF file path
            
        Returns:
            Path to generated file
        """
        # Fetch data from database
        data = self._fetch_data(analysis_id, database_path)
        
        if not data['results']:
            raise ValueError("No analysis results found")
        
        # Create NetCDF file
        dataset = nc.Dataset(output_path, 'w', format='NETCDF4')
        
        try:
            # Create dimensions
            time_dim = dataset.createDimension('time', len(data['results']))
            track_dim = dataset.createDimension('track_id', len(data['unique_tracks']))
            
            # Create coordinate variables
            times = dataset.createVariable('time', 'f8', ('time',))
            times.units = 'hours since 1970-01-01 00:00:00'
            times.calendar = 'gregorian'
            times[:] = np.arange(len(data['results']))  # Placeholder
            
            track_ids = dataset.createVariable('track_id', 'i4', ('track_id',))
            track_ids[:] = data['unique_tracks']
            
            # Create data variables
            centroid_lat = dataset.createVariable('centroid_lat', 'f4', ('time',))
            centroid_lat.units = 'degrees_north'
            centroid_lat.standard_name = 'latitude'
            centroid_lat[:] = [r['centroid_lat'] for r in data['results']]
            
            centroid_lon = dataset.createVariable('centroid_lon', 'f4', ('time',))
            centroid_lon.units = 'degrees_east'
            centroid_lon.standard_name = 'longitude'
            centroid_lon[:] = [r['centroid_lon'] for r in data['results']]
            
            area = dataset.createVariable('area_km2', 'f4', ('time',))
            area.units = 'km2'
            area.long_name = 'Cluster Area'
            area[:] = [r['area_km2'] or 0 for r in data['results']]
            
            radius = dataset.createVariable('radius_km', 'f4', ('time',))
            radius.units = 'km'
            radius.long_name = 'Equivalent Radius'
            radius[:] = [r['radius_km'] or 0 for r in data['results']]
            
            mean_bt = dataset.createVariable('mean_bt', 'f4', ('time',))
            mean_bt.units = 'K'
            mean_bt.long_name = 'Mean Brightness Temperature'
            mean_bt[:] = [r['mean_bt'] or 0 for r in data['results']]
            
            # Global attributes
            dataset.title = 'CloudSense TCC Analysis Report'
            dataset.source = f"Analysis ID: {analysis_id}"
            dataset.institution = 'CloudSense Platform'
            dataset.analysis_method = 'DBSCAN clustering + Kalman tracking'
            dataset.Conventions = 'CF-1.8'
            dataset.creation_date = datetime.now().isoformat()
            
        finally:
            dataset.close()
        
        return output_path
    
    def _fetch_data(self, analysis_id, database_path):
        """Fetch analysis results from database."""
        conn = sqlite3.connect(database_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Fetch results
        cursor.execute('''
            SELECT * FROM analysis_results
            WHERE analysis_id = ?
            ORDER BY id
        ''', (analysis_id,))
        
        results = [dict(row) for row in cursor.fetchall()]
        
        # Get unique track IDs
        unique_tracks = list(set([r['track_id'] for r in results if r['track_id'] is not None]))
        
        conn.close()
        
        return {
            'results': results,
            'unique_tracks': unique_tracks
        }
