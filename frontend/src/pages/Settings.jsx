import { useState } from 'react';
import { Settings, Monitor, Thermometer, Info, Shield, Database } from 'lucide-react';
import Sidebar from '@/components/dashboard/Sidebar';
import DashboardHeader from '@/components/dashboard/DashboardHeader';
import { Switch } from '@/components/ui/switch';

const SettingsPage = () => {
  const [darkMode, setDarkMode] = useState(true);
  const [tempUnit, setTempUnit] = useState('kelvin');
  const [distanceUnit, setDistanceUnit] = useState('km');

  return (
    <div className="flex h-screen bg-[#010816]">
      <Sidebar />
      <div className="flex-1 flex flex-col">
        <DashboardHeader />
        <div className="flex-1 overflow-auto p-6 space-y-6">
          {/* Display Settings */}
          <div className="bg-slate-900 rounded-lg shadow p-6 border border-slate-800">
            <div className="flex items-center gap-3 mb-6 pb-4 border-b border-slate-800">
              <Monitor className="w-5 h-5 text-cyan-400" />
              <h2 className="text-lg font-semibold text-slate-50">Display</h2>
            </div>
            <div className="space-y-4">
              <div className="flex items-center justify-between p-3 rounded-lg hover:bg-slate-800/50 transition-colors">
                <div>
                  <p className="font-medium text-slate-100">Dark Mode</p>
                  <p className="text-sm text-slate-400">Use dark theme (recommended)</p>
                </div>
                <Switch checked={darkMode} onChange={setDarkMode} />
              </div>
              <div className="flex items-center justify-between p-3 rounded-lg hover:bg-slate-800/50 transition-colors">
                <div>
                  <p className="font-medium text-slate-100">High Contrast</p>
                  <p className="text-sm text-slate-400">Increase visual contrast</p>
                </div>
                <Switch defaultChecked={false} />
              </div>
              <div className="flex items-center justify-between p-3 rounded-lg hover:bg-slate-800/50 transition-colors">
                <div>
                  <p className="font-medium text-slate-100">Animations</p>
                  <p className="text-sm text-slate-400">Enable UI animations</p>
                </div>
                <Switch defaultChecked={true} />
              </div>
            </div>
          </div>

          {/* Units & Measurements */}
          <div className="bg-slate-900 rounded-lg shadow p-6 border border-slate-800">
            <div className="flex items-center gap-3 mb-6 pb-4 border-b border-slate-800">
              <Thermometer className="w-5 h-5 text-cyan-400" />
              <h2 className="text-lg font-semibold text-slate-50">Units & Measurements</h2>
            </div>
            <div className="space-y-4">
              <div>
                <label className="text-sm font-medium text-slate-100">Temperature Unit</label>
                <p className="text-sm text-slate-400 mb-3">Brightness temperature display</p>
                <select
                  value={tempUnit}
                  onChange={(e) => setTempUnit(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-700 rounded-lg bg-slate-800 text-slate-100 focus:border-cyan-400 focus:outline-none transition-colors"
                >
                  <option value="kelvin">Kelvin (K)</option>
                  <option value="celsius">Celsius (°C)</option>
                </select>
              </div>
              <div>
                <label className="text-sm font-medium text-slate-100">Distance Unit</label>
                <p className="text-sm text-slate-400 mb-3">Radius and area measurements</p>
                <select
                  value={distanceUnit}
                  onChange={(e) => setDistanceUnit(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-700 rounded-lg bg-slate-800 text-slate-100 focus:border-cyan-400 focus:outline-none transition-colors"
                >
                  <option value="km">Kilometers</option>
                  <option value="miles">Miles</option>
                  <option value="nautical">Nautical Miles</option>
                </select>
              </div>
              <div>
                <label className="text-sm font-medium text-slate-100">Time Zone</label>
                <p className="text-sm text-slate-400 mb-3">Timestamp display format</p>
                <select className="w-full px-3 py-2 border border-slate-700 rounded-lg bg-slate-800 text-slate-100 focus:border-cyan-400 focus:outline-none transition-colors">
                  <option value="utc">UTC</option>
                  <option value="local">Local Time</option>
                </select>
              </div>
            </div>
          </div>

          {/* System Info */}
          <div className="bg-slate-900 rounded-lg shadow p-6 border border-slate-800">
            <div className="flex items-center gap-3 mb-6 pb-4 border-b border-slate-800">
              <Info className="w-5 h-5 text-cyan-400" />
              <h2 className="text-lg font-semibold text-slate-50">System Information</h2>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-6">
              <div className="p-3 bg-slate-800/50 rounded-lg border border-slate-700">
                <p className="text-sm text-slate-400">Version</p>
                <p className="font-semibold text-slate-100 mt-1">1.0.0</p>
              </div>
              <div className="p-3 bg-slate-800/50 rounded-lg border border-slate-700">
                <p className="text-sm text-slate-400">Build</p>
                <p className="font-semibold text-slate-100 mt-1">2024.01.15.001</p>
              </div>
              <div className="p-3 bg-slate-800/50 rounded-lg border border-slate-700">
                <p className="text-sm text-slate-400">Last Updated</p>
                <p className="font-semibold text-slate-100 mt-1">2024-01-15 14:30 UTC</p>
              </div>
              <div className="p-3 bg-slate-800/50 rounded-lg border border-slate-700">
                <p className="text-sm text-slate-400">API Status</p>
                <p className="font-semibold text-green-400 mt-1">Connected</p>
              </div>
              <div className="p-3 bg-slate-800/50 rounded-lg border border-slate-700">
                <p className="text-sm text-slate-400">Data Pipeline</p>
                <p className="font-semibold text-green-400 mt-1">Operational</p>
              </div>
            </div>
          </div>

          {/* Data & Storage */}
          <div className="bg-slate-900 rounded-lg shadow p-6 border border-slate-800">
            <div className="flex items-center gap-3 mb-6 pb-4 border-b border-slate-800">
              <Database className="w-5 h-5 text-cyan-400" />
              <h2 className="text-lg font-semibold text-slate-50">Data & Storage</h2>
            </div>
            <div className="space-y-4">
              {[
                { label: 'Cache Size', value: '2.4 GB' },
                { label: 'Stored Exports', value: '847.6 MB' },
                { label: 'Analysis History', value: '124 sessions' },
              ].map((item, i) => (
                <div key={i} className="flex justify-between p-2 rounded">
                  <span className="text-sm text-slate-400">{item.label}</span>
                  <span className="font-semibold text-slate-100">{item.value}</span>
                </div>
              ))}
              <div className="pt-4 border-t border-slate-700">
                <div className="flex justify-between mb-3">
                  <span className="text-sm font-medium text-slate-100">Storage Usage</span>
                  <span className="font-semibold text-slate-100">3.2 GB / 10 GB</span>
                </div>
                <div className="w-full h-2 bg-slate-700 rounded-full overflow-hidden border border-slate-600">
                  <div className="h-full bg-gradient-to-r from-cyan-500 to-cyan-400" style={{ width: '32%' }} />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SettingsPage;
