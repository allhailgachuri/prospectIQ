import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  Users,
  Globe,
  BarChart2,
  FileText,
  Settings,
  Zap,
  ExternalLink,
  Moon,
  Sun,
} from "lucide-react";

const NAV = [
  { to: "/", icon: LayoutDashboard, label: "Dashboard" },
  { to: "/prospects", icon: Users, label: "Prospects" },
  { to: "/websites", icon: Globe, label: "Website Intelligence" },
  { to: "/analytics", icon: BarChart2, label: "Analytics" },
  { to: "/reports", icon: FileText, label: "Reports" },
  { to: "/pipeline", icon: Zap, label: "Run Pipeline" },
  { to: "/settings", icon: Settings, label: "Settings" },
];

export function Sidebar({
  theme,
  onToggleTheme,
}: {
  theme: "light" | "dark";
  onToggleTheme: () => void;
}) {
  return (
    <aside className="app-sidebar w-64 min-h-screen text-white flex flex-col shrink-0">
      {/* Logo */}
      <div className="px-6 py-5 border-b border-white/10">
        <div className="flex items-center gap-3">
          <div className="brand-mark w-8 h-8 rounded-lg flex items-center justify-center font-bold text-sm">
            P
          </div>
          <div>
            <div className="font-semibold text-sm leading-none">ProspectIQ</div>
            <div className="text-xs sidebar-muted mt-0.5">
              Business Intelligence
            </div>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-0.5">
        {NAV.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/"}
            className={({ isActive }) =>
              `sidebar-link flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors
               ${
                 isActive
                   ? "active text-white font-medium"
                   : "text-slate-400 hover:text-white hover:bg-white/5"
               }`
            }
          >
            <Icon size={16} />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* Agency link */}
      <div className="px-4 py-4 border-t border-white/10">
        <button
          type="button"
          onClick={onToggleTheme}
          className="theme-toggle flex items-center gap-2 w-full text-xs text-slate-400 hover:text-white transition-colors mb-4"
        >
          {theme === "dark" ? <Sun size={14} /> : <Moon size={14} />}
          {theme === "dark" ? "Light appearance" : "Dark appearance"}
        </button>
        <a
          href="https://builtbyrushion.vercel.app/"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-2 text-xs text-slate-400 hover:text-white transition-colors"
        >
          <ExternalLink size={12} />
          BuiltByRushion
        </a>
        <p className="text-xs text-slate-600 mt-1">v0.2.0</p>
      </div>
    </aside>
  );
}
