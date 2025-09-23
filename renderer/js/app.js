/**
 * メインアプリケーション制御
 * Electron統合とChainlit連携
 */

const normalizeChainlitUrl = (url) => {
    if (!url) return '';
    const trimmed = String(url).trim();
    if (!trimmed) return '';
    try {
        const parsed = new URL(trimmed);
        return parsed.origin;
    } catch (error) {
        try {
            const withProtocol = /^https?:\/\//i.test(trimmed) ? trimmed : `http://${trimmed.replace(/^\/+/, '')}`;
            const parsed = new URL(withProtocol);
            return parsed.origin;
        } catch (innerError) {
            const fallback = /^https?:\/\//i.test(trimmed) ? trimmed : `http://${trimmed.replace(/^\/+/, '')}`;
            return fallback.replace(/\/+$/, '');
        }
    }
};

class ChainlitElectronApp {
    constructor() {
        this.chainlitUrl = null;
        this.isInitialized = false;
        
        // UIエレメント
        this.loadingScreen = document.getElementById('loading-screen');
        this.mainApp = document.getElementById('main-app');
        this.chainlitFrame = document.getElementById('chainlit-frame');
        this.connectionStatus = document.getElementById('connection-status');
        this.systemStatus = document.getElementById('system-status');
        this.currentTime = document.getElementById('current-time');
        
        // 初期化
        this.init();
    }
    
    async init() {
        try {
            this.updateLoadingMessage('システムチェック中...');
            
            // Electronの可用性確認
            if (typeof window.electronAPI === 'undefined') {
                throw new Error('Electron APIが利用できません');
            }
            
            // システム情報取得
            this.updateLoadingMessage('システム情報を取得中...');
            const systemInfo = await window.electronAPI.getSystemInfo();
            console.log('System Info:', systemInfo);
            
            // Chainlit URLの取得とヘルスチェック
            this.updateLoadingMessage('Chainlitサーバーへの接続確認中...');
            this.chainlitUrl = await this.resolveChainlitUrl();
            console.log('🔗 Chainlit base URL resolved:', this.chainlitUrl);

            // サーバー起動待ち
            await this.waitForChainlitServer();
            
            // UI初期化
            this.updateLoadingMessage('UIを初期化中...');
            this.setupEventListeners();
            this.setupChainlitFrame();
            this.startStatusUpdates();
            
            // アプリケーション表示
            this.showMainApp();
            
            this.isInitialized = true;
            console.log('✅ Chainlit Electron App初期化完了');

            // API呼び出しの統一ラッパ（通知＋ログ導線）
            this.installApiCallWrapper();

        } catch (error) {
            console.error('❌ アプリケーション初期化エラー:', error);
            this.showError('アプリケーションの初期化に失敗しました: ' + error.message);
        }
    }
    
    async resolveChainlitUrl() {
        const rawUrl = await window.electronAPI.getChainlitUrl();
        console.log('ℹ️ Chainlit URL (raw):', rawUrl);
        const normalized = normalizeChainlitUrl(rawUrl);
        if (!normalized) {
            throw new Error('Chainlit URL が取得できませんでした');
        }
        console.log('ℹ️ Chainlit URL (normalized):', normalized);
        return normalized;
    }

    async waitForChainlitServer(maxRetries = 30, delay = 1000) {
        const okStatuses = new Set([200, 204, 301, 302, 307, 308, 401, 403, 404]);
        const baseUrl = normalizeChainlitUrl(this.chainlitUrl);

        if (!baseUrl) {
            throw new Error('Chainlit URL が未取得です');
        }

        for (let i = 0; i < maxRetries; i++) {
            if (window.electronAPI?.probeChainlit) {
                try {
                    const probe = await window.electronAPI.probeChainlit(baseUrl);
                    if (probe?.success) {
                        console.log('✅ Chainlit server reachable via IPC', probe.detail);
                        this.updateConnectionStatus('🟢 接続済み', 'システム正常稼働中');
                        return;
                    }
                    if (probe?.detail) {
                        console.debug('Chainlit IPC probe detail', probe.detail);
                    }
                } catch (probeError) {
                    console.debug('Chainlit IPC probe error', probeError);
                }
            }

            const targets = [`${baseUrl}/health`, `${baseUrl}/login`, `${baseUrl}/`, baseUrl];
            for (const target of targets) {
                try {
                    const response = await fetch(target, {
                        method: 'GET',
                        redirect: 'manual',
                        credentials: 'include'
                    });
                    if (okStatuses.has(response.status)) {
                        console.log('✅ Chainlit server responding', {
                            url: target,
                            status: response.status,
                            statusText: response.statusText
                        });
                        this.updateConnectionStatus('🟢 接続済み', 'システム正常稼働中');
                        return;
                    }
                    console.debug('Chainlit probe response', {
                        url: target,
                        status: response.status,
                        statusText: response.statusText
                    });
                } catch (error) {
                    console.debug('Chainlit probe error', { url: target, error });
                }
            }

            if (i % 5 === 0) {
                console.warn('Chainlit probing retry', { attempt: i + 1 });
            }

            this.updateLoadingMessage(`Chainlitサーバー起動待ち... (${i + 1}/${maxRetries})`);
            await new Promise(resolve => setTimeout(resolve, delay));
        }

        throw new Error('Chainlitサーバーへの接続がタイムアウトしました');
    }

    installApiCallWrapper() {
        if (!window.electronAPI || !window.electronAPI.callAPI) return;
        if (window.electronAPI._rawCallAPI) return; // 二重適用防止

        window.electronAPI._rawCallAPI = window.electronAPI.callAPI;
        window.electronAPI.callAPI = async (endpoint, method = 'GET', data = null, options = { silent: true }) => {
            try {
                const res = await window.electronAPI._rawCallAPI(endpoint, method, data);
                if (!res || !res.success) {
                    const message = (res && res.error) ? res.error : 'API呼び出しに失敗しました';
                    // エラートースト（ログを開くボタン付き）
                    window.NotificationManager?.error('APIエラー', message, {
                        actions: [
                            {
                                id: 'openLogs',
                                text: '📁 ログを開く',
                                class: 'btn-secondary'
                            }
                        ]
                    });
                } else if (!options || !options.silent) {
                    // 成功時の軽い通知（明示的要求時のみ）
                    window.NotificationManager?.success('成功', '処理が完了しました');
                }
                return res;
            } catch (e) {
                window.NotificationManager?.error('APIエラー', String(e), {
                    actions: [
                        { id: 'openLogs', text: '📁 ログを開く', class: 'btn-secondary' }
                    ]
                });
                return { success: false, error: String(e) };
            }
        };

        // 通知アクション: ログを開く
        document.addEventListener('notificationAction', (event) => {
            const { actionId } = event.detail || {};
            if (actionId === 'openLogs') {
                try { window.electronAPI.app.openLogFolder(); } catch {}
            }
        });
    }
    
    setupEventListeners() {
        // ウィンドウコントロール
        const minimizeBtn = document.getElementById('minimize-btn');
        const maximizeBtn = document.getElementById('maximize-btn');
        const closeBtn = document.getElementById('close-btn');
        
        minimizeBtn?.addEventListener('click', () => {
            window.electronAPI.app.minimize();
        });
        
        maximizeBtn?.addEventListener('click', () => {
            window.electronAPI.app.maximize();
        });
        
        closeBtn?.addEventListener('click', () => {
            if (confirm('アプリケーションを終了しますか？')) {
                window.electronAPI.app.close();
            }
        });
        
        // ウィンドウリサイズ処理
        window.addEventListener('resize', () => {
            this.handleWindowResize();
        });
        
        // エラーハンドリング
        window.addEventListener('error', (event) => {
            console.error('Global error:', event.error);
            this.showNotification('エラー', event.error.message, 'error');
        });
        
        // 未処理のPromise拒否
        window.addEventListener('unhandledrejection', (event) => {
            console.error('Unhandled promise rejection:', event.reason);
            this.showNotification('エラー', 'システムエラーが発生しました', 'error');
        });
    }
    
    setupChainlitFrame() {
        if (!this.chainlitFrame || !this.chainlitUrl) return;
        
        // Chainlit URLを設定
        this.chainlitFrame.src = `${this.chainlitUrl}/`;
        
        // フレーム読み込み完了処理
        this.chainlitFrame.onload = () => {
            console.log('✅ Chainlitフレーム読み込み完了');
            this.updateConnectionStatus('🟢 接続済み', 'Chainlit正常稼働中');
        };
        
        // フレームエラー処理
        this.chainlitFrame.onerror = (error) => {
            console.error('❌ Chainlitフレーム読み込みエラー:', error);
            this.updateConnectionStatus('🔴 エラー', 'Chainlit接続エラー');
        };
    }
    
    startStatusUpdates() {
        // 現在時刻の更新
        const updateTime = () => {
            if (this.currentTime) {
                this.currentTime.textContent = new Date().toLocaleString('ja-JP');
            }
        };
        
        updateTime();
        setInterval(updateTime, 1000);
        
        // システム状態の定期チェック
        const checkSystemStatus = async () => {
            try {
                const healthStatus = await window.electronAPI.system.health();
                if (healthStatus && healthStatus.status === 'healthy') {
                    this.updateConnectionStatus('🟢 接続済み', 'システム正常稼働中');
                } else {
                    this.updateConnectionStatus('🟡 警告', 'システム状態を確認してください');
                }
            } catch (error) {
                this.updateConnectionStatus('🔴 エラー', 'システム接続エラー');
            }
        };
        
        // 30秒間隔でヘルスチェック
        setInterval(checkSystemStatus, 30000);
    }
    
    showMainApp() {
        if (this.loadingScreen) {
            this.loadingScreen.style.display = 'none';
        }
        if (this.mainApp) {
            this.mainApp.classList.remove('hidden');
        }
    }
    
    updateLoadingMessage(message) {
        const loadingMessage = document.getElementById('loading-message');
        if (loadingMessage) {
            loadingMessage.textContent = message;
        }
        console.log('🔄', message);
    }
    
    updateConnectionStatus(status, message) {
        if (this.connectionStatus) {
            this.connectionStatus.textContent = status;
        }
        if (this.systemStatus) {
            this.systemStatus.textContent = message;
        }
    }
    
    showError(message) {
        const errorHtml = `
            <div style="text-align: center; padding: 2rem; color: #dc3545;">
                <h3>⚠️ エラーが発生しました</h3>
                <p>${message}</p>
                <button onclick="location.reload()" class="btn btn-primary" style="margin-top: 1rem;">
                    再試行
                </button>
            </div>
        `;
        
        if (this.loadingScreen) {
            this.loadingScreen.innerHTML = errorHtml;
        } else {
            document.body.innerHTML = errorHtml;
        }
    }
    
    showNotification(title, message, type = 'info') {
        // 通知システムを使用（notifications.js）
        if (window.NotificationManager) {
            window.NotificationManager.show(title, message, type);
        } else {
            console.log(`${type.toUpperCase()}: ${title} - ${message}`);
        }
    }
    
    handleWindowResize() {
        // ウィンドウリサイズ時の処理
        const { innerWidth, innerHeight } = window;
        
        // モバイル表示モードの切り替え
        const isMobile = innerWidth < 768;
        document.body.classList.toggle('mobile-mode', isMobile);
        
        // タブ表示の調整
        if (window.TabManager) {
            window.TabManager.handleResize(innerWidth, innerHeight);
        }
    }
    
    // パブリックメソッド
    getChainlitUrl() {
        return this.chainlitUrl;
    }
    
    isAppReady() {
        return this.isInitialized;
    }
    
    async refreshChainlitFrame() {
        if (this.chainlitFrame && this.chainlitUrl) {
            this.chainlitFrame.src = `${this.chainlitUrl}/`;
            this.updateConnectionStatus('🔄 再接続中...', 'Chainlitを再読み込み中');
        }
    }
}

// アプリケーション初期化
let app;

document.addEventListener('DOMContentLoaded', () => {
    console.log('🚀 Chainlit Electron App starting...');
    app = new ChainlitElectronApp();
});

// グローバルアクセス用
window.ChainlitApp = app;
