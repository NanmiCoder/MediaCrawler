import { useState, useEffect, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { ChevronDown, ChevronUp, Trash2, RefreshCw } from 'lucide-react'
import { TerminalLine } from './TerminalLine'
import { useCrawlerStore } from '@/store/crawlerStore'
import { Button } from '@/components/ui/button'
import { DataExplorerDialog } from '@/components/data/DataExplorerDialog'

export function Terminal() {
  const { t } = useTranslation('terminal')
  const [isCollapsed, setIsCollapsed] = useState(false)
  const logs = useCrawlerStore((state) => state.logs)
  const clearLogs = useCrawlerStore((state) => state.clearLogs)
  const restoreLogs = useCrawlerStore((state) => state.restoreLogs)
  const clearedAfterLogId = useCrawlerStore((state) => state.clearedAfterLogId)
  const status = useCrawlerStore((state) => state.status)
  const scrollRef = useRef<HTMLDivElement>(null)

  // Auto scroll to bottom
  useEffect(() => {
    if (scrollRef.current && !isCollapsed) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [logs, isCollapsed])

  return (
    <div className={`flex flex-col rounded-lg overflow-hidden transition-all duration-300 border border-cyber-border-subtle bg-[#0d1117] ${isCollapsed ? 'h-12' : 'h-full'}`}>
      {/* Terminal Header */}
      <div className="flex items-center justify-between px-4 py-2.5 bg-[#161b22] border-b border-[#30363d] flex-shrink-0">
        <div className="flex items-center gap-3">
          {/* Window buttons */}
          <div className="flex gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-cyber-neon-pink/80" />
            <span className="w-2.5 h-2.5 rounded-full bg-cyber-neon-orange/80" />
            <span className="w-2.5 h-2.5 rounded-full bg-cyber-neon-green/80" />
          </div>
          <span className="text-xs text-[#8b949e] font-mono tracking-wider">
            {t('header.title')}
          </span>
        </div>

        <div className="flex items-center gap-3">
          {/* Log count & status */}
          <div className="flex items-center gap-3 text-xs font-mono">
            <span className="text-[#8b949e]">{t('header.entries', { count: logs.length })}</span>
            {status === 'running' && (
              <div className="flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 bg-cyber-neon-green rounded-full shadow-glow-green-sm animate-pulse-fast" />
                <span className="text-cyber-neon-green">{t('header.active')}</span>
              </div>
            )}
          </div>

          {/* Data Explorer */}
          <DataExplorerDialog />

          {/* Restore logs - 只在有清除标记时显示 */}
          {clearedAfterLogId !== null && (
            <Button
              variant="ghost"
              size="sm"
              onClick={restoreLogs}
              className="h-7 px-2 text-[#8b949e] hover:text-[#00ffff] hover:bg-[#00ffff]/10"
              title={t('header.restore')}
            >
              <RefreshCw className="w-4 h-4" />
            </Button>
          )}

          {/* Clear logs */}
          <Button
            variant="ghost"
            size="sm"
            onClick={clearLogs}
            disabled={logs.length === 0}
            className="h-7 px-2 text-[#8b949e] hover:text-[#ff0080] hover:bg-[#ff0080]/10 disabled:opacity-30"
            title={t('header.clear')}
          >
            <Trash2 className="w-4 h-4" />
          </Button>

          {/* Collapse toggle */}
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setIsCollapsed(!isCollapsed)}
            className="h-7 px-2 text-[#8b949e] hover:text-[#00ffff] hover:bg-[#00ffff]/10"
          >
            {isCollapsed ? (
              <ChevronDown className="w-4 h-4" />
            ) : (
              <ChevronUp className="w-4 h-4" />
            )}
          </Button>
        </div>
      </div>

      {/* Terminal Content - only show when not collapsed */}
      {!isCollapsed && (
        <>
          <div
            ref={scrollRef}
            className="flex-1 overflow-auto p-4 font-mono text-sm terminal-scroll bg-[#0d1117] min-h-0"
          >
            {/* ASCII Art Banner when empty */}
            {logs.length === 0 ? (
              <div className="space-y-4">
                <pre className="text-cyber-neon-cyan/70 text-xs leading-tight">
{`  ╔══════════════════════════════════════════════════════╗
  ║   __  __          _ _       ____                     ║
  ║  |  \\/  | ___  __| (_) __ _/ ___|_ __ __ ___      __ ║
  ║  | |\\/| |/ _ \\/ _\` | |/ _\` | |   | '__/ _\` \\ \\ /\\ / / ║
  ║  | |  | |  __/ (_| | | (_| | |___| | | (_| |\\ V  V /  ║
  ║  |_|  |_|\\___|\\__,_|_|\\__,_|\\____|_|  \\__,_| \\_/\\_/   ║
  ║                                                      ║
  ║          [ NEURAL EXTRACTION UNIT v1.0 ]             ║
  ╚══════════════════════════════════════════════════════╝`}
                </pre>
                <div className="text-[#c9d1d9] text-xs space-y-1">
                  <p className="text-cyber-neon-green/70">{t('banner.systemInit')}</p>
                  <p className="text-[#8b949e]">{t('banner.configHint')}</p>
                </div>
              </div>
            ) : (
              <div className="space-y-0.5">
                {logs.map((log) => (
                  <TerminalLine key={log.id} log={log} />
                ))}
              </div>
            )}

            {/* Active Cursor */}
            {status === 'running' && (
              <div className="flex items-center gap-1 mt-3">
                <span className="text-cyber-neon-green/80">root@crawler:~$</span>
                <span className="w-2 h-4 bg-cyber-neon-green/80 cursor-blink" />
              </div>
            )}
          </div>

          {/* Terminal Footer */}
          <div className="px-4 py-2 border-t border-[#30363d] bg-[#161b22] flex items-center justify-end flex-shrink-0">
            <div className="text-xs font-mono text-[#8b949e]">
              {status.toUpperCase()}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
