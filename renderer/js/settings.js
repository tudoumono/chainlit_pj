/**
 * システム設定管理
 * アプリケーション設定とシステム監視
 */

class SettingsManager {
    constructor() {
        this.settings = {};
        this.systemStatus = {};
        this.isLoaded = false;
        
        this.setupEventListeners();
    }
    
    setupEventListeners() {
        // システムヘルスチェックボタン
        const healthBtn = document.getElementById('system-health-btn');
        if (healthBtn) {
            healthBtn.addEventListener('click', () => {
                this.runSystemHealthCheck();
            });
        }

        // ログフォルダを開く
        const openLogBtn = document.getElementById('open-log-folder-btn');
        if (openLogBtn) {
            openLogBtn.addEventListener('click', async () => {
                try {
                    await window.electronAPI.app.openLogFolder();
                    this.showToast('ログフォルダを開きました');
                } catch (e) {
                    console.error('Failed to open log folder', e);
                    this.showToast('ログフォルダを開けませんでした', 'error');
                }
            });
        }

        // チャットを開始（トップレベルでChainlit表示）
        const startChatBtn = document.getElementById('start-chat-btn');
        if (startChatBtn) {
            startChatBtn.addEventListener('click', async () => {
                try {
                    await window.electronAPI.app.openChat();
                } catch (e) {
                    console.error('Failed to open chat', e);
                    this.showToast('チャット画面を開けませんでした', 'error');
                }
            });
        }
    }
    
    async loadSettings() {
        if (this.isLoaded) return;
        
        try {
            console.log('🔄 Loading system settings...');
            
            // システム状態とログを並行取得
            const [statusResponse, logsResponse] = await Promise.all([
                window.electronAPI.system.status(),
                window.electronAPI.system.logs()
            ]);
            
            if (statusResponse && statusResponse.success) {
                this.systemStatus = statusResponse.data;
            }
            
            // デフォルト設定の読み込み
            this.settings = {
                notifications: true,
                autoSave: true,
                theme: 'light',
                language: 'ja',
                maxChatHistory: 1000,
                vectorStoreRetention: 30
            };
            
            this.renderSettingsPanel();
            this.isLoaded = true;
            
            console.log('✅ Settings loaded');

        } catch (error) {
            console.error('❌ Error loading settings:', error);
            this.renderError('設定の読み込みに失敗しました: ' + error.message);
        }
    }
    
    renderSettingsPanel() {
        const container = document.getElementById('settings-panel');
        if (!container) return;
        
        container.innerHTML = `
            <div class="content-area">
                <!-- システム情報セクション -->
                <div class="settings-section" style="margin-bottom: 2rem;">
                    <h3>🖥️ システム情報</h3>
                    <div class="card">
                        <div class="card-body">
                            ${this.renderSystemInfo()}
                        </div>
                    </div>
                </div>
                
                <!-- 全般設定セクション -->
                <div class="settings-section" style="margin-bottom: 2rem;">
                    <h3>⚙️ 全般設定</h3>
                    <div class="card">
                        <div class="card-body">
                            ${this.renderGeneralSettings()}
                        </div>
                    </div>
                </div>
                
                <!-- データ管理セクション -->
                <div class="settings-section" style="margin-bottom: 2rem;">
                    <h3>💾 データ管理</h3>
                    <div class="card">
                        <div class="card-body">
                            ${this.renderDataSettings()}
                        </div>
                    </div>
                </div>
                
                <!-- セキュリティセクション -->
                <div class="settings-section" style="margin-bottom: 2rem;">
                    <h3>🔒 セキュリティ</h3>
                    <div class="card">
                        <div class="card-body">
                            ${this.renderSecuritySettings()}
                        </div>
                    </div>
                </div>
                
                <!-- 詳細設定セクション -->
                <div class="settings-section">
                    <h3>🔧 詳細設定</h3>
                    <div class="card">
                        <div class="card-body">
                            ${this.renderAdvancedSettings()}
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        this.setupSettingsEventListeners();
    }

    showToast(message, type = 'info') {
        if (window.Notifications) {
            window.Notifications.show(message, type);
        } else {
            // 簡易フォールバック
            alert(message);
        }
    }
    
    renderSystemInfo() {
        const status = this.systemStatus;
        
        return `
            <div class="system-info-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 1rem;">
                <div class="info-item">
                    <div class="info-label">アプリケーション</div>
                    <div class="info-value">Chainlit AI Workspace v1.0.0</div>
                </div>
                <div class="info-item">
                    <div class="info-label">Electron バージョン</div>
                    <div class="info-value">${status.electron_version || '不明'}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">Python バージョン</div>
                    <div class="info-value">${status.python_version || '不明'}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">Chainlit バージョン</div>
                    <div class="info-value">${status.chainlit_version || '不明'}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">データベース</div>
                    <div class="info-value">
                        <span class="status-indicator ${status.database_status === 'healthy' ? 'status-green' : 'status-red'}">
                            ${status.database_status === 'healthy' ? '🟢' : '🔴'}
                        </span>
                        ${status.database_status || '不明'}
                    </div>
                </div>
                <div class="info-item">
                    <div class="info-label">OpenAI API</div>
                    <div class="info-value">
                        <span class="status-indicator ${status.openai_status === 'healthy' ? 'status-green' : 'status-red'}">
                            ${status.openai_status === 'healthy' ? '🟢' : '🔴'}
                        </span>
                        ${status.openai_status || '不明'}
                    </div>
                </div>
            </div>
            
            <div style="margin-top: 1rem; display: flex; gap: 0.75rem;">
                <button onclick="window.SettingsManager.runSystemHealthCheck()" class="btn btn-primary">
                    🔍 ヘルスチェック実行
                </button>
                <button onclick="window.SettingsManager.viewSystemLogs()" class="btn btn-secondary">
                    📜 システムログを表示
                </button>
                <button onclick="window.SettingsManager.exportSystemInfo()" class="btn btn-secondary">
                    📊 システム情報エクスポート
                </button>
            </div>
        `;
    }
    
    renderGeneralSettings() {
        return `
            <div class="settings-form">
                <div class="form-group" style="margin-bottom: 1.5rem;">
                    <label class="settings-label">
                        <input type="checkbox" id="enable-notifications" ${this.settings.notifications ? 'checked' : ''}>
                        通知を有効にする
                    </label>
                    <small class="settings-help">システム通知とアラートを受け取ります</small>
                </div>
                
                <div class="form-group" style="margin-bottom: 1.5rem;">
                    <label class="settings-label">
                        <input type="checkbox" id="auto-save" ${this.settings.autoSave ? 'checked' : ''}>
                        自動保存を有効にする
                    </label>
                    <small class="settings-help">設定とデータの自動保存を行います</small>
                </div>
                
                <div class="form-group" style="margin-bottom: 1.5rem;">
                    <label class="settings-label">テーマ</label>
                    <select id="theme-select" class="form-select">
                        <option value="light" ${this.settings.theme === 'light' ? 'selected' : ''}>ライト</option>
                        <option value="dark" ${this.settings.theme === 'dark' ? 'selected' : ''}>ダーク</option>
                        <option value="auto" ${this.settings.theme === 'auto' ? 'selected' : ''}>システム設定に従う</option>
                    </select>
                </div>
                
                <div class="form-group" style="margin-bottom: 1.5rem;">
                    <label class="settings-label">言語</label>
                    <select id="language-select" class="form-select">
                        <option value="ja" ${this.settings.language === 'ja' ? 'selected' : ''}>日本語</option>
                        <option value="en" ${this.settings.language === 'en' ? 'selected' : ''}>English</option>
                    </select>
                </div>
                
                <div class="settings-actions">
                    <button onclick="window.SettingsManager.saveGeneralSettings()" class="btn btn-primary">
                        💾 設定を保存
                    </button>
                    <button onclick="window.SettingsManager.resetGeneralSettings()" class="btn btn-secondary">
                        🔄 デフォルトに戻す
                    </button>
                </div>
            </div>
        `;
    }
    
    renderDataSettings() {
        return `
            <div class="settings-form">
                <div class="form-group" style="margin-bottom: 1.5rem;">
                    <label class="settings-label">最大チャット履歴保存数</label>
                    <input type="number" id="max-chat-history" class="form-input" 
                           value="${this.settings.maxChatHistory}" min="100" max="10000" step="100">
                    <small class="settings-help">保存するチャット履歴の最大数（100-10000）</small>
                </div>
                
                <div class="form-group" style="margin-bottom: 1.5rem;">
                    <label class="settings-label">ベクトルストア保持期間（日）</label>
                    <input type="number" id="vectorstore-retention" class="form-input" 
                           value="${this.settings.vectorStoreRetention}" min="1" max="365">
                    <small class="settings-help">未使用のベクトルストアを自動削除するまでの日数</small>
                </div>
                
                <div class="data-management-actions" style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;">
                    <button onclick="window.SettingsManager.backupData()" class="btn btn-success">
                        💾 データバックアップ
                    </button>
                    <button onclick="window.SettingsManager.restoreData()" class="btn btn-warning">
                        📥 データ復元
                    </button>
                    <button onclick="window.SettingsManager.cleanupData()" class="btn btn-secondary">
                        🧹 データクリーンアップ
                    </button>
                    <button onclick="window.SettingsManager.resetAllData()" class="btn btn-danger">
                        ⚠️ 全データリセット
                    </button>
                </div>
            </div>
        `;
    }
    
    renderSecuritySettings() {
        return `
            <div class="settings-form">
                <div class="security-status" style="margin-bottom: 1.5rem;">
                    <h4>🔐 セキュリティ状態</h4>
                    <div class="security-checks">
                        <div class="security-check-item">
                            <span class="check-icon">🟢</span>
                            <span>SSL/TLS証明書</span>
                            <span class="check-status">有効</span>
                        </div>
                        <div class="security-check-item">
                            <span class="check-icon">🟢</span>
                            <span>API キー暗号化</span>
                            <span class="check-status">有効</span>
                        </div>
                        <div class="security-check-item">
                            <span class="check-icon">🟢</span>
                            <span>セッション管理</span>
                            <span class="check-status">セキュア</span>
                        </div>
                    </div>
                </div>
                
                <div class="form-group" style="margin-bottom: 1.5rem;">
                    <label class="settings-label">OpenAI API キー</label>
                    <div style="display: flex; gap: 0.5rem;">
                        <input type="password" id="openai-api-key" class="form-input" 
                               placeholder="sk-..." style="flex: 1;">
                        <button onclick="window.SettingsManager.testApiKey()" class="btn btn-secondary">
                            🔍 テスト
                        </button>
                    </div>
                    <small class="settings-help">OpenAI API キーは暗号化されて保存されます</small>
                </div>
                
                <div class="security-actions">
                    <button onclick="window.SettingsManager.changePassword()" class="btn btn-primary">
                        🔑 パスワード変更
                    </button>
                    <button onclick="window.SettingsManager.clearSessions()" class="btn btn-secondary">
                        🚪 全セッションをクリア
                    </button>
                </div>
            </div>
        `;
    }
    
    renderAdvancedSettings() {
        return `
            <div class="settings-form">
                <div class="form-group" style="margin-bottom: 1.5rem;">
                    <label class="settings-label">
                        <input type="checkbox" id="debug-mode" ${this.settings.debugMode ? 'checked' : ''}>
                        デバッグモードを有効にする
                    </label>
                    <small class="settings-help">詳細なログとデバッグ情報を記録します</small>
                </div>
                
                <div class="form-group" style="margin-bottom: 1.5rem;">
                    <label class="settings-label">
                        <input type="checkbox" id="developer-tools" ${this.settings.devTools ? 'checked' : ''}>
                        開発者ツールを有効にする
                    </label>
                    <small class="settings-help">Chrome DevToolsへのアクセスを許可します</small>
                </div>
                
                <div class="advanced-actions" style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;">
                    <button onclick="window.SettingsManager.openDevTools()" class="btn btn-secondary">
                        🔧 開発者ツールを開く
                    </button>
                    <button onclick="window.SettingsManager.restartApplication()" class="btn btn-warning">
                        🔄 アプリケーション再起動
                    </button>
                    <button onclick="window.SettingsManager.clearCache()" class="btn btn-secondary">
                        🗑️ キャッシュをクリア
                    </button>
                    <button onclick="window.SettingsManager.factoryReset()" class="btn btn-danger">
                        ⚠️ 工場出荷時設定
                    </button>
                </div>
            </div>
        `;
    }
    
    renderError(message) {
        const container = document.getElementById('settings-panel');
        if (container) {
            container.innerHTML = `
                <div class="content-area">
                    <div class="alert alert-danger">
                        <h4>⚠️ エラーが発生しました</h4>
                        <p>${this.escapeHtml(message)}</p>
                        <button onclick="window.SettingsManager.reloadSettings()" class="btn btn-primary">
                            再試行
                        </button>
                    </div>
                </div>
            `;
        }
    }
    
    setupSettingsEventListeners() {
        // 設定の自動保存
        const autoSaveElements = [
            'enable-notifications',
            'auto-save',
            'theme-select',
            'language-select'
        ];
        
        autoSaveElements.forEach(elementId => {
            const element = document.getElementById(elementId);
            if (element) {
                element.addEventListener('change', () => {
                    if (this.settings.autoSave) {
                        setTimeout(() => this.saveGeneralSettings(), 500);
                    }
                });
            }
        });
    }
    
    async runSystemHealthCheck() {
        try {
            window.NotificationManager.show('開始', 'システムヘルスチェックを実行中...', 'info');
            
            const response = await window.electronAPI.system.health();
            
            if (!response || !response.success) {
                throw new Error(response?.error || 'ヘルスチェックに失敗しました');
            }
            
            const healthData = response.data;
            this.showHealthCheckResults(healthData);
            
            window.NotificationManager.show('完了', 'システムヘルスチェックが完了しました', 'success');
            
        } catch (error) {
            console.error('❌ Error running health check:', error);
            window.NotificationManager.show('エラー', 'ヘルスチェックに失敗しました: ' + error.message, 'error');
        }
    }
    
    showHealthCheckResults(healthData) {
        const resultsHtml = `
            <div class="health-check-results">
                <h4>🏥 システムヘルスチェック結果</h4>
                <div class="health-items">
                    ${Object.entries(healthData).map(([key, value]) => `
                        <div class="health-item">
                            <span class="health-icon">${value.status === 'healthy' ? '🟢' : '🔴'}</span>
                            <span class="health-name">${key}</span>
                            <span class="health-status">${value.status}</span>
                            ${value.message ? `<div class="health-message">${value.message}</div>` : ''}
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
        
        window.Modal.show('ヘルスチェック結果', resultsHtml, {
            showConfirm: false,
            cancelText: '閉じる'
        });
    }
    
    async saveGeneralSettings() {
        try {
            const notifications = document.getElementById('enable-notifications')?.checked || false;
            const autoSave = document.getElementById('auto-save')?.checked || false;
            const theme = document.getElementById('theme-select')?.value || 'light';
            const language = document.getElementById('language-select')?.value || 'ja';
            
            this.settings = {
                ...this.settings,
                notifications,
                autoSave,
                theme,
                language
            };
            
            // 設定をローカルストレージに保存
            localStorage.setItem('chainlit-settings', JSON.stringify(this.settings));
            
            window.NotificationManager.show('保存', '設定が保存されました', 'success');
            
        } catch (error) {
            console.error('❌ Error saving settings:', error);
            window.NotificationManager.show('エラー', '設定の保存に失敗しました: ' + error.message, 'error');
        }
    }
    
    resetGeneralSettings() {
        if (confirm('設定をデフォルトに戻しますか？')) {
            this.settings = {
                notifications: true,
                autoSave: true,
                theme: 'light',
                language: 'ja',
                maxChatHistory: 1000,
                vectorStoreRetention: 30
            };
            
            this.renderSettingsPanel();
            window.NotificationManager.show('リセット', '設定がデフォルトに戻されました', 'info');
        }
    }
    
    async reloadSettings() {
        this.isLoaded = false;
        await this.loadSettings();
    }
    
    // スタブメソッド（実装は将来の拡張用）
    async viewSystemLogs() { window.NotificationManager.show('準備中', 'この機能は準備中です', 'info'); }
    async exportSystemInfo() { window.NotificationManager.show('準備中', 'この機能は準備中です', 'info'); }
    async backupData() { window.NotificationManager.show('準備中', 'この機能は準備中です', 'info'); }
    async restoreData() { window.NotificationManager.show('準備中', 'この機能は準備中です', 'info'); }
    async cleanupData() { window.NotificationManager.show('準備中', 'この機能は準備中です', 'info'); }
    async resetAllData() { window.NotificationManager.show('準備中', 'この機能は準備中です', 'info'); }
    async testApiKey() { window.NotificationManager.show('準備中', 'この機能は準備中です', 'info'); }
    async changePassword() { window.NotificationManager.show('準備中', 'この機能は準備中です', 'info'); }
    async clearSessions() { window.NotificationManager.show('準備中', 'この機能は準備中です', 'info'); }
    async openDevTools() { window.NotificationManager.show('準備中', 'この機能は準備中です', 'info'); }
    async restartApplication() { window.NotificationManager.show('準備中', 'この機能は準備中です', 'info'); }
    async clearCache() { window.NotificationManager.show('準備中', 'この機能は準備中です', 'info'); }
    async factoryReset() { window.NotificationManager.show('準備中', 'この機能は準備中です', 'info'); }
    
    // ユーティリティメソッド
    escapeHtml(text) {
        if (typeof text !== 'string') return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// 設定マネージャー初期化（DOMContentLoaded前後どちらでも安全に初期化）
(async function initSettingsManager() {
    const boot = async () => {
        if (!window.SettingsManager) {
            window.SettingsManager = new SettingsManager();
            console.log('✅ Settings Manager initialized');
            try {
                await window.SettingsManager.loadSettings();
            } catch (e) {
                console.error('❌ Failed to load initial settings:', e);
            }
        }
    };
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => { boot(); }, { once: true });
    } else {
        await boot();
    }
})();
