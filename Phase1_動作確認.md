# Phase 1 動作確認チェックリスト

## 前提条件

### uvのインストール
```bash
# バージョン確認
uv --version

# インストール（Windows PowerShell）
irm https://astral.sh/uv/install.ps1 | iex

# インストール（macOS/Linux）
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## セットアップと動作確認

### 1. 環境準備
```bash
# 仮想環境作成
uv venv

# 依存関係インストール
uv pip install -e .

# .env作成
cp .env.example .env
```

### 2. 環境チェック実行
```bash
uv run python check_env.py
```

確認項目：
- [ ] Python 3.10以上
- [ ] 必要なライブラリがインストール済み
- [ ] 必要なファイル・ディレクトリが存在
- [ ] app.pyの構造が正しい

### 3. APIキー設定（オプション）
`.env`ファイルを編集：
```
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxx
```

### 4. Chainlit起動
```bash
uv run chainlit run app.py
```

### 5. ブラウザで動作確認
- [ ] http://localhost:8000 にアクセス
- [ ] ウェルカムメッセージが表示される
- [ ] Version: 0.1.0 (Phase 1) が表示される
- [ ] テストメッセージを送信できる
- [ ] エコー応答が返ってくる

## トラブルシューティング

### 問題が発生したら

1. **環境チェックを実行**
   ```bash
   uv run python check_env.py
   ```
   表示される問題と解決方法を確認

2. **よくある問題**

   **ModuleNotFoundError**
   ```bash
   uv pip install -e .
   ```

   **ポート8000が使用中**
   ```bash
   uv run chainlit run app.py --port 8001
   ```

   **chainlitコマンドが見つからない**
   ```bash
   uv pip install chainlit
   ```

## Phase 1 完了基準

`check_env.py`で以下が確認できたら完了：
- ✅ All checks passed! Environment is ready.
- ✅ Chainlitが起動する
- ✅ ウェルカムメッセージが表示される
- ✅ メッセージの送受信ができる

## 次のステップ

Phase 2（設定管理機能）に進む：
- `utils/config.py`の作成
- API接続テスト機能の実装
- 設定画面UIの追加