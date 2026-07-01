export interface TaskInfo {
  task_id: string;
  task_type: string;
  workspace: string;
  params: Record<string, any>;
  status: 'pending' | 'running' | 'completed' | 'failed';
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  error: string | null;
  exit_code: number;
  result: Record<string, any> | null;
  progress: string;
}

export interface TaskStats {
  total: number;
  pending: number;
  running: number;
  completed: number;
  failed: number;
}

export interface TaskListResponse {
  tasks: TaskInfo[];
  total: number;
  offset: number;
  limit: number;
  stats: TaskStats;
}

export interface CreateTaskResponse {
  task_id: string;
  status: string;
  type: string;
}

export interface HealthResponse {
  status: 'healthy' | 'degraded' | 'unhealthy';
  uptime_seconds: number;
  checks: {
    chrome_cdp: { status: string; detail?: string };
    disk: { status: string; available_gb?: number; detail?: string };
    ffmpeg: { status: string; detail?: string };
  };
  system: Record<string, any>;
  tasks: TaskStats;
}

export interface WSTaskEvent {
  type: 'task_created' | 'task_started' | 'task_progress' | 'task_completed' | 'task_failed';
  task_id: string;
  status: string;
  progress?: string;
  result?: Record<string, any>;
  error?: string;
  timestamp: string;
}

export interface WSLogMessage {
  type: 'log';
  data: {
    id?: number;
    timestamp?: string;
    level?: string;
    message?: string;
  };
}

export type WSMessage = WSTaskEvent | WSLogMessage;

export interface SearchParams {
  keywords: string[];
  max_count?: number;
  project_dir?: string;
}

export interface CommentsParams {
  video_jsonl?: string;
  project_dir?: string;
}

export interface ScriptsParams {
  video_jsonl?: string;
  model?: string;
  project_dir?: string;
}

export interface MergeParams {
  video_jsonl?: string;
  comments_jsonl?: string;
  scripts_jsonl?: string;
  output_csv?: string;
  project_dir?: string;
}

export interface RunAllParams {
  keywords: string[];
  max_count?: number;
  steps?: string[];
  project_dir?: string;
}

// ─── 数据管理 ───────────────────────────────────────────────

export interface DataFileItem {
  task_id: string;
  task_type: string;
  file_name: string;
  file_path: string;
  file_size: number;
  row_count: number;
  created_at: string;
  keywords: string[];
}

export interface DataListResponse {
  items: DataFileItem[];
  total: number;
}

export interface DataPreviewResponse {
  task_id: string;
  file_name: string;
  format?: 'csv' | 'jsonl' | string;
  rows: Record<string, string>[];
  total_rows: number;
}

export interface ExportRequest {
  task_ids: string[];
  format: 'csv' | 'txt';
  limit?: number;
}
