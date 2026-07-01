import React from 'react';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';
import { STATUS_CONFIG, type TaskStatus } from '../../utils/constants';

interface Props {
  stats: {
    pending: number;
    running: number;
    completed: number;
    failed: number;
  };
  onCardClick?: (status: string) => void;
}

const CARDS: { key: TaskStatus; icon: string }[] = [
  { key: 'pending', icon: '⏳' },
  { key: 'running', icon: '⚡' },
  { key: 'completed', icon: '✅' },
  { key: 'failed', icon: '❌' },
];

export default function StatsCards({ stats, onCardClick }: Props) {
  return (
    <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 2, mb: 3 }}>
      {CARDS.map(({ key, icon }) => {
        const cfg = STATUS_CONFIG[key];
        return (
          <Card
            key={key}
            sx={{ cursor: onCardClick ? 'pointer' : 'default', '&:hover': { boxShadow: 4 } }}
            onClick={() => onCardClick?.(key)}
          >
            <CardContent>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Typography variant="body2" color="text.secondary">{cfg.label}</Typography>
                <span style={{ fontSize: 24 }}>{icon}</span>
              </Box>
              <Typography variant="h4" fontWeight={700} sx={{ mt: 1, color: cfg.color }}>
                {stats[key]}
              </Typography>
            </CardContent>
          </Card>
        );
      })}
    </Box>
  );
}
