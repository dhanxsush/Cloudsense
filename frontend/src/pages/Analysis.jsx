import { useState, useEffect } from 'react';
import { RefreshCw, AlertCircle } from 'lucide-react';
import Sidebar from '@/components/dashboard/Sidebar';
import DashboardHeader from '@/components/dashboard/DashboardHeader';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { cn } from '@/lib/utils';
import apiClient from '@/services/api';
import { useAnalysisContext } from '@/contexts/AnalysisContext';
import { useNavigate } from 'react-router-dom';

const overlayOptions = [
  { id: 'trajectory', label: 'Trajectory Path', color: 'hsl(var(--primary))' },
  { id: 'points', label: 'Data Points', color: 'hsl(var(--success))' },
];

const Analysis = () => {
  const [activeOverlays, setActiveOverlays] = useState(['trajectory', 'points']);
  const [trajectoryData, setTrajectoryData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const { currentAnalysisId } = useAnalysisContext();
  const navigate = useNavigate();

  const fetchTrajectory = async () => {
    setLoading(true);
    setError(null);

    try {
      // Use mock API - no backend needed
      const data = await apiClient.getTrajectory(currentAnalysisId);
      setTrajectoryData(data || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTrajectory();
  }, [currentAnalysisId]);

  const toggleOverlay = (id) => {
    setActiveOverlays(prev =>
      prev.includes(id) ? prev.filter(o => o !== id) : [...prev, id]
    );
  };

  // Transform to pixel coords (Bay of Bengal: 5-25°N, 80-100°E)
  const transformToPixel = (lat, lon) => {
    const x = ((lon - 80) / 20) * 512;
    const y = 512 - ((lat - 5) / 20) * 512;
    return { x: Math.max(0, Math.min(512, x)), y: Math.max(0, Math.min(512, y)) };
  };

  return (
    <div className="flex h-screen bg-[#010816]">
      <Sidebar />
      <div className="flex-1 flex flex-col">
        <DashboardHeader />
        <div className="flex-1 overflow-auto">
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 p-6">
            {/* Main Visualization */}
            <div className="lg:col-span-3 bg-slate-900 rounded-lg shadow border border-slate-800">
              <div className="p-4 border-b border-slate-800 flex justify-between items-center">
                <span className="text-sm text-slate-400">
                  {loading ? "Loading..." : `${trajectoryData.length} data points | Demo Mode`}
                </span>
                <div className="flex gap-2">
                  <span className="text-xs px-2 py-1 bg-cyan-500/20 text-cyan-400 rounded">DEMO</span>
                  <Button size="sm" variant="outline" onClick={fetchTrajectory} disabled={loading}>
                    <RefreshCw className={cn("w-4 h-4", loading && "animate-spin")} />
                  </Button>
                </div>
              </div>

              <div className="aspect-square bg-slate-800 p-6">
                {loading ? (
                  <div className="flex items-center justify-center h-full text-slate-400">
                    Loading trajectory data...
                  </div>
                ) : error ? (
                  <div className="flex flex-col items-center justify-center h-full text-red-400 gap-4">
                    <AlertCircle className="w-12 h-12" />
                    <p>{error}</p>
                  </div>
                ) : (
                  <svg className="w-full h-full" viewBox="0 0 512 512">
                    {/* Grid */}
                    {Array.from({ length: 17 }).map((_, i) => (
                      <g key={`grid-${i}`}>
                        <line x1={i * 32} y1="0" x2={i * 32} y2="512" stroke="#334155" strokeWidth="1" />
                        <line x1="0" y1={i * 32} x2="512" y2={i * 32} stroke="#334155" strokeWidth="1" />
                      </g>
                    ))}

                    {/* Trajectory Lines - Group by track_id */}
                    {activeOverlays.includes('trajectory') && (
                      <>
                        {/* Track 1 */}
                        <polyline
                          points={trajectoryData.filter(d => d.track_id === 1).map(d => {
                            const { x, y } = transformToPixel(d.centroid_lat, d.centroid_lon);
                            return `${x},${y}`;
                          }).join(' ')}
                          fill="none"
                          stroke="#22d3ee"
                          strokeWidth="3"
                        />
                        {/* Track 2 */}
                        <polyline
                          points={trajectoryData.filter(d => d.track_id === 2).map(d => {
                            const { x, y } = transformToPixel(d.centroid_lat, d.centroid_lon);
                            return `${x},${y}`;
                          }).join(' ')}
                          fill="none"
                          stroke="#a855f7"
                          strokeWidth="3"
                        />
                      </>
                    )}

                    {/* Data Points */}
                    {activeOverlays.includes('points') && trajectoryData.map((point, idx) => {
                      const { x, y } = transformToPixel(point.centroid_lat, point.centroid_lon);
                      return (
                        <circle
                          key={idx}
                          cx={x}
                          cy={y}
                          r="6"
                          fill={point.is_predicted ? "#ef4444" : "#22c55e"}
                          stroke="#fff"
                          strokeWidth="2"
                          opacity="0.9"
                        />
                      );
                    })}
                  </svg>
                )}

                <div className="mt-4 flex items-center gap-4 text-xs">
                  <div className="flex items-center gap-2">
                    <div className="w-4 h-4 rounded-full bg-green-500" />
                    <span className="text-slate-400">Measured</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-4 h-4 rounded-full bg-red-500" />
                    <span className="text-slate-400">Predicted</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-4 h-1 bg-cyan-400" />
                    <span className="text-slate-400">Track 1</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-4 h-1 bg-purple-500" />
                    <span className="text-slate-400">Track 2</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Controls Panel */}
            <div className="space-y-6">
              <div className="bg-slate-900 rounded-lg shadow p-6 border border-slate-800">
                <h3 className="font-semibold mb-4 text-slate-50">Overlay Layers</h3>
                <div className="space-y-3">
                  {overlayOptions.map((option) => (
                    <div key={option.id} className="flex items-center justify-between">
                      <label className="text-sm text-slate-300">{option.label}</label>
                      <Switch
                        checked={activeOverlays.includes(option.id)}
                        onCheckedChange={() => toggleOverlay(option.id)}
                      />
                    </div>
                  ))}
                </div>
              </div>

              {trajectoryData.length > 0 && (
                <div className="bg-slate-900 rounded-lg shadow p-6 border border-slate-800">
                  <h3 className="font-semibold mb-4 text-slate-50">Data Summary</h3>
                  <div className="space-y-2 text-xs text-slate-400">
                    <div className="flex justify-between">
                      <span>Total Points</span>
                      <span className="font-mono text-slate-300">{trajectoryData.length}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Tracks</span>
                      <span className="font-mono text-slate-300">{new Set(trajectoryData.map(d => d.track_id)).size}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Mean BT</span>
                      <span className="font-mono text-slate-300">
                        {(trajectoryData.reduce((a, b) => a + b.mean_bt, 0) / trajectoryData.length).toFixed(1)} K
                      </span>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Analysis;
