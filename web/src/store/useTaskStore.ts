import { create } from 'zustand';
import { api } from '../api/client';
import type { TaskInfo, TaskStats } from '../api/types';

interface TaskStore {
  tasks: TaskInfo[];
  stats: TaskStats | null;
  loading: boolean;
  error: string | null;
  currentTask: TaskInfo | null;

  fetchTasks: (params?: { task_type?: string; status?: string; limit?: number; offset?: number }) => Promise<void>;
  fetchTaskDetail: (taskId: string) => Promise<void>;
  createTask: (type: string, params: any) => Promise<string | null>;
  deleteTask: (taskId: string) => Promise<void>;
  cleanupTasks: (hours: number) => Promise<number>;
  upsertTask: (task: TaskInfo) => void;
  updateTaskStatus: (taskId: string, status: string, progress?: string) => void;
  setCurrentTask: (task: TaskInfo | null) => void;
  clearError: () => void;
}

export const useTaskStore = create<TaskStore>((set, get) => ({
  tasks: [],
  stats: null,
  loading: false,
  error: null,
  currentTask: null,

  fetchTasks: async (params) => {
    set({ loading: true, error: null });
    try {
      const resp = await api.listTasks(params);
      set({ tasks: resp.tasks, stats: resp.stats, loading: false });
    } catch (e: any) {
      set({ error: e.message || '获取任务列表失败', loading: false });
    }
  },

  fetchTaskDetail: async (taskId) => {
    set({ loading: true, error: null });
    try {
      const task = await api.getTaskStatus(taskId);
      set({ currentTask: task, loading: false });
    } catch (e: any) {
      set({ error: e.message || '获取任务详情失败', loading: false });
    }
  },

  createTask: async (type, params) => {
    set({ loading: true, error: null });
    try {
      let resp;
      switch (type) {
        case 'search': resp = await api.createSearch(params); break;
        case 'comments': resp = await api.createComments(params); break;
        case 'scripts': resp = await api.createScripts(params); break;
        case 'merge': resp = await api.createMerge(params); break;
        case 'run_all': resp = await api.createRunAll(params); break;
        default: throw new Error(`未知任务类型: ${type}`);
      }
      set({ loading: false });
      return resp.task_id;
    } catch (e: any) {
      set({ error: e.message || '创建任务失败', loading: false });
      return null;
    }
  },

  deleteTask: async (taskId) => {
    try {
      await api.deleteTask(taskId);
      set((s) => ({ tasks: s.tasks.filter((t) => t.task_id !== taskId) }));
    } catch (e: any) {
      set({ error: e.message || '删除任务失败' });
    }
  },

  cleanupTasks: async (hours) => {
    try {
      const resp = await api.cleanupTasks(hours);
      return resp.removed || 0;
    } catch (e: any) {
      set({ error: e.message || '清理任务失败' });
      return 0;
    }
  },

  upsertTask: (task) => {
    set((s) => {
      const idx = s.tasks.findIndex((t) => t.task_id === task.task_id);
      if (idx >= 0) {
        const newTasks = [...s.tasks];
        newTasks[idx] = task;
        return { tasks: newTasks };
      }
      return { tasks: [task, ...s.tasks] };
    });
  },

  updateTaskStatus: (taskId, status, progress) => {
    set((s) => ({
      tasks: s.tasks.map((t) =>
        t.task_id === taskId
          ? { ...t, status: status as TaskInfo['status'], progress: progress ?? t.progress }
          : t
      ),
      currentTask: s.currentTask?.task_id === taskId
        ? { ...s.currentTask, status: status as TaskInfo['status'], progress: progress ?? s.currentTask.progress }
        : s.currentTask,
    }));
  },

  setCurrentTask: (task) => set({ currentTask: task }),
  clearError: () => set({ error: null }),
}));
