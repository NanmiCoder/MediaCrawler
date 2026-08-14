import { Bug, Wifi, AlertTriangle, Github, Save } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { useCrawlerStore } from '@/store/crawlerStore'
import { useCrawlerStatus } from '@/hooks/useCrawler'
import { LanguageSwitch } from './LanguageSwitch'
import { ThemeToggle } from './ThemeToggle'

interface SidebarProps {
  onShowDisclaimer?: () => void
}

export function Sidebar({ onShowDisclaimer }: SidebarProps) {
  const { t } = useTranslation()
  const { t: tLicense } = useTranslation('license')
  const { t: tConfig } = useTranslation('config')
  const status = useCrawlerStore((state) => state.status)
  const saveConfig = useCrawlerStore((state) => state.saveConfig)

  // Poll status
  useCrawlerStatus()

  const isRunning = status === 'running'

  const handleSaveConfig = () => {
    const saved = saveConfig()
    if (saved) {
      toast.success(tConfig('toast.configSaved'))
    } else {
      toast.error(tConfig('toast.configSaveFailed'))
    }
  }

  return (
    <header className="h-14 flex-shrink-0 glass-panel border-b border-cyber-border-subtle relative z-10">
      <div className="grid h-full grid-cols-[1fr_auto_1fr] items-center gap-4 px-4">
        {/* Left: Logo and GitHub Star */}
        <div className="flex min-w-0 items-center gap-3 justify-self-start">
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
          className="hidden 2xl:flex items-center gap-3 px-4 py-1.5 rounded-lg border border-cyber-neon-orange/50 bg-cyber-neon-orange/10 hover:bg-cyber-neon-orange/20 transition-all cursor-pointer"
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
        <button
          type="button"
          onClick={onShowDisclaimer}
          className="2xl:hidden flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg border border-cyber-neon-orange/50 bg-cyber-neon-orange/10 text-cyber-neon-orange transition-all hover:bg-cyber-neon-orange/20"
          title={`${tLicense('content.line1')} ${tLicense('content.line2')}`}
          aria-label={`${tLicense('content.line1')} ${tLicense('content.line2')}`}
        >
          <AlertTriangle className="h-4 w-4" />
        </button>

        {/* Right: Actions and Status */}
        <div className="flex items-center gap-3 justify-self-end">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={handleSaveConfig}
            className="h-7 flex-shrink-0 border-cyber-neon-cyan/40 bg-cyber-neon-cyan/5 px-3 text-xs font-mono font-semibold text-cyber-neon-cyan hover:bg-cyber-neon-cyan/10 hover:text-cyber-neon-cyan hover:border-cyber-neon-cyan/70"
          >
            <Save className="w-3.5 h-3.5" />
            {tConfig('button.saveAllConfig')}
          </Button>
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
