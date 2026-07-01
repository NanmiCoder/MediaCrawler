import { useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Search } from 'lucide-react'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Input } from '@/components/ui/input'

interface DataPreviewTableProps {
  data: Record<string, unknown>[]
  columns?: string[]
}

export function DataPreviewTable({ data, columns: propColumns }: DataPreviewTableProps) {
  const { t } = useTranslation('data')
  const [searchTerm, setSearchTerm] = useState('')

  // 自动获取列名（JSON 可能没有 columns）
  const columns = useMemo(() => {
    if (propColumns && propColumns.length > 0) return propColumns
    if (data.length === 0) return []
    return Object.keys(data[0])
  }, [data, propColumns])

  // 过滤数据
  const filteredData = useMemo(() => {
    if (!searchTerm) return data
    const term = searchTerm.toLowerCase()
    return data.filter(row =>
      Object.values(row).some(value =>
        String(value ?? '').toLowerCase().includes(term)
      )
    )
  }, [data, searchTerm])

  // 格式化单元格值
  const formatCellValue = (value: unknown): string => {
    if (value === null || value === undefined) return '-'
    if (typeof value === 'object') return JSON.stringify(value)
    return String(value)
  }

  return (
    <div className="h-full flex flex-col">
      {/* 搜索栏 */}
      <div className="flex-shrink-0 mb-3">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-cyber-text-muted" />
          <Input
            placeholder={t('preview.searchPlaceholder')}
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-9 h-9 text-xs font-mono"
          />
        </div>
      </div>

      {/* 表格 */}
      <ScrollArea className="flex-1 border border-cyber-border-DEFAULT rounded-lg">
        <div className="min-w-full">
          <table className="w-full text-xs font-mono">
            <thead className="sticky top-0 bg-cyber-bg-tertiary border-b border-cyber-border-DEFAULT">
              <tr>
                <th className="px-3 py-2 text-left text-cyber-text-muted w-12">#</th>
                {columns.map((col) => (
                  <th
                    key={col}
                    className="px-3 py-2 text-left text-cyber-neon-cyan whitespace-nowrap"
                  >
                    {col}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filteredData.map((row, idx) => (
                <tr
                  key={idx}
                  className="border-b border-cyber-border-subtle hover:bg-cyber-bg-elevated/50 transition-colors"
                >
                  <td className="px-3 py-2 text-cyber-text-muted">{idx + 1}</td>
                  {columns.map((col) => (
                    <td
                      key={col}
                      className="px-3 py-2 text-cyber-text-primary max-w-xs truncate"
                      title={formatCellValue(row[col])}
                    >
                      {formatCellValue(row[col])}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </ScrollArea>

      {/* 过滤结果提示 */}
      {searchTerm && (
        <div className="flex-shrink-0 mt-2 text-xs text-cyber-text-muted font-mono">
          {t('preview.showing', { filtered: filteredData.length, total: data.length })}
        </div>
      )}
    </div>
  )
}
