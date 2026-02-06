import { useState } from 'react';
import { Download, FileType, CheckCircle2, Loader2, Database, FileText } from 'lucide-react';
import Sidebar from '@/components/dashboard/Sidebar';
import DashboardHeader from '@/components/dashboard/DashboardHeader';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { useToast } from "@/components/ui/use-toast";
import apiClient from '@/services/api';

const Exports = () => {
  const [selectedExport, setSelectedExport] = useState('netcdf');
  const [generating, setGenerating] = useState(false);
  const [exports, setExports] = useState([
    { id: 'netcdf', name: 'tcc_trajectory_demo.nc', type: 'NetCDF', status: 'ready', description: 'CF-compliant trajectory data for meteorology tools' },
    { id: 'csv', name: 'tcc_trajectory_demo.csv', type: 'CSV', status: 'ready', description: 'Spreadsheet-compatible trajectory data' },
    { id: 'json', name: 'tcc_analysis_demo.json', type: 'JSON', status: 'ready', description: 'Full analysis data for API integration' },
  ]);
  const { toast } = useToast();

  const metadata = {
    total_frames: 10,
    total_tracks: 2,
    mean_bt: 205.8,
    min_bt: 182.0,
    max_bt: 218.2,
  };

  const regenerateReport = async () => {
    setGenerating(true);
    try {
      await apiClient.generateReport('demo');
      toast({
        title: "Report Generated",
        description: "All export files refreshed (Demo Mode)",
      });
    } catch (err) {
      toast({
        title: "Error",
        description: err.message,
        variant: "destructive"
      });
    } finally {
      setGenerating(false);
    }
  };

  const downloadFile = (exportItem) => {
    toast({
      title: "Demo Mode",
      description: `Download for ${exportItem.name} would start here in production`,
    });
  };

  const getFileIcon = (type) => {
    switch (type) {
      case 'NetCDF': return Database;
      case 'CSV': return FileText;
      case 'JSON': return FileType;
      default: return FileType;
    }
  };

  return (
    <div className="flex h-screen bg-[#010816]">
      <Sidebar />
      <div className="flex-1 flex flex-col">
        <DashboardHeader />
        <div className="flex-1 overflow-auto p-6 space-y-6">
          {/* Demo Banner */}
          <div className="bg-cyan-500/10 border border-cyan-500/30 rounded-lg p-3 flex items-center gap-3">
            <span className="text-cyan-400 text-sm">🎮 Demo Mode - Export files are simulated</span>
          </div>

          {/* Generate Report */}
          <div className="bg-slate-900 rounded-lg shadow border border-slate-800 p-6">
            <div className="flex justify-between items-center">
              <div>
                <h2 className="text-xl font-semibold text-slate-50">Generate Export Files</h2>
                <p className="text-sm text-slate-400 mt-1">Create NetCDF, CSV, and JSON exports</p>
              </div>
              <Button
                onClick={regenerateReport}
                disabled={generating}
                className="bg-cyan-600 hover:bg-cyan-700"
              >
                {generating ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Generating...
                  </>
                ) : (
                  <>
                    <Download className="w-4 h-4 mr-2" />
                    Generate Report
                  </>
                )}
              </Button>
            </div>
          </div>

          {/* Export List */}
          <div className="bg-slate-900 rounded-lg shadow border border-slate-800">
            <div className="p-6 border-b border-slate-800 flex justify-between items-center">
              <h2 className="text-xl font-semibold text-slate-50">Available Exports</h2>
              <span className="text-sm text-slate-400">{exports.length} files ready</span>
            </div>
            <div className="space-y-2 p-6">
              {exports.map((item) => {
                const Icon = getFileIcon(item.type);
                return (
                  <div
                    key={item.id}
                    onClick={() => setSelectedExport(item.id)}
                    className={cn(
                      "p-4 rounded-lg border cursor-pointer transition-all duration-200",
                      selectedExport === item.id
                        ? "border-cyan-400 bg-slate-800"
                        : "border-slate-700 bg-slate-800/50 hover:border-slate-600"
                    )}
                  >
                    <div className="flex justify-between items-start">
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <Icon className="w-4 h-4 text-cyan-400" />
                          <h3 className="font-medium text-slate-100">{item.name}</h3>
                        </div>
                        <p className="text-sm text-slate-400 mt-1">{item.description}</p>
                        <span className="text-xs text-slate-500 mt-2 inline-block">{item.type}</span>
                      </div>
                      <div className="flex items-center gap-3">
                        <CheckCircle2 className="w-5 h-5 text-green-500" />
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={(e) => { e.stopPropagation(); downloadFile(item); }}
                        >
                          <Download className="w-4 h-4" />
                        </Button>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Metadata */}
          <div className="bg-slate-900 rounded-lg shadow border border-slate-800">
            <div className="p-6 border-b border-slate-800">
              <h2 className="text-xl font-semibold text-slate-50">Export Metadata</h2>
            </div>
            <div className="p-6 space-y-6">
              <div>
                <h3 className="font-semibold mb-3 text-slate-100">Analysis Summary</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="p-3 bg-slate-800 rounded-lg">
                    <p className="text-sm text-slate-400">Total Frames</p>
                    <p className="text-xl font-bold text-slate-100">{metadata.total_frames}</p>
                  </div>
                  <div className="p-3 bg-slate-800 rounded-lg">
                    <p className="text-sm text-slate-400">Tracks</p>
                    <p className="text-xl font-bold text-slate-100">{metadata.total_tracks}</p>
                  </div>
                  <div className="p-3 bg-slate-800 rounded-lg">
                    <p className="text-sm text-slate-400">Mean BT</p>
                    <p className="text-xl font-bold text-slate-100">{metadata.mean_bt} K</p>
                  </div>
                  <div className="p-3 bg-slate-800 rounded-lg">
                    <p className="text-sm text-slate-400">Min BT</p>
                    <p className="text-xl font-bold text-slate-100">{metadata.min_bt} K</p>
                  </div>
                </div>
              </div>

              <div>
                <h3 className="font-semibold mb-3 text-slate-100">NetCDF Format</h3>
                <div className="space-y-2">
                  <div className="p-2 bg-slate-800 rounded text-sm text-slate-300 font-mono">
                    Convention: CF-1.8
                  </div>
                  <div className="p-2 bg-slate-800 rounded text-sm text-slate-300 font-mono">
                    Variables: track_id, timestamp, centroid_lat, centroid_lon, area_km2, mean_bt
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Exports;
