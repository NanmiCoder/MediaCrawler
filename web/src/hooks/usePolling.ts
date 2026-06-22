import { useEffect, useRef } from 'react';
import { useTaskStore } from '../store/useTaskStore';
import { POLLING_INTERVAL_MS } from '../utils/constants';

export function usePolling(enabled: boolean, params?: Record<string, any>) {
  const fetchTasks = useTaskStore((s) => s.fetchTasks);
  const timerRef = useRef<ReturnType<typeof setInterval>>();

  useEffect(() => {
    if (!enabled) return;
    fetchTasks(params as any);
    timerRef.current = setInterval(() => fetchTasks(params as any), POLLING_INTERVAL_MS);
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [enabled, fetchTasks]);
}
