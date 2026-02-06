import { cn } from '@/lib/utils';

// Sample cluster data
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';

// API fetcher
const fetchClusters = async () => {
  try {
    const token = localStorage.getItem('token');
    const response = await axios.get('http://localhost:8000/api/analysis/clusters', {
      headers: { Authorization: `Bearer ${token}` }
    });
    return response.data;
  } catch (error) {
    console.error("Failed to fetch clusters", error);
    return [];
  }
};

const ClusterTable = () => {
  const { data: clusters = [], isLoading } = useQuery({
    queryKey: ['clusters'],
    queryFn: fetchClusters,
    refetchInterval: 5000 // Poll every 5s for real-time updates
  });

  if (isLoading) return <div className="p-4 text-slate-400">Loading live data...</div>;

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg overflow-hidden shadow-lg">
      <div className="p-4 border-b border-slate-800">
        <h3 className="text-lg font-semibold text-slate-50">Detected TCC Clusters</h3>
        <p className="text-sm text-slate-400">Real-time Tropical Cloud Cluster monitoring</p>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-slate-800">
            <tr>
              <th className="text-left py-3 px-4 text-xs font-medium text-slate-300 uppercase tracking-wider">
                Cluster ID
              </th>
              <th className="text-left py-3 px-4 text-xs font-medium text-slate-300 uppercase tracking-wider">
                Centroid (Lat, Lon)
              </th>
              <th className="text-left py-3 px-4 text-xs font-medium text-slate-300 uppercase tracking-wider">
                Mean BT (K)
              </th>
              <th className="text-left py-3 px-4 text-xs font-medium text-slate-300 uppercase tracking-wider">
                Radius (km)
              </th>
              <th className="text-left py-3 px-4 text-xs font-medium text-slate-300 uppercase tracking-wider">
                Status
              </th>
              <th className="text-left py-3 px-4 text-xs font-medium text-slate-300 uppercase tracking-wider">
                Data Source
              </th>
              <th className="text-left py-3 px-4 text-xs font-medium text-slate-300 uppercase tracking-wider">
                Last Updated
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800">
            {clusters.map((cluster, index) => (
              <tr key={index} className="hover:bg-slate-800/50 transition-colors">
                <td className="py-3 px-4 font-medium text-cyan-400">{cluster.id}</td>
                <td className="py-3 px-4 text-slate-200">
                  {cluster.centroidLat.toFixed(2)}°N, {cluster.centroidLon.toFixed(2)}°E
                </td>
                <td className="py-3 px-4 text-slate-200 font-medium">{cluster.avgBT.toFixed(1)} K</td>
                <td className="py-3 px-4 text-slate-200 font-medium">{cluster.radius} km</td>
                <td className="py-3 px-4">
                  <span
                    className={cn(
                      "inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold",
                      cluster.status === 'active' && "bg-green-500/20 text-green-300 border border-green-500/30",
                      cluster.status === 'forming' && "bg-blue-500/20 text-blue-300 border border-blue-500/30",
                      cluster.status === 'dissipating' && "bg-yellow-500/20 text-yellow-300 border border-yellow-500/30"
                    )}
                  >
                    {cluster.status.charAt(0).toUpperCase() + cluster.status.slice(1)}
                  </span>
                </td>
                <td className="py-3 px-4">
                  <div className="flex items-center space-x-1">
                    <span className={cn("w-2 h-2 rounded-full",
                      cluster.source?.includes("Live") ? "bg-green-500 animate-pulse" : "bg-slate-500"
                    )}></span>
                    <span className="text-xs text-slate-300 font-mono">{cluster.source || "Unknown"}</span>
                  </div>
                </td>
                <td className="py-3 px-4 text-slate-400 text-sm">{cluster.lastUpdate}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default ClusterTable;

