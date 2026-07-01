import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { FileJson, FileSpreadsheet, FileText, Download, Eye } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { dataApi } from '@/lib/api'
import { formatFileSize, formatDateTime } from '@/lib/utils'
import { DataPreviewDialog } from './preview/DataPreviewDialog'
import type { DataFile } from '@/types/crawler'

interface FileCardProps {
  file: DataFile
}

const fileIcons: Record<string, typeof FileJson> = {
  json: FileJson,
  csv: FileSpreadsheet,
  xlsx: FileSpreadsheet,
  xls: FileSpreadsheet,
}

const fileStyles: Record<string, { icon: string; border: string; badge: string }> = {
  json: {
    icon: 'text-cyber-neon-yellow',
    border: 'hover:border-cyber-neon-yellow/50',
    badge: 'border-cyber-neon-yellow/30 bg-cyber-neon-yellow/10 text-cyber-neon-yellow'
  },
  csv: {
    icon: 'text-cyber-neon-green',
    border: 'hover:border-cyber-neon-green/50',
    badge: 'border-cyber-neon-green/30 bg-cyber-neon-green/10 text-cyber-neon-green'
  },
  xlsx: {
    icon: 'text-cyber-neon-cyan',
    border: 'hover:border-cyber-neon-cyan/50',
    badge: 'border-cyber-neon-cyan/30 bg-cyber-neon-cyan/10 text-cyber-neon-cyan'
  },
  xls: {
    icon: 'text-cyber-neon-cyan',
    border: 'hover:border-cyber-neon-cyan/50',
    badge: 'border-cyber-neon-cyan/30 bg-cyber-neon-cyan/10 text-cyber-neon-cyan'
  },
}

export function FileCard({ file }: FileCardProps) {
  const { t } = useTranslation('data')
  const [previewOpen, setPreviewOpen] = useState(false)

  const Icon = fileIcons[file.type] || FileText
  const styles = fileStyles[file.type] || {
    icon: 'text-cyber-text-muted',
    border: 'hover:border-cyber-neon-cyan/50',
    badge: 'border-cyber-border-DEFAULT bg-cyber-bg-tertiary text-cyber-text-secondary'
  }

  // 检查是否支持预览
  const isPreviewable = ['json', 'csv', 'xlsx', 'xls'].includes(file.type.toLowerCase())

  const handleDownload = () => {
    const url = dataApi.getDownloadUrl(file.path)
    window.open(url, '_blank')
  }

  return (
    <>
      <Card className={`relative overflow-hidden card-scan group transition-all ${styles.border} hover:shadow-[0_0_15px_rgb(var(--cyber-neon-cyan)/0.15)]`}>
        {/* Scan effect overlay */}
        <div className="absolute inset-0 bg-gradient-to-r from-transparent via-cyber-neon-cyan/5 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-700 pointer-events-none" />

        <CardContent className="p-4 relative">
          <div className="flex items-start gap-3">
            <div className={`p-2 rounded bg-cyber-bg-panel border border-cyber-border-DEFAULT ${styles.icon}`}>
              <Icon className="w-6 h-6" />
            </div>
            <div className="flex-1 min-w-0">
              <h3 className="font-mono font-medium text-sm text-cyber-text-primary truncate" title={file.name}>
                {file.name}
              </h3>
              <p className="text-xs text-cyber-text-muted mt-1 font-mono">
                {formatFileSize(file.size)}
                {file.record_count !== null && (
                  <span className="text-cyber-neon-green"> | {t('file.entries', { count: file.record_count })}</span>
                )}
              </p>
              <p className="text-xs text-cyber-text-muted mt-1 font-mono">
                {formatDateTime(file.modified_at)}
              </p>
            </div>
          </div>

          <div className="flex items-center justify-between mt-3 pt-3 border-t border-cyber-border-subtle">
            <Badge variant="outline" className={`text-[10px] font-mono ${styles.badge}`}>
              .{file.type.toUpperCase()}
            </Badge>
            <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
              {isPreviewable && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 px-2 font-mono text-cyber-neon-cyan hover:text-cyber-neon-cyan hover:bg-cyber-neon-cyan/10"
                  onClick={() => setPreviewOpen(true)}
                >
                  <Eye className="w-3 h-3 mr-1" />
                  {t('file.preview')}
                </Button>
              )}
              <Button
                variant="ghost"
                size="sm"
                className="h-7 px-2 font-mono text-cyber-neon-cyan hover:text-cyber-neon-cyan hover:bg-cyber-neon-cyan/10"
                onClick={handleDownload}
              >
                <Download className="w-3 h-3 mr-1" />
                {t('file.extract')}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 预览对话框 */}
      {isPreviewable && (
        <DataPreviewDialog
          file={file}
          open={previewOpen}
          onOpenChange={setPreviewOpen}
        />
      )}
    </>
  )
}
