/**
 * モーダルダイアログ管理システム
 * 汎用モーダル表示とイベント処理
 */

class Modal {
    constructor() {
        this.overlay = document.getElementById('modal-overlay');
        this.dialog = this.overlay?.querySelector('.modal-dialog');
        this.title = document.getElementById('modal-title');
        this.body = document.getElementById('modal-body');
        this.cancelBtn = document.getElementById('modal-cancel-btn');
        this.confirmBtn = document.getElementById('modal-confirm-btn');
        this.closeBtn = document.getElementById('modal-close-btn');
        
        this.currentOptions = {};
        this.isVisible = false;
        
        this.setupEventListeners();
    }
    
    setupEventListeners() {
        if (!this.overlay) return;
        
        // 背景クリックで閉じる
        this.overlay.addEventListener('click', (event) => {
            if (event.target === this.overlay) {
                this.hide();
            }
        });
        
        // Escapeキーで閉じる（IME合成中は無視）
        document.addEventListener('keydown', (event) => {
            if (event.isComposing) return; // 日本語IME合成中はESCを奪わない
            if (event.key === 'Escape' && this.isVisible) {
                event.preventDefault();
                this.hide();
            }
        });
        
        // 閉じるボタン
        this.closeBtn?.addEventListener('click', () => {
            this.hide();
        });
        
        // キャンセルボタン
        this.cancelBtn?.addEventListener('click', () => {
            this.hide();
        });
        
        // 確認ボタン
        this.confirmBtn?.addEventListener('click', () => {
            this.handleConfirm();
        });
    }
    
    show(title, bodyHtml, options = {}) {
        if (!this.overlay) {
            console.error('Modal overlay not found');
            return;
        }
        
        this.currentOptions = {
            showConfirm: true,
            showCancel: true,
            confirmText: 'OK',
            cancelText: 'キャンセル',
            confirmClass: 'btn-primary',
            cancelClass: 'btn-secondary',
            onConfirm: null,
            onCancel: null,
            ...options
        };
        
        // タイトルとコンテンツを設定
        if (this.title) {
            this.title.textContent = title;
        }
        
        if (this.body) {
            this.body.innerHTML = bodyHtml;
        }
        
        // ボタンの設定
        this.setupButtons();
        
        // モーダルを表示
        this.overlay.classList.remove('hidden');
        this.isVisible = true;
        
        // フォーカス設定
        setTimeout(() => {
            const firstInput = this.body.querySelector('input, textarea, select');
            if (firstInput) {
                firstInput.focus();
            } else if (this.confirmBtn && this.confirmBtn.style.display !== 'none') {
                this.confirmBtn.focus();
            }
        }, 100);
        
        // ボディのスクロールを無効化
        document.body.style.overflow = 'hidden';
        
        console.log('✅ Modal shown:', title);
    }
    
    hide() {
        if (!this.overlay || !this.isVisible) return;
        
        this.overlay.classList.add('hidden');
        this.isVisible = false;
        
        // ボディのスクロールを復元
        document.body.style.overflow = '';
        
        // コールバック実行
        if (this.currentOptions.onCancel) {
            this.currentOptions.onCancel();
        }
        
        // クリーンアップ
        this.currentOptions = {};
        
        console.log('✅ Modal hidden');
    }
    
    setupButtons() {
        if (!this.confirmBtn || !this.cancelBtn) return;
        
        const { showConfirm, showCancel, confirmText, cancelText, confirmClass, cancelClass } = this.currentOptions;
        
        // 確認ボタンの設定
        if (showConfirm) {
            this.confirmBtn.style.display = 'inline-flex';
            this.confirmBtn.textContent = confirmText;
            this.confirmBtn.className = `btn ${confirmClass}`;
        } else {
            this.confirmBtn.style.display = 'none';
        }
        
        // キャンセルボタンの設定
        if (showCancel) {
            this.cancelBtn.style.display = 'inline-flex';
            this.cancelBtn.textContent = cancelText;
            this.cancelBtn.className = `btn ${cancelClass}`;
        } else {
            this.cancelBtn.style.display = 'none';
        }
    }
    
    handleConfirm() {
        // フォームの検証
        const form = this.body.querySelector('form');
        if (form) {
            // HTML5バリデーション
            if (!form.checkValidity()) {
                form.reportValidity();
                return;
            }
            
            // カスタムフォーム送信処理
            if (form.onsubmit) {
                const event = new Event('submit', { cancelable: true });
                const result = form.onsubmit(event);
                if (event.defaultPrevented || result === false) {
                    return;
                }
            } else {
                // フォームイベントを手動で発火
                const submitEvent = new Event('submit', { bubbles: true, cancelable: true });
                if (!form.dispatchEvent(submitEvent)) {
                    return;
                }
            }
        }
        
        // コールバック実行
        if (this.currentOptions.onConfirm) {
            const result = this.currentOptions.onConfirm();
            if (result === false) {
                return; // コールバックが false を返した場合は閉じない
            }
        }
        
        // フォーム以外の場合は自動で閉じる
        if (!form) {
            this.hide();
        }
    }
    
    // 静的メソッド（グローバルアクセス用）
    static show(title, bodyHtml, options = {}) {
        if (!window.modalInstance) {
            console.error('Modal instance not initialized');
            return;
        }
        window.modalInstance.show(title, bodyHtml, options);
    }
    
    static hide() {
        if (!window.modalInstance) {
            console.error('Modal instance not initialized');
            return;
        }
        window.modalInstance.hide();
    }
    
    static confirm(title, message, onConfirm, onCancel) {
        const bodyHtml = `<p>${message.replace(/\n/g, '<br>')}</p>`;
        
        Modal.show(title, bodyHtml, {
            confirmText: '確認',
            cancelText: 'キャンセル',
            confirmClass: 'btn-primary',
            onConfirm,
            onCancel
        });
    }
    
    static alert(title, message, onClose) {
        const bodyHtml = `<p>${message.replace(/\n/g, '<br>')}</p>`;
        
        Modal.show(title, bodyHtml, {
            showConfirm: false,
            cancelText: 'OK',
            onCancel: onClose
        });
    }
    
    static prompt(title, message, defaultValue = '', onConfirm, onCancel) {
        const bodyHtml = `
            <p>${message.replace(/\n/g, '<br>')}</p>
            <form id="prompt-form" onsubmit="event.preventDefault(); window.Modal.handlePromptSubmit();">
                <input type="text" id="prompt-input" class="form-input" 
                       style="width: 100%; margin-top: 1rem;" 
                       value="${defaultValue.replace(/"/g, '&quot;')}" required>
            </form>
        `;
        
        Modal.show(title, bodyHtml, {
            confirmText: '確認',
            cancelText: 'キャンセル',
            onConfirm: () => {
                const input = document.getElementById('prompt-input');
                if (input && onConfirm) {
                    const result = onConfirm(input.value);
                    if (result !== false) {
                        Modal.hide();
                    }
                    return false; // 自動では閉じない
                }
            },
            onCancel
        });
        
        // 入力フィールドにフォーカス
        setTimeout(() => {
            const input = document.getElementById('prompt-input');
            if (input) {
                input.focus();
                input.select();
            }
        }, 100);
    }
    
    static handlePromptSubmit() {
        // Enterキーでの送信処理
        const confirmBtn = document.getElementById('modal-confirm-btn');
        if (confirmBtn) {
            confirmBtn.click();
        }
    }
    
    // 便利メソッド
    static loading(title = '読み込み中...', message = '') {
        const bodyHtml = `
            <div style="text-align: center; padding: 2rem;">
                <div class="spinner spinner-lg" style="margin-bottom: 1rem;"></div>
                <p>${message || 'しばらくお待ちください...'}</p>
            </div>
        `;
        
        Modal.show(title, bodyHtml, {
            showConfirm: false,
            showCancel: false
        });
    }
    
    static success(title, message, onClose) {
        const bodyHtml = `
            <div style="text-align: center; padding: 1rem;">
                <div style="font-size: 3rem; color: #28a745; margin-bottom: 1rem;">✅</div>
                <p>${message.replace(/\n/g, '<br>')}</p>
            </div>
        `;
        
        Modal.show(title, bodyHtml, {
            showConfirm: false,
            cancelText: 'OK',
            cancelClass: 'btn-success',
            onCancel: onClose
        });
    }
    
    static error(title, message, onClose) {
        const bodyHtml = `
            <div style="text-align: center; padding: 1rem;">
                <div style="font-size: 3rem; color: #dc3545; margin-bottom: 1rem;">❌</div>
                <p>${message.replace(/\n/g, '<br>')}</p>
            </div>
        `;
        
        Modal.show(title, bodyHtml, {
            showConfirm: false,
            cancelText: 'OK',
            cancelClass: 'btn-danger',
            onCancel: onClose
        });
    }
    
    static warning(title, message, onClose) {
        const bodyHtml = `
            <div style="text-align: center; padding: 1rem;">
                <div style="font-size: 3rem; color: #ffc107; margin-bottom: 1rem;">⚠️</div>
                <p>${message.replace(/\n/g, '<br>')}</p>
            </div>
        `;
        
        Modal.show(title, bodyHtml, {
            showConfirm: false,
            cancelText: 'OK',
            cancelClass: 'btn-warning',
            onCancel: onClose
        });
    }
    
    // 現在の状態を取得
    static isVisible() {
        return window.modalInstance?.isVisible || false;
    }
}

// モーダル初期化
document.addEventListener('DOMContentLoaded', () => {
    window.modalInstance = new Modal();
    window.Modal = Modal;
    console.log('✅ Modal system initialized');
});
