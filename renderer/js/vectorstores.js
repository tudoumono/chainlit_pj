/**
 * ベクトルストア管理システム
 * ベクトルストアの作成・ファイルアップロード・削除
 */

class VectorStoreManager {
    constructor() {
        this.vectorStores = [];
        this.selectedVectorStore = null;
        this.isLoaded = false;
        
        this.setupEventListeners();
    }
    
    setupEventListeners() {
        // 新しいベクトルストア作成ボタン
        const createBtn = document.getElementById('create-vectorstore-btn');
        if (createBtn) {
            createBtn.addEventListener('click', () => {
                this.showCreateVectorStoreModal();
            });
        }

        // ブラウザで開く
        const openBrowserBtn = document.getElementById('open-vectorstores-browser');
        if (openBrowserBtn && window.electronAPI?.app?.openInBrowser) {
            openBrowserBtn.addEventListener('click', () => {
                window.electronAPI.app.openInBrowser('');
            });
        }

        // 再読み込み
        const refreshBtn = document.getElementById('refresh-vectorstores-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', async () => {
                this.isLoaded = false;
                await this.loadVectorStores();
                window.NotificationManager?.info('更新', 'ベクトルストア一覧を更新しました');
            });
        }
    }
    
    async loadVectorStores() {
        if (this.isLoaded) return;

        // ローディング表示
        const container = document.getElementById('vectorstore-manager');
        if (container) {
            container.innerHTML = `
                <div class="content-area">
                    <div class="loading-message">
                        <div class="loading-spinner-dark"></div>
                        <div id="vs-loading-text">ベクトルストア一覧を読み込み中...</div>
                    </div>
                </div>
            `;
        }

        // 長時間時の案内（3秒後に文言を更新）
        let slowNoticeTimer = null;
        try {
            console.log('🔄 Loading vector stores...');
            slowNoticeTimer = setTimeout(() => {
                const textEl = document.getElementById('vs-loading-text');
                if (textEl) {
                    textEl.textContent = '時間がかかっています… 大きなデータの集計中か、ネットワーク待機中です';
                }
            }, 3000);

            const response = await window.electronAPI.vectorStore.list();
            if (response && response.success) {
                this.vectorStores = response.data || [];
            } else {
                throw new Error(response?.error || 'ベクトルストアデータの取得に失敗しました');
            }
            
            this.renderVectorStoreList();
            this.isLoaded = true;
            
            console.log(`✅ Loaded ${this.vectorStores.length} vector stores`);
            
        } catch (error) {
            console.error('❌ Error loading vector stores:', error);
            this.renderError('ベクトルストアの読み込みに失敗しました: ' + error.message);
        } finally {
            if (slowNoticeTimer) {
                clearTimeout(slowNoticeTimer);
            }
        }
    }
    
    renderVectorStoreList() {
        const container = document.getElementById('vectorstore-manager');
        if (!container) return;
        
        if (this.vectorStores.length === 0) {
            container.innerHTML = `
                <div class="content-area">
                    <div class="text-center" style="padding: 3rem;">
                        <h3>📚 ベクトルストアが見つかりません</h3>
                        <p class="text-muted">新しいベクトルストアを作成してドキュメントを管理しましょう。</p>
                        <button onclick="window.VectorStoreManager.showCreateVectorStoreModal()" class="btn btn-primary">
                            ＋ 最初のベクトルストアを作成
                        </button>
                    </div>
                </div>
            `;
            return;
        }
        
        const vectorStoreCards = this.vectorStores.map(vs => this.renderVectorStoreCard(vs)).join('');
        
        container.innerHTML = `
            <div class="content-area">
                <div class="row" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(400px, 1fr)); gap: 1rem;">
                    ${vectorStoreCards}
                </div>
            </div>
        `;
    }
    
    renderVectorStoreCard(vectorStore) {
        const fileCount = vectorStore.file_counts?.total || 0;
        const isActive = vectorStore.status === 'completed';
        const statusBadge = isActive ? 'badge-success' : 'badge-warning';
        const statusText = this.getStatusText(vectorStore.status);
        
        return `
            <div class="card vectorstore-card" data-vectorstore-id="${vectorStore.id}">
                <div class="card-header">
                    <div class="card-title">${this.escapeHtml(vectorStore.name)}</div>
                    <span class="badge ${statusBadge}">${statusText}</span>
                </div>
                <div class="card-body">
                    <div class="vectorstore-stats" style="margin-bottom: 1rem;">
                        <div class="stat-item">
                            <span class="stat-label">📄 ファイル数:</span>
                            <span class="stat-value">${fileCount}</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-label">📊 使用量:</span>
                            <span class="stat-value">${this.formatBytes(vectorStore.usage_bytes || 0)}</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-label">🕒 作成日:</span>
                            <span class="stat-value">${this.formatDate(vectorStore.created_at)}</span>
                        </div>
                    </div>
                    
                    ${vectorStore.expires_at ? `
                        <div class="expiry-info" style="background: #fff3cd; padding: 0.5rem; border-radius: 4px; font-size: 0.875rem;">
                            ⚠️ 有効期限: ${this.formatDate(vectorStore.expires_at)}
                        </div>
                    ` : ''}
                </div>
                <div class="card-footer">
                    <div class="btn-group" style="display: flex; gap: 0.5rem; flex-wrap: wrap;">
                        <button onclick="window.VectorStoreManager.viewFiles('${vectorStore.id}')" 
                                class="btn btn-secondary btn-sm">
                            📁 ファイル一覧
                        </button>
                        <button onclick="window.VectorStoreManager.renameVectorStore('${vectorStore.id}')" 
                                class="btn btn-secondary btn-sm">
                            ✏️ 名前を変更
                        </button>
                        <button onclick="window.VectorStoreManager.uploadFiles('${vectorStore.id}')" 
                                class="btn btn-primary btn-sm">
                            📤 アップロード
                        </button>
                        <button onclick="window.VectorStoreManager.deleteVectorStore('${vectorStore.id}')" 
                                class="btn btn-danger btn-sm">
                            🗑️ 削除
                        </button>
                    </div>
                </div>
            </div>
        `;
    }

    renameVectorStore(vectorStoreId, currentName = '') {
        const vs = this.vectorStores.find(v => v.id === vectorStoreId);
        const nameForInput = (vs && typeof vs.name === 'string') ? vs.name : currentName;
        const modalHtml = `
            <form id="rename-vs-form" onsubmit="window.VectorStoreManager.handleRenameSubmit(event, '${vectorStoreId}')">
                <div class="form-group" style="margin-bottom: 1rem;">
                    <label for="new-vs-name">新しい名前 *</label>
                    <input type="text" id="new-vs-name" name="name" class="form-input"
                           style="width: 100%; margin-top: 0.25rem;" required
                           value="${this.escapeHtml(nameForInput || '')}" maxlength="120">
                </div>
                <div class="alert alert-info" style="margin-top: 1rem;">
                    <small>この操作はOpenAIのベクトルストア名も更新します。</small>
                </div>
            </form>
        `;
        window.Modal.show('ベクトルストア名の変更', modalHtml, {
            confirmText: '保存',
            confirmClass: 'btn-success'
        });
        // 入力にフォーカス
        setTimeout(() => { document.getElementById('new-vs-name')?.focus(); }, 0);
    }

    async handleRenameSubmit(event, vectorStoreId) {
        event.preventDefault();
        try {
            const formData = new FormData(event.target);
            const newName = String(formData.get('name') || '').trim();
            if (!newName) throw new Error('名前を入力してください');

            const res = await window.electronAPI.vectorStore.rename(vectorStoreId, newName);
            if (!res || !res.success) {
                throw new Error(res?.error || '名前の更新に失敗しました');
            }
            window.Modal.hide();
            await this.reloadVectorStores();
            window.NotificationManager?.success('成功', 'ベクトルストア名を更新しました');
        } catch (err) {
            console.error('❌ Error renaming vector store:', err);
            window.NotificationManager?.error('エラー', 'ベクトルストア名の更新に失敗しました: ' + err.message);
        }
    }
    
    renderError(message) {
        const container = document.getElementById('vectorstore-manager');
        if (container) {
            container.innerHTML = `
                <div class="content-area">
                    <div class="alert alert-danger">
                        <h4>⚠️ エラーが発生しました</h4>
                        <p>${this.escapeHtml(message)}</p>
                        <button onclick="window.VectorStoreManager.reloadVectorStores()" class="btn btn-primary">
                            再試行
                        </button>
                    </div>
                </div>
            `;
        }
    }
    
    showCreateVectorStoreModal() {
        const modalHtml = `
            <form id="vectorstore-form" onsubmit="window.VectorStoreManager.handleVectorStoreSubmit(event)">
                <div class="form-group" style="margin-bottom: 1rem;">
                    <label for="vectorstore-name">ベクトルストア名 *</label>
                    <input type="text" id="vectorstore-name" name="name" class="form-input" 
                           style="width: 100%; margin-top: 0.25rem;" required 
                           placeholder="例: プロジェクトドキュメント">
                </div>
                
                <div class="form-group" style="margin-bottom: 1rem;">
                    <label for="vectorstore-expires-after">自動削除日数</label>
                    <select id="vectorstore-expires-after" name="expires_after_days" class="form-select" 
                            style="width: 100%; margin-top: 0.25rem;">
                        <option value="">自動削除しない</option>
                        <option value="7">7日後</option>
                        <option value="30" selected>30日後</option>
                        <option value="90">90日後</option>
                        <option value="365">365日後</option>
                    </select>
                    <small class="text-muted">指定した日数後にベクトルストアは自動的に削除されます</small>
                </div>
                
                <div class="alert alert-info" style="margin-top: 1rem;">
                    <h5>📋 注意事項</h5>
                    <ul style="margin: 0.5rem 0; padding-left: 1.5rem;">
                        <li>作成後にファイルをアップロードできます</li>
                        <li>ファイル処理には時間がかかる場合があります</li>
                        <li>サポートファイル形式: PDF, TXT, DOCX, MD</li>
                    </ul>
                </div>
            </form>
        `;
        
        window.Modal.show('新しいベクトルストアを作成', modalHtml, {
            confirmText: 'ベクトルストアを作成',
            confirmClass: 'btn-success'
        });
    }
    
    async handleVectorStoreSubmit(event) {
        event.preventDefault();
        
        try {
            const formData = new FormData(event.target);
            const vectorStoreData = {
                name: formData.get('name')
            };
            
            const expiresAfterDays = formData.get('expires_after_days');
            if (expiresAfterDays) {
                vectorStoreData.expires_after_days = parseInt(expiresAfterDays);
            }
            
            const response = await window.electronAPI.vectorStore.create(vectorStoreData);
            
            if (!response || !response.success) {
                throw new Error(response?.error || 'ベクトルストアの作成に失敗しました');
            }
            
            window.Modal.hide();
            await this.reloadVectorStores();
            
            window.NotificationManager.show('成功', 'ベクトルストアが作成されました', 'success');
            
        } catch (error) {
            console.error('❌ Error creating vector store:', error);
            window.NotificationManager.show('エラー', 'ベクトルストアの作成に失敗しました: ' + error.message, 'error');
        }
    }
    
    async viewFiles(vectorStoreId) {
        try {
            const response = await window.electronAPI.vectorStore.get(vectorStoreId);
            if (!response || !response.success) {
                throw new Error('ベクトルストアデータの取得に失敗しました');
            }
            
            const vectorStore = response.data;
            const files = vectorStore.file_details || [];
            
            let filesHtml = '';
            if (files.length === 0) {
                filesHtml = '<p class="text-muted">アップロードされたファイルはありません。</p>';
            } else {
                const fileRows = files.map(file => `
                    <tr>
                        <td title="${this.escapeHtml(file.id)}">${this.escapeHtml(file.filename || file.id)}</td>
                        <td>${this.formatBytes(file.size || 0)}</td>
                        <td><span class="badge ${this.getFileStatusBadge(file.status)}">${this.getFileStatusText(file.status)}</span></td>
                        <td>${this.formatDate(file.created_at)}</td>
                    </tr>
                `).join('');
                
                filesHtml = `
                    <div style="overflow-x: auto;">
                        <table class="table" style="width: 100%; border-collapse: collapse;">
                            <thead style="background: #f8f9fa;">
                                <tr>
                                    <th style="padding: 0.5rem; border: 1px solid #dee2e6;">ファイル名</th>
                                    <th style="padding: 0.5rem; border: 1px solid #dee2e6;">サイズ</th>
                                    <th style="padding: 0.5rem; border: 1px solid #dee2e6;">ステータス</th>
                                    <th style="padding: 0.5rem; border: 1px solid #dee2e6;">作成日</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${fileRows}
                            </tbody>
                        </table>
                    </div>
                `;
            }
            
            const modalHtml = `
                <div class="vectorstore-files">
                    <div class="files-header" style="margin-bottom: 1rem;">
                        <h4>📚 ${this.escapeHtml(vectorStore.name)}</h4>
                        <p class="text-muted">合計ファイル数: ${files.length}</p>
                    </div>
                    ${filesHtml}
                    <div style="margin-top: 1rem;">
                        <button onclick="window.VectorStoreManager.uploadFiles('${vectorStoreId}')" class="btn btn-primary">
                            📤 新しいファイルをアップロード
                        </button>
                    </div>
                </div>
            `;
            
            window.Modal.show('ベクトルストアファイル一覧', modalHtml, {
                showConfirm: false,
                cancelText: '閉じる'
            });
            
        } catch (error) {
            console.error('❌ Error viewing files:', error);
            window.NotificationManager.show('エラー', 'ファイル一覧の取得に失敗しました: ' + error.message, 'error');
        }
    }
    
    uploadFiles(vectorStoreId) {
        const modalHtml = `
            <form id="upload-form" onsubmit="window.VectorStoreManager.handleFileUpload(event, '${vectorStoreId}')">
                <div class="form-group" style="margin-bottom: 1rem;">
                    <label for="upload-files">ファイルを選択 *</label>
                    <input type="file" id="upload-files" name="files" class="form-input" 
                           style="width: 100%; margin-top: 0.25rem; padding: 0.5rem;" 
                           multiple accept=".pdf,.txt,.docx,.md,.doc" required>
                    <small class="text-muted">
                        サポート形式: PDF, TXT, DOCX, MD, DOC（複数選択可能）
                    </small>
                </div>
                
                <div id="upload-progress" class="hidden" style="margin-top: 1rem;">
                    <div class="progress">
                        <div id="progress-bar" class="progress-bar" style="width: 0%"></div>
                    </div>
                    <p id="progress-text" class="text-center" style="margin-top: 0.5rem;">アップロード準備中...</p>
                </div>
                
                <div class="alert alert-info" style="margin-top: 1rem;">
                    <h5>📋 アップロード注意事項</h5>
                    <ul style="margin: 0.5rem 0; padding-left: 1.5rem;">
                        <li>ファイル処理には時間がかかる場合があります</li>
                        <li>大きなファイルは分割して処理されます</li>
                        <li>処理が完了するとベクトル検索で利用可能になります</li>
                    </ul>
                </div>
            </form>
        `;
        
        window.Modal.show('ファイルアップロード', modalHtml, {
            confirmText: 'アップロード開始',
            confirmClass: 'btn-success'
        });
    }
    
    async handleFileUpload(event, vectorStoreId) {
        event.preventDefault();
        
        try {
            const formData = new FormData(event.target);
            const files = formData.getAll('files');
            
            if (files.length === 0) {
                throw new Error('ファイルが選択されていません');
            }
            
            // プログレス表示
            const progressContainer = document.getElementById('upload-progress');
            const progressBar = document.getElementById('progress-bar');
            const progressText = document.getElementById('progress-text');
            
            progressContainer.classList.remove('hidden');
            progressText.textContent = 'アップロード中...';
            
            // ファイルを Base64 に変換してアップロード
            for (let i = 0; i < files.length; i++) {
                const file = files[i];
                const progress = ((i + 1) / files.length) * 100;
                
                progressBar.style.width = `${progress}%`;
                progressText.textContent = `ファイル ${i + 1}/${files.length} をアップロード中: ${file.name}`;
                
                const fileData = await this.fileToBase64(file);
                const uploadData = {
                    filename: file.name,
                    content: fileData,
                    size: file.size,
                    type: file.type
                };
                
                const response = await window.electronAPI.vectorStore.upload(vectorStoreId, uploadData);
                
                if (!response || !response.success) {
                    throw new Error(response?.error || `${file.name} のアップロードに失敗しました`);
                }
            }
            
            window.Modal.hide();
            await this.reloadVectorStores();
            
            window.NotificationManager.show('成功', `${files.length}個のファイルがアップロードされました`, 'success');
            
        } catch (error) {
            console.error('❌ Error uploading files:', error);
            window.NotificationManager.show('エラー', 'ファイルアップロードに失敗しました: ' + error.message, 'error');
        }
    }
    
    async deleteVectorStore(vectorStoreId) {
        const vectorStore = this.vectorStores.find(vs => vs.id === vectorStoreId);
        if (!vectorStore) return;
        
        const confirmMessage = `ベクトルストア "${vectorStore.name}" を削除しますか？\n\n含まれるファイル: ${vectorStore.file_counts?.total || 0}個\n\nこの操作は取り消せません。`;
        
        if (!confirm(confirmMessage)) {
            return;
        }
        
        try {
            const response = await window.electronAPI.vectorStore.delete(vectorStoreId);
            
            if (!response || !response.success) {
                throw new Error('ベクトルストアの削除に失敗しました');
            }
            
            await this.reloadVectorStores();
            window.NotificationManager.show('成功', 'ベクトルストアが削除されました', 'success');
            
        } catch (error) {
            console.error('❌ Error deleting vector store:', error);
            window.NotificationManager.show('エラー', 'ベクトルストアの削除に失敗しました: ' + error.message, 'error');
        }
    }
    
    async reloadVectorStores() {
        this.isLoaded = false;
        await this.loadVectorStores();
    }
    
    // ユーティリティメソッド
    fileToBase64(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.readAsDataURL(file);
            reader.onload = () => resolve(reader.result);
            reader.onerror = error => reject(error);
        });
    }
    
    getStatusText(status) {
        const statusMap = {
            'in_progress': '処理中',
            'completed': '完了',
            'cancelled': 'キャンセル',
            'failed': '失敗',
            'requires_action': '要アクション'
        };
        return statusMap[status] || '不明';
    }
    
    getFileStatusText(status) {
        const statusMap = {
            'in_progress': '処理中',
            'completed': '完了',
            'cancelled': 'キャンセル',
            'failed': '失敗'
        };
        return statusMap[status] || '不明';
    }
    
    getFileStatusBadge(status) {
        const badgeMap = {
            'in_progress': 'badge-warning',
            'completed': 'badge-success',
            'cancelled': 'badge-secondary',
            'failed': 'badge-danger'
        };
        return badgeMap[status] || 'badge-secondary';
    }
    
    formatBytes(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
    
    escapeHtml(text) {
        if (typeof text !== 'string') return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    formatDate(dateString) {
        if (!dateString) return '不明';
        try {
            return new Date(dateString).toLocaleString('ja-JP');
        } catch {
            return '不明';
        }
    }
}

// ベクトルストアマネージャー初期化
document.addEventListener('DOMContentLoaded', () => {
    window.VectorStoreManager = new VectorStoreManager();
    console.log('✅ Vector Store Manager initialized');
});
