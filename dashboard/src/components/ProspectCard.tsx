import { Link } from "react-router-dom";
import {
  Phone,
  Mail,
  Globe,
  MapPin,
  ExternalLink,
  MessageCircle,
} from "lucide-react";
import {
  Badge,
  priorityVariant,
  websiteStatusVariant,
  auditVariant,
} from "./Badge";
import type { Business } from "../types";

interface ProspectCardProps {
  business: Business;
}

export function ProspectCard({ business: b }: ProspectCardProps) {
  const websiteUrl = b.verified_url || b.website;
  const safeWebsiteUrl =
    websiteUrl && /^https?:\/\//i.test(websiteUrl) ? websiteUrl : null;
  const wsLabel = b.website_status
    ? b.website_status.replace(/^WEBSITE_/, "").replace(/_/g, " ")
    : b.website_presence === "not_listed_in_osm"
      ? "NOT IN OSM"
      : "UNKNOWN";

  return (
    <div className="bg-white border border-slate-200 rounded-2xl p-5 hover:border-blue-300 hover:shadow-md transition-all group">
      {/* Header */}
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="min-w-0">
          <h3 className="font-semibold text-slate-900 truncate group-hover:text-blue-700 transition-colors">
            {b.name}
          </h3>
          <p className="text-xs text-slate-400 mt-0.5">
            {b.industry ?? b.category ?? "—"}
          </p>
        </div>
        <div className="shrink-0 flex flex-col items-end gap-1.5">
          {b.priority && (
            <Badge label={b.priority} variant={priorityVariant(b.priority)} />
          )}
          {b.lead_score !== undefined && (
            <span className="text-xs text-slate-500 font-medium">
              {b.lead_score}/100
            </span>
          )}
        </div>
      </div>

      {/* Location */}
      {b.neighbourhood && (
        <div className="flex items-center gap-1.5 text-xs text-slate-500 mb-2">
          <MapPin size={12} className="shrink-0" />
          <span className="truncate">
            {b.neighbourhood}
            {b.address ? ` · ${b.address}` : ""}
          </span>
        </div>
      )}

      {b.description && (
        <p className="text-xs text-slate-500 leading-relaxed mb-3 line-clamp-2">
          {b.description}
        </p>
      )}

      {/* Website status */}
      <div className="flex flex-wrap gap-1.5 mb-3">
        <Badge
          label={wsLabel}
          variant={websiteStatusVariant(b.website_status ?? b.website_presence)}
          size="sm"
        />
        {b.audit_quality_label && (
          <Badge
            label={`Audit: ${b.audit_quality_label}`}
            variant={auditVariant(b.audit_quality_label)}
            size="sm"
          />
        )}
        {b.audit_score !== undefined && (
          <Badge
            label={`Score: ${b.audit_score}/100`}
            variant="default"
            size="sm"
          />
        )}
      </div>

      {/* Contact icons */}
      <div className="flex items-center gap-3 text-slate-400 mb-3">
        {b.phone && (
          <a
            href={`tel:${b.phone}`}
            aria-label={`Call ${b.name}: ${b.phone}`}
            title={b.phone}
            className="text-emerald-600"
          >
            <Phone size={14} />
          </a>
        )}
        {b.whatsapp && (
          <a
            href={`https://wa.me/${b.whatsapp.replace(/\D/g, "")}`}
            target="_blank"
            rel="noopener noreferrer"
            aria-label={`WhatsApp ${b.name}`}
            title={b.whatsapp}
            className="text-emerald-600"
          >
            <MessageCircle size={14} />
          </a>
        )}
        {b.email && (
          <a
            href={`mailto:${b.email}`}
            aria-label={`Email ${b.name}: ${b.email}`}
            title={b.email}
            className="text-blue-600"
          >
            <Mail size={14} />
          </a>
        )}
        {safeWebsiteUrl && (
          <a
            href={safeWebsiteUrl}
            target="_blank"
            rel="noopener noreferrer"
            aria-label={`Open ${b.name} website`}
            title={safeWebsiteUrl}
            className="text-cyan-700"
          >
            <Globe size={14} />
          </a>
        )}
        {b.map_link && (
          <a
            href={b.map_link}
            target="_blank"
            rel="noopener noreferrer"
            onClick={(e) => e.stopPropagation()}
          >
            <MapPin
              size={14}
              className="text-rose-400 hover:text-rose-600 transition-colors"
            />
          </a>
        )}
      </div>

      {safeWebsiteUrl && (
        <a
          href={safeWebsiteUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-2 min-w-0 text-xs text-blue-700 hover:text-blue-900 mb-3"
        >
          <Globe size={12} className="shrink-0" />
          <span className="truncate">
            {safeWebsiteUrl.replace(/^https?:\/\//i, "")}
          </span>
          <ExternalLink size={11} className="shrink-0" />
        </a>
      )}

      {/* Action */}
      <Link
        to={`/prospects/${encodeURIComponent(b.source_record_id)}`}
        className="flex items-center justify-between w-full px-3 py-2 bg-slate-50 hover:bg-blue-50 rounded-xl text-sm text-slate-600 hover:text-blue-700 transition-colors font-medium"
      >
        View full profile
        <ExternalLink size={13} />
      </Link>
    </div>
  );
}
