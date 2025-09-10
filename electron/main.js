/**
 * Electron Main Process
 * Chainlit + Electron統合アプリケーションのメインプロセス
 * Context7のElectronドキュメントベストプラクティスに準拠
 */

const { app, BrowserWindow, ipcMain, shell, Menu } = require('electron');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
const axios = require('axios');

// セキュリティ・互換性調整（ready 前に設定）
try {
    // 1) 埋め込み時の認証維持のため、第三者Cookie/SameSite強制を無効化
    app.commandLine.appendSwitch(
        'disable-features',
        'BlockThirdPartyCookies,SameSiteByDefaultCookies,CookiesWithoutSameSiteMustBeSecure'
    );
    // 2) 一部環境（WSL/VM 等）のGPU初期化エラー回避
    app.disableHardwareAcceleration();
} catch {}
const log = require('electron-log');

function getLogDir() {
    // ワーキングフォルダ直下に Log/ を作成して使用（env LOG_DIR があれば優先）
    return process.env.LOG_DIR || path.join(process.cwd(), 'Log');
}

function ensureLogDir() {
    const dir = getLogDir();
    try { fs.mkdirSync(dir, { recursive: true }); } catch {}
    return dir;
}

function setupMainLogger() {
    const dir = ensureLogDir();
    const mainLogPath = path.join(dir, 'main.log');
    // electron-log 設定
    // electron-log API変更への対応（resolvePathFn を使用）
    if (log.transports.file.resolvePathFn) {
        log.transports.file.resolvePathFn = () => mainLogPath;
    } else {
        // 後方互換
        // @ts-ignore
        log.transports.file.resolvePath = () => mainLogPath;
    }
    const level = (process.env.LOG_LEVEL_MAIN || 'info').toLowerCase();
    log.transports.console.level = process.env.LOG_ENABLE_CONSOLE === 'false' ? false : level;
    log.transports.file.level = process.env.LOG_ENABLE_FILE === 'false' ? false : level;
    log.info('Logger initialized', { mainLogPath });
    return { dir, mainLogPath };
}

// 環境ファイルの配置方針（Option B想定）
// - 開発時: リポジトリ直下の `.env` を使用
// - 配布時: 初回起動時に `<userData>/.env` を作成（存在しなければ `.env` または `.env.example` をコピー）
// - Electron と Python（Chainlit/Electron API）の双方が同じ .env を参照できるよう、パスを一元化
function ensureUserEnvFile() {
    const userDataDir = app.getPath('userData');
    const targetEnv = path.join(userDataDir, '.env');

    try {
        // すでに存在する場合は何もしない
        if (fs.existsSync(targetEnv)) {
            process.env.DOTENV_PATH = targetEnv;
            return targetEnv;
        }

        // サンプルテンプレート（最終フォールバック用）
        const defaultTemplate = `# Chainlit / Electron 共通設定 (サンプル)
# 生成場所: ${targetEnv}

# OpenAI API
OPENAI_API_KEY=
DEFAULT_MODEL=gpt-4o-mini

# Chainlit 認証
CHAINLIT_AUTH_SECRET=

# オプション: ベクトルストアIDなど
# COMPANY_VECTOR_STORE_ID=

# その他アプリ設定（必要に応じて追記）
`;

        // 開発 or 配布のテンプレート候補を作成
        const cwdEnv = path.join(process.cwd(), '.env');
        const cwdEnvExample = path.join(process.cwd(), '.env.example');
        const resourceEnv = app.isPackaged ? path.join(process.resourcesPath, '.env') : null;
        const resourceEnvExample = app.isPackaged ? path.join(process.resourcesPath, '.env.example') : null;

        // パッケージ環境では .env.example を優先（秘密情報の同梱を避ける）
        const candidateOrder = app.isPackaged
            ? [resourceEnvExample, resourceEnv, cwdEnvExample, cwdEnv]
            : [cwdEnv, cwdEnvExample, resourceEnv, resourceEnvExample];

        const src = candidateOrder.find(p => {
            try { return p && fs.existsSync(p); } catch { return false; }
        });

        // userData 配下に.envを作成（テンプレートが無ければサンプルを生成）
        fs.mkdirSync(userDataDir, { recursive: true });
        if (src) {
            try {
                fs.copyFileSync(src, targetEnv);
            } catch (copyErr) {
                console.warn('Failed to copy .env template, writing default sample:', copyErr);
                fs.writeFileSync(targetEnv, defaultTemplate, 'utf-8');
            }
        } else {
            fs.writeFileSync(targetEnv, defaultTemplate, 'utf-8');
        }

        process.env.DOTENV_PATH = targetEnv;
        return targetEnv;
    } catch (e) {
        console.error('Failed to ensure user .env file:', e);
        return null;
    }
}

class ChainlitIntegratedManager {
    constructor() {
        this.pythonProcess = null; // backward compat (will hold chainlitProcess)
        this.chainlitProcess = null;
        this.apiProcess = null;
        this.chainlitUrl = 'http://localhost:8000';
        this.electronApiUrl = 'http://localhost:8001';
        this.mainWindow = null;
    }

    getPaths() {
        const baseDir = app.isPackaged ? process.resourcesPath : path.join(__dirname, '..');
        const pythonDist = app.isPackaged
            ? (process.platform === 'win32'
                ? path.join(process.resourcesPath, 'python_dist', 'python.exe')
                : path.join(process.resourcesPath, 'python_dist', 'bin', 'python'))
            : null;
        return { baseDir, pythonDist };
    }

    buildPythonEnv(extra = {}) {
        const { baseDir, pythonDist } = this.getPaths();
        const env = {
            ...process.env,
            PYTHONUNBUFFERED: '1',
            CHAINLIT_CONFIG_PATH: path.join(baseDir, '.chainlit', 'config.toml'),
            DOTENV_PATH: process.env.DOTENV_PATH || ''
        };
        if (app.isPackaged && pythonDist) {
            const pyHome = path.dirname(pythonDist);
            env.PYTHONHOME = pyHome;
            // site-packages 想定パス（配布時の配置に合わせて調整可能）
            const sitePackages = process.platform === 'win32'
                ? path.join(pyHome, 'Lib', 'site-packages')
                : path.join(pyHome, '..', 'lib', 'python3', 'site-packages');
            env.PYTHONPATH = sitePackages;
            env.PATH = `${pyHome}${path.delimiter}${process.env.PATH || ''}`;
        }
        return { ...env, ...extra };
    }

    async startChainlit() {
        if (this.chainlitProcess) return true;
        // ALWAYS_SPAWN=true の場合は検出スキップ
        if (process.env.ALWAYS_SPAWN === 'true') {
            console.log('⚙️ ALWAYS_SPAWN=true: forcing Chainlit spawn');
        } else {
            // すでに外部で起動している場合は起動をスキップ
            try {
                await axios.get(this.chainlitUrl, { timeout: 1000 });
                console.log('ℹ️ Detected existing Chainlit server; skip spawn');
                return true;
            } catch {}
        }
        // すでに外部で起動している場合は起動をスキップ
        try {
            await axios.get(this.chainlitUrl, { timeout: 1000 });
            console.log('ℹ️ Detected existing Chainlit server; skip spawn');
            return true;
        } catch {}
        const { baseDir, pythonDist } = this.getPaths();
        console.log('🚀 Chainlit サーバーを起動中...');
        let command;
        let args;
        let cwd = baseDir;
        if (app.isPackaged && pythonDist) {
            command = pythonDist;
            args = ['-m', 'chainlit', 'run', path.join(baseDir, 'app.py'), '--host', '127.0.0.1', '--port', '8000'];
        } else {
            command = 'uv';
            args = ['run', 'chainlit', 'run', path.join(baseDir, 'app.py'), '--host', '127.0.0.1', '--port', '8000'];
        }
        this.chainlitProcess = spawn(command, args, {
            stdio: ['pipe', 'pipe', 'pipe'],
            cwd,
            env: this.buildPythonEnv()
        });
        this.pythonProcess = this.chainlitProcess; // for backward compat on shutdown
        // ログ出力
        try {
            const dir = ensureLogDir();
            const out = fs.createWriteStream(path.join(dir, 'chainlit.out.log'), { flags: 'a' });
            const err = fs.createWriteStream(path.join(dir, 'chainlit.err.log'), { flags: 'a' });
            this.chainlitProcess.stdout.pipe(out);
            this.chainlitProcess.stderr.pipe(err);
        } catch {}
        this.chainlitProcess.stdout.on('data', (d) => console.log('🐍 Chainlit:', d.toString()));
        this.chainlitProcess.stderr.on('data', (d) => console.error('🔴 Chainlit:', d.toString()));
        this.chainlitProcess.on('close', (code) => console.log(`🛑 Chainlit exited: ${code}`));
        return true;
    }

    async startElectronAPI() {
        if (this.apiProcess) return true;
        if (process.env.ALWAYS_SPAWN === 'true') {
            console.log('⚙️ ALWAYS_SPAWN=true: forcing Electron API spawn');
        } else {
            // すでに外部で起動している場合は起動をスキップ
            try {
                await axios.get(`${this.electronApiUrl}/api/health`, { timeout: 1000 });
                console.log('ℹ️ Detected existing Electron API server; skip spawn');
                return true;
            } catch {}
        }
        const { baseDir, pythonDist } = this.getPaths();
        console.log('📡 Electron API サーバーを起動中...');
        let command;
        let args;
        let cwd = baseDir;
        if (app.isPackaged && pythonDist) {
            command = pythonDist;
            args = [path.join(baseDir, 'electron_api.py')];
        } else {
            command = 'uv';
            args = ['run', 'python', path.join(baseDir, 'electron_api.py')];
        }
        this.apiProcess = spawn(command, args, {
            stdio: ['pipe', 'pipe', 'pipe'],
            cwd,
            env: this.buildPythonEnv()
        });
        // ログ出力
        try {
            const dir = ensureLogDir();
            const out = fs.createWriteStream(path.join(dir, 'electron-api.out.log'), { flags: 'a' });
            const err = fs.createWriteStream(path.join(dir, 'electron-api.err.log'), { flags: 'a' });
            this.apiProcess.stdout.pipe(out);
            this.apiProcess.stderr.pipe(err);
        } catch {}
        this.apiProcess.stdout.on('data', (d) => console.log('📡 Electron API:', d.toString()));
        this.apiProcess.stderr.on('data', (d) => console.error('🔴 Electron API:', d.toString()));
        this.apiProcess.on('close', (code) => console.log(`🛑 Electron API exited: ${code}`));
        return true;
    }

    async start() {
        await this.startChainlit();
        await this.startElectronAPI();
        await this.waitForServers();
    }

    async waitForServers() {
        console.log('⏳ サーバー起動を待機中...');
        const maxAttempts = 30;
        let chainlitReady = false;
        let electronApiReady = false;

        for (let i = 0; i < maxAttempts; i++) {
            try {
                if (!chainlitReady) {
                    await axios.get(this.chainlitUrl, { timeout: 2000 });
                    chainlitReady = true;
                    console.log('✅ Chainlit server ready');
                }

                if (!electronApiReady) {
                    await axios.get(`${this.electronApiUrl}/api/health`, { timeout: 2000 });
                    electronApiReady = true;
                    console.log('✅ Electron API server ready');
                }

                if (chainlitReady && electronApiReady) {
                    break;
                }
            } catch (error) {
                // サーバーがまだ起動していない
                if (i % 5 === 0) {
                    console.log(`⏳ 起動待機中... (${i + 1}/${maxAttempts})`);
                }
            }

            await new Promise(resolve => setTimeout(resolve, 1000));
        }

        if (!chainlitReady || !electronApiReady) {
            throw new Error('Failed to start Python servers');
        }

        console.log('🎉 全サーバーの起動が完了しました');
    }

    async callElectronAPI(endpoint, method = 'GET', data = null) {
        /**
         * Electron API呼び出し
         * RESTful APIエンドポイントとの通信を管理
         */
        try {
            const config = {
                method,
                url: `${this.electronApiUrl}${endpoint}`,
                headers: { 'Content-Type': 'application/json' },
                timeout: 10000
            };

            if (data) {
                config.data = data;
            }

            const response = await axios(config);
            return response.data;
        } catch (error) {
            console.error(`API Error [${method} ${endpoint}]:`, error.message);
            throw new Error(`API Error: ${error.message}`);
        }
    }

    createMainWindow() {
        /**
         * メインウィンドウ作成
         * Context7のベストプラクティスに従ったBrowserWindow設定
         */
        this.mainWindow = new BrowserWindow({
            width: 1400,
            height: 900,
            minWidth: 800,
            minHeight: 600,
            show: false,  // ready-to-showイベントまで非表示
            webPreferences: {
                nodeIntegration: false,        // セキュリティ: Node.js統合を無効化
                contextIsolation: true,        // セキュリティ: コンテキスト分離を有効化
                enableRemoteModule: false,     // セキュリティ: リモートモジュールを無効化
                preload: path.join(__dirname, 'preload.js'),
                webSecurity: false  // 開発環境用: Cross-originリクエストを許可
            },
            icon: path.join(__dirname, '..', 'build', 'icon.png'), // アプリケーションアイコン
            titleBarStyle: process.platform === 'darwin' ? 'hiddenInset' : 'default'
        });

        // 初期は設定画面（自前UI）をロード
        this.mainWindow.loadFile(path.join(__dirname, '..', 'renderer', 'index.html'));

        // ready-to-showイベント: 視覚的なフラッシュを防ぐ
        this.mainWindow.once('ready-to-show', () => {
            this.mainWindow.show();
            
            // 開発時のDevTools自動オープンは無効化（必要なら手動で開く）
        });

        // ウィンドウが閉じられた時の処理
        this.mainWindow.on('closed', () => {
            this.mainWindow = null;
        });

        return this.mainWindow;
    }
}

// グローバルインスタンス
const chainlitManager = new ChainlitIntegratedManager();

// アプリケーション初期化
app.whenReady().then(async () => {
    try {
        console.log('🚀 Electronアプリケーション起動');

        // ロガー初期化
        const { dir: logDir } = setupMainLogger();
        console.log('📁 Log directory:', logDir);

        // 共有 .env の用意（ユーザーが編集可能な場所）
        const dotenvPath = ensureUserEnvFile();
        if (dotenvPath) {
            console.log('📄 Using .env at:', dotenvPath);
        }
        
        // Python統合サーバーを起動
        await chainlitManager.start();
        
        // メインウィンドウ作成
        chainlitManager.createMainWindow();

        // アプリメニュー（設定に戻る）
        const template = [
            {
                label: 'アプリ',
                submenu: [
                    {
                        label: '設定に戻る',
                        click: () => {
                            if (chainlitManager.mainWindow) {
                                chainlitManager.mainWindow.loadFile(path.join(__dirname, '..', 'renderer', 'index.html'));
                            }
                        }
                    },
                    { type: 'separator' },
                    { role: 'quit', label: '終了' }
                ]
            },
            // 開発メニュー（パッケージ時は非表示）
            ...(!app.isPackaged ? [{
                label: '開発',
                submenu: [
                    { role: 'reload', label: '再読み込み' },
                    { role: 'forceReload', label: '強制再読み込み' },
                    { role: 'toggleDevTools', label: '開発者ツール' }
                ]
            }] : [])
        ];
        const menu = Menu.buildFromTemplate(template);
        Menu.setApplicationMenu(menu);
        
    } catch (error) {
        console.error('❌ アプリケーションの起動に失敗:', error);
        
        // エラーダイアログを表示後、アプリを終了
        const { dialog } = require('electron');
        await dialog.showErrorBox('起動エラー', 
            `アプリケーションの起動に失敗しました:\n${error.message}\n\n必要な依存関係がインストールされているか確認してください。`
        );
        app.quit();
    }
});

// macOS: Dockアイコンクリック時の処理
app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
        chainlitManager.createMainWindow();
    }
});

// アプリケーション終了時の処理
app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') {
        app.quit();
    }
});

app.on('before-quit', () => {
    console.log('🛑 アプリケーションを終了中...');
    
    // 子プロセスを適切に終了
    try {
        if (chainlitManager.apiProcess) {
            chainlitManager.apiProcess.kill('SIGTERM');
            console.log('✅ Electron APIプロセスを終了しました');
        }
        if (chainlitManager.chainlitProcess) {
            chainlitManager.chainlitProcess.kill('SIGTERM');
            console.log('✅ Chainlitプロセスを終了しました');
        }
    } catch (e) {
        console.error('子プロセス終了時のエラー:', e);
    }
});

// IPC Handlers: Renderer ⇔ Main Process通信

// Electron API呼び出し
ipcMain.handle('electron-api', async (event, endpoint, method, data) => {
    try {
        const result = await chainlitManager.callElectronAPI(endpoint, method, data);
        return { success: true, data: result };
    } catch (error) {
        return { success: false, error: error.message };
    }
});

// サーバー起動/停止（IPC）
ipcMain.handle('start-chainlit', async () => {
    await chainlitManager.startChainlit();
    return { success: true };
});
ipcMain.handle('start-electron-api', async () => {
    await chainlitManager.startElectronAPI();
    return { success: true };
});
ipcMain.handle('stop-chainlit', async () => {
    if (chainlitManager.chainlitProcess) {
        chainlitManager.chainlitProcess.kill('SIGTERM');
        chainlitManager.chainlitProcess = null;
    }
    return { success: true };
});
ipcMain.handle('stop-electron-api', async () => {
    if (chainlitManager.apiProcess) {
        chainlitManager.apiProcess.kill('SIGTERM');
        chainlitManager.apiProcess = null;
    }
    return { success: true };
});

// 画面遷移（IPC）
ipcMain.handle('open-chat', async () => {
    if (chainlitManager.mainWindow) {
        await chainlitManager.mainWindow.loadURL(chainlitManager.chainlitUrl);
        return { success: true };
    }
    return { success: false, error: 'No main window' };
});

ipcMain.handle('return-to-settings', async () => {
    if (chainlitManager.mainWindow) {
        await chainlitManager.mainWindow.loadFile(path.join(__dirname, '..', 'renderer', 'index.html'));
        return { success: true };
    }
    return { success: false, error: 'No main window' };
});

// Chainlit URL取得
ipcMain.handle('get-chainlit-url', () => {
    return chainlitManager.chainlitUrl;
});

// システム情報取得
ipcMain.handle('get-system-info', () => {
    return {
        platform: process.platform,
        arch: process.arch,
        version: app.getVersion(),
        electronVersion: process.versions.electron,
        nodeVersion: process.versions.node,
        isPackaged: app.isPackaged,
        dotenvPath: process.env.DOTENV_PATH || null,
        logDir: getLogDir()
    };
});

// アプリケーション終了
ipcMain.handle('app-quit', () => {
    app.quit();
});

// ウィンドウ制御
ipcMain.handle('window-minimize', () => {
    if (chainlitManager.mainWindow) {
        chainlitManager.mainWindow.minimize();
    }
});

ipcMain.handle('window-maximize', () => {
    if (chainlitManager.mainWindow) {
        if (chainlitManager.mainWindow.isMaximized()) {
            chainlitManager.mainWindow.unmaximize();
        } else {
            chainlitManager.mainWindow.maximize();
        }
    }
});

ipcMain.handle('window-close', () => {
    if (chainlitManager.mainWindow) {
        chainlitManager.mainWindow.close();
    }
});

// フォルダオープン
ipcMain.handle('open-log-folder', async () => {
    const dir = ensureLogDir();
    return await shell.openPath(dir);
});

console.log('📱 Electron Main Process initialized');
