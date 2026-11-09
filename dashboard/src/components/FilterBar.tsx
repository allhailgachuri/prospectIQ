import { Search, X } from 'lucide-react';
import type { Filters } from '../types';
import type { BusinessQuery } from '../api';

interface FilterBarProps {
  filters: Filters;
  query: BusinessQuery;
  onChange: (q: BusinessQuery) => void;
}

function Select({
  label, value, options, onChange,
}: { label: string; value?: string; options: string[]; onChange: (v: string) => void }) {
  return (
    <select
      value={value ?? ''}
      onChange={e => onChange(e.target.value || '')}
      className="text-sm border border-slate-200 rounded-lg px-3 py-2 bg-white text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500 min-w-36"
    >
      <option value="">{label}</option>
      {options.map(o => <option key={o} value={o}>{o.replace(/_/g, ' ')}</option>)}
    </select>
  );
}

export function FilterBar({ filters, query, onChange }: FilterBarProps) {
  const hasActive = !!(query.search || query.category || query.neighbourhood ||
    query.website_status || query.audit_label || query.priority ||
    query.crm_status || query.has_phone || query.has_email);

  return (
    <div className="bg-white border border-slate-200 rounded-2xl p-4 space-y-3">
      {/* Search */}
      <div className="relative">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
        <input
          type="text"
          placeholder="Search businesses by name, address, description..."
          value={query.search ?? ''}
          onChange={e => onChange({ ...query, search: e.target.value || undefined, page: 1 })}
          className="w-full pl-9 pr-4 py-2.5 text-sm border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      {/* Filter row */}
      <div className="flex flex-wrap gap-2 items-center">
        <Select
          label="Category"
          value={query.category}
          options={filters.categories}
          onChange={v => onChange({ ...query, category: v || undefined, page: 1 })}
        />
        <Select
          label="Neighbourhood"
          value={query.neighbourhood}
          options={filters.neighbourhoods}
          onChange={v => onChange({ ...query, neighbourhood: v || undefined, page: 1 })}
        />
        <Select
          label="Website Status"
          value={query.website_status}
          options={filters.website_statuses}
          onChange={v => onChange({ ...query, website_status: v || undefined, page: 1 })}
        />
        <Select
          label="Audit Quality"
          value={query.audit_label}
          options={filters.audit_labels}
          onChange={v => onChange({ ...query, audit_label: v || undefined, page: 1 })}
        />
        <Select
          label="Priority"
          value={query.priority}
          options={filters.priorities}
          onChange={v => onChange({ ...query, priority: v || undefined, page: 1 })}
        />
        <Select
          label="CRM Status"
          value={query.crm_status}
          options={filters.crm_statuses}
          onChange={v => onChange({ ...query, crm_status: v || undefined, page: 1 })}
        />

        {/* Toggles */}
        <label className="flex items-center gap-1.5 text-sm text-slate-600 cursor-pointer select-none">
          <input
            type="checkbox"
            checked={query.has_phone === true}
            onChange={e => onChange({ ...query, has_phone: e.target.checked ? true : undefined, page: 1 })}
            className="rounded"
          />
          Has phone
        </label>
        <label className="flex items-center gap-1.5 text-sm text-slate-600 cursor-pointer select-none">
          <input
            type="checkbox"
            checked={query.has_email === true}
            onChange={e => onChange({ ...query, has_email: e.target.checked ? true : undefined, page: 1 })}
            className="rounded"
          />
          Has email
        </label>

        {hasActive && (
          <button
            onClick={() => onChange({ page: 1, page_size: query.page_size })}
            className="flex items-center gap-1 text-sm text-red-500 hover:text-red-700 ml-auto"
          >
            <X size={14} /> Clear filters
          </button>
        )}
      </div>
    </div>
  );
}
