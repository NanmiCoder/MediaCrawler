import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  ChevronDown, ChevronRight, ExternalLink, Heart, MessageCircle,
} from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import type { CommentRunGroup } from '@/types/crawler'

type Props = {
  group: CommentRunGroup
}

function formatDateTime(iso: string | null): string {
  if (!iso) return ''
  const d = new Date(iso)
  if (isNaN(d.getTime())) return iso
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function formatCreateTime(ts: number | null): string {
  if (!ts || ts <= 0) return '-'
  // 抖音 create_time 是秒级时间戳
  const d = new Date(ts * 1000)
  if (isNaN(d.getTime())) return '-'
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

const STATUS_COLOR: Record<string, string> = {
  running: 'text-cyber-neon-cyan border-cyber-neon-cyan/30 bg-cyber-neon-cyan/10',
  success: 'text-cyber-neon-green border-cyber-neon-green/30 bg-cyber-neon-green/10',
  failed: 'text-cyber-neon-pink border-cyber-neon-pink/30 bg-cyber-neon-pink/10',
  stopped: 'text-cyber-text-muted border-cyber-border-DEFAULT bg-cyber-bg-tertiary',
  historical: 'text-cyber-text-muted border-cyber-border-subtle bg-cyber-bg-tertiary/50',
}

export function CommentRunGroupCard({ group }: Props) {
  const { t } = useTranslation('comments')

  const [collapsed, setCollapsed] = useState(false)

  const isUnattributed = group.run_id === 'unattributed'
  const statusKey = group.status === 'historical' ? 'historical' : group.status ?? ''
  const statusText = group.status === 'historical'
    ? t('unattributed')
    : (group.status ?? '')

  return (
    <div className="border border-cyber-border-subtle rounded-lg overflow-hidden bg-cyber-bg-tertiary/40">
      {/* 分组 header：可折叠 */}
      <button
        type="button"
        onClick={() => setCollapsed((c) => !c)}
        className="w-full flex items-center gap-3 px-3 py-2 hover:bg-cyber-bg-elevated/50 transition-colors text-left"
      >
        {collapsed ? (
          <ChevronRight className="w-4 h-4 text-cyber-text-muted flex-shrink-0" />
        ) : (
          <ChevronDown className="w-4 h-4 text-cyber-text-muted flex-shrink-0" />
        )}
        <div className="flex-1 min-w-0 flex items-center gap-2 flex-wrap">
          <span className="text-sm font-mono font-semibold text-cyber-text-primary truncate">
            {group.keyword || t('unattributed')}
          </span>
          {statusText && (
            <Badge
              variant="outline"
              className={`text-[9px] font-mono ${STATUS_COLOR[statusKey] ?? ''}`}
            >
              {statusText}
            </Badge>
          )}
          {!isUnattributed && group.started_at && (
            <span className="text-[10px] font-mono text-cyber-text-muted">
              {formatDateTime(group.started_at)}
            </span>
          )}
        </div>
        <Badge variant="outline" className="text-[10px] font-mono text-cyber-neon-cyan flex-shrink-0">
          {t('commentCount', { count: group.comment_count })}
        </Badge>
      </button>

      {/* 评论列表 */}
      {!collapsed && (
        <div className="space-y-1.5 px-2 pb-2">
          {group.comments.map((comment) => (
            <div
              key={comment.comment_id}
              className="relative overflow-hidden card-scan group transition-all border border-cyber-border-subtle hover:border-cyber-neon-cyan/30 rounded-md"
            >
              <div className="absolute inset-0 bg-gradient-to-r from-transparent via-cyber-neon-cyan/5 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-700 pointer-events-none" />
              <div className="p-2.5 relative">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs font-mono font-semibold text-cyber-neon-cyan truncate" title={comment.nickname}>
                    {comment.nickname || t('nickname')}
                  </span>
                  {comment.sub_comment_count > 0 && (
                    <span className="inline-flex items-center gap-0.5 text-[10px] font-mono text-cyber-text-muted">
                      <MessageCircle className="w-2.5 h-2.5" />
                      {comment.sub_comment_count}
                    </span>
                  )}
                  <span className="text-[10px] font-mono text-cyber-text-muted ml-auto">
                    {formatCreateTime(comment.create_time)}
                  </span>
                </div>
                <p className="text-xs font-mono text-cyber-text-primary break-words whitespace-pre-wrap leading-relaxed">
                  {comment.content}
                </p>
                <div className="flex items-center justify-between mt-1.5">
                  <span className="inline-flex items-center gap-1 text-[10px] font-mono text-cyber-text-secondary">
                    <Heart className="w-2.5 h-2.5 text-cyber-neon-pink/70" />
                    {comment.like_count ?? 0}
                  </span>
                  {comment.aweme_id && (
                    <a
                      href={`https://www.douyin.com/video/${comment.aweme_id}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 text-[10px] font-mono text-cyber-text-muted hover:text-cyber-neon-cyan transition-colors"
                      title={t('viewOriginal')}
                    >
                      <ExternalLink className="w-2.5 h-2.5" />
                      {t('viewOriginal')}
                    </a>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
