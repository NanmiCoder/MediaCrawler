import { create } from 'zustand';
import { API_KEY_STORAGE_KEY, API_BASE_URL_STORAGE_KEY, DEFAULT_API_BASE } from '../utils/constants';
import { resetClient } from '../api/client';

interface SettingsStore {
  apiKey: string;
  apiBaseUrl: string;
  setApiKey: (key: string) => void;
  setApiBaseUrl: (url: string) => void;
  loadFromStorage: () => void;
}

export const useSettingsStore = create<SettingsStore>((set) => ({
  apiKey: '',
  apiBaseUrl: DEFAULT_API_BASE,

  setApiKey: (key) => {
    localStorage.setItem(API_KEY_STORAGE_KEY, key);
    set({ apiKey: key });
  },

  setApiBaseUrl: (url) => {
    localStorage.setItem(API_BASE_URL_STORAGE_KEY, url);
    resetClient(url);
    set({ apiBaseUrl: url });
  },

  loadFromStorage: () => {
    const key = localStorage.getItem(API_KEY_STORAGE_KEY) || '';
    const url = localStorage.getItem(API_BASE_URL_STORAGE_KEY) || DEFAULT_API_BASE;
    set({ apiKey: key, apiBaseUrl: url });
    if (url !== DEFAULT_API_BASE) {
      resetClient(url);
    }
  },
}));
