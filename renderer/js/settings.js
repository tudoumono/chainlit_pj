/**
 * システム設定管理
 * アプリケーション設定とシステム監視
 */

const normalizeChainlitUrlSafe = window.normalizeChainlitUrl || ((url) => {
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
});

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
            
            // デフォルト設定（通知/自動保存/言語は固定）
            this.settings = {
                theme: 'light'
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
        
        this.bindRenderedEvents();
        this.setupSettingsEventListeners();
    }

    bindRenderedEvents() {
        const bind = (selector, handler) => {
            if (!selector || typeof handler !== 'function') return;
            const elements = document.querySelectorAll(selector);
            elements.forEach((el) => {
                el.addEventListener('click', (event) => {
                    event.preventDefault();
                    handler.call(this, event);
                });
            });
        };

        bind('#btn-refresh-status', this.refreshSystemStatus);
        bind('#btn-run-health', this.runSystemHealthCheck);
        bind('#btn-view-logs', this.viewSystemLogs);
        bind('#btn-save-general', this.saveGeneralSettings);
        bind('#btn-reset-general', this.resetGeneralSettings);
        bind('#btn-cleanup-data', this.cleanupData);
        bind('#btn-reset-all', this.resetAllData);
        bind('#btn-test-api', this.testApiKey);
        bind('#btn-open-devtools', this.openDevTools);
        bind('#btn-restart-app', this.restartApplication);
        bind('#btn-view-logs-adv', this.viewSystemLogs);
        bind('#btn-export-info-adv', this.exportSystemInfo);
        bind('#btn-reload-settings', this.reloadSettings);
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
        const s = this.systemStatus || {};
        const dash = (v) => (v && String(v).trim() ? v : '—'); // 不要な心配を与えないダッシュ表記
        const icon = (state) => state === 'healthy' ? '🟢' : state === 'unhealthy' ? '🔴' : '⚪';
        const cls = (state) => state === 'healthy' ? 'status-green' : state === 'unhealthy' ? 'status-red' : 'status-gray';

        const rows = [];
        rows.push(`
            <div class="info-item">
                <div class="info-label">アプリケーション</div>
                <div class="info-value">Chainlit AI Workspace v${dash(s.app_version) || '1.0.0'}</div>
            </div>`);
        if (dash(s.electron_version) !== '—') rows.push(`
            <div class="info-item">
                <div class="info-label">Electron バージョン</div>
                <div class="info-value">${dash(s.electron_version)}</div>
            </div>`);
        if (dash(s.python_version) !== '—') rows.push(`
            <div class="info-item">
                <div class="info-label">Python バージョン</div>
                <div class="info-value">${dash(s.python_version)}</div>
            </div>`);
        if (dash(s.chainlit_version) !== '—') rows.push(`
            <div class="info-item">
                <div class="info-label">Chainlit バージョン</div>
                <div class="info-value">${dash(s.chainlit_version)}</div>
            </div>`);

        rows.push(`
            <div class="info-item">
                <div class="info-label">データベース</div>
                <div class="info-value">
                    <span class="status-indicator ${cls(s.database_status)}">${icon(s.database_status)}</span>
                    ${dash(s.database_status)}
                </div>
            </div>`);
        rows.push(`
            <div class="info-item">
                <div class="info-label">OpenAI API</div>
                <div class="info-value">
                    <span class="status-indicator ${cls(s.openai_status)}">${icon(s.openai_status)}</span>
                    ${s.openai_status === 'unknown' ? '未設定' : dash(s.openai_status)}
                </div>
            </div>`);

        return `
            <div class="system-info-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 1rem;">
                ${rows.join('\n')}
            </div>
            <div style="margin-top: 1rem; display: flex; gap: 0.75rem;">
                <button id="btn-refresh-status" class="btn btn-secondary">🔄 再取得</button>
                <button id="btn-run-health" class="btn btn-primary">🔍 ヘルスチェック実行</button>
                <button id="btn-view-logs" class="btn btn-secondary">📜 システムログを表示</button>
                <button id="btn-export-info-adv" class="btn btn-secondary">📊 システム情報エクスポート</button>
            </div>
        `;
    }
    
    renderGeneralSettings() {
        return `
            <div class="settings-form">
                
                
                <div class="form-group" style="margin-bottom: 1.5rem;">
                    <label class="settings-label">テーマ</label>
                    <select id="theme-select" class="form-select">
                        <option value="light" ${this.settings.theme === 'light' ? 'selected' : ''}>ライト</option>
                        <option value="dark" ${this.settings.theme === 'dark' ? 'selected' : ''}>ダーク</option>
                        <option value="auto" ${this.settings.theme === 'auto' ? 'selected' : ''}>システム設定に従う</option>
                    </select>
                    <small class="settings-help">表示テーマのみ変更できます。通知は常に有効、表示言語は日本語固定です。</small>
                </div>
                
                
                
                <div class="settings-actions">
                    <button id="btn-save-general" class="btn btn-primary">
                        💾 設定を保存
                    </button>
                    <button id="btn-reset-general" class="btn btn-secondary">
                        🔄 デフォルトに戻す
                    </button>
                </div>
            </div>
        `;
    }
    
    renderDataSettings() {
        return `
            <div class="settings-form">
                <div class="data-management-actions" style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;">
                    <button id="btn-cleanup-data" class="btn btn-secondary">
                        🧹 データクリーンアップ
                    </button>
                    <button id="btn-reset-all" class="btn btn-danger">
                        ⚠️ 全データリセット
                    </button>
                </div>
            </div>
        `;
    }
    
    renderSecuritySettings() {
        return `
            <div class="settings-form">
                <div class="form-group" style="margin-bottom: 1.5rem;">
                    <label class="settings-label">OpenAI API キー疎通テスト</label>
                    <div style="display: flex; gap: 0.5rem; align-items: center;">
                        <input type="password" id="openai-api-key" class="form-input" placeholder="sk-...（未入力なら現在のキーを使用）" style="flex: 1;">
                        <button id="btn-test-api" class="btn btn-secondary">🔍 テスト</button>
                    </div>
                    <small class="settings-help">テストは最小限のリクエストで行われ、OpenAI側のリソースに変更は加えません。</small>
                </div>
            </div>
        `;
    }
    
    renderAdvancedSettings() {
        return `
            <div class="settings-form">
                <div class="advanced-actions" style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;">
                    <button id="btn-open-devtools" class="btn btn-secondary">
                        🔧 開発者ツールを開く
                    </button>
                    <button id="btn-restart-app" class="btn btn-warning">
                        🔄 アプリケーション再起動
                    </button>
                    <button id="btn-view-logs-adv" class="btn btn-secondary">
                        📜 システムログを表示
                    </button>
                    <button id="btn-export-info-adv" class="btn btn-secondary">
                        📊 システム情報エクスポート
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
                        <button id="btn-reload-settings" class="btn btn-primary">
                            再試行
                        </button>
                    </div>
                </div>
            `;
        }

        const reloadBtn = document.getElementById('btn-reload-settings');
        if (reloadBtn) {
            reloadBtn.addEventListener('click', (event) => {
                event.preventDefault();
                this.reloadSettings();
            });
        }
    }
    
    setupSettingsEventListeners() {
        // 設定の自動保存
        // 自動保存は行わない（ユーザー操作で保存）。必要なイベントだけを設定
        const themeSelect = document.getElementById('theme-select');
        if (themeSelect) {
            themeSelect.addEventListener('change', () => {
                this.settings.theme = themeSelect.value;
            });
        }
    }
    
    async runSystemHealthCheck() {
        try {
            window.NotificationManager.show('開始', 'システムヘルスチェックを実行中...', 'info');

            const health = {};

            // 1) Electron API 自身
            try {
                const statusRes = await window.electronAPI.system.status();
                if (!statusRes || !statusRes.success) throw new Error(statusRes?.error || 'NG');
                health['electron_api'] = { status: 'healthy', message: 'APIサーバー応答OK' };
                // 2) Database（status APIの応答があればOKとみなす）
                health['database'] = { status: 'healthy', message: `DB応答OK (${statusRes.data?.database_path || 'path不明'})` };
            } catch (e) {
                health['electron_api'] = { status: 'unhealthy', message: String(e) };
                health['database'] = { status: 'unknown', message: 'APIが不安定のため判定不可' };
            }

            // 3) Chainlit
            try {
                const url = await window.electronAPI.getChainlitUrl();
                const baseUrl = normalizeChainlitUrlSafe(url);
                if (!baseUrl) {
                    throw new Error('Chainlit URL 未設定');
                }

                let chainlitReady = false;

                if (window.electronAPI?.probeChainlit) {
                    try {
                        const probe = await window.electronAPI.probeChainlit(baseUrl);
                        if (probe?.success) {
                            console.log('✅ Chainlit health via IPC', probe.detail);
                            health['chainlit'] = { status: 'healthy', message: 'Chainlit応答OK' };
                            chainlitReady = true;
                        } else if (probe?.detail) {
                            console.debug('Chainlit IPC health detail', probe.detail);
                        }
                    } catch (probeErr) {
                        console.debug('Chainlit IPC health error', probeErr);
                    }
                }

                if (!chainlitReady) {
                    const controller = new AbortController();
                    const timeout = setTimeout(() => controller.abort(), 2000);
                    const okStatuses = new Set([200, 204, 301, 302, 307, 308, 401, 403, 404]);

                    for (const target of [`${baseUrl}/health`, `${baseUrl}/login`, `${baseUrl}/`, baseUrl]) {
                        try {
                            const response = await fetch(target, {
                                signal: controller.signal,
                                redirect: 'manual',
                                credentials: 'include'
                            });
                            if (okStatuses.has(response.status)) {
                                console.log('✅ Chainlit health check success', {
                                    url: target,
                                    status: response.status
                                });
                                chainlitReady = true;
                                break;
                            }
                        } catch (innerError) {
                            if (innerError.name !== 'AbortError') {
                                continue;
                            }
                        }
                    }

                    clearTimeout(timeout);
                }

                if (!chainlitReady) {
                    throw new Error('Chainlit未応答');
                }

                health['chainlit'] = { status: 'healthy', message: 'Chainlit応答OK' };
            } catch (e) {
                health['chainlit'] = { status: 'unhealthy', message: 'Chainlitに接続できません' };
            }

            // 4) OpenAI（ユーザー操作で課金が発生する可能性があるため、最小呼び出し）
            try {
                const test = await window.electronAPI.callAPI('/api/system/test-openai-key', 'POST', {}, { silent: true });
                if (test && test.success) {
                    health['openai'] = { status: 'healthy', message: `model=${test.data?.model}, latency=${test.data?.latency_ms}ms` };
                } else {
                    throw new Error(test?.error || '疎通失敗');
                }
            } catch (e) {
                health['openai'] = { status: 'unhealthy', message: 'APIキー未設定または疎通失敗' };
            }

            this.showHealthCheckResults(health);
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
    
    async refreshSystemStatus() {
        try {
            const res = await window.electronAPI.system.status();
            if (res && res.success) {
                this.systemStatus = res.data || {};
                // 表示を最新化
                this.renderSettingsPanel();
            } else {
                throw new Error(res?.error || '更新に失敗しました');
            }
        } catch (e) {
            window.NotificationManager.error('エラー', String(e));
        }
    }
    
    async saveGeneralSettings() {
        try {
            const theme = document.getElementById('theme-select')?.value || 'light';
            
            this.settings = {
                ...this.settings,
                theme
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
                theme: 'light'
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
    async viewSystemLogs() {
        try {
            const res = await window.electronAPI.system.logs();
            if (!res || !res.success) throw new Error(res?.error || 'ログの取得に失敗しました');
            const logs = (res.data?.logs || []).join('');
            const html = `
                <div style="max-height: 60vh; overflow: auto; background:#0f172a; color:#e2e8f0; padding: 12px; border-radius: 6px; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace; font-size: 12px;">
                    <pre style="margin:0; white-space: pre-wrap;">${this.escapeHtml(logs)}</pre>
                </div>`;
            window.Modal.show('📜 システムログ（最新100行）', html, { showCancel: true, cancelText: '閉じる', showConfirm: false });
        } catch (e) {
            window.NotificationManager.error('エラー', String(e));
        }
    }

    async exportSystemInfo() {
        try {
            const res = await window.electronAPI.callAPI('/api/system/export', 'GET', null, { silent: false });
            if (!res || !res.success) throw new Error(res?.error || 'エクスポートに失敗しました');
            window.NotificationManager.success('完了', `システム情報をエクスポートしました: ${res.data?.filename}`);
        } catch (e) {
            window.NotificationManager.error('エラー', String(e));
        }
    }

    async testApiKey() {
        try {
            const key = document.getElementById('openai-api-key')?.value || '';
            const payload = key ? { api_key: key } : {};
            const res = await window.electronAPI.callAPI('/api/system/test-openai-key', 'POST', payload, { silent: false });
            if (!res || !res.success) throw new Error(res?.error || '疎通テストに失敗しました');
            const m = res.data?.model || 'unknown';
            const t = res.data?.latency_ms != null ? `${res.data.latency_ms} ms` : 'OK';
            window.NotificationManager.success('OpenAI 接続OK', `model=${m}, latency=${t}`);
        } catch (e) {
            window.NotificationManager.error('OpenAI 接続エラー', String(e));
        }
    }

    async cleanupData() {
        const proceed = confirm('一時ファイル・古いログ・エクスポート/アップロードをクリーンアップします。\n\nOpenAI側のデータには一切影響しません。続行しますか？');
        if (!proceed) return;
        try {
            const res = await window.electronAPI.callAPI('/api/system/cleanup', 'POST', {});
            if (!res || !res.success) throw new Error(res?.error || 'クリーンアップに失敗しました');
            const d = res.data || {};
            window.NotificationManager.success('完了', `削除: ファイル ${d.removed_files || 0}, ディレクトリ ${d.removed_dirs || 0}`);
        } catch (e) {
            window.NotificationManager.error('エラー', String(e));
        }
    }

    async resetAllData() {
        try {
            // プレビュー
            const preview = await window.electronAPI.callAPI('/api/system/factory-reset', 'POST', { preview: true, confirm: false });
            const p = preview?.data?.preview || {};
            const msg = `以下を初期化します（OpenAI API側は変更しません）:\n\n` +
                        `DB: ${p.db || 0} / 一時: ${p.tmp || 0} / ログ: ${p.logs || 0} / exports: ${p.exports || 0} / uploads: ${p.uploads || 0} / personas: ${p.personas || 0}`;
            const ok = confirm(msg + '\n\n本当に実行しますか？この操作は取り消せません。');
            if (!ok) return;
            const res = await window.electronAPI.callAPI('/api/system/factory-reset', 'POST', { confirm: true });
            if (!res || !res.success) throw new Error(res?.error || '初期化に失敗しました');
            window.NotificationManager.success('完了', 'アプリデータを初期化しました。アプリを再起動します。');
            // 再起動
            setTimeout(() => { try { window.electronAPI.app.relaunch(); } catch {} }, 1200);
        } catch (e) {
            window.NotificationManager.error('エラー', String(e));
        }
    }

    async openDevTools() { try { await window.electronAPI.app.toggleDevTools(); } catch (e) { console.error(e); } }
    async restartApplication() { try { await window.electronAPI.app.relaunch(); } catch (e) { console.error(e); } }
    
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
