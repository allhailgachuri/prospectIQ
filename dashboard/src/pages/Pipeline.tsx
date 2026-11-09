import { useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import {
  Zap,
  Globe,
  FileText,
  CheckCircle,
  AlertCircle,
  Loader2,
  Search,
  Download,
} from "lucide-react";
import {
  startCheckJob,
  startDiscoveryJob,
  startReportJob,
  fetchJobStatus,
  reportUrl,
} from "../api";
import type { Job } from "../types";

interface JobState {
  id: string;
  type: "discover" | "check" | "report";
  job: Job;
}
const AREAS: Record<string, string> = {
  Nairobi: "-1.45,36.65,-1.15,37.10",
  Mombasa: "-4.15,39.55,-3.95,39.75",
  Kisumu: "-0.15,34.65,0.15,34.85",
  Kampala: "0.25,32.45,0.42,32.65",
  "Dar es Salaam": "-6.95,39.15,-6.65,39.35",
};

function JobCard({ state }: { state: JobState }) {
  const pct = state.job.total
    ? Math.round((state.job.done / state.job.total) * 100)
    : 0;
  const isRunning = state.job.status === "running";
  const isDone = state.job.status === "done";
  const isError = state.job.status === "error";
  const labels = {
    discover: "Business discovery",
    check: "Website checks",
    report: "Report generation",
  };

  return (
    <div
      className={`border rounded-xl p-5 ${isDone ? "border-emerald-200 bg-emerald-50" : isError ? "border-red-200 bg-red-50" : "border-blue-200 bg-blue-50"}`}
    >
      <div className="flex items-center justify-between mb-3">
        <span className="font-medium text-sm">{labels[state.type]}</span>
        <div className="flex items-center gap-2 text-sm">
          {isRunning && (
            <Loader2 size={14} className="animate-spin text-blue-600" />
          )}
          {isDone && <CheckCircle size={14} className="text-emerald-600" />}
          {isError && <AlertCircle size={14} className="text-red-600" />}
          <span>{state.job.status}</span>
        </div>
      </div>
      {state.job.total > 0 && (
        <>
          <div className="flex justify-between text-xs text-slate-500 mb-1">
            <span>
              {state.job.done} / {state.job.total}
            </span>
            <span>{pct}%</span>
          </div>
          <div className="h-2 bg-white rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all ${isDone ? "bg-emerald-500" : "bg-blue-500"}`}
              style={{ width: `${pct}%` }}
            />
          </div>
        </>
      )}
      {isDone && state.type === "discover" && (
        <p className="text-sm text-emerald-800 mt-3">
          {state.job.records ?? 0} records added or updated.
        </p>
      )}
      {isDone && state.type === "report" && (
        <div className="flex flex-wrap gap-2 mt-3">
          <a
            href={reportUrl("/reports/latest")}
            className="action-button action-primary"
          >
            <FileText size={14} /> Word report
          </a>
          <a
            href={reportUrl("/reports/latest/excel")}
            className="action-button action-soft"
          >
            <Download size={14} /> Excel outreach
          </a>
        </div>
      )}
      {isError && (
        <p className="mt-2 text-xs text-red-700">{state.job.error}</p>
      )}
    </div>
  );
}

export function Pipeline() {
  const qc = useQueryClient();
  const [checkLimit, setCheckLimit] = useState(100);
  const [reportLimit, setReportLimit] = useState(50);
  const [selectedArea, setSelectedArea] = useState("Nairobi");
  const [bbox, setBbox] = useState(AREAS.Nairobi);
  const [jobs, setJobs] = useState<JobState[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    const running = jobs.filter((job) => job.job.status === "running");
    if (!running.length) return;
    const timer = setInterval(async () => {
      try {
        const updates = await Promise.all(
          running.map(async (job) => ({
            ...job,
            job: await fetchJobStatus(job.id),
          })),
        );
        setJobs((previous) =>
          previous.map(
            (job) => updates.find((update) => update.id === job.id) ?? job,
          ),
        );
        if (updates.some((update) => update.job.status === "done")) {
          qc.invalidateQueries({ queryKey: ["stats"] });
          qc.invalidateQueries({ queryKey: ["businesses"] });
          qc.invalidateQueries({ queryKey: ["reports"] });
        }
      } catch {
        setError(
          "A job status check failed. The task may still be running; refresh later to verify.",
        );
      }
    }, 2000);
    return () => clearInterval(timer);
  }, [jobs, qc]);

  const start = async (
    type: JobState["type"],
    action: () => Promise<{ job_id: string }>,
  ) => {
    setError("");
    try {
      const { job_id } = await action();
      setJobs((previous) => [
        ...previous,
        { id: job_id, type, job: { status: "running", done: 0, total: 0 } },
      ]);
    } catch (reason) {
      setError(
        reason instanceof Error ? reason.message : "Unable to start the task.",
      );
    }
  };

  return (
    <div className="page-stack">
      <header className="page-heading">
        <div>
          <p className="eyebrow">Research operations</p>
          <h1>Run Pipeline</h1>
          <p>
            Discover businesses, check websites, then prepare client-ready
            reports.
          </p>
        </div>
      </header>

      <section className="settings-section">
        <div className="settings-icon">
          <Search size={18} />
        </div>
        <div className="settings-copy">
          <h2>Discover businesses by area</h2>
          <p>
            Search OpenStreetMap's public data for named businesses. Coverage
            depends on community mapping and is not exhaustive. For larger
            regions, run smaller areas one at a time.
          </p>
        </div>
      </section>
      <section className="panel chart-panel space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <label className="text-xs font-semibold text-slate-600">
            Area preset
            <select
              value={selectedArea}
              onChange={(event) => {
                setSelectedArea(event.target.value);
                if (event.target.value !== "Custom")
                  setBbox(AREAS[event.target.value]);
              }}
              className="mt-2 block w-full border border-slate-200 rounded-lg px-3 py-2.5 text-sm font-normal"
            >
              {[...Object.keys(AREAS), "Custom"].map((area) => (
                <option key={area}>{area}</option>
              ))}
            </select>
          </label>
          <label className="text-xs font-semibold text-slate-600">
            Bounding box (south, west, north, east)
            <input
              value={bbox}
              onChange={(event) => {
                setSelectedArea("Custom");
                setBbox(event.target.value);
              }}
              placeholder="-1.30,36.75,-1.25,36.90"
              className="mt-2 block w-full border border-slate-200 rounded-lg px-3 py-2.5 text-sm font-normal"
            />
          </label>
        </div>
        <div className="text-xs text-slate-500 bg-slate-50 border border-slate-200 rounded-lg px-4 py-3">
          Each discovery request is limited to 0.5 degrees per side and 0.15
          square degrees overall to protect the public source. Use smaller
          mapped areas for consistent results.
        </div>
        <button
          type="button"
          onClick={() => start("discover", () => startDiscoveryJob(bbox))}
          className="action-button action-primary"
        >
          <Search size={14} /> Discover this area
        </button>
      </section>

      <section className="panel chart-panel space-y-4">
        <div className="flex items-center gap-3">
          <div className="settings-icon">
            <Globe size={18} />
          </div>
          <div>
            <h2 className="font-semibold text-sm text-slate-800">
              Check websites
            </h2>
            <p className="text-xs text-slate-500 mt-1">
              Verify listed websites and run lightweight quality audits.
            </p>
          </div>
        </div>
        <label className="text-xs text-slate-600 flex items-center gap-3">
          Businesses to check
          <input
            type="number"
            min={1}
            max={500}
            value={checkLimit}
            onChange={(event) => setCheckLimit(Number(event.target.value))}
            className="w-24 border border-slate-200 rounded-lg px-3 py-2 text-sm"
          />
        </label>
        <p className="text-xs text-slate-500">
          Checks make a single request to each business website. Only use this
          for public sites, and allow time for the queue to complete.
        </p>
        <button
          type="button"
          onClick={() => start("check", () => startCheckJob(checkLimit))}
          className="action-button action-primary"
        >
          <Zap size={14} /> Start website checks
        </button>
      </section>

      <section className="panel chart-panel space-y-4">
        <div className="flex items-center gap-3">
          <div className="settings-icon">
            <FileText size={18} />
          </div>
          <div>
            <h2 className="font-semibold text-sm text-slate-800">
              Generate reports
            </h2>
            <p className="text-xs text-slate-500 mt-1">
              Create the detailed Word report and a concise Excel outreach
              sheet.
            </p>
          </div>
        </div>
        <label className="text-xs text-slate-600 flex items-center gap-3">
          Prospects to include
          <input
            type="number"
            min={1}
            max={200}
            value={reportLimit}
            onChange={(event) => setReportLimit(Number(event.target.value))}
            className="w-24 border border-slate-200 rounded-lg px-3 py-2 text-sm"
          />
        </label>
        <p className="text-xs text-slate-500">
          The Word file contains the full prospect research and outreach
          details. The Excel file contains only name, phone, WhatsApp, email,
          opportunity, and brief solution.
        </p>
        <button
          type="button"
          onClick={() => start("report", () => startReportJob(reportLimit))}
          className="action-button action-primary"
        >
          <FileText size={14} /> Generate both reports
        </button>
      </section>

      {error && (
        <div
          role="alert"
          className="border border-red-200 bg-red-50 text-red-800 rounded-lg px-4 py-3 text-sm"
        >
          {error}
        </div>
      )}
      {jobs.length > 0 && (
        <section className="space-y-3">
          <h2 className="font-semibold text-slate-700">Recent jobs</h2>
          {[...jobs].reverse().map((job) => (
            <JobCard key={job.id} state={job} />
          ))}
        </section>
      )}
    </div>
  );
}
