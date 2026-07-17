import { useTranslation } from 'react-i18next'
import { Activity, CheckCircle2, XCircle, Square } from 'lucide-react'
import type { RunRecord } from '@/types/crawler'

// 平台短名 → 显示名
const PLATFORM_LABEL: Record<string, string> = {
  dy: '抖音', xhs: '小红书', ks: '快手', bili: '哔哩哔哩',
  wb: '微博', tieba: '贴吧', zhihu: '知乎',
}

// 爬取类型短名 → 显示名
const CRAWLER_TYPE_LABEL: Record<string, string> = {
  search: '搜索', detail: '详情', creator: '创作者',
}

interface RunRowProps {
  run: RunRecord
}

function formatDuration(startedAt: string | null, endedAt: string | null, t: (k: string, o?: any) => string): string {
  if (!startedAt || !endedAt) return '-'
  const start = new Date(startedAt).getTime()
  const end = new Date(endedAt).getTime()
  if (isNaN(start) || isNaN(end) || end < start) return '-'
  const totalSec = Math.floor((end - start) / 1000)
  const min = Math.floor(totalSec / 60)
  const sec = totalSec % 60
  if (min > 0) return t('durationMinutes', { min, sec })
  return t('durationSeconds', { sec })
}

function formatDateTime(iso: string | null): string {
  if (!iso) return '-'
  const d = new Date(iso)
  if (isNaN(d.getTime())) return iso
  // YYYY-MM-DD HH:mm:ss
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

export function RunRow({ run }: RunRowProps) {
  const { t } = useTranslation('history')

  const statusConfig = {
    running: {
      icon: Activity,
      color: 'text-cyber-neon-cyan',
      border: 'border-cyber-neon-cyan/30',
      bg: 'bg-cyber-neon-cyan/10',
    },
    success: {
      icon: CheckCircle2,
      color: 'text-cyber-neon-green',
      border: 'border-cyber-neon-green/30',
      bg: 'bg-cyber-neon-green/10',
    },
    failed: {
      icon: XCircle,
      color: 'text-cyber-neon-pink',
      border: 'border-cyber-neon-pink/30',
      bg: 'bg-cyber-neon-pink/10',
    },
    stopped: {
      icon: Square,
      color: 'text-cyber-text-muted',
      border: 'border-cyber-border-DEFAULT',
      bg: 'bg-cyber-bg-tertiary',
    },
  }[run.status]

  const StatusIcon = statusConfig.icon

  return (
    <div className={`relative overflow-hidden card-scan group transition-all border ${statusConfig.border} ${statusConfig.bg} rounded-lg`}>
      <div className="absolute inset-0 bg-gradient-to-r from-transparent via-cyber-neon-cyan/5 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-700 pointer-events-none" />
      <div className="p-3 relative">
        <div className="flex items-center gap-4 flex-wrap">
          {/* 平台 */}
          <div className="flex-shrink-0 min-w-[80px]">
            <div className="text-[10px] text-cyber-text-muted font-mono uppercase">
              {t('column.platform')}
            </div>
            <div className="text-sm font-mono text-cyber-text-primary font-semibold">
              {run.platform ? (PLATFORM_LABEL[run.platform] || run.platform) : '-'}
            </div>
          </div>

          {/* 爬取类型 */}
          <div className="flex-shrink-0 min-w-[80px]">
            <div className="text-[10px] text-cyber-text-muted font-mono uppercase">
              {t('column.type')}
            </div>
            <div className="text-sm font-mono text-cyber-text-primary">
              {run.crawler_type ? (CRAWLER_TYPE_LABEL[run.crawler_type] || run.crawler_type) : '-'}
            </div>
          </div>

          {/* 状态 */}
          <div className="flex-shrink-0 min-w-[90px]">
            <div className="text-[10px] text-cyber-text-muted font-mono uppercase">
              {t('column.status')}
            </div>
            <div className={`flex items-center gap-1.5 text-sm font-mono font-semibold ${statusConfig.color}`}>
              {run.status === 'running' && <Activity className="w-3.5 h-3.5 animate-pulse" />}
              {run.status !== 'running' && <StatusIcon className="w-3.5 h-3.5" />}
              {t(`status.${run.status}`)}
            </div>
          </div>

          {/* 开始时间 */}
          <div className="flex-shrink-0 min-w-[160px]">
            <div className="text-[10px] text-cyber-text-muted font-mono uppercase">
              {t('column.startedAt')}
            </div>
            <div className="text-xs font-mono text-cyber-text-secondary">
              {formatDateTime(run.started_at)}
            </div>
          </div>

          {/* 时长 */}
          <div className="flex-shrink-0 min-w-[80px]">
            <div className="text-[10px] text-cyber-text-muted font-mono uppercase">
              {t('column.duration')}
            </div>
            <div className="text-xs font-mono text-cyber-text-secondary">
              {formatDuration(run.started_at, run.ended_at, t)}
            </div>
          </div>

          {/* 条数 */}
          <div className="flex-shrink-0 min-w-[70px]">
            <div className="text-[10px] text-cyber-text-muted font-mono uppercase">
              {t('column.records')}
            </div>
            <div className="text-sm font-mono text-cyber-neon-green font-semibold">
              {run.record_count ?? '-'}
            </div>
          </div>

          {/* 关键词 */}
          <div className="flex-1 min-w-[120px]">
            <div className="text-[10px] text-cyber-text-muted font-mono uppercase">
              {t('column.keywords')}
            </div>
            <div className="text-xs font-mono text-cyber-text-secondary truncate" title={run.keywords || ''}>
              {run.keywords || '-'}
            </div>
          </div>
        </div>

        {/* 错误信息 */}
        {run.error_message && (
          <div className="mt-2 pt-2 border-t border-cyber-border-subtle/50">
            <div className="text-[10px] text-cyber-neon-pink font-mono uppercase">
              {t('column.error')}
            </div>
            <div className="text-xs font-mono text-cyber-neon-pink/90 break-all line-clamp-2">
              {run.error_message}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
