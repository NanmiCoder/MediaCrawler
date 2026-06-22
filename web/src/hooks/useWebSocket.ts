import { useEffect, useRef, useCallback, useState } from 'react';
import { useTaskStore } from '../store/useTaskStore';
import { useSettingsStore } from '../store/useSettingsStore';
import {
  WS_RECONNECT_BASE_MS, WS_RECONNECT_MAX_MS,
  WS_MAX_RETRIES, POLLING_INTERVAL_MS, API_KEY_STORAGE_KEY,
} from '../utils/constants';
import type { WSMessage } from '../api/types';

export type WSStatus = 'connected' | 'connecting' | 'disconnected';

export interface UseWebSocketReturn {
  status: WSStatus;
  logs: Array<{ id: number; timestamp: string; level: string; message: string }>;
  clearLogs: () => void;
}

export function useWebSocket(): UseWebSocketReturn {
  const [status, setStatus] = useState<WSStatus>('disconnected');
  const [logs, setLogs] = useState<Array<{ id: number; timestamp: string; level: string; message: string }>>([]);
  const wsRef = useRef<WebSocket | null>(null);
  const retriesRef = useRef(0);
  const timerRef = useRef<ReturnType<typeof setTimeout>>();
  const pollingRef = useRef<ReturnType<typeof setInterval>>();

  const updateTaskStatus = useTaskStore((s) => s.updateTaskStatus);
  const fetchTasks = useTaskStore((s) => s.fetchTasks);
  const apiBaseUrl = useSettingsStore((s) => s.apiBaseUrl);

  const clearTimers = useCallback(() => {
    if (timerRef.current) clearTimeout(timerRef.current);
    if (pollingRef.current) clearInterval(pollingRef.current);
  }, []);

  const startPolling = useCallback(() => {
    if (pollingRef.current) clearInterval(pollingRef.current);
    fetchTasks({ limit: 50 });
    pollingRef.current = setInterval(() => {
      fetchTasks({ limit: 50 });
    }, POLLING_INTERVAL_MS);
  }, [fetchTasks]);

  const clearLogs = useCallback(() => setLogs([]), []);

  const connect = useCallback(() => {
    clearTimers();
    const wsUrl = apiBaseUrl.replace(/^http/, 'ws') + '/ws/tasks';
    const apiKey = localStorage.getItem(API_KEY_STORAGE_KEY);
    const fullUrl = apiKey ? `${wsUrl}?api_key=${apiKey}` : wsUrl;

    try {
      const ws = new WebSocket(fullUrl);
      wsRef.current = ws;
      setStatus('connecting');

      ws.onopen = () => {
        setStatus('connected');
        retriesRef.current = 0;
        // Stop polling if it was running
        if (pollingRef.current) {
          clearInterval(pollingRef.current);
          pollingRef.current = undefined;
        }
      };

      ws.onmessage = (event) => {
        try {
          const msg: WSMessage = JSON.parse(event.data);

          // Handle task status events
          if (msg.type !== 'log' && 'task_id' in msg) {
            updateTaskStatus(msg.task_id, msg.status, msg.progress);
          }

          // Handle log messages (pushed via same WS connection)
          if (msg.type === 'log') {
            const d = msg.data;
            setLogs((prev) => {
              const next = [...prev, {
                id: d.id ?? prev.length,
                timestamp: d.timestamp ?? '',
                level: d.level ?? 'info',
                message: d.message ?? '',
              }];
              // Keep last 500 logs
              return next.length > 500 ? next.slice(-500) : next;
            });
          }
        } catch {
          // ignore parse errors
        }
      };

      ws.onclose = () => {
        setStatus('disconnected');
        wsRef.current = null;
        scheduleReconnect();
      };

      ws.onerror = () => {
        ws.close();
      };
    } catch {
      setStatus('disconnected');
      scheduleReconnect();
    }
  }, [apiBaseUrl, updateTaskStatus, clearTimers]);

  const scheduleReconnect = useCallback(() => {
    if (retriesRef.current >= WS_MAX_RETRIES) {
      console.warn('WebSocket 重连失败，降级为轮询');
      startPolling();
      return;
    }
    const delay = Math.min(
      WS_RECONNECT_BASE_MS * Math.pow(2, retriesRef.current),
      WS_RECONNECT_MAX_MS
    );
    retriesRef.current++;
    timerRef.current = setTimeout(connect, delay);
  }, [connect, startPolling]);

  useEffect(() => {
    connect();
    return () => {
      wsRef.current?.close();
      clearTimers();
    };
  }, [connect, clearTimers]);

  return { status, logs, clearLogs };
}
