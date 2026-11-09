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

export const fetchStats = (): Promise<Stats> =>
  api.get("/stats").then((r) => r.data);

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
