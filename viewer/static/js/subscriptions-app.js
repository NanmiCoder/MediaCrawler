// 订阅管理应用逻辑

let allSubscriptions = [];
let platformOptions = [];

// DOM 元素 - 在DOMContentLoaded后初始化
let subscriptionList, subEmptyState, subLoadingState, subTotalCount, subActiveCount;
let subLastUpdate, addSubscriptionBtn, refreshSubscriptionsBtn;

// 模态框元素
let subscriptionModal, subModalClose, subModalTitle, subscriptionForm;
let subId, subKeyword, subPlatform, subCron, subEnabled, subCancelBtn, subSaveBtn;

// 确认框元素
let confirmModal, confirmTitle, confirmMessage, confirmCancelBtn, confirmOkBtn;

let pendingDeleteId = null;

// API 函数
const SubAPI = {
    async getSubscriptions() {
        const response = await fetch('/api/subscriptions');
        if (!response.ok) throw new Error('获取订阅列表失败');
        return response.json();
    },

    async getPlatformConfig() {
        const response = await fetch('/api/subscriptions/config/platforms');
        if (!response.ok) throw new Error('获取平台配置失败');
        return response.json();
    },

    async createSubscription(data) {
        const response = await fetch('/api/subscriptions', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || '创建订阅失败');
        }
        return response.json();
    },

    async updateSubscription(id, data) {
        const response = await fetch(`/api/subscriptions/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || '更新订阅失败');
        }
        return response.json();
    },

    async deleteSubscription(id) {
        const response = await fetch(`/api/subscriptions/${id}`, {
            method: 'DELETE'
        });
        if (!response.ok) throw new Error('删除订阅失败');
        return response.json();
    },

    async runSubscription(id) {
        const response = await fetch(`/api/subscriptions/${id}/run`, {
            method: 'POST'
        });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || '执行订阅失败');
        }
        return response.json();
    }
};

// 初始化
document.addEventListener('DOMContentLoaded', async () => {
    // 初始化DOM元素引用
    subscriptionList = document.getElementById('subscriptionList');
    subEmptyState = document.getElementById('subEmptyState');
    subLoadingState = document.getElementById('subLoadingState');
    subTotalCount = document.getElementById('subTotalCount');
    subActiveCount = document.getElementById('subActiveCount');
    subLastUpdate = document.getElementById('subLastUpdate');
    addSubscriptionBtn = document.getElementById('addSubscriptionBtn');
    refreshSubscriptionsBtn = document.getElementById('refreshSubscriptionsBtn');

    subscriptionModal = document.getElementById('subscriptionModal');
    subModalClose = document.getElementById('subModalClose');
    subModalTitle = document.getElementById('subModalTitle');
    subscriptionForm = document.getElementById('subscriptionForm');
    subId = document.getElementById('subId');
    subKeyword = document.getElementById('subKeyword');
    subPlatform = document.getElementById('subPlatform');
    subCron = document.getElementById('subCron');
    subEnabled = document.getElementById('subEnabled');
    subCancelBtn = document.getElementById('subCancelBtn');
    subSaveBtn = document.getElementById('subSaveBtn');

    confirmModal = document.getElementById('confirmModal');
    confirmTitle = document.getElementById('confirmTitle');
    confirmMessage = document.getElementById('confirmMessage');
    confirmCancelBtn = document.getElementById('confirmCancelBtn');
    confirmOkBtn = document.getElementById('confirmOkBtn');

    try {
        await loadPlatformConfig();
        setupEventListeners();
        setupSubscriptionModalEvents();
        setupWebSocketSubscription();
    } catch (error) {
        console.error('初始化订阅管理失败:', error);
        showError('初始化失败，请刷新页面重试');
    }
});

// 设置 WebSocket 订阅更新监听
function setupWebSocketSubscription() {
    // 检查 WebSocket 客户端是否可用
    if (window.WSClient && typeof window.WSClient.subscribeSubscription === 'function') {
        window.WSClient.subscribeSubscription((data) => {
            console.log('[订阅] 收到订阅更新通知:', data);
            handleSubscriptionUpdate(data);
        });
        console.log('[订阅] WebSocket 订阅监听已启动');
    } else {
        console.warn('[订阅] WebSocket 客户端不可用，将无法接收实时更新');
    }
}

// 处理订阅更新通知
function handleSubscriptionUpdate(data) {
    const { subscription_id, keyword, platform, new_count, timestamp } = data;

    // 显示通知
    const platformLabel = getPlatformLabel(platform);
    const message = `订阅 "${keyword}" (${platformLabel}) 爬取完成`;
    showNotification(message, 'success');

    // 刷新订阅列表
    loadSubscriptions();

    // 更新对应行的状态（如果存在）
    const row = document.querySelector(`tr[data-sub-id="${subscription_id}"]`);
    if (row) {
        // 添加高亮效果
        row.classList.add('subscription-updated');
        setTimeout(() => row.classList.remove('subscription-updated'), 2000);
    }
}

// 加载平台配置
async function loadPlatformConfig() {
    try {
        const data = await SubAPI.getPlatformConfig();
        platformOptions = data.platforms || [];
        renderPlatformOptions();
    } catch (error) {
        console.error('加载平台配置失败:', error);
    }
}

// 渲染平台选项
function renderPlatformOptions() {
    subPlatform.innerHTML = '<option value="">选择平台</option>';
    platformOptions.forEach(platform => {
        const option = document.createElement('option');
        option.value = platform.value;
        option.textContent = platform.label;
        subPlatform.appendChild(option);
    });
}

// 加载订阅列表
async function loadSubscriptions() {
    showLoading(true);

    try {
        const data = await SubAPI.getSubscriptions();
        allSubscriptions = data.subscriptions || [];

        renderSubscriptions(allSubscriptions);
        updateStats();
        updateLastUpdate();
    } catch (error) {
        console.error('加载订阅列表失败:', error);
        showError('加载订阅列表失败');
    } finally {
        showLoading(false);
    }
}

// 渲染订阅列表
function renderSubscriptions(subscriptions) {
    subscriptionList.innerHTML = '';

    if (subscriptions.length === 0) {
        subEmptyState.style.display = 'flex';
        return;
    }

    subEmptyState.style.display = 'none';

    subscriptions.forEach(sub => {
        const row = createSubscriptionRow(sub);
        subscriptionList.appendChild(row);
    });
}

// 创建订阅行
function createSubscriptionRow(sub) {
    const row = document.createElement('tr');
    row.className = 'subscription-row';
    row.dataset.subId = sub.id;

    // 关键词
    const keywordCell = document.createElement('td');
    keywordCell.className = 'sub-keyword';
    keywordCell.textContent = sub.keyword;
    row.appendChild(keywordCell);

    // 平台
    const platformCell = document.createElement('td');
    platformCell.className = 'sub-platform';
    const platformBadge = document.createElement('span');
    platformBadge.className = `platform-badge platform-${sub.platform}`;
    platformBadge.textContent = getPlatformLabel(sub.platform);
    platformCell.appendChild(platformBadge);
    row.appendChild(platformCell);

    // 频率
    const cronCell = document.createElement('td');
    cronCell.className = 'sub-cron';
    cronCell.innerHTML = `<span class="cron-expression">${sub.cron || '未设置'}</span>`;
    row.appendChild(cronCell);

    // 状态
    const statusCell = document.createElement('td');
    statusCell.className = 'sub-status';
    const statusBadge = document.createElement('span');
    statusBadge.className = `status-badge ${sub.enabled ? 'status-active' : 'status-inactive'}`;
    statusBadge.textContent = sub.enabled ? '启用' : '禁用';
    statusCell.appendChild(statusBadge);
    row.appendChild(statusCell);

    // 最后执行时间
    const lastRunCell = document.createElement('td');
    lastRunCell.className = 'sub-last-run';
    if (sub.last_run_at) {
        const lastRun = new Date(sub.last_run_at);
        lastRunCell.innerHTML = `
            <span class="last-run-time">${formatDateTime(lastRun)}</span>
            ${sub.last_run_status ? `<span class="last-run-status status-${sub.last_run_status}">${getStatusLabel(sub.last_run_status)}</span>` : ''}
        `;
    } else {
        lastRunCell.innerHTML = '<span class="no-data">从未执行</span>';
    }
    row.appendChild(lastRunCell);

    // 操作
    const actionsCell = document.createElement('td');
    actionsCell.className = 'sub-actions';
    actionsCell.innerHTML = `
        <button class="action-btn btn-trends" title="查看趋势" data-action="trends">
            <svg viewBox="0 0 24 24" width="16" height="16"><path fill="currentColor" d="M3.5 18.49l6-6.01 4 4L22 6.92l-1.41-1.41-7.09 7.97-4-4L2 16.99z"/></svg>
        </button>
        <button class="action-btn btn-run" title="立即爬取" data-action="run">
            <svg viewBox="0 0 24 24" width="16" height="16"><path fill="currentColor" d="M8 5v14l11-7z"/></svg>
        </button>
        <button class="action-btn btn-edit" title="编辑" data-action="edit">
            <svg viewBox="0 0 24 24" width="16" height="16"><path fill="currentColor" d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04c.39-.39.39-1.02 0-1.41l-2.34-2.34c-.39-.39-1.02-.39-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z"/></svg>
        </button>
        <button class="action-btn btn-delete" title="删除" data-action="delete">
            <svg viewBox="0 0 24 24" width="16" height="16"><path fill="currentColor" d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/></svg>
        </button>
    `;

    // 绑定操作事件
    actionsCell.querySelectorAll('.action-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            const action = btn.dataset.action;
            handleAction(action, sub);
        });
    });

    row.appendChild(actionsCell);
    return row;
}

// 处理操作
function handleAction(action, sub) {
    switch (action) {
        case 'trends':
            openTrendsModal(sub);
            break;
        case 'run':
            runSubscription(sub);
            break;
        case 'edit':
            openEditModal(sub);
            break;
        case 'delete':
            openDeleteConfirm(sub);
            break;
    }
}

// 立即执行订阅
async function runSubscription(sub) {
    const row = document.querySelector(`tr[data-sub-id="${sub.id}"]`);
    const runBtn = row?.querySelector('.btn-run');

    try {
        if (runBtn) {
            runBtn.classList.add('loading');
            runBtn.disabled = true;
        }

        const result = await SubAPI.runSubscription(sub.id);
        showNotification(`订阅 "${sub.keyword}" 已开始执行`, 'success');

        // 刷新列表
        setTimeout(() => loadSubscriptions(), 1000);
    } catch (error) {
        console.error('执行订阅失败:', error);
        showNotification(error.message, 'error');
    } finally {
        if (runBtn) {
            runBtn.classList.remove('loading');
            runBtn.disabled = false;
        }
    }
}

// 打开编辑模态框
function openEditModal(sub) {
    subModalTitle.textContent = '编辑订阅';
    subId.value = sub.id;
    subKeyword.value = sub.keyword;
    subPlatform.value = sub.platform;
    subCron.value = sub.cron || '';
    subEnabled.checked = sub.enabled;

    subscriptionModal.style.display = 'flex';
    document.body.style.overflow = 'hidden';
}

// 打开添加模态框
function openAddModal() {
    subModalTitle.textContent = '添加订阅';
    subId.value = '';
    subscriptionForm.reset();
    subEnabled.checked = true;

    subscriptionModal.style.display = 'flex';
    document.body.style.overflow = 'hidden';
}

// 关闭模态框
function closeSubModal() {
    subscriptionModal.style.display = 'none';
    document.body.style.overflow = '';
    subscriptionForm.reset();
}

// 打开删除确认框
function openDeleteConfirm(sub) {
    pendingDeleteId = sub.id;
    confirmTitle.textContent = '确认删除';
    confirmMessage.textContent = `确定要删除订阅 "${sub.keyword}" 吗？此操作不可撤销。`;
    confirmModal.style.display = 'flex';
    document.body.style.overflow = 'hidden';
}

// 关闭确认框
function closeConfirmModal() {
    confirmModal.style.display = 'none';
    document.body.style.overflow = '';
    pendingDeleteId = null;
}

// 执行删除
async function executeDelete() {
    if (!pendingDeleteId) return;

    try {
        await SubAPI.deleteSubscription(pendingDeleteId);
        showNotification('订阅已删除', 'success');
        closeConfirmModal();
        loadSubscriptions();
    } catch (error) {
        console.error('删除订阅失败:', error);
        showNotification(error.message, 'error');
    }
}

// 设置事件监听
function setupEventListeners() {
    // 添加订阅按钮
    addSubscriptionBtn.addEventListener('click', openAddModal);

    // 刷新按钮
    refreshSubscriptionsBtn.addEventListener('click', async () => {
        refreshSubscriptionsBtn.classList.add('loading');
        await loadSubscriptions();
        refreshSubscriptionsBtn.classList.remove('loading');
    });
}

// 设置订阅模态框事件
function setupSubscriptionModalEvents() {
    // 关闭订阅模态框
    subModalClose.addEventListener('click', closeSubModal);
    subCancelBtn.addEventListener('click', closeSubModal);

    // 点击遮罩关闭
    subscriptionModal.querySelector('.modal-overlay').addEventListener('click', closeSubModal);

    // ESC 键关闭
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            if (subscriptionModal.style.display === 'flex') {
                closeSubModal();
            }
            if (confirmModal.style.display === 'flex') {
                closeConfirmModal();
            }
        }
    });

    // 表单提交
    subscriptionForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        await saveSubscription();
    });

    // 确认框事件
    confirmCancelBtn.addEventListener('click', closeConfirmModal);
    confirmOkBtn.addEventListener('click', executeDelete);
    confirmModal.querySelector('.modal-overlay').addEventListener('click', closeConfirmModal);
}

// 保存订阅
async function saveSubscription() {
    const data = {
        keyword: subKeyword.value.trim(),
        platform: subPlatform.value,
        cron: subCron.value.trim() || null,
        enabled: subEnabled.checked
    };

    if (!data.keyword || !data.platform) {
        showNotification('请填写关键词和选择平台', 'error');
        return;
    }

    try {
        subSaveBtn.disabled = true;
        subSaveBtn.textContent = '保存中...';

        const id = subId.value;
        if (id) {
            await SubAPI.updateSubscription(parseInt(id), data);
            showNotification('订阅已更新', 'success');
        } else {
            await SubAPI.createSubscription(data);
            showNotification('订阅已创建', 'success');
        }

        closeSubModal();
        loadSubscriptions();
    } catch (error) {
        console.error('保存订阅失败:', error);
        showNotification(error.message, 'error');
    } finally {
        subSaveBtn.disabled = false;
        subSaveBtn.textContent = '保存';
    }
}

// 更新统计
function updateStats() {
    const total = allSubscriptions.length;
    const active = allSubscriptions.filter(s => s.enabled).length;

    subTotalCount.textContent = total;
    subActiveCount.textContent = active;
}

// 更新最后更新时间
function updateLastUpdate() {
    const now = new Date();
    const timeStr = now.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
    subLastUpdate.textContent = `更新于 ${timeStr}`;
}

// 显示/隐藏加载状态
function showLoading(show) {
    subLoadingState.style.display = show ? 'flex' : 'none';
    if (show) {
        subEmptyState.style.display = 'none';
    }
}

// 显示错误
function showError(message) {
    subEmptyState.style.display = 'flex';
    subEmptyState.querySelector('.empty-text').textContent = message;
    subEmptyState.querySelector('.empty-hint').textContent = '请检查网络连接或刷新页面';
}

// 显示通知
function showNotification(message, type = 'info') {
    // 创建通知元素
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;

    // 添加到页面
    document.body.appendChild(notification);

    // 动画显示
    requestAnimationFrame(() => {
        notification.classList.add('show');
    });

    // 3秒后移除
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// 获取平台标签
function getPlatformLabel(platform) {
    const labels = {
        'xhs': '小红书',
        'zhihu': '知乎',
        'douyin': '抖音',
        'bilibili': 'B站'
    };
    return labels[platform] || platform;
}

// 获取状态标签
function getStatusLabel(status) {
    const labels = {
        'success': '成功',
        'failed': '失败',
        'running': '运行中'
    };
    return labels[status] || status;
}

// 格式化日期时间
function formatDateTime(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const hour = String(date.getHours()).padStart(2, '0');
    const minute = String(date.getMinutes()).padStart(2, '0');
    return `${year}-${month}-${day} ${hour}:${minute}`;
}

// 导出模块
window.subApp = {
    loadSubscriptions
};

// 打开趋势看板
function openTrendsModal(sub) {
    if (window.trendsApp) {
        window.trendsApp.openTrendsModal(sub);
    }
}
