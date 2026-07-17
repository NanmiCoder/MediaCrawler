import { create } from 'zustand'

type View = 'crawler' | 'history' | 'bgm' | 'comments'

interface ViewState {
  currentView: View
  setView: (v: View) => void
}

export const useViewStore = create<ViewState>((set) => ({
  currentView: 'crawler',
  setView: (v) => set({ currentView: v }),
}))
