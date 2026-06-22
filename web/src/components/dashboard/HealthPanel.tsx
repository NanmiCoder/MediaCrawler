import React from 'react';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';
import LinearProgress from '@mui/material/LinearProgress';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ErrorIcon from '@mui/icons-material/Error';
import type { HealthResponse } from '../../api/types';

interface Props {
  health: HealthResponse;
}

export default function HealthPanel({ health }: Props) {
  const checks = [
    {
      label: 'Chrome CDP',
      status: health.checks?.chrome_cdp?.status,
      detail: health.checks?.chrome_cdp?.detail,
    },
    {
      label: '磁盘空间',
      status: health.checks?.disk?.status,
      detail: health.checks?.disk?.detail,
      value: health.checks?.disk?.available_gb,
    },
    {
      label: 'FFmpeg',
      status: health.checks?.ffmpeg?.status,
      detail: health.checks?.ffmpeg?.detail,
    },
  ];

  return (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>系统健康</Typography>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          {checks.map((check) => (
            <Box key={check.label} sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              {check.status === 'ok' || check.status === 'healthy' ? (
                <CheckCircleIcon color="success" />
              ) : (
                <ErrorIcon color="error" />
              )}
              <Typography variant="body2" sx={{ minWidth: 80 }}>{check.label}</Typography>
              <Typography variant="body2" color="text.secondary">
                {check.value ? `${check.value} GB 可用` : check.status || '未知'}
              </Typography>
              {check.detail && (
                <Typography variant="caption" color="text.secondary">({check.detail})</Typography>
              )}
            </Box>
          ))}
        </Box>
        {health.uptime_seconds != null && (
          <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
            运行时间: {Math.floor(health.uptime_seconds / 3600)}h {Math.floor((health.uptime_seconds % 3600) / 60)}m
          </Typography>
        )}
      </CardContent>
    </Card>
  );
}
