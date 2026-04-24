// 知乎应用逻辑

let allZhihuAnswers = [];
let currentZhihuCreator = '';
let currentZhihuSearch = '';

// 知乎 DOM 元素
let zhihuGrid = null;
let zhihuEmptyState = null;
let zhihuLoadingState = null;
let zhihuCreatorFilter = null;
let zhihuSearchInput = null;
let zhihuRefreshBtn = null;
let zhihuLastUpdate = null;
let zhihuTotalAnswers = null;
let zhihuTotalVoteup = null;
let zhihuCreatorsStats = null;

// 初始化知乎模块
function initZhihuApp() {
    // 获取 DOM 元素
    zhihuGrid = document.getElementById('zhihuGrid');
    zhihuEmptyState = document.getElementById('zhihuEmptyState');
    zhihuLoadingState = document.getElementById('zhihuLoadingState');
    zhihuCreatorFilter = document.getElementById('zhihuCreatorFilter');
    zhihuSearchInput = document.getElementById('zhihuSearchInput');
    zhihuRefreshBtn = document.getElementById('zhihuRefreshBtn');
    zhihuLastUpdate = document.getElementById('zhihuLastUpdate');
    zhihuTotalAnswers = document.getElementById('zhihuTotalAnswers');
    zhihuTotalVoteup = document.getElementById('zhihuTotalVoteup');
    zhihuCreatorsStats = document.getElementById('zhihuCreatorsStats');

    // 设置事件监听
    setupZhihuEventListeners();
}

// 加载创作者列表
async function loadZhihuCreators() {
    if (!zhihuCreatorFilter) return;

    try {
        const data = await ZhihuAPI.getCreators();
        zhihuCreatorFilter.innerHTML = '<option value="">全部创作者</option>';
        data.creators.forEach(creator => {
            const option = document.createElement('option');
            option.value = creator;
            const info = data.creator_info[creator] || {};
            option.textContent = info.nickname || creator;
            zhihuCreatorFilter.appendChild(option);
        });
    } catch (error) {
        console.error('加载创作者列表失败:', error);
    }
}

// 加载知乎回答数据
async function loadZhihuAnswers() {
    if (!zhihuGrid) return;

    showZhihuLoading(true);

    try {
        const params = {};
        if (currentZhihuCreator) params.creator = currentZhihuCreator;
        if (currentZhihuSearch) params.search = currentZhihuSearch;

        const data = await ZhihuAPI.getAnswers(params);
        allZhihuAnswers = data.answers;

        renderZhihuAnswers(allZhihuAnswers);
        updateZhihuLastUpdate();
    } catch (error) {
        console.error('加载知乎回答失败:', error);
        showZhihuError('加载知乎数据失败');
    } finally {
        showZhihuLoading(false);
    }
}

// 加载知乎统计
async function loadZhihuStats() {
    try {
        const data = await ZhihuAPI.getStats();

        if (zhihuTotalAnswers) {
            zhihuTotalAnswers.textContent = formatZhihuNumber(data.total_answers);
        }
        if (zhihuTotalVoteup) {
            zhihuTotalVoteup.textContent = formatZhihuNumber(data.total_voteup);
        }

        // 更新创作者统计
        if (zhihuCreatorsStats && data.creators_stats) {
            zhihuCreatorsStats.innerHTML = '';
            Object.entries(data.creators_stats).forEach(([creator, count]) => {
                const tag = document.createElement('span');
                tag.className = 'keyword-tag';
                tag.innerHTML = `${creator}: <span>${formatZhihuNumber(count)}</span>`;
                zhihuCreatorsStats.appendChild(tag);
            });
        }
    } catch (error) {
        console.error('加载知乎统计失败:', error);
    }
}

// 渲染知乎回答列表
function renderZhihuAnswers(answers) {
    if (!zhihuGrid) return;

    zhihuGrid.innerHTML = '';

    if (answers.length === 0) {
        if (zhihuEmptyState) zhihuEmptyState.style.display = 'flex';
        return;
    }

    if (zhihuEmptyState) zhihuEmptyState.style.display = 'none';

    answers.forEach(answer => {
        const card = createZhihuCard(answer);
        zhihuGrid.appendChild(card);
    });
}

// 创建知乎卡片
function createZhihuCard(answer) {
    const card = document.createElement('div');
    card.className = 'zhihu-card';
    card.dataset.contentId = answer.content_id;

    // 内容区域
    const content = document.createElement('div');
    content.className = 'zhihu-card-content';

    // 回答文本
    const text = document.createElement('div');
    text.className = 'zhihu-card-text';
    text.textContent = answer.desc || answer.content_text || '暂无内容';
    content.appendChild(text);

    // 元信息
    const meta = document.createElement('div');
    meta.className = 'zhihu-card-meta';

    // 作者信息
    const author = document.createElement('div');
    author.className = 'zhihu-card-author';
    if (answer.user_avatar) {
        const avatar = document.createElement('img');
        avatar.src = answer.user_avatar;
        avatar.onerror = () => avatar.style.display = 'none';
        author.appendChild(avatar);
    }
    const authorName = document.createElement('span');
    authorName.textContent = answer.user_nickname || '匿名用户';
    author.appendChild(authorName);
    meta.appendChild(author);

    // 互动数据
    const stats = document.createElement('div');
    stats.className = 'zhihu-card-stats';

    const voteup = document.createElement('span');
    voteup.textContent = `👍 ${formatZhihuNumber(answer.voteup_count)}`;
    stats.appendChild(voteup);

    const comments = document.createElement('span');
    comments.textContent = `💬 ${formatZhihuNumber(answer.comment_count)}`;
    stats.appendChild(comments);

    meta.appendChild(stats);
    content.appendChild(meta);
    card.appendChild(content);

    // 点击事件
    card.addEventListener('click', () => openZhihuModal(answer));

    return card;
}

// 设置事件监听
function setupZhihuEventListeners() {
    // 创作者筛选
    if (zhihuCreatorFilter) {
        zhihuCreatorFilter.addEventListener('change', (e) => {
            currentZhihuCreator = e.target.value;
            loadZhihuAnswers();
        });
    }

    // 搜索（防抖）
    if (zhihuSearchInput) {
        let searchTimeout;
        zhihuSearchInput.addEventListener('input', (e) => {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                currentZhihuSearch = e.target.value.trim();
                loadZhihuAnswers();
            }, 300);
        });
    }

    // 刷新按钮
    if (zhihuRefreshBtn) {
        zhihuRefreshBtn.addEventListener('click', async () => {
            zhihuRefreshBtn.classList.add('loading');
            await loadZhihuAnswers();
            await loadZhihuStats();
            zhihuRefreshBtn.classList.remove('loading');
        });
    }
}

// 显示/隐藏加载状态
function showZhihuLoading(show) {
    if (zhihuLoadingState) {
        zhihuLoadingState.style.display = show ? 'flex' : 'none';
    }
    if (show && zhihuEmptyState) {
        zhihuEmptyState.style.display = 'none';
    }
}

// 显示错误
function showZhihuError(message) {
    if (zhihuEmptyState) {
        zhihuEmptyState.style.display = 'flex';
        const emptyText = zhihuEmptyState.querySelector('.empty-text');
        const emptyHint = zhihuEmptyState.querySelector('.empty-hint');
        if (emptyText) emptyText.textContent = message;
        if (emptyHint) emptyHint.textContent = '请检查网络连接或刷新页面';
    }
}

// 更新最后更新时间
function updateZhihuLastUpdate() {
    if (zhihuLastUpdate) {
        const now = new Date();
        const timeStr = now.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
        zhihuLastUpdate.textContent = `更新于 ${timeStr}`;
    }
}

// 格式化数字
function formatZhihuNumber(num) {
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

// 导出函数供其他模块使用
window.zhihuApp = {
    init: initZhihuApp,
    loadAnswers: loadZhihuAnswers,
    loadStats: loadZhihuStats,
    loadCreators: loadZhihuCreators,
    updateLastUpdate: updateZhihuLastUpdate
};

// Subscribe to WebSocket updates for Zhihu (zhihu)
// Use a small delay to ensure WSClient is fully initialized
function subscribeToZhihuUpdates() {
    if (window.WSClient && typeof window.WSClient.subscribe === 'function') {
        window.WSClient.subscribe('zhihu', (data) => {
            console.log('[ZHIHU] Received update notification:', data.type);

            // 显示实时数据通知弹窗
            if (window.DataNotification) {
                if (data.type === 'data_update') {
                    window.DataNotification.handleDataUpdate(data);
                } else if (data.type === 'stats_update') {
                    // 统计更新仅用于数据展示，不触发通知
                    console.log('[ZHIHU] Stats updated');
                }
            }

            // Only reload if Zhihu panel is visible
            const zhihuPanel = document.getElementById('zhihu-panel');
            if (zhihuPanel && zhihuPanel.style.display !== 'none') {
                loadZhihuAnswers();
                loadZhihuStats();
            }
        });
        console.log('[ZHIHU] Subscribed to WebSocket updates');
    } else {
        // Retry after a short delay if WSClient not ready
        setTimeout(subscribeToZhihuUpdates, 100);
    }
}
subscribeToZhihuUpdates();
