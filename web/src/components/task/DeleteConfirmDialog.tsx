import React, { useState } from 'react';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogActions from '@mui/material/DialogActions';
import Button from '@mui/material/Button';
import Typography from '@mui/material/Typography';

interface Props {
  open: boolean;
  taskId: string;
  onConfirm: () => void;
  onCancel: () => void;
}

export default function DeleteConfirmDialog({ open, taskId, onConfirm, onCancel }: Props) {
  return (
    <Dialog open={open} onClose={onCancel} maxWidth="xs" fullWidth>
      <DialogTitle>确认删除</DialogTitle>
      <DialogContent>
        <Typography>
          确定要删除任务 <code className="font-mono bg-gray-100 px-1 rounded">{taskId}</code> 吗？此操作不可恢复。
        </Typography>
      </DialogContent>
      <DialogActions>
        <Button onClick={onCancel}>取消</Button>
        <Button onClick={onConfirm} color="error" variant="contained">删除</Button>
      </DialogActions>
    </Dialog>
  );
}
