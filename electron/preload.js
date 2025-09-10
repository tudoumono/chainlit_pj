/**
 * Electron Preload Script
 * Context7のセキュリティベストプラクティスに準拠
 * contextBridgeを使用してセキュアなAPIを公開
 */

const { contextBridge, ipcRenderer } = require('electron');

// セキュアなAPI公開
contextBridge.exposeInMainWorld('electronAPI', {
    // システム情報
    getSystemInfo: () => ipcRenderer.invoke('get-system-info'),
    
    // Chainlit URL取得
    getChainlitUrl: () => ipcRenderer.invoke('get-chainlit-url'),
    
    // Electron Backend API (REST)
    callAPI: (endpoint, method = 'GET', data = null) => 
        ipcRenderer.invoke('electron-api', endpoint, method, data),
    
    // ペルソナ管理API
    personas: {
        list: () => ipcRenderer.invoke('electron-api', '/api/personas', 'GET'),
        create: (personaData) => 
            ipcRenderer.invoke('electron-api', '/api/personas', 'POST', personaData),
        get: (personaId) => 
            ipcRenderer.invoke('electron-api', `/api/personas/${personaId}`, 'GET'),
        update: (personaId, personaData) =>
            ipcRenderer.invoke('electron-api', `/api/personas/${personaId}`, 'PUT', personaData),
        delete: (personaId) =>
            ipcRenderer.invoke('electron-api', `/api/personas/${personaId}`, 'DELETE')
    },
    
    // ベクトルストア管理API
    vectorStore: {
        list: () => ipcRenderer.invoke('electron-api', '/api/vectorstores', 'GET'),
        create: (data) => 
            ipcRenderer.invoke('electron-api', '/api/vectorstores', 'POST', data),
        get: (vectorStoreId) => 
            ipcRenderer.invoke('electron-api', `/api/vectorstores/${vectorStoreId}`, 'GET'),
        rename: (vectorStoreId, name) =>
            ipcRenderer.invoke('electron-api', `/api/vectorstores/${vectorStoreId}`, 'PATCH', { name }),
        upload: (vectorStoreId, fileData) =>
            ipcRenderer.invoke('electron-api', `/api/vectorstores/${vectorStoreId}/upload`, 'POST', fileData),
        delete: (vectorStoreId) =>
            ipcRenderer.invoke('electron-api', `/api/vectorstores/${vectorStoreId}`, 'DELETE')
    },
    
    // 分析・統計API
    analytics: {
        dashboard: (userId) => 
            ipcRenderer.invoke('electron-api', `/api/analytics/dashboard/${userId}`, 'GET'),
        usage: (userId, period) =>
            ipcRenderer.invoke('electron-api', `/api/analytics/usage/${userId}?period=${period}`, 'GET'),
        export: (userId, format) =>
            ipcRenderer.invoke('electron-api', `/api/analytics/export/${userId}?format=${format}`, 'GET')
    },
    
    // システム情報API
    system: {
        status: () => ipcRenderer.invoke('electron-api', '/api/system/status', 'GET'),
        logs: () => ipcRenderer.invoke('electron-api', '/api/system/logs', 'GET'),
        health: () => ipcRenderer.invoke('electron-api', '/api/health', 'GET')
    },
    
    // ファイル操作API
    files: {
        export: (data, filename) => 
            ipcRenderer.invoke('electron-api', '/api/files/export', 'POST', { data, filename }),
        import: (filepath) =>
            ipcRenderer.invoke('electron-api', '/api/files/import', 'POST', { filepath })
    },
    
    // アプリケーション制御
    app: {
        quit: () => ipcRenderer.invoke('app-quit'),
        minimize: () => ipcRenderer.invoke('window-minimize'),
        maximize: () => ipcRenderer.invoke('window-maximize'),
        close: () => ipcRenderer.invoke('window-close'),
        startChainlit: () => ipcRenderer.invoke('start-chainlit'),
        startElectronAPI: () => ipcRenderer.invoke('start-electron-api'),
        openLogFolder: () => ipcRenderer.invoke('open-log-folder'),
        openChat: () => ipcRenderer.invoke('open-chat'),
        openInBrowser: (path = '') => ipcRenderer.invoke('open-in-browser', path),
        toggleDevTools: () => ipcRenderer.invoke('toggle-devtools'),
        relaunch: () => ipcRenderer.invoke('app-relaunch'),
        returnToSettings: () => ipcRenderer.invoke('return-to-settings')
    },
    
    // 通知API
    notification: {
        show: (title, body, options = {}) => {
            // ブラウザのNotification APIを安全に使用
            if ('Notification' in window && Notification.permission === 'granted') {
                return new Notification(title, { body, ...options });
            } else if (Notification.permission === 'default') {
                Notification.requestPermission().then(permission => {
                    if (permission === 'granted') {
                        return new Notification(title, { body, ...options });
                    }
                });
            }
            return null;
        },
        requestPermission: () => {
            if ('Notification' in window) {
                return Notification.requestPermission();
            }
            return Promise.resolve('denied');
        }
    }
});

// 開発時のデバッグ情報
if (process.env.NODE_ENV === 'development') {
    contextBridge.exposeInMainWorld('electronDebug', {
        platform: process.platform,
        versions: process.versions,
        cwd: process.cwd()
    });
}

console.log('🔒 Preload script loaded - Secure APIs exposed');


// DynamicCSPUpdateMarker
// 動的CSP更新（環境変数のポートに追従）
try {
  window.addEventListener('DOMContentLoaded', () => {
    const clPort = process.env.CHAINLIT_PORT || "8000";
    const apiPort = process.env.ELECTRON_API_PORT || "8001";
    const clHost = process.env.CHAINLIT_HOST || "127.0.0.1";
    const apiHost = process.env.ELECTRON_API_HOST || "127.0.0.1";
    const meta = document.querySelector('meta[http-equiv="Content-Security-Policy"]');
    if (meta) {
      const csp = [
        "default-src 'self'",
        "script-src 'self'",
        "style-src 'self' 'unsafe-inline'",
        "img-src 'self' data: https:",
        "connect-src 'self' http://"+clHost+":"+clPort+" http://"+apiHost+":"+apiPort,
        "frame-src 'self' http://"+clHost+":"+clPort
      ].join('; ');
      meta.setAttribute('content', csp);
      console.log('🔐 CSP updated for ports', { clPort, apiPort });
    }
  });
} catch {}
