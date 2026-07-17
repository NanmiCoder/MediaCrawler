import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { History, Trash2, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Checkbox } from '@/components/ui/checkbox'
import {
  Dialog, DialogContent, DialogDescription, DialogFooter,
  DialogHeader, DialogTitle, DialogTrigger,
} from '@/components/ui/dialog'
import { ScrollArea } from '@/components/ui/scroll-area'
import { useRunHistory, useClearHistory } from '@/hooks/useCrawler'
import { RunRow } from './RunRow'

export function HistoryView() {
  const { t } = useTranslation('history')
  const { data: runs, isLoading } = useRunHistory()
  const clearMutation = useClearHistory()

  const [dialogOpen, setDialogOpen] = useState(false)
  const [clearFiles, setClearFiles] = useState(true)
  const [clearDb, setClearDb] = useState(false)
  const [clearRuns, setClearRuns] = useState(true)

  const handleClear = () => {
    clearMutation.mutate(
      { clear_files: clearFiles, clear_db: clearDb, clear_runs: clearRuns },
      {
        onSuccess: () => setDialogOpen(false),
      },
    )
  }

  return (
    <div className="h-full flex flex-col gap-3">
      {/* 标题栏 */}
      <div className="flex items-center justify-between flex-shrink-0">
        <div className="flex items-center gap-2">
          <History className="w-5 h-5 text-cyber-neon-cyan" />
          <h2 className="font-mono font-bold text-cyber-text-primary tracking-wider text-sm">
            {t('title')}
          </h2>
          {runs && runs.length > 0 && (
            <Badge variant="outline" className="text-[10px] font-mono">
              {runs.length}
            </Badge>
          )}
        </div>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger asChild>
            <Button
              variant="outline"
              size="sm"
              className="h-8 font-mono text-xs border-cyber-neon-pink/40 text-cyber-neon-pink hover:text-cyber-neon-pink hover:bg-cyber-neon-pink/10"
              disabled={clearMutation.isPending}
            >
              <Trash2 className="w-3.5 h-3.5 mr-1" />
              {t('clear')}
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle className="font-mono text-cyber-neon-pink">
                {t('clearConfirm')}
              </DialogTitle>
              <DialogDescription className="font-mono text-cyber-text-muted">
                {t('clearHint')}
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-3 py-2">
              <label className="flex items-center gap-3 cursor-pointer">
                <Checkbox checked={clearFiles} onCheckedChange={(v) => setClearFiles(Boolean(v))} />
                <span className="text-sm font-mono text-cyber-text-primary">{t('clearFiles')}</span>
              </label>
              <label className="flex items-center gap-3 cursor-pointer">
                <Checkbox checked={clearDb} onCheckedChange={(v) => setClearDb(Boolean(v))} />
                <span className="text-sm font-mono text-cyber-text-primary">{t('clearDb')}</span>
              </label>
              <label className="flex items-center gap-3 cursor-pointer">
                <Checkbox checked={clearRuns} onCheckedChange={(v) => setClearRuns(Boolean(v))} />
                <span className="text-sm font-mono text-cyber-text-primary">{t('clearRuns')}</span>
              </label>
            </div>
            <DialogFooter>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setDialogOpen(false)}
                disabled={clearMutation.isPending}
                className="font-mono"
              >
                {t('cancel')}
              </Button>
              <Button
                size="sm"
                onClick={handleClear}
                disabled={clearMutation.isPending || (!clearFiles && !clearDb && !clearRuns)}
                className="font-mono bg-cyber-neon-pink text-white hover:bg-cyber-neon-pink/90"
              >
                {clearMutation.isPending ? (
                  <Loader2 className="w-3.5 h-3.5 mr-1 animate-spin" />
                ) : (
                  <Trash2 className="w-3.5 h-3.5 mr-1" />
                )}
                {t('clear')}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {/* 列表 */}
      <ScrollArea className="flex-1 min-h-0">
        {isLoading ? (
          <div className="flex items-center justify-center h-32">
            <Loader2 className="w-5 h-5 text-cyber-neon-cyan animate-spin" />
          </div>
        ) : !runs || runs.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-64 text-center">
            <History className="w-10 h-10 text-cyber-text-muted/40 mb-3" />
            <p className="text-sm font-mono text-cyber-text-muted">{t('empty')}</p>
            <p className="text-xs font-mono text-cyber-text-muted/60 mt-1">{t('emptyHint')}</p>
          </div>
        ) : (
          <div className="space-y-2 pr-2">
            {runs.map((run) => (
              <RunRow key={run.run_id} run={run} />
            ))}
          </div>
        )}
      </ScrollArea>
    </div>
  )
}
