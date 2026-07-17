import { useState } from 'react'
import { Toaster } from 'sonner'
import { Sidebar } from '@/components/layout/Sidebar'
import { MainContent } from '@/components/layout/MainContent'
import { CrawlerConfigPanel } from '@/components/config/CrawlerConfigPanel'
import { HistoryView } from '@/components/history/HistoryView'
import { BgmPlayer } from '@/components/bgm/BgmPlayer'
import { CommentsView } from '@/components/comments/CommentsView'
import { EnvironmentCheck, isEnvChecked } from '@/components/env/EnvironmentCheck'
import { LicenseDisclaimer, isLicenseAccepted } from '@/components/license/LicenseDisclaimer'
import { useViewStore } from '@/store/viewStore'

function App() {
  // Initialize by checking localStorage if license has been accepted
  const [licenseAccepted, setLicenseAccepted] = useState(() => isLicenseAccepted())
  // Initialize by checking localStorage if env check has passed
  const [envChecked, setEnvChecked] = useState(() => isEnvChecked())
  // State for showing disclaimer manually
  const [showDisclaimer, setShowDisclaimer] = useState(false)

  const currentView = useViewStore((s) => s.currentView)

  const handleEnvCheckComplete = () => {
    setEnvChecked(true)
  }

  const handleLicenseAccept = () => {
    setLicenseAccepted(true)
    setShowDisclaimer(false)
  }

  const handleShowDisclaimer = () => {
    setShowDisclaimer(true)
  }

  return (
    <div className="flex flex-col h-screen cyber-grid overflow-hidden relative">
      {/* License Disclaimer Modal - Shows first or when triggered */}
      {(!licenseAccepted || showDisclaimer) && (
        <LicenseDisclaimer onAccept={handleLicenseAccept} />
      )}

      {/* Environment Check Modal - Shows after license accepted */}
      {licenseAccepted && !showDisclaimer && !envChecked && (
        <EnvironmentCheck onCheckComplete={handleEnvCheckComplete} />
      )}

      {/* Header Bar */}
      <Sidebar onShowDisclaimer={handleShowDisclaimer} />

      {/* Main Area */}
      <div className="flex-1 flex flex-col gap-4 p-4 overflow-hidden min-h-0">
        {/* View switch: crawler / history / bgm */}
        {currentView === 'crawler' && (
          <>
            {/* Config Panel - Primary Action Area (Always Expanded) */}
            <div className="flex-shrink-0">
              <CrawlerConfigPanel />
            </div>

            {/* Console - Collapsible Terminal */}
            <MainContent />
          </>
        )}
        {currentView === 'history' && (
          <div className="flex-1 min-h-0">
            <HistoryView />
          </div>
        )}
        {currentView === 'bgm' && (
          <div className="flex-1 min-h-0">
            <BgmPlayer />
          </div>
        )}
        {currentView === 'comments' && (
          <div className="flex-1 min-h-0">
            <CommentsView />
          </div>
        )}
      </div>

      {/* Toast notifications - Theme-aware style */}
      <Toaster
        position="top-right"
        toastOptions={{
          className: 'glass-panel font-mono text-cyber-text-primary',
          style: {
            fontFamily: 'JetBrains Mono, monospace',
          },
        }}
      />
    </div>
  )
}

export default App
