// Bilibili App - Main application logic

let allBiliVideos = [];
let currentBiliSource = '';
let currentBiliSearch = '';

// DOM elements
let biliGrid, biliEmptyState, biliLoadingState;
let biliSourceFilter, biliSearchInput, biliRefreshBtn, biliLastUpdate;
let biliTotalVideos, biliTotalPlay, biliTotalLikes, biliTotalComments;
let biliSourceStats;

// Initialize
function initBilibili() {
    // Get DOM elements
    biliGrid = document.getElementById('biliGrid');
    biliEmptyState = document.getElementById('biliEmptyState');
    biliLoadingState = document.getElementById('biliLoadingState');
    biliSourceFilter = document.getElementById('biliSourceFilter');
    biliSearchInput = document.getElementById('biliSearchInput');
    biliRefreshBtn = document.getElementById('biliRefreshBtn');
    biliLastUpdate = document.getElementById('biliLastUpdate');
    biliTotalVideos = document.getElementById('biliTotalVideos');
    biliTotalPlay = document.getElementById('biliTotalPlay');
    biliTotalLikes = document.getElementById('biliTotalLikes');
    biliTotalComments = document.getElementById('biliTotalComments');
    biliSourceStats = document.getElementById('biliSourceStats');

    // Setup event listeners
    setupBiliEventListeners();
}

async function loadBilibiliData() {
    showBiliLoading(true);

    try {
        // Load stats
        const stats = await BiliAPI.getStats();
        renderBiliStats(stats);

        // Load sources
        const sourcesData = await BiliAPI.getSources();
        renderBiliSourceFilter(sourcesData.sources);

        // Load videos
        const params = {};
        if (currentBiliSource) params.source = currentBiliSource;
        if (currentBiliSearch) params.search = currentBiliSearch;

        const data = await BiliAPI.getVideos(params);
        allBiliVideos = data.videos;

        renderBiliVideos(allBiliVideos);
        updateBiliLastUpdate();
    } catch (error) {
        console.error('Failed to load Bilibili data:', error);
        showBiliError('Failed to load data');
    } finally {
        showBiliLoading(false);
    }
}

function renderBiliStats(stats) {
    if (biliTotalVideos) biliTotalVideos.textContent = formatBiliNumber(stats.total_videos);
    if (biliTotalPlay) biliTotalPlay.textContent = formatBiliNumber(stats.total_play);
    if (biliTotalLikes) biliTotalLikes.textContent = formatBiliNumber(stats.total_likes);
    if (biliTotalComments) biliTotalComments.textContent = formatBiliNumber(stats.total_comments);

    // Render source stats
    if (biliSourceStats && stats.source_stats) {
        biliSourceStats.innerHTML = '';
        Object.entries(stats.source_stats).forEach(([source, count]) => {
            const tag = document.createElement('span');
            tag.className = 'keyword-tag';
            tag.innerHTML = `${source}: <span>${count}</span>`;
            biliSourceStats.appendChild(tag);
        });
    }
}

function renderBiliSourceFilter(sources) {
    if (!biliSourceFilter) return;

    biliSourceFilter.innerHTML = '<option value="">All Sources</option>';
    sources.forEach(source => {
        const option = document.createElement('option');
        option.value = source;
        option.textContent = source;
        biliSourceFilter.appendChild(option);
    });

    // Restore current selection
    if (currentBiliSource) {
        biliSourceFilter.value = currentBiliSource;
    }
}

function renderBiliVideos(videos) {
    if (!biliGrid) return;

    biliGrid.innerHTML = '';

    if (videos.length === 0) {
        if (biliEmptyState) biliEmptyState.style.display = 'flex';
        return;
    }

    if (biliEmptyState) biliEmptyState.style.display = 'none';

    videos.forEach(video => {
        const card = createBiliVideoCard(video);
        biliGrid.appendChild(card);
    });
}

function createBiliVideoCard(video) {
    const card = document.createElement('div');
    card.className = 'bili-card';
    card.dataset.videoId = video.video_id;

    // Cover image
    const coverDiv = document.createElement('div');
    coverDiv.className = 'bili-card-cover';

    if (video.video_cover_url) {
        const img = document.createElement('img');
        img.src = video.video_cover_url;
        img.alt = video.title;
        img.loading = 'lazy';
        img.onerror = () => {
            img.style.display = 'none';
            const placeholder = document.createElement('div');
            placeholder.className = 'bili-card-placeholder';
            placeholder.textContent = 'Video';
            coverDiv.appendChild(placeholder);
        };
        coverDiv.appendChild(img);
    } else {
        const placeholder = document.createElement('div');
        placeholder.className = 'bili-card-placeholder';
        placeholder.textContent = 'Video';
        coverDiv.appendChild(placeholder);
    }

    // Duration badge (simulated)
    const durationBadge = document.createElement('span');
    durationBadge.className = 'bili-duration';
    durationBadge.textContent = formatBiliDuration(video.video_play_count);
    coverDiv.appendChild(durationBadge);

    card.appendChild(coverDiv);

    // Content
    const content = document.createElement('div');
    content.className = 'bili-card-content';

    // Title
    const title = document.createElement('h3');
    title.className = 'bili-card-title';
    title.textContent = video.title || 'No Title';
    content.appendChild(title);

    // Meta info
    const meta = document.createElement('div');
    meta.className = 'bili-card-meta';

    // Author
    const author = document.createElement('div');
    author.className = 'bili-card-author';
    if (video.avatar) {
        const avatar = document.createElement('img');
        avatar.src = video.avatar;
        avatar.onerror = () => avatar.style.display = 'none';
        author.appendChild(avatar);
    }
    const authorName = document.createElement('span');
    authorName.textContent = video.nickname || 'Anonymous';
    author.appendChild(authorName);
    meta.appendChild(author);

    content.appendChild(meta);

    // Stats
    const stats = document.createElement('div');
    stats.className = 'bili-card-stats';

    const playStat = document.createElement('span');
    playStat.innerHTML = `<svg viewBox="0 0 24 24" width="14" height="14"><path fill="currentColor" d="M8 5v14l11-7z"/></svg> ${formatBiliNumber(video.video_play_count)}`;
    stats.appendChild(playStat);

    const likeStat = document.createElement('span');
    likeStat.innerHTML = `<svg viewBox="0 0 24 24" width="14" height="14"><path fill="currentColor" d="M1 21h4V9H1v12zm22-11c0-1.1-.9-2-2-2h-6.31l.95-4.57.03-.32c0-.41-.17-.79-.44-1.06L14.17 1 7.59 7.59C7.22 7.95 7 8.45 7 9v10c0 1.1.9 2 2 2h9c.83 0 1.54-.5 1.84-1.22l3.02-7.05c.09-.23.14-.47.14-.73v-2z"/></svg> ${formatBiliNumber(video.liked_count)}`;
    stats.appendChild(likeStat);

    const coinStat = document.createElement('span');
    coinStat.innerHTML = `<svg viewBox="0 0 24 24" width="14" height="14"><path fill="currentColor" d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm.31-8.86c-1.77-.45-2.34-.94-2.34-1.67 0-.84.79-1.43 2.1-1.43 1.38 0 1.9.66 1.94 1.64h1.71c-.05-1.34-.87-2.57-2.49-2.97V5H10.9v1.69c-1.51.32-2.72 1.3-2.72 2.81 0 1.79 1.49 2.69 3.66 3.21 1.95.46 2.34 1.15 2.34 1.87 0 .53-.39 1.39-2.1 1.39-1.6 0-2.23-.72-2.32-1.64H8.04c.1 1.7 1.36 2.66 2.86 2.97V19h2.34v-1.67c1.52-.29 2.72-1.16 2.73-2.77-.01-2.2-1.9-2.96-3.66-3.42z"/></svg> ${formatBiliNumber(video.video_coin_count)}`;
    stats.appendChild(coinStat);

    content.appendChild(stats);
    card.appendChild(content);

    // Click to open modal
    card.addEventListener('click', () => openBiliModal(video));

    return card;
}

function setupBiliEventListeners() {
    // Source filter
    if (biliSourceFilter) {
        biliSourceFilter.addEventListener('change', (e) => {
            currentBiliSource = e.target.value;
            loadBilibiliData();
        });
    }

    // Search (debounce)
    if (biliSearchInput) {
        let searchTimeout;
        biliSearchInput.addEventListener('input', (e) => {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                currentBiliSearch = e.target.value.trim();
                loadBilibiliData();
            }, 300);
        });
    }

    // Refresh button
    if (biliRefreshBtn) {
        biliRefreshBtn.addEventListener('click', async () => {
            biliRefreshBtn.classList.add('loading');
            await loadBilibiliData();
            biliRefreshBtn.classList.remove('loading');
        });
    }
}

function showBiliLoading(show) {
    if (biliLoadingState) biliLoadingState.style.display = show ? 'flex' : 'none';
    if (show && biliEmptyState) biliEmptyState.style.display = 'none';
}

function showBiliError(message) {
    if (biliEmptyState) {
        biliEmptyState.style.display = 'flex';
        const emptyText = biliEmptyState.querySelector('.empty-text');
        const emptyHint = biliEmptyState.querySelector('.empty-hint');
        if (emptyText) emptyText.textContent = message;
        if (emptyHint) emptyHint.textContent = 'Please check network connection or refresh';
    }
}

function updateBiliLastUpdate() {
    if (biliLastUpdate) {
        const now = new Date();
        const timeStr = now.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
        biliLastUpdate.textContent = `Updated ${timeStr}`;
    }
}

function formatBiliNumber(num) {
    if (!num) return '0';
    const n = parseInt(num);
    if (isNaN(n)) return '0';
    if (n >= 100000000) {
        return (n / 100000000).toFixed(1) + 'B';
    }
    if (n >= 10000) {
        return (n / 10000).toFixed(1) + 'W';
    }
    if (n >= 1000) {
        return (n / 1000).toFixed(1) + 'K';
    }
    return n.toString();
}

function formatBiliDuration(playCount) {
    // Just a visual indicator based on play count
    return '';
}

// Export for global access
window.biliApp = {
    init: initBilibili,
    loadVideos: loadBilibiliData,
    loadStats: loadBilibiliData
};

// Subscribe to WebSocket updates for Bilibili (bili)
// Use a small delay to ensure WSClient is fully initialized
function subscribeToBilibiliUpdates() {
    if (window.WSClient && typeof window.WSClient.subscribe === 'function') {
        window.WSClient.subscribe('bili', (data) => {
            console.log('[BILI] Received update notification:', data.type);

            // 显示实时数据通知弹窗
            if (window.DataNotification) {
                if (data.type === 'data_update') {
                    window.DataNotification.handleDataUpdate(data);
                } else {
                    window.DataNotification.show({
                        platform: 'bili',
                        message: '📺 B站数据已更新'
                    });
                }
            }

            // Only reload if Bilibili panel is visible
            const biliPanel = document.getElementById('bilibili-panel');
            if (biliPanel && biliPanel.style.display !== 'none') {
                loadBilibiliData();
            }
        });
        console.log('[BILI] Subscribed to WebSocket updates');
    } else {
        // Retry after a short delay if WSClient not ready
        setTimeout(subscribeToBilibiliUpdates, 100);
    }
}
subscribeToBilibiliUpdates();
