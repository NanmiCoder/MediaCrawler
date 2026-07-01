import React from 'react';
import CircleIcon from '@mui/icons-material/Circle';
import Tooltip from '@mui/material/Tooltip';
import { type WSStatus } from '../../hooks/useWebSocket';

interface Props {
  status: WSStatus;
}

const STATUS_MAP: Record<WSStatus, { color: string; label: string }> = {
  connected: { color: '#4caf50', label: 'WebSocket 已连接' },
  connecting: { color: '#ff9800', label: 'WebSocket 连接中...' },
  disconnected: { color: '#f44336', label: 'WebSocket 已断开' },
};

export default function ConnectionIndicator({ status }: Props) {
  const cfg = STATUS_MAP[status];
  return (
    <Tooltip title={cfg.label}>
      <CircleIcon
        sx={{
          fontSize: 12,
          color: cfg.color,
          animation: status === 'connecting' ? 'pulse-blue 1s ease-in-out infinite' : 'none',
        }}
      />
    </Tooltip>
  );
}
