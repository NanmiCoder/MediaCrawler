export interface CrawlerConfig {
  platform: string
  login_type: string
  crawler_type: string
  keywords: string
  specified_ids: string  // 详情模式下的帖子/视频ID
  creator_ids: string    // 创作者模式下的创作者ID
  start_page: number
  enable_comments: boolean
  enable_sub_comments: boolean
  enable_bgm: boolean
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

export interface Platform {
  value: string
  label: string
  icon: string
}

export interface ConfigOption {
  value: string
  label: string
}

// 爬取运行历史记录
export interface RunRecord {
  run_id: string
  platform: string | null
  crawler_type: string | null
  save_option: string | null
  keywords: string | null
  started_at: string | null
  ended_at: string | null
  status: 'running' | 'success' | 'failed' | 'stopped'
  exit_code: number | null
  record_count: number | null
  error_message: string | null
}

// 清除历史数据请求
export interface ClearHistoryRequest {
  clear_files: boolean
  clear_db: boolean
  clear_runs: boolean
  platform?: string | null
}

// BGM 播放清单曲目（带 run 分组字段）
export interface BgmTrack {
  aweme_id: string
  music_title: string
  music_author: string
  music_duration: number
  aweme_url: string
  has_local: boolean
  run_id: string
  keyword: string
  add_ts: number
}

// BGM 按 run 分组
export interface BgmRunGroup {
  run_id: string
  keyword: string
  started_at: string | null
  crawler_type: string | null
  status: string | null
  track_count: number
  comment_count: number
  tracks: BgmTrack[]
}

// 评论条目
export interface CommentTrack {
  comment_id: string
  aweme_id: string
  nickname: string
  content: string
  like_count: number
  create_time: number | null
  sub_comment_count: number
  run_id: string
}

// 评论按 run 分组
export interface CommentRunGroup {
  run_id: string
  keyword: string
  started_at: string | null
  crawler_type: string | null
  status: string | null
  track_count: number
  comment_count: number
  comments: CommentTrack[]
}
