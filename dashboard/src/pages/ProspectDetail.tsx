import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  Phone,
  Mail,
  Globe,
  MapPin,
  ExternalLink,
  MessageSquare,
  PhoneCall,
  Calendar,
  CheckCircle,
  Tag,
  Building2,
  Star,
  ClipboardList,
} from "lucide-react";
import { fetchBusinessDetail, updateCRM } from "../api";
import {
  Badge,
  priorityVariant,
  websiteStatusVariant,
  auditVariant,
} from "../components/Badge";
import type { AuditFinding } from "../types";

function Section({
  title,
  icon: Icon,
  children,
}: {
  title: string;
  icon: typeof Phone;
  children: React.ReactNode;
}) {
  return (
    <div className="bg-white border border-slate-200 rounded-2xl p-6">
      <h2 className="font-semibold text-slate-800 mb-4 flex items-center gap-2">
        <Icon size={16} className="text-blue-600" />
        {title}
      </h2>
      {children}
    </div>
  );
}

function InfoRow({
  label,
  value,
}: {
  label: string;
  value?: string | number | null;
}) {
  if (!value) return null;
  return (
    <div className="flex items-start gap-3 py-2 border-b border-slate-50 last:border-0">
      <span className="text-xs font-medium text-slate-400 uppercase tracking-wide w-36 shrink-0 pt-0.5">
        {label}
      </span>
      <span className="text-sm text-slate-700 break-all">{String(value)}</span>
    </div>
  );
}

function CodeBlock({ content }: { content: string }) {
  const [copied, setCopied] = useState(false);
  const copy = () => {
    navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  return (
    <div className="relative">
      <pre className="bg-slate-50 border border-slate-200 rounded-xl p-4 text-sm text-slate-700 whitespace-pre-wrap overflow-auto max-h-96">
        {content}
      </pre>
      <button
        onClick={copy}
        className="absolute top-2 right-2 px-2 py-1 text-xs bg-white border border-slate-200 rounded-lg text-slate-500 hover:bg-blue-50 hover:text-blue-600 transition-colors"
      >
        {copied ? "Copied!" : "Copy"}
      </button>
    </div>
  );
}

const CRM_OPTIONS = [
  { value: "new", label: "New", color: "bg-blue-100 text-blue-700" },
  {
    value: "contacted",
    label: "Contacted",
    color: "bg-amber-100 text-amber-700",
  },
  {
    value: "interested",
    label: "Interested",
    color: "bg-emerald-100 text-emerald-700",
  },
  {
    value: "not_interested",
    label: "Not Interested",
    color: "bg-slate-100 text-slate-600",
  },
  { value: "dnc", label: "Do Not Contact", color: "bg-red-100 text-red-700" },
];

export function ProspectDetail() {
  const { id } = useParams<{ id: string }>();
  const qc = useQueryClient();
  const [activeTab, setActiveTab] = useState<
    "profile" | "website" | "outreach" | "crm"
  >("profile");
  const [crmStatus, setCrmStatus] = useState("");
  const [crmNotes, setCrmNotes] = useState("");
  const [crmFollowUp, setCrmFollowUp] = useState("");
  const [saved, setSaved] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ["business", id],
    queryFn: () => fetchBusinessDetail(id!),
    enabled: !!id,
  });

  useEffect(() => {
    if (!data) return;
    setCrmStatus(data.business.crm_status ?? "");
    setCrmNotes(data.business.crm_notes ?? "");
    setCrmFollowUp(data.business.crm_follow_up ?? "");
  }, [data]);

  const mutation = useMutation({
    mutationFn: () =>
      updateCRM(id!, {
        crm_status: crmStatus || undefined,
        crm_notes: crmNotes || undefined,
        crm_follow_up: crmFollowUp || undefined,
      }),
    onSuccess: () => {
      setSaved(true);
      setTimeout(() => setSaved(false), 2500);
      qc.invalidateQueries({ queryKey: ["businesses"] });
    },
  });

  if (isLoading)
    return (
      <div className="flex items-center justify-center h-64 text-slate-400">
        Loading prospect profile...
      </div>
    );
  if (!data) return <div className="text-slate-500">Prospect not found.</div>;

  const { business: b, intelligence: intel, outreach } = data;

  const TABS = [
    { key: "profile", label: "Profile", icon: Building2 },
    { key: "website", label: "Website Audit", icon: Globe },
    { key: "outreach", label: "Outreach Scripts", icon: MessageSquare },
    { key: "crm", label: "CRM & Notes", icon: ClipboardList },
  ] as const;

  const findings: AuditFinding[] = b.audit_findings_json
    ? JSON.parse(b.audit_findings_json)
    : [];

  return (
    <div className="space-y-5 max-w-5xl">
      {/* Back */}
      <Link
        to="/prospects"
        className="flex items-center gap-2 text-sm text-slate-500 hover:text-blue-600 transition-colors w-fit"
      >
        <ArrowLeft size={15} /> Back to Prospects
      </Link>

      {/* Hero */}
      <div className="bg-white border border-slate-200 rounded-2xl p-6">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">{b.name}</h1>
            <p className="text-slate-500 mt-1">{intel.industry}</p>
            {b.neighbourhood && (
              <div className="flex items-center gap-1.5 text-sm text-slate-400 mt-2">
                <MapPin size={13} /> {b.neighbourhood}
              </div>
            )}
          </div>
          <div className="flex flex-col items-end gap-2">
            <Badge
              label={intel.priority}
              variant={priorityVariant(intel.priority)}
              size="md"
            />
            <div className="text-right">
              <span className="text-3xl font-bold text-slate-800">
                {intel.lead_score}
              </span>
              <span className="text-slate-400 text-sm">/100</span>
            </div>
          </div>
        </div>

        {/* Score reasons */}
        {intel.score_reasons.length > 0 && (
          <div className="mt-4 p-4 bg-blue-50 rounded-xl">
            <p className="text-xs font-semibold text-blue-700 mb-2 uppercase tracking-wide">
              Why this score
            </p>
            <ul className="space-y-1">
              {intel.score_reasons.map((r, i) => (
                <li
                  key={i}
                  className="text-sm text-blue-800 flex items-start gap-2"
                >
                  <CheckCircle size={13} className="mt-0.5 shrink-0" /> {r}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Contact quick-access */}
        <div className="flex flex-wrap gap-3 mt-4">
          {b.phone && (
            <a
              href={`tel:${b.phone}`}
              className="flex items-center gap-2 px-3 py-2 bg-emerald-50 hover:bg-emerald-100 text-emerald-700 rounded-xl text-sm transition-colors"
            >
              <Phone size={14} /> {b.phone}
            </a>
          )}
          {b.email && (
            <a
              href={`mailto:${b.email}`}
              className="flex items-center gap-2 px-3 py-2 bg-blue-50 hover:bg-blue-100 text-blue-700 rounded-xl text-sm transition-colors"
            >
              <Mail size={14} /> {b.email}
            </a>
          )}
          {b.verified_url && (
            <a
              href={b.verified_url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 px-3 py-2 bg-cyan-50 hover:bg-cyan-100 text-cyan-700 rounded-xl text-sm transition-colors"
            >
              <Globe size={14} /> Website <ExternalLink size={11} />
            </a>
          )}
          {b.map_link && (
            <a
              href={b.map_link}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 px-3 py-2 bg-rose-50 hover:bg-rose-100 text-rose-700 rounded-xl text-sm transition-colors"
            >
              <MapPin size={14} /> Map <ExternalLink size={11} />
            </a>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-slate-100 p-1 rounded-xl w-fit">
        {TABS.map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => setActiveTab(key)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors
              ${
                activeTab === key
                  ? "bg-white text-slate-900 shadow-sm"
                  : "text-slate-500 hover:text-slate-700"
              }`}
          >
            <Icon size={14} /> {label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {activeTab === "profile" && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          <Section title="Business Identity" icon={Building2}>
            <InfoRow label="Category" value={b.category} />
            <InfoRow label="Subcategory" value={b.subcategory} />
            <InfoRow label="Industry" value={intel.industry} />
            <InfoRow label="What it does" value={intel.what_it_does} />
            <InfoRow label="Likely customers" value={intel.likely_customers} />
            <InfoRow label="Description" value={b.description} />
            <InfoRow label="Opening hours" value={b.opening_hours} />
            <InfoRow label="Brand" value={b.brand} />
          </Section>

          <Section title="Location" icon={MapPin}>
            <InfoRow label="Neighbourhood" value={b.neighbourhood} />
            <InfoRow label="Address" value={b.address} />
            <InfoRow label="Latitude" value={b.latitude} />
            <InfoRow label="Longitude" value={b.longitude} />
            <InfoRow label="Source" value={b.source} />
            <InfoRow label="OSM record" value={b.source_record_id} />
            <InfoRow label="First seen" value={b.first_seen_at} />
            <InfoRow label="Last seen" value={b.last_seen_at} />
          </Section>

          <Section title="Opportunity Analysis" icon={Star}>
            <p className="text-sm text-slate-700 mb-4">{intel.opportunity}</p>
            <div>
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">
                Recommended services
              </p>
              <div className="flex flex-wrap gap-2">
                {intel.services.map((s) => (
                  <span
                    key={s}
                    className={`text-xs px-3 py-1 rounded-full border font-medium
                    ${
                      s === intel.primary_service
                        ? "bg-blue-600 text-white border-blue-600"
                        : "bg-slate-50 text-slate-600 border-slate-200"
                    }`}
                  >
                    {s === intel.primary_service ? "★ " : ""}
                    {s}
                  </span>
                ))}
              </div>
            </div>
          </Section>

          <Section title="Contacts" icon={Phone}>
            <InfoRow label="Phone" value={b.phone} />
            <InfoRow label="Email" value={b.email} />
            <InfoRow label="WhatsApp" value={b.whatsapp} />
            <InfoRow label="Website" value={b.website} />
            <InfoRow label="Facebook" value={b.facebook} />
            <InfoRow label="Instagram" value={b.instagram} />
            <InfoRow label="Twitter/X" value={b.twitter} />
            <p className="text-xs text-slate-400 mt-3 italic">
              Contact details sourced from OpenStreetMap public tags only.
              Verify before outreach.
            </p>
          </Section>
        </div>
      )}

      {activeTab === "website" && (
        <div className="space-y-5">
          <Section title="Website Verification" icon={Globe}>
            <div className="flex flex-wrap gap-3 mb-4">
              <Badge
                label={(b.website_status ?? b.website_presence ?? "UNKNOWN")
                  .replace(/^WEBSITE_/, "")
                  .replace(/_/g, " ")}
                variant={websiteStatusVariant(
                  b.website_status ?? b.website_presence,
                )}
                size="md"
              />
              {b.audit_quality_label && (
                <Badge
                  label={`Audit: ${b.audit_quality_label}`}
                  variant={auditVariant(b.audit_quality_label)}
                  size="md"
                />
              )}
              {b.audit_score !== undefined && (
                <span className="text-2xl font-bold text-slate-800">
                  {b.audit_score}
                  <span className="text-slate-400 text-sm">/100</span>
                </span>
              )}
            </div>
            <InfoRow label="OSM website" value={b.website} />
            <InfoRow label="Verified URL" value={b.verified_url} />
            <InfoRow
              label="HTTPS"
              value={
                b.https !== null && b.https !== undefined
                  ? b.https
                    ? "Yes"
                    : "No"
                  : undefined
              }
            />
            <InfoRow label="HTTP status" value={b.http_status} />
            <InfoRow label="Error" value={b.website_error} />
            <InfoRow label="Checked at" value={b.website_checked_at} />
            <InfoRow
              label="Mobile friendly"
              value={
                b.audit_mobile_friendly !== null &&
                b.audit_mobile_friendly !== undefined
                  ? b.audit_mobile_friendly
                    ? "Yes"
                    : "No"
                  : undefined
              }
            />
            <InfoRow
              label="Contact on site"
              value={
                b.audit_has_contact !== null
                  ? b.audit_has_contact
                    ? "Yes"
                    : "No"
                  : undefined
              }
            />
          </Section>

          {findings.length > 0 && (
            <Section title="Audit Findings" icon={Tag}>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-100">
                      <th className="text-left py-2 px-3 text-slate-500 font-medium">
                        Check
                      </th>
                      <th className="text-left py-2 px-3 text-slate-500 font-medium">
                        Result
                      </th>
                      <th className="text-left py-2 px-3 text-slate-500 font-medium">
                        Finding
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {findings.map((f, i) => (
                      <tr key={i} className="border-b border-slate-50">
                        <td className="py-2 px-3 font-medium text-slate-700">
                          {f.check}
                        </td>
                        <td className="py-2 px-3">
                          <Badge
                            label={f.result}
                            variant={
                              f.result === "PASS"
                                ? "verified"
                                : f.result === "FAIL"
                                  ? "unreachable"
                                  : "medium"
                            }
                            size="sm"
                          />
                        </td>
                        <td className="py-2 px-3 text-slate-600">{f.detail}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Section>
          )}

          {b.audit_recommendations && (
            <Section title="Recommendations" icon={CheckCircle}>
              <ul className="space-y-2">
                {b.audit_recommendations
                  .split(";")
                  .filter(Boolean)
                  .map((r, i) => (
                    <li
                      key={i}
                      className="flex items-start gap-2 text-sm text-slate-700"
                    >
                      <span className="text-blue-500 mt-0.5 shrink-0">→</span>
                      {r.trim()}
                    </li>
                  ))}
              </ul>
            </Section>
          )}
        </div>
      )}

      {activeTab === "outreach" && (
        <div className="space-y-5">
          <Section title="WhatsApp / SMS Message" icon={MessageSquare}>
            <CodeBlock content={outreach.whatsapp_message} />
          </Section>

          <Section title="Email Outreach" icon={Mail}>
            {outreach.email.available === "true" ? (
              <div className="space-y-3">
                <div className="bg-slate-50 rounded-xl px-4 py-2">
                  <span className="text-xs font-semibold text-slate-500 uppercase tracking-wide">
                    Subject
                  </span>
                  <p className="text-sm text-slate-800 font-medium mt-1">
                    {outreach.email.subject}
                  </p>
                </div>
                <div className="bg-slate-50 rounded-xl px-4 py-2">
                  <span className="text-xs font-semibold text-slate-500 uppercase tracking-wide">
                    To
                  </span>
                  <p className="text-sm text-slate-800 mt-1">
                    {outreach.email.to}
                  </p>
                </div>
                <CodeBlock content={outreach.email.body} />
              </div>
            ) : (
              <p className="text-sm text-slate-500 italic">
                {outreach.email.body}
              </p>
            )}
          </Section>

          <Section title="Phone Call Script" icon={PhoneCall}>
            <CodeBlock content={outreach.call_script.full_script} />
            <div className="mt-4">
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">
                Short version
              </p>
              <CodeBlock content={outreach.call_script.short_script} />
            </div>
          </Section>

          <Section title="Follow-up Strategy" icon={Calendar}>
            <CodeBlock content={outreach.followup_strategy} />
          </Section>

          <div className="bg-blue-50 border border-blue-200 rounded-xl px-4 py-3 text-sm text-blue-800">
            Agency link included in every script:{" "}
            <a
              href={outreach.agency_url}
              target="_blank"
              rel="noopener noreferrer"
              className="font-medium underline"
            >
              {outreach.agency_url}
            </a>
          </div>
        </div>
      )}

      {activeTab === "crm" && (
        <Section title="CRM & Outreach Tracking" icon={ClipboardList}>
          <div className="space-y-5">
            {/* Status */}
            <div>
              <label className="text-xs font-semibold text-slate-500 uppercase tracking-wide block mb-2">
                Status
              </label>
              <div className="flex flex-wrap gap-2">
                {CRM_OPTIONS.map((opt) => (
                  <button
                    key={opt.value}
                    onClick={() => setCrmStatus(opt.value)}
                    className={`px-3 py-1.5 rounded-lg text-sm font-medium border transition-all
                      ${
                        crmStatus === opt.value
                          ? `${opt.color} border-current ring-2 ring-offset-1 ring-blue-300`
                          : "bg-white text-slate-500 border-slate-200 hover:border-slate-400"
                      }`}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Notes */}
            <div>
              <label className="text-xs font-semibold text-slate-500 uppercase tracking-wide block mb-2">
                Notes
              </label>
              <textarea
                rows={4}
                value={crmNotes}
                onChange={(e) => setCrmNotes(e.target.value)}
                placeholder="Record what happened when you contacted this business..."
                className="w-full border border-slate-200 rounded-xl px-4 py-3 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
              />
            </div>

            {/* Follow-up date */}
            <div>
              <label className="text-xs font-semibold text-slate-500 uppercase tracking-wide block mb-2">
                Follow-up date
              </label>
              <input
                type="date"
                value={crmFollowUp}
                onChange={(e) => setCrmFollowUp(e.target.value)}
                className="border border-slate-200 rounded-xl px-4 py-2 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <button
              onClick={() => mutation.mutate()}
              disabled={mutation.isPending}
              className="flex items-center gap-2 px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-sm font-semibold transition-colors disabled:opacity-50"
            >
              {mutation.isPending
                ? "Saving..."
                : saved
                  ? "✓ Saved!"
                  : "Save CRM Update"}
            </button>

            {crmStatus === "dnc" && (
              <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-3 text-sm text-red-700">
                This prospect is marked <strong>Do Not Contact</strong>. No
                outreach should be sent.
              </div>
            )}
          </div>
        </Section>
      )}
    </div>
  );
}
