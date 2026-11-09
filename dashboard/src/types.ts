export interface Business {
  source_record_id: string;
  source: string;
  name: string;
  alt_name?: string;
  category?: string;
  subcategory?: string;
  description?: string;
  brand?: string;
  opening_hours?: string;
  website?: string;
  website_presence?: string;
  website_status?: string;
  verified_url?: string;
  https?: boolean;
  http_status?: number;
  website_error?: string;
  website_checked_at?: string;
  audit_score?: number;
  audit_quality_label?: string;
  audit_mobile_friendly?: boolean;
  audit_has_contact?: boolean;
  audit_has_cta?: boolean;
  audit_findings_json?: string;
  audit_recommendations?: string;
  audit_at?: string;
  email?: string;
  phone?: string;
  whatsapp?: string;
  facebook?: string;
  instagram?: string;
  twitter?: string;
  neighbourhood?: string;
  address?: string;
  latitude?: number;
  longitude?: number;
  map_link?: string;
  osm_tags_json?: string;
  first_seen_at?: string;
  last_seen_at?: string;
  crm_status?: string;
  crm_notes?: string;
  crm_follow_up?: string;
  // computed by API
  lead_score?: number;
  priority?: "HIGH" | "MEDIUM" | "LOW" | "NEEDS_MANUAL_REVIEW";
  industry?: string;
}

export interface Intelligence {
  industry: string;
  what_it_does: string;
  likely_customers: string;
  services: string[];
  primary_service: string;
  opportunity: string;
  lead_score: number;
  priority: string;
  score_reasons: string[];
  score_deductions: string[];
}

export interface EmailOutreach {
  subject: string;
  body: string;
  to?: string;
  available: string;
}

export interface CallScript {
  full_script: string;
  short_script: string;
  phone: string;
}

export interface Outreach {
  whatsapp_message: string;
  email: EmailOutreach;
  call_script: CallScript;
  followup_strategy: string;
  agency_url: string;
}

export interface BusinessDetail {
  business: Business;
  intelligence: Intelligence;
  outreach: Outreach;
}

export interface PaginatedBusinesses {
  items: Business[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface Stats {
  total: number;
  with_website: number;
  without_website: number;
  with_phone: number;
  with_email: number;
  total_checked: number;
  by_category: Array<{ category: string; n: number }>;
  by_neighbourhood: Array<{ neighbourhood: string; n: number }>;
  website_statuses: Array<{ website_status: string; n: number }>;
  audit_labels: Array<{ audit_quality_label: string; n: number }>;
  crm_statuses: Array<{ crm_status: string; n: number }>;
}

export interface Filters {
  categories: string[];
  neighbourhoods: string[];
  website_statuses: string[];
  audit_labels: string[];
  priorities: string[];
  crm_statuses: string[];
}

export interface AuditFinding {
  check: string;
  result: "PASS" | "FAIL" | "WEAK";
  detail: string;
  severity?: "HIGH" | "MEDIUM" | "LOW" | null;
}

export interface Job {
  status: "running" | "done" | "error";
  done: number;
  total: number;
  records?: number;
  file?: string;
  error?: string;
}
