import { useTranslation } from 'react-i18next'
import { ShieldAlert, ExternalLink } from 'lucide-react'
import { Button } from '@/components/ui/button'

const LICENSE_KEY = 'mediacrawler_license_accepted'

// 检查是否已经接受协议
export function isLicenseAccepted(): boolean {
  return localStorage.getItem(LICENSE_KEY) === 'true'
}

// 清除协议接受状态
export function clearLicenseAccepted(): void {
  localStorage.removeItem(LICENSE_KEY)
}

interface LicenseDisclaimerProps {
  onAccept: () => void
}

export function LicenseDisclaimer({ onAccept }: LicenseDisclaimerProps) {
  const { t } = useTranslation('license')

  const handleConfirm = () => {
    localStorage.setItem(LICENSE_KEY, 'true')
    onAccept()
  }

  const handleDecline = () => {
    // 尝试关闭当前标签页（不会关闭整个浏览器，只关闭当前tab）
    try {
      // 方式1: 直接关闭当前标签页
      window.close()

      // 方式2: 将当前标签页导航到空白页
      setTimeout(() => {
        window.location.href = 'about:blank'
      }, 100)
    } catch {
      // 忽略错误
    }

    // 如果无法关闭（浏览器安全限制），显示拒绝访问页面
    setTimeout(() => {
      document.body.innerHTML = `
        <div style="
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          height: 100vh;
          background: #0d1117;
          color: #f85149;
          font-family: 'JetBrains Mono', monospace;
          text-align: center;
          padding: 20px;
        ">
          <div style="font-size: 48px; margin-bottom: 20px;">⛔</div>
          <div style="font-size: 24px; font-weight: bold; margin-bottom: 10px;">访问已拒绝</div>
          <div style="font-size: 14px; color: #8b949e;">您未同意使用条款，请关闭此标签页</div>
        </div>
      `
    }, 200)
  }

  return (
    <div className="fixed inset-0 bg-black/95 backdrop-blur-sm flex items-center justify-center z-[100] overflow-y-auto py-8">
      <div className="bg-cyber-bg-panel border-2 border-cyber-neon-pink rounded-lg shadow-cyber-card p-6 max-w-2xl w-full mx-4 relative">
        {/* Corner decorations - Pink/Red theme for seriousness */}
        <div className="absolute top-0 left-0 w-6 h-6 border-t-2 border-l-2 border-cyber-neon-pink" />
        <div className="absolute top-0 right-0 w-6 h-6 border-t-2 border-r-2 border-cyber-neon-pink" />
        <div className="absolute bottom-0 left-0 w-6 h-6 border-b-2 border-l-2 border-cyber-neon-pink" />
        <div className="absolute bottom-0 right-0 w-6 h-6 border-b-2 border-r-2 border-cyber-neon-pink" />

        {/* Header with warning icon */}
        <div className="flex items-center justify-center gap-3 mb-4">
          <ShieldAlert className="w-8 h-8 text-cyber-neon-pink animate-pulse" />
          <h2 className="text-xl font-mono font-bold text-cyber-neon-pink">
            {t('title')}
          </h2>
        </div>

        {/* Warning subtitle */}
        <div className="text-center mb-4">
          <span className="text-base font-mono text-cyber-neon-orange">
            {t('warning')}
          </span>
        </div>

        {/* Content box */}
        <div className="bg-black/50 border border-cyber-neon-pink/30 rounded-lg p-4 mb-4">
          <ul className="space-y-2 text-sm font-mono">
            <li className="flex items-start gap-2">
              <span className="text-cyber-neon-pink font-bold">1.</span>
              <span className="text-cyber-text-primary">{t('content.line1')}</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-cyber-neon-pink font-bold">2.</span>
              <span className="text-cyber-text-primary">{t('content.line2')}</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-cyber-neon-pink font-bold">3.</span>
              <span className="text-cyber-text-primary">{t('content.line3')}</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-cyber-neon-pink font-bold">4.</span>
              <span className="text-cyber-text-primary">{t('content.line4')}</span>
            </li>
          </ul>
        </div>

        {/* License Link */}
        <div className="flex justify-center mb-6">
          <a
            href="https://github.com/NanmiCoder/MediaCrawler/blob/main/LICENSE"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 text-cyber-neon-cyan hover:underline text-sm font-mono"
          >
            <ExternalLink className="w-4 h-4" />
            {t('license')}
          </a>
        </div>

        {/* Action buttons */}
        <div className="flex gap-4">
          <Button
            onClick={handleDecline}
            variant="outline"
            className="flex-1 font-mono border-cyber-neon-pink/50 text-cyber-neon-pink hover:bg-cyber-neon-pink/10"
          >
            {t('decline')}
          </Button>
          <Button
            onClick={handleConfirm}
            className="flex-1 font-mono bg-cyber-neon-green text-black font-bold hover:bg-cyber-neon-green/90"
          >
            {t('confirm')}
          </Button>
        </div>
      </div>
    </div>
  )
}
