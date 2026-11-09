interface BadgeProps {
  label: string;
  variant?: 'high' | 'medium' | 'low' | 'review' | 'verified' | 'unreachable' | 'notfound' | 'unknown' | 'good' | 'fair' | 'weak' | 'poor' | 'default';
  size?: 'sm' | 'md';
}

const VARIANT_CLASSES: Record<string, string> = {
  high:        'bg-red-100 text-red-700 border border-red-200',
  medium:      'bg-amber-100 text-amber-700 border border-amber-200',
  low:         'bg-slate-100 text-slate-600 border border-slate-200',
  review:      'bg-purple-100 text-purple-700 border border-purple-200',
  verified:    'bg-emerald-100 text-emerald-700 border border-emerald-200',
  unreachable: 'bg-red-100 text-red-700 border border-red-200',
  notfound:    'bg-orange-100 text-orange-700 border border-orange-200',
  unknown:     'bg-slate-100 text-slate-500 border border-slate-200',
  good:        'bg-emerald-100 text-emerald-700 border border-emerald-200',
  fair:        'bg-blue-100 text-blue-700 border border-blue-200',
  weak:        'bg-amber-100 text-amber-700 border border-amber-200',
  poor:        'bg-red-100 text-red-700 border border-red-200',
  default:     'bg-slate-100 text-slate-600 border border-slate-200',
};

export function Badge({ label, variant = 'default', size = 'sm' }: BadgeProps) {
  const cls = VARIANT_CLASSES[variant] ?? VARIANT_CLASSES.default;
  const sz  = size === 'sm' ? 'text-xs px-2 py-0.5' : 'text-sm px-3 py-1';
  return (
    <span className={`inline-flex items-center rounded-full font-medium ${sz} ${cls}`}>
      {label}
    </span>
  );
}

export function priorityVariant(p?: string): BadgeProps['variant'] {
  const map: Record<string, BadgeProps['variant']> = {
    HIGH: 'high', MEDIUM: 'medium', LOW: 'low', NEEDS_MANUAL_REVIEW: 'review',
  };
  return map[p ?? ''] ?? 'default';
}

export function websiteStatusVariant(s?: string): BadgeProps['variant'] {
  const map: Record<string, BadgeProps['variant']> = {
    VERIFIED_WEBSITE: 'verified',
    WEBSITE_UNREACHABLE: 'unreachable',
    WEBSITE_NOT_FOUND_AFTER_CHECKS: 'notfound',
    WEBSITE_STATUS_UNKNOWN: 'unknown',
    listed_in_osm: 'verified',
    not_listed_in_osm: 'notfound',
  };
  return map[s ?? ''] ?? 'default';
}

export function auditVariant(l?: string): BadgeProps['variant'] {
  const map: Record<string, BadgeProps['variant']> = {
    GOOD: 'good', FAIR: 'fair', WEAK: 'weak', POOR: 'poor',
  };
  return map[l ?? ''] ?? 'default';
}
