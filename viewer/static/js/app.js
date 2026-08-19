// 主应用逻辑

let allNotes = [];
let currentKeyword = '';
let currentSearch = '';
let refreshTimeout = null;

// DOM 元素
const notesGrid = document.getElementById('notesGrid');
const emptyState = document.getElementById('emptyState');
const loadingState = document.getElementById('loadingState');
const keywordFilter = document.getElementById('keywordFilter');
const searchInput = document.getElementById('searchInput');
const refreshBtn = document.getElementById('refreshBtn');
const lastUpdate = document.getElementById('lastUpdate');

// 初始化
document.addEventListener('DOMContentLoaded', async () => {
    try {
        await loadKeywords();
        await loadNotes();
        setupEventListeners();
        setupLazyLoading();
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
    showLoading(true);

    try {
        const params = {};
        if (currentKeyword) params.keyword = currentKeyword;
        if (currentSearch) params.search = currentSearch;

        const data = await API.getNotes(params);
        allNotes = data.notes;

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

// 设置事件监听
function setupEventListeners() {
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
    refreshBtn.addEventListener('click', async () => {
        refreshBtn.classList.add('loading');
        await loadNotes();
        refreshBtn.classList.remove('loading');
    });
}

// 设置懒加载
function setupLazyLoading() {
    if ('IntersectionObserver' in window) {
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
