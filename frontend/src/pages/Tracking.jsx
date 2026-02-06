import { useState, useEffect } from 'react';
import { GitBranch, Circle, ArrowRight, Merge, CloudOff, RefreshCw, Loader2 } from 'lucide-react';
import Sidebar from '@/components/dashboard/Sidebar';
import DashboardHeader from '@/components/dashboard/DashboardHeader';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import apiClient from '@/services/api';

const getEventIcon = (type) => {
  switch (type) {
    case 'formation': return Circle;
    case 'movement': return ArrowRight;
    case 'merge': return Merge;
    case 'dissipation': return CloudOff;
    default: return Circle;
  }
};

const Tracking = () => {
  const [selectedTrack, setSelectedTrack] = useState(null);
  const [tracks, setTracks] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchTrackingData = async () => {
    setLoading(true);
    try {
      const data = await apiClient.getTrajectory();

      // Group by track_id
      const trackMap = {};
      data.forEach(point => {
        const id = point.track_id || 1;
        if (!trackMap[id]) {
          trackMap[id] = {
            id: `TRK-${String(id).padStart(3, '0')}`,
            trackId: id,
            observations: [],
            events: []
          };
        }
        trackMap[id].observations.push(point);
      });

      // Generate events
      const processedTracks = Object.values(trackMap).map(track => {
        const obs = track.observations;
        const events = [];

        if (obs.length > 0) {
          const first = obs[0];
          events.push({
            time: first.timestamp?.split('T')[1]?.slice(0, 5) || 'T+0',
            type: 'formation',
            description: `Cluster formed at ${first.centroid_lat?.toFixed(1)}°N, ${first.centroid_lon?.toFixed(1)}°E`
          });

          if (obs.length > 2) {
            const mid = obs[Math.floor(obs.length / 2)];
            events.push({
              time: mid.timestamp?.split('T')[1]?.slice(0, 5) || 'T+X',
              type: 'movement',
              description: `Moving NW, BT: ${mid.mean_bt?.toFixed(1)}K`
            });
          }

          const last = obs[obs.length - 1];
          events.push({
            time: last.timestamp?.split('T')[1]?.slice(0, 5) || 'Current',
            type: 'movement',
            description: `Current: ${last.centroid_lat?.toFixed(1)}°N, ${last.centroid_lon?.toFixed(1)}°E`
          });
        }

        return {
          ...track,
          status: 'active',
          events
        };
      });

      setTracks(processedTracks);
      if (processedTracks.length > 0) {
        setSelectedTrack(processedTracks[0].id);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTrackingData();
  }, []);

  const currentTrack = tracks.find(t => t.id === selectedTrack);

  if (loading) {
    return (
      <div className="flex h-screen bg-[#010816]">
        <Sidebar />
        <div className="flex-1 flex flex-col">
          <DashboardHeader />
          <div className="flex-1 flex items-center justify-center">
            <Loader2 className="w-8 h-8 text-cyan-500 animate-spin" />
            <span className="ml-3 text-slate-400">Loading tracking data...</span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-[#010816]">
      <Sidebar />
      <div className="flex-1 flex flex-col">
        <DashboardHeader />
        <div className="flex-1 overflow-auto p-6 space-y-6">
          {/* Demo Banner */}
          <div className="bg-cyan-500/10 border border-cyan-500/30 rounded-lg p-3 flex items-center gap-3">
            <span className="text-cyan-400 text-sm">🎮 Demo Mode - Showing simulated TCC tracks</span>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Track List */}
            <div className="bg-slate-900 rounded-lg shadow border border-slate-800">
              <div className="p-6 border-b border-slate-800 flex justify-between items-center">
                <h2 className="text-xl font-semibold text-slate-50">Active Tracks</h2>
                <Button size="sm" variant="outline" onClick={fetchTrackingData}>
                  <RefreshCw className="w-4 h-4" />
                </Button>
              </div>
              <div className="space-y-2 p-6">
                {tracks.map((track) => (
                  <div
                    key={track.id}
                    onClick={() => setSelectedTrack(track.id)}
                    className={cn(
                      "p-4 rounded-lg border cursor-pointer transition-all duration-200",
                      selectedTrack === track.id
                        ? "border-cyan-400 bg-slate-800"
                        : "border-slate-700 bg-slate-800/50 hover:border-slate-600"
                    )}
                  >
                    <div className="flex justify-between items-start mb-2">
                      <span className="font-semibold text-slate-100">{track.id}</span>
                      <span className="text-xs px-2 py-1 rounded-full bg-green-500/20 text-green-400">
                        {track.status}
                      </span>
                    </div>
                    <p className="text-sm text-slate-400">
                      {track.observations?.length || 0} observations
                    </p>
                  </div>
                ))}
              </div>
            </div>

            {/* Timeline */}
            <div className="lg:col-span-2 bg-slate-900 rounded-lg shadow border border-slate-800">
              <div className="p-6 border-b border-slate-800">
                <h2 className="text-xl font-semibold text-slate-50">Lifecycle Timeline</h2>
                <p className="text-sm text-slate-400">Track: {selectedTrack || 'None'}</p>
              </div>
              <div className="p-6 space-y-4">
                {currentTrack ? (
                  <>
                    <div className="space-y-3">
                      {currentTrack.events.map((event, index) => {
                        const Icon = getEventIcon(event.type);
                        return (
                          <div key={index} className="flex gap-4">
                            <div className="flex flex-col items-center">
                              <div className="w-3 h-3 bg-cyan-400 rounded-full" />
                              {index < currentTrack.events.length - 1 && (
                                <div className="w-0.5 h-12 bg-slate-700" />
                              )}
                            </div>
                            <div className="pb-4">
                              <p className="font-mono text-sm text-cyan-400">{event.time}</p>
                              <p className="font-semibold capitalize text-slate-100">{event.type}</p>
                              <p className="text-sm text-slate-400">{event.description}</p>
                            </div>
                          </div>
                        );
                      })}
                    </div>

                    {/* Path Visualization */}
                    <div className="mt-8 p-4 bg-slate-800 rounded-lg border border-slate-700">
                      <svg className="w-full h-32" viewBox="0 0 400 128">
                        <defs>
                          <linearGradient id="pathGrad" x1="0%" y1="0%" x2="100%" y2="0%">
                            <stop offset="0%" stopColor="#22d3ee" />
                            <stop offset="100%" stopColor="#a855f7" />
                          </linearGradient>
                        </defs>
                        {[0, 50, 100, 150, 200, 250, 300, 350, 400].map((x) => (
                          <line key={`v${x}`} x1={x} y1="0" x2={x} y2="128" stroke="#334155" strokeWidth="1" />
                        ))}
                        <polyline
                          points="20,100 80,90 140,75 200,60 260,50 320,45 380,35"
                          fill="none"
                          stroke="url(#pathGrad)"
                          strokeWidth="3"
                        />
                        <circle cx="20" cy="100" r="5" fill="#22c55e" />
                        <circle cx="380" cy="35" r="5" fill="#ef4444" />
                        <text x="20" y="120" textAnchor="middle" fontSize="10" fill="#94a3b8">START</text>
                        <text x="380" y="25" textAnchor="middle" fontSize="10" fill="#94a3b8">CURRENT</text>
                      </svg>
                    </div>
                  </>
                ) : (
                  <div className="text-center text-slate-400 py-12">
                    <p>Select a track to view timeline</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Tracking;
