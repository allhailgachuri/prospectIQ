import { useQuery } from "@tanstack/react-query";
import { FileText, Download, Plus, Table2 } from "lucide-react";
import { Link } from "react-router-dom";
import { fetchReports, reportUrl } from "../api";

export function Reports() {
  const { data: reports, isLoading } = useQuery({
    queryKey: ["reports"],
    queryFn: fetchReports,
    refetchInterval: 10000,
  });

  const fmt = (ts: number) =>
    new Date(ts * 1000).toLocaleDateString("en-KE", {
      day: "numeric",
      month: "long",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });

  return (
    <div className="space-y-6 max-w-3xl">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Reports</h1>
          <p className="text-sm text-slate-500 mt-1">
            Detailed Word research and concise Excel outreach lists
          </p>
        </div>
        <Link
          to="/pipeline"
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-sm font-medium transition-colors"
        >
          <Plus size={15} /> New Report
        </Link>
      </div>

      {isLoading ? (
        <div className="text-slate-400 py-8 text-center">
          Loading reports...
        </div>
      ) : !reports || reports.length === 0 ? (
        <div className="bg-slate-50 border border-slate-200 rounded-2xl p-12 text-center">
          <FileText size={32} className="mx-auto text-slate-300 mb-3" />
          <p className="font-medium text-slate-600">No reports yet</p>
          <p className="text-sm text-slate-400 mt-1">
            Run the pipeline to generate your first prospect report
          </p>
          <Link
            to="/pipeline"
            className="mt-4 inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-xl text-sm font-medium"
          >
            <Plus size={14} /> Go to Pipeline
          </Link>
        </div>
      ) : (
        <div className="space-y-3">
          {reports.map((r, i) => (
            <div
              key={r.name}
              className="bg-white border border-slate-200 hover:border-blue-300 rounded-2xl p-5 flex items-center justify-between gap-4 transition-all"
            >
              <div className="flex items-center gap-4">
                <div className="w-10 h-10 bg-blue-100 text-blue-600 rounded-xl flex items-center justify-center shrink-0">
                  {r.name.toLowerCase().endsWith(".xlsx") ? (
                    <Table2 size={18} />
                  ) : (
                    <FileText size={18} />
                  )}
                </div>
                <div>
                  <p className="font-medium text-slate-800">{r.name}</p>
                  <p className="text-xs text-slate-400 mt-0.5">
                    {r.size_kb} KB · {fmt(r.created)}
                    {i === 0 && (
                      <span className="ml-2 bg-emerald-100 text-emerald-700 text-xs px-2 py-0.5 rounded-full">
                        Latest
                      </span>
                    )}
                  </p>
                </div>
              </div>
              <a
                href={reportUrl(`/reports/file/${encodeURIComponent(r.name)}`)}
                className="flex items-center gap-2 px-4 py-2 bg-slate-100 hover:bg-blue-50 text-slate-700 hover:text-blue-700 rounded-xl text-sm font-medium transition-colors"
              >
                <Download size={14} /> Download
              </a>
            </div>
          ))}
        </div>
      )}

      <div className="bg-blue-50 border border-blue-200 rounded-xl px-5 py-4 text-sm text-blue-800">
        <strong>Reports contain researched business data.</strong> The Word
        report includes: business profile, website audit, personalised outreach
        (WhatsApp, email, call script), lead score, and your agency link:{" "}
        <a
          href="https://builtbyrushion.vercel.app/"
          target="_blank"
          rel="noopener noreferrer"
          className="underline font-medium"
        >
          builtbyrushion.vercel.app
        </a>
      </div>
    </div>
  );
}
