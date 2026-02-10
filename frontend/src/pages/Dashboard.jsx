import { useState, useEffect } from 'react';
import { Cloud, Thermometer, Activity, Radar, ArrowUpRight, TrendingUp, AlertTriangle } from 'lucide-react';
import Sidebar from '@/components/dashboard/Sidebar';
import DashboardHeader from '@/components/dashboard/DashboardHeader';
import WorldMap from '@/components/dashboard/WorldMap';
import ClusterTable from '@/components/dashboard/ClusterTable';
import apiClient from '@/services/api';
import { useNavigate } from 'react-router-dom';

const Dashboard = () => {
  const navigate = useNavigate();
  const [stats, setStats] = useState({
    active_tccs: 0,
    min_bt: 0,
    avg_cloud_height: 0,
    mean_radius: 0
  });
  const [recentAnalyses, setRecentAnalyses] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [statsRes, analysesRes] = await Promise.all([
          fetch(`${apiClient.baseURL}/api/dashboard/stats`, {
            headers: { 'Authorization': `Bearer ${apiClient.getToken()}` }
          }),
          fetch(`${apiClient.baseURL}/api/analyses/recent?limit=5`, {
            headers: { 'Authorization': `Bearer ${apiClient.getToken()}` }
          })
        ]);
        if (statsRes.ok) setStats(await statsRes.json());
        if (analysesRes.ok) setRecentAnalyses(await analysesRes.json());
      } catch (error) {
        console.error("Failed to fetch dashboard data", error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, []);

  const hasData = stats.active_tccs > 0;

  return (
    <div className="flex h-screen bg-[#010816]">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <DashboardHeader title="CloudSense Dashboard" subtitle="Tropical Cloud Cluster Detection & Analysis" />
        <div className="flex-1 overflow-auto p-6 space-y-6">

          {/* KPI Stats Row */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">

            {/* Active TCCs */}
            <div className="relative overflow-hidden rounded-xl bg-gradient-to-br from-cyan-500/10 to-cyan-900/20 border border-cyan-500/20 p-5">
              <div className="absolute top-0 right-0 w-20 h-20 bg-cyan-500/5 rounded-full -translate-y-6 translate-x-6" />
              <div className="flex items-center gap-3 mb-3">
                <div className="p-2 rounded-lg bg-cyan-500/15">
                  <Radar className="w-5 h-5 text-cyan-400" />
                </div>
                <span className="text-sm text-slate-400 font-medium">Active TCCs</span>
              </div>
              <div className="flex items-baseline gap-2">
                <span className="text-4xl font-bold text-white">{stats.active_tccs}</span>
                <span className="text-sm text-slate-500">clusters</span>
              </div>
              {hasData && (
                <div className="flex items-center gap-1 mt-2 text-xs text-cyan-400">
                  <Activity className="w-3 h-3" />
                  <span>From latest analysis</span>
                </div>
              )}
            </div>

            {/* Min Brightness Temp */}
            <div className="relative overflow-hidden rounded-xl bg-gradient-to-br from-red-500/10 to-orange-900/20 border border-red-500/20 p-5">
              <div className="absolute top-0 right-0 w-20 h-20 bg-red-500/5 rounded-full -translate-y-6 translate-x-6" />
              <div className="flex items-center gap-3 mb-3">
                <div className="p-2 rounded-lg bg-red-500/15">
                  <Thermometer className="w-5 h-5 text-red-400" />
                </div>
                <span className="text-sm text-slate-400 font-medium">Min Brightness Temp</span>
              </div>
              <div className="flex items-baseline gap-2">
                <span className="text-4xl font-bold text-white">{stats.min_bt?.toFixed(1) || '—'}</span>
                <span className="text-sm text-slate-500">K</span>
              </div>
              {stats.min_bt > 0 && stats.min_bt < 220 && (
                <div className="flex items-center gap-1 mt-2 text-xs text-red-400">
                  <AlertTriangle className="w-3 h-3" />
                  <span>Deep convection detected</span>
                </div>
              )}
            </div>

            {/* Cloud-Top Height */}
            <div className="relative overflow-hidden rounded-xl bg-gradient-to-br from-purple-500/10 to-purple-900/20 border border-purple-500/20 p-5">
              <div className="absolute top-0 right-0 w-20 h-20 bg-purple-500/5 rounded-full -translate-y-6 translate-x-6" />
              <div className="flex items-center gap-3 mb-3">
                <div className="p-2 rounded-lg bg-purple-500/15">
                  <TrendingUp className="w-5 h-5 text-purple-400" />
                </div>
                <span className="text-sm text-slate-400 font-medium">Avg Cloud-Top Height</span>
              </div>
              <div className="flex items-baseline gap-2">
                <span className="text-4xl font-bold text-white">{stats.avg_cloud_height?.toFixed(1) || '—'}</span>
                <span className="text-sm text-slate-500">km</span>
              </div>
              <div className="flex items-center gap-1 mt-2 text-xs text-slate-500">
                <span>Estimated from BT lapse rate</span>
              </div>
            </div>

            {/* Mean Radius */}
            <div className="relative overflow-hidden rounded-xl bg-gradient-to-br from-emerald-500/10 to-emerald-900/20 border border-emerald-500/20 p-5">
              <div className="absolute top-0 right-0 w-20 h-20 bg-emerald-500/5 rounded-full -translate-y-6 translate-x-6" />
              <div className="flex items-center gap-3 mb-3">
                <div className="p-2 rounded-lg bg-emerald-500/15">
                  <Cloud className="w-5 h-5 text-emerald-400" />
                </div>
                <span className="text-sm text-slate-400 font-medium">Mean TCC Radius</span>
              </div>
              <div className="flex items-baseline gap-2">
                <span className="text-4xl font-bold text-white">{stats.mean_radius?.toFixed(1) || '—'}</span>
                <span className="text-sm text-slate-500">km</span>
              </div>
              <div className="flex items-center gap-1 mt-2 text-xs text-slate-500">
                <span>Avg across all detections</span>
              </div>
            </div>
          </div>

          {/* Main Content: Map + Recent Activity */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* World Map - Takes 2/3 */}
            <div className="lg:col-span-2 bg-slate-900/50 rounded-xl border border-slate-800 overflow-hidden">
              <div className="px-5 py-3 border-b border-slate-800 flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-semibold text-slate-200">TCC Detection Map</h3>
                  <p className="text-xs text-slate-500">Lat/Lon positions of detected clusters</p>
                </div>
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
                  <span className="text-xs text-slate-400">Auto-refresh</span>
                </div>
              </div>
              <WorldMap />
            </div>

            {/* Recent Analyses Sidebar */}
            <div className="bg-slate-900/50 rounded-xl border border-slate-800 overflow-hidden">
              <div className="px-5 py-3 border-b border-slate-800">
                <h3 className="text-sm font-semibold text-slate-200">Recent Analyses</h3>
                <p className="text-xs text-slate-500">Latest processed files</p>
              </div>
              <div className="p-3 space-y-2 max-h-[420px] overflow-y-auto">
                {recentAnalyses.length === 0 ? (
                  <div className="text-center py-8 text-slate-500">
                    <Cloud className="w-10 h-10 mx-auto mb-3 opacity-30" />
                    <p className="text-sm">No analyses yet</p>
                    <button
                      onClick={() => navigate('/dashboard/upload')}
                      className="mt-3 text-xs text-cyan-400 hover:text-cyan-300 transition-colors"
                    >
                      Upload a file to get started →
                    </button>
                  </div>
                ) : (
                  recentAnalyses.map((a, i) => {
                    const results = typeof a.results === 'string' ? JSON.parse(a.results || '{}') : (a.results || {});
                    const detections = results.detections || [];
                    const tccCount = detections.filter(d => d.is_tcc).length;

                    return (
                      <div
                        key={i}
                        onClick={() => navigate('/analysis')}
                        className="p-3 rounded-lg bg-slate-800/50 hover:bg-slate-800 border border-slate-700/50 cursor-pointer transition-all hover:border-cyan-500/30 group"
                      >
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-xs font-mono text-slate-300 truncate max-w-[180px]">
                            {a.filename}
                          </span>
                          <ArrowUpRight className="w-3 h-3 text-slate-600 group-hover:text-cyan-400 transition-colors" />
                        </div>
                        <div className="flex items-center gap-3 text-xs">
                          <span className="text-cyan-400 font-semibold">{detections.length} clusters</span>
                          {tccCount > 0 && (
                            <span className="text-red-400">{tccCount} TCC</span>
                          )}
                          <span className="text-slate-500 ml-auto">
                            {a.source === 'mosdac' ? '🛰️' : '📁'} {a.source || 'upload'}
                          </span>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          </div>

          {/* Cluster Table */}
          <div className="bg-slate-900/50 rounded-xl border border-slate-800 overflow-hidden">
            <div className="px-5 py-3 border-b border-slate-800 flex items-center justify-between">
              <div>
                <h3 className="text-sm font-semibold text-slate-200">Detected Clusters</h3>
                <p className="text-xs text-slate-500">All detections from recent analyses</p>
              </div>
            </div>
            <ClusterTable />
          </div>

        </div>
      </div>
    </div>
  );
};

export default Dashboard;
