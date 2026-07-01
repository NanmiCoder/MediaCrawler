import React from 'react';
import Alert from '@mui/material/Alert';
import IconButton from '@mui/material/IconButton';
import CloseIcon from '@mui/icons-material/Close';

interface Props {
  message: string;
  onClose?: () => void;
}

export default function ErrorAlert({ message, onClose }: Props) {
  return (
    <Alert
      severity="error"
      className="mb-4"
      action={
        onClose ? (
          <IconButton size="small" onClick={onClose}>
            <CloseIcon fontSize="small" />
          </IconButton>
        ) : undefined
      }
    >
      {message}
    </Alert>
  );
}
