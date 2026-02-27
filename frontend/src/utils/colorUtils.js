// colorUtils.js - Shared status colors and symbols for service users.
// Uses both color AND a symbol so colorblind users can distinguish statuses.
// Palette chosen to be distinguishable under deuteranopia/protanopia:
//   Active  → blue  (safe for all CVD types)
//   Pending → orange/amber (distinguishable from blue)
//   Inactive → medium grey (neutral, clearly different from both)

export const STATUS_OPTIONS = ['Active', 'Pending', 'Inactive'];

export const STATUS_CONFIG = {
  Active:   { color: '#2563EB', bg: '#EFF6FF', symbol: '●', label: 'Active' },   // blue
  Pending:  { color: '#D97706', bg: '#FFFBEB', symbol: '◆', label: 'Pending' },  // amber
  Inactive: { color: '#6B7280', bg: '#F3F4F6', symbol: '■', label: 'Inactive' }, // grey
};

const DEFAULT_CONFIG = { color: '#9CA3AF', bg: '#F9FAFB', symbol: '○', label: '' };

/**
 * Returns the full config for a given status string.
 * Normalizes 'active', 'ACTIVE', 'Active' → 'Active'.
 */
export function statusConfig(status) {
  if (!status) return DEFAULT_CONFIG;
  const normalized = status.charAt(0).toUpperCase() + status.slice(1).toLowerCase();
  return STATUS_CONFIG[normalized] ?? DEFAULT_CONFIG;
}

/** Convenience: just the hex color */
export function colorForStatus(status) {
  return statusConfig(status).color;
}