import dayjs from 'dayjs';
import duration from 'dayjs/plugin/duration';
import relativeTime from 'dayjs/plugin/relativeTime';

dayjs.extend(duration);
dayjs.extend(relativeTime);

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return '-';
  return dayjs(iso).format('YYYY-MM-DD HH:mm');
}

export function formatDuration(startIso: string | null, endIso: string | null): string {
  if (!startIso) return '-';
  const end = endIso ? dayjs(endIso) : dayjs();
  const ms = end.diff(dayjs(startIso));
  if (ms < 0) return '-';
  const d = dayjs.duration(ms);
  const h = Math.floor(d.asHours());
  const m = d.minutes();
  const s = d.seconds();
  if (h > 0) return `${h}h ${m}m ${s}s`;
  if (m > 0) return `${m}m ${s}s`;
  return `${s}s`;
}

export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
