import axios from "axios";
import type {
  BusinessDetail,
  PaginatedBusinesses,
  Stats,
  Filters,
  Job,
} from "./types";

export const apiBaseUrl = import.meta.env.VITE_API_URL || "/api";
export const reportUrl = (path: string) => `${apiBaseUrl}${path}`;
const api = axios.create({ baseURL: apiBaseUrl });

export interface BusinessQuery {
  search?: string;
  category?: string;
  neighbourhood?: string;
  website_status?: string;
  audit_label?: string;
  priority?: string;
  has_phone?: boolean;
  has_email?: boolean;
  has_website?: boolean;
  crm_status?: string;
  page?: number;
  page_size?: number;
}

const asCount = (value: unknown): number =>
  typeof value === "number" && Number.isFinite(value) ? value : 0;

const asArray = <T>(value: unknown): T[] =>
  Array.isArray(value) ? (value as T[]) : [];

export const fetchStats = async (): Promise<Stats> => {
  const { data } = await api.get<unknown>("/stats");
  if (!data || typeof data !== "object" || Array.isArray(data)) {
    throw new Error(
      "The API returned an invalid response. In Vercel, set VITE_API_URL to your deployed backend URL ending in /api, then redeploy the dashboard.",
    );
  }

  const payload = data as Record<string, unknown>;
  if (typeof payload.total !== "number") {
    throw new Error(
      "The API response is missing dashboard statistics. In Vercel, set VITE_API_URL to your deployed backend URL ending in /api, then redeploy the dashboard.",
    );
  }
  return {
    total: asCount(payload.total),
    with_website: asCount(payload.with_website),
    without_website: asCount(payload.without_website),
    with_phone: asCount(payload.with_phone),
    with_email: asCount(payload.with_email),
    total_checked: asCount(payload.total_checked),
    by_category: asArray<Stats["by_category"][number]>(payload.by_category),
    by_neighbourhood: asArray<Stats["by_neighbourhood"][number]>(
      payload.by_neighbourhood,
    ),
    website_statuses: asArray<Stats["website_statuses"][number]>(
      payload.website_statuses,
    ),
    audit_labels: asArray<Stats["audit_labels"][number]>(payload.audit_labels),
    crm_statuses: asArray<Stats["crm_statuses"][number]>(payload.crm_statuses),
  };
};

export const fetchFilters = (): Promise<Filters> =>
  api.get("/filters").then((r) => r.data);

export const fetchBusinesses = (
  q: BusinessQuery = {},
): Promise<PaginatedBusinesses> => {
  const params: Record<string, unknown> = { ...q };
  Object.keys(params).forEach(
    (k) => params[k] === undefined && delete params[k],
  );
  return api.get("/businesses", { params }).then((r) => r.data);
};

export const fetchBusinessDetail = (id: string): Promise<BusinessDetail> =>
  api.get(`/businesses/${encodeURIComponent(id)}`).then((r) => r.data);

export const updateCRM = (
  id: string,
  payload: { crm_status?: string; crm_notes?: string; crm_follow_up?: string },
): Promise<void> =>
  api
    .patch(`/businesses/${encodeURIComponent(id)}/crm`, payload)
    .then(() => undefined);

export const startCheckJob = (limit = 100): Promise<{ job_id: string }> =>
  api.post("/jobs/check", null, { params: { limit } }).then((r) => r.data);

export const startDiscoveryJob = (bbox: string): Promise<{ job_id: string }> =>
  api.post("/jobs/discover", null, { params: { bbox } }).then((r) => r.data);

export const startReportJob = (limit = 50): Promise<{ job_id: string }> =>
  api.post("/jobs/report", null, { params: { limit } }).then((r) => r.data);

export const fetchJobStatus = (jobId: string): Promise<Job> =>
  api.get(`/jobs/${jobId}`).then((r) => r.data);

export const fetchReports = (): Promise<
  Array<{ name: string; size_kb: number; created: number }>
> => api.get("/reports").then((r) => r.data);

export const downloadReport = (): void => {
  window.open(reportUrl("/reports/latest"), "_blank");
};

export const downloadCSV = (): void => {
  window.open(reportUrl("/export/csv"), "_blank");
};

export const downloadExcel = (): void => {
  window.open(reportUrl("/export/xlsx"), "_blank");
};
