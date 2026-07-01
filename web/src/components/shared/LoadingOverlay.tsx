import React from 'react';
import CircularProgress from '@mui/material/CircularProgress';
import Box from '@mui/material/Box';

interface Props {
  loading?: boolean;
}

export default function LoadingOverlay({ loading = true }: Props) {
  if (!loading) return null;
  return (
    <Box className="flex items-center justify-center py-12">
      <CircularProgress />
    </Box>
  );
}
