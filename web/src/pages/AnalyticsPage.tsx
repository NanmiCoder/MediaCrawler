import React, { useEffect, useMemo } from 'react';
import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Grid from '@mui/material/Grid';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend } from 'recharts';
import { useTaskStore } from '../store/useTaskStore';
import { useNavigate } from 'react-router-dom';
import { TASK_TYPE_LABELS } from '../utils/constants';

const PIE_COLORS = ['#2e7d32', '#d32f2f', '#1976d2', '#9e9e9e'];

export default function AnalyticsPage() {
  const navigate = useNavigate();
  const { tasks, stats, fetchTasks } = useTaskStore();

  useEffect(() => {
    fetchTasks({ limit: 200 });
  }, [fetchTasks]);

  const typeData = useMemo(() => {
    const counts: Record<string, number> = {};
    tasks.forEach((t) => {
      const label = TASK_TYPE_LABELS[t.task_type] || t.task_type;
      counts[label] = (counts[label] || 0) + 1;
    });
    return Object.entries(counts).map(([name, count]) => ({ name, count }));
  }, [tasks]);

  const statusData = useMemo(() => {
    if (!stats) return [];
    return [
      { name: '已完成', value: stats.completed, status: 'completed' },
      { name: '失败', value: stats.failed, status: 'failed' },
      { name: '执行中', value: stats.running, status: 'running' },
      { name: '待执行', value: stats.pending, status: 'pending' },
    ].filter((d) => d.value > 0);
  }, [stats]);

  return (
    <Box>
      <Typography variant="h4" gutterBottom>数据可视化</Typography>

      {/* 概览卡片 */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={6} md={3}>
          <Card><CardContent>
            <Typography variant="body2" color="text.secondary">总任务数</Typography>
            <Typography variant="h4" fontWeight={700}>{stats?.total || 0}</Typography>
          </CardContent></Card>
        </Grid>
        <Grid item xs={6} md={3}>
          <Card><CardContent>
            <Typography variant="body2" color="text.secondary">已完成</Typography>
            <Typography variant="h4" fontWeight={700} color="success.main">{stats?.completed || 0}</Typography>
          </CardContent></Card>
        </Grid>
        <Grid item xs={6} md={3}>
          <Card><CardContent>
            <Typography variant="body2" color="text.secondary">执行中</Typography>
            <Typography variant="h4" fontWeight={700} color="primary.main">{stats?.running || 0}</Typography>
          </CardContent></Card>
        </Grid>
        <Grid item xs={6} md={3}>
          <Card><CardContent>
            <Typography variant="body2" color="text.secondary">成功率</Typography>
            <Typography variant="h4" fontWeight={700}>
              {stats && stats.total > 0
                ? `${((stats.completed / stats.total) * 100).toFixed(1)}%`
                : '-'}
            </Typography>
          </CardContent></Card>
        </Grid>
      </Grid>

      <Grid container spacing={3}>
        {/* 任务类型柱状图 */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>任务类型分布</Typography>
              {typeData.length === 0 ? (
                <Typography color="text.secondary" align="center" sx={{ py: 4 }}>暂无数据</Typography>
              ) : (
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={typeData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="name" />
                    <YAxis allowDecimals={false} />
                    <Tooltip />
                    <Bar dataKey="count" fill="#1976d2" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* 状态饼图 */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>任务状态分布</Typography>
              {statusData.length === 0 ? (
                <Typography color="text.secondary" align="center" sx={{ py: 4 }}>暂无数据</Typography>
              ) : (
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                    <Pie
                      data={statusData}
                      dataKey="value"
                      nameKey="name"
                      cx="50%"
                      cy="50%"
                      outerRadius={100}
                      label
                    >
                      {statusData.map((_, idx) => (
                        <Cell key={idx} fill={PIE_COLORS[idx % PIE_COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}
