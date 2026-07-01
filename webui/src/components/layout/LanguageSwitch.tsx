import { Globe } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'

const languages = [
  { code: 'zh-CN', label: '中文' },
  { code: 'en-US', label: 'EN' },
]

export function LanguageSwitch() {
  const { i18n } = useTranslation()

  const currentLang = languages.find(l => l.code === i18n.language) || languages[0]

  return (
    <Select value={i18n.language} onValueChange={(lang) => i18n.changeLanguage(lang)}>
      <SelectTrigger className="w-20 h-7 text-xs font-mono border-cyber-border-subtle bg-cyber-bg-tertiary/50 hover:border-cyber-neon-cyan/50 transition-colors">
        <Globe className="w-3 h-3 mr-1 text-cyber-text-secondary" />
        <SelectValue>{currentLang.label}</SelectValue>
      </SelectTrigger>
      <SelectContent>
        {languages.map((lang) => (
          <SelectItem key={lang.code} value={lang.code} className="text-xs font-mono">
            {lang.label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}
