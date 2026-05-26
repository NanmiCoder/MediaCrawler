// Douyin Modal - Video detail modal

let currentDyVideo = null;

// Initialize modal
function initDyModal() {
    const modal = document.getElementById('dyModal');
    const closeBtn = document.getElementById('dyModalClose');
    const overlay = modal?.querySelector('.modal-overlay');

    if (closeBtn) {
        closeBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            closeDyModal();
        });
    }

    if (overlay) {
        overlay.addEventListener('click', () => {
            closeDyModal();
        });
    }

    // ESC key to close
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && modal?.style.display !== 'none') {
            closeDyModal();
        }
    });
}

function openDyModal(video) {
    currentDyVideo = video;

    const modal = document.getElementById('dyModal');
    if (!modal) return;

    // Set cover image
    const coverImg = document.getElementById('dyModalCover');
    if (coverImg) {
        if (video.video_cover_url) {
            coverImg.src = video.video_cover_url;
            coverImg.style.display = 'block';
        } else {
            coverImg.style.display = 'none';
        }
    }

    // Set title
    const titleEl = document.getElementById('dyModalTitle');
    if (titleEl) titleEl.textContent = video.title || video.desc || '无标题';

    // Set author
    const authorAvatar = document.getElementById('dyModalAuthorAvatar');
    const authorName = document.getElementById('dyModalAuthorName');
    if (authorAvatar && video.avatar) {
        authorAvatar.src = video.avatar;
    }
    if (authorName) authorName.textContent = video.nickname || '匿名用户';

    // Set time
    const timeEl = document.getElementById('dyModalTime');
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
    const playCount = document.getElementById('dyModalPlay');
    const likeCount = document.getElementById('dyModalLike');
    const commentCount = document.getElementById('dyModalComment');
    const shareCount = document.getElementById('dyModalShare');
    const collectCount = document.getElementById('dyModalCollect');

    if (playCount) playCount.textContent = formatDyModalNumber(video.play_count);
    if (likeCount) likeCount.textContent = formatDyModalNumber(video.liked_count);
    if (commentCount) commentCount.textContent = formatDyModalNumber(video.comment_count);
    if (shareCount) shareCount.textContent = formatDyModalNumber(video.share_count);
    if (collectCount) collectCount.textContent = formatDyModalNumber(video.collect_count);

    // Set description
    const descEl = document.getElementById('dyModalDesc');
    if (descEl) {
        descEl.textContent = video.desc || '暂无描述';
        descEl.style.whiteSpace = 'pre-wrap';
    }

    // Set music info
    const musicEl = document.getElementById('dyModalMusic');
    if (musicEl) {
        if (video.music_title) {
            musicEl.textContent = `🎵 ${video.music_title}${video.music_author ? ' - ' + video.music_author : ''}`;
            musicEl.style.display = 'block';
        } else {
            musicEl.style.display = 'none';
        }
    }

    // Set link
    const linkEl = document.getElementById('dyModalLink');
    if (linkEl && video.video_url) {
        linkEl.href = video.video_url;
        linkEl.style.display = 'inline-flex';
    } else if (linkEl) {
        linkEl.style.display = 'none';
    }

    // Load comments
    loadDyModalComments(video.aweme_id);

    // Show modal
    modal.style.display = 'block';
    document.body.style.overflow = 'hidden';
}

function closeDyModal() {
    const modal = document.getElementById('dyModal');
    if (modal) {
        modal.style.display = 'none';
        document.body.style.overflow = '';
    }
    currentDyVideo = null;
}

async function loadDyModalComments(awemeId) {
    const commentsContainer = document.getElementById('dyModalComments');
    if (!commentsContainer) return;

    commentsContainer.innerHTML = '<div class="dy-comments-loading">加载评论中...</div>';

    try {
        const data = await DyAPI.getVideoComments(awemeId, { limit: 20 });

        if (data.comments && data.comments.length > 0) {
            renderDyComments(data.comments, commentsContainer);
        } else {
            commentsContainer.innerHTML = '<div class="dy-comments-empty">暂无评论</div>';
        }
    } catch (error) {
        console.error('Failed to load comments:', error);
        commentsContainer.innerHTML = '<div class="dy-comments-empty">加载评论失败</div>';
    }
}

function renderDyComments(comments, container) {
    container.innerHTML = '';

    comments.forEach(comment => {
        const commentEl = document.createElement('div');
        commentEl.className = 'dy-comment';

        const header = document.createElement('div');
        header.className = 'dy-comment-header';

        if (comment.avatar) {
            const avatar = document.createElement('img');
            avatar.className = 'dy-comment-avatar';
            avatar.src = comment.avatar;
            header.appendChild(avatar);
        }

        const info = document.createElement('div');
        info.className = 'dy-comment-info';

        const name = document.createElement('span');
        name.className = 'dy-comment-name';
        name.textContent = comment.nickname || '匿名用户';
        info.appendChild(name);

        const time = document.createElement('span');
        time.className = 'dy-comment-time';
        if (comment.create_time) {
            const date = new Date(comment.create_time * 1000);
            time.textContent = date.toLocaleDateString('zh-CN');
        }
        info.appendChild(time);

        header.appendChild(info);
        commentEl.appendChild(header);

        const content = document.createElement('div');
        content.className = 'dy-comment-content';
        content.textContent = comment.content || '';
        commentEl.appendChild(content);

        const actions = document.createElement('div');
        actions.className = 'dy-comment-actions';

        const likeSpan = document.createElement('span');
        likeSpan.innerHTML = `<svg viewBox="0 0 24 24" width="14" height="14"><path fill="currentColor" d="M1 21h4V9H1v12zm22-11c0-1.1-.9-2-2-2h-6.31l.95-4.57.03-.32c0-.41-.17-.79-.44-1.06L14.17 1 7.59 7.59C7.22 7.95 7 8.45 7 9v10c0 1.1.9 2 2 2h9c.83 0 1.54-.5 1.84-1.22l3.02-7.05c.09-.23.14-.47.14-.73v-2z"/></svg> ${comment.like_count || 0}`;
        actions.appendChild(likeSpan);

        commentEl.appendChild(actions);
        container.appendChild(commentEl);
    });
}

function formatDyModalNumber(num) {
    if (!num) return '0';
    const n = parseInt(num);
    if (isNaN(n)) return '0';
    if (n >= 100000000) {
        return (n / 100000000).toFixed(1) + '亿';
    }
    if (n >= 10000) {
        return (n / 10000).toFixed(1) + 'w';
    }
    return n.toLocaleString();
}

// Export
window.dyModal = {
    init: initDyModal,
    open: openDyModal,
    close: closeDyModal
};
