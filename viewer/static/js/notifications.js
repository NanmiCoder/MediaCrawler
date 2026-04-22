/**
 * 实时数据通知模块 - 叶子式弹窗
 * 从右侧滑入，非阻塞式通知
 */

(function() {
    'use strict';

    // 通知容器
    let notificationContainer = null;

    // 平台配置
    const PLATFORM_CONFIG = {
        'xhs': { name: '小红书', icon: '📕', color: '#FF2E4D', gradient: 'linear-gradient(135deg, #FF2E4D 0%, #FF6B8A 100%)' },
        'dy': { name: '抖音', icon: '🎵', color: '#00F5D4', gradient: 'linear-gradient(135deg, #00F5D4 0%, #00D9FF 100%)' },
        'bili': { name: 'B站', icon: '📺', color: '#FB7299', gradient: 'linear-gradient(135deg, #FB7299 0%, #00A1D6 100%)' },
        'zhihu': { name: '知乎', icon: '◈', color: '#0084FF', gradient: 'linear-gradient(135deg, #0084FF 0%, #00C6FF 100%)' }
    };

    // 通知去重 - 基于 content hash 和时间窗口
    const NOTIFICATION_DEDUP = {
        recentNotifications: new Map(),  // hash -> timestamp
        dedupWindowMs: 5000,             // 5 秒去重窗口
        cleanupIntervalMs: 30000         // 30 秒清理一次
    };

    // 初始化通知容器
    function init() {
        if (notificationContainer) return;

        notificationContainer = document.createElement('div');
        notificationContainer.id = 'data-notification-container';
        notificationContainer.style.cssText = `
            position: fixed;
            top: 80px;
            right: 20px;
            z-index: 3000;
            display: flex;
            flex-direction: column;
            gap: 12px;
            pointer-events: none;
            max-height: calc(100vh - 100px);
            overflow: hidden;
        `;
        document.body.appendChild(notificationContainer);
    }

    /**
     * 生成通知去重哈希
     * @param {Object} data - 通知数据
     * @returns {string} 哈希字符串
     */
    function generateNotificationHash(data) {
        // 使用 platform + titles + count 作为去重键
        const titles = data.titles ? data.titles.slice(0, 3).join(',') : '';
        const count = data.count || 0;
        return `${data.platform}-${titles}-${count}`;
    }

    /**
     * 检查是否为重复通知
     * @param {string} hash - 通知哈希
     * @returns {boolean} true 表示是重复通知，应跳过
     */
    function isDuplicateNotification(hash) {
        const now = Date.now();
        const lastShown = NOTIFICATION_DEDUP.recentNotifications.get(hash);

        if (lastShown && (now - lastShown < NOTIFICATION_DEDUP.dedupWindowMs)) {
            return true;
        }

        // 记录本次通知时间
        NOTIFICATION_DEDUP.recentNotifications.set(hash, now);

        // 定期清理过期条目（每 30 秒）
        if (NOTIFICATION_DEDUP.recentNotifications.size > 50) {
            for (const [key, timestamp] of NOTIFICATION_DEDUP.recentNotifications) {
                if (now - timestamp > NOTIFICATION_DEDUP.cleanupIntervalMs) {
                    NOTIFICATION_DEDUP.recentNotifications.delete(key);
                }
            }
        }

        return false;
    }

    /**
     * 显示数据更新通知 - 叶子式弹窗
     * @param {Object} data - 通知数据
     * @param {string} data.platform - 平台标识 (xhs, dy, bili, zhihu)
     * @param {number} data.count - 新增数据数量
     * @param {string} data.keyword - 搜索关键词（可选）
     * @param {string} data.message - 自定义消息（可选）
     */
    function showDataNotification(data) {
        if (!notificationContainer) init();

        // 去重检查
        const hash = generateNotificationHash(data);
        if (isDuplicateNotification(hash)) {
            console.log('[通知] 去重，跳过:', hash);
            return;
        }

        const config = PLATFORM_CONFIG[data.platform] || PLATFORM_CONFIG['xhs'];
        const notification = document.createElement('div');
        notification.className = 'data-notification-leaf';

        // 构建通知内容
        const title = data.message || `📥 ${config.name} 新数据`;
        const detail = data.keyword
            ? `关键词: ${data.keyword}`
            : (data.count ? `新增 ${data.count} 条数据` : '数据已更新');

        notification.innerHTML = `
            <div class="notification-leaf-header" style="background: ${config.gradient}">
                <span class="notification-leaf-icon">${config.icon}</span>
                <span class="notification-leaf-title">${title}</span>
            </div>
            <div class="notification-leaf-body">
                <span class="notification-leaf-detail">${detail}</span>
                <span class="notification-leaf-time">${formatTime(new Date())}</span>
            </div>
            <div class="notification-leaf-progress" style="background: ${config.color}"></div>
        `;

        // 添加样式
        notification.style.cssText = `
            width: 320px;
            background: rgba(18, 18, 26, 0.95);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 16px;
            overflow: hidden;
            backdrop-filter: blur(12px);
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4), 0 0 20px ${config.color}22;
            transform: translateX(120%);
            transition: transform 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
            pointer-events: auto;
            cursor: pointer;
        `;

        // 添加内部元素样式
        const style = document.createElement('style');
        style.textContent = `
            .data-notification-leaf { }
            .notification-leaf-header {
                display: flex;
                align-items: center;
                gap: 10px;
                padding: 14px 16px;
            }
            .notification-leaf-icon {
                font-size: 20px;
            }
            .notification-leaf-title {
                font-size: 15px;
                font-weight: 600;
                color: white;
                text-shadow: 0 1px 2px rgba(0,0,0,0.3);
            }
            .notification-leaf-body {
                display: flex;
                align-items: center;
                justify-content: space-between;
                padding: 12px 16px;
                background: rgba(0, 0, 0, 0.2);
            }
            .notification-leaf-detail {
                font-size: 13px;
                color: #c8c8d0;
            }
            .notification-leaf-time {
                font-size: 11px;
                color: #6e6e7a;
                font-family: 'JetBrains Mono', monospace;
            }
            .notification-leaf-progress {
                height: 3px;
                animation: notification-progress 5s linear forwards;
            }
            @keyframes notification-progress {
                from { width: 100%; }
                to { width: 0%; }
            }
        `;
        if (!document.querySelector('#notification-leaf-styles')) {
            style.id = 'notification-leaf-styles';
            document.head.appendChild(style);
        }

        // 添加到容器
        notificationContainer.appendChild(notification);

        // 触发滑入动画
        requestAnimationFrame(() => {
            notification.style.transform = 'translateX(0)';
        });

        // 点击关闭
        notification.addEventListener('click', () => {
            closeNotification(notification);
        });

        // 自动关闭
        const autoCloseTimeout = setTimeout(() => {
            closeNotification(notification);
        }, 5000);

        // 鼠标悬停暂停
        notification.addEventListener('mouseenter', () => {
            notification.querySelector('.notification-leaf-progress').style.animationPlayState = 'paused';
            clearTimeout(autoCloseTimeout);
        });

        notification.addEventListener('mouseleave', () => {
            notification.querySelector('.notification-leaf-progress').style.animationPlayState = 'running';
            setTimeout(() => {
                closeNotification(notification);
            }, 2000);
        });

        console.log(`[通知] ${config.name}: ${detail}`);
    }

    /**
     * 关闭通知 - 叶子式滑出
     */
    function closeNotification(notification) {
        if (!notification || notification.style.transform === 'translateX(120%)') return;

        notification.style.transform = 'translateX(120%)';
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 400);
    }

    /**
     * 格式化时间
     */
    function formatTime(date) {
        return date.toLocaleTimeString('zh-CN', {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
    }

    /**
     * 处理WebSocket数据更新
     */
    function handleDataUpdate(data) {
        const platform = data.platform || 'xhs';
        const timestamp = data.timestamp ? new Date(data.timestamp) : new Date();

        showDataNotification({
            platform: platform,
            count: data.new_count || 0,
            keyword: data.keyword || null,
            message: null,
            timestamp: timestamp
        });
    }

    /**
     * 处理订阅更新
     */
    function handleSubscriptionUpdate(data) {
        showDataNotification({
            platform: data.platform || 'xhs',
            count: data.new_count || 0,
            keyword: data.keyword || null,
            message: `订阅完成: ${data.keyword}`,
            timestamp: new Date(data.timestamp)
        });
    }

    // 暴露API
    window.DataNotification = {
        init,
        show: showDataNotification,
        handleDataUpdate,
        handleSubscriptionUpdate
    };

    // 自动初始化
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    console.log('[通知模块] 实时数据通知模块已加载');

})();
