export function apiMessage(error) {
  const detail = error?.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) return detail.map((item) => item.msg || item.message).join('. ');
  return 'No fue posible completar la operación.';
}

export function formatNumber(value, suffix = '') {
  if (value === null || value === undefined || value === '') return '—';
  return `${Number(value).toLocaleString('es-MX', { maximumFractionDigits: 4 })}${suffix}`;
}

export function dateLabel(value) {
  if (!value) return '—';
  return new Intl.DateTimeFormat('es-MX', { dateStyle: 'medium', timeZone: 'UTC' }).format(new Date(`${value.slice(0, 10)}T00:00:00Z`));
}
