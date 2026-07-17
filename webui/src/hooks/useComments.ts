import { useQuery } from '@tanstack/react-query'
import { dataApi } from '@/lib/api'

// 评论清单（按 run 分组）。staleTime 30s，避免频繁刷新。
export function useCommentsPlaylist(runId?: string) {
  return useQuery({
    queryKey: ['commentsPlaylist', runId ?? null],
    queryFn: async () => {
      const { data } = await dataApi.getCommentsPlaylist(runId)
      return data.groups
    },
    staleTime: 30_000,
  })
}
