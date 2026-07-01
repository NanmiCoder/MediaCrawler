import React from 'react';
import Box from '@mui/material/Box';
import Drawer from '@mui/material/Drawer';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import ListItemButton from '@mui/material/ListItemButton';
import ListItemIcon from '@mui/material/ListItemIcon';
import ListItemText from '@mui/material/ListItemText';
import Typography from '@mui/material/Typography';
import Badge from '@mui/material/Badge';
import DashboardIcon from '@mui/icons-material/Dashboard';
import AddCircleIcon from '@mui/icons-material/AddCircle';
import ListAltIcon from '@mui/icons-material/ListAlt';
import BarChartIcon from '@mui/icons-material/BarChart';
import SettingsIcon from '@mui/icons-material/Settings';
import StorageIcon from '@mui/icons-material/Storage';
import ConnectionIndicator from '../shared/ConnectionIndicator';
import { useWebSocket } from '../../hooks/useWebSocket';
import { useNavigate, useLocation, Outlet } from 'react-router-dom';
import { useTaskStore } from '../../store/useTaskStore';

const DRAWER_WIDTH = 240;

export default function AppLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const { status: wsStatus } = useWebSocket();
  const { stats } = useTaskStore();

  const runningCount = stats?.running ?? 0;

  const NAV_ITEMS = [
    { path: '/', label: '仪表盘', icon: <DashboardIcon /> },
    { path: '/create', label: '创建任务', icon: <AddCircleIcon /> },
    {
      path: '/tasks',
      label: '任务列表',
      icon: (
        <Badge badgeContent={runningCount} color="primary" max={9} invisible={runningCount === 0}>
          <ListAltIcon />
        </Badge>
      ),
    },
    { path: '/data', label: '数据管理', icon: <StorageIcon /> },
    { path: '/analytics', label: '数据可视化', icon: <BarChartIcon /> },
    { path: '/settings', label: '设置', icon: <SettingsIcon /> },
  ];

  return (
    <Box sx={{ display: 'flex' }}>
      <Drawer
        variant="permanent"
        sx={{
          width: DRAWER_WIDTH,
          flexShrink: 0,
          '& .MuiDrawer-paper': {
            width: DRAWER_WIDTH,
            boxSizing: 'border-box',
          },
        }}
      >
        <Box sx={{ p: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
          <Typography variant="h6" color="primary" fontWeight={700}>
            MediaCrawler
          </Typography>
          <Box sx={{ ml: 'auto' }}>
            <ConnectionIndicator status={wsStatus} />
          </Box>
        </Box>
        <List>
          {NAV_ITEMS.map((item) => {
            const isActive = location.pathname === item.path ||
              (item.path !== '/' && location.pathname.startsWith(item.path));
            return (
              <ListItem key={item.path} disablePadding>
                <ListItemButton
                  selected={isActive}
                  onClick={() => navigate(item.path)}
                  sx={{
                    mx: 1,
                    borderRadius: 2,
                    '&.Mui-selected': {
                      backgroundColor: 'primary.main',
                      color: 'white',
                      '&:hover': { backgroundColor: 'primary.dark' },
                      '& .MuiListItemIcon-root': { color: 'white' },
                    },
                  }}
                >
                  <ListItemIcon sx={{ minWidth: 40 }}>{item.icon}</ListItemIcon>
                  <ListItemText primary={item.label} />
                </ListItemButton>
              </ListItem>
            );
          })}
        </List>
      </Drawer>
      <Box component="main" sx={{ flexGrow: 1, p: 3, minHeight: '100vh', backgroundColor: '#f5f5f5' }}>
        <Outlet />
      </Box>
    </Box>
  );
}
