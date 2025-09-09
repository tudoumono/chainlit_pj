/**
 * タブ管理システム
 * タブ切り替えとコンテンツ管理
 */

class TabManager {
    constructor() {
        this.activeTab = 'chat';
        this.tabButtons = new Map();
        this.tabPanes = new Map();
        this.loadedTabs = new Set(['chat']); // チャットタブは最初から読み込み済み
        
        this.init();
    }
    
    init() {
        this.setupTabElements();
        this.setupEventListeners();
        this.showActiveTab();
        
        console.log('✅ Tab Manager initialized');
    }
    
    setupTabElements() {
        // タブボタンの取得
        const tabButtonElements = document.querySelectorAll('.tab-button');
        tabButtonElements.forEach(button => {
            const tabId = button.getAttribute('data-tab');
            this.tabButtons.set(tabId, button);
        });
        
        // タブペインの取得
        const tabPaneElements = document.querySelectorAll('.tab-pane');
        tabPaneElements.forEach(pane => {
            const tabId = pane.id;
            this.tabPanes.set(tabId, pane);
        });
    }
    
    setupEventListeners() {
        // タブボタンのクリックイベント
        this.tabButtons.forEach((button, tabId) => {
            button.addEventListener('click', (event) => {
                event.preventDefault();
                this.switchTab(tabId);
            });
        });
        
        // キーボードショートカット
        document.addEventListener('keydown', (event) => {
            if (event.ctrlKey || event.metaKey) {
                const keyMap = {
                    '1': 'chat',
                    '2': 'personas',
                    '3': 'vectorstores',
                    '4': 'analytics',
                    '5': 'settings'
                };
                
                const tabId = keyMap[event.key];
                if (tabId) {
                    event.preventDefault();
                    this.switchTab(tabId);
                }
            }
        });
    }
    
    async switchTab(tabId) {
        if (!this.tabButtons.has(tabId) || !this.tabPanes.has(tabId)) {
            console.warn(`Tab '${tabId}' not found`);
            return;
        }
        
        // 現在のタブと同じ場合は何もしない
        if (this.activeTab === tabId) {
            return;
        }
        
        console.log(`🔄 Switching from '${this.activeTab}' to '${tabId}'`);
        
        try {
            // ローディング状態を表示
            this.showTabLoading(tabId);
            
            // タブの非同期読み込み
            if (!this.loadedTabs.has(tabId)) {
                await this.loadTabContent(tabId);
                this.loadedTabs.add(tabId);
            }
            
            // UIの更新
            this.updateTabUI(tabId);
            
            // アクティブタブの更新
            this.activeTab = tabId;
            
            console.log(`✅ Tab switched to '${tabId}'`);
            
        } catch (error) {
            console.error(`❌ Error switching to tab '${tabId}':`, error);
            this.showTabError(tabId, error.message);
        }
    }
    
    async loadTabContent(tabId) {
        switch (tabId) {
            case 'personas':
                if (window.PersonaManager) {
                    await window.PersonaManager.loadPersonas();
                }
                break;
                
            case 'vectorstores':
                if (window.VectorStoreManager) {
                    await window.VectorStoreManager.loadVectorStores();
                }
                break;
                
            case 'analytics':
                if (window.AnalyticsManager) {
                    await window.AnalyticsManager.loadDashboard();
                }
                break;
                
            case 'settings':
                if (window.SettingsManager) {
                    await window.SettingsManager.loadSettings();
                }
                break;
                
            case 'chat':
            default:
                // チャットタブは常に読み込み済み
                break;
        }
    }
    
    updateTabUI(tabId) {
        // 全てのタブボタンから active クラスを削除
        this.tabButtons.forEach(button => {
            button.classList.remove('active');
            button.classList.remove('loading');
        });
        
        // 全てのタブペインを非表示
        this.tabPanes.forEach(pane => {
            pane.classList.remove('active');
        });
        
        // アクティブなタブのボタンとペインをアクティブ化
        const activeButton = this.tabButtons.get(tabId);
        const activePane = this.tabPanes.get(tabId);
        
        if (activeButton) {
            activeButton.classList.add('active');
        }
        
        if (activePane) {
            activePane.classList.add('active');
        }
    }
    
    showTabLoading(tabId) {
        const button = this.tabButtons.get(tabId);
        if (button && !this.loadedTabs.has(tabId)) {
            button.classList.add('loading');
        }
    }
    
    showTabError(tabId, errorMessage) {
        const pane = this.tabPanes.get(tabId);
        if (pane) {
            const errorHtml = `
                <div class="content-area">
                    <div class="alert alert-danger">
                        <h4>⚠️ エラーが発生しました</h4>
                        <p>${errorMessage}</p>
                        <button onclick="window.TabManager.retryLoadTab('${tabId}')" class="btn btn-primary">
                            再試行
                        </button>
                    </div>
                </div>
            `;
            pane.innerHTML = errorHtml;
        }
    }
    
    async retryLoadTab(tabId) {
        // 読み込み済みフラグをリセット
        this.loadedTabs.delete(tabId);
        
        // タブを再読み込み
        await this.switchTab(tabId);
    }
    
    showActiveTab() {
        this.updateTabUI(this.activeTab);
    }
    
    // タブにバッジを表示（通知用）
    showTabBadge(tabId, count) {
        const button = this.tabButtons.get(tabId);
        if (!button) return;
        
        let badge = button.querySelector('.tab-badge');
        if (!badge) {
            badge = document.createElement('span');
            badge.className = 'tab-badge';
            button.appendChild(badge);
        }
        
        if (count > 0) {
            badge.textContent = count > 99 ? '99+' : count.toString();
            badge.style.display = 'block';
        } else {
            badge.style.display = 'none';
        }
    }
    
    // タブのローディング状態を制御
    setTabLoading(tabId, loading) {
        const button = this.tabButtons.get(tabId);
        if (button) {
            button.classList.toggle('loading', loading);
        }
    }
    
    // ウィンドウリサイズ時の処理
    handleResize(width, height) {
        // モバイル表示での調整
        const isMobile = width < 768;
        
        if (isMobile) {
            // モバイルではテキストを非表示にしてアイコンのみ表示
            this.tabButtons.forEach(button => {
                const text = button.querySelector('.tab-text');
                if (text) {
                    text.style.display = 'none';
                }
            });
        } else {
            // デスクトップではテキストを表示
            this.tabButtons.forEach(button => {
                const text = button.querySelector('.tab-text');
                if (text) {
                    text.style.display = '';
                }
            });
        }
    }
    
    // 現在のアクティブタブIDを取得
    getActiveTab() {
        return this.activeTab;
    }
    
    // タブが読み込み済みかチェック
    isTabLoaded(tabId) {
        return this.loadedTabs.has(tabId);
    }
    
    // 全てのタブを再読み込み
    async reloadAllTabs() {
        this.loadedTabs.clear();
        this.loadedTabs.add('chat'); // チャットタブは常に読み込み済み扱い
        
        // 現在のアクティブタブを再読み込み
        await this.loadTabContent(this.activeTab);
        this.loadedTabs.add(this.activeTab);
    }
}

// タブマネージャー初期化
let tabManager;

document.addEventListener('DOMContentLoaded', () => {
    console.log('🚀 Tab Manager starting...');
    tabManager = new TabManager();
    
    // グローバルアクセス用
    window.TabManager = tabManager;
});