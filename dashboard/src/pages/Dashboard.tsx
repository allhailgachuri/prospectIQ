import { useQuery } from "@tanstack/react-query";
import {
  Building2,
  Globe2,
  Phone,
  Mail,
  ArrowUpRight,
  MapPinned,
  Zap,
} from "lucide-react";
import { Link } from "react-router-dom";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { fetchStats } from "../api";

const CHART_COLORS = [
  "#1765cf",
  "#27a99b",
  "#e7a544",
  "#e06459",
  "#66869e",
  "#87b9d1",
];
const number = (value: number) => value.toLocaleString();

function ChartTip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: Array<{ value: number; name: string; color: string }>;
  label?: string;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="chart-tooltip">
      <strong>{label ?? payload[0].name}</strong>
      {payload.map((item) => (
        <div key={item.name} style={{ color: item.color }}>
          {item.name}: {number(item.value)}
        </div>
      ))}
    </div>
  );
}

export function Dashboard() {
  const {
    data: stats,
    isLoading,
    isError,
    error,
  } = useQuery({ queryKey: ["stats"], queryFn: fetchStats });

  if (isLoading)
    return (
      <div className="py-20 text-center text-slate-400">
        Loading workspace overview...
      </div>
    );
  if (isError || !stats)
    return (
      <div className="py-20 text-center text-slate-500">
        {error instanceof Error
          ? error.message
          : "Dashboard data is unavailable. Check that the ProspectIQ API is running."}
      </div>
    );

  const verified =
    stats.website_statuses?.find(
      (item) => item.website_status === "VERIFIED_WEBSITE",
    )?.n ?? 0;
  const statusData = [
    { name: "Verified website", value: verified },
    {
      name: "Needs review",
      value:
        stats.website_statuses?.find(
          (item) => item.website_status === "WEBSITE_REQUIRES_MANUAL_REVIEW",
        )?.n ?? 0,
    },
    {
      name: "Unreachable",
      value:
        stats.website_statuses?.find(
          (item) => item.website_status === "WEBSITE_UNREACHABLE",
        )?.n ?? 0,
    },
    {
      name: "Not found",
      value:
        stats.website_statuses?.find(
          (item) => item.website_status === "WEBSITE_NOT_FOUND_AFTER_CHECKS",
        )?.n ?? 0,
    },
    {
      name: "Not checked",
      value: Math.max(0, stats.total - stats.total_checked),
    },
  ].filter((item) => item.value > 0);
  const categories = stats.by_category.slice(0, 7);
  const topAreas = stats.by_neighbourhood.slice(0, 8);
  const coverage = stats.total
    ? Math.round((stats.total_checked / stats.total) * 100)
    : 0;
  const kpis = [
    {
      label: "Businesses discovered",
      value: stats.total,
      note: "Across saved research areas",
      icon: Building2,
      className: "kpi-blue",
    },
    {
      label: "Website checks",
      value: stats.total_checked,
      note: `${coverage}% of records checked`,
      icon: Globe2,
      className: "kpi-mint",
    },
    {
      label: "Public phone contacts",
      value: stats.with_phone,
      note: `${stats.with_email.toLocaleString()} with email`,
      icon: Phone,
      className: "kpi-pale",
    },
    {
      label: "Verified websites",
      value: verified,
      note: `${Math.max(0, stats.total - stats.with_website).toLocaleString()} not listed in OSM`,
      icon: Mail,
      className: "kpi-cyan",
    },
  ];

  return (
    <div className="page-stack">
      <header className="page-heading">
        <div>
          <p className="eyebrow">Prospect intelligence / Kenya</p>
          <h1>Dashboard</h1>
          <p>Business discovery and digital opportunity overview.</p>
        </div>
        <div className="quick-actions">
          <Link to="/analytics" className="action-button action-soft">
            <ArrowUpRight size={15} /> Full analytics
          </Link>
          <Link to="/pipeline" className="action-button action-primary">
            <Zap size={14} /> Run pipeline
          </Link>
        </div>
      </header>

      <section className="dashboard-kpis" aria-label="Prospect metrics">
        {kpis.map(({ label, value, note, icon: Icon, className }) => (
          <article key={label} className={`dashboard-kpi ${className}`}>
            <div className="kpi-label">
              <Icon size={15} /> {label}
            </div>
            <div className="kpi-value">{number(value)}</div>
            <div className="kpi-foot">{note}</div>
          </article>
        ))}
      </section>

      <section className="dashboard-grid">
        <article className="panel chart-panel">
          <div className="panel-heading">
            <div>
              <h2>Prospect landscape</h2>
              <p>Businesses found by mapped category</p>
            </div>
            <Link to="/prospects" className="text-link">
              Browse all <ArrowUpRight size={13} />
            </Link>
          </div>
          <div className="chart-wrap">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={categories}
                margin={{ top: 8, right: 12, bottom: 4, left: -18 }}
              >
                <CartesianGrid
                  vertical={false}
                  stroke="var(--line)"
                  strokeDasharray="3 4"
                />
                <XAxis
                  dataKey="category"
                  tick={{ fill: "var(--muted)", fontSize: 10 }}
                  axisLine={false}
                  tickLine={false}
                  tickMargin={10}
                />
                <YAxis
                  tick={{ fill: "var(--muted)", fontSize: 10 }}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip
                  content={<ChartTip />}
                  cursor={{ fill: "rgba(80,140,180,.08)" }}
                />
                <Bar
                  dataKey="n"
                  name="Businesses"
                  fill="#1765cf"
                  radius={[5, 5, 0, 0]}
                  maxBarSize={38}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </article>

        <article className="panel chart-panel">
          <div className="panel-heading">
            <div>
              <h2>Website coverage</h2>
              <p>Verification status across the database</p>
            </div>
          </div>
          <div className="chart-wrap compact">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={statusData}
                  dataKey="value"
                  nameKey="name"
                  innerRadius="58%"
                  outerRadius="82%"
                  paddingAngle={3}
                  stroke="none"
                >
                  {statusData.map((item, index) => (
                    <Cell
                      key={item.name}
                      fill={CHART_COLORS[index % CHART_COLORS.length]}
                    />
                  ))}
                </Pie>
                <Tooltip content={<ChartTip />} />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="chart-legend">
            {statusData.slice(0, 4).map((item, index) => (
              <div className="legend-row" key={item.name}>
                <span
                  className="legend-dot"
                  style={{ background: CHART_COLORS[index] }}
                />
                {item.name}
                <strong>{number(item.value)}</strong>
              </div>
            ))}
          </div>
        </article>
      </section>

      <section className="dashboard-grid">
        <article className="panel chart-panel">
          <div className="panel-heading">
            <div>
              <h2>Mapped business activity</h2>
              <p>Top neighbourhoods in the current dataset</p>
            </div>
            <MapPinned size={17} color="var(--blue)" />
          </div>
          <div className="chart-wrap compact">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart
                data={topAreas}
                margin={{ top: 8, right: 12, bottom: 4, left: -18 }}
              >
                <defs>
                  <linearGradient id="areaFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#27a99b" stopOpacity={0.36} />
                    <stop
                      offset="100%"
                      stopColor="#27a99b"
                      stopOpacity={0.02}
                    />
                  </linearGradient>
                </defs>
                <CartesianGrid
                  vertical={false}
                  stroke="var(--line)"
                  strokeDasharray="3 4"
                />
                <XAxis
                  dataKey="neighbourhood"
                  tick={{ fill: "var(--muted)", fontSize: 10 }}
                  axisLine={false}
                  tickLine={false}
                  tickMargin={10}
                />
                <YAxis
                  tick={{ fill: "var(--muted)", fontSize: 10 }}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip content={<ChartTip />} />
                <Area
                  type="monotone"
                  dataKey="n"
                  name="Businesses"
                  stroke="#218f86"
                  strokeWidth={2.5}
                  fill="url(#areaFill)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </article>
        <article className="panel chart-panel">
          <div className="panel-heading">
            <div>
              <h2>Start with a workflow</h2>
              <p>Move from discovery to client-ready deliverables</p>
            </div>
          </div>
          <div className="quick-actions">
            <Link to="/prospects" className="action-button action-soft">
              <Building2 size={15} /> Open prospects
            </Link>
            <Link to="/pipeline" className="action-button action-primary">
              <Zap size={14} /> Discover businesses
            </Link>
            <Link to="/reports" className="action-button action-soft">
              <ArrowUpRight size={15} /> View reports
            </Link>
          </div>
          <div className="mt-6 text-sm text-slate-500">
            Source coverage varies by location. OSM's missing website tag is not
            proof that a business has no website.
          </div>
        </article>
      </section>

      <section className="panel chart-panel">
        <div className="panel-heading">
          <div>
            <h2>Top categories</h2>
            <p>Jump directly into a business segment</p>
          </div>
        </div>
        <div className="category-strip">
          {categories.slice(0, 4).map((row) => (
            <Link
              key={row.category}
              to={`/prospects?category=${encodeURIComponent(row.category)}`}
              className="category-chip"
            >
              <strong>{number(row.n)}</strong>
              <span>{row.category}</span>
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}
