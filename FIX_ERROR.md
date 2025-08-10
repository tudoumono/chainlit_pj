# AI Workspace - セットアップと実行ガイド

## エラー解決方法

`uv sync`でエラーが発生した場合は、代わりに以下のコマンドを使用してください：

### 正しいセットアップ手順

```bash
# 1. 仮想環境がアクティブになっていることを確認
# (ai-workspace-chainlit) というプロンプトが表示されているはず

# 2. 依存関係を直接インストール（syncの代わり）
uv pip install chainlit openai python-dotenv aiosqlite pypdf pillow reportlab jinja2 httpx typing-extensions

# 開発用ツール（オプション）
uv pip install pytest pytest-asyncio black ruff mypy

# 3. 環境チェック
uv run python check_env.py

# 4. アプリケーション起動
uv run chainlit run app.py
```

## なぜエラーが起きたか

- `uv sync`はプロジェクトをPythonパッケージとしてビルドしようとします
- ChainlitアプリケーションはWebアプリなので、パッケージ化は不要です
- 単に依存関係をインストールすれば動作します

## 推奨される使い方

### 初回セットアップ
```bash
# 仮想環境作成（未作成の場合）
uv venv

# 仮想環境を有効化
.\.venv\Scripts\Activate.ps1  # Windows PowerShell
# または
source .venv/bin/activate      # macOS/Linux

# 依存関係インストール
uv pip install chainlit openai python-dotenv aiosqlite pypdf pillow reportlab jinja2 httpx typing-extensions
```

### 日常的な使用
```bash
# アプリ起動
uv run chainlit run app.py

# 環境チェック
uv run python check_env.py
```

## トラブルシューティング

### もし`uv pip install`でもエラーが出る場合

```bash
# キャッシュをクリアして再インストール
uv pip install --force-reinstall chainlit openai python-dotenv aiosqlite pypdf pillow reportlab jinja2 httpx typing-extensions
```

### パッケージのバージョン確認
```bash
uv pip list
```

これで問題なく動作するはずです！