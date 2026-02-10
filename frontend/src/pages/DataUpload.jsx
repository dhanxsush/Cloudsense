import { useState } from 'react';
import { Upload, FileType, CheckCircle2, AlertCircle, Loader2, Cloud, Download } from 'lucide-react';
import Sidebar from '@/components/dashboard/Sidebar';
import DashboardHeader from '@/components/dashboard/DashboardHeader';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { cn } from '@/lib/utils';
import { useToast } from "@/components/ui/use-toast";
import { useNavigate } from 'react-router-dom';
import apiClient from '@/services/api';

const DataUpload = () => {
  const [isDragging, setIsDragging] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [processingStatus, setProcessingStatus] = useState(null);
  const [logs, setLogs] = useState([]);
  const { toast } = useToast();
  const navigate = useNavigate();

  // MOSDAC credentials
  const [mosdacUsername, setMosdacUsername] = useState('');
  const [mosdacPassword, setMosdacPassword] = useState('');
  const [hoursBack, setHoursBack] = useState(6);
  const [isDownloading, setIsDownloading] = useState(false);
  const [downloadResults, setDownloadResults] = useState(null);

  const addLog = (message) => {
    setLogs(prev => [...prev, { time: new Date().toLocaleTimeString(), message }]);
  };

  // ==================== MOSDAC DOWNLOAD ====================
  const handleMosdacDownload = async () => {
    if (!mosdacUsername || !mosdacPassword) {
      toast({
        title: "Missing Credentials",
        description: "Please enter your MOSDAC username and password",
        variant: "destructive"
      });
      return;
    }

    setIsDownloading(true);
    setProcessingStatus('downloading');
    setLogs([]);
    addLog("Connecting to MOSDAC API...");
    addLog(`Dataset: 3RIMG_L1C_ASIA_MER (INSAT-3DR Asian Sector)`);
    addLog(`Time range: Last ${hoursBack} hours`);

    try {
      const response = await fetch(`${apiClient.baseURL}/api/mosdac/download`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${apiClient.getToken()}`
        },
        body: JSON.stringify({
          username: mosdacUsername,
          password: mosdacPassword,
          hours_back: hoursBack
        })
      });

      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.detail || 'Download failed');
      }

      if (result.status === 'no_data') {
        addLog("⚠ No data available for the selected time range");
        setProcessingStatus('no_data');
      } else {
        addLog(`✓ Downloaded ${result.files_downloaded} files`);
        addLog("Running U-Net inference on downloaded data...");

        result.results?.forEach((r, i) => {
          addLog(`✓ Processed: ${r.file} — ${r.tcc_count || 0} TCCs detected, ${r.tcc_pixels} TCC pixels`);
          if (r.total_area_km2) addLog(`   Total area: ${(r.total_area_km2 / 1000).toFixed(0)}k km²`);
        });

        addLog("✓ All files processed successfully!");
        setProcessingStatus('complete');
        setDownloadResults(result.results);

        toast({
          title: "Download & Analysis Complete",
          description: `Processed ${result.files_downloaded} files from MOSDAC`,
        });
      }
    } catch (error) {
      console.error(error);
      setProcessingStatus('error');
      addLog(`Error: ${error.message}`);
      toast({
        title: "MOSDAC Download Failed",
        description: error.message,
        variant: "destructive"
      });
    } finally {
      setIsDownloading(false);
    }
  };

  // ==================== FILE UPLOAD ====================
  const handleFileSelect = (file) => {
    const validExtensions = ['.h5', '.hdf5', '.png', '.jpg', '.jpeg'];
    const fileExt = file.name.toLowerCase().slice(file.name.lastIndexOf('.'));

    if (file && validExtensions.includes(fileExt)) {
      setSelectedFile(file);
      setProcessingStatus(null);
      setLogs([]);
      setDownloadResults(null);
    } else {
      toast({
        title: "Invalid File",
        description: "Please select an HDF5 (.h5, .hdf5) or image (.png, .jpg, .jpeg) file",
        variant: "destructive"
      });
    }
  };

  const uploadAndProcess = async () => {
    if (!selectedFile) return;

    setIsUploading(true);
    setProcessingStatus('uploading');
    setLogs([]);
    setDownloadResults(null);
    addLog("Uploading file...");

    try {
      const formData = new FormData();
      formData.append('file', selectedFile);

      const response = await fetch(`${apiClient.baseURL}/api/upload`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${apiClient.getToken()}`
        },
        body: formData
      });

      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.detail || 'Upload failed');
      }

      addLog("✓ Upload complete");
      addLog("Running U-Net inference...");
      addLog(`✓ Analysis Complete! TCC pixels: ${result.tcc_pixels}`);
      addLog(`Analysis ID: ${result.analysis_id}`);

      setProcessingStatus('complete');
      setDownloadResults([{
        analysis_id: result.analysis_id,
        file: selectedFile.name,
        tcc_pixels: result.tcc_pixels,
        tcc_count: result.tcc_count,
        total_area_km2: result.total_area_km2,
        detections: result.detections,
        outputs: result.outputs
      }]);

      toast({
        title: "Analysis Complete",
        description: `Successfully processed ${selectedFile.name}`,
      });

    } catch (error) {
      console.error(error);
      setProcessingStatus('error');
      addLog(`Error: ${error.message}`);
      toast({
        title: "Processing Failed",
        description: error.message,
        variant: "destructive"
      });
    } finally {
      setIsUploading(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      handleFileSelect(files[0]);
    }
  };

  return (
    <div className="flex h-screen bg-[#010816]">
      <Sidebar />
      <div className="flex-1 flex flex-col">
        <DashboardHeader />
        <div className="flex-1 overflow-auto p-6">
          <div className="max-w-4xl mx-auto space-y-6">

            {/* MOSDAC Download Section */}
            <div className="bg-gradient-to-br from-cyan-900/30 to-blue-900/30 rounded-xl border border-cyan-500/30 p-6">
              <div className="flex items-center gap-3 mb-4">
                <Cloud className="w-8 h-8 text-cyan-400" />
                <div>
                  <h2 className="text-xl font-bold text-slate-100">Download from MOSDAC</h2>
                  <p className="text-sm text-slate-400">INSAT-3DR: 3RIMG_L1C_ASIA_MER (Asian Sector)</p>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
                <div>
                  <label className="text-sm text-slate-400 block mb-1">MOSDAC Username</label>
                  <Input
                    type="text"
                    placeholder="Your MOSDAC username"
                    value={mosdacUsername}
                    onChange={(e) => setMosdacUsername(e.target.value)}
                    className="bg-slate-800 border-slate-700"
                  />
                </div>
                <div>
                  <label className="text-sm text-slate-400 block mb-1">MOSDAC Password</label>
                  <Input
                    type="password"
                    placeholder="Your MOSDAC password"
                    value={mosdacPassword}
                    onChange={(e) => setMosdacPassword(e.target.value)}
                    className="bg-slate-800 border-slate-700"
                  />
                </div>
                <div>
                  <label className="text-sm text-slate-400 block mb-1">Hours Back</label>
                  <Input
                    type="number"
                    min="1"
                    max="72"
                    value={hoursBack}
                    onChange={(e) => setHoursBack(parseInt(e.target.value) || 6)}
                    className="bg-slate-800 border-slate-700"
                  />
                </div>
              </div>

              <Button
                onClick={handleMosdacDownload}
                disabled={isDownloading}
                className="bg-cyan-600 hover:bg-cyan-700 w-full"
              >
                {isDownloading ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Downloading & Processing...
                  </>
                ) : (
                  <>
                    <Download className="w-4 h-4 mr-2" />
                    Download Current Data & Run Inference
                  </>
                )}
              </Button>

              <p className="text-xs text-slate-500 mt-2">
                Don't have an account? <a href="https://mosdac.gov.in/signup/" target="_blank" rel="noopener noreferrer" className="text-cyan-400 hover:underline">Sign up at MOSDAC</a>
              </p>
            </div>

            {/* Divider */}
            <div className="flex items-center gap-4">
              <div className="flex-1 h-px bg-slate-700" />
              <span className="text-slate-500 text-sm">OR</span>
              <div className="flex-1 h-px bg-slate-700" />
            </div>

            {/* Upload Area */}
            <div
              onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={handleDrop}
              className={cn(
                "border-2 border-dashed rounded-xl p-12 text-center transition-all duration-300",
                isDragging ? "border-cyan-400 bg-cyan-400/10" : "border-slate-700 bg-slate-900/50",
                "hover:border-slate-500"
              )}
            >
              <Upload className="w-16 h-16 mx-auto mb-4 text-slate-500" />
              <h3 className="text-xl font-semibold text-slate-200 mb-2">
                Upload Local File
              </h3>
              <p className="text-slate-400 mb-4">
                Drag & drop or browse for HDF5 (.h5, .hdf5) or image (.png, .jpg, .jpeg) files
              </p>
              <input
                type="file"
                id="file-input"
                className="hidden"
                accept=".h5,.hdf5,.png,.jpg,.jpeg"
                onChange={(e) => e.target.files[0] && handleFileSelect(e.target.files[0])}
              />
              <Button variant="outline" onClick={() => document.getElementById('file-input').click()}>
                Browse Files
              </Button>
            </div>

            {/* Selected File */}
            {selectedFile && (
              <div className="bg-slate-900 rounded-lg border border-slate-800 p-6">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <FileType className="w-10 h-10 text-cyan-400" />
                    <div>
                      <p className="font-medium text-slate-200">{selectedFile.name}</p>
                      <p className="text-sm text-slate-400">
                        {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                      </p>
                    </div>
                  </div>
                  <Button
                    onClick={uploadAndProcess}
                    disabled={isUploading}
                    className="bg-cyan-600 hover:bg-cyan-700"
                  >
                    {isUploading ? (
                      <>
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        Processing...
                      </>
                    ) : (
                      "Run Inference"
                    )}
                  </Button>
                </div>
              </div>
            )}

            {/* Status & Logs */}
            {processingStatus && (
              <div className="bg-slate-900 rounded-lg border border-slate-800 p-6">
                <div className="flex items-center gap-3 mb-4">
                  {processingStatus === 'complete' && (
                    <CheckCircle2 className="w-6 h-6 text-green-500" />
                  )}
                  {processingStatus === 'error' && (
                    <AlertCircle className="w-6 h-6 text-red-500" />
                  )}
                  {processingStatus === 'no_data' && (
                    <AlertCircle className="w-6 h-6 text-yellow-500" />
                  )}
                  {(processingStatus === 'uploading' || processingStatus === 'downloading' || processingStatus === 'processing') && (
                    <Loader2 className="w-6 h-6 text-cyan-400 animate-spin" />
                  )}
                  <span className="font-medium text-slate-200 capitalize">
                    {processingStatus === 'complete' ? 'Analysis Complete' :
                      processingStatus === 'no_data' ? 'No Data Available' : processingStatus}
                  </span>
                </div>

                {/* Log Output */}
                <div className="bg-slate-950 rounded-lg p-4 font-mono text-sm max-h-48 overflow-auto">
                  {logs.map((log, i) => (
                    <div key={i} className="text-slate-400">
                      <span className="text-slate-600">[{log.time}]</span> {log.message}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Download Results - Combined Visualization */}
            {downloadResults && downloadResults.length > 0 && (
              <div className="bg-slate-900 rounded-lg border border-green-500/30 p-6">
                <h3 className="text-lg font-semibold text-slate-200 mb-4">📦 TCC Detection Result</h3>
                <div className="space-y-4">
                  {downloadResults.map((result, i) => (
                    <div key={i} className="space-y-4">
                      <p className="text-slate-400 text-sm">{result.file}</p>

                      {/* Combined visualization (IR + TCC Mask) */}
                      <div className="bg-black rounded-lg overflow-hidden">
                        <img
                          src={`${apiClient.baseURL}${result.outputs.overlay_png}?t=${Date.now()}`}
                          alt="TCC Detection Result"
                          className="w-full"
                          onError={(e) => {
                            e.target.style.display = 'none';
                            e.target.nextSibling.style.display = 'flex';
                          }}
                        />
                        <div className="hidden items-center justify-center h-48 text-slate-500">
                          Combined visualization loading...
                        </div>
                      </div>

                      {/* Stats */}
                      <div className="grid grid-cols-3 gap-4">
                        <div className="bg-slate-800 rounded-lg p-3">
                          <p className="text-slate-400 text-sm">TCC Pixels</p>
                          <p className="text-2xl font-bold text-purple-400">{result.tcc_pixels || 0}</p>
                        </div>
                        <div className="bg-slate-800 rounded-lg p-3">
                          <p className="text-slate-400 text-sm">TCC Count</p>
                          <p className="text-2xl font-bold text-cyan-400">{result.tcc_count || 0}</p>
                        </div>
                        <div className="bg-slate-800 rounded-lg p-3">
                          <p className="text-slate-400 text-sm">Total Area</p>
                          <p className="text-2xl font-bold text-green-400">
                            {result.total_area_km2 ? `${(result.total_area_km2 / 1000).toFixed(0)}k km²` : '0'}
                          </p>
                        </div>
                      </div>

                      {/* Download buttons */}
                      <div className="flex flex-wrap gap-2">
                        <a
                          href={`${apiClient.baseURL}${result.outputs.overlay_png}`}
                          className="px-3 py-1 bg-cyan-600 hover:bg-cyan-700 text-white text-sm rounded"
                          download
                        >
                          📊 Download Result
                        </a>
                        {result.outputs.netcdf && (
                          <a
                            href={`${apiClient.baseURL}${result.outputs.netcdf}`}
                            className="px-3 py-1 bg-green-600 hover:bg-green-700 text-white text-sm rounded"
                            download
                          >
                            📁 NetCDF
                          </a>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
                <Button
                  onClick={() => navigate('/analysis')}
                  className="mt-4 w-full bg-cyan-600 hover:bg-cyan-700"
                >
                  View Analysis Details
                </Button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default DataUpload;
