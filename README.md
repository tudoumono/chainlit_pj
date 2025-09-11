# 🎭 多機能AIワークスペース - Modular Architecture版

Chainlitを使用したモジュラー設計による保守性重視のAIワークスペースアプリケーション

## 🌟 概要

OpenAI Responses APIを活用したプロフェッショナル向けのAIチャットアプリケーションです。  
**2024年8月版**では、保守性向上のためModular Handler Architectureを導入し、2,468行のapp.pyを440行まで削減（82%削減）しました。

### 🎯 主な特徴

- 🗣️ **リアルタイムAI対話** - OpenAI Responses API専用実装
- 💾 **完全な永続化** - SQLiteで履歴が消えない  
- 🏗️ **モジュラー設計** - 保守性とテスト容易性を重視
- 🎭 **ペルソナ管理** - カスタマイズ可能なAIアシスタント
- 🗂️ **3層ベクトルストア** - Company/Personal/Session構造
- 📊 **統計機能** - 使用状況の可視化
- 🔍 **強力な検索機能** - 過去の会話を素早く発見
- 🛡️ **統一エラーハンドリング** - 堅牢で信頼性の高い処理

## 🏗️ アーキテクチャ概要

### Modular Handler Architecture

```
app.py (440行) - コア処理のみ
├── handlers/                 # 機能別ハンドラー
│   ├── command_handler.py    # コマンドルーティング (234行)
│   ├── persona_handler.py    # ペルソナCRUD操作 (183行)
│   ├── settings_handler.py   # 設定・統計・テスト (280行)
│   └── vector_store_commands.py # ベクトルストア管理 (316行)
├── utils/                    # 共通ユーティリティ
│   ├── ui_helper.py         # UI操作の統一化 (107行)
│   ├── error_handler.py     # エラー処理の統一化 (209行)
│   ├── responses_handler.py # Responses API処理
│   ├── config.py           # 設定管理
│   ├── persona_manager.py  # ペルソナエンジン
│   └── vector_store_handler.py # ベクトルストアエンジン
└── .chainlit/              # データ永続化
    ├── chainlit.db         # SQLiteデータベース
    ├── personas.json       # ペルソナデータ
    └── vector_stores/      # ベクトルストア管理
```

### 🎯 設計原則

- **単一責任原則**: 各ハンドラーが明確な責任を持つ
- **DRY原則**: UI・エラー処理の共通化で重複排除
- **疎結合**: 遅延インポートで循環参照を回避
- **高凝集**: 関連機能を論理的にグループ化

## 📚 ドキュメント

- プロジェクト概要: `README.md`（本書）
- 実装サマリ: `IMPLEMENTATION_SUMMARY_v1.0.md`
- Electron/Python統合ガイド: `ElectronとPython統合_詳細実装ガイド.md`
- アーカイブ（旧版・補助資料）:
  - `docs/archive/SETUP_GUIDE.md`
  - `docs/archive/vectorstore_management.md`
  - `docs/archive/CLAUDE.md`
  - `docs/archive/CLAUDE.local.md`

## 📦 実装状況

| Phase | タイトル | 状態 | アーキテクチャ対応 |
|-------|---------|------|----|
| Phase 1 | 基本環境構築 | ✅ 完了 | ✅ 新アーキテクチャ対応 |
| Phase 2 | 設定管理機能 | ✅ 完了 | ✅ settings_handlerに分離 |
| Phase 3 | データベース基盤 | ✅ 完了 | ✅ SQLite永続化対応 |
| Phase 4 | 基本的なチャット機能 | ✅ 完了 | ✅ responses_handler統合 |
| Phase 5 | セッション永続化の強化 | ✅ 完了 | ✅ 新アーキテクチャ対応 |
| Phase 6 | ペルソナ管理 | ✅ 完了 | ✅ persona_handlerに分離 |
| Phase 7 | ベクトルストア | ✅ 完了 | ✅ vector_store_commandsに分離 |
| **Refactor** | **モジュラー化** | ✅ **完了** | ✅ **保守性向上達成** |

## ⚠️ 重要な注意事項

### 📖 API使用に関する重要事項

**OpenAI Responses API専用実装:**
- ✅ **Responses API必須** - `client.responses.create()`のみ使用
- ❌ **Chat Completions API使用禁止** - 一切の使用を禁止
- ✅ OpenAIの正式サポート機能を使用
- ✅ 会話の状態管理はOpenAIのresponse_idで管理

**ベクトルストア3層構造:**
- 🏢 **Company層** - 環境変数`COMPANY_VECTOR_STORE_ID`
- 👤 **Personal層** - ユーザー別、自動作成・管理
- 💬 **Session層** - チャット別、一時的

### Chainlit Action API仕様

**`payload`パラメータは必ず辞書型（dict）である必要があります:**

```python
# ❌ 間違い
cl.Action(name="action", payload="yes", label="はい")  # エラー

# ✅ 正しい
cl.Action(name="action", payload={"action": "yes"}, label="はい")
```

ヘルパー関数の使用を推奨：
```python
from utils.action_helper import ask_confirmation
if await ask_confirmation("削除してもよろしいですか？"):
    # 削除処理
```

## 🚀 クイックスタート

### 1. 環境構築

```bash
# 依存関係をインストール
pip install -r requirements.txt

# 環境変数を設定
cp .env.example .env
```

### 2. 環境変数設定

`.env`ファイルを編集：
```env
# OpenAI API設定
OPENAI_API_KEY=your_api_key_here
DEFAULT_MODEL=gpt-4o-mini

# 認証設定
CHAINLIT_AUTH_TYPE=credentials
CHAINLIT_AUTH_SECRET=admin123

# ベクトルストア設定（オプション）
COMPANY_VECTOR_STORE_ID=vs_company_xxxxx
```

### 3. アプリケーション起動

```bash
# 推奨: Pythonスクリプトで起動
python run.py

# または直接Chainlitで起動
chainlit run app.py
```

### 4. ログイン

ブラウザで http://localhost:8000 を開き、以下でログイン：
- **ユーザー名**: admin
- **パスワード**: admin123

## 🎛️ 機能一覧

### コマンド

| コマンド | 説明 | 実装ハンドラー |
|---------|------|-------------|
| `/help` | ヘルプ表示 | CommandHandler |
| `/stats` | 統計情報表示 | SettingsHandler |
| `/status` | システム状態表示 | SettingsHandler |
| `/settings` | 設定管理画面 | SettingsHandler |
| `/test` | API接続テスト | SettingsHandler |
| `/setkey [APIキー]` | APIキー設定 | SettingsHandler |
| `/model [モデル名]` | モデル変更 | SettingsHandler |
| `/system [プロンプト]` | システムプロンプト設定 | SettingsHandler |
| `/new` | 新しいチャット開始 | SettingsHandler |
| `/clear` | チャット履歴クリア | CommandHandler |

### ペルソナ管理

| コマンド | 説明 | 実装ハンドラー |
|---------|------|-------------|
| `/persona` | ペルソナ一覧表示 | PersonaHandler |
| `/persona [名前]` | ペルソナ切り替え | PersonaHandler |
| `/persona create` | 新しいペルソナ作成 | PersonaHandler |
| `/persona edit [名前]` | ペルソナ編集 | PersonaHandler |
| `/persona delete [名前]` | ペルソナ削除 | PersonaHandler |

### ベクトルストア管理

| コマンド | 説明 | 実装ハンドラー |
|---------|------|-------------|
| `/vs` | ベクトルストア一覧 | VectorStoreHandler |
| ファイルアップロード | 自動ベクトルストア追加 | VectorStoreHandler |

### 設定UI

チャット画面右上の設定パネルから：
- 🤖 **Model**: GPT-4o, GPT-4o-mini, GPT-4-turbo
- 🌡️ **Temperature**: 0.0-2.0（創造性調整）
- 🔄 **Stream**: リアルタイム応答の有効/無効
- 🏢 **Company Vector Store ID**: 企業レベルベクトルストア
- 👤 **Personal Vector Store ID**: 個人レベルベクトルストア

## 🔧 技術スタック

- **フレームワーク**: Chainlit
- **言語**: Python 3.11+
- **AI API**: OpenAI Responses API（専用実装）
- **データベース**: SQLite（永続化）
- **認証**: Chainlit Authentication
- **アーキテクチャ**: Modular Handler Pattern

## 🧪 開発・テスト

### コード品質チェック

```bash
# 構文チェック
python3 -m py_compile app.py handlers/*.py utils/*.py

# インポートチェック（依存関係確認後）
python3 -c "import app; print('Import successful')"
```

## 💻 Electron統合と配布方針（重要）

- 起動方式（ADR-0001）: Option B を採用。
  - Electron Main が埋め込みPythonを直接 `spawn` し、Chainlit(8000) と Electron API(8001) を個別起動・監視・終了します。
  - 開発時は `uv run`、配布時は `resources/python_dist` の埋め込みPythonを使用します。
- 代表IPC（予定）: `start-chainlit` / `start-electron-api` / `stop-*`（冪等）
- 配布要件: `electron-builder` の `extraResources` に `python_dist`（埋め込みPython + 必要site-packages）を同梱します。
- 環境変数（packaged例）:
  - `PYTHONHOME`, `PYTHONPATH`, `PATH`（`path.delimiter` 使用）
  - `CHAINLIT_CONFIG_PATH` → `<resources>/.chainlit/config.toml`
  - `EXE_DIR`, `CHAT_LOG_DIR`, `CONSOLE_LOG_DIR` → `app.getPath('userData')` 等

### 共有 .env / データの運用（Portable版）
- 開発時: ルートの `.env` を使用（両者で共通）。
- 配布時: 初回起動時に **EXEと同じディレクトリ** に `.env` と `.chainlit/` を自動作成（テンプレをコピー）。
- 会話履歴は `.chainlit/chainlit.db`（EXEと同じ場所）。
- EXEフォルダに書き込み権限が無い場合はエラーで起動を停止します。

詳細: docs/WINDOWS_PACKAGING.md / docs/WINDOWS_TASKS.md を参照（配布はWindowsのみ）。

## 📨 Windows配布手順（Portable版）

インストール不要のZIP配布ガイドです。ZIPを展開してEXEを実行するだけで使えます。

- 対象OS: Windows 10 / 11（x64）
- 配布物: `Chainlit AI Workspace-<version>-windows-x64.zip`
- 使い方:
  1. ZIPを書き込み可能なフォルダに展開（デスクトップ/ドキュメント配下など）。
  2. 展開フォルダ直下の `Chainlit AI Workspace.exe` を実行。
  3. 初回に `.env` と `.chainlit/` がEXEと同じ場所に自動作成されます。`.env` の `OPENAI_API_KEY` を設定してください。
- 保存先（すべてEXEと同じフォルダ）:
  - `.env`, `.chainlit/chainlit.db`, `.chainlit/personas/`
- 更新方法: 新しいZIPを上書き展開（履歴と設定は残ります）。
- 注意: `C:\\Program Files` 配下は書き込み不可のため不可。SmartScreen警告は「詳細情報」→「実行」で進めます。

選択肢A（`integrated_run.py` による統合起動）を選ばない理由:
- 起動/終了/ログ/環境変数の責務が分散し、配布運用が複雑化するため。
- 非エンジニア配布で外部依存（`uv` 等）が残るリスクがあるため。
- Electron 側でヘルスチェックとUX（再試行・通知）を完結させにくいため。

### ファイル構造詳細

```
chainlit_pj/
├── app.py                    # メインアプリケーション (440行)
├── docs/archive/app_backup.py # リファクタリング前バックアップ（退避済み）
├── docs/archive/SETUP_GUIDE.md
├── docs/archive/vectorstore_management.md
├── docs/archive/CLAUDE.md
├── docs/archive/CLAUDE.local.md
├── run.py                    # 起動スクリプト
├── auth.py                   # 認証ハンドラー
├── data_layer.py             # SQLiteデータレイヤー
├── handlers/                 # Modular Handlers
│   ├── __init__.py
│   ├── command_handler.py    # コマンドルーティング
│   ├── persona_handler.py    # ペルソナ管理
│   ├── settings_handler.py   # 設定・統計管理
│   └── vector_store_commands.py # ベクトルストア管理
├── utils/                    # 共通ユーティリティ
│   ├── __init__.py
│   ├── ui_helper.py         # UI処理統一化
│   ├── error_handler.py     # エラー処理統一化
│   ├── config.py            # 設定管理
│   ├── responses_handler.py # Responses API処理
│   ├── tools_config.py      # Tools設定
│   ├── persona_manager.py   # ペルソナエンジン
│   ├── vector_store_handler.py # ベクトルストアエンジン
│   ├── action_helper.py     # Actionヘルパー
│   └── logger.py            # ログシステム
├── .chainlit/               # Chainlit設定・データ
│   ├── config.toml          # Chainlit設定
│   ├── chainlit.db          # SQLiteデータベース
│   ├── tools_config.json    # Tools設定
│   ├── personas.json        # ペルソナデータ
│   └── vector_stores/       # ベクトルストア管理
├── docs/                    # ドキュメント
├── .env                     # 環境変数
└── requirements.txt         # 依存関係
```

## 🎯 開発指針

### 新機能追加時の指針

1. **適切なハンドラーに機能を追加**
   - UI関連 → `ui_helper.py`
   - エラー処理 → `error_handler.py`  
   - コマンド → `command_handler.py`
   - ペルソナ → `persona_handler.py`
   - 設定 → `settings_handler.py`
   - ベクトルストア → `vector_store_commands.py`

2. **単一責任原則を遵守**
   - 1つのクラス/関数は1つの責任のみ
   - 機能追加時は既存ハンドラーの責任範囲を確認

3. **統一されたエラーハンドリング**
   - `error_handler.py`の専用メソッドを使用
   - ユーザーフレンドリーなエラーメッセージ

4. **統一されたUI処理**
   - `ui_helper.py`のメソッドを使用
   - 一貫したメッセージフォーマット

## 📝 ライセンス

MIT License

## 👥 貢献

プルリクエストやイシューの報告を歓迎します！

新しいModular Handler Architectureに準拠した開発をお願いします。

## 🔄 更新履歴

- **v1.0.0** (2024-08) - **Modular Handler Architecture導入**
  - app.pyを2,468行→440行に削減（82%削減）
  - handlers/パッケージによる機能分離
  - 統一UI処理・エラーハンドリング
  - 保守性・テスト容易性の大幅向上
- **v0.7.0** - Responses API + Tools機能対応
- **v0.6.1** - SQLite永続化実装  
- **v0.5.0** - セッション管理強化
- **v0.4.0** - 基本的なチャット機能
- **v0.3.0** - データベース基盤
- **v0.2.0** - 設定管理機能
- **v0.1.0** - 初期リリース

## Ports and Logs
- Ports are configurable via `.env`: `CHAINLIT_PORT` (default 8000), `ELECTRON_API_PORT` (default 8001).
- Electron main updates CSP dynamically to match these ports.
- Logs are written under `<UserData>/logs` and accessible via Settings.

Windows packaging steps: see `docs/WINDOWS_PACKAGING.md` and `docs/WINDOWS_TASKS.md`.
