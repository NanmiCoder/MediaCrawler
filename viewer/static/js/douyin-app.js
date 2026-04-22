// Douyin App - Main application logic

let allDyVideos = [];
let currentDySource = '';
let currentDySearch = '';

// DOM elements
let dyGrid, dyEmptyState, dyLoadingState;
let dySourceFilter, dySearchInput, dyRefreshBtn, dyLastUpdate;
let dyTotalVideos, dyTotalPlay, dyTotalLikes, dyTotalComments;
let dySourceStats;

// Initialize
function initDouyin() {
    // Get DOM elements
    dyGrid = document.getElementById('dyGrid');
    dyEmptyState = document.getElementById('dyEmptyState');
    dyLoadingState = document.getElementById('dyLoadingState');
    dySourceFilter = document.getElementById('dySourceFilter');
    dySearchInput = document.getElementById('dySearchInput');
    dyRefreshBtn = document.getElementById('dyRefreshBtn');
    dyLastUpdate = document.getElementById('dyLastUpdate');
    dyTotalVideos = document.getElementById('dyTotalVideos');
    dyTotalPlay = document.getElementById('dyTotalPlay');
    dyTotalLikes = document.getElementById('dyTotalLikes');
    dyTotalComments = document.getElementById('dyTotalComments');
    dySourceStats = document.getElementById('dySourceStats');

    // Setup event listeners
    setupDyEventListeners();
}

async function loadDouyinData() {
    showDyLoading(true);

    try {
        // Load stats
        const stats = await DyAPI.getStats();
        renderDyStats(stats);

        // Load sources
        const sourcesData = await DyAPI.getSources();
        renderDySourceFilter(sourcesData.sources);

        // Load videos
        const params = {};
        if (currentDySource) params.source = currentDySource;
        if (currentDySearch) params.search = currentDySearch;

        const data = await DyAPI.getVideos(params);
        allDyVideos = data.videos;

        renderDyVideos(allDyVideos);
        updateDyLastUpdate();
    } catch (error) {
        console.error('Failed to load Douyin data:', error);
        showDyError('Failed to load data');
    } finally {
        showDyLoading(false);
    }
}

function renderDyStats(stats) {
    if (dyTotalVideos) dyTotalVideos.textContent = formatDyNumber(stats.total_videos);
    if (dyTotalPlay) dyTotalPlay.textContent = formatDyNumber(stats.total_play);
    if (dyTotalLikes) dyTotalLikes.textContent = formatDyNumber(stats.total_likes);
    if (dyTotalComments) dyTotalComments.textContent = formatDyNumber(stats.total_comments);

    // Render source stats
    if (dySourceStats && stats.source_stats) {
        dySourceStats.innerHTML = '';
        Object.entries(stats.source_stats).forEach(([source, count]) => {
            const tag = document.createElement('span');
            tag.className = 'keyword-tag';
            tag.innerHTML = `${source}: <span>${count}</span>`;
            dySourceStats.appendChild(tag);
        });
    }
}

function renderDySourceFilter(sources) {
    if (!dySourceFilter) return;

    dySourceFilter.innerHTML = '<option value="">全部关键词</option>';
    sources.forEach(source => {
        const option = document.createElement('option');
        option.value = source;
        option.textContent = source;
        dySourceFilter.appendChild(option);
    });

    // Restore current selection
    if (currentDySource) {
        dySourceFilter.value = currentDySource;
    }
}

function renderDyVideos(videos) {
    if (!dyGrid) return;

    dyGrid.innerHTML = '';

    if (videos.length === 0) {
        if (dyEmptyState) dyEmptyState.style.display = 'flex';
        return;
    }

    if (dyEmptyState) dyEmptyState.style.display = 'none';

    videos.forEach(video => {
        const card = createDyVideoCard(video);
        dyGrid.appendChild(card);
    });
}

function createDyVideoCard(video) {
    const card = document.createElement('div');
    card.className = 'dy-card';
    card.dataset.awemeId = video.aweme_id;

    // Cover image
    const coverDiv = document.createElement('div');
    coverDiv.className = 'dy-card-cover';

    if (video.video_cover_url) {
        const img = document.createElement('img');
        img.src = video.video_cover_url;
        img.alt = video.title;
        img.loading = 'lazy';
        img.onerror = () => {
            img.style.display = 'none';
            const placeholder = document.createElement('div');
            placeholder.className = 'dy-card-placeholder';
            placeholder.textContent = '🎬';
            coverDiv.appendChild(placeholder);
        };
        coverDiv.appendChild(img);
    } else {
        const placeholder = document.createElement('div');
        placeholder.className = 'dy-card-placeholder';
        placeholder.textContent = '🎬';
        coverDiv.appendChild(placeholder);
    }

    // Duration badge
    if (video.video_duration) {
        const durationBadge = document.createElement('span');
        durationBadge.className = 'dy-duration';
        durationBadge.textContent = formatDyDuration(video.video_duration);
        coverDiv.appendChild(durationBadge);
    }

    // Video type badge
    const typeBadge = document.createElement('span');
    typeBadge.className = 'dy-type-badge';
    typeBadge.textContent = video.aweme_type === 0 ? '视频' : '图文';
    coverDiv.appendChild(typeBadge);

    card.appendChild(coverDiv);

    // Content
    const content = document.createElement('div');
    content.className = 'dy-card-content';

    // Title
    const title = document.createElement('h3');
    title.className = 'dy-card-title';
    title.textContent = video.title || video.desc || '无标题';
    content.appendChild(title);

    // Meta info
    const meta = document.createElement('div');
    meta.className = 'dy-card-meta';

    // Author
    const author = document.createElement('div');
    author.className = 'dy-card-author';
    if (video.avatar) {
        const avatar = document.createElement('img');
        avatar.src = video.avatar;
        avatar.onerror = () => avatar.style.display = 'none';
        author.appendChild(avatar);
    }
    const authorName = document.createElement('span');
    authorName.textContent = video.nickname || '匿名用户';
    author.appendChild(authorName);
    meta.appendChild(author);

    content.appendChild(meta);

    // Stats
    const stats = document.createElement('div');
    stats.className = 'dy-card-stats';

    const playStat = document.createElement('span');
    playStat.innerHTML = `<svg viewBox="0 0 24 24" width="14" height="14"><path fill="currentColor" d="M8 5v14l11-7z"/></svg> ${formatDyNumber(video.play_count)}`;
    stats.appendChild(playStat);

    const likeStat = document.createElement('span');
    likeStat.innerHTML = `<svg viewBox="0 0 24 24" width="14" height="14"><path fill="currentColor" d="M1 21h4V9H1v12zm22-11c0-1.1-.9-2-2-2h-6.31l.95-4.57.03-.32c0-.41-.17-.79-.44-1.06L14.17 1 7.59 7.59C7.22 7.95 7 8.45 7 9v10c0 1.1.9 2 2 2h9c.83 0 1.54-.5 1.84-1.22l3.02-7.05c.09-.23.14-.47.14-.73v-2z"/></svg> ${formatDyNumber(video.liked_count)}`;
    stats.appendChild(likeStat);

    const commentStat = document.createElement('span');
    commentStat.innerHTML = `<svg viewBox="0 0 24 24" width="14" height="14"><path fill="currentColor" d="M21.99 4c0-1.1-.89-2-1.99-2H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h14l4 4-.01-18z"/></svg> ${formatDyNumber(video.comment_count)}`;
    stats.appendChild(commentStat);

    content.appendChild(stats);
    card.appendChild(content);

    // Click to open modal
    card.addEventListener('click', () => openDyModal(video));

    return card;
}

function setupDyEventListeners() {
    // Source filter
    if (dySourceFilter) {
        dySourceFilter.addEventListener('change', (e) => {
            currentDySource = e.target.value;
            loadDouyinData();
        });
    }

    // Search (debounce)
    if (dySearchInput) {
        let searchTimeout;
        dySearchInput.addEventListener('input', (e) => {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                currentDySearch = e.target.value.trim();
                loadDouyinData();
            }, 300);
        });
    }

    // Refresh button
    if (dyRefreshBtn) {
        dyRefreshBtn.addEventListener('click', async () => {
            dyRefreshBtn.classList.add('loading');
            await loadDouyinData();
            dyRefreshBtn.classList.remove('loading');
        });
    }
}

function showDyLoading(show) {
    if (dyLoadingState) dyLoadingState.style.display = show ? 'flex' : 'none';
    if (show && dyEmptyState) dyEmptyState.style.display = 'none';
}

function showDyError(message) {
    if (dyEmptyState) {
        dyEmptyState.style.display = 'flex';
        const emptyText = dyEmptyState.querySelector('.empty-text');
        const emptyHint = dyEmptyState.querySelector('.empty-hint');
        if (emptyText) emptyText.textContent = message;
        if (emptyHint) emptyHint.textContent = '请检查网络连接或刷新页面';
    }
}

function updateDyLastUpdate() {
    if (dyLastUpdate) {
        const now = new Date();
        const timeStr = now.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
        dyLastUpdate.textContent = `更新于 ${timeStr}`;
    }
}

function formatDyNumber(num) {
    if (!num) return '0';
    const n = parseInt(num);
    if (isNaN(n)) return '0';
    if (n >= 100000000) {
        return (n / 100000000).toFixed(1) + '亿';
    }
    if (n >= 10000) {
        return (n / 10000).toFixed(1) + 'w';
    }
    return n.toString();
}

function formatDyDuration(seconds) {
    if (!seconds) return '';
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
}

// Export for global access
window.dyApp = {
    init: initDouyin,
    loadVideos: loadDouyinData,
    loadStats: loadDouyinData
};

// Subscribe to WebSocket updates for Douyin (dy)
// Use a small delay to ensure WSClient is fully initialized
function subscribeToDouyinUpdates() {
    if (window.WSClient && typeof window.WSClient.subscribe === 'function') {
        window.WSClient.subscribe('dy', (data) => {
            console.log('[DY] Received update notification:', data.type);

            // 显示实时数据通知弹窗
            if (window.DataNotification) {
                if (data.type === 'data_update') {
                    window.DataNotification.handleDataUpdate(data);
                } else if (data.type === 'stats_update') {
                    // 统计更新仅用于数据展示，不触发通知
                    console.log('[DY] Stats updated');
                }
            }

            // Only reload if Douyin panel is visible
            const dyPanel = document.getElementById('douyin-panel');
            if (dyPanel && dyPanel.style.display !== 'none') {
                loadDouyinData();
            }
        });
        console.log('[DY] Subscribed to WebSocket updates');
    } else {
        // Retry after a short delay if WSClient not ready
        setTimeout(subscribeToDouyinUpdates, 100);
    }
}
subscribeToDouyinUpdates();
