import React, { useEffect, useState } from 'react';
import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';
import Grid from '@mui/material/Grid';
import { useTaskStore } from '../store/useTaskStore';
import { api } from '../api/client';
import StatsCards from '../components/dashboard/StatsCards';
import HealthPanel from '../components/dashboard/HealthPanel';
import RecentTasks from '../components/dashboard/RecentTasks';
import LoadingOverlay from '../components/shared/LoadingOverlay';
import ErrorAlert from '../components/shared/ErrorAlert';
import type { HealthResponse } from '../api/types';
import { useNavigate } from 'react-router-dom';

export default function DashboardPage() {
  const navigate = useNavigate();
  const { tasks, stats, loading, error, fetchTasks, clearError } = useTaskStore();
  const [health, setHealth] = useState<HealthResponse | null>(null);

  useEffect(() => {
    fetchTasks({ limit: 5 });
    api.getHealth().then(setHealth).catch(() => {});
  }, [fetchTasks]);

  const handleCardClick = (status: string) => {
    navigate(`/tasks?status=${status}`);
  };

  if (loading && tasks.length === 0) return <LoadingOverlay />;

  return (
    <Box>
      <Typography variant="h4" gutterBottom>仪表盘</Typography>
      {error && <ErrorAlert message={error} onClose={clearError} />}
      <StatsCards
        stats={stats || { pending: 0, running: 0, completed: 0, failed: 0 }}
        onCardClick={handleCardClick}
      />
      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          {health && <HealthPanel health={health} />}
        </Grid>
        <Grid item xs={12} md={6}>
          <RecentTasks tasks={tasks} />
        </Grid>
      </Grid>
    </Box>
  );
}
