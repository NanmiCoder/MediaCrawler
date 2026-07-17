import { useTranslation } from 'react-i18next'
import { MessageSquare, Loader2 } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { useCommentsPlaylist } from '@/hooks/useComments'
import { CommentRunGroupCard } from './CommentRunGroupCard'

export function CommentsView() {
  const { t } = useTranslation('comments')
  const { data: groups, isLoading } = useCommentsPlaylist()

  const totalCount = (groups ?? []).reduce((sum, g) => sum + (g.comment_count ?? 0), 0)

  return (
    <div className="h-full flex flex-col gap-3">
      {/* 标题栏 */}
      <div className="flex items-center justify-between flex-shrink-0">
        <div className="flex items-center gap-2">
          <MessageSquare className="w-5 h-5 text-cyber-neon-cyan" />
          <h2 className="font-mono font-bold text-cyber-text-primary tracking-wider text-sm">
            {t('title')}
          </h2>
          {totalCount > 0 && (
            <Badge variant="outline" className="text-[10px] font-mono">
              {t('commentCount', { count: totalCount })}
            </Badge>
          )}
        </div>
      </div>

      {/* 按 run 分组列表 */}
      <ScrollArea className="flex-1 min-h-0">
        {isLoading ? (
          <div className="flex items-center justify-center h-32">
            <Loader2 className="w-5 h-5 text-cyber-neon-cyan animate-spin" />
          </div>
        ) : !groups || groups.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-64 text-center">
            <MessageSquare className="w-10 h-10 text-cyber-text-muted/40 mb-3" />
            <p className="text-sm font-mono text-cyber-text-muted">{t('empty')}</p>
            <p className="text-xs font-mono text-cyber-text-muted/60 mt-1">{t('emptyHint')}</p>
          </div>
        ) : (
          <div className="space-y-3 pr-2">
            {groups.map((group) => (
              <CommentRunGroupCard key={group.run_id} group={group} />
            ))}
          </div>
        )}
      </ScrollArea>
    </div>
  )
}
