import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { dataApi } from '@/lib/api'

// BGM 播放清单（按 run 分组）。返回 groups 供视图按 run 折叠渲染。
export function useBgmPlaylist(runId?: string) {
  return useQuery({
    queryKey: ['bgmPlaylist', runId ?? null],
    queryFn: async () => {
      const { data } = await dataApi.getBgmPlaylist(runId)
      return data
    },
    staleTime: 10_000,
  })
}

// BGM 场景标签映射（aweme_id -> scene）
export function useBgmTags() {
  return useQuery({
    queryKey: ['bgmTags'],
    queryFn: async () => {
      const { data } = await dataApi.getBgmTags()
      return data.tags
    },
    staleTime: 30_000,
  })
}

// 删除 BGM 曲目（从 jsonl 移除行 + 可选删音频文件）
export function useDeleteBgm() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ awemeId, deleteAudio }: { awemeId: string; deleteAudio: boolean }) =>
      dataApi.deleteBgm(awemeId, deleteAudio),
    onSuccess: (res) => {
      const audioMsg = res.data.audio_deleted ? '（含音频文件）' : ''
      toast.success(`已删除 BGM 记录${audioMsg}，移除 ${res.data.removed_rows} 行`)
      queryClient.invalidateQueries({ queryKey: ['bgmPlaylist'] })
    },
    onError: (error: Error) => {
      toast.error(`删除失败: ${error.message}`)
    },
  })
}

// 更新 BGM 场景标签（空字符串=清除）
export function useUpdateBgmScene() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ awemeId, scene }: { awemeId: string; scene: string }) =>
      dataApi.updateBgmScene(awemeId, scene),
    onSuccess: (_res, variables) => {
      toast.success(variables.scene ? '场景标签已保存' : '场景标签已清除')
      queryClient.invalidateQueries({ queryKey: ['bgmTags'] })
    },
    onError: (error: Error) => {
      toast.error(`保存失败: ${error.message}`)
    },
  })
}
