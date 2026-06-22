export const DEFAULT_API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:18080';
export const API_KEY_HEADER = 'X-API-Key';
export const API_KEY_STORAGE_KEY = 'mc_api_key';
export const API_BASE_URL_STORAGE_KEY = 'mc_api_base_url';
export const WS_BASE = import.meta.env.VITE_WS_BASE_URL || 'ws://localhost:18080';

export const STATUS_CONFIG = {
  pending:   { color: '#9e9e9e', bg: '#f5f5f5', label: '待执行' },
  running:   { color: '#1976d2', bg: '#e3f2fd', label: '执行中', pulse: true },
  completed: { color: '#2e7d32', bg: '#e8f5e9', label: '已完成' },
  failed:    { color: '#d32f2f', bg: '#ffebee', label: '失败' },
} as const;

export type TaskStatus = keyof typeof STATUS_CONFIG;

export const TASK_TYPE_LABELS: Record<string, string> = {
  search: '搜索采集',
  comments: '评论采集',
  scripts: '文案提取',
  merge: '数据合并',
  run_all: '一键全流程',
};

export const WHISPER_MODELS = [
  { value: 'tiny', label: 'Tiny (最快)' },
  { value: 'base', label: 'Base' },
  { value: 'small', label: 'Small (推荐)' },
  { value: 'medium', label: 'Medium' },
  { value: 'large', label: 'Large (最准)' },
] as const;

export const PAGE_SIZE = 20;
export const WS_RECONNECT_BASE_MS = 1000;
export const WS_RECONNECT_MAX_MS = 30000;
export const WS_MAX_RETRIES = 5;
export const POLLING_INTERVAL_MS = 5000;
