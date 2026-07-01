import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { crawlerApi, configApi } from '@/lib/api'
import { useCrawlerStore } from '@/store/crawlerStore'
import type { CrawlerConfig } from '@/types/crawler'

export function useCrawlerStatus() {
  const setStatus = useCrawlerStore((state) => state.setStatus)
  const setRunningInfo = useCrawlerStore((state) => state.setRunningInfo)

  return useQuery({
    queryKey: ['crawlerStatus'],
    queryFn: async () => {
      const { data } = await crawlerApi.getStatus()
      setStatus(data.status)
      setRunningInfo(data.platform, data.crawler_type, data.started_at)
      return data
    },
    refetchInterval: 2000,
  })
}

export function useStartCrawler() {
  const queryClient = useQueryClient()
  const setStatus = useCrawlerStore((state) => state.setStatus)
  const clearLogs = useCrawlerStore((state) => state.clearLogs)

  return useMutation({
    mutationFn: (config: CrawlerConfig) => crawlerApi.start(config),
    onMutate: () => {
      clearLogs()
      setStatus('running')
    },
    onSuccess: () => {
      toast.success('Crawler started successfully')
      queryClient.invalidateQueries({ queryKey: ['crawlerStatus'] })
    },
    onError: (error: Error) => {
      setStatus('idle')
      toast.error(`Failed to start crawler: ${error.message}`)
    },
  })
}

export function useStopCrawler() {
  const queryClient = useQueryClient()
  const setStatus = useCrawlerStore((state) => state.setStatus)

  return useMutation({
    mutationFn: () => crawlerApi.stop(),
    onMutate: () => {
      setStatus('stopping')
    },
    onSuccess: () => {
      toast.success('Crawler stopped')
      setStatus('idle')
      queryClient.invalidateQueries({ queryKey: ['crawlerStatus'] })
    },
    onError: (error: Error) => {
      toast.error(`Failed to stop crawler: ${error.message}`)
    },
  })
}

export function useCrawlerLogs() {
  const setLogs = useCrawlerStore((state) => state.setLogs)

  return useQuery({
    queryKey: ['crawlerLogs'],
    queryFn: async () => {
      const { data } = await crawlerApi.getLogs(500)
      setLogs(data.logs)
      return data.logs
    },
    refetchInterval: false, // Use WebSocket instead
  })
}

export function usePlatforms() {
  return useQuery({
    queryKey: ['platforms'],
    queryFn: async () => {
      const { data } = await configApi.getPlatforms()
      return data.platforms
    },
    staleTime: Infinity,
  })
}

export function useConfigOptions() {
  return useQuery({
    queryKey: ['configOptions'],
    queryFn: async () => {
      const { data } = await configApi.getOptions()
      return data
    },
    staleTime: Infinity,
  })
}
