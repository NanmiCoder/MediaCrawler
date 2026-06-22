import React, { useCallback, useEffect, useRef, useState } from 'react';
import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import TablePagination from '@mui/material/TablePagination';
import FormControl from '@mui/material/FormControl';
import InputLabel from '@mui/material/InputLabel';
import Select from '@mui/material/Select';
import MenuItem from '@mui/material/MenuItem';
import IconButton from '@mui/material/IconButton';
import Tooltip from '@mui/material/Tooltip';
import Chip from '@mui/material/Chip';
import LinearProgress from '@mui/material/LinearProgress';
import Alert from '@mui/material/Alert';
import Button from '@mui/material/Button';
import DeleteIcon from '@mui/icons-material/Delete';
import DownloadIcon from '@mui/icons-material/Download';
import VisibilityIcon from '@mui/icons-material/Visibility';
import AddIcon from '@mui/icons-material/Add';
import RefreshIcon from '@mui/icons-material/Refresh';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useTaskStore } from '../store/useTaskStore';
import { api } from '../api/client';
import StatusBadge from '../components/task/StatusBadge';
import TaskTypeIcon from '../components/task/TaskTypeIcon';
import DeleteConfirmDialog from '../components/task/DeleteConfirmDialog';
import LoadingOverlay from '../components/shared/LoadingOverlay';
import ErrorAlert from '../components/shared/ErrorAlert';
import { formatDateTime, formatDuration } from '../utils/format';
import { PAGE_SIZE } from '../utils/constants';

// TaskListPage 内部用于计算耗时的辅助函数
function calcDuration(startedAt: string | null, completedAt: string | null): string {
  if (!startedAt) return '';
  return formatDuration(startedAt, completedAt);
}

const POLL_INTERVAL = 5000; // 5s 轮询

export default function TaskListPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { tasks, stats, loading, error, fetchTasks, deleteTask, clearError } = useTaskStore();

  const [statusFilter, setStatusFilter] = useState(searchParams.get('status') || '');
  const [typeFilter, setTypeFilter] = useState('');
  const [page, setPage] = useState(0);
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const pollTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const loadTasks = useCallback(async (silent = false) => {
    if (!silent) setRefreshing(true);
    const params: any = { limit: PAGE_SIZE, offset: page * PAGE_SIZE };
    if (statusFilter) params.status = statusFilter;
    if (typeFilter) params.task_type = typeFilter;
    await fetchTasks(params);
    if (!silent) setRefreshing(false);
  }, [statusFilter, typeFilter, page, fetchTasks]);

  // 首次 & 条件变化时加载
  useEffect(() => {
    loadTasks();
  }, [loadTasks]);

  // 有运行中任务时自动轮询
  useEffect(() => {
    const hasRunning = tasks.some((t) => t.status === 'running' || t.status === 'pending');
    if (hasRunning) {
      pollTimerRef.current = setTimeout(() => loadTasks(true), POLL_INTERVAL);
    }
    return () => {
      if (pollTimerRef.current) clearTimeout(pollTimerRef.current);
    };
  }, [tasks, loadTasks]);

  const handleDelete = async () => {
    if (deleteTarget) {
      await deleteTask(deleteTarget);
      setDeleteTarget(null);
    }
  };

  const runningCount = stats?.running ?? 0;
  const pendingCount = stats?.pending ?? 0;

  return (
    <Box>
      {/* 顶部标题栏 */}
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 2, gap: 2 }}>
        <Typography variant="h4" sx={{ flexGrow: 1 }}>任务列表</Typography>
        <Button
          variant="outlined"
          startIcon={<RefreshIcon />}
          size="small"
          onClick={() => loadTasks()}
          disabled={loading || refreshing}
        >
          刷新
        </Button>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          size="small"
          onClick={() => navigate('/create')}
        >
          创建任务
        </Button>
      </Box>

      {/* 后台执行提示 */}
      {(runningCount > 0 || pendingCount > 0) && (
        <Alert severity="info" sx={{ mb: 2 }} icon={false}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Box
              sx={{
                width: 8, height: 8, borderRadius: '50%',
                backgroundColor: '#2196f3',
                animation: 'pulse 1.5s infinite',
                '@keyframes pulse': {
                  '0%': { opacity: 1 },
                  '50%': { opacity: 0.3 },
                  '100%': { opacity: 1 },
                },
              }}
            />
            <Typography variant="body2">
              {runningCount > 0 && `${runningCount} 个任务正在后台执行`}
              {runningCount > 0 && pendingCount > 0 && '，'}
              {pendingCount > 0 && `${pendingCount} 个等待中`}
              &nbsp;— 离开页面不影响后台执行，每 5 秒自动刷新
            </Typography>
          </Box>
        </Alert>
      )}

      {error && <ErrorAlert message={error} onClose={clearError} />}

      <Card>
        <CardContent>
          {/* 筛选栏 */}
          <Box sx={{ display: 'flex', gap: 2, mb: 2, flexWrap: 'wrap', alignItems: 'center' }}>
            <FormControl size="small" sx={{ minWidth: 120 }}>
              <InputLabel>状态</InputLabel>
              <Select value={statusFilter} label="状态" onChange={(e) => { setStatusFilter(e.target.value); setPage(0); }}>
                <MenuItem value="">全部</MenuItem>
                <MenuItem value="pending">
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    待执行
                    {pendingCount > 0 && <Chip label={pendingCount} size="small" color="default" sx={{ height: 18, fontSize: 11 }} />}
                  </Box>
                </MenuItem>
                <MenuItem value="running">
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    执行中
                    {runningCount > 0 && <Chip label={runningCount} size="small" color="primary" sx={{ height: 18, fontSize: 11 }} />}
                  </Box>
                </MenuItem>
                <MenuItem value="completed">已完成</MenuItem>
                <MenuItem value="failed">失败</MenuItem>
              </Select>
            </FormControl>
            <FormControl size="small" sx={{ minWidth: 140 }}>
              <InputLabel>类型</InputLabel>
              <Select value={typeFilter} label="类型" onChange={(e) => { setTypeFilter(e.target.value); setPage(0); }}>
                <MenuItem value="">全部</MenuItem>
                <MenuItem value="search">搜索采集</MenuItem>
                <MenuItem value="comments">评论采集</MenuItem>
                <MenuItem value="scripts">文案提取</MenuItem>
                <MenuItem value="merge">数据合并</MenuItem>
                <MenuItem value="run_all">一键全流程</MenuItem>
              </Select>
            </FormControl>
            <Box sx={{ ml: 'auto' }}>
              <Typography variant="body2" color="text.secondary">
                共 {stats?.total ?? 0} 个任务
              </Typography>
            </Box>
          </Box>

          {loading && tasks.length === 0 ? <LoadingOverlay /> : (
            <>
              {/* 有运行中任务时显示全局进度条 */}
              {(loading || refreshing) && (
                <LinearProgress sx={{ mb: 1, borderRadius: 1 }} />
              )}
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell width={100}>Task ID</TableCell>
                    <TableCell width={130}>类型</TableCell>
                    <TableCell width={110}>状态</TableCell>
                    <TableCell>关键词</TableCell>
                    <TableCell width={140}>创建时间</TableCell>
                    <TableCell width={80}>耗时</TableCell>
                    <TableCell align="right" width={120}>操作</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {tasks.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={7} align="center">
                        <Box sx={{ py: 4 }}>
                          <Typography color="text.secondary" sx={{ mb: 1 }}>暂无任务</Typography>
                          <Button
                            variant="contained"
                            startIcon={<AddIcon />}
                            size="small"
                            onClick={() => navigate('/create')}
                          >
                            立即创建
                          </Button>
                        </Box>
                      </TableCell>
                    </TableRow>
                  ) : (
                    tasks.map((task) => {
                      const isRunning = task.status === 'running';
                      const isPending = task.status === 'pending';
                      const keywords = task.params?.keywords as string[] | undefined;

                      // 计算耗时
                      const duration = calcDuration(task.started_at, task.completed_at);

                      return (
                        <TableRow
                          key={task.task_id}
                          hover
                          sx={{
                            backgroundColor: isRunning
                              ? 'rgba(33, 150, 243, 0.04)'
                              : isPending
                              ? 'rgba(255, 193, 7, 0.04)'
                              : undefined,
                            '&:hover': {
                              backgroundColor: isRunning
                                ? 'rgba(33, 150, 243, 0.08) !important'
                                : undefined,
                            },
                          }}
                        >
                          <TableCell>
                            <code
                              className="font-mono text-xs bg-gray-100 px-1 rounded cursor-pointer hover:bg-gray-200"
                              onClick={() => navigate(`/tasks/${task.task_id}`)}
                            >
                              {task.task_id.slice(0, 8)}
                            </code>
                          </TableCell>
                          <TableCell>
                            <TaskTypeIcon type={task.task_type} />
                          </TableCell>
                          <TableCell>
                            <StatusBadge status={task.status} size="small" />
                          </TableCell>
                          <TableCell>
                            {keywords && keywords.length > 0 ? (
                              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                                {keywords.slice(0, 3).map((kw) => (
                                  <Chip key={kw} label={kw} size="small" variant="outlined" sx={{ height: 20, fontSize: 11 }} />
                                ))}
                                {keywords.length > 3 && (
                                  <Chip label={`+${keywords.length - 3}`} size="small" sx={{ height: 20, fontSize: 11 }} />
                                )}
                              </Box>
                            ) : (
                              <Typography variant="body2" color="text.secondary">—</Typography>
                            )}
                          </TableCell>
                          <TableCell>
                            <Typography variant="body2">{formatDateTime(task.created_at)}</Typography>
                          </TableCell>
                          <TableCell>
                            <Typography variant="body2" color="text.secondary">
                              {duration || '—'}
                            </Typography>
                          </TableCell>
                          <TableCell align="right">
                            <Tooltip title="查看详情">
                              <IconButton size="small" onClick={() => navigate(`/tasks/${task.task_id}`)}>
                                <VisibilityIcon fontSize="small" />
                              </IconButton>
                            </Tooltip>
                            {task.status === 'completed' && (
                              <Tooltip title="下载结果">
                                <IconButton
                                  size="small"
                                  onClick={() => void api.downloadResult(task.task_id)}
                                >
                                  <DownloadIcon fontSize="small" />
                                </IconButton>
                              </Tooltip>
                            )}
                            <Tooltip title="删除">
                              <span>
                                <IconButton
                                  size="small"
                                  onClick={() => setDeleteTarget(task.task_id)}
                                  disabled={isRunning}
                                >
                                  <DeleteIcon fontSize="small" color={isRunning ? 'disabled' : 'error'} />
                                </IconButton>
                              </span>
                            </Tooltip>
                          </TableCell>
                        </TableRow>
                      );
                    })
                  )}
                </TableBody>
              </Table>
              <TablePagination
                component="div"
                count={stats?.total || 0}
                page={page}
                onPageChange={(_, p) => setPage(p)}
                rowsPerPage={PAGE_SIZE}
                rowsPerPageOptions={[PAGE_SIZE]}
                labelDisplayedRows={({ from, to, count }) => `${from}–${to} / ${count}`}
              />
            </>
          )}
        </CardContent>
      </Card>

      <DeleteConfirmDialog
        open={!!deleteTarget}
        taskId={deleteTarget || ''}
        onConfirm={handleDelete}
        onCancel={() => setDeleteTarget(null)}
      />
    </Box>
  );
}
