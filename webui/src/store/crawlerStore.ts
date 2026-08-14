import { create } from 'zustand'
import type { LogEntry, CrawlerConfig } from '@/types/crawler'

interface CrawlerState {
  // Status
  status: 'idle' | 'running' | 'stopping' | 'error'
  platform: string | null
  crawlerType: string | null
  startedAt: string | null

  // Logs
  logs: LogEntry[]
  clearedAfterLogId: number | null  // 清除日志后，只显示 id 大于此值的日志

  // Config
  config: CrawlerConfig

  // Actions
  setStatus: (status: CrawlerState['status']) => void
  setRunningInfo: (platform: string | null, crawlerType: string | null, startedAt: string | null) => void
  addLog: (log: LogEntry) => void
  setLogs: (logs: LogEntry[]) => void
  clearLogs: () => void
  restoreLogs: () => void
  updateConfig: (config: Partial<CrawlerConfig>) => void
  saveConfig: () => boolean
  reset: () => void
}

// 持久化相关的 localStorage key
const CLEARED_LOG_ID_KEY = 'mediacrawler_cleared_log_id'
const SAVED_CONFIG_KEY = 'mediacrawler_saved_config'
const MIN_LIMIT = 1
const MAX_LIMIT = 10000

// 从 localStorage 读取清除标记
function getClearedLogIdFromStorage(): number | null {
  const stored = localStorage.getItem(CLEARED_LOG_ID_KEY)
  if (stored === null) return null
  const value = parseInt(stored, 10)
  return isNaN(value) ? null : value
}

// 保存清除标记到 localStorage
function saveClearedLogIdToStorage(id: number | null): void {
  if (id === null) {
    localStorage.removeItem(CLEARED_LOG_ID_KEY)
  } else {
    localStorage.setItem(CLEARED_LOG_ID_KEY, id.toString())
  }
}

const defaultConfig: CrawlerConfig = {
  platform: 'bili',
  login_type: 'qrcode',
  crawler_type: 'search',
  keywords: '',
  specified_ids: '',
  creator_ids: '',
  start_page: 1,
  enable_comments: true,
  enable_sub_comments: false,
  save_option: 'json',
  cookies: '',
  headless: false,
  max_notes_count: 20,
  max_comments_count: 10,
}

function clampInteger(value: unknown, fallback: number, max = MAX_LIMIT): number {
  if (typeof value !== 'number' || !Number.isFinite(value)) return fallback
  return Math.min(max, Math.max(MIN_LIMIT, Math.trunc(value)))
}

function loadSavedConfig(): CrawlerConfig {
  const restored: CrawlerConfig = { ...defaultConfig }
  if (typeof window === 'undefined') return restored

  try {
    const raw = localStorage.getItem(SAVED_CONFIG_KEY)
    if (!raw) return restored

    const saved: unknown = JSON.parse(raw)
    if (!saved || typeof saved !== 'object' || Array.isArray(saved)) return restored
    const value = saved as Record<string, unknown>

    if (typeof value.platform === 'string') restored.platform = value.platform
    if (typeof value.login_type === 'string') restored.login_type = value.login_type
    if (typeof value.crawler_type === 'string') restored.crawler_type = value.crawler_type
    if (typeof value.keywords === 'string') restored.keywords = value.keywords
    if (typeof value.specified_ids === 'string') restored.specified_ids = value.specified_ids
    if (typeof value.creator_ids === 'string') restored.creator_ids = value.creator_ids
    if (typeof value.save_option === 'string') restored.save_option = value.save_option
    if (typeof value.enable_comments === 'boolean') restored.enable_comments = value.enable_comments
    if (typeof value.enable_sub_comments === 'boolean') restored.enable_sub_comments = value.enable_sub_comments
    if (typeof value.headless === 'boolean') restored.headless = value.headless

    restored.start_page = clampInteger(value.start_page, defaultConfig.start_page)
    restored.max_notes_count = clampInteger(value.max_notes_count, defaultConfig.max_notes_count)
    restored.max_comments_count = clampInteger(value.max_comments_count, defaultConfig.max_comments_count)
    restored.enable_sub_comments = restored.enable_comments && restored.enable_sub_comments
    restored.cookies = ''
  } catch {
    return { ...defaultConfig }
  }

  return restored
}

export const useCrawlerStore = create<CrawlerState>((set, get) => ({
  status: 'idle',
  platform: null,
  crawlerType: null,
  startedAt: null,
  logs: [],
  clearedAfterLogId: getClearedLogIdFromStorage(), // 从 localStorage 初始化
  config: loadSavedConfig(),

  setStatus: (status) => {
    set({ status })
    // 当开始新的爬虫任务时，清除之前的清除标记
    if (status === 'running') {
      const currentClearedId = get().clearedAfterLogId
      if (currentClearedId !== null) {
        set({ clearedAfterLogId: null })
        saveClearedLogIdToStorage(null)
      }
    }
  },

  setRunningInfo: (platform, crawlerType, startedAt) => {
    set({ platform, crawlerType, startedAt })
    // 当设置新的运行信息时，也清除之前的清除标记
    if (startedAt !== null) {
      const currentClearedId = get().clearedAfterLogId
      if (currentClearedId !== null) {
        set({ clearedAfterLogId: null })
        saveClearedLogIdToStorage(null)
      }
    }
  },

  addLog: (log) => {
    const { clearedAfterLogId, logs } = get()
    // 如果有清除标记，过滤掉 id 小于等于该标记的日志
    if (clearedAfterLogId !== null && log.id <= clearedAfterLogId) {
      return
    }
    // 防止 WebSocket 重连/重复连接导致的重复日志
    if (logs.length > 0 && logs[logs.length - 1].id === log.id) {
      return
    }
    if (logs.some((existing) => existing.id === log.id)) {
      return
    }
    set((state) => ({
      logs: [...state.logs.slice(-499), log], // Keep last 500 logs
    }))
  },

  setLogs: (logs) => {
    const { clearedAfterLogId } = get()
    // 如果有清除标记，过滤掉 id 小于等于该标记的日志
    const filteredLogs = clearedAfterLogId !== null
      ? logs.filter((log) => log.id > clearedAfterLogId)
      : logs
    set({ logs: filteredLogs })
  },

  clearLogs: () => {
    const { logs } = get()
    // 记录当前最大的 log id，清除后只显示比这个 id 大的日志
    const maxLogId = logs.length > 0 ? Math.max(...logs.map(l => l.id)) : 0
    set({ logs: [], clearedAfterLogId: maxLogId })
    // 持久化到 localStorage
    saveClearedLogIdToStorage(maxLogId)
  },

  restoreLogs: () => {
    // 清除清除标记，这样下次重新加载日志时就会显示所有日志
    set({ clearedAfterLogId: null })
    saveClearedLogIdToStorage(null)
    // 触发日志重新加载（通过刷新页面或重新连接 WebSocket）
    window.location.reload()
  },

  updateConfig: (config) =>
    set((state) => ({
      config: { ...state.config, ...config },
    })),

  saveConfig: () => {
    if (typeof window === 'undefined') return false

    try {
      const { cookies: _cookies, ...safeConfig } = get().config
      localStorage.setItem(SAVED_CONFIG_KEY, JSON.stringify(safeConfig))
      return true
    } catch {
      return false
    }
  },

  reset: () =>
    set({
      status: 'idle',
      platform: null,
      crawlerType: null,
      startedAt: null,
    }),
}))
