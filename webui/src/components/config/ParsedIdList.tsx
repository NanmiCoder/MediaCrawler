import { useMemo } from 'react'
import { Check, AlertTriangle, X } from 'lucide-react'
import { parseMultipleUrls, type ParsedId } from '@/lib/urlParser'

interface ParsedIdListProps {
  value: string
  platform: string
  type: 'detail' | 'creator'
  onRemove?: (index: number) => void
  disabled?: boolean
}

export function ParsedIdList({ value, platform, type, onRemove, disabled }: ParsedIdListProps) {
  const parsed = useMemo(() => {
    return parseMultipleUrls(value, platform)
  }, [value, platform])

  if (parsed.length === 0) return null

  const handleRemove = (index: number) => {
    if (disabled || !onRemove) return

    const items = value
      .split(/[,\n]+/)
      .map(s => s.trim())
      .filter(Boolean)

    items.splice(index, 1)
    onRemove(index)
  }

  return (
    <div className="space-y-1.5 mt-2">
      <div className="text-[10px] text-cyber-text-muted font-mono">
        已识别 {parsed.length} 个{type === 'detail' ? '帖子/视频' : '创作者'}:
      </div>
      <div className="flex flex-wrap gap-1.5">
        {parsed.map((item, index) => (
          <ParsedIdTag
            key={`${item.id}-${index}`}
            item={item}
            expectedType={type}
            onRemove={!disabled ? () => handleRemove(index) : undefined}
          />
        ))}
      </div>
    </div>
  )
}

interface ParsedIdTagProps {
  item: ParsedId
  expectedType: 'detail' | 'creator'
  onRemove?: () => void
}

function ParsedIdTag({ item, expectedType, onRemove }: ParsedIdTagProps) {
  // 检查类型是否匹配
  const typeMatch = item.type === 'unknown' ||
    (expectedType === 'detail' && item.type === 'video') ||
    (expectedType === 'creator' && item.type === 'creator')

  // 警告状态：小红书需要xsec_token
  const needsWarning = !item.isValid || !typeMatch

  return (
    <span
      className={`
        inline-flex items-center gap-1 px-2 py-1 rounded-md text-[10px] font-mono
        ${needsWarning
          ? 'bg-cyber-neon-orange/10 border border-cyber-neon-orange/30 text-cyber-neon-orange'
          : 'bg-cyber-neon-cyan/10 border border-cyber-neon-cyan/30 text-cyber-neon-cyan'
        }
      `}
      title={item.original}
    >
      {needsWarning ? (
        <AlertTriangle className="w-3 h-3 flex-shrink-0" />
      ) : (
        <Check className="w-3 h-3 flex-shrink-0" />
      )}
      <span className="max-w-[120px] truncate">
        {item.id.length > 20 ? item.id.slice(0, 8) + '...' + item.id.slice(-8) : item.id}
      </span>
      {onRemove && (
        <button
          type="button"
          onClick={onRemove}
          className="hover:text-cyber-neon-pink transition-colors ml-0.5"
        >
          <X className="w-3 h-3" />
        </button>
      )}
    </span>
  )
}
