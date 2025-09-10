/**
 * 分析・統計管理システム
 * ユーザー使用状況の分析とダッシュボード表示
 */

class AnalyticsManager {
    constructor() {
        this.dashboardData = null;
        this.currentUserId = 'admin'; // デフォルトユーザー
        this.currentPeriod = '30d';
        this.isLoaded = false;
        
        this.setupEventListeners();
    }
    
    setupEventListeners() {
        // 期間選択
        const periodSelect = document.getElementById('analytics-period');
        if (periodSelect) {
            periodSelect.addEventListener('change', (event) => {
                this.currentPeriod = event.target.value;
                this.reloadDashboard();
            });
        }
        
        // エクスポートボタン
        const exportBtn = document.getElementById('export-analytics-btn');
        if (exportBtn) {
            exportBtn.addEventListener('click', () => {
                this.showExportModal();
            });
        }

        // ブラウザで開く
        const openBrowserBtn = document.getElementById('open-analytics-browser');
        if (openBrowserBtn && window.electronAPI?.app?.openInBrowser) {
            openBrowserBtn.addEventListener('click', () => {
                window.electronAPI.app.openInBrowser('');
            });
        }
    }
    
    async loadDashboard() {
        if (this.isLoaded) return;
        
        try {
            console.log(`🔄 Loading analytics dashboard for user ${this.currentUserId}...`);
            
            // ダッシュボードデータとユーザー使用状況を並行取得
            const [dashboardResponse, usageResponse] = await Promise.all([
                window.electronAPI.analytics.dashboard(this.currentUserId),
                window.electronAPI.analytics.usage(this.currentUserId, this.currentPeriod)
            ]);
            
            if (!dashboardResponse || !dashboardResponse.success) {
                throw new Error(dashboardResponse?.error || 'ダッシュボードデータの取得に失敗しました');
            }
            
            if (!usageResponse || !usageResponse.success) {
                throw new Error(usageResponse?.error || '使用状況データの取得に失敗しました');
            }
            
            this.dashboardData = {
                dashboard: dashboardResponse.data,
                usage: usageResponse.data
            };
            
            this.renderDashboard();
            this.isLoaded = true;
            
            console.log('✅ Analytics dashboard loaded');
            
        } catch (error) {
            console.error('❌ Error loading analytics:', error);
            this.renderError('分析データの読み込みに失敗しました: ' + error.message);
        }
    }
    
    renderDashboard() {
        const container = document.getElementById('analytics-dashboard');
        if (!container || !this.dashboardData) return;
        
        const { dashboard, usage } = this.dashboardData;
        
        container.innerHTML = `
            <div class="content-area">
                <!-- 概要カード -->
                <div class="dashboard-overview" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 1rem; margin-bottom: 2rem;">
                    ${this.renderOverviewCard('💬', 'チャット数', dashboard.total_chats || 0, '累計セッション数')}
                    ${this.renderOverviewCard('📝', 'メッセージ数', dashboard.total_messages || 0, '送受信メッセージ数')}
                    ${this.renderOverviewCard('📚', 'ベクトルストア', dashboard.total_vector_stores || 0, '作成済みストア数')}
                    ${this.renderOverviewCard('👤', 'ペルソナ', dashboard.total_personas || 0, '登録済みペルソナ数')}
                </div>
                
                <!-- グラフとチャート -->
                <div class="dashboard-charts" style="display: grid; grid-template-columns: 1fr 1fr; gap: 2rem; margin-bottom: 2rem;">
                    <!-- 使用状況グラフ -->
                    <div class="card">
                        <div class="card-header">
                            <h3 class="card-title">📈 使用状況推移</h3>
                        </div>
                        <div class="card-body">
                            ${this.renderUsageChart(usage.daily_usage || [])}
                        </div>
                    </div>
                    
                    <!-- トップ機能 -->
                    <div class="card">
                        <div class="card-header">
                            <h3 class="card-title">🏆 よく使用される機能</h3>
                        </div>
                        <div class="card-body">
                            ${this.renderTopFeatures(usage.feature_usage || [])}
                        </div>
                    </div>
                </div>
                
                <!-- 詳細テーブル -->
                <div class="dashboard-tables" style="display: grid; grid-template-columns: 1fr; gap: 2rem;">
                    <!-- 最近のアクティビティ -->
                    <div class="card">
                        <div class="card-header">
                            <h3 class="card-title">🕒 最近のアクティビティ</h3>
                        </div>
                        <div class="card-body">
                            ${this.renderRecentActivity(usage.recent_activities || [])}
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
    
    renderOverviewCard(icon, title, value, description) {
        return `
            <div class="card overview-card">
                <div class="card-body" style="text-align: center; padding: 1.5rem;">
                    <div style="font-size: 2rem; margin-bottom: 0.5rem;">${icon}</div>
                    <h3 style="font-size: 2rem; margin: 0; color: #007bff;">${this.formatNumber(value)}</h3>
                    <div style="font-weight: 600; margin: 0.5rem 0;">${title}</div>
                    <div style="font-size: 0.875rem; color: #6c757d;">${description}</div>
                </div>
            </div>
        `;
    }
    
    renderUsageChart(dailyUsage) {
        if (dailyUsage.length === 0) {
            return '<p class="text-muted text-center" style="padding: 2rem;">使用データがありません</p>';
        }
        
        const maxValue = Math.max(...dailyUsage.map(d => d.count));
        const chartBars = dailyUsage.slice(-14).map(data => { // 最新14日分
            const height = maxValue > 0 ? (data.count / maxValue) * 100 : 0;
            const date = new Date(data.date).toLocaleDateString('ja-JP', { month: 'short', day: 'numeric' });
            
            return `
                <div class="chart-bar" style="text-align: center; flex: 1;">
                    <div style="height: 120px; display: flex; align-items: end; justify-content: center; margin-bottom: 0.5rem;">
                        <div style="
                            width: 24px; 
                            height: ${height}%; 
                            background: linear-gradient(to top, #007bff, #00c3ff);
                            border-radius: 2px 2px 0 0;
                            transition: height 0.3s ease;
                            ${height === 0 ? 'min-height: 2px; opacity: 0.3;' : ''}
                        " title="${date}: ${data.count}回"></div>
                    </div>
                    <div style="font-size: 0.75rem; color: #6c757d;">${date}</div>
                </div>
            `;
        }).join('');
        
        return `
            <div class="usage-chart" style="display: flex; align-items: end; gap: 4px; padding: 1rem 0;">
                ${chartBars}
            </div>
        `;
    }
    
    renderTopFeatures(featureUsage) {
        if (featureUsage.length === 0) {
            return '<p class="text-muted text-center" style="padding: 2rem;">機能使用データがありません</p>';
        }
        
        const maxUsage = Math.max(...featureUsage.map(f => f.count));
        
        const featureItems = featureUsage.slice(0, 5).map(feature => {
            const percentage = maxUsage > 0 ? (feature.count / maxUsage) * 100 : 0;
            const icon = this.getFeatureIcon(feature.feature_name);
            
            return `
                <div class="feature-item" style="margin-bottom: 1rem;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.25rem;">
                        <span style="display: flex; align-items: center; gap: 0.5rem;">
                            ${icon} ${this.escapeHtml(feature.feature_name)}
                        </span>
                        <span style="font-weight: 600;">${this.formatNumber(feature.count)}</span>
                    </div>
                    <div class="progress" style="height: 6px;">
                        <div class="progress-bar" style="width: ${percentage}%; background: #28a745;"></div>
                    </div>
                </div>
            `;
        }).join('');
        
        return featureItems;
    }
    
    renderRecentActivity(activities) {
        if (activities.length === 0) {
            return '<p class="text-muted text-center" style="padding: 2rem;">最近のアクティビティがありません</p>';
        }
        
        const activityRows = activities.slice(0, 10).map(activity => `
            <tr>
                <td style="padding: 0.75rem; border-bottom: 1px solid #e9ecef;">
                    ${this.getActivityIcon(activity.type)} ${this.escapeHtml(activity.description)}
                </td>
                <td style="padding: 0.75rem; border-bottom: 1px solid #e9ecef; color: #6c757d; font-size: 0.875rem;">
                    ${this.formatDate(activity.timestamp)}
                </td>
            </tr>
        `).join('');
        
        return `
            <div style="overflow-x: auto;">
                <table style="width: 100%; border-collapse: collapse;">
                    <thead style="background: #f8f9fa;">
                        <tr>
                            <th style="padding: 0.75rem; text-align: left; border-bottom: 2px solid #dee2e6;">アクティビティ</th>
                            <th style="padding: 0.75rem; text-align: left; border-bottom: 2px solid #dee2e6; width: 200px;">日時</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${activityRows}
                    </tbody>
                </table>
            </div>
        `;
    }
    
    renderError(message) {
        const container = document.getElementById('analytics-dashboard');
        if (container) {
            container.innerHTML = `
                <div class="content-area">
                    <div class="alert alert-danger">
                        <h4>⚠️ エラーが発生しました</h4>
                        <p>${this.escapeHtml(message)}</p>
                        <button onclick="window.AnalyticsManager.reloadDashboard()" class="btn btn-primary">
                            再試行
                        </button>
                    </div>
                </div>
            `;
        }
    }
    
    showExportModal() {
        const modalHtml = `
            <form id="export-form" onsubmit="window.AnalyticsManager.handleExport(event)">
                <div class="form-group" style="margin-bottom: 1rem;">
                    <label for="export-format">エクスポート形式</label>
                    <select id="export-format" name="format" class="form-select" style="width: 100%; margin-top: 0.25rem;">
                        <option value="csv">CSV ファイル</option>
                        <option value="json">JSON ファイル</option>
                        <option value="pdf">PDF レポート</option>
                    </select>
                </div>
                
                <div class="form-group" style="margin-bottom: 1rem;">
                    <label for="export-period">データ期間</label>
                    <select id="export-period" name="period" class="form-select" style="width: 100%; margin-top: 0.25rem;">
                        <option value="7d">過去7日</option>
                        <option value="30d" selected>過去30日</option>
                        <option value="90d">過去90日</option>
                        <option value="all">全期間</option>
                    </select>
                </div>
                
                <div class="form-group" style="margin-bottom: 1rem;">
                    <label>含めるデータ</label>
                    <div style="margin-top: 0.5rem;">
                        <label style="display: block; margin-bottom: 0.25rem;">
                            <input type="checkbox" name="include_data" value="usage" checked> 使用状況統計
                        </label>
                        <label style="display: block; margin-bottom: 0.25rem;">
                            <input type="checkbox" name="include_data" value="chats" checked> チャット履歴
                        </label>
                        <label style="display: block; margin-bottom: 0.25rem;">
                            <input type="checkbox" name="include_data" value="vectorstores"> ベクトルストア情報
                        </label>
                        <label style="display: block; margin-bottom: 0.25rem;">
                            <input type="checkbox" name="include_data" value="personas"> ペルソナ設定
                        </label>
                    </div>
                </div>
                
                <div class="alert alert-info" style="margin-top: 1rem;">
                    <h5>📋 エクスポート注意事項</h5>
                    <ul style="margin: 0.5rem 0; padding-left: 1.5rem;">
                        <li>大量のデータの場合、処理に時間がかかる可能性があります</li>
                        <li>PDFレポートには概要統計のみが含まれます</li>
                        <li>個人情報は適切に匿名化されます</li>
                    </ul>
                </div>
            </form>
        `;
        
        window.Modal.show('データエクスポート', modalHtml, {
            confirmText: 'エクスポート開始',
            confirmClass: 'btn-success'
        });
    }
    
    async handleExport(event) {
        event.preventDefault();
        
        try {
            const formData = new FormData(event.target);
            const format = formData.get('format');
            const period = formData.get('period');
            const includeData = formData.getAll('include_data');
            
            if (includeData.length === 0) {
                throw new Error('エクスポートするデータを選択してください');
            }
            
            window.Modal.hide();
            
            // エクスポート開始通知
            window.NotificationManager.show('開始', 'データエクスポートを開始しました', 'info');
            
            const response = await window.electronAPI.analytics.export(this.currentUserId, format);
            
            if (!response || !response.success) {
                throw new Error(response?.error || 'データエクスポートに失敗しました');
            }
            
            // ダウンロードリンクの表示（実装は電子側で処理される想定）
            window.NotificationManager.show('完了', 'データエクスポートが完了しました', 'success');
            
        } catch (error) {
            console.error('❌ Error exporting data:', error);
            window.NotificationManager.show('エラー', 'データエクスポートに失敗しました: ' + error.message, 'error');
        }
    }
    
    async reloadDashboard() {
        this.isLoaded = false;
        await this.loadDashboard();
    }
    
    // ユーティリティメソッド
    getFeatureIcon(featureName) {
        const iconMap = {
            'chat': '💬',
            'vectorstore': '📚',
            'persona': '👤',
            'upload': '📤',
            'search': '🔍',
            'export': '📊',
            'settings': '⚙️'
        };
        
        const key = featureName.toLowerCase();
        return iconMap[key] || '📌';
    }
    
    getActivityIcon(activityType) {
        const iconMap = {
            'chat': '💬',
            'upload': '📤',
            'create': '➕',
            'update': '✏️',
            'delete': '🗑️',
            'login': '🔑',
            'export': '📊'
        };
        
        return iconMap[activityType] || '📝';
    }
    
    formatNumber(num) {
        if (num >= 1000000) {
            return (num / 1000000).toFixed(1) + 'M';
        } else if (num >= 1000) {
            return (num / 1000).toFixed(1) + 'K';
        }
        return num.toLocaleString();
    }
    
    formatDate(dateString) {
        if (!dateString) return '不明';
        try {
            return new Date(dateString).toLocaleString('ja-JP');
        } catch {
            return '不明';
        }
    }
    
    escapeHtml(text) {
        if (typeof text !== 'string') return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// 分析マネージャー初期化（DOMContentLoaded前後どちらでも安全に初期化）
(function initAnalyticsManager() {
    const boot = () => {
        if (!window.AnalyticsManager) {
            window.AnalyticsManager = new AnalyticsManager();
            console.log('✅ Analytics Manager initialized');
        }
    };
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', boot, { once: true });
    } else {
        boot();
    }
})();
