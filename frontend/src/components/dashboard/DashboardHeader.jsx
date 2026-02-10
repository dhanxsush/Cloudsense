import { Search } from 'lucide-react';
import { Input } from '@/components/ui/input';

const DashboardHeader = ({ title, subtitle }) => {
  return (
    <header className="bg-slate-900 border-b border-slate-800 px-6 py-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-50">{title}</h1>
          {subtitle && <p className="text-sm text-slate-400">{subtitle}</p>}
        </div>
        <div className="flex items-center gap-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
            <Input placeholder="Search..." className="pl-10 w-64 bg-slate-800 border-slate-700 text-slate-100 placeholder-slate-500" />
          </div>
        </div>
      </div>
    </header>
  );
};

export default DashboardHeader;
