// Bilibili Modal - Video detail modal

let currentBiliVideo = null;

// Initialize modal
function initBiliModal() {
    const modal = document.getElementById('biliModal');
    const closeBtn = document.getElementById('biliModalClose');
    const overlay = modal?.querySelector('.modal-overlay');

    if (closeBtn) {
        closeBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            closeBiliModal();
        });
    }

    if (overlay) {
        overlay.addEventListener('click', () => {
            closeBiliModal();
        });
    }

    // ESC key to close
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && modal?.style.display !== 'none') {
            closeBiliModal();
        }
    });
}

function openBiliModal(video) {
    currentBiliVideo = video;

    const modal = document.getElementById('biliModal');
    if (!modal) return;

    // Set cover image
    const coverImg = document.getElementById('biliModalCover');
    if (coverImg) {
        if (video.video_cover_url) {
            coverImg.src = video.video_cover_url;
            coverImg.style.display = 'block';
        } else {
            coverImg.style.display = 'none';
        }
    }

    // Set title
    const titleEl = document.getElementById('biliModalTitle');
    if (titleEl) titleEl.textContent = video.title || 'No Title';

    // Set author
    const authorAvatar = document.getElementById('biliModalAuthorAvatar');
    const authorName = document.getElementById('biliModalAuthorName');
    if (authorAvatar && video.avatar) {
        authorAvatar.src = video.avatar;
    }
    if (authorName) authorName.textContent = video.nickname || 'Anonymous';

    // Set time
    const timeEl = document.getElementById('biliModalTime');
    if (timeEl) {
        const timestamp = video.create_time;
        if (timestamp) {
            const date = new Date(timestamp * 1000);
            timeEl.textContent = date.toLocaleDateString('zh-CN');
        } else {
            timeEl.textContent = '';
        }
    }

    // Set stats
    const playCount = document.getElementById('biliModalPlay');
    const likeCount = document.getElementById('biliModalLike');
    const coinCount = document.getElementById('biliModalCoin');
    const favoriteCount = document.getElementById('biliModalFavorite');
    const shareCount = document.getElementById('biliModalShare');
    const danmakuCount = document.getElementById('biliModalDanmaku');
    const commentCount = document.getElementById('biliModalComment');

    if (playCount) playCount.textContent = formatBiliModalNumber(video.video_play_count);
    if (likeCount) likeCount.textContent = formatBiliModalNumber(video.liked_count);
    if (coinCount) coinCount.textContent = formatBiliModalNumber(video.video_coin_count);
    if (favoriteCount) favoriteCount.textContent = formatBiliModalNumber(video.video_favorite_count);
    if (shareCount) shareCount.textContent = formatBiliModalNumber(video.video_share_count);
    if (danmakuCount) danmakuCount.textContent = formatBiliModalNumber(video.video_danmaku);
    if (commentCount) commentCount.textContent = formatBiliModalNumber(video.video_comment);

    // Set description
    const descEl = document.getElementById('biliModalDesc');
    if (descEl) {
        descEl.textContent = video.desc || 'No description';
        descEl.style.whiteSpace = 'pre-wrap';
    }

    // Set link
    const linkEl = document.getElementById('biliModalLink');
    if (linkEl && video.video_url) {
        linkEl.href = video.video_url;
        linkEl.style.display = 'inline-flex';
    } else if (linkEl) {
        linkEl.style.display = 'none';
    }

    // Load comments
    loadBiliModalComments(video.video_id);

    // Show modal
    modal.style.display = 'block';
    document.body.style.overflow = 'hidden';
}

function closeBiliModal() {
    const modal = document.getElementById('biliModal');
    if (modal) {
        modal.style.display = 'none';
        document.body.style.overflow = '';
    }
    currentBiliVideo = null;
}

async function loadBiliModalComments(videoId) {
    const commentsContainer = document.getElementById('biliModalComments');
    if (!commentsContainer) return;

    commentsContainer.innerHTML = '<div class="bili-comments-loading">Loading comments...</div>';

    try {
        const data = await BiliAPI.getVideoComments(videoId, { limit: 20 });

        if (data.comments && data.comments.length > 0) {
            renderBiliComments(data.comments, commentsContainer);
        } else {
            commentsContainer.innerHTML = '<div class="bili-comments-empty">No comments yet</div>';
        }
    } catch (error) {
        console.error('Failed to load comments:', error);
        commentsContainer.innerHTML = '<div class="bili-comments-empty">Failed to load comments</div>';
    }
}

function renderBiliComments(comments, container) {
    container.innerHTML = '';

    comments.forEach(comment => {
        const commentEl = document.createElement('div');
        commentEl.className = 'bili-comment';

        const header = document.createElement('div');
        header.className = 'bili-comment-header';

        if (comment.avatar) {
            const avatar = document.createElement('img');
            avatar.className = 'bili-comment-avatar';
            avatar.src = comment.avatar;
            header.appendChild(avatar);
        }

        const info = document.createElement('div');
        info.className = 'bili-comment-info';

        const name = document.createElement('span');
        name.className = 'bili-comment-name';
        name.textContent = comment.nickname || 'Anonymous';
        info.appendChild(name);

        const time = document.createElement('span');
        time.className = 'bili-comment-time';
        if (comment.create_time) {
            const date = new Date(comment.create_time * 1000);
            time.textContent = date.toLocaleDateString('zh-CN');
        }
        info.appendChild(time);

        header.appendChild(info);
        commentEl.appendChild(header);

        const content = document.createElement('div');
        content.className = 'bili-comment-content';
        content.textContent = comment.content || '';
        commentEl.appendChild(content);

        const actions = document.createElement('div');
        actions.className = 'bili-comment-actions';

        const likeSpan = document.createElement('span');
        likeSpan.innerHTML = `<svg viewBox="0 0 24 24" width="14" height="14"><path fill="currentColor" d="M1 21h4V9H1v12zm22-11c0-1.1-.9-2-2-2h-6.31l.95-4.57.03-.32c0-.41-.17-.79-.44-1.06L14.17 1 7.59 7.59C7.22 7.95 7 8.45 7 9v10c0 1.1.9 2 2 2h9c.83 0 1.54-.5 1.84-1.22l3.02-7.05c.09-.23.14-.47.14-.73v-2z"/></svg> ${comment.like_count || 0}`;
        actions.appendChild(likeSpan);

        commentEl.appendChild(actions);
        container.appendChild(commentEl);
    });
}

function formatBiliModalNumber(num) {
    if (!num) return '0';
    const n = parseInt(num);
    if (isNaN(n)) return '0';
    if (n >= 100000000) {
        return (n / 100000000).toFixed(1) + ' B';
    }
    if (n >= 10000) {
        return (n / 10000).toFixed(1) + ' W';
    }
    return n.toLocaleString();
}

// Export
window.biliModal = {
    init: initBiliModal,
    open: openBiliModal,
    close: closeBiliModal
};
