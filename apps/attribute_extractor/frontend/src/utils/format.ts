export function formatPackageLabel(tzId: string, executionVariant: string | null | undefined): string {
  const variant = executionVariant?.trim();
  return variant ? `${tzId} (${variant})` : tzId;
}

export function formatDate(value: string): string {
  return new Date(value).toLocaleDateString('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  });
}

export function formatIssueDetail(value: unknown): string {
  if (Array.isArray(value)) return value.map((item) => String(item)).join(', ');
  if (value && typeof value === 'object') return JSON.stringify(value, null, 2);
  if (value === null || value === undefined) return 'Н/Д';
  return String(value);
}
