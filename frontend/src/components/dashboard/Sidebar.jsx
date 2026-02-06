import { Link, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  Upload,
  Activity,
  Radar,
  BarChart3,
  Download,
  Settings,
  Satellite,
  ChevronLeft,
  ChevronRight
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { useState } from 'react';

const menuItems = [
  { icon: LayoutDashboard, label: 'Dashboard', path: '/dashboard' },
  { icon: Upload, label: 'Data Upload', path: '/dashboard/upload' },
  { icon: Activity, label: 'Analysis', path: '/analysis' },
  { icon: Radar, label: 'Tracking', path: '/tracking' },
  { icon: BarChart3, label: 'Insights', path: '/insights' },
  { icon: Download, label: 'Exports', path: '/exports' },
  { icon: Settings, label: 'Settings', path: '/settings' },
];

const Sidebar = () => {
  const location = useLocation();
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div className={cn(
      "bg-slate-900 border-r border-slate-800 h-screen flex flex-col transition-all duration-300",
      collapsed ? "w-20" : "w-64"
    )}>
      {/* Logo Area - Maintain spacing */}
      <div className="p-6 border-b border-slate-800">
        {/* Branding is in Navbar - sidebar acts as pure navigation */}
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto p-4 space-y-2">
        {menuItems.map((item) => {
          const Icon = item.icon;
          const isActive = location.pathname === item.path ||
            (item.path !== '/dashboard' && location.pathname.startsWith(item.path));
          return (
            <Link
              key={item.path}
              to={item.path}
              className={cn(
                "flex items-center gap-3 px-4 py-2 rounded-lg transition-colors",
                isActive
                  ? "bg-cyan-600 text-white"
                  : "text-slate-300 hover:bg-slate-800"
              )}
            >
              <Icon className="w-5 h-5 flex-shrink-0" />
              {!collapsed && <span>{item.label}</span>}
            </Link>
          );
        })}
      </nav>

      {/* Status */}
      <div className="p-4 border-t border-slate-800">
        {!collapsed && (
          <div className="flex items-center gap-2 text-sm">
            <div className="w-2 h-2 rounded-full bg-green-500" />
            <span className="text-slate-400">System Operational</span>
          </div>
        )}
      </div>

      {/* Collapse toggle */}
      <Button
        variant="ghost"
        size="icon"
        onClick={() => setCollapsed(!collapsed)}
        className="absolute -right-3 top-20 h-6 w-6 rounded-full border border-slate-700 bg-slate-800 shadow-lg hover:bg-slate-700"
      >
        {collapsed ? (
          <ChevronRight className="w-4 h-4" />
        ) : (
          <ChevronLeft className="w-4 h-4" />
        )}
      </Button>
    </div>
  );
};

export default Sidebar;
