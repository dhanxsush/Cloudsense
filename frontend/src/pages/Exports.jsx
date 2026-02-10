import { useState, useEffect } from 'react';
import { Download, FileType, Loader2, Database, Image, RefreshCw } from 'lucide-react';
import Sidebar from '@/components/dashboard/Sidebar';
import DashboardHeader from '@/components/dashboard/DashboardHeader';
import { Button } from '@/components/ui/button';
import { useToast } from "@/components/ui/use-toast";
import apiClient from '@/services/api';

const Exports = () => {
  const [loading, setLoading] = useState(true);
  const [exports, setExports] = useState([]);
  const [error, setError] = useState(null);
  const { toast } = useToast();

  useEffect(() => {
    fetchExports();
  }, []);

  const fetchExports = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${apiClient.baseURL}/api/exports`, {
        headers: {
          'Authorization': `Bearer ${apiClient.getToken()}`
        }
      });

      if (!response.ok) {
        throw new Error('Failed to fetch exports');
      }

      const data = await response.json();
      setExports(data);
    } catch (err) {
      console.error('Error fetching exports:', err);
      setError('No exports available. Run inference first.');
    } finally {
      setLoading(false);
    }
  };

  const downloadFile = async (url, filename) => {
    try {
      const response = await fetch(`${apiClient.baseURL}${url}`, {
        headers: {
          'Authorization': `Bearer ${apiClient.getToken()}`
        }
      });

      if (!response.ok) {
        throw new Error('Download failed');
      }

      const blob = await response.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = downloadUrl;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(downloadUrl);

      toast({
        title: "Download Started",
        description: `Downloading ${filename}`,
      });
    } catch (err) {
      toast({
        title: "Download Failed",
        description: err.message,
        variant: "destructive"
      });
    }
  };

  const getFileIcon = (filename) => {
    if (filename.endsWith('.nc')) return Database;
    if (filename.endsWith('.png')) return Image;
    return FileType;
  };

  return (
    <div className="flex h-screen bg-[#010816]">
      <Sidebar />
      <div className="flex-1 flex flex-col">
        <DashboardHeader />
        <div className="flex-1 overflow-auto p-6 space-y-6">
          {/* Header */}
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-2xl font-bold text-slate-50">Exports</h1>
              <p className="text-slate-400">Download inference outputs: mask.npy, mask.png, output.nc</p>
            </div>
            <Button
              onClick={fetchExports}
              variant="outline"
              className="border-slate-600 hover:bg-slate-700"
            >
              <RefreshCw className="w-4 h-4 mr-2" />
              Refresh
            </Button>
          </div>

          {/* Loading */}
          {loading && (
            <div className="flex items-center justify-center h-64">
              <Loader2 className="w-8 h-8 animate-spin text-cyan-500" />
            </div>
          )}

          {/* Error / Empty State */}
          {!loading && (error || exports.length === 0) && (
            <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-8 text-center">
              <FileType className="w-12 h-12 text-slate-500 mx-auto mb-4" />
              <p className="text-slate-400 text-lg mb-4">
                {error || 'No exports available'}
              </p>
              <Button
                onClick={() => window.location.href = '/dashboard/upload'}
                className="bg-cyan-600 hover:bg-cyan-700"
              >
                Upload & Process Data
              </Button>
            </div>
          )}

          {/* Exports List */}
          {!loading && exports.length > 0 && (
            <div className="space-y-4">
              {exports.map((analysis) => (
                <div
                  key={analysis.analysis_id}
                  className="bg-slate-900 rounded-xl border border-slate-700 p-6"
                >
                  <div className="flex justify-between items-start mb-4">
                    <div>
                      <h3 className="font-semibold text-lg text-slate-100">
                        Analysis: {analysis.analysis_id.slice(0, 8)}...
                      </h3>
                      <p className="text-sm text-slate-400">
                        {analysis.files.length} output files
                      </p>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    {/* mask.npy */}
                    {analysis.download_urls.mask_npy && (
                      <div className="bg-slate-800 rounded-lg p-4 flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <FileType className="w-8 h-8 text-purple-400" />
                          <div>
                            <p className="font-medium text-slate-100">mask.npy</p>
                            <p className="text-xs text-slate-400">NumPy Binary Mask</p>
                          </div>
                        </div>
                        <Button
                          size="sm"
                          onClick={() => downloadFile(analysis.download_urls.mask_npy, `${analysis.analysis_id}_mask.npy`)}
                          className="bg-cyan-600 hover:bg-cyan-700"
                        >
                          <Download className="w-4 h-4" />
                        </Button>
                      </div>
                    )}

                    {/* mask.png */}
                    {analysis.download_urls.mask_png && (
                      <div className="bg-slate-800 rounded-lg p-4 flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <Image className="w-8 h-8 text-green-400" />
                          <div>
                            <p className="font-medium text-slate-100">mask.png</p>
                            <p className="text-xs text-slate-400">Visual Mask</p>
                          </div>
                        </div>
                        <Button
                          size="sm"
                          onClick={() => downloadFile(analysis.download_urls.mask_png, `${analysis.analysis_id}_mask.png`)}
                          className="bg-cyan-600 hover:bg-cyan-700"
                        >
                          <Download className="w-4 h-4" />
                        </Button>
                      </div>
                    )}

                    {/* output.nc */}
                    {analysis.download_urls.netcdf && (
                      <div className="bg-slate-800 rounded-lg p-4 flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <Database className="w-8 h-8 text-cyan-400" />
                          <div>
                            <p className="font-medium text-slate-100">output.nc</p>
                            <p className="text-xs text-slate-400">NetCDF (CF-1.8)</p>
                          </div>
                        </div>
                        <Button
                          size="sm"
                          onClick={() => downloadFile(analysis.download_urls.netcdf, `${analysis.analysis_id}_output.nc`)}
                          className="bg-cyan-600 hover:bg-cyan-700"
                        >
                          <Download className="w-4 h-4" />
                        </Button>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Info Box */}
          <div className="bg-slate-800/30 border border-slate-700 rounded-lg p-4">
            <h4 className="font-semibold text-cyan-400 mb-2">Output Specification (PRD FR-4)</h4>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm text-slate-400">
              <div>
                <span className="text-slate-200">mask.npy</span> - Binary mask array (H×W)
              </div>
              <div>
                <span className="text-slate-200">mask.png</span> - Visual representation
              </div>
              <div>
                <span className="text-slate-200">output.nc</span> - NetCDF with irbt, tcc_probability, tcc_mask
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Exports;
