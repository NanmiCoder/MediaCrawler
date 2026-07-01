import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { CheckCircle, XCircle, Loader2, RefreshCw, AlertTriangle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { envApi, EnvCheckResult } from '@/lib/api'

const ENV_CHECK_KEY = 'mediacrawler_env_checked'

interface EnvironmentCheckProps {
  onCheckComplete: (success: boolean) => void
}

// 检查是否已经通过环境检测
export function isEnvChecked(): boolean {
  return localStorage.getItem(ENV_CHECK_KEY) === 'true'
}

// 清除环境检测状态
export function clearEnvCheck(): void {
  localStorage.removeItem(ENV_CHECK_KEY)
}

export function EnvironmentCheck({ onCheckComplete }: EnvironmentCheckProps) {
  const { t } = useTranslation('env')
  const [status, setStatus] = useState<'checking' | 'success' | 'error'>('checking')
  const [result, setResult] = useState<EnvCheckResult | null>(null)
  const [showDetails, setShowDetails] = useState(false)

  const checkEnvironment = async () => {
    setStatus('checking')
    setResult(null)
    try {
      const response = await envApi.check()
      setResult(response.data)
      if (response.data.success) {
        setStatus('success')
        // 存储到 localStorage
        localStorage.setItem(ENV_CHECK_KEY, 'true')
        // 成功后延迟关闭
        setTimeout(() => onCheckComplete(true), 1500)
      } else {
        setStatus('error')
      }
    } catch (error) {
      setResult({
        success: false,
        message: t('defaultError'),
        error: t('defaultErrorHint')
      })
      setStatus('error')
    }
  }

  useEffect(() => {
    checkEnvironment()
  }, [])

  const handleSkip = () => {
    localStorage.setItem(ENV_CHECK_KEY, 'true')
    onCheckComplete(false)
  }

  const handleRetry = () => {
    checkEnvironment()
  }

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50">
      <div className="bg-cyber-bg-panel border border-cyber-border-DEFAULT rounded-lg shadow-cyber-card p-6 max-w-md w-full mx-4 relative">
        {/* Corner decorations */}
        <div className="absolute top-0 left-0 w-4 h-4 border-t-2 border-l-2 border-cyber-neon-cyan" />
        <div className="absolute top-0 right-0 w-4 h-4 border-t-2 border-r-2 border-cyber-neon-cyan" />
        <div className="absolute bottom-0 left-0 w-4 h-4 border-b-2 border-l-2 border-cyber-neon-cyan" />
        <div className="absolute bottom-0 right-0 w-4 h-4 border-b-2 border-r-2 border-cyber-neon-cyan" />

        {/* Header */}
        <div className="flex items-center gap-3 mb-4">
          <AlertTriangle className="w-6 h-6 text-cyber-neon-orange" />
          <h2 className="text-lg font-mono font-semibold text-cyber-neon-cyan glow-text-cyan">
            {t('title')}
          </h2>
        </div>

        {/* Status Display */}
        <div className="bg-cyber-bg-tertiary border border-cyber-border-DEFAULT rounded-lg p-4 mb-4">
          <div className="flex items-center gap-3">
            {status === 'checking' && (
              <>
                <Loader2 className="w-5 h-5 text-cyber-neon-cyan animate-spin" />
                <span className="text-cyber-text-primary font-mono text-sm">
                  {t('scanning')}
                </span>
              </>
            )}
            {status === 'success' && (
              <>
                <CheckCircle className="w-5 h-5 text-cyber-neon-green" />
                <span className="text-cyber-neon-green font-mono text-sm">
                  {t('success', { message: result?.message })}
                </span>
              </>
            )}
            {status === 'error' && (
              <>
                <XCircle className="w-5 h-5 text-cyber-neon-pink" />
                <span className="text-cyber-neon-pink font-mono text-sm">
                  {t('error', { message: result?.message })}
                </span>
              </>
            )}
          </div>

          {/* Error Details */}
          {status === 'error' && result?.error && (
            <div className="mt-3">
              <button
                onClick={() => setShowDetails(!showDetails)}
                className="text-sm text-cyber-neon-cyan hover:underline font-mono"
              >
                {showDetails ? t('hideDetails') : t('showDetails')}
              </button>
              {showDetails && (
                <pre className="mt-2 p-3 bg-black text-cyber-neon-green rounded text-xs font-mono overflow-x-auto whitespace-pre-wrap border border-cyber-border-DEFAULT">
                  {result.error}
                </pre>
              )}
            </div>
          )}
        </div>

        {/* Help Text */}
        {status === 'error' && (
          <div className="text-sm text-cyber-text-secondary mb-4 space-y-2 font-mono">
            <p className="text-cyber-neon-orange">{t('requirements')}</p>
            <ol className="list-decimal list-inside space-y-1 pl-2 text-cyber-text-muted">
              <li>{t('requirementsList.1')}</li>
              <li>{t('requirementsList.2')}</li>
              <li>{t('requirementsList.3')}</li>
            </ol>
          </div>
        )}

        {/* Actions */}
        <div className="flex gap-3">
          {status === 'error' && (
            <>
              <Button
                variant="outline"
                className="flex-1 font-mono"
                onClick={handleSkip}
              >
                {t('skipCheck')}
              </Button>
              <Button
                variant="glow"
                className="flex-1 font-mono"
                onClick={handleRetry}
              >
                <RefreshCw className="w-4 h-4" />
                {t('retryCheck')}
              </Button>
            </>
          )}
          {status === 'checking' && (
            <Button
              variant="outline"
              className="w-full font-mono"
              onClick={handleSkip}
            >
              {t('skipCheck')}
            </Button>
          )}
        </div>
      </div>
    </div>
  )
}
