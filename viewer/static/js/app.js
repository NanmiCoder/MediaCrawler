// 主应用逻辑

let allNotes = [];
let currentKeyword = '';
let currentSearch = '';
let refreshTimeout = null;

// 无限滚动状态变量
let currentOffset = 0;
let currentLimit = 100;
let isLoadingMore = false;
let hasMoreData = true;

// 排序状态变量
let currentSortOrder = 'time'; // 默认按时间排序
const SORT_STORAGE_KEY = 'xhs_sort_order';

// DOM 元素 - 在DOMContentLoaded后初始化
let notesGrid, emptyState, loadingState, keywordFilter, searchInput, refreshBtn, lastUpdate;

// 初始化
document.addEventListener('DOMContentLoaded', async () => {
    console.log('[XHS] DOMContentLoaded - starting initialization');

    // 读取保存的排序偏好
    const savedSort = localStorage.getItem(SORT_STORAGE_KEY);
    if (savedSort) {
        currentSortOrder = savedSort;
    }

    // 初始化DOM元素引用
    notesGrid = document.getElementById('notesGrid');
    emptyState = document.getElementById('emptyState');
    loadingState = document.getElementById('loadingState');
    keywordFilter = document.getElementById('keywordFilter');
    searchInput = document.getElementById('searchInput');
    refreshBtn = document.getElementById('refreshBtn');
    lastUpdate = document.getElementById('lastUpdate');

    console.log('[XHS] DOM elements:', {
        notesGrid: !!notesGrid,
        emptyState: !!emptyState,
        loadingState: !!loadingState,
        keywordFilter: !!keywordFilter,
        searchInput: !!searchInput,
        refreshBtn: !!refreshBtn,
        lastUpdate: !!lastUpdate
    });

    // 如果 refreshBtn 不存在，尝试直接绑定
    if (!refreshBtn) {
        console.error('[XHS] refreshBtn not found! Trying to find it...');
        refreshBtn = document.querySelector('.refresh-btn');
        console.log('[XHS] Found via querySelector:', !!refreshBtn);
    }

    try {
        await loadKeywords();
        console.log('[XHS] loadKeywords done');
        await loadNotes();
        console.log('[XHS] loadNotes done');
        setupEventListeners();
        console.log('[XHS] setupEventListeners done');
        setupLazyLoading();
        console.log('[XHS] setupLazyLoading done');
    } catch (error) {
        console.error('初始化失败:', error);
        showError('加载数据失败，请刷新页面重试');
    }
});

// 加载关键词列表
async function loadKeywords() {
    try {
        const data = await API.getKeywords();
        keywordFilter.innerHTML = '<option value="">全部关键词</option>';
        data.keywords.forEach(keyword => {
            const option = document.createElement('option');
            option.value = keyword;
            option.textContent = keyword;
            keywordFilter.appendChild(option);
        });
    } catch (error) {
        console.error('加载关键词失败:', error);
    }
}

// 加载笔记数据
async function loadNotes() {
    console.log('[XHS] loadNotes called');
    showLoading(true);

    // 重置分页状态
    currentOffset = 0;
    hasMoreData = true;

    try {
        const params = {};
        if (currentKeyword) params.keyword = currentKeyword;
        if (currentSearch) params.search = currentSearch;

        console.log('[XHS] Fetching notes with params:', params);
        const data = await API.getNotes(params);
        allNotes = data.notes;
        console.log('[XHS] Loaded notes:', allNotes.length);

        // 更新分页状态
        currentOffset = allNotes.length;
        hasMoreData = allNotes.length === currentLimit;

        renderNotes(allNotes);
        updateLastUpdate();
    } catch (error) {
        console.error('加载笔记失败:', error);
        showError('加载笔记数据失败');
    } finally {
        showLoading(false);
    }
}

// 渲染笔记列表
function renderNotes(notes) {
    notesGrid.innerHTML = '';

    if (notes.length === 0) {
        emptyState.style.display = 'flex';
        return;
    }

    emptyState.style.display = 'none';

    notes.forEach(note => {
        const card = createNoteCard(note);
        notesGrid.appendChild(card);
    });

    // 触发懒加载
    triggerLazyLoad();

    // 设置无限滚动 sentinel
    setupInfiniteScrollSentinel();

    // 滚动到顶部
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// 加载更多笔记数据（无限滚动）
async function loadMoreNotes() {
    // 检查是否可以加载
    if (isLoadingMore || !hasMoreData) {
        return;
    }

    isLoadingMore = true;
    showLoadingMore(true);

    try {
        const params = {
            offset: currentOffset,
            limit: currentLimit
        };
        if (currentKeyword) params.keyword = currentKeyword;
        if (currentSearch) params.search = currentSearch;

        console.log('[XHS] Loading more notes with params:', params);
        const data = await API.getNotes(params);
        const newNotes = data.notes;

        if (newNotes.length > 0) {
            // 追加到 allNotes
            allNotes = [...allNotes, ...newNotes];
            currentOffset += newNotes.length;

            // 增量渲染
            renderMoreNotes(newNotes);
        }

        // 更新 hasMoreData 状态
        hasMoreData = newNotes.length === currentLimit;

    } catch (error) {
        console.error('加载更多笔记失败:', error);
    } finally {
        isLoadingMore = false;
        // 只有还有更多数据时才清除加载指示器
        // 如果没有更多数据，显示"没有更多数据了"
        if (hasMoreData) {
            showLoadingMore(false);
        } else {
            showNoMoreData();
        }
    }
}

// 增量渲染笔记（无限滚动）
function renderMoreNotes(notes) {
    notes.forEach(note => {
        const card = createNoteCard(note);
        notesGrid.appendChild(card);
    });

    // 触发懒加载
    triggerLazyLoad();

    // 不滚动，保持当前位置
}

// 创建笔记卡片
function createNoteCard(note) {
    const card = document.createElement('div');
    card.className = 'note-card';
    card.dataset.noteId = note.note_id;

    // 图片区域
    const imageContainer = document.createElement('div');
    imageContainer.style.position = 'relative';

    if (note.first_image_url) {
        const img = document.createElement('img');
        img.className = 'note-card-image lazy';
        img.dataset.src = note.first_image_url;
        img.alt = note.title;
        img.onerror = () => {
            img.style.display = 'none';
            const placeholder = document.createElement('div');
            placeholder.className = 'note-card-placeholder';
            placeholder.textContent = '🖼️';
            imageContainer.appendChild(placeholder);
        };
        imageContainer.appendChild(img);
    } else {
        const placeholder = document.createElement('div');
        placeholder.className = 'note-card-placeholder';
        placeholder.textContent = note.type === 'video' ? '🎬' : '📝';
        imageContainer.appendChild(placeholder);
    }

    // 视频标识
    if (note.type === 'video') {
        const badge = document.createElement('span');
        badge.className = 'video-badge';
        badge.textContent = '🎬 视频';
        imageContainer.appendChild(badge);
    }

    card.appendChild(imageContainer);

    // 内容区域
    const content = document.createElement('div');
    content.className = 'note-card-content';

    const title = document.createElement('h3');
    title.className = 'note-card-title';
    title.textContent = note.title || '无标题';
    content.appendChild(title);

    const meta = document.createElement('div');
    meta.className = 'note-card-meta';

    const author = document.createElement('div');
    author.className = 'note-card-author';
    if (note.avatar) {
        const avatar = document.createElement('img');
        avatar.src = note.avatar;
        avatar.onerror = () => avatar.style.display = 'none';
        author.appendChild(avatar);
    }
    const authorName = document.createElement('span');
    authorName.textContent = note.nickname || '匿名用户';
    author.appendChild(authorName);
    meta.appendChild(author);

    const stats = document.createElement('div');
    stats.className = 'note-card-stats';

    const likes = document.createElement('span');
    likes.textContent = `👍 ${formatCount(note.liked_count)}`;
    stats.appendChild(likes);

    const collects = document.createElement('span');
    collects.textContent = `⭐ ${formatCount(note.collected_count)}`;
    stats.appendChild(collects);

    meta.appendChild(stats);

    // 时间显示
    if (note.time) {
        const timeEl = document.createElement('div');
        timeEl.className = 'note-card-time';
        timeEl.textContent = formatTime(note.time);
        content.appendChild(timeEl);
    }

    content.appendChild(meta);
    card.appendChild(content);

    // 点击事件
    card.addEventListener('click', () => openNoteModal(note));

    return card;
}

// 格式化数量显示
function formatCount(count) {
    if (!count) return '0';
    return count;
}

// 格式化时间显示
function formatTime(timestamp) {
    if (!timestamp) return '';
    const date = new Date(timestamp * 1000); // Unix timestamp to Date
    const now = new Date();
    const diff = (now - date) / 1000; // 秒

    if (diff < 60) return '刚刚';
    if (diff < 3600) return `${Math.floor(diff / 60)}分钟前`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}小时前`;
    if (diff < 604800) return `${Math.floor(diff / 86400)}天前`;

    // 超过一周显示日期
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}

// 设置事件监听
function setupEventListeners() {
    console.log('[XHS] Setting up event listeners');
    console.log('[XHS] refreshBtn element:', refreshBtn);

    // 关键词筛选
    keywordFilter.addEventListener('change', (e) => {
        currentKeyword = e.target.value;
        loadNotes();
    });

    // 搜索（防抖）
    let searchTimeout;
    searchInput.addEventListener('input', (e) => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            currentSearch = e.target.value.trim();
            loadNotes();
        }, 300);
    });

    // 刷新按钮
    refreshBtn.addEventListener('click', async (e) => {
        console.log('[XHS] Refresh button clicked!');
        e.preventDefault();
        refreshBtn.classList.add('loading');
        try {
            await loadNotes();
        } finally {
            refreshBtn.classList.remove('loading');
        }
    });
    console.log('[XHS] Refresh button listener attached');

    // 排序选择器
    const sortSelect = document.getElementById('sortSelect');
    if (sortSelect) {
        sortSelect.value = currentSortOrder;
        sortSelect.addEventListener('change', (e) => {
            currentSortOrder = e.target.value;
            localStorage.setItem(SORT_STORAGE_KEY, currentSortOrder);
            // 重新加载数据
            loadNotes();
        });
        console.log('[XHS] Sort select listener attached');
    }
}

// 设置懒加载和无限滚动
function setupLazyLoading() {
    if ('IntersectionObserver' in window) {
        // 图片懒加载 Observer
        window.lazyObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    if (img.dataset.src) {
                        img.src = img.dataset.src;
                        img.onload = () => img.classList.add('loaded');
                        window.lazyObserver.unobserve(img);
                    }
                }
            });
        }, {
            rootMargin: '100px'
        });

        // 无限滚动 Observer
        window.scrollObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting && !isLoadingMore && hasMoreData) {
                    console.log('[XHS] Infinite scroll triggered');
                    loadMoreNotes();
                }
            });
        }, {
            rootMargin: '100px'
        });
    }
}

// 触发懒加载
function triggerLazyLoad() {
    const images = notesGrid.querySelectorAll('.note-card-image.lazy');
    images.forEach(img => {
        if (window.lazyObserver) {
            window.lazyObserver.observe(img);
        } else {
            // 降级处理
            if (img.dataset.src) {
                img.src = img.dataset.src;
                img.onload = () => img.classList.add('loaded');
            }
        }
    });
}

// 显示/隐藏加载状态
function showLoading(show) {
    loadingState.style.display = show ? 'flex' : 'none';
    if (show) {
        emptyState.style.display = 'none';
    }
}

// 显示错误
function showError(message) {
    emptyState.style.display = 'flex';
    emptyState.querySelector('.empty-text').textContent = message;
    emptyState.querySelector('.empty-hint').textContent = '请检查网络连接或刷新页面';
}

// 显示/隐藏加载更多指示器
function showLoadingMore(show) {
    let sentinel = document.getElementById('infinite-scroll-sentinel');
    if (!sentinel) {
        sentinel = document.createElement('div');
        sentinel.id = 'infinite-scroll-sentinel';
        notesGrid.appendChild(sentinel);
    }

    if (show) {
        sentinel.innerHTML = `
            <div class="loading-more">
                <div class="loading-spinner"></div>
                <span>加载中...</span>
            </div>
        `;
    } else {
        sentinel.innerHTML = '';
    }
}

// 显示没有更多数据
function showNoMoreData() {
    let sentinel = document.getElementById('infinite-scroll-sentinel');
    if (!sentinel) {
        sentinel = document.createElement('div');
        sentinel.id = 'infinite-scroll-sentinel';
        notesGrid.appendChild(sentinel);
    }

    sentinel.innerHTML = `<div class="no-more">没有更多数据了</div>`;
}

// 设置无限滚动 sentinel
function setupInfiniteScrollSentinel() {
    let sentinel = document.getElementById('infinite-scroll-sentinel');
    if (!sentinel) {
        sentinel = document.createElement('div');
        sentinel.id = 'infinite-scroll-sentinel';
        notesGrid.appendChild(sentinel);
    }

    if (window.scrollObserver) {
        window.scrollObserver.observe(sentinel);
    }
}

// 更新最后更新时间
function updateLastUpdate() {
    const now = new Date();
    const timeStr = now.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
    lastUpdate.textContent = `更新于 ${timeStr}`;
}

// 导出函数供其他模块使用
window.app = {
    loadNotes,
    updateLastUpdate
};

// Subscribe to WebSocket updates for Xiaohongshu (xhs)
// Use a small delay to ensure WSClient is fully initialized
function subscribeToXhsUpdates() {
    if (window.WSClient && typeof window.WSClient.subscribe === 'function') {
        window.WSClient.subscribe('xhs', (data) => {
            console.log('[XHS] Received update notification:', data.type);

            // 显示实时数据通知弹窗
            if (window.DataNotification) {
                if (data.type === 'data_update') {
                    window.DataNotification.handleDataUpdate(data);
                } else if (data.type === 'subscription_update') {
                    window.DataNotification.handleSubscriptionUpdate(data);
                } else if (data.type === 'stats_update') {
                    // 统计更新仅用于数据展示，不触发通知
                    console.log('[XHS] Stats updated:', data.total_notes, 'notes');
                }
            }

            // Only reload if XHS panel is visible
            const xhsPanel = document.getElementById('xiaohongshu-panel');
            if (xhsPanel && xhsPanel.style.display !== 'none') {
                loadNotes();
            }
        });
        console.log('[XHS] Subscribed to WebSocket updates');
    } else {
        // Retry after a short delay if WSClient not ready
        setTimeout(subscribeToXhsUpdates, 100);
    }
}
subscribeToXhsUpdates();
