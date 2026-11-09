import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import {
  fetchBusinesses,
  fetchFilters,
  downloadCSV,
  downloadExcel,
} from "../api";
import type { BusinessQuery } from "../api";
import { FilterBar } from "../components/FilterBar";
import { ProspectCard } from "../components/ProspectCard";
import { Pagination } from "../components/Pagination";
import { Download, FileSpreadsheet } from "lucide-react";

export function Prospects() {
  const [searchParams] = useSearchParams();
  const [query, setQuery] = useState<BusinessQuery>(() => ({
    page: 1,
    page_size: 24,
    category: searchParams.get("category") || undefined,
  }));

  const { data: filters } = useQuery({
    queryKey: ["filters"],
    queryFn: fetchFilters,
  });
  const { data, isLoading } = useQuery({
    queryKey: ["businesses", query],
    queryFn: () => fetchBusinesses(query),
    placeholderData: (prev) => prev,
  });

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Prospects</h1>
          <p className="text-sm text-slate-500 mt-1">
            {data
              ? `${data.total.toLocaleString()} businesses found`
              : "Loading..."}
          </p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <button
            type="button"
            onClick={downloadExcel}
            className="export-button action-primary"
          >
            <FileSpreadsheet size={15} /> Export outreach Excel
          </button>
          <button
            type="button"
            onClick={downloadCSV}
            aria-label="Export all data as CSV"
            title="Export all data as CSV"
            className="export-button action-soft"
          >
            <Download size={15} /> CSV
          </button>
        </div>
      </div>

      {filters && (
        <FilterBar filters={filters} query={query} onChange={setQuery} />
      )}

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <div
              key={i}
              className="h-52 bg-slate-100 animate-pulse rounded-2xl"
            />
          ))}
        </div>
      ) : data?.items.length === 0 ? (
        <div className="text-center py-20 text-slate-400">
          <p className="text-lg font-medium">
            No businesses match your filters
          </p>
          <p className="text-sm mt-1">
            Try removing some filters to broaden the search
          </p>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {data?.items.map((b) => (
              <ProspectCard key={b.source_record_id} business={b} />
            ))}
          </div>
          {data && data.pages > 1 && (
            <Pagination
              page={data.page}
              pages={data.pages}
              total={data.total}
              pageSize={data.page_size}
              onChange={(p) => setQuery((q) => ({ ...q, page: p }))}
            />
          )}
        </>
      )}
    </div>
  );
}
