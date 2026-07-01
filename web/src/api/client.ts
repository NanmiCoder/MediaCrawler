import ky, { type KyInstance } from 'ky';
import {
  DEFAULT_API_BASE, API_KEY_HEADER, API_KEY_STORAGE_KEY,
} from '../utils/constants';
import type {
  TaskListResponse, TaskInfo, CreateTaskResponse, HealthResponse,
  SearchParams, CommentsParams, ScriptsParams, MergeParams, RunAllParams,
  DataListResponse, DataPreviewResponse, ExportRequest,
} from './types';

function getApiKey(): string {
  return localStorage.getItem(API_KEY_STORAGE_KEY) || '';
}

function createApiClient(baseUrl?: string): KyInstance {
  const base = baseUrl || DEFAULT_API_BASE;
  return ky.create({
    prefixUrl: base,
    hooks: {
      beforeRequest: [
        (request) => {
          const key = getApiKey();
          if (key) {
            request.headers.set(API_KEY_HEADER, key);
          }
        },
      ],
    },
    timeout: 30_000,
  });
}

let _client: KyInstance | null = null;

function getDownloadFilename(disposition: string, fallback: string): string {
  const encoded = disposition.match(/filename\*=utf-8''([^;]+)/i);
  if (encoded) {
    try {
      return decodeURIComponent(encoded[1]);
    } catch {
      return encoded[1];
    }
  }
  const plain = disposition.match(/filename="?([^";]+)"?/i);
  return plain?.[1] || fallback;
}

async function downloadAuthenticatedFile(path: string, fallback: string): Promise<void> {
  const resp = await getClient().get(path, { timeout: false });
  const blob = await resp.blob();
  const filename = getDownloadFilename(
    resp.headers.get('content-disposition') || '',
    fallback,
  );
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  setTimeout(() => {
    document.body.removeChild(anchor);
    URL.revokeObjectURL(url);
  }, 100);
}

export function getClient(): KyInstance {
  if (!_client) {
    _client = createApiClient();
  }
  return _client;
}

export function resetClient(baseUrl?: string): void {
  _client = createApiClient(baseUrl);
}

export const api = {
  getHealth: () =>
    getClient().get('health').json<HealthResponse>(),

  listTasks: (params?: { task_type?: string; status?: string; limit?: number; offset?: number }) => {
    const searchParams: Record<string, string | number> = {};
    if (params?.task_type) searchParams.task_type = params.task_type;
    if (params?.status) searchParams.status = params.status;
    if (params?.limit) searchParams.limit = params.limit;
    if (params?.offset) searchParams.offset = params.offset;
    return getClient().get('scrape/tasks', { searchParams }).json<TaskListResponse>();
  },

  getTaskStatus: (taskId: string) =>
    getClient().get(`scrape/status/${taskId}`).json<TaskInfo>(),

  deleteTask: (taskId: string) =>
    getClient().delete(`scrape/tasks/${taskId}`).json(),

  cleanupTasks: (maxAgeHours = 72) =>
    getClient().post('scrape/cleanup', { searchParams: { max_age_hours: maxAgeHours } }).json<{ removed: number; remaining: number }>(),

  resetStep: (data: { step: string; clear_dedupe?: boolean; project_dir?: string }) =>
    getClient().post('scrape/reset', { json: data }).json(),

  createSearch: (data: SearchParams) =>
    getClient().post('scrape/search', { json: data }).json<CreateTaskResponse>(),

  createComments: (data: CommentsParams) =>
    getClient().post('scrape/comments', { json: data }).json<CreateTaskResponse>(),

  createScripts: (data: ScriptsParams) =>
    getClient().post('scrape/scripts', { json: data }).json<CreateTaskResponse>(),

  createMerge: (data: MergeParams) =>
    getClient().post('scrape/merge', { json: data }).json<CreateTaskResponse>(),

  createRunAll: (data: RunAllParams) =>
    getClient().post('scrape/run-all', { json: data }).json<CreateTaskResponse>(),

  downloadResult: (taskId: string) =>
    downloadAuthenticatedFile(
      `scrape/result/${taskId}`,
      `${taskId}-result`,
    ),

  downloadDataFile: (taskId: string) =>
    downloadAuthenticatedFile(
      `scrape/data/export?task_id=${encodeURIComponent(taskId)}`,
      `${taskId}-data`,
    ),

  // ─── 数据管理 ───────────────────────────────────────────────

  listDataFiles: () =>
    getClient().get('scrape/data/list').json<DataListResponse>(),

  previewData: (taskId: string, limit?: number) =>
    getClient().get(`scrape/data/preview/${taskId}`, {
      searchParams: limit ? { limit } : undefined,
    }).json<DataPreviewResponse>(),

  /** 导出数据，返回 Blob 供前端触发下载 */
  exportData: async (req: ExportRequest): Promise<{ blob: Blob; filename: string }> => {
    const resp = await getClient().post('scrape/data/export', { json: req });
    const blob = await resp.blob();
    const disposition = resp.headers.get('content-disposition') || '';
    const match = disposition.match(/filename="?([^"]+)"?/);
    const filename = match ? match[1] : `export.${req.format}`;
    return { blob, filename };
  },
};
