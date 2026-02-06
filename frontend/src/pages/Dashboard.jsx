import { Cloud, Thermometer, Circle, Clock } from 'lucide-react';
import Sidebar from '@/components/dashboard/Sidebar';
import DashboardHeader from '@/components/dashboard/DashboardHeader';
import KPICard from '@/components/dashboard/KPICard';
import WorldMap from '@/components/dashboard/WorldMap';
import TimelineSlider from '@/components/dashboard/TimelineSlider';
import ClusterTable from '@/components/dashboard/ClusterTable';

const Dashboard = () => {
  return (
    <div className="flex h-screen bg-[#010816]">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <DashboardHeader title="TCC Cluster Analysis Dashboard" subtitle="Real-time Tropical Cloud Cluster Detection & Tracking" />
        <div className="flex-1 overflow-auto p-6 space-y-6">
          {/* KPI Cards - TCC Metrics */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <KPICard 
              icon={Circle} 
              label="Active TCCs" 
              value="47" 
              unit="clusters"
              trend="+12%" 
            />
            <KPICard 
              icon={Thermometer} 
              label="Min Brightness Temp" 
              value="185.2" 
              unit="K"
              trend="-2%" 
            />
            <KPICard 
              icon={Cloud} 
              label="Avg Cloud-Top Height" 
              value="12.4" 
              unit="km"
              trend="+8%" 
            />
            <KPICard 
              icon={Clock} 
              label="Mean TCC Radius" 
              value="124.5" 
              unit="km"
              trend="-5%" 
            />
          </div>

          {/* Map and Timeline */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 bg-slate-900 rounded-lg p-4 border border-slate-800">
              <WorldMap />
            </div>
            <div className="bg-slate-900 rounded-lg p-4 border border-slate-800">
              <TimelineSlider />
            </div>
          </div>

          {/* Detected TCC Clusters Table */}
          <div className="bg-slate-900 rounded-lg p-4 border border-slate-800">
            <h2 className="text-lg font-semibold text-slate-100 mb-4">Detected TCC Clusters</h2>
            <ClusterTable />
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
