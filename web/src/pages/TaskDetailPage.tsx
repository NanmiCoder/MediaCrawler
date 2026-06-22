import React, { useEffect, useRef, useState } from 'react';
import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Grid from '@mui/material/Grid';
import Button from '@mui/material/Button';
import Chip from '@mui/material/Chip';
import Divider from '@mui/material/Divider';
import LinearProgress from '@mui/material/LinearProgress';
import Tooltip from '@mui/material/Tooltip';
import IconButton from '@mui/material/IconButton';
import Collapse from '@mui/material/Collapse';
import Paper from '@mui/material/Paper';
import Alert from '@mui/material/Alert';
import DownloadIcon from '@mui/icons-material/Download';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import RefreshIcon from '@mui/icons-material/Refresh';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline';
import ErrorOutlineIcon from '@mui/icons-material/ErrorOutline';
import HourglassTopIcon from '@mui/icons-material/HourglassTop';
import ScheduleIcon from '@mui/icons-material/Schedule';
import FolderOpenIcon from '@mui/icons-material/FolderOpen';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import SearchIcon from '@mui/icons-material/Search';
import CommentIcon from '@mui/icons-material/Comment';
import TextSnippetIcon from '@mui/icons-material/TextSnippet';
import MergeTypeIcon from '@mui/icons-material/MergeType';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import { useParams, useNavigate } from 'react-router-dom';
import { useTaskStore } from '../store/useTaskStore';
import { api } from '../api/client';
import StatusBadge from '../components/task/StatusBadge';
import LoadingOverlay from '../components/shared/LoadingOverlay';
import ErrorAlert from '../components/shared/ErrorAlert';
import { formatDateTime, formatDuration } from '../utils/format';
import { TASK_TYPE_LABELS } from '../utils/constants';
import { useWebSocket } from '../hooks/useWebSocket';

// ─── 步骤定义 ────────────────────────────────────────────────

const STEP_DEFS: Record<string, { steps: string[]; label: string }> = {
  search:   { label: '搜索采集',   steps: ['初始化环境', '关键词搜索', '数据清洗', '保存结果'] },
  comments: { label: '评论采集',   steps: ['初始化环境', '读取视频列表', '批量采集评论', '保存结果'] },
  scripts:  { label: '文案提取',   steps: ['初始化环境', '下载音频', '语音识别', '保存结果'] },
  merge:    { label: '数据合并',   steps: ['读取数据文件', '数据校验', '合并处理', '输出 CSV'] },
  run_all:  { label: '一键全流程', steps: ['搜索采集', '评论采集', '文案提取', '数据合并'] },
};

const TASK_ICONS: Record<string, React.ReactNode> = {
  search:   <SearchIcon fontSize="small" />,
  comments: <CommentIcon fontSize="small" />,
  scripts:  <TextSnippetIcon fontSize="small" />,
  merge:    <MergeTypeIcon fontSize="small" />,
  run_all:  <PlayArrowIcon fontSize="small" />,
};

// ─── 颜色 ─────────────────────────────────────────────────────

const STATUS_COLORS: Record<string, { bg: string; color: string; border: string }> = {
  pending:   { bg: '#f5f5f5',  color: '#757575', border: '#bdbdbd' },
  running:   { bg: '#e3f2fd',  color: '#1565c0', border: '#1976d2' },
  completed: { bg: '#e8f5e9',  color: '#2e7d32', border: '#43a047' },
  failed:    { bg: '#ffebee',  color: '#c62828', border: '#e53935' },
};

// ─── 时间线步骤组件 ───────────────────────────────────────────

function TaskTimeline({
  taskType,
  status,
  progress,
  startedAt,
  completedAt,
  logs,
}: {
  taskType: string;
  status: string;
  progress: string;
  startedAt: string | null;
  completedAt: string | null;
  logs?: Array<{ id: number; timestamp: string; level: string; message: string }>;
}) {
  const def = STEP_DEFS[taskType];
  if (!def) return null;
  const steps = def.steps;

  // 根据 progress 文本粗略判断当前进行到第几步
  const currentStep =
    status === 'completed' ? steps.length :
    status === 'failed'    ? -1 :
    status === 'running'   ? Math.max(1, Math.min(steps.length - 1, Math.round(steps.length / 2))) :
    0;

  return (
    <Box>
      {steps.map((step, idx) => {
        const done    = status === 'completed' || idx < currentStep;
        const active  = status === 'running'   && idx === currentStep;
        const failed  = status === 'failed'    && idx === currentStep;
        const pending = !done && !active && !failed;

        return (
          <Box key={step} sx={{ display: 'flex', gap: 1.5, mb: idx < steps.length - 1 ? 0 : 0 }}>
            {/* 竖线 + 圆点 */}
            <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', minWidth: 24 }}>
              <Box
                sx={{
                  width: 22,
                  height: 22,
                  borderRadius: '50%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  bgcolor:
                    done    ? '#43a047' :
                    active  ? '#1976d2' :
                    failed  ? '#e53935' :
                              '#e0e0e0',
                  color: 'white',
                  fontSize: 12,
                  fontWeight: 700,
                  flexShrink: 0,
                  transition: 'all 0.3s ease',
                  ...(active && {
                    animation: 'pulse 1.5s infinite',
                    '@keyframes pulse': {
                      '0%, 100%': { boxShadow: '0 0 0 0 rgba(25,118,210,0.4)' },
                      '50%':      { boxShadow: '0 0 0 6px rgba(25,118,210,0)' },
                    },
                  }),
                }}
              >
                {done ? '✓' : failed ? '✕' : idx + 1}
              </Box>
              {idx < steps.length - 1 && (
                <Box
                  sx={{
                    width: 2,
                    flex: 1,
                    minHeight: 20,
                    my: 0.5,
                    bgcolor: done ? '#43a047' : '#e0e0e0',
                    transition: 'background-color 0.4s ease',
                  }}
                />
              )}
            </Box>

            {/* 步骤内容 */}
            <Box sx={{ pb: idx < steps.length - 1 ? 2 : 0 }}>
              <Typography
                variant="body2"
                fontWeight={active ? 700 : 400}
                color={
                  done    ? 'text.secondary' :
                  active  ? 'primary.main'   :
                  failed  ? 'error.main'     :
                            'text.disabled'
                }
              >
                {step}
                {active && (
                  <Chip
                    label="进行中"
                    size="small"
                    color="primary"
                    variant="outlined"
                    sx={{ ml: 1, height: 18, fontSize: '0.7rem' }}
                  />
                )}
              </Typography>
              {active && progress && (
                <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.25 }}>
                  {progress}
                </Typography>
              )}
            </Box>
          </Box>
        );
      })}
    </Box>
  );
}

// ─── 参数展示组件 ─────────────────────────────────────────────

function ParamsDisplay({ params }: { params: Record<string, any> }) {
  const [expanded, setExpanded] = useState(false);

  const renderValue = (key: string, val: any) => {
    if (Array.isArray(val)) {
      return (
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
          {val.map((v, i) => (
            <Chip key={i} label={String(v)} size="small" variant="outlined" />
          ))}
        </Box>
      );
    }
    if (val === null || val === undefined || val === '') {
      return <Typography variant="body2" color="text.disabled">—</Typography>;
    }
    return <Typography variant="body2">{String(val)}</Typography>;
  };

  const PARAM_LABELS: Record<string, string> = {
    keywords:    '关键词',
    max_count:   '每词数量',
    steps:       '执行步骤',
    project_dir: '工作目录',
    video_jsonl: '视频文件',
    model:       'Whisper 模型',
    output_csv:  '输出 CSV',
  };

  const entries = Object.entries(params).filter(([, v]) => v !== null && v !== undefined);
  const visible = expanded ? entries : entries.slice(0, 4);

  return (
    <Box>
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
        {visible.map(([k, v]) => (
          <Box key={k} sx={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 2 }}>
            <Typography variant="body2" color="text.secondary" sx={{ minWidth: 80, flexShrink: 0 }}>
              {PARAM_LABELS[k] || k}
            </Typography>
            <Box sx={{ textAlign: 'right' }}>{renderValue(k, v)}</Box>
          </Box>
        ))}
      </Box>
      {entries.length > 4 && (
        <Button
          size="small"
          onClick={() => setExpanded(!expanded)}
          endIcon={expanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
          sx={{ mt: 1, p: 0 }}
        >
          {expanded ? '收起' : `展开全部 (${entries.length})`}
        </Button>
      )}
    </Box>
  );
}

// ─── 结果文件组件 ──────────────────────────────────────────────

function ResultSection({ task }: { task: any }) {
  if (task.status !== 'completed') return null;

  const result = task.result;
  const isContentAsset = task.task_type === 'merge' || Boolean(
    result?.content_asset_csv || result?.content_asset_jsonl || result?.content_asset_stats
  );
  const contentAssetStats = result?.content_asset_stats;
  const resultEntries = result
    ? Object.entries(result).filter(([k]) =>
        k !== 'status' && k !== 'content_asset_stats'
      )
    : [];
  const statsFields = [
    ['rows_in', '输入行数'],
    ['rows_out', '输出行数'],
    ['comments_available', '有评论数据'],
    ['scripts_available', '有文案数据'],
    ['valid_comments_total', '有效评论数'],
    ['asr_available', '真实 ASR 可用'],
    ['fallback_script_total', '降级文案数'],
    ['missing_script_total', '缺失文案数'],
    ['content_asset_csv_generated', 'CSV 已生成'],
  ] as const;

  return (
    <Card sx={{ border: '1px solid #43a047', bgcolor: '#f1f8e9' }}>
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
          <CheckCircleOutlineIcon color="success" />
          <Typography variant="h6" color="success.dark">任务已完成</Typography>
        </Box>

        {isContentAsset && (
          <Paper variant="outlined" sx={{ p: 1.5, mb: 2, bgcolor: '#fff' }}>
            <Typography variant="body2" fontWeight={700}>
              主结果：内容资产表
            </Typography>
            <Typography variant="caption" color="text.secondary">
              content_asset.csv
            </Typography>
          </Paper>
        )}

        {resultEntries.length > 0 && (
          <Box sx={{ mb: 2, display: 'flex', flexDirection: 'column', gap: 1 }}>
            {resultEntries.map(([k, v]) => (
              <Box key={k} sx={{ display: 'flex', justifyContent: 'space-between', gap: 2 }}>
                <Typography variant="body2" color="text.secondary">{k}</Typography>
                <Typography variant="body2" sx={{ fontFamily: 'monospace', wordBreak: 'break-all', textAlign: 'right', maxWidth: '60%' }}>
                  {String(v)}
                </Typography>
              </Box>
            ))}
          </Box>
        )}

        {contentAssetStats && typeof contentAssetStats === 'object' && (
          <Box sx={{ mb: 2 }}>
            <Typography variant="subtitle2" gutterBottom>
              内容资产统计
            </Typography>
            <Box
              sx={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
                gap: 1,
              }}
            >
              {statsFields.map(([key, label]) => (
                contentAssetStats[key] !== undefined && (
                  <Paper key={key} variant="outlined" sx={{ p: 1, bgcolor: '#fff' }}>
                    <Typography variant="caption" color="text.secondary">
                      {label}
                    </Typography>
                    <Typography variant="body2" fontWeight={600}>
                      {typeof contentAssetStats[key] === 'boolean'
                        ? (contentAssetStats[key] ? '是' : '否')
                        : String(contentAssetStats[key])}
                    </Typography>
                  </Paper>
                )
              ))}
            </Box>
            {Array.isArray(contentAssetStats.errors) && contentAssetStats.errors.length > 0 && (
              <Alert severity="warning" sx={{ mt: 1 }}>
                {contentAssetStats.errors.join('；')}
              </Alert>
            )}
          </Box>
        )}

        <Button
          variant="contained"
          color="success"
          startIcon={<DownloadIcon />}
          href={api.getResultUrl(task.task_id)}
          target="_blank"
          size="small"
        >
          {isContentAsset ? '下载内容资产表' : '下载结果文件'}
        </Button>
      </CardContent>
    </Card>
  );
}

// ─── 错误组件 ─────────────────────────────────────────────────

function ErrorSection({ error, exitCode }: { error: string; exitCode: number }) {
  const [showRaw, setShowRaw] = useState(false);

  const exitCodeLabel: Record<number, { label: string; color: 'warning' | 'error' | 'info' }> = {
    1: { label: '可重试 (exit 1)', color: 'warning' },
    2: { label: '参数错误 (exit 2)', color: 'error' },
    3: { label: '致命错误 (exit 3)', color: 'error' },
    4: { label: '服务关闭 (exit 4)', color: 'info' },
  };

  const cfg = exitCodeLabel[exitCode] || { label: `exit ${exitCode}`, color: 'error' as const };
  const isInterrupted = exitCode === 4;

  return (
    <Card sx={{ border: `1px solid ${isInterrupted ? '#0288d1' : '#e53935'}`, bgcolor: isInterrupted ? '#f0f7ff' : '#fff8f8' }}>
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1.5 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <ErrorOutlineIcon sx={{ color: isInterrupted ? '#0288d1' : undefined }} color={isInterrupted ? undefined : 'error'} />
            <Typography variant="h6" sx={{ color: isInterrupted ? '#0288d1' : undefined }} color={isInterrupted ? undefined : 'error.dark'}>
              {isInterrupted ? '任务被中断' : '任务失败'}
            </Typography>
          </Box>
          {exitCode > 0 && (
            <Chip
              label={cfg.label}
              size="small"
              color={cfg.color}
              variant="outlined"
            />
          )}
        </Box>

        {isInterrupted && (
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
            容器重启或进程退出导致任务中断。已采集的数据保存在 workspace 中，可以重新执行任务。
          </Typography>
        )}

        <Typography variant="body2" color={isInterrupted ? 'text.primary' : 'error.main'} sx={{ mb: 1 }}>
          {error.split('\n')[0]}
        </Typography>

        {error.includes('\n') && (
          <>
            <Button size="small" onClick={() => setShowRaw(!showRaw)} sx={{ p: 0 }}>
              {showRaw ? '收起详细' : '查看详细'}
            </Button>
            <Collapse in={showRaw}>
              <Box
                component="pre"
                sx={{
                  mt: 1,
                  p: 1.5,
                  bgcolor: '#1e1e1e',
                  color: '#f48771',
                  borderRadius: 1,
                  fontSize: '0.75rem',
                  overflow: 'auto',
                  maxHeight: 200,
                  fontFamily: '"JetBrains Mono", monospace',
                }}
              >
                {error}
              </Box>
            </Collapse>
          </>
        )}
      </CardContent>
    </Card>
  );
}

// ─── 主组件 ───────────────────────────────────────────────────

export default function TaskDetailPage() {
  const { taskId } = useParams<{ taskId: string }>();
  const navigate = useNavigate();
  const { currentTask, loading, error, fetchTaskDetail, clearError } = useTaskStore();
  const [elapsed, setElapsed] = useState('');
  const [copied, setCopied] = useState(false);
  const { logs, clearLogs } = useWebSocket();
  const [logPanelOpen, setLogPanelOpen] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval>>();

  // 初始加载
  useEffect(() => {
    if (taskId) fetchTaskDetail(taskId);
  }, [taskId, fetchTaskDetail]);

  // running 时每 3s 轮询一次
  useEffect(() => {
    if (currentTask?.status === 'running') {
      pollRef.current = setInterval(() => {
        if (taskId) fetchTaskDetail(taskId);
      }, 3000);
    } else {
      clearInterval(pollRef.current);
    }
    return () => clearInterval(pollRef.current);
  }, [currentTask?.status, taskId, fetchTaskDetail]);

  // 实时计时
  useEffect(() => {
    if (!currentTask || currentTask.status !== 'running') return;
    const timer = setInterval(() => {
      setElapsed(formatDuration(currentTask.started_at, null));
    }, 1000);
    return () => clearInterval(timer);
  }, [currentTask]);

  const handleCopyId = () => {
    if (!currentTask) return;
    navigator.clipboard.writeText(currentTask.task_id);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (loading && !currentTask) return <LoadingOverlay />;
  if (!currentTask) return (
    <Box sx={{ textAlign: 'center', mt: 8 }}>
      <Typography color="text.secondary">任务不存在或已被删除</Typography>
      <Button sx={{ mt: 2 }} onClick={() => navigate('/tasks')}>返回列表</Button>
    </Box>
  );

  const sc = STATUS_COLORS[currentTask.status] || STATUS_COLORS.pending;
  const typeLabel = TASK_TYPE_LABELS[currentTask.task_type] || currentTask.task_type;
  const isRunning = currentTask.status === 'running';
  const isFailed  = currentTask.status === 'failed';
  const isDone    = currentTask.status === 'completed';

  return (
    <Box>
      {/* 顶部导航 */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 3 }}>
        <Button startIcon={<ArrowBackIcon />} onClick={() => navigate('/tasks')} size="small">
          返回列表
        </Button>
        <Box sx={{ flex: 1 }} />
        <Tooltip title="刷新">
          <IconButton size="small" onClick={() => taskId && fetchTaskDetail(taskId)}>
            <RefreshIcon fontSize="small" />
          </IconButton>
        </Tooltip>
      </Box>

      {error && <ErrorAlert message={error} onClose={clearError} />}

      {/* ── 状态大卡片 ── */}
      <Card
        sx={{
          mb: 3,
          border: `2px solid ${sc.border}`,
          bgcolor: sc.bg,
          position: 'relative',
          overflow: 'visible',
        }}
      >
        {isRunning && (
          <LinearProgress
            sx={{
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              borderRadius: '8px 8px 0 0',
              height: 3,
            }}
          />
        )}
        <CardContent sx={{ pt: isRunning ? 2.5 : 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 2, flexWrap: 'wrap' }}>
            {/* 任务类型图标 */}
            <Box
              sx={{
                width: 48,
                height: 48,
                borderRadius: 2,
                bgcolor: sc.border,
                color: 'white',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0,
              }}
            >
              {TASK_ICONS[currentTask.task_type] || <PlayArrowIcon />}
            </Box>

            <Box sx={{ flex: 1, minWidth: 0 }}>
              {/* 类型 + 状态 */}
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5, flexWrap: 'wrap' }}>
                <Typography variant="h5" fontWeight={600} color={sc.color}>
                  {typeLabel}
                </Typography>
                <StatusBadge status={currentTask.status} />
                {isRunning && elapsed && (
                  <Chip
                    icon={<HourglassTopIcon sx={{ fontSize: '14px !important' }} />}
                    label={elapsed}
                    size="small"
                    color="primary"
                    variant="outlined"
                  />
                )}
              </Box>

              {/* Task ID */}
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                <Typography
                  variant="caption"
                  color="text.secondary"
                  sx={{ fontFamily: '"JetBrains Mono", monospace' }}
                >
                  #{currentTask.task_id}
                </Typography>
                <Tooltip title={copied ? '已复制' : '复制 ID'}>
                  <IconButton size="small" onClick={handleCopyId} sx={{ p: 0.25 }}>
                    <ContentCopyIcon sx={{ fontSize: 14 }} />
                  </IconButton>
                </Tooltip>
              </Box>

              {/* 进度文字 */}
              {currentTask.progress && (
                <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                  {currentTask.progress}
                </Typography>
              )}
            </Box>

            {/* 完成时的耗时 */}
            {(isDone || isFailed) && currentTask.started_at && (
              <Box sx={{ textAlign: 'right', flexShrink: 0 }}>
                <Typography variant="caption" color="text.secondary">耗时</Typography>
                <Typography variant="h6" color={sc.color}>
                  {formatDuration(currentTask.started_at, currentTask.completed_at)}
                </Typography>
              </Box>
            )}
          </Box>
        </CardContent>
      </Card>

      {/* ── 主体双栏 ── */}
      <Grid container spacing={3}>

        {/* 左列：执行进度 + 时间线 */}
        <Grid item xs={12} md={5}>
          {/* 执行时间线 */}
          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Typography variant="subtitle1" fontWeight={600} gutterBottom>
                执行步骤
              </Typography>
              <Divider sx={{ mb: 2 }} />
              <TaskTimeline
                taskType={currentTask.task_type}
                status={currentTask.status}
                progress={currentTask.progress}
                startedAt={currentTask.started_at}
                completedAt={currentTask.completed_at}
                logs={logs}
              />
            </CardContent>
          </Card>

          {/* 时间信息 */}
          <Card>
            <CardContent>
              <Typography variant="subtitle1" fontWeight={600} gutterBottom>
                时间记录
              </Typography>
              <Divider sx={{ mb: 2 }} />
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
                <TimeRow icon={<ScheduleIcon fontSize="small" color="action" />} label="创建" value={formatDateTime(currentTask.created_at)} />
                <TimeRow icon={<PlayArrowIcon fontSize="small" color="primary" />} label="开始" value={formatDateTime(currentTask.started_at)} />
                <TimeRow
                  icon={isDone
                    ? <CheckCircleOutlineIcon fontSize="small" color="success" />
                    : <ErrorOutlineIcon fontSize="small" color="error" />}
                  label="结束"
                  value={formatDateTime(currentTask.completed_at)}
                  hidden={isRunning}
                />
                {!isRunning && currentTask.started_at && (
                  <TimeRow
                    icon={<HourglassTopIcon fontSize="small" color="action" />}
                    label="耗时"
                    value={formatDuration(currentTask.started_at, currentTask.completed_at)}
                  />
                )}
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* 右列：参数 + 结果/错误 + workspace */}
        <Grid item xs={12} md={7}>
          {/* 参数 */}
          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Typography variant="subtitle1" fontWeight={600} gutterBottom>
                执行参数
              </Typography>
              <Divider sx={{ mb: 2 }} />
              <ParamsDisplay params={currentTask.params} />
            </CardContent>
          </Card>

          {/* 实时日志面板（任务运行中时显示） */}
          {isRunning && (
            <Card sx={{ mb: 3, border: '1px solid #1976d2' }}>
              <CardContent sx={{ py: 1.5, '&:last-child': { pb: 1.5 } }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Button
                    size="small"
                    startIcon={logPanelOpen ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                    onClick={() => setLogPanelOpen(!logPanelOpen)}
                    color="primary"
                    variant={logPanelOpen ? 'contained' : 'text'}
                    disableElevation
                  >
                    {logPanelOpen ? '收起实时日志' : '查看实时日志'}
                  </Button>
                  {logs.length > 0 && (
                    <Chip
                      label={`${logs.length} 条`}
                      size="small"
                      color="primary"
                      variant="outlined"
                    />
                  )}
                  <Box sx={{ flex: 1 }} />
                  {logs.length > 0 && (
                    <IconButton size="small" onClick={clearLogs} title="清空" color="primary">
                      <Typography variant="caption" sx={{ fontSize: '0.7rem', fontWeight: 600 }}>
                        清空
                      </Typography>
                    </IconButton>
                  )}
                </Box>
                <Collapse in={logPanelOpen}>
                  <Divider sx={{ my: 1.5 }} />
                  <Box
                    sx={{
                      maxHeight: 400,
                      overflow: 'auto',
                      fontFamily: '"JetBrains Mono", "Fira Code", monospace',
                      fontSize: '0.75rem',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: 0.25,
                    }}
                  >
                    {logs.length === 0 ? (
                      <Typography variant="caption" color="text.secondary" sx={{ fontFamily: 'inherit' }}>
                        ⏳ 等待日志输出...
                      </Typography>
                    ) : (
                      logs.map((log) => {
                        const lvl = log.level || 'info';
                        const color =
                          lvl === 'error'   ? '#c62828' :
                          lvl === 'warning' ? '#e65100' :
                          lvl === 'success' ? '#2e7d32' :
                          lvl === 'debug'   ? '#6a1b9a' :
                                               '#263238';
                        return (
                          <Box
                            key={log.id}
                            sx={{
                              display: 'flex',
                              gap: 1,
                              py: 0.15,
                              px: 0.5,
                              borderRadius: 0.5,
                              '&:hover': { bgcolor: '#f5f5f5' },
                            }}
                          >
                            <Typography
                              variant="caption"
                              color="text.disabled"
                              sx={{
                                fontFamily: 'inherit',
                                flexShrink: 0,
                                width: 52,
                                textAlign: 'right',
                                userSelect: 'none',
                              }}
                            >
                              {log.timestamp}
                            </Typography>
                            <Typography
                              variant="caption"
                              sx={{
                                fontFamily: 'inherit',
                                color,
                                flex: 1,
                                wordBreak: 'break-all',
                                whiteSpace: 'pre-wrap',
                                lineHeight: 1.4,
                              }}
                            >
                              {log.message}
                            </Typography>
                          </Box>
                        );
                      })
                    )}
                  </Box>
                </Collapse>
              </CardContent>
            </Card>
          )}

          {/* 结果 */}
          {isDone && (
            <Box sx={{ mb: 3 }}>
              <ResultSection task={currentTask} />
            </Box>
          )}

          {/* 错误 */}
          {isFailed && currentTask.error && (
            <Box sx={{ mb: 3 }}>
              <ErrorSection error={currentTask.error} exitCode={currentTask.exit_code} />
            </Box>
          )}

          {/* Workspace */}
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                <FolderOpenIcon fontSize="small" color="action" />
                <Typography variant="subtitle1" fontWeight={600}>工作目录</Typography>
              </Box>
              <Typography
                variant="body2"
                sx={{
                  fontFamily: '"JetBrains Mono", monospace',
                  fontSize: '0.75rem',
                  bgcolor: '#f5f5f5',
                  p: 1,
                  borderRadius: 1,
                  wordBreak: 'break-all',
                  color: 'text.secondary',
                }}
              >
                {currentTask.workspace}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}

// ─── 辅助组件 ─────────────────────────────────────────────────

function TimeRow({
  icon,
  label,
  value,
  hidden,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  hidden?: boolean;
}) {
  if (hidden) return null;
  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
      {icon}
      <Typography variant="body2" color="text.secondary" sx={{ minWidth: 32 }}>
        {label}
      </Typography>
      <Typography variant="body2" sx={{ ml: 'auto', fontVariantNumeric: 'tabular-nums' }}>
        {value}
      </Typography>
    </Box>
  );
}
