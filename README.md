# AI Workspace - Chainlit Multi-functional Application

## 概要
OpenAI APIを活用した多機能AIワークスペースアプリケーション

## 必要要件
- Python 3.10以上
- [uv](https://github.com/astral-sh/uv) (Pythonパッケージマネージャー)

## uvのインストール

### Windows (PowerShell)
```powershell
irm https://astral.sh/uv/install.ps1 | iex
```

### macOS/Linux
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## セットアップ（3ステップ）

```bash
# 1. 仮想環境作成
uv venv

# 2. 依存関係インストール
uv pip install -r requirements.in

# 3. 環境変数設定
cp .env.example .env
# .envを編集してAPIキー設定
```

## 実行

```bash
# 環境チェック
uv run python check_env.py

# アプリケーション起動
uv run chainlit run app.py
```

ブラウザで http://localhost:8000 にアクセス

## ディレクトリ構成
```
.
├── app.py                 # メインアプリケーション
├── check_env.py          # 環境チェックスクリプト
├── requirements.in       # 依存関係リスト
├── .env.example         # 環境変数テンプレート
├── .env                # 環境変数（要作成）
├── pages/              # チャットページ（Phase 4以降）
├── utils/              # ユーティリティモジュール
└── chat_history.db    # SQLiteデータベース（自動生成）
```

## 開発フェーズ

現在: **Phase 1 - 基本環境構築**

詳細は`開発順序計画書.md`を参照

## トラブルシューティング

問題が発生したら`SIMPLE_SETUP.md`または`FIX_ERROR.md`を参照してください。

### よくあるコマンド

```bash
# パッケージ一覧
uv pip list

# パッケージ追加
uv pip install package_name

# 環境の再構築
rm -rf .venv
uv venv
uv pip install -r requirements.in
```