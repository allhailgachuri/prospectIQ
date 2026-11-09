import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { Globe, CheckCircle2, XCircle, AlertTriangle, ExternalLink } from 'lucide-react';
import { fetchBusinesses, fetchFilters } from '../api';
import { Badge, websiteStatusVariant, auditVariant } from '../components/Badge';
import { Pagination } from '../components/Pagination';

const STATUS_TABS = [
  { key: '',                              label: 'All Checked',    icon: Globe },
  { key: 'VERIFIED_WEBSITE',             label: 'Verified',        icon: CheckCircle2 },
  { key: 'WEBSITE_UNREACHABLE',          label: 'Unreachable',     icon: XCircle },
  { key: 'WEBSITE_NOT_FOUND_AFTER_CHECKS', label: 'Not Found',    icon: AlertTriangle },
];

export function WebsiteIntelligence() {
  const [status, setStatus]   = useState('');
  const [audit, setAudit]     = useState('');
  const [page, setPage]       = useState(1);

  const q = {
    website_status: status || undefined,
    audit_label: audit || undefined,
    has_website: true,
    page,
    page_size: 20,
  };

  const { data, isLoading } = useQuery({
    queryKey: ['websites', q],
    queryFn:  () => fetchBusinesses({ ...q, has_website: undefined }),
    placeholderData: prev => prev,
  });

  const { data: filters } = useQuery({ queryKey: ['filters'], queryFn: fetchFilters });

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Website Intelligence</h1>
        <p className="text-sm text-slate-500 mt-1">
          Audit results for checked websites. WEAK / POOR scores = redesign opportunities.
        </p>
      </div>

      {/* Status tabs */}
      <div className="flex gap-2 flex-wrap">
        {STATUS_TABS.map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => { setStatus(key); setPage(1); }}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-colors border
              ${status === key
                ? 'bg-blue-600 text-white border-blue-600'
                : 'bg-white text-slate-600 border-slate-200 hover:border-blue-300'
              }`}
          >
            <Icon size={14} /> {label}
          </button>
        ))}

        {/* Audit label filter */}
        {filters && (
          <select
            value={audit}
            onChange={e => { setAudit(e.target.value); setPage(1); }}
            className="ml-auto text-sm border border-slate-200 rounded-xl px-3 py-2 bg-white text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">All audit scores</option>
            {filters.audit_labels.map(l => (
              <option key={l} value={l}>{l}</option>
            ))}
          </select>
        )}
      </div>

      {/* Table */}
      <div className="bg-white border border-slate-200 rounded-2xl overflow-hidden">
        {isLoading ? (
          <div className="py-16 text-center text-slate-400">Loading...</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-slate-50 border-b border-slate-200">
              <tr>
                <th className="text-left px-5 py-3 font-medium text-slate-600">Business</th>
                <th className="text-left px-4 py-3 font-medium text-slate-600">Status</th>
                <th className="text-left px-4 py-3 font-medium text-slate-600">Audit</th>
                <th className="text-left px-4 py-3 font-medium text-slate-600">Score</th>
                <th className="text-left px-4 py-3 font-medium text-slate-600">HTTPS</th>
                <th className="text-left px-4 py-3 font-medium text-slate-600">Mobile</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {data?.items.map(b => (
                <tr key={b.source_record_id} className="hover:bg-slate-50 transition-colors">
                  <td className="px-5 py-3">
                    <div className="font-medium text-slate-800">{b.name}</div>
                    {b.neighbourhood && (
                      <div className="text-xs text-slate-400">{b.neighbourhood}</div>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <Badge
                      label={(b.website_status ?? b.website_presence ?? '—').replace(/^WEBSITE_/, '').replace(/_/g, ' ')}
                      variant={websiteStatusVariant(b.website_status ?? b.website_presence)}
                    />
                  </td>
                  <td className="px-4 py-3">
                    {b.audit_quality_label
                      ? <Badge label={b.audit_quality_label} variant={auditVariant(b.audit_quality_label)} />
                      : <span className="text-slate-300">—</span>
                    }
                  </td>
                  <td className="px-4 py-3 font-semibold text-slate-700">
                    {b.audit_score !== undefined && b.audit_score !== null
                      ? `${b.audit_score}/100`
                      : <span className="text-slate-300">—</span>
                    }
                  </td>
                  <td className="px-4 py-3">
                    {b.https !== undefined && b.https !== null
                      ? b.https
                        ? <span className="text-emerald-600">✓</span>
                        : <span className="text-red-500">✗</span>
                      : <span className="text-slate-300">—</span>
                    }
                  </td>
                  <td className="px-4 py-3">
                    {b.audit_mobile_friendly !== undefined && b.audit_mobile_friendly !== null
                      ? b.audit_mobile_friendly
                        ? <span className="text-emerald-600">✓</span>
                        : <span className="text-red-500">✗</span>
                      : <span className="text-slate-300">—</span>
                    }
                  </td>
                  <td className="px-4 py-3">
                    <Link
                      to={`/prospects/${encodeURIComponent(b.source_record_id)}`}
                      className="text-blue-600 hover:text-blue-800 transition-colors"
                    >
                      <ExternalLink size={14} />
                    </Link>
                  </td>
                </tr>
              ))}
              {(!data || data.items.length === 0) && (
                <tr><td colSpan={7} className="py-12 text-center text-slate-400">No results</td></tr>
              )}
            </tbody>
          </table>
        )}
      </div>

      {data && data.pages > 1 && (
        <Pagination
          page={data.page} pages={data.pages}
          total={data.total} pageSize={data.page_size}
          onChange={setPage}
        />
      )}
    </div>
  );
}
