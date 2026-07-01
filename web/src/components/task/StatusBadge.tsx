import React from 'react';
import Chip from '@mui/material/Chip';
import { STATUS_CONFIG, type TaskStatus } from '../../utils/constants';

interface Props {
  status: string;
  size?: 'small' | 'medium';
}

export default function StatusBadge({ status, size = 'medium' }: Props) {
  const cfg = STATUS_CONFIG[status as TaskStatus] || STATUS_CONFIG.pending;
  return (
    <Chip
      label={cfg.label}
      size={size}
      sx={{
        backgroundColor: cfg.bg,
        color: cfg.color,
        fontWeight: 600,
        ...('pulse' in cfg && cfg.pulse ? { animation: 'pulse-blue 2s ease-in-out infinite' } : {}),
      }}
    />
  );
}
