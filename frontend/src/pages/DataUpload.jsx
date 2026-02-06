import { useState, useCallback } from 'react';
import { Upload, FileType, CheckCircle2, AlertCircle, Loader2 } from 'lucide-react';
import Sidebar from '@/components/dashboard/Sidebar';
import DashboardHeader from '@/components/dashboard/DashboardHeader';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { useToast } from "@/components/ui/use-toast";
import { useNavigate } from 'react-router-dom';
import { useAnalysisContext } from '@/contexts/AnalysisContext';
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
  const { selectAnalysis } = useAnalysisContext();

  const addLog = (message) => {
    setLogs(prev => [...prev, { time: new Date().toLocaleTimeString(), message }]);
  };

  const handleFileSelect = (file) => {
    if (file && (file.name.endsWith('.h5') || file.name.endsWith('.hdf5') || file.name.endsWith('.nc'))) {
      setSelectedFile(file);
      setProcessingStatus(null);
      setLogs([]);
    } else {
      toast({
        title: "Invalid File",
        description: "Please select an HDF5 (.h5, .hdf5) or NetCDF (.nc) file",
        variant: "destructive"
      });
    }
  };

  const uploadAndProcess = async () => {
    if (!selectedFile) return;

    setIsUploading(true);
    setProcessingStatus('uploading');
    setLogs([]);
    addLog("Initializing upload...");

    try {
      addLog("Processing file (Demo Mode)...");

      // Use mock API - simulates processing
      const result = await apiClient.uploadFile(selectedFile, (progress) => {
        setUploadProgress(progress);
        if (progress === 50) {
          addLog("Running U-Net inference...");
        }
        if (progress === 80) {
          addLog("Applying Kalman tracking...");
        }
      });

      addLog("Upload complete. Analysis started...");
      setProcessingStatus('processing');

      if (result.analysis_id) {
        selectAnalysis(result.analysis_id);
        addLog(`✓ Analysis Complete. Processed ${result.total_frames} frames.`);
        addLog(`Analysis ID: ${result.analysis_id}`);
        setProcessingStatus('complete');

        toast({
          title: "Analysis Complete",
          description: `Successfully processed ${selectedFile.name}. Redirecting...`,
        });

        setTimeout(() => {
          navigate('/analysis');
        }, 2000);
      }
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
            {/* Demo Mode Banner */}
            <div className="bg-cyan-500/10 border border-cyan-500/30 rounded-lg p-4 flex items-center gap-3">
              <span className="text-cyan-400 text-sm">🎮 Demo Mode Active - No backend required. Upload any file to see simulated analysis.</span>
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
                Drop your satellite data here
              </h3>
              <p className="text-slate-400 mb-4">
                Supports HDF5 (.h5, .hdf5) and NetCDF (.nc) files
              </p>
              <input
                type="file"
                id="file-input"
                className="hidden"
                accept=".h5,.hdf5,.nc"
                onChange={(e) => e.target.files[0] && handleFileSelect(e.target.files[0])}
              />
              <Button onClick={() => document.getElementById('file-input').click()}>
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
                      "Start Analysis"
                    )}
                  </Button>
                </div>

                {/* Progress */}
                {isUploading && (
                  <div className="mt-4">
                    <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-gradient-to-r from-cyan-500 to-blue-500 transition-all duration-300"
                        style={{ width: `${uploadProgress}%` }}
                      />
                    </div>
                    <p className="text-sm text-slate-400 mt-2">{uploadProgress}% complete</p>
                  </div>
                )}
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
                  {(processingStatus === 'uploading' || processingStatus === 'processing') && (
                    <Loader2 className="w-6 h-6 text-cyan-400 animate-spin" />
                  )}
                  <span className="font-medium text-slate-200 capitalize">
                    {processingStatus === 'complete' ? 'Analysis Complete' : processingStatus}
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
          </div>
        </div>
      </div>
    </div>
  );
};

export default DataUpload;
