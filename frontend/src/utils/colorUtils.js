// colorUtils.js - Shared stable color assignment for service users
// Colors are based on status so they're meaningful and consistent everywhere.

export const STATUS_COLORS = {
    Active:   '#79C981', // green
    Inactive: '#E57C7E', // red/pink
    Pending:  '#FFBC2A', // amber
    Closed:   '#AAAAAA', // grey
  };
  
  const DEFAULT_COLOR = '#34A2ED'; // blue fallback
  
  /**
   * Returns a color for a given status string.
   * Capitalizes first letter so 'active' and 'Active' both match.
   *
   * @param {string} status - e.g. 'Active', 'active', 'Inactive'
   * @returns {string} hex color
   */
  export function colorForStatus(status) {
    if (!status) return DEFAULT_COLOR;
    const normalized = status.charAt(0).toUpperCase() + status.slice(1).toLowerCase();
    return STATUS_COLORS[normalized] ?? DEFAULT_COLOR;
  }