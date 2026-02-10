import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { RefreshCw, Loader2, Upload, Cloud, Maximize2, Download } from 'lucide-react';
import Sidebar from '@/components/dashboard/Sidebar';
import DashboardHeader from '@/components/dashboard/DashboardHeader';
import apiClient from '@/services/api';

export default function Analysis() {
    const navigate = useNavigate();
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [analysis, setAnalysis] = useState(null);
    const [detections, setDetections] = useState([]);
    const [tccStats, setTccStats] = useState({ count: 0, totalArea: 0 });

    useEffect(() => {
        loadLatestAnalysis();
    }, []);

    const loadLatestAnalysis = async () => {
        setLoading(true);
        setError(null);

        try {
            const response = await fetch(`${apiClient.baseURL}/api/analyses/recent?limit=1`, {
                headers: {
                    'Authorization': `Bearer ${apiClient.getToken()}`
                }
            });

            if (!response.ok) {
                throw new Error('Failed to fetch analysis');
            }

            const analyses = await response.json();
            console.log('Analyses:', analyses);

            if (!analyses || analyses.length === 0) {
                setError('No analysis results found. Please upload a file first.');
                setLoading(false);
                return;
            }

            const latest = analyses[0];
            console.log('Latest analysis:', latest);

            // Parse results
            let parsedResults = {};
            if (latest.results) {
                parsedResults = typeof latest.results === 'string'
                    ? JSON.parse(latest.results)
                    : latest.results;
            }

            const tccDetections = parsedResults.detections || [];
            const tccCount = parsedResults.tcc_count || tccDetections.length || 0;
            const totalArea = parsedResults.total_area_km2 || 0;

            setDetections(tccDetections);
            setTccStats({ count: tccCount, totalArea: totalArea });

            setAnalysis({
                id: latest.analysis_id,
                filename: latest.filename,
                status: latest.status,
                overlay_url: `${apiClient.baseURL}/api/download/${latest.analysis_id}/overlay.png`,
                netcdf_url: `${apiClient.baseURL}/api/download/${latest.analysis_id}/output.nc`,
                mask_png_url: `${apiClient.baseURL}/api/download/${latest.analysis_id}/mask.png`,
            });

            setLoading(false);
        } catch (err) {
            console.error('Error loading analysis:', err);
            setError('Failed to load analysis. Please upload a file first.');
            setLoading(false);
        }
    };

    const downloadOverlay = () => {
        if (analysis?.overlay_url) {
            window.open(analysis.overlay_url, '_blank');
        }
    };

    return (
        <div className="flex h-screen bg-[#010816]">
            <Sidebar />
            <div className="flex-1 flex flex-col">
                <DashboardHeader />
                <div className="flex-1 overflow-auto p-6">
                    {/* Header */}
                    <div className="flex items-center justify-between mb-6">
                        <div>
                            <h1 className="text-2xl font-bold text-slate-50">TCC Analysis</h1>
                            <p className="text-slate-400">Combined IR + TCC Mask Visualization</p>
                        </div>
                        <Button
                            onClick={loadLatestAnalysis}
                            variant="outline"
                            className="border-slate-600 hover:bg-slate-700"
                        >
                            <RefreshCw className="w-4 h-4 mr-2" />
                            Refresh
                        </Button>
                    </div>

                    {/* Loading */}
                    {loading && (
                        <div className="flex items-center justify-center h-96">
                            <Loader2 className="w-12 h-12 animate-spin text-cyan-500" />
                        </div>
                    )}

                    {/* Error */}
                    {error && !loading && (
                        <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-12 text-center">
                            <Upload className="w-16 h-16 text-slate-500 mx-auto mb-4" />
                            <p className="text-slate-400 text-lg mb-6">{error}</p>
                            <Button
                                onClick={() => navigate('/dashboard/upload')}
                                className="bg-cyan-600 hover:bg-cyan-700"
                            >
                                Go to Upload
                            </Button>
                        </div>
                    )}

                    {/* Results */}
                    {!loading && !error && analysis && (
                        <>
                            {/* Stats Row */}
                            <div className="grid grid-cols-3 gap-4 mb-6">
                                <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-4">
                                    <div className="text-slate-400 text-sm">File</div>
                                    <div className="text-white font-medium truncate">{analysis.filename}</div>
                                </div>
                                <div className="bg-slate-800/50 border border-cyan-600/50 rounded-lg p-4">
                                    <div className="flex items-center gap-2 text-cyan-400 text-sm">
                                        <Cloud className="w-4 h-4" />
                                        TCC Detected
                                    </div>
                                    <div className="text-3xl font-bold text-white">{tccStats.count}</div>
                                </div>
                                <div className="bg-slate-800/50 border border-green-600/50 rounded-lg p-4">
                                    <div className="flex items-center gap-2 text-green-400 text-sm">
                                        <Maximize2 className="w-4 h-4" />
                                        Total Area
                                    </div>
                                    <div className="text-3xl font-bold text-white">
                                        {tccStats.totalArea > 0 ? `${(tccStats.totalArea / 1000).toFixed(0)}k km²` : '0'}
                                    </div>
                                </div>
                            </div>

                            {/* MAIN OUTPUT: Combined Overlay (IR + TCC Mask) */}
                            <div className="bg-slate-900 rounded-xl border border-slate-700 overflow-hidden mb-6">
                                <div className="p-4 border-b border-slate-700 flex items-center justify-between">
                                    <div>
                                        <h3 className="text-lg font-semibold text-cyan-400">
                                            TCC Detection Result
                                        </h3>
                                        <p className="text-sm text-slate-400">
                                            Left: IR Brightness Temperature | Right: TCC Mask
                                        </p>
                                    </div>
                                    <Button
                                        onClick={downloadOverlay}
                                        variant="outline"
                                        size="sm"
                                        className="border-slate-600"
                                    >
                                        <Download className="w-4 h-4 mr-2" />
                                        Overlay PNG
                                    </Button>
                                    {analysis.netcdf_url && (
                                        <a
                                            href={analysis.netcdf_url}
                                            download
                                            className="inline-flex items-center px-3 py-1 bg-green-600 hover:bg-green-700 text-white text-sm rounded-md"
                                        >
                                            <Download className="w-4 h-4 mr-2" />
                                            NetCDF
                                        </a>
                                    )}
                                </div>
                                <div className="p-4 bg-black">
                                    <img
                                        src={`${analysis.overlay_url}?t=${Date.now()}`}
                                        alt="TCC Detection Result"
                                        className="w-full rounded"
                                        style={{ maxHeight: '700px', objectFit: 'contain' }}
                                        onError={(e) => {
                                            console.error('Image load error');
                                            e.target.style.display = 'none';
                                            document.getElementById('img-error').style.display = 'flex';
                                        }}
                                    />
                                    <div
                                        id="img-error"
                                        className="hidden items-center justify-center h-64 text-slate-500"
                                    >
                                        Image not available. Please upload and process a file first.
                                    </div>
                                </div>
                            </div>

                            {/* Detection Table */}
                            {detections.length > 0 && (
                                <div className="bg-slate-900 rounded-xl border border-slate-700 overflow-hidden">
                                    <div className="p-4 border-b border-slate-700">
                                        <h3 className="text-lg font-semibold text-cyan-400">
                                            Detected Cloud Clusters
                                        </h3>
                                    </div>
                                    <div className="overflow-x-auto">
                                        <table className="w-full text-sm">
                                            <thead className="bg-slate-800">
                                                <tr>
                                                    <th className="px-4 py-3 text-left text-slate-400">ID</th>
                                                    <th className="px-4 py-3 text-left text-slate-400">Classification</th>
                                                    <th className="px-4 py-3 text-left text-slate-400">Area (km²)</th>
                                                    <th className="px-4 py-3 text-left text-slate-400">Radius (km)</th>
                                                    <th className="px-4 py-3 text-left text-slate-400">Centroid</th>
                                                    <th className="px-4 py-3 text-left text-slate-400">Mean BT (K)</th>
                                                    <th className="px-4 py-3 text-left text-slate-400">Min BT (K)</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {detections.map((d, idx) => (
                                                    <tr key={idx} className="border-t border-slate-800">
                                                        <td className="px-4 py-3 text-white font-mono">TCC-{d.cluster_id}</td>
                                                        <td className="px-4 py-3">
                                                            <span className={`inline-flex px-2 py-1 rounded-full text-xs font-semibold ${d.classification === 'Confirmed TCC' ? 'bg-red-500/20 text-red-300 border border-red-500/30' :
                                                                    d.classification === 'Likely TCC' ? 'bg-yellow-500/20 text-yellow-300 border border-yellow-500/30' :
                                                                        'bg-slate-500/20 text-slate-300 border border-slate-500/30'
                                                                }`}>
                                                                {d.classification || (d.is_tcc ? 'Likely TCC' : 'Cloud Cluster')}
                                                            </span>
                                                        </td>
                                                        <td className="px-4 py-3 text-cyan-400">{d.area_km2?.toLocaleString()}</td>
                                                        <td className="px-4 py-3 text-slate-300">{d.radius_km?.toFixed(1)}</td>
                                                        <td className="px-4 py-3 text-slate-300">
                                                            {d.centroid_lat?.toFixed(2)}°, {d.centroid_lon?.toFixed(2)}°
                                                        </td>
                                                        <td className="px-4 py-3 text-orange-400">{d.mean_bt?.toFixed(1)}</td>
                                                        <td className="px-4 py-3 text-red-400">{d.min_bt?.toFixed(1)}</td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>
                                </div>
                            )}
                        </>
                    )}
                </div>
            </div>
        </div>
    );
}
