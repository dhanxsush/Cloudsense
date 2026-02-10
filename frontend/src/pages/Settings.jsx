import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { ArrowLeft, Save, RotateCcw } from 'lucide-react';

// Default settings
const DEFAULT_SETTINGS = {
    inference: {
        threshold: 0.5,
        overlayEnabled: true,
    },
    mosdac: {
        datasetId: '3RIMG_L1C_ASIA_MER',
        hoursBack: 24,
        autoDownload: false,
    },
    output: {
        directory: './outputs',
        overwritePrevious: true,
    },
    system: {
        device: 'auto', // 'auto', 'cpu', 'gpu'
    },
};

// Load settings from localStorage
const loadSettings = () => {
    try {
        const saved = localStorage.getItem('cloudsense_settings');
        if (saved) {
            return { ...DEFAULT_SETTINGS, ...JSON.parse(saved) };
        }
    } catch (e) {
        console.error('Error loading settings:', e);
    }
    return DEFAULT_SETTINGS;
};

// Save settings to localStorage
const saveSettings = (settings) => {
    localStorage.setItem('cloudsense_settings', JSON.stringify(settings));
};

export default function Settings() {
    const navigate = useNavigate();
    const [settings, setSettings] = useState(loadSettings);
    const [saved, setSaved] = useState(false);

    const updateSetting = (category, key, value) => {
        setSettings(prev => ({
            ...prev,
            [category]: {
                ...prev[category],
                [key]: value,
            },
        }));
        setSaved(false);
    };

    const handleSave = () => {
        saveSettings(settings);
        setSaved(true);
        setTimeout(() => setSaved(false), 2000);
    };

    const handleReset = () => {
        setSettings(DEFAULT_SETTINGS);
        saveSettings(DEFAULT_SETTINGS);
        setSaved(true);
    };

    return (
        <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 text-white">
            <div className="max-w-4xl mx-auto px-4 py-8">
                {/* Header */}
                <div className="flex items-center justify-between mb-8">
                    <div className="flex items-center gap-4">
                        <button
                            onClick={() => navigate('/dashboard')}
                            className="p-2 hover:bg-slate-700 rounded-lg transition-colors"
                        >
                            <ArrowLeft className="w-5 h-5" />
                        </button>
                        <h1 className="text-2xl font-bold">Settings</h1>
                    </div>
                    <div className="flex gap-2">
                        <Button
                            onClick={handleReset}
                            variant="outline"
                            className="border-slate-600 hover:bg-slate-700"
                        >
                            <RotateCcw className="w-4 h-4 mr-2" />
                            Reset
                        </Button>
                        <Button
                            onClick={handleSave}
                            className="bg-cyan-600 hover:bg-cyan-700"
                        >
                            <Save className="w-4 h-4 mr-2" />
                            {saved ? 'Saved!' : 'Save'}
                        </Button>
                    </div>
                </div>

                {/* Inference Settings */}
                <section className="bg-slate-800/50 rounded-xl p-6 mb-6 border border-slate-700">
                    <h2 className="text-lg font-semibold text-cyan-400 mb-4">🔧 Inference Settings</h2>

                    <div className="space-y-4">
                        <div className="flex items-center justify-between">
                            <div>
                                <label className="font-medium">Probability Threshold</label>
                                <p className="text-sm text-slate-400">Minimum confidence for TCC detection</p>
                            </div>
                            <div className="flex items-center gap-4">
                                <input
                                    type="range"
                                    min="0.1"
                                    max="0.9"
                                    step="0.05"
                                    value={settings.inference.threshold}
                                    onChange={(e) => updateSetting('inference', 'threshold', parseFloat(e.target.value))}
                                    className="w-32 accent-cyan-500"
                                />
                                <span className="w-12 text-center bg-slate-700 px-2 py-1 rounded">
                                    {settings.inference.threshold.toFixed(2)}
                                </span>
                            </div>
                        </div>

                        <div className="flex items-center justify-between">
                            <div>
                                <label className="font-medium">Overlay Mask</label>
                                <p className="text-sm text-slate-400">Show TCC mask overlay on satellite image</p>
                            </div>
                            <button
                                onClick={() => updateSetting('inference', 'overlayEnabled', !settings.inference.overlayEnabled)}
                                className={`w-12 h-6 rounded-full transition-colors ${settings.inference.overlayEnabled ? 'bg-cyan-500' : 'bg-slate-600'
                                    }`}
                            >
                                <div className={`w-5 h-5 bg-white rounded-full transition-transform ${settings.inference.overlayEnabled ? 'translate-x-6' : 'translate-x-1'
                                    }`} />
                            </button>
                        </div>
                    </div>
                </section>

                {/* MOSDAC Settings */}
                <section className="bg-slate-800/50 rounded-xl p-6 mb-6 border border-slate-700">
                    <h2 className="text-lg font-semibold text-cyan-400 mb-4">🛰 MOSDAC Settings</h2>

                    <div className="space-y-4">
                        <div className="flex items-center justify-between">
                            <div>
                                <label className="font-medium">Dataset ID</label>
                                <p className="text-sm text-slate-400">INSAT-3D product identifier</p>
                            </div>
                            <select
                                value={settings.mosdac.datasetId}
                                onChange={(e) => updateSetting('mosdac', 'datasetId', e.target.value)}
                                className="bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm"
                            >
                                <option value="3RIMG_L1C_ASIA_MER">3RIMG_L1C_ASIA_MER</option>
                                <option value="3RIMG_L1C_INDIA">3RIMG_L1C_INDIA</option>
                                <option value="3DIMG_L1C_ASIA">3DIMG_L1C_ASIA</option>
                            </select>
                        </div>

                        <div className="flex items-center justify-between">
                            <div>
                                <label className="font-medium">Hours Back</label>
                                <p className="text-sm text-slate-400">Default time range for data download</p>
                            </div>
                            <input
                                type="number"
                                min="1"
                                max="168"
                                value={settings.mosdac.hoursBack}
                                onChange={(e) => updateSetting('mosdac', 'hoursBack', parseInt(e.target.value))}
                                className="w-20 bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm text-center"
                            />
                        </div>

                        <div className="flex items-center justify-between">
                            <div>
                                <label className="font-medium">Auto-Download</label>
                                <p className="text-sm text-slate-400">Automatically fetch latest data on page load</p>
                            </div>
                            <button
                                onClick={() => updateSetting('mosdac', 'autoDownload', !settings.mosdac.autoDownload)}
                                className={`w-12 h-6 rounded-full transition-colors ${settings.mosdac.autoDownload ? 'bg-cyan-500' : 'bg-slate-600'
                                    }`}
                            >
                                <div className={`w-5 h-5 bg-white rounded-full transition-transform ${settings.mosdac.autoDownload ? 'translate-x-6' : 'translate-x-1'
                                    }`} />
                            </button>
                        </div>
                    </div>
                </section>

                {/* Output Settings */}
                <section className="bg-slate-800/50 rounded-xl p-6 mb-6 border border-slate-700">
                    <h2 className="text-lg font-semibold text-cyan-400 mb-4">📁 Output Settings</h2>

                    <div className="space-y-4">
                        <div className="flex items-center justify-between">
                            <div>
                                <label className="font-medium">Output Directory</label>
                                <p className="text-sm text-slate-400">Where to save inference results</p>
                            </div>
                            <input
                                type="text"
                                value={settings.output.directory}
                                onChange={(e) => updateSetting('output', 'directory', e.target.value)}
                                className="w-48 bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm"
                            />
                        </div>

                        <div className="flex items-center justify-between">
                            <div>
                                <label className="font-medium">Overwrite Previous</label>
                                <p className="text-sm text-slate-400">Replace existing output files</p>
                            </div>
                            <button
                                onClick={() => updateSetting('output', 'overwritePrevious', !settings.output.overwritePrevious)}
                                className={`w-12 h-6 rounded-full transition-colors ${settings.output.overwritePrevious ? 'bg-cyan-500' : 'bg-slate-600'
                                    }`}
                            >
                                <div className={`w-5 h-5 bg-white rounded-full transition-transform ${settings.output.overwritePrevious ? 'translate-x-6' : 'translate-x-1'
                                    }`} />
                            </button>
                        </div>
                    </div>
                </section>

                {/* System Settings */}
                <section className="bg-slate-800/50 rounded-xl p-6 border border-slate-700">
                    <h2 className="text-lg font-semibold text-cyan-400 mb-4">⚙ System Settings</h2>

                    <div className="flex items-center justify-between">
                        <div>
                            <label className="font-medium">Compute Device</label>
                            <p className="text-sm text-slate-400">Hardware for model inference</p>
                        </div>
                        <select
                            value={settings.system.device}
                            onChange={(e) => updateSetting('system', 'device', e.target.value)}
                            className="bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm"
                        >
                            <option value="auto">Auto (Recommended)</option>
                            <option value="cpu">CPU Only</option>
                            <option value="gpu">GPU (MPS/CUDA)</option>
                        </select>
                    </div>
                </section>
            </div>
        </div>
    );
}

// Export helper to get settings from other components
export const getSettings = loadSettings;
