/**
 * 通知システム管理
 * トースト通知とデスクトップ通知の統合管理
 */

class NotificationManager {
    constructor() {
        this.container = document.getElementById('toast-container');
        this.notifications = new Map();
        this.nextId = 1;
        this.maxNotifications = 5;
        this.defaultDuration = 5000; // 5秒
        
        this.setupEventListeners();
        console.log('✅ Notification Manager initialized');
    }
    
    setupEventListeners() {
        // 通知許可を確認
        this.checkNotificationPermission();
    }
    
    async checkNotificationPermission() {
        if ('Notification' in window && Notification.permission === 'default') {
            try {
                const permission = await Notification.requestPermission();
                console.log('Notification permission:', permission);
            } catch (error) {
                console.log('Notification permission request failed:', error);
            }
        }
    }
    
    show(title, message, type = 'info', options = {}) {
        const notificationOptions = {
            duration: this.defaultDuration,
            showDesktop: false,
            persistent: false,
            actions: [],
            ...options
        };
        
        // トースト通知を表示
        const toastId = this.showToast(title, message, type, notificationOptions);
        
        // デスクトップ通知を表示（必要に応じて）
        if (notificationOptions.showDesktop) {
            this.showDesktopNotification(title, message, type, notificationOptions);
        }
        
        return toastId;
    }
    
    showToast(title, message, type, options) {
        if (!this.container) {
            console.warn('Toast container not found');
            return null;
        }
        
        const toastId = this.nextId++;
        
        // 最大表示数チェック
        if (this.notifications.size >= this.maxNotifications) {
            this.removeOldestNotification();
        }
        
        // トースト要素を作成
        const toast = this.createToastElement(toastId, title, message, type, options);
        
        // コンテナに追加
        this.container.appendChild(toast);
        this.notifications.set(toastId, {
            element: toast,
            type,
            timestamp: Date.now(),
            duration: options.duration
        });
        
        // アニメーション
        setTimeout(() => {
            toast.style.transform = 'translateX(0)';
            toast.style.opacity = '1';
        }, 10);
        
        // 自動削除（永続的でない場合）
        if (!options.persistent && options.duration > 0) {
            setTimeout(() => {
                this.hideToast(toastId);
            }, options.duration);
        }
        
        console.log(`📢 Toast notification shown: ${title} (${type})`);
        return toastId;
    }
    
    createToastElement(id, title, message, type, options) {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.setAttribute('data-toast-id', id);
        
        const icon = this.getTypeIcon(type);
        
        let actionsHtml = '';
        if (options.actions && options.actions.length > 0) {
            actionsHtml = `
                <div class="toast-actions" style="margin-top: 0.5rem;">
                    ${options.actions.map(action => `
                        <button onclick="window.NotificationManager.handleAction('${id}', '${action.id}')" 
                                class="btn btn-sm ${action.class || 'btn-secondary'}" 
                                style="margin-right: 0.25rem;">
                            ${action.text}
                        </button>
                    `).join('')}
                </div>
            `;
        }
        
        toast.innerHTML = `
            <div class="toast-header">
                <div class="toast-title">
                    ${icon} ${this.escapeHtml(title)}
                </div>
                <button class="toast-close" onclick="window.NotificationManager.hideToast('${id}')" 
                        aria-label="閉じる">×</button>
            </div>
            <div class="toast-body">
                ${this.escapeHtml(message).replace(/\n/g, '<br>')}
                ${actionsHtml}
            </div>
            ${options.duration > 0 && !options.persistent ? `
                <div class="toast-progress">
                    <div class="toast-progress-bar" style="animation: toastProgress ${options.duration}ms linear;"></div>
                </div>
            ` : ''}
        `;
        
        return toast;
    }
    
    showDesktopNotification(title, message, type, options) {
        if (!('Notification' in window) || Notification.permission !== 'granted') {
            return;
        }
        
        try {
            const notification = new Notification(title, {
                body: message,
                icon: this.getTypeIcon(type, true), // デスクトップ用アイコン
                badge: '/assets/badge-icon.png',
                tag: `chainlit-${type}-${Date.now()}`,
                requireInteraction: options.persistent,
                ...options.desktopOptions
            });
            
            // クリック時の処理
            notification.onclick = () => {
                window.focus();
                notification.close();
                
                if (options.onClick) {
                    options.onClick();
                }
            };
            
            // 自動閉じる
            if (!options.persistent && options.duration > 0) {
                setTimeout(() => {
                    notification.close();
                }, options.duration);
            }
            
            console.log(`🖥️ Desktop notification shown: ${title}`);
            
        } catch (error) {
            console.error('Desktop notification error:', error);
        }
    }
    
    hideToast(toastId) {
        const notification = this.notifications.get(toastId);
        if (!notification) return;
        
        const { element } = notification;
        
        // フェードアウトアニメーション
        element.style.transform = 'translateX(100%)';
        element.style.opacity = '0';
        
        setTimeout(() => {
            if (element.parentNode) {
                element.parentNode.removeChild(element);
            }
            this.notifications.delete(toastId);
        }, 300);
        
        console.log(`📢 Toast notification hidden: ${toastId}`);
    }
    
    hideAll() {
        Array.from(this.notifications.keys()).forEach(id => {
            this.hideToast(id);
        });
    }
    
    removeOldestNotification() {
        if (this.notifications.size === 0) return;
        
        let oldestId = null;
        let oldestTime = Date.now();
        
        this.notifications.forEach((notification, id) => {
            if (notification.timestamp < oldestTime) {
                oldestTime = notification.timestamp;
                oldestId = id;
            }
        });
        
        if (oldestId) {
            this.hideToast(oldestId);
        }
    }
    
    handleAction(toastId, actionId) {
        const notification = this.notifications.get(toastId);
        if (!notification) return;
        
        // アクション処理のイベントを発火
        const actionEvent = new CustomEvent('notificationAction', {
            detail: { toastId, actionId, notification }
        });
        document.dispatchEvent(actionEvent);
        
        // 通知を閉じる
        this.hideToast(toastId);
    }
    
    getTypeIcon(type, isDesktop = false) {
        const iconMap = {
            success: '✅',
            error: '❌',
            warning: '⚠️',
            info: 'ℹ️'
        };
        
        if (isDesktop) {
            // デスクトップ通知用のアイコンパス
            const desktopIconMap = {
                success: '/assets/icons/success.png',
                error: '/assets/icons/error.png',
                warning: '/assets/icons/warning.png',
                info: '/assets/icons/info.png'
            };
            return desktopIconMap[type] || desktopIconMap.info;
        }
        
        return iconMap[type] || iconMap.info;
    }
    
    // 便利メソッド
    success(title, message, options = {}) {
        return this.show(title, message, 'success', options);
    }
    
    error(title, message, options = {}) {
        return this.show(title, message, 'error', {
            ...options,
            duration: options.duration || 8000, // エラーは長めに表示
            showDesktop: options.showDesktop !== false // デフォルトでデスクトップ通知も表示
        });
    }
    
    warning(title, message, options = {}) {
        return this.show(title, message, 'warning', options);
    }
    
    info(title, message, options = {}) {
        return this.show(title, message, 'info', options);
    }
    
    // アクション付き通知
    confirm(title, message, confirmAction, cancelAction) {
        return this.show(title, message, 'warning', {
            persistent: true,
            actions: [
                {
                    id: 'confirm',
                    text: '確認',
                    class: 'btn-primary',
                    handler: confirmAction
                },
                {
                    id: 'cancel',
                    text: 'キャンセル',
                    class: 'btn-secondary',
                    handler: cancelAction
                }
            ]
        });
    }
    
    // プログレス通知
    progress(title, message, currentProgress = 0) {
        const progressHtml = `
            <div style="margin-top: 0.5rem;">
                <div class="progress">
                    <div class="progress-bar" style="width: ${currentProgress}%"></div>
                </div>
                <small class="text-muted">${currentProgress}% 完了</small>
            </div>
        `;
        
        return this.show(title, message + progressHtml, 'info', {
            persistent: true,
            duration: 0
        });
    }
    
    updateProgress(toastId, progress, message = null) {
        const notification = this.notifications.get(toastId);
        if (!notification) return;
        
        const progressBar = notification.element.querySelector('.progress-bar');
        const progressText = notification.element.querySelector('.text-muted');
        
        if (progressBar) {
            progressBar.style.width = `${progress}%`;
        }
        
        if (progressText) {
            progressText.textContent = `${progress}% 完了`;
        }
        
        if (message) {
            const body = notification.element.querySelector('.toast-body');
            if (body) {
                const messageText = body.childNodes[0];
                if (messageText) {
                    messageText.textContent = message;
                }
            }
        }
        
        // 100%になったら自動で成功通知に変更
        if (progress >= 100) {
            setTimeout(() => {
                this.hideToast(toastId);
                this.success('完了', message || '処理が完了しました');
            }, 1000);
        }
    }
    
    // システム通知
    system(message, type = 'info') {
        return this.show('システム', message, type, {
            showDesktop: true,
            duration: 3000
        });
    }
    
    // 統計情報
    getStats() {
        return {
            total: this.notifications.size,
            byType: Array.from(this.notifications.values()).reduce((acc, notification) => {
                acc[notification.type] = (acc[notification.type] || 0) + 1;
                return acc;
            }, {})
        };
    }
    
    // ユーティリティメソッド
    escapeHtml(text) {
        if (typeof text !== 'string') return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    // 静的メソッド（グローバルアクセス用）
    static show(title, message, type, options) {
        return window.notificationManagerInstance?.show(title, message, type, options);
    }
    
    static success(title, message, options) {
        return window.notificationManagerInstance?.success(title, message, options);
    }
    
    static error(title, message, options) {
        return window.notificationManagerInstance?.error(title, message, options);
    }
    
    static warning(title, message, options) {
        return window.notificationManagerInstance?.warning(title, message, options);
    }
    
    static info(title, message, options) {
        return window.notificationManagerInstance?.info(title, message, options);
    }
    
    static hideAll() {
        return window.notificationManagerInstance?.hideAll();
    }
}

// CSS アニメーションを追加
const style = document.createElement('style');
style.textContent = `
@keyframes toastProgress {
    from { width: 100%; }
    to { width: 0%; }
}

.toast-progress {
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    height: 3px;
    background: rgba(0, 0, 0, 0.1);
    overflow: hidden;
}

.toast-progress-bar {
    height: 100%;
    background: currentColor;
    opacity: 0.3;
}

.toast-actions .btn {
    font-size: 0.75rem;
    padding: 0.25rem 0.5rem;
}
`;
document.head.appendChild(style);

// 通知マネージャー初期化
document.addEventListener('DOMContentLoaded', () => {
    window.notificationManagerInstance = new NotificationManager();
    window.NotificationManager = NotificationManager;
    
    // アクションハンドラーの設定
    document.addEventListener('notificationAction', (event) => {
        const { actionId, toastId } = event.detail;
        console.log(`Notification action triggered: ${actionId} for toast ${toastId}`);
        
        // カスタムアクション処理をここに追加
    });
    
    console.log('✅ Notification system initialized');
});