import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import LanguageDetector from 'i18next-browser-languagedetector'

// 中文翻译
import zhCommon from './locales/zh-CN/common.json'
import zhConfig from './locales/zh-CN/config.json'
import zhTerminal from './locales/zh-CN/terminal.json'
import zhData from './locales/zh-CN/data.json'
import zhEnv from './locales/zh-CN/env.json'
import zhLicense from './locales/zh-CN/license.json'

// 英文翻译
import enCommon from './locales/en-US/common.json'
import enConfig from './locales/en-US/config.json'
import enTerminal from './locales/en-US/terminal.json'
import enData from './locales/en-US/data.json'
import enEnv from './locales/en-US/env.json'
import enLicense from './locales/en-US/license.json'

// 越南文翻译
import viCommon from './locales/vi-VN/common.json'
import viConfig from './locales/vi-VN/config.json'
import viTerminal from './locales/vi-VN/terminal.json'
import viData from './locales/vi-VN/data.json'
import viEnv from './locales/vi-VN/env.json'
import viLicense from './locales/vi-VN/license.json'

const resources = {
  'zh-CN': {
    common: zhCommon,
    config: zhConfig,
    terminal: zhTerminal,
    data: zhData,
    env: zhEnv,
    license: zhLicense,
  },
  'en-US': {
    common: enCommon,
    config: enConfig,
    terminal: enTerminal,
    data: enData,
    env: enEnv,
    license: enLicense,
  },
  'vi-VN': {
    common: viCommon,
    config: viConfig,
    terminal: viTerminal,
    data: viData,
    env: viEnv,
    license: viLicense,
  },
}

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources,
    fallbackLng: 'vi-VN',
    defaultNS: 'common',
    interpolation: {
      escapeValue: false,
    },
    detection: {
      order: ['localStorage', 'navigator'],
      caches: ['localStorage'],
      lookupLocalStorage: 'mediacrawler_language',
    },
  })

export default i18n
