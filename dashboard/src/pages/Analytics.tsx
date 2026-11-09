import { useQuery } from "@tanstack/react-query";
import { BarChart3, PieChart as PieIcon, MapPin, Activity } from "lucide-react";
import {
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

const COLORS = [
  "#1765cf",
  "#27a99b",
  "#e7a544",
  "#e06459",
  "#66869e",
  "#87b9d1",
  "#9378c5",
];

export function Analytics() {
  const {
    data: stats,
    isLoading,
    isError,
  } = useQuery({ queryKey: ["stats"], queryFn: fetchStats });
  if (isLoading)
    return (
      <div className="py-20 text-center text-slate-400">
        Loading analytics...
      </div>
    );
  if (isError || !stats)
    return (
      <div className="py-20 text-center text-slate-500">
        Analytics data is unavailable.
      </div>
    );

  const websiteData = (stats.website_statuses ?? []).map((row) => ({
    name: row.website_status
      .replace(/^WEBSITE_/, "")
      .replace(/_/g, " ")
      .toLowerCase(),
    value: row.n,
  }));
  const auditData = (stats.audit_labels ?? []).map((row) => ({
    name: row.audit_quality_label,
    value: row.n,
  }));
  const totals = [
    { label: "Businesses discovered", value: stats.total },
    { label: "Website listed", value: stats.with_website },
    { label: "With phone", value: stats.with_phone },
    { label: "With email", value: stats.with_email },
  ];

  return (
    <div className="page-stack">
      <header className="page-heading">
        <div>
          <p className="eyebrow">Research performance</p>
          <h1>Analytics</h1>
          <p>
            Coverage and opportunity signals across{" "}
            {stats.total.toLocaleString()} mapped businesses.
          </p>
        </div>
      </header>

      <section className="dashboard-kpis" aria-label="Database totals">
        {totals.map((item, index) => (
          <article
            key={item.label}
            className={`dashboard-kpi ${["kpi-blue", "kpi-mint", "kpi-pale", "kpi-cyan"][index]}`}
          >
            <div className="kpi-label">{item.label}</div>
            <div className="kpi-value">{item.value.toLocaleString()}</div>
            <div className="kpi-foot">
              {stats.total ? Math.round((item.value / stats.total) * 100) : 0}%
              of saved records
            </div>
          </article>
        ))}
      </section>

      <section className="dashboard-grid">
        <article className="panel chart-panel">
          <div className="panel-heading">
            <div>
              <h2>
                <BarChart3 size={15} className="inline mr-2" />
                Business segments
              </h2>
              <p>Most represented OSM business categories</p>
            </div>
          </div>
          <div className="chart-wrap">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={stats.by_category.slice(0, 10)}
                layout="vertical"
                margin={{ top: 4, right: 12, bottom: 4, left: 18 }}
              >
                <CartesianGrid
                  horizontal={false}
                  stroke="var(--line)"
                  strokeDasharray="3 4"
                />
                <XAxis
                  type="number"
                  tick={{ fill: "var(--muted)", fontSize: 10 }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  type="category"
                  dataKey="category"
                  width={105}
                  tick={{ fill: "var(--muted)", fontSize: 10 }}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip
                  formatter={(value) => [
                    Number(value).toLocaleString(),
                    "Businesses",
                  ]}
                />
                <Bar
                  dataKey="n"
                  name="Businesses"
                  fill="#1765cf"
                  radius={[0, 5, 5, 0]}
                  maxBarSize={20}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </article>

        <article className="panel chart-panel">
          <div className="panel-heading">
            <div>
              <h2>
                <PieIcon size={15} className="inline mr-2" />
                Website status
              </h2>
              <p>Verification coverage, not just OSM tags</p>
            </div>
          </div>
          <div className="chart-wrap compact">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={websiteData}
                  dataKey="value"
                  nameKey="name"
                  innerRadius="54%"
                  outerRadius="79%"
                  paddingAngle={3}
                  stroke="none"
                >
                  {websiteData.map((item, index) => (
                    <Cell
                      key={item.name}
                      fill={COLORS[index % COLORS.length]}
                    />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="chart-legend">
            {websiteData.map((item, index) => (
              <div key={item.name} className="legend-row">
                <span
                  className="legend-dot"
                  style={{ background: COLORS[index % COLORS.length] }}
                />
                {item.name}
                <strong>{item.value.toLocaleString()}</strong>
              </div>
            ))}
          </div>
        </article>
      </section>

      <section className="dashboard-grid">
        <article className="panel chart-panel">
          <div className="panel-heading">
            <div>
              <h2>
                <MapPin size={15} className="inline mr-2" />
                Top neighbourhoods
              </h2>
              <p>Geographic concentration of saved businesses</p>
            </div>
          </div>
          <div className="chart-wrap">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={stats.by_neighbourhood.slice(0, 10)}
                margin={{ top: 8, right: 12, bottom: 4, left: -18 }}
              >
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
                <Tooltip
                  formatter={(value) => [
                    Number(value).toLocaleString(),
                    "Businesses",
                  ]}
                />
                <Bar
                  dataKey="n"
                  name="Businesses"
                  fill="#27a99b"
                  radius={[5, 5, 0, 0]}
                  maxBarSize={32}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </article>

        <article className="panel chart-panel">
          <div className="panel-heading">
            <div>
              <h2>
                <Activity size={15} className="inline mr-2" />
                Website audit quality
              </h2>
              <p>Quality labels from completed website checks</p>
            </div>
          </div>
          {auditData.length ? (
            <div className="chart-wrap compact">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={auditData}
                    dataKey="value"
                    nameKey="name"
                    innerRadius="56%"
                    outerRadius="80%"
                    paddingAngle={4}
                    stroke="none"
                  >
                    {auditData.map((item, index) => (
                      <Cell
                        key={item.name}
                        fill={COLORS[index % COLORS.length]}
                      />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="py-16 text-center text-sm text-slate-500">
              Website checks have not produced audit labels yet.
            </div>
          )}
          <div className="chart-legend">
            {auditData.map((item, index) => (
              <div key={item.name} className="legend-row">
                <span
                  className="legend-dot"
                  style={{ background: COLORS[index % COLORS.length] }}
                />
                {item.name}
                <strong>{item.value.toLocaleString()}</strong>
              </div>
            ))}
          </div>
        </article>
      </section>
    </div>
  );
}
