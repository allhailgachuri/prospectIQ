import type { LucideIcon } from 'lucide-react';

interface StatCardProps {
  label: string;
  value: number | string;
  icon: LucideIcon;
  color?: 'blue' | 'green' | 'amber' | 'red' | 'purple' | 'cyan';
  sub?: string;
}

const COLORS = {
  blue:   { bg: 'bg-blue-50',   icon: 'bg-blue-100 text-blue-600',   val: 'text-blue-700' },
  green:  { bg: 'bg-emerald-50',icon: 'bg-emerald-100 text-emerald-600', val: 'text-emerald-700' },
  amber:  { bg: 'bg-amber-50',  icon: 'bg-amber-100 text-amber-600', val: 'text-amber-700' },
  red:    { bg: 'bg-red-50',    icon: 'bg-red-100 text-red-600',     val: 'text-red-700' },
  purple: { bg: 'bg-purple-50', icon: 'bg-purple-100 text-purple-600', val: 'text-purple-700' },
  cyan:   { bg: 'bg-cyan-50',   icon: 'bg-cyan-100 text-cyan-600',   val: 'text-cyan-700' },
};

export function StatCard({ label, value, icon: Icon, color = 'blue', sub }: StatCardProps) {
  const c = COLORS[color];
  return (
    <div className={`${c.bg} rounded-2xl p-5 flex items-start gap-4`}>
      <div className={`${c.icon} w-10 h-10 rounded-xl flex items-center justify-center shrink-0`}>
        <Icon size={18} />
      </div>
      <div className="min-w-0">
        <p className="text-sm text-slate-500 font-medium truncate">{label}</p>
        <p className={`text-2xl font-bold ${c.val} mt-0.5`}>{value.toLocaleString()}</p>
        {sub && <p className="text-xs text-slate-400 mt-0.5">{sub}</p>}
      </div>
    </div>
  );
}
