import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Music, Loader2, Music2 } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { useBgmPlaylist, useBgmTags } from '@/hooks/useBgm'
import { BgmRunGroupCard } from './BgmRunGroupCard'
import type { BgmTrack } from '@/types/crawler'

function formatDuration(sec: number): string {
  if (!sec || sec <= 0) return '--:--'
  const m = Math.floor(sec / 60)
  const s = Math.floor(sec % 60)
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
}

export function BgmPlayer() {
  const { t } = useTranslation('bgm')
  const [activeId, setActiveId] = useState<string | null>(null)
  const [isPlaying, setIsPlaying] = useState(false)

  const { data, isLoading } = useBgmPlaylist()
  const groups = data?.groups ?? []
  // 场景标签映射（供卡片显示/编辑）
  useBgmTags()

  const tracks: BgmTrack[] = data?.tracks ?? []
  const activeTrack = tracks.find((tr) => tr.aweme_id === activeId) ?? null

  const handleToggle = (awemeId: string, hasLocal: boolean) => {
    if (!hasLocal) return
    if (activeId === awemeId) {
      setIsPlaying((p) => !p)
    } else {
      setActiveId(awemeId)
      setIsPlaying(true)
    }
  }

  const totalTracks = tracks.length

  return (
    <div className="h-full flex flex-col gap-3">
      {/* 标题栏 */}
      <div className="flex items-center justify-between flex-shrink-0">
        <div className="flex items-center gap-2">
          <Music className="w-5 h-5 text-cyber-neon-cyan" />
          <h2 className="font-mono font-bold text-cyber-text-primary tracking-wider text-sm">
            {t('title')}
          </h2>
          {totalTracks > 0 && (
            <Badge variant="outline" className="text-[10px] font-mono">
              {t('tracks', { count: totalTracks })}
            </Badge>
          )}
        </div>
      </div>

      {/* 粘性播放器 */}
      {activeTrack && (
        <div className="flex-shrink-0 glass-panel float-panel rounded-lg p-3 border border-cyber-neon-cyan/30">
          <div className="flex items-center gap-2 mb-2">
            <Music2 className="w-4 h-4 text-cyber-neon-cyan animate-pulse" />
            <span className="text-[10px] font-mono text-cyber-neon-cyan uppercase tracking-wider">
              {t('nowPlaying')}
            </span>
            <span className="text-xs font-mono text-cyber-text-primary truncate flex-1" title={activeTrack.music_title}>
              {activeTrack.music_title || '-'}
            </span>
            <span className="text-xs font-mono text-cyber-text-muted">
              {activeTrack.music_author || '-'}
            </span>
            <span className="text-xs font-mono text-cyber-text-secondary">
              {formatDuration(activeTrack.music_duration)}
            </span>
          </div>
          <audio
            key={activeTrack.aweme_id}
            src={`/api/data/bgm/${activeTrack.aweme_id}`}
            controls
            autoPlay
            preload="metadata"
            className="w-full h-9"
            onPlay={() => setIsPlaying(true)}
            onPause={() => setIsPlaying(false)}
          />
        </div>
      )}

      {/* 按 run 分组列表 */}
      <ScrollArea className="flex-1 min-h-0">
        {isLoading ? (
          <div className="flex items-center justify-center h-32">
            <Loader2 className="w-5 h-5 text-cyber-neon-cyan animate-spin" />
          </div>
        ) : groups.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-64 text-center">
            <Music className="w-10 h-10 text-cyber-text-muted/40 mb-3" />
            <p className="text-sm font-mono text-cyber-text-muted">{t('empty')}</p>
            <p className="text-xs font-mono text-cyber-text-muted/60 mt-1">{t('emptyHint')}</p>
          </div>
        ) : (
          <div className="space-y-3 pr-2">
            {groups.map((group) => (
              <BgmRunGroupCard
                key={group.run_id}
                group={group}
                activeId={activeId}
                isPlaying={isPlaying}
                onToggle={handleToggle}
              />
            ))}
          </div>
        )}
      </ScrollArea>
    </div>
  )
}

export { formatDuration }
