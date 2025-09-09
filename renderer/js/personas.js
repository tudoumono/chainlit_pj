/**
 * ペルソナ管理システム
 * AIアシスタントペルソナの作成・編集・削除
 */

class PersonaManager {
    constructor() {
        this.personas = [];
        this.selectedPersona = null;
        this.isLoaded = false;
        
        this.setupEventListeners();
    }
    
    setupEventListeners() {
        // 新しいペルソナ作成ボタン
        const createBtn = document.getElementById('create-persona-btn');
        if (createBtn) {
            createBtn.addEventListener('click', () => {
                this.showCreatePersonaModal();
            });
        }
    }
    
    async loadPersonas() {
        if (this.isLoaded) return;
        
        try {
            console.log('🔄 Loading personas...');
            
            const response = await window.electronAPI.personas.list();
            if (response && response.success) {
                this.personas = response.data || [];
            } else {
                throw new Error(response?.error || 'ペルソナデータの取得に失敗しました');
            }
            
            this.renderPersonaList();
            this.isLoaded = true;
            
            console.log(`✅ Loaded ${this.personas.length} personas`);
            
        } catch (error) {
            console.error('❌ Error loading personas:', error);
            this.renderError('ペルソナの読み込みに失敗しました: ' + error.message);
        }
    }
    
    renderPersonaList() {
        const container = document.getElementById('persona-manager');
        if (!container) return;
        
        if (this.personas.length === 0) {
            container.innerHTML = `
                <div class="content-area">
                    <div class="text-center" style="padding: 3rem;">
                        <h3>👤 ペルソナが見つかりません</h3>
                        <p class="text-muted">新しいペルソナを作成して始めましょう。</p>
                        <button onclick="window.PersonaManager.showCreatePersonaModal()" class="btn btn-primary">
                            ＋ 最初のペルソナを作成
                        </button>
                    </div>
                </div>
            `;
            return;
        }
        
        const personaCards = this.personas.map(persona => this.renderPersonaCard(persona)).join('');
        
        container.innerHTML = `
            <div class="content-area">
                <div class="row" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(350px, 1fr)); gap: 1rem;">
                    ${personaCards}
                </div>
            </div>
        `;
    }
    
    renderPersonaCard(persona) {
        const isActive = persona.is_active ? 'badge-success' : 'badge-secondary';
        const statusText = persona.is_active ? 'アクティブ' : '無効';
        
        return `
            <div class="card persona-card" data-persona-id="${persona.id}">
                <div class="card-header">
                    <div class="card-title">${this.escapeHtml(persona.name)}</div>
                    <span class="badge ${isActive}">${statusText}</span>
                </div>
                <div class="card-body">
                    <p class="persona-description">
                        ${this.escapeHtml(persona.description || '説明なし')}
                    </p>
                    <div class="persona-meta">
                        <small class="text-muted">
                            モデル: ${this.escapeHtml(persona.model || 'デフォルト')}<br>
                            作成日: ${this.formatDate(persona.created_at)}
                        </small>
                    </div>
                </div>
                <div class="card-footer">
                    <div class="btn-group" style="display: flex; gap: 0.5rem;">
                        <button onclick="window.PersonaManager.editPersona('${persona.id}')" 
                                class="btn btn-secondary btn-sm">
                            ✏️ 編集
                        </button>
                        <button onclick="window.PersonaManager.togglePersonaStatus('${persona.id}', ${!persona.is_active})" 
                                class="btn btn-${persona.is_active ? 'warning' : 'success'} btn-sm">
                            ${persona.is_active ? '❌ 無効化' : '✅ 有効化'}
                        </button>
                        <button onclick="window.PersonaManager.deletePersona('${persona.id}')" 
                                class="btn btn-danger btn-sm">
                            🗑️ 削除
                        </button>
                    </div>
                </div>
            </div>
        `;
    }
    
    renderError(message) {
        const container = document.getElementById('persona-manager');
        if (container) {
            container.innerHTML = `
                <div class="content-area">
                    <div class="alert alert-danger">
                        <h4>⚠️ エラーが発生しました</h4>
                        <p>${this.escapeHtml(message)}</p>
                        <button onclick="window.PersonaManager.reloadPersonas()" class="btn btn-primary">
                            再試行
                        </button>
                    </div>
                </div>
            `;
        }
    }
    
    showCreatePersonaModal() {
        const modalHtml = `
            <form id="persona-form" onsubmit="window.PersonaManager.handlePersonaSubmit(event)">
                <div class="form-group" style="margin-bottom: 1rem;">
                    <label for="persona-name">ペルソナ名 *</label>
                    <input type="text" id="persona-name" name="name" class="form-input" 
                           style="width: 100%; margin-top: 0.25rem;" required>
                </div>
                
                <div class="form-group" style="margin-bottom: 1rem;">
                    <label for="persona-description">説明</label>
                    <textarea id="persona-description" name="description" class="form-input" 
                              rows="3" style="width: 100%; margin-top: 0.25rem; resize: vertical;"></textarea>
                </div>
                
                <div class="form-group" style="margin-bottom: 1rem;">
                    <label for="persona-system-prompt">システムプロンプト *</label>
                    <textarea id="persona-system-prompt" name="system_prompt" class="form-input" 
                              rows="5" style="width: 100%; margin-top: 0.25rem; resize: vertical;" required 
                              placeholder="この AI はどのような役割を果たすべきかを説明してください..."></textarea>
                </div>
                
                <div class="form-group" style="margin-bottom: 1rem;">
                    <label for="persona-model">モデル</label>
                    <select id="persona-model" name="model" class="form-select" style="width: 100%; margin-top: 0.25rem;">
                        <option value="gpt-4o">GPT-4o</option>
                        <option value="gpt-4o-mini">GPT-4o Mini</option>
                        <option value="gpt-4">GPT-4</option>
                        <option value="gpt-3.5-turbo">GPT-3.5 Turbo</option>
                    </select>
                </div>
                
                <div class="form-group" style="margin-bottom: 1rem;">
                    <label>
                        <input type="checkbox" id="persona-active" name="is_active" checked>
                        このペルソナをアクティブにする
                    </label>
                </div>
            </form>
        `;
        
        window.Modal.show('新しいペルソナを作成', modalHtml, {
            confirmText: 'ペルソナを作成',
            confirmClass: 'btn-success'
        });
    }
    
    async editPersona(personaId) {
        try {
            const response = await window.electronAPI.personas.get(personaId);
            if (!response || !response.success) {
                throw new Error('ペルソナデータの取得に失敗しました');
            }
            
            const persona = response.data;
            const modalHtml = `
                <form id="persona-form" onsubmit="window.PersonaManager.handlePersonaSubmit(event, '${personaId}')">
                    <div class="form-group" style="margin-bottom: 1rem;">
                        <label for="persona-name">ペルソナ名 *</label>
                        <input type="text" id="persona-name" name="name" class="form-input" 
                               style="width: 100%; margin-top: 0.25rem;" required 
                               value="${this.escapeHtml(persona.name)}">
                    </div>
                    
                    <div class="form-group" style="margin-bottom: 1rem;">
                        <label for="persona-description">説明</label>
                        <textarea id="persona-description" name="description" class="form-input" 
                                  rows="3" style="width: 100%; margin-top: 0.25rem; resize: vertical;">${this.escapeHtml(persona.description || '')}</textarea>
                    </div>
                    
                    <div class="form-group" style="margin-bottom: 1rem;">
                        <label for="persona-system-prompt">システムプロンプト *</label>
                        <textarea id="persona-system-prompt" name="system_prompt" class="form-input" 
                                  rows="5" style="width: 100%; margin-top: 0.25rem; resize: vertical;" required>${this.escapeHtml(persona.system_prompt || '')}</textarea>
                    </div>
                    
                    <div class="form-group" style="margin-bottom: 1rem;">
                        <label for="persona-model">モデル</label>
                        <select id="persona-model" name="model" class="form-select" style="width: 100%; margin-top: 0.25rem;">
                            <option value="gpt-4o" ${persona.model === 'gpt-4o' ? 'selected' : ''}>GPT-4o</option>
                            <option value="gpt-4o-mini" ${persona.model === 'gpt-4o-mini' ? 'selected' : ''}>GPT-4o Mini</option>
                            <option value="gpt-4" ${persona.model === 'gpt-4' ? 'selected' : ''}>GPT-4</option>
                            <option value="gpt-3.5-turbo" ${persona.model === 'gpt-3.5-turbo' ? 'selected' : ''}>GPT-3.5 Turbo</option>
                        </select>
                    </div>
                    
                    <div class="form-group" style="margin-bottom: 1rem;">
                        <label>
                            <input type="checkbox" id="persona-active" name="is_active" ${persona.is_active ? 'checked' : ''}>
                            このペルソナをアクティブにする
                        </label>
                    </div>
                </form>
            `;
            
            window.Modal.show('ペルソナを編集', modalHtml, {
                confirmText: 'ペルソナを更新',
                confirmClass: 'btn-primary'
            });
            
        } catch (error) {
            console.error('❌ Error editing persona:', error);
            window.NotificationManager.show('エラー', 'ペルソナの編集に失敗しました: ' + error.message, 'error');
        }
    }
    
    async handlePersonaSubmit(event, personaId = null) {
        event.preventDefault();
        
        try {
            const formData = new FormData(event.target);
            const personaData = {
                name: formData.get('name'),
                description: formData.get('description'),
                system_prompt: formData.get('system_prompt'),
                model: formData.get('model'),
                is_active: formData.has('is_active')
            };
            
            let response;
            if (personaId) {
                response = await window.electronAPI.personas.update(personaId, personaData);
            } else {
                response = await window.electronAPI.personas.create(personaData);
            }
            
            if (!response || !response.success) {
                throw new Error(response?.error || 'ペルソナの保存に失敗しました');
            }
            
            window.Modal.hide();
            await this.reloadPersonas();
            
            const action = personaId ? '更新' : '作成';
            window.NotificationManager.show('成功', `ペルソナが${action}されました`, 'success');
            
        } catch (error) {
            console.error('❌ Error saving persona:', error);
            window.NotificationManager.show('エラー', 'ペルソナの保存に失敗しました: ' + error.message, 'error');
        }
    }
    
    async togglePersonaStatus(personaId, newStatus) {
        try {
            const response = await window.electronAPI.personas.update(personaId, {
                is_active: newStatus
            });
            
            if (!response || !response.success) {
                throw new Error('ペルソナステータスの更新に失敗しました');
            }
            
            await this.reloadPersonas();
            
            const statusText = newStatus ? '有効化' : '無効化';
            window.NotificationManager.show('成功', `ペルソナが${statusText}されました`, 'success');
            
        } catch (error) {
            console.error('❌ Error toggling persona status:', error);
            window.NotificationManager.show('エラー', 'ペルソナステータスの更新に失敗しました: ' + error.message, 'error');
        }
    }
    
    async deletePersona(personaId) {
        const persona = this.personas.find(p => p.id === personaId);
        if (!persona) return;
        
        const confirmMessage = `ペルソナ "${persona.name}" を削除しますか？\n\nこの操作は取り消せません。`;
        
        if (!confirm(confirmMessage)) {
            return;
        }
        
        try {
            const response = await window.electronAPI.personas.delete(personaId);
            
            if (!response || !response.success) {
                throw new Error('ペルソナの削除に失敗しました');
            }
            
            await this.reloadPersonas();
            window.NotificationManager.show('成功', 'ペルソナが削除されました', 'success');
            
        } catch (error) {
            console.error('❌ Error deleting persona:', error);
            window.NotificationManager.show('エラー', 'ペルソナの削除に失敗しました: ' + error.message, 'error');
        }
    }
    
    async reloadPersonas() {
        this.isLoaded = false;
        await this.loadPersonas();
    }
    
    // ユーティリティメソッド
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

// ペルソナマネージャー初期化
document.addEventListener('DOMContentLoaded', () => {
    window.PersonaManager = new PersonaManager();
    console.log('✅ Persona Manager initialized');
});