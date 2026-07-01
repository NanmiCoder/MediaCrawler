import { useTranslation } from 'react-i18next'
import { Database } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { DataExplorer } from './DataExplorer'

export function DataExplorerDialog() {
  const { t } = useTranslation('data')

  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button
          variant="outline"
          size="sm"
          className="font-mono text-xs text-[#c9d1d9] border-[#30363d] bg-transparent hover:bg-[#21262d] hover:text-[#00ffff] hover:border-[#00ffff]/50"
        >
          <Database className="w-3.5 h-3.5" />
          {t('dialog.button')}
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-5xl max-h-[85vh] overflow-hidden">
        <DialogHeader>
          <DialogTitle>{t('dialog.title')}</DialogTitle>
        </DialogHeader>
        <div className="overflow-auto max-h-[calc(85vh-100px)] pr-2">
          <DataExplorer />
        </div>
      </DialogContent>
    </Dialog>
  )
}
