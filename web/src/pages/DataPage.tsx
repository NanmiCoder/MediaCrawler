import React, { useCallback, useEffect, useState } from 'react';
import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import Checkbox from '@mui/material/Checkbox';
import Button from '@mui/material/Button';
import IconButton from '@mui/material/IconButton';
import Tooltip from '@mui/material/Tooltip';
import Chip from '@mui/material/Chip';
import Divider from '@mui/material/Divider';
import CircularProgress from '@mui/material/CircularProgress';
import LinearProgress from '@mui/material/LinearProgress';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogActions from '@mui/material/DialogActions';
import ToggleButton from '@mui/material/ToggleButton';
import ToggleButtonGroup from '@mui/material/ToggleButtonGroup';
import Alert from '@mui/material/Alert';
import Stack from '@mui/material/Stack';
import Paper from '@mui/material/Paper';
import TableContainer from '@mui/material/TableContainer';
import Collapse from '@mui/material/Collapse';
import DownloadIcon from '@mui/icons-material/Download';
import PreviewIcon from '@mui/icons-material/Preview';
import RefreshIcon from '@mui/icons-material/Refresh';
import StorageIcon from '@mui/icons-material/Storage';
import CheckBoxOutlineBlankIcon from '@mui/icons-material/CheckBoxOutlineBlank';
import CheckBoxIcon from '@mui/icons-material/CheckBox';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import ArticleIcon from '@mui/icons-material/Article';
import GridOnIcon from '@mui/icons-material/GridOn';
import ViewColumnIcon from '@mui/icons-material/ViewColumn';

import { api } from '../api/client';
import type { DataFileItem, DataPreviewResponse } from '../api/types';
import { formatDateTime, formatFileSize } from '../utils/format';
import TaskTypeIcon from '../components/task/TaskTypeIcon';
import ErrorAlert from '../components/shared/ErrorAlert';

const PRIMARY_FILE_PRIORITY = [
  'content_asset.csv',
  'script_clean.csv',
  'comments_clean.csv',
  'search_result.csv',
  'content_asset.jsonl',
  'script_clean.jsonl',
  'comments_clean.jsonl',
  'search_result.jsonl',
];

const CONTENT_ASSET_CORE_COLUMNS = [
  'source_keyword',
  'platform',
  'aweme_id',
  'clean_title',
  'topic',
  'pain_point',
  'teaching_angle',
  'nickname',
  'liked_count',
  'collected_count',
  'comment_count',
  'share_count',
  'total_engagement',
  'valid_comment_count',
  'comment_data_status',
  'asr_data_status',
  'asset_quality',
];

const LONG_TEXT_COLUMNS = new Set([
  'script_text',
  'script_clean_text',
  'top_valid_comments',
  'comment_pain_tags',
  'desc',
  'clean_desc',
]);

function filePriority(item: DataFileItem): number {
  const exact = PRIMARY_FILE_PRIORITY.indexOf(item.file_name);
  if (exact >= 0) return exact;
  if (item.file_name.endsWith('.csv')) return PRIMARY_FILE_PRIORITY.length;
  if (item.file_name.endsWith('.jsonl')) return PRIMARY_FILE_PRIORITY.length + 1;
  return PRIMARY_FILE_PRIORITY.length + 2;
}

function selectPrimaryFiles(items: DataFileItem[]): DataFileItem[] {
  const grouped = new Map<string, DataFileItem[]>();
  items
    .filter((item) => item.file_name !== 'execution_log.jsonl')
    .forEach((item) => {
      const group = grouped.get(item.task_id) || [];
      group.push(item);
      grouped.set(item.task_id, group);
    });

  return Array.from(grouped.values()).map((files) =>
    [...files].sort((a, b) => filePriority(a) - filePriority(b))[0]
  );
}

function fileLabel(item: DataFileItem): string {
  if (item.file_name.startsWith('content_asset.') || item.task_type === 'merge') {
    return '内容资产表';
  }
  if (item.file_name.startsWith('search_result.')) return '搜索结果表';
  if (item.file_name.startsWith('comments_clean.')) return '评论清洗表';
  if (item.file_name.startsWith('script_clean.')) return '文案清洗表';
  return '结果文件';
}

function fileFormat(fileName: string): string {
  return fileName.split('.').pop()?.toUpperCase() || 'FILE';
}

// ─── 预览对话框 ────────────────────────────────────────────────

function PreviewDialog({
  open, taskId, onClose,
}: { open: boolean; taskId: string | null; onClose: () => void }) {
  const [data, setData] = useState<DataPreviewResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState('');
  const [showAllColumns, setShowAllColumns] = useState(false);

  useEffect(() => {
    if (!open || !taskId) return;
    setLoading(true);
    setErr('');
    setData(null);
    setShowAllColumns(false);
    api.previewData(taskId, 20)
      .then(setData)
      .catch((e) => setErr(e.message || '预览失败'))
      .finally(() => setLoading(false));
  }, [open, taskId]);

  const allColumns = data?.rows?.[0] ? Object.keys(data.rows[0]) : [];
  const isContentAsset = data?.file_name.startsWith('content_asset.') ?? false;
  const columns = isContentAsset && !showAllColumns
    ? CONTENT_ASSET_CORE_COLUMNS.filter((column) => allColumns.includes(column))
    : allColumns;

  return (
    <Dialog open={open} onClose={onClose} maxWidth="lg" fullWidth scroll="paper">
      <DialogTitle>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <PreviewIcon color="primary" />
          <span>数据预览</span>
          {data && (
            <>
              <Chip
                label={isContentAsset ? '内容资产表' : data.file_name}
                size="small"
                color={isContentAsset ? 'primary' : 'default'}
                variant="outlined"
                sx={{ ml: 1 }}
              />
              <Chip
                label={`${data.format?.toUpperCase() || fileFormat(data.file_name)} · 共 ${data.total_rows} 行`}
                size="small"
                variant="outlined"
              />
            </>
          )}
          <Box sx={{ flex: 1 }} />
          {isContentAsset && data && (
            <Button
              size="small"
              variant="outlined"
              startIcon={<ViewColumnIcon />}
              onClick={() => setShowAllColumns((value) => !value)}
            >
              {showAllColumns ? '只看核心字段' : '查看全部字段'}
            </Button>
          )}
        </Box>
      </DialogTitle>
      <DialogContent dividers>
        {loading && <LinearProgress sx={{ mb: 2 }} />}
        {err && <Alert severity="error">{err}</Alert>}
        {data && data.rows.length > 0 && (
          <TableContainer component={Paper} variant="outlined">
            <Table size="small" stickyHeader>
              <TableHead>
                <TableRow>
                  {columns.map((col) => (
                    <TableCell key={col} sx={{ fontWeight: 600, whiteSpace: 'nowrap' }}>
                      {col}
                    </TableCell>
                  ))}
                </TableRow>
              </TableHead>
              <TableBody>
                {data.rows.map((row, i) => (
                  <TableRow key={i} hover>
                    {columns.map((col) => (
                      <TableCell
                        key={col}
                        sx={{
                          minWidth: LONG_TEXT_COLUMNS.has(col) ? 240 : 110,
                          maxWidth: LONG_TEXT_COLUMNS.has(col) ? 360 : 180,
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap',
                          fontSize: 12,
                        }}
                      >
                        <Tooltip title={String(row[col] ?? '')} placement="top" arrow>
                          <span>{String(row[col] ?? '')}</span>
                        </Tooltip>
                      </TableCell>
                    ))}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        )}
        {data && data.rows.length === 0 && (
          <Typography color="text.secondary" align="center" sx={{ py: 4 }}>
            文件为空
          </Typography>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>关闭</Button>
      </DialogActions>
    </Dialog>
  );
}

// ─── 导出对话框 ────────────────────────────────────────────────

function ExportDialog({
  open,
  selectedIds,
  selectedItems,
  onClose,
}: {
  open: boolean;
  selectedIds: string[];
  selectedItems: DataFileItem[];
  onClose: () => void;
}) {
  const [format, setFormat] = useState<'csv' | 'txt'>('csv');
  const [exporting, setExporting] = useState(false);
  const [err, setErr] = useState('');
  const [showFormatGuide, setShowFormatGuide] = useState(false);

  const totalRows = selectedItems.reduce((s, i) => s + i.row_count, 0);
  const totalSize = selectedItems.reduce((s, i) => s + i.file_size, 0);
  const willTruncate = totalRows > 200;

  const handleExport = async () => {
    setExporting(true);
    setErr('');
    try {
      const { blob, filename } = await api.exportData({
        task_ids: selectedIds,
        format,
        limit: 200,
      });
      // 触发浏览器下载
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      setTimeout(() => {
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      }, 100);
      onClose();
    } catch (e: any) {
      setErr(e.message || '导出失败，请重试');
    } finally {
      setExporting(false);
    }
  };

  return (
    <Dialog open={open} onClose={!exporting ? onClose : undefined} maxWidth="sm" fullWidth>
      <DialogTitle>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <DownloadIcon color="primary" />
          <span>批量导出数据</span>
        </Box>
      </DialogTitle>
      <DialogContent>
        <Stack spacing={2}>
          {/* 选中概览 */}
          <Paper variant="outlined" sx={{ p: 2, borderRadius: 2, backgroundColor: 'rgba(33,150,243,0.04)' }}>
            <Typography variant="body2" fontWeight={600} gutterBottom>已选中</Typography>
            <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
              <Chip icon={<StorageIcon />} label={`${selectedIds.length} 个任务`} size="small" />
              <Chip label={`${totalRows} 行数据`} size="small" color={willTruncate ? 'warning' : 'default'} />
              <Chip label={formatFileSize(totalSize)} size="small" />
            </Box>
            {willTruncate && (
              <Alert severity="warning" sx={{ mt: 1, py: 0 }}>
                数据超过 200 行上限，将自动截断至前 200 行
              </Alert>
            )}
          </Paper>

          {/* 格式选择 */}
          <Box>
            <Typography variant="body2" fontWeight={600} gutterBottom>选择导出格式</Typography>
            <ToggleButtonGroup
              value={format}
              exclusive
              onChange={(_, v) => v && setFormat(v)}
              size="small"
            >
              <ToggleButton value="csv" sx={{ gap: 1, px: 3 }}>
                <GridOnIcon fontSize="small" />
                CSV
              </ToggleButton>
              <ToggleButton value="txt" sx={{ gap: 1, px: 3 }}>
                <ArticleIcon fontSize="small" />
                TXT
              </ToggleButton>
            </ToggleButtonGroup>
          </Box>

          {/* 格式说明（可折叠） */}
          <Box>
            <Button
              size="small"
              onClick={() => setShowFormatGuide(!showFormatGuide)}
              endIcon={showFormatGuide ? <ExpandLessIcon /> : <ExpandMoreIcon />}
              sx={{ color: 'text.secondary', p: 0 }}
            >
              格式说明
            </Button>
            <Collapse in={showFormatGuide}>
              <Paper variant="outlined" sx={{ p: 1.5, mt: 1, borderRadius: 1, backgroundColor: '#fafafa' }}>
                {format === 'csv' ? (
                  <>
                    <Typography variant="caption" color="text.secondary" display="block" gutterBottom>
                      CSV 格式：标准逗号分隔，UTF-8 编码
                    </Typography>
                    <Typography variant="caption" component="pre" sx={{ fontFamily: 'monospace', fontSize: 11, color: '#333' }}>
                      {`列：video_id, platform, script_text,\n     likes, favorites, shares, comments\n评论多值用 | 分隔`}
                    </Typography>
                  </>
                ) : (
                  <>
                    <Typography variant="caption" color="text.secondary" display="block" gutterBottom>
                      TXT 格式：每行一条，字段用 || 分隔，UTF-8 编码
                    </Typography>
                    <Typography variant="caption" component="pre" sx={{ fontFamily: 'monospace', fontSize: 11, color: '#333', whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
                      {`video_id||script_text||likes||favorites||shares||comments\n\n上限：200 行 / 2MB`}
                    </Typography>
                  </>
                )}
              </Paper>
            </Collapse>
          </Box>

          {err && <Alert severity="error">{err}</Alert>}
        </Stack>
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button onClick={onClose} disabled={exporting}>取消</Button>
        <Button
          variant="contained"
          startIcon={exporting ? <CircularProgress size={14} color="inherit" /> : <DownloadIcon />}
          onClick={handleExport}
          disabled={exporting || selectedIds.length === 0}
        >
          {exporting ? '导出中…' : `导出 ${format.toUpperCase()}`}
        </Button>
      </DialogActions>
    </Dialog>
  );
}

// ─── 主页面 ─────────────────────────────────────────────────────

export default function DataPage() {
  const [items, setItems] = useState<DataFileItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState('');
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [previewTaskId, setPreviewTaskId] = useState<string | null>(null);
  const [exportOpen, setExportOpen] = useState(false);

  const loadData = useCallback(async () => {
    setLoading(true);
    setErr('');
    try {
      const resp = await api.listDataFiles();
      setItems(selectPrimaryFiles(resp.items));
    } catch (e: any) {
      setErr(e.message || '获取数据列表失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const allSelected = items.length > 0 && selected.size === items.length;
  const someSelected = selected.size > 0 && !allSelected;

  const toggleAll = () => {
    if (allSelected) {
      setSelected(new Set());
    } else {
      setSelected(new Set(items.map((i) => i.task_id)));
    }
  };

  const toggleItem = (taskId: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(taskId)) next.delete(taskId);
      else next.add(taskId);
      return next;
    });
  };

  const selectedItems = items.filter((i) => selected.has(i.task_id));
  const totalSelectedRows = selectedItems.reduce((s, i) => s + i.row_count, 0);
  const totalSelectedSize = selectedItems.reduce((s, i) => s + i.file_size, 0);

  return (
    <Box>
      {/* 标题栏 */}
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 2, gap: 2 }}>
        <StorageIcon color="primary" />
        <Typography variant="h4" sx={{ flexGrow: 1 }}>数据管理</Typography>
        <Button
          variant="outlined"
          startIcon={<RefreshIcon />}
          size="small"
          onClick={loadData}
          disabled={loading}
        >
          刷新
        </Button>
        <Button
          variant="contained"
          startIcon={<DownloadIcon />}
          size="small"
          disabled={selected.size === 0}
          onClick={() => setExportOpen(true)}
        >
          批量导出旧七字段 {selected.size > 0 && `(${selected.size})`}
        </Button>
      </Box>

      {err && <ErrorAlert message={err} onClose={() => setErr('')} />}

      {/* 选中状态栏 */}
      {selected.size > 0 && (
        <Alert
          severity="info"
          icon={false}
          sx={{ mb: 2 }}
          action={
            <Button size="small" color="inherit" onClick={() => setSelected(new Set())}>
              取消全选
            </Button>
          }
        >
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Typography variant="body2">
              已选 <strong>{selected.size}</strong> 个任务
            </Typography>
            <Chip label={`${totalSelectedRows} 行`} size="small" />
            <Chip label={formatFileSize(totalSelectedSize)} size="small" />
            {totalSelectedRows > 200 && (
              <Chip label="超出 200 行上限，将截断" size="small" color="warning" />
            )}
          </Box>
        </Alert>
      )}

      <Card>
        {loading && <LinearProgress />}
        <CardContent>
          {items.length === 0 && !loading ? (
            <Box sx={{ py: 8, textAlign: 'center' }}>
              <StorageIcon sx={{ fontSize: 48, color: 'text.disabled', mb: 1 }} />
              <Typography color="text.secondary">
                暂无可导出的数据
              </Typography>
              <Typography variant="body2" color="text.disabled" sx={{ mt: 0.5 }}>
                完成采集任务后，结果数据将在此显示
              </Typography>
            </Box>
          ) : (
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell padding="checkbox">
                    <Checkbox
                      indeterminate={someSelected}
                      checked={allSelected}
                      onChange={toggleAll}
                      icon={<CheckBoxOutlineBlankIcon />}
                      checkedIcon={<CheckBoxIcon />}
                    />
                  </TableCell>
                  <TableCell width={100}>Task ID</TableCell>
                  <TableCell width={130}>类型</TableCell>
                  <TableCell>主结果文件</TableCell>
                  <TableCell width={80}>格式</TableCell>
                  <TableCell width={100} align="right">行数</TableCell>
                  <TableCell width={100} align="right">文件大小</TableCell>
                  <TableCell width={140}>完成时间</TableCell>
                  <TableCell align="right" width={100}>操作</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {items.map((item) => (
                  <TableRow
                    key={`${item.task_id}:${item.file_path}`}
                    hover
                    selected={selected.has(item.task_id)}
                    sx={{
                      cursor: 'pointer',
                      backgroundColor: selected.has(item.task_id)
                        ? 'rgba(33,150,243,0.06) !important'
                        : undefined,
                    }}
                    onClick={() => toggleItem(item.task_id)}
                  >
                    <TableCell padding="checkbox" onClick={(e) => e.stopPropagation()}>
                      <Checkbox
                        checked={selected.has(item.task_id)}
                        onChange={() => toggleItem(item.task_id)}
                      />
                    </TableCell>
                    <TableCell>
                      <code className="font-mono text-xs bg-gray-100 px-1 rounded">
                        {item.task_id.slice(0, 8)}
                      </code>
                    </TableCell>
                    <TableCell>
                      <TaskTypeIcon type={item.task_type} />
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" fontWeight={600}>
                        {fileLabel(item)}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {item.file_name}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={fileFormat(item.file_name)}
                        size="small"
                        variant="outlined"
                      />
                    </TableCell>
                    <TableCell align="right">
                      <Typography variant="body2" fontWeight={600}>
                        {item.row_count.toLocaleString()}
                      </Typography>
                    </TableCell>
                    <TableCell align="right">
                      <Typography variant="body2" color="text.secondary">
                        {formatFileSize(item.file_size)}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2">{formatDateTime(item.created_at)}</Typography>
                    </TableCell>
                    <TableCell align="right" onClick={(e) => e.stopPropagation()}>
                      <Tooltip title="预览数据">
                        <IconButton
                          size="small"
                          onClick={() => setPreviewTaskId(item.task_id)}
                        >
                          <PreviewIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="下载原始文件">
                        <IconButton
                          size="small"
                          component="a"
                          href={api.getDataExportUrl(item.task_id)}
                          target="_blank"
                          rel="noreferrer"
                        >
                          <DownloadIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <Alert severity="info" sx={{ mt: 2 }}>
        “下载原始文件”会保留 content_asset.csv 的完整字段；“批量导出旧七字段”会统一导出
        video_id、platform、script_text、likes、favorites、shares、comments。
      </Alert>

      {/* 格式说明卡片 */}
      <Card sx={{ mt: 2 }}>
        <CardContent>
          <Typography variant="subtitle2" gutterBottom>批量旧格式说明</Typography>
          <Divider sx={{ mb: 2 }} />
          <Box sx={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
            <Box sx={{ flex: 1, minWidth: 260 }}>
              <Typography variant="body2" fontWeight={600} gutterBottom>
                <GridOnIcon sx={{ fontSize: 16, mr: 0.5, verticalAlign: 'middle' }} />
                CSV 格式
              </Typography>
              <Paper variant="outlined" sx={{ p: 1.5, fontFamily: 'monospace', fontSize: 12, backgroundColor: '#fafafa' }}>
                video_id, platform, script_text,<br />
                likes, favorites, shares, comments<br />
                <Typography variant="caption" color="text.secondary">（comments 多值用 | 分隔）</Typography>
              </Paper>
            </Box>
            <Box sx={{ flex: 1, minWidth: 260 }}>
              <Typography variant="body2" fontWeight={600} gutterBottom>
                <ArticleIcon sx={{ fontSize: 16, mr: 0.5, verticalAlign: 'middle' }} />
                TXT 格式
              </Typography>
              <Paper variant="outlined" sx={{ p: 1.5, fontFamily: 'monospace', fontSize: 12, backgroundColor: '#fafafa' }}>
                video_id||script_text||likes<br />
                ||favorites||shares||comments<br />
                <Typography variant="caption" color="text.secondary">
                  字段用 || 分隔 · 上限 200 行 / 2MB · UTF-8
                </Typography>
              </Paper>
            </Box>
          </Box>
        </CardContent>
      </Card>

      {/* 预览对话框 */}
      <PreviewDialog
        open={!!previewTaskId}
        taskId={previewTaskId}
        onClose={() => setPreviewTaskId(null)}
      />

      {/* 导出对话框 */}
      <ExportDialog
        open={exportOpen}
        selectedIds={Array.from(selected)}
        selectedItems={selectedItems}
        onClose={() => setExportOpen(false)}
      />
    </Box>
  );
}
