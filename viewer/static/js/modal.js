// 笔记详情模态框

let currentNote = null;
let currentImageIndex = 0;
let currentImages = [];

// DOM 元素 - 在DOMContentLoaded后初始化
let noteModal, modalClose, modalOverlay, galleryImage, galleryPrev, galleryNext;
let galleryIndex, imageGallery, modalTitle, modalAuthor, modalTime;
let modalLikes, modalCollects, modalComments, modalShares, modalTags, modalDesc, modalLink;

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    // 初始化DOM元素引用
    noteModal = document.getElementById('noteModal');
    modalClose = document.getElementById('modalClose');
    if (noteModal) {
        modalOverlay = noteModal.querySelector('.modal-overlay');
    }
    galleryImage = document.getElementById('galleryImage');
    galleryPrev = document.getElementById('galleryPrev');
    galleryNext = document.getElementById('galleryNext');
    galleryIndex = document.getElementById('galleryIndex');
    imageGallery = document.getElementById('imageGallery');
    modalTitle = document.getElementById('modalTitle');
    modalAuthor = document.getElementById('modalAuthor');
    modalTime = document.getElementById('modalTime');
    modalLikes = document.getElementById('modalLikes');
    modalCollects = document.getElementById('modalCollects');
    modalComments = document.getElementById('modalComments');
    modalShares = document.getElementById('modalShares');
    modalTags = document.getElementById('modalTags');
    modalDesc = document.getElementById('modalDesc');
    modalLink = document.getElementById('modalLink');

    setupModalEvents();
});

// 设置模态框事件
function setupModalEvents() {
    if (!noteModal || !modalClose || !modalOverlay) return;

    // 关闭按钮
    modalClose.addEventListener('click', (e) => {
        e.stopPropagation();
        closeNoteModal();
    });

    // 点击遮罩关闭
    modalOverlay.addEventListener('click', () => {
        closeNoteModal();
    });

    // ESC 键关闭
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && noteModal && noteModal.style.display !== 'none') {
            closeNoteModal();
        }
        // 图片导航
        if (noteModal && noteModal.style.display !== 'none') {
            if (e.key === 'ArrowLeft') navigateGallery(-1);
            if (e.key === 'ArrowRight') navigateGallery(1);
        }
    });

    // 图片导航按钮
    if (galleryPrev) galleryPrev.addEventListener('click', () => navigateGallery(-1));
    if (galleryNext) galleryNext.addEventListener('click', () => navigateGallery(1));
}

// 打开笔记详情模态框
async function openNoteModal(note) {
    if (!noteModal) return;

    currentNote = note;
    currentImageIndex = 0;

    // 设置基本信息
    if (modalTitle) modalTitle.textContent = note.title || '无标题';
    if (modalAuthor) modalAuthor.textContent = `作者: ${note.nickname || '匿名用户'}`;
    if (modalTime) modalTime.textContent = note.time || '';

    // 设置统计数据
    if (modalLikes) modalLikes.textContent = formatCount(note.liked_count);
    if (modalCollects) modalCollects.textContent = formatCount(note.collected_count);
    if (modalComments) modalComments.textContent = formatCount(note.comment_count);
    if (modalShares) modalShares.textContent = formatCount(note.share_count);

    // 设置标签
    if (modalTags) {
        modalTags.innerHTML = '';
        if (note.keywords && note.keywords.length > 0) {
            note.keywords.forEach(keyword => {
                const tag = document.createElement('span');
                tag.className = 'note-tag';
                tag.textContent = `#${keyword}`;
                tag.addEventListener('click', () => {
                    closeNoteModal();
                    // 点击标签筛选该关键词
                    if (keywordFilter) keywordFilter.value = keyword;
                    currentKeyword = keyword;
                    loadNotes();
                });
                modalTags.appendChild(tag);
            });
        }
    }

    // 设置描述
    if (modalDesc) modalDesc.textContent = note.desc || '暂无描述';

    // 设置原笔记链接
    if (modalLink) {
        if (note.note_url) {
            modalLink.href = note.note_url;
            modalLink.style.display = 'inline-block';
        } else {
            modalLink.style.display = 'none';
        }
    }

    // 设置图片画廊
    currentImages = note.image_list || [];
    if (currentImages.length > 0) {
        if (imageGallery) imageGallery.style.display = 'block';
        updateGallery();
    } else if (note.video_url) {
        // 视频内容
        if (imageGallery) imageGallery.style.display = 'block';
        if (galleryImage) {
            galleryImage.src = '';
            galleryImage.style.display = 'none';
        }
        if (galleryPrev) galleryPrev.style.display = 'none';
        if (galleryNext) galleryNext.style.display = 'none';
        if (galleryIndex) galleryIndex.textContent = '🎬 视频内容';

        // 创建视频播放器
        const videoContainer = document.createElement('div');
        videoContainer.className = 'video-container';
        videoContainer.innerHTML = `
            <video controls style="width: 100%; max-height: 400px;">
                <source src="${note.video_url}" type="video/mp4">
                您的浏览器不支持视频播放
            </video>
        `;
        const galleryMain = document.querySelector('.gallery-main');
        if (galleryMain) {
            const existingVideo = galleryMain.querySelector('.video-container');
            if (existingVideo) existingVideo.remove();
            galleryMain.appendChild(videoContainer);
        }
    } else {
        if (imageGallery) imageGallery.style.display = 'none';
    }

    // 显示模态框
    noteModal.style.display = 'flex';
    document.body.style.overflow = 'hidden';
}

// 关闭模态框
function closeNoteModal() {
    if (!noteModal) return;

    noteModal.style.display = 'none';
    document.body.style.overflow = '';

    // 清理视频
    const videoContainer = document.querySelector('.gallery-main .video-container');
    if (videoContainer) {
        videoContainer.remove();
    }
    if (galleryImage) galleryImage.style.display = 'block';

    currentNote = null;
    currentImages = [];
}

// 更新图片画廊
function updateGallery() {
    if (currentImages.length === 0) return;

    // 移除视频容器
    const videoContainer = document.querySelector('.gallery-main .video-container');
    if (videoContainer) videoContainer.remove();
    if (galleryImage) galleryImage.style.display = 'block';

    if (galleryImage) {
        galleryImage.src = currentImages[currentImageIndex];
        galleryImage.alt = currentNote?.title || '笔记图片';
    }

    // 更新索引显示
    if (galleryIndex) galleryIndex.textContent = `${currentImageIndex + 1}/${currentImages.length}`;

    // 更新导航按钮
    if (galleryPrev) galleryPrev.style.display = currentImages.length > 1 ? 'flex' : 'none';
    if (galleryNext) galleryNext.style.display = currentImages.length > 1 ? 'flex' : 'none';

    // 更新按钮状态
    if (galleryPrev) galleryPrev.style.opacity = currentImageIndex === 0 ? '0.5' : '1';
    if (galleryNext) galleryNext.style.opacity = currentImageIndex === currentImages.length - 1 ? '0.5' : '1';
}

// 图片导航
function navigateGallery(direction) {
    if (currentImages.length <= 1) return;

    currentImageIndex += direction;

    // 循环导航
    if (currentImageIndex < 0) currentImageIndex = currentImages.length - 1;
    if (currentImageIndex >= currentImages.length) currentImageIndex = 0;

    updateGallery();
}

// 格式化数量
function formatCount(count) {
    if (!count) return '0';
    const num = parseInt(count);
    if (isNaN(num)) return count;
    if (num >= 10000) {
        return (num / 10000).toFixed(1) + 'w';
    }
    if (num >= 1000) {
        return (num / 1000).toFixed(1) + 'k';
    }
    return num.toString();
}

// 导出函数
window.modal = {
    openNoteModal,
    closeNoteModal
};
