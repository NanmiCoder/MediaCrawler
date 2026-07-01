import React from 'react';
import SearchIcon from '@mui/icons-material/Search';
import CommentIcon from '@mui/icons-material/Comment';
import TranscribeIcon from '@mui/icons-material/Transcribe';
import MergeIcon from '@mui/icons-material/Merge';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import { TASK_TYPE_LABELS } from '../../utils/constants';

const ICON_MAP: Record<string, React.ReactElement> = {
  search: <SearchIcon fontSize="small" />,
  comments: <CommentIcon fontSize="small" />,
  scripts: <TranscribeIcon fontSize="small" />,
  merge: <MergeIcon fontSize="small" />,
  run_all: <PlayArrowIcon fontSize="small" />,
};

interface Props {
  type: string;
  showLabel?: boolean;
}

export default function TaskTypeIcon({ type, showLabel = true }: Props) {
  return (
    <span className="flex items-center gap-1">
      {ICON_MAP[type] || <SearchIcon fontSize="small" />}
      {showLabel && <span>{TASK_TYPE_LABELS[type] || type}</span>}
    </span>
  );
}
