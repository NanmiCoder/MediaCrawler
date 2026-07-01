import React from 'react';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Typography from '@mui/material/Typography';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import { useNavigate } from 'react-router-dom';
import StatusBadge from '../task/StatusBadge';
import TaskTypeIcon from '../task/TaskTypeIcon';
import type { TaskInfo } from '../../api/types';
import { formatDateTime } from '../../utils/format';

interface Props {
  tasks: TaskInfo[];
}

export default function RecentTasks({ tasks }: Props) {
  const navigate = useNavigate();

  return (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>最近任务</Typography>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Task ID</TableCell>
              <TableCell>类型</TableCell>
              <TableCell>状态</TableCell>
              <TableCell>创建时间</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {tasks.length === 0 ? (
              <TableRow>
                <TableCell colSpan={4} align="center">
                  <Typography color="text.secondary">暂无任务</Typography>
                </TableCell>
              </TableRow>
            ) : (
              tasks.slice(0, 5).map((task) => (
                <TableRow
                  key={task.task_id}
                  hover
                  sx={{ cursor: 'pointer' }}
                  onClick={() => navigate(`/tasks/${task.task_id}`)}
                >
                  <TableCell>
                    <code className="font-mono text-xs bg-gray-100 px-1 rounded">
                      {task.task_id.slice(0, 8)}
                    </code>
                  </TableCell>
                  <TableCell><TaskTypeIcon type={task.task_type} /></TableCell>
                  <TableCell><StatusBadge status={task.status} size="small" /></TableCell>
                  <TableCell>{formatDateTime(task.created_at)}</TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
