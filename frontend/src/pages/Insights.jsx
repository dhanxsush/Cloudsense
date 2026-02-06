import { BarChart3, TrendingUp, TrendingDown, Minus } from 'lucide-react';
import Sidebar from '@/components/dashboard/Sidebar';
import DashboardHeader from '@/components/dashboard/DashboardHeader';

const btTimeSeriesData = [
  { time: '00:00', min: 205, max: 230, mean: 218 },
  { time: '02:00', min: 203, max: 228, mean: 215 },
  { time: '04:00', min: 200, max: 225, mean: 212 },
  { time: '06:00', min: 198, max: 223, mean: 210 },
  { time: '08:00', min: 196, max: 220, mean: 208 },
  { time: '10:00', min: 203, max: 227, mean: 215 },
  { time: '12:00', min: 206, max: 230, mean: 218 },
  { time: '14:00', min: 208, max: 232, mean: 220 },
  { time: '16:00', min: 205, max: 229, mean: 217 },
  { time: '18:00', min: 202, max: 226, mean: 214 },
  { time: '20:00', min: 198, max: 222, mean: 210 },
  { time: '22:00', min: 196, max: 220, mean: 208 },
];

const radiusDistribution = [
  { range: '0-50', count: 12 },
  { range: '50-100', count: 28 },
  { range: '100-150', count: 45 },
  { range: '150-200', count: 32 },
  { range: '200-250', count: 18 },
  { range: '250+', count: 8 },
];

const statistics = [
  { label: 'Min BT', value: '185.2', unit: 'K', trend: 'down', change: -2.3 },
  { label: 'Max BT', value: '248.7', unit: 'K', trend: 'up', change: 1.8 },
  { label: 'Mean BT', value: '215.4', unit: 'K', trend: 'stable', change: 0.1 },
  { label: 'Std Dev', value: '18.6', unit: 'K', trend: 'up', change: 3.2 },
  { label: 'Avg Radius', value: '124.5', unit: 'km', trend: 'up', change: 5.7 },
  { label: 'Max Radius', value: '287.3', unit: 'km', trend: 'down', change: -8.4 },
  { label: 'Total Area', value: '487,230', unit: 'km²', trend: 'up', change: 12.3 },
  { label: 'Cloud Top', value: '12.4', unit: 'km', trend: 'stable', change: 0.2 },
];

const Insights = () => {
  return (
    <div className="flex h-screen bg-[#010816]">
      <Sidebar />
      <div className="flex-1 flex flex-col">
        <DashboardHeader />
        <div className="flex-1 overflow-auto p-6 space-y-6">
          {/* Statistics Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {statistics.map((stat, index) => (
              <div key={index} className="bg-slate-900 rounded-lg shadow p-6 border border-slate-800">
                <p className="text-sm text-slate-400 mb-2">{stat.label}</p>
                <div className="flex items-baseline gap-2 mb-3">
                  <p className="text-2xl font-bold text-slate-100">{stat.value}</p>
                  <p className="text-sm text-slate-500">{stat.unit}</p>
                </div>
                <div className="flex items-center gap-2">
                  {stat.trend === 'up' && <TrendingUp className="w-4 h-4 text-green-400" />}
                  {stat.trend === 'down' && <TrendingDown className="w-4 h-4 text-red-400" />}
                  {stat.trend === 'stable' && <Minus className="w-4 h-4 text-slate-500" />}
                  <span className={`text-sm font-semibold ${
                    stat.trend === 'up' ? 'text-green-400' :
                    stat.trend === 'down' ? 'text-red-400' :
                    'text-slate-500'
                  }`}>
                    {stat.change > 0 ? '+' : ''}{stat.change}%
                  </span>
                </div>
              </div>
            ))}
          </div>

          {/* Charts */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* BT Time Series */}
            <div className="bg-slate-900 rounded-lg shadow p-6 border border-slate-800">
              <h3 className="text-lg font-semibold mb-4 text-slate-50">Brightness Temperature (24h)</h3>
              <div className="h-64 bg-slate-800 rounded flex items-center justify-center border border-slate-700">
                <p className="text-slate-500">Chart visualization</p>
              </div>
            </div>

            {/* Radius Distribution */}
            <div className="bg-slate-900 rounded-lg shadow p-6 border border-slate-800">
              <h3 className="text-lg font-semibold mb-4 text-slate-50">Radius Distribution (km)</h3>
              <div className="space-y-2">
                {radiusDistribution.map((item, i) => (
                  <div key={i} className="flex items-center gap-4">
                    <span className="text-sm w-16 text-slate-300">{item.range}</span>
                    <div className="flex-1 h-6 bg-slate-700 rounded overflow-hidden border border-slate-600">
                      <div
                        className="h-full bg-cyan-500"
                        style={{ width: `${(item.count / 45) * 100}%` }}
                      />
                    </div>
                    <span className="text-sm font-semibold w-8 text-right text-slate-300">{item.count}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Summary Panel */}
          <div className="bg-slate-900 rounded-lg shadow p-6 border border-slate-800">
            <h3 className="text-lg font-semibold mb-6 text-slate-50">Analysis Summary</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div>
                <p className="text-sm text-slate-400 mb-2">Observation Period</p>
                <p className="font-semibold text-slate-200">2024-01-15 00:00 - 23:30 UTC</p>
                <p className="text-sm text-slate-500">48 half-hourly observations</p>
              </div>
              <div>
                <p className="text-sm text-slate-400 mb-2">Coverage Area</p>
                <p className="font-semibold text-slate-200">30°N - 30°S, 60°E - 180°E</p>
                <p className="text-sm text-slate-500">Indo-Pacific tropical region</p>
              </div>
              <div>
                <p className="text-sm text-slate-400 mb-2">Data Quality</p>
                <p className="font-semibold text-slate-200">98.7% valid pixels</p>
                <p className="text-sm text-slate-500">1.3% flagged/invalid</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Insights;
