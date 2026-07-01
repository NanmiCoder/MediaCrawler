import React, { useState } from 'react';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';
import TextField from '@mui/material/TextField';
import Button from '@mui/material/Button';
import Slider from '@mui/material/Slider';
import Select from '@mui/material/Select';
import MenuItem from '@mui/material/MenuItem';
import InputLabel from '@mui/material/InputLabel';
import FormControl from '@mui/material/FormControl';
import ToggleButton from '@mui/material/ToggleButton';
import ToggleButtonGroup from '@mui/material/ToggleButtonGroup';
import Alert from '@mui/material/Alert';
import Snackbar from '@mui/material/Snackbar';
import Grid from '@mui/material/Grid';
import { useNavigate } from 'react-router-dom';
import { useTaskStore } from '../store/useTaskStore';
import { TASK_TYPE_LABELS, WHISPER_MODELS } from '../utils/constants';
import ErrorAlert from '../components/shared/ErrorAlert';

const TASK_TYPES = ['search', 'comments', 'scripts', 'merge', 'run_all'] as const;

export default function CreateTaskPage() {
  const navigate = useNavigate();
  const { loading, error, createTask, clearError } = useTaskStore();
  const [taskType, setTaskType] = useState<string>('search');
  const [keywords, setKeywords] = useState('');
  const [maxCount, setMaxCount] = useState(20);
  const [model, setModel] = useState('small');
  const [videoJsonl, setVideoJsonl] = useState('');
  const [commentsJsonl, setCommentsJsonl] = useState('');
  const [scriptsJsonl, setScriptsJsonl] = useState('');
  const [snackOpen, setSnackOpen] = useState(false);
  const [createdId, setCreatedId] = useState('');

  const parsedKeywords = keywords
    .split(/[\n,]/)
    .map((s) => s.trim())
    .filter(Boolean);

  const handleSubmit = async () => {
    clearError();
    let taskId: string | null = null;

    switch (taskType) {
      case 'search':
        taskId = await createTask('search', {
          keywords: parsedKeywords,
          max_count: maxCount,
        });
        break;
      case 'comments':
        taskId = await createTask('comments', { video_jsonl: videoJsonl || undefined });
        break;
      case 'scripts':
        taskId = await createTask('scripts', { video_jsonl: videoJsonl || undefined, model });
        break;
      case 'merge':
        taskId = await createTask('merge', {
          video_jsonl: videoJsonl || undefined,
          comments_jsonl: commentsJsonl || undefined,
          scripts_jsonl: scriptsJsonl || undefined,
        });
        break;
      case 'run_all':
        taskId = await createTask('run_all', {
          keywords: parsedKeywords,
          max_count: maxCount,
        });
        break;
    }

    if (taskId) {
      setCreatedId(taskId);
      setSnackOpen(true);
      setTimeout(() => navigate(`/tasks/${taskId}`), 1500);
    }
  };

  const showKeywords = taskType === 'search' || taskType === 'run_all';
  const showMaxCount = taskType === 'search' || taskType === 'run_all';
  const showVideoInput = taskType === 'comments' || taskType === 'scripts' || taskType === 'merge';
  const showCommentsInput = taskType === 'merge';
  const showScriptsInput = taskType === 'merge';
  const showModel = taskType === 'scripts';

  const canSubmit = (() => {
    if (taskType === 'search' || taskType === 'run_all') return parsedKeywords.length > 0;
    return true;
  })();

  return (
    <Box>
      <Typography variant="h4" gutterBottom>创建任务</Typography>
      {error && <ErrorAlert message={error} onClose={clearError} />}

      <Grid container spacing={3}>
        <Grid item xs={12} md={8}>
          <Card>
            <CardContent sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
              {/* 任务类型选择 */}
              <FormControl fullWidth>
                <InputLabel>任务类型</InputLabel>
                <Select value={taskType} label="任务类型" onChange={(e) => setTaskType(e.target.value)}>
                  {TASK_TYPES.map((t) => (
                    <MenuItem key={t} value={t}>{TASK_TYPE_LABELS[t]}</MenuItem>
                  ))}
                </Select>
              </FormControl>

              {/* 关键词输入 */}
              {showKeywords && (
                <>
                  <TextField
                    label="搜索关键词"
                    placeholder="每行一个关键词，最多 50 个"
                    multiline
                    rows={4}
                    value={keywords}
                    onChange={(e) => setKeywords(e.target.value)}
                    helperText={`已输入 ${parsedKeywords.length}/50 个关键词`}
                    error={parsedKeywords.length > 50}
                  />
                </>
              )}

              {/* 最大采集数 */}
              {showMaxCount && (
                <Box>
                  <Typography variant="body2" color="text.secondary" gutterBottom>
                    每个关键词最大采集数: {maxCount}
                  </Typography>
                  <Slider
                    value={maxCount}
                    onChange={(_, v) => setMaxCount(v as number)}
                    min={1}
                    max={200}
                    valueLabelDisplay="auto"
                  />
                </Box>
              )}

              {/* 视频文件路径 */}
              {showVideoInput && (
                <TextField
                  label="视频 JSONL 路径（可选）"
                  value={videoJsonl}
                  onChange={(e) => setVideoJsonl(e.target.value)}
                  placeholder="留空使用上次搜索结果"
                />
              )}

              {/* 评论文件路径 */}
              {showCommentsInput && (
                <TextField
                  label="评论 JSONL 路径（可选）"
                  value={commentsJsonl}
                  onChange={(e) => setCommentsJsonl(e.target.value)}
                />
              )}

              {/* 文案文件路径 */}
              {showScriptsInput && (
                <TextField
                  label="文案 JSONL 路径（可选）"
                  value={scriptsJsonl}
                  onChange={(e) => setScriptsJsonl(e.target.value)}
                />
              )}

              {/* Whisper 模型选择 */}
              {showModel && (
                <FormControl fullWidth>
                  <InputLabel>Whisper 模型</InputLabel>
                  <Select value={model} label="Whisper 模型" onChange={(e) => setModel(e.target.value)}>
                    {WHISPER_MODELS.map((m) => (
                      <MenuItem key={m.value} value={m.value}>{m.label}</MenuItem>
                    ))}
                  </Select>
                </FormControl>
              )}

              {/* 提交按钮 */}
              <Button
                variant="contained"
                size="large"
                disabled={!canSubmit || loading}
                onClick={handleSubmit}
                sx={{ mt: 1 }}
              >
                {loading ? '提交中...' : '提交任务'}
              </Button>
            </CardContent>
          </Card>
        </Grid>

        {/* 参数预览 */}
        <Grid item xs={12} md={4}>
          <Card sx={{ position: 'sticky', top: 24 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>参数预览</Typography>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                <Typography variant="body2">
                  <strong>类型:</strong> {TASK_TYPE_LABELS[taskType]}
                </Typography>
                {showKeywords && (
                  <Typography variant="body2">
                    <strong>关键词数:</strong> {parsedKeywords.length}
                  </Typography>
                )}
                {showMaxCount && (
                  <Typography variant="body2">
                    <strong>最大采集数:</strong> {maxCount}
                  </Typography>
                )}
                {showModel && (
                  <Typography variant="body2">
                    <strong>Whisper 模型:</strong> {model}
                  </Typography>
                )}
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Snackbar
        open={snackOpen}
        autoHideDuration={3000}
        onClose={() => setSnackOpen(false)}
        message={`任务已创建: ${createdId.slice(0, 8)}...`}
      />
    </Box>
  );
}
