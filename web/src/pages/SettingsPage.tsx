import React, { useState } from 'react';
import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import TextField from '@mui/material/TextField';
import Button from '@mui/material/Button';
import Alert from '@mui/material/Alert';
import Divider from '@mui/material/Divider';
import DeleteSweepIcon from '@mui/icons-material/DeleteSweep';
import { useSettingsStore } from '../store/useSettingsStore';
import { useTaskStore } from '../store/useTaskStore';
import { DEFAULT_API_BASE } from '../utils/constants';

export default function SettingsPage() {
  const { apiKey, apiBaseUrl, setApiKey, setApiBaseUrl, loadFromStorage } = useSettingsStore();
  const { cleanupTasks } = useTaskStore();
  const [keyInput, setKeyInput] = useState(apiKey);
  const [urlInput, setUrlInput] = useState(apiBaseUrl);
  const [cleanupHours, setCleanupHours] = useState(72);
  const [saved, setSaved] = useState(false);
  const [cleanupResult, setCleanupResult] = useState<string | null>(null);

  const handleSave = () => {
    setApiKey(keyInput);
    setApiBaseUrl(urlInput);
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  };

  const handleCleanup = async () => {
    const removed = await cleanupTasks(cleanupHours);
    setCleanupResult(`已清理 ${removed} 个过期任务`);
    setTimeout(() => setCleanupResult(null), 5000);
  };

  React.useEffect(() => {
    loadFromStorage();
  }, [loadFromStorage]);

  return (
    <Box>
      <Typography variant="h4" gutterBottom>设置</Typography>

      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>API 配置</Typography>
          <Divider sx={{ mb: 2 }} />
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, maxWidth: 500 }}>
            <TextField
              label="API Base URL"
              value={urlInput}
              onChange={(e) => setUrlInput(e.target.value)}
              placeholder={DEFAULT_API_BASE}
              helperText="后端 API 地址"
            />
            <TextField
              label="API Key"
              type="password"
              value={keyInput}
              onChange={(e) => setKeyInput(e.target.value)}
              placeholder="可选，配置后端认证时需要"
              helperText="存储在浏览器 localStorage 中"
            />
            <Button variant="contained" onClick={handleSave} sx={{ alignSelf: 'flex-start' }}>
              保存
            </Button>
            {saved && <Alert severity="success">设置已保存</Alert>}
          </Box>
        </CardContent>
      </Card>

      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>任务清理</Typography>
          <Divider sx={{ mb: 2 }} />
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, maxWidth: 500 }}>
            <TextField
              label="保留最近 N 小时的任务"
              type="number"
              value={cleanupHours}
              onChange={(e) => setCleanupHours(Number(e.target.value))}
              inputProps={{ min: 1 }}
            />
            <Button
              variant="outlined"
              startIcon={<DeleteSweepIcon />}
              onClick={handleCleanup}
              color="warning"
            >
              清理过期任务
            </Button>
            {cleanupResult && <Alert severity="info">{cleanupResult}</Alert>}
          </Box>
        </CardContent>
      </Card>
    </Box>
  );
}
