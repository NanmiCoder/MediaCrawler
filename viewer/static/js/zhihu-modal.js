// 知乎回答详情模态框

let currentZhihuAnswer = null;

// DOM 元素
let zhihuModal = null;
let zhihuModalClose = null;
let zhihuModalOverlay = null;
let zhihuModalTitle = null;
let zhihuModalAuthor = null;
let zhihuModalAuthorName = null;
let zhihuModalAuthorTime = null;
let zhihuModalText = null;
let zhihuModalVoteup = null;
let zhihuModalComments = null;
let zhihuModalLink = null;

// 初始化知乎模态框
function initZhihuModal() {
    // 获取 DOM 元素
    zhihuModal = document.getElementById('zhihuModal');
    if (!zhihuModal) return;

    zhihuModalClose = document.getElementById('zhihuModalClose');
    zhihuModalOverlay = zhihuModal.querySelector('.modal-overlay');
    zhihuModalTitle = document.getElementById('zhihuModalTitle');
    zhihuModalAuthor = document.getElementById('zhihuModalAuthor');
    zhihuModalAuthorName = document.getElementById('zhihuModalAuthorName');
    zhihuModalAuthorTime = document.getElementById('zhihuModalAuthorTime');
    zhihuModalText = document.getElementById('zhihuModalText');
    zhihuModalVoteup = document.getElementById('zhihuModalVoteup');
    zhihuModalComments = document.getElementById('zhihuModalComments');
    zhihuModalLink = document.getElementById('zhihuModalLink');

    setupZhihuModalEvents();
}

// 设置模态框事件
function setupZhihuModalEvents() {
    // 关闭按钮
    if (zhihuModalClose) {
        zhihuModalClose.addEventListener('click', (e) => {
            e.stopPropagation();
            closeZhihuModal();
        });
    }

    // 点击遮罩关闭
    if (zhihuModalOverlay) {
        zhihuModalOverlay.addEventListener('click', () => {
            closeZhihuModal();
        });
    }

    // ESC 键关闭
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && zhihuModal && zhihuModal.style.display !== 'none') {
            closeZhihuModal();
        }
    });
}

// 打开知乎回答详情模态框
function openZhihuModal(answer) {
    if (!zhihuModal) return;

    currentZhihuAnswer = answer;

    // 设置标题（使用问题ID或默认标题）
    if (zhihuModalTitle) {
        zhihuModalTitle.textContent = '知乎回答';
    }

    // 设置作者信息
    if (zhihuModalAuthor) {
        if (answer.user_avatar) {
            zhihuModalAuthor.src = answer.user_avatar;
            zhihuModalAuthor.onerror = () => zhihuModalAuthor.style.display = 'none';
        } else {
            zhihuModalAuthor.style.display = 'none';
        }
    }

    if (zhihuModalAuthorName) {
        zhihuModalAuthorName.textContent = answer.user_nickname || '匿名用户';
    }

    if (zhihuModalAuthorTime) {
        if (answer.created_time) {
            const date = new Date(answer.created_time * 1000);
            zhihuModalAuthorTime.textContent = date.toLocaleDateString('zh-CN');
        } else {
            zhihuModalAuthorTime.textContent = '';
        }
    }

    // 设置回答文本
    if (zhihuModalText) {
        zhihuModalText.textContent = answer.content_text || answer.desc || '暂无内容';
    }

    // 设置互动数据
    if (zhihuModalVoteup) {
        zhihuModalVoteup.textContent = formatZhihuModalCount(answer.voteup_count);
    }
    if (zhihuModalComments) {
        zhihuModalComments.textContent = formatZhihuModalCount(answer.comment_count);
    }

    // 设置原链接
    if (zhihuModalLink) {
        if (answer.content_url) {
            zhihuModalLink.href = answer.content_url;
            zhihuModalLink.style.display = 'inline-flex';
        } else {
            zhihuModalLink.style.display = 'none';
        }
    }

    // 显示模态框
    zhihuModal.style.display = 'flex';
    document.body.style.overflow = 'hidden';
}

// 关闭模态框
function closeZhihuModal() {
    if (zhihuModal) {
        zhihuModal.style.display = 'none';
        document.body.style.overflow = '';
    }
    currentZhihuAnswer = null;
}

// 格式化数量
function formatZhihuModalCount(count) {
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
window.zhihuModal = {
    init: initZhihuModal,
    open: openZhihuModal,
    close: closeZhihuModal
};
