// 监控面板

let statsInterval = null;
let ws = null;
let reconnectAttempts = 0;
const MAX_RECONNECT = 5;

// DOM 元素
const statusIndicator = document.getElementById('statusIndicator');
const statusDot = statusIndicator.querySelector('.status-dot');
const statusText = statusIndicator.querySelector('.status-text');
const totalNotes = document.getElementById('totalNotes');
const totalImages = document.getElementById('totalImages');
const keywordsStats = document.getElementById('keywordsStats');

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    loadStats();
    startPolling();
    connectWebSocket();
});

// 加载统计数据
async function loadStats() {
    try {
        const data = await API.getStats();
        updateStats(data);
    } catch (error) {
        console.error('加载统计失败:', error);
    }
}

// 更新统计显示
function updateStats(data) {
    // 更新笔记总数
    if (data.total_notes !== undefined) {
        totalNotes.textContent = formatNumber(data.total_notes);
    }

    // 更新图片总数
    if (data.total_images !== undefined) {
        totalImages.textContent = formatNumber(data.total_images);
    }

    // 更新关键词统计
    if (data.keyword_stats) {
        keywordsStats.innerHTML = '';
        Object.entries(data.keyword_stats).forEach(([keyword, count]) => {
            const tag = document.createElement('span');
            tag.className = 'keyword-tag';
            tag.innerHTML = `${keyword}: <span>${formatNumber(count)}</span>`;
            keywordsStats.appendChild(tag);
        });
    }
}

// 开始轮询
function startPolling() {
    // 每 5 秒刷新一次统计
    statsInterval = setInterval(loadStats, 5000);
}

// 停止轮询
function stopPolling() {
    if (statsInterval) {
        clearInterval(statsInterval);
        statsInterval = null;
    }
}

// 连接 WebSocket
function connectWebSocket() {
    // 检查浏览器支持
    if (!window.WebSocket) {
        console.warn('浏览器不支持 WebSocket');
        return;
    }

    const wsUrl = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/api/ws/status`;

    try {
        ws = new WebSocket(wsUrl);

        ws.onopen = () => {
            console.log('WebSocket 连接成功');
            reconnectAttempts = 0;
            updateCrawlerStatus({ status: 'connected' });
        };

        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                handleWebSocketMessage(data);
            } catch (error) {
                console.error('解析 WebSocket 消息失败:', error);
            }
        };

        ws.onclose = (event) => {
            console.log('WebSocket 连接关闭:', event.code, event.reason);
            updateCrawlerStatus({ status: 'disconnected' });

            // 自动重连
            if (reconnectAttempts < MAX_RECONNECT) {
                reconnectAttempts++;
                const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), 30000);
                console.log(`${delay / 1000}秒后尝试重连...`);
                setTimeout(connectWebSocket, delay);
            }
        };

        ws.onerror = (error) => {
            console.error('WebSocket 错误:', error);
            updateCrawlerStatus({ status: 'error' });
        };
    } catch (error) {
        console.error('创建 WebSocket 失败:', error);
    }
}

// 处理 WebSocket 消息
function handleWebSocketMessage(data) {
    switch (data.type) {
        case 'crawler_status':
            updateCrawlerStatus(data);
            break;
        case 'stats_update':
            updateStats(data);
            // 同时刷新笔记列表
            if (window.app && window.app.loadNotes) {
                window.app.loadNotes();
            }
            break;
        case 'new_note':
            // 有新笔记，刷新列表
            if (window.app && window.app.loadNotes) {
                window.app.loadNotes();
            }
            loadStats();
            break;
        default:
            console.log('未知消息类型:', data.type);
    }
}

// 更新爬虫状态显示
function updateCrawlerStatus(data) {
    // 移除所有状态类
    statusIndicator.classList.remove('running', 'stopped');

    switch (data.status) {
        case 'running':
            statusIndicator.classList.add('running');
            statusText.textContent = `爬虫运行中 (${data.platform || ''})`;
            break;
        case 'stopped':
            statusIndicator.classList.add('stopped');
            statusText.textContent = '爬虫已停止';
            break;
        case 'connected':
            statusText.textContent = '监控已连接';
            break;
        case 'disconnected':
            statusText.textContent = '监控断开';
            break;
        case 'error':
            statusText.textContent = '监控错误';
            break;
        default:
            statusText.textContent = data.status || '未知状态';
    }
}

// 格式化数字
function formatNumber(num) {
    if (!num) return '0';
    const n = parseInt(num);
    if (isNaN(n)) return num;
    if (n >= 10000) {
        return (n / 10000).toFixed(1) + 'w';
    }
    if (n >= 1000) {
        return (n / 1000).toFixed(1) + 'k';
    }
    return n.toString();
}

// 手动刷新
async function manualRefresh() {
    await loadStats();
    if (window.app && window.app.loadNotes) {
        await window.app.loadNotes();
    }
}

// 页面卸载时清理
window.addEventListener('beforeunload', () => {
    stopPolling();
    if (ws) {
        ws.close();
    }
});

// 导出函数
window.monitor = {
    loadStats,
    manualRefresh,
    connectWebSocket
};
