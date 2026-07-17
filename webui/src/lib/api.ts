import axios from 'axios'
import type { RunRecord, ClearHistoryRequest, BgmTrack, BgmRunGroup, CommentRunGroup } from '@/types/crawler'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Types
export interface CrawlerConfig {
  platform: string
  login_type: string
  crawler_type: string
  keywords: string
  start_page: number
  enable_comments: boolean
  enable_sub_comments: boolean
  save_option: string
  cookies: string
  headless: boolean
}

export interface CrawlerStatus {
  status: 'idle' | 'running' | 'stopping' | 'error'
  platform: string | null
  crawler_type: string | null
  started_at: string | null
  error_message: string | null
}

export interface LogEntry {
  id: number
  timestamp: string
  level: 'info' | 'warning' | 'error' | 'success' | 'debug'
  message: string
}

export interface DataFile {
  name: string
  path: string
  size: number
  modified_at: number
  record_count: number | null
  type: string
}

export interface FilePreviewResponse {
  data: Record<string, unknown>[]
  total: number
  columns?: string[]
}

export interface Platform {
  value: string
  label: string
  icon: string
}

export interface ConfigOption {
  value: string
  label: string
}

// API functions
export const crawlerApi = {
  start: (config: CrawlerConfig) => api.post('/crawler/start', config),
  stop: () => api.post('/crawler/stop'),
  getStatus: () => api.get<CrawlerStatus>('/crawler/status'),
  getLogs: (limit = 100) => api.get<{ logs: LogEntry[] }>('/crawler/logs', { params: { limit } }),
  getHistory: (limit = 50) =>
    api.get<{ runs: RunRecord[] }>('/crawler/history', { params: { limit } }),
  clearHistory: (payload: ClearHistoryRequest) =>
    api.delete<{ deleted_files: number; truncated_tables: string[]; cleared_runs: boolean }>(
      '/crawler/history',
      { data: payload },
    ),
}

export const dataApi = {
  getFiles: (platform?: string, fileType?: string) =>
    api.get<{ files: DataFile[] }>('/data/files', { params: { platform, file_type: fileType } }),
  getFileContent: (path: string, limit = 100) =>
    api.get<FilePreviewResponse>('/data/files/' + path, { params: { preview: true, limit } }),
  getStats: () => api.get('/data/stats'),
  getDownloadUrl: (path: string) => `/api/data/download/${path}`,
  getBgmPlaylist: (runId?: string) =>
    api.get<{ tracks: BgmTrack[]; groups: BgmRunGroup[] }>('/data/bgm/playlist', {
      params: { run_id: runId },
    }),
  getBgmStreamUrl: (awemeId: string) => `/api/data/bgm/${awemeId}`,
  deleteBgm: (awemeId: string, deleteAudio = false) =>
    api.delete<{ removed_rows: number; audio_deleted: boolean }>(
      `/data/bgm/${awemeId}`,
      { params: { delete_audio: deleteAudio } },
    ),
  getBgmTags: () => api.get<{ tags: Record<string, string> }>('/data/bgm/tags'),
  updateBgmScene: (awemeId: string, scene: string) =>
    api.put(`/data/bgm/scene/${awemeId}`, { scene }),
  getCommentsPlaylist: (runId?: string) =>
    api.get<{ groups: CommentRunGroup[] }>('/data/comments/playlist', {
      params: { run_id: runId },
    }),
}

export const configApi = {
  getPlatforms: () => api.get<{ platforms: Platform[] }>('/config/platforms'),
  getOptions: () =>
    api.get<{
      login_types: ConfigOption[]
      crawler_types: ConfigOption[]
      save_options: ConfigOption[]
    }>('/config/options'),
}

export interface EnvCheckResult {
  success: boolean
  message: string
  output?: string
  error?: string
}

export const envApi = {
  check: () => api.get<EnvCheckResult>('/env/check'),
}

export default api
