import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Play, Pause, ChevronDown, ChevronRight, Trash2, Tag, ExternalLink, Loader2 } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
  DialogClose,
} from '@/components/ui/dialog'
import { useBgmTags, useDeleteBgm, useUpdateBgmScene } from '@/hooks/useBgm'
import { formatDuration } from './BgmPlayer'
import type { BgmRunGroup } from '@/types/crawler'

type Props = {
  group: BgmRunGroup
  activeId: string | null
  isPlaying: boolean
  onToggle: (awemeId: string, hasLocal: boolean) => void
}

function formatDateTime(iso: string | null): string {
  if (!iso) return ''
  const d = new Date(iso)
  if (isNaN(d.getTime())) return iso
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

export function BgmRunGroupCard({ group, activeId, isPlaying, onToggle }: Props) {
  const { t } = useTranslation('bgm')
  const { data: tags } = useBgmTags()
  const deleteBgm = useDeleteBgm()
  const updateScene = useUpdateBgmScene()

  const [collapsed, setCollapsed] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null)
  const [sceneTarget, setSceneTarget] = useState<{ awemeId: string; current: string } | null>(null)
  const [sceneInput, setSceneInput] = useState('')

  const isUnattributed = group.run_id === 'unattributed'
  const statusText = group.status === 'historical'
    ? t('unattributed')
    : group.status ?? ''

  const handleOpenScene = (awemeId: string) => {
    const current = tags?.[awemeId] ?? ''
    setSceneInput(current)
    setSceneTarget({ awemeId, current })
  }

  const handleSaveScene = () => {
    if (!sceneTarget) return
    updateScene.mutate({ awemeId: sceneTarget.awemeId, scene: sceneInput.trim() })
    setSceneTarget(null)
  }

  const handleConfirmDelete = () => {
    if (!deleteTarget) return
    deleteBgm.mutate({ awemeId: deleteTarget, deleteAudio: true }, {
      onSuccess: () => setDeleteTarget(null),
    })
  }

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
            <Badge variant="outline" className="text-[9px] font-mono text-cyber-text-muted">
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
          {t('trackCount', { count: group.track_count })}
        </Badge>
      </button>

      {/* 曲目列表 */}
      {!collapsed && (
        <div className="space-y-1.5 px-2 pb-2">
          {group.tracks.map((track) => {
            const isActive = track.aweme_id === activeId
            const scene = tags?.[track.aweme_id] ?? ''
            const sceneLabel = scene || track.keyword || ''
            return (
              <div
                key={track.aweme_id}
                className={`relative overflow-hidden card-scan group transition-all border rounded-md ${
                  isActive
                    ? 'border-cyber-neon-cyan/50 bg-cyber-neon-cyan/5'
                    : 'border-cyber-border-subtle hover:border-cyber-neon-cyan/30'
                }`}
              >
                <div className="absolute inset-0 bg-gradient-to-r from-transparent via-cyber-neon-cyan/5 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-700 pointer-events-none" />
                <div className="p-2.5 relative flex items-center gap-2.5">
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    disabled={!track.has_local}
                    onClick={() => onToggle(track.aweme_id, track.has_local)}
                    className={`h-8 w-8 p-0 flex-shrink-0 ${
                      track.has_local
                        ? 'text-cyber-neon-cyan hover:bg-cyber-neon-cyan/10'
                        : 'text-cyber-text-muted/40 cursor-not-allowed'
                    }`}
                    title={track.has_local ? t('play') : t('noLocal')}
                  >
                    {isActive && isPlaying ? (
                      <Pause className="w-3.5 h-3.5" />
                    ) : (
                      <Play className="w-3.5 h-3.5" />
                    )}
                  </Button>
                  <div className="flex-1 min-w-0">
                    <div className="text-xs font-mono text-cyber-text-primary truncate" title={track.music_title}>
                      {track.music_title || t('track')}
                    </div>
                    <div className="text-[10px] font-mono text-cyber-text-muted truncate">
                      {track.music_author || '-'}
                    </div>
                  </div>
                  <div className="flex items-center gap-1.5 flex-shrink-0">
                    {/* 场景标签：点击编辑 */}
                    <button
                      type="button"
                      onClick={() => handleOpenScene(track.aweme_id)}
                      className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[9px] font-mono border transition-colors ${
                        scene
                          ? 'border-cyber-neon-green/40 bg-cyber-neon-green/10 text-cyber-neon-green'
                          : 'border-cyber-border-subtle text-cyber-text-muted hover:border-cyber-neon-cyan/40 hover:text-cyber-neon-cyan'
                      }`}
                      title={t('sceneEdit')}
                    >
                      <Tag className="w-2.5 h-2.5" />
                      {scene || (sceneLabel ? `${t('scene')}: ${track.keyword}` : t('sceneDefault'))}
                    </button>
                    <span className="text-[10px] font-mono text-cyber-text-secondary">
                      {formatDuration(track.music_duration)}
                    </span>
                    {track.aweme_url && (
                      <a
                        href={track.aweme_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-cyber-text-muted hover:text-cyber-neon-cyan transition-colors"
                        title={t('openSource')}
                      >
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    )}
                    {/* 删除按钮 */}
                    <button
                      type="button"
                      onClick={() => setDeleteTarget(track.aweme_id)}
                      className="text-cyber-text-muted hover:text-cyber-neon-pink transition-colors"
                      title={t('delete')}
                    >
                      <Trash2 className="w-3 h-3" />
                    </button>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* 删除确认 Dialog */}
      <Dialog open={deleteTarget !== null} onOpenChange={(o) => !o && setDeleteTarget(null)}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>{t('delete')}</DialogTitle>
          </DialogHeader>
          <p className="text-xs font-mono text-cyber-text-secondary">
            {t('deleteConfirm', { audio: t('deleteAudioSuffix') })}
          </p>
          <DialogFooter className="gap-2">
            <DialogClose asChild>
              <Button variant="ghost" size="sm" className="font-mono text-xs">{t('cancel')}</Button>
            </DialogClose>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleConfirmDelete}
              disabled={deleteBgm.isPending}
              className="font-mono text-xs text-cyber-neon-pink hover:bg-cyber-neon-pink/10"
            >
              {deleteBgm.isPending ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : t('delete')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 场景标签编辑 Dialog */}
      <Dialog open={sceneTarget !== null} onOpenChange={(o) => !o && setSceneTarget(null)}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>{t('sceneEdit')}</DialogTitle>
          </DialogHeader>
          <Input
            value={sceneInput}
            onChange={(e) => setSceneInput(e.target.value)}
            placeholder={t('scenePlaceholder')}
            className="font-mono text-xs"
            autoFocus
          />
          <DialogFooter className="gap-2">
            {sceneTarget?.current && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  setSceneInput('')
                  // 直接调 mutate 清除（空字符串后端会删键）
                  if (sceneTarget) {
                    updateScene.mutate({ awemeId: sceneTarget.awemeId, scene: '' })
                    setSceneTarget(null)
                  }
                }}
                className="font-mono text-xs text-cyber-text-muted hover:text-cyber-neon-pink"
              >
                {t('deleteScene')}
              </Button>
            )}
            <DialogClose asChild>
              <Button variant="ghost" size="sm" className="font-mono text-xs">{t('cancel')}</Button>
            </DialogClose>
            <Button
              size="sm"
              onClick={handleSaveScene}
              disabled={updateScene.isPending}
              className="font-mono text-xs bg-cyber-neon-cyan/20 text-cyber-neon-cyan hover:bg-cyber-neon-cyan/30"
            >
              {t('save')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
