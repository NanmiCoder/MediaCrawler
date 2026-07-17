import { Bug, Wifi, AlertTriangle, Github, History, Music, MessageSquare, Bug as CrawlerIcon } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { useCrawlerStore } from '@/store/crawlerStore'
import { useViewStore } from '@/store/viewStore'
import { useCrawlerStatus } from '@/hooks/useCrawler'
import { LanguageSwitch } from './LanguageSwitch'
import { ThemeToggle } from './ThemeToggle'

interface SidebarProps {
  onShowDisclaimer?: () => void
}

type ViewKey = 'crawler' | 'history' | 'bgm' | 'comments'

export function Sidebar({ onShowDisclaimer }: SidebarProps) {
  const { t } = useTranslation()
  const { t: tLicense } = useTranslation('license')
  const status = useCrawlerStore((state) => state.status)
  const currentView = useViewStore((s) => s.currentView)
  const setView = useViewStore((s) => s.setView)

  // Poll status
  useCrawlerStatus()

  const isRunning = status === 'running'

  const viewButtons: { key: ViewKey; icon: typeof History; label: string }[] = [
    { key: 'crawler', icon: CrawlerIcon, label: t('sidebar.crawler', '爬虫') },
    { key: 'history', icon: History, label: t('sidebar.history', '历史') },
    { key: 'bgm', icon: Music, label: t('sidebar.bgm', 'BGM') },
    { key: 'comments', icon: MessageSquare, label: t('sidebar.comments', '评论') },
  ]

  return (
    <header className="h-14 flex-shrink-0 glass-panel border-b border-cyber-border-subtle relative z-10">
      <div className="h-full px-4 flex items-center justify-between">
        {/* Left: Logo and GitHub Star */}
        <div className="flex items-center gap-3">
          <Bug className="w-5 h-5 text-cyber-neon-cyan" />
          <span className="font-mono font-bold text-cyber-text-primary tracking-wider text-sm">
            MediaCrawler
          </span>
          <a
            href="https://github.com/NanmiCoder/MediaCrawler"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 px-2 py-1 rounded-md border border-cyber-border-subtle hover:border-cyber-neon-cyan hover:shadow-glow-cyan-sm transition-all bg-cyber-bg-tertiary"
          >
            <Github className="w-4 h-4 text-cyber-text-secondary" />
            <span className="text-xs font-mono text-cyber-text-secondary">Star</span>
          </a>
          {isRunning && (
            <Badge variant="running" className="text-[10px]">
              {t('status.active')}
            </Badge>
          )}
          {isRunning && (
            <span className="w-2 h-2 bg-cyber-neon-green rounded-full shadow-glow-green-sm animate-pulse-fast" />
          )}
        </div>

        {/* Center: Warning Text */}
        <button
          onClick={onShowDisclaimer}
          className="flex items-center gap-3 px-4 py-1.5 rounded-lg border border-cyber-neon-orange/50 bg-cyber-neon-orange/10 hover:bg-cyber-neon-orange/20 transition-all cursor-pointer"
        >
          <AlertTriangle className="w-4 h-4 text-cyber-neon-orange flex-shrink-0" />
          <div className="flex items-center gap-4 text-xs font-mono">
            <span className="text-cyber-neon-orange">
              <span className="text-cyber-neon-pink font-bold">1.</span> {tLicense('content.line1')}
            </span>
            <span className="text-cyber-neon-orange">
              <span className="text-cyber-neon-pink font-bold">2.</span> {tLicense('content.line2')}
            </span>
          </div>
        </button>

        {/* Right: View switch + Actions + Status */}
        <div className="flex items-center gap-3">
          {/* View switcher */}
          <div className="flex items-center gap-1 p-0.5 rounded-md border border-cyber-border-subtle bg-cyber-bg-tertiary">
            {viewButtons.map(({ key, icon: Icon, label }) => {
              const active = currentView === key
              return (
                <Button
                  key={key}
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => setView(key)}
                  title={label}
                  className={`h-7 px-2 font-mono text-xs transition-all ${
                    active
                      ? 'bg-cyber-neon-cyan/20 text-cyber-neon-cyan shadow-glow-cyan-sm'
                      : 'text-cyber-text-muted hover:text-cyber-text-primary hover:bg-cyber-bg-elevated'
                  }`}
                >
                  <Icon className="w-3.5 h-3.5" />
                </Button>
              )
            })}
          </div>

          {/* Theme Toggle */}
          <ThemeToggle />
          {/* Language Switch */}
          <LanguageSwitch />

          {/* Status Info */}
          <div className="hidden lg:flex items-center gap-2 text-xs font-mono">
            <span className="text-cyber-text-muted">{t('sidebar.api')}:</span>
            <span className="text-cyber-neon-green">v1.0.0</span>
            <div className="flex items-center gap-1.5">
              <Wifi className="w-3 h-3 text-cyber-text-secondary" />
              <span className="text-cyber-text-secondary">{t('sidebar.local')}</span>
              <span className="status-dot status-dot-online" />
            </div>
          </div>
        </div>
      </div>
    </header>
  )
}
